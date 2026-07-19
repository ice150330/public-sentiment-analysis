import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, DatePicker, Drawer, Input, message, Pagination, Select, Tag } from 'antd';
import {
  DownloadOutlined,
  LinkOutlined,
  ReloadOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import type { Dayjs } from 'dayjs';
import {
  exportTopicsCsv,
  getErrorMessage,
  getPlatforms,
  getTopics,
  HotTopic,
  Pagination as PageInfo,
  Platform,
  TopicQuery,
} from '@/services/api';
import {
  DataState,
  formatDateTime,
  formatNumber,
  Panel,
  PlatformBadge,
} from '@/components/DesignSystem';
import { HotspotsViewProps } from '../types';

const PAGE_SIZE = 12;

type RangeValue = [Dayjs | null, Dayjs | null] | null;

interface TopicFilters {
  platform?: string;
  category?: string;
  keyword: string;
  range: RangeValue;
  sortBy: string;
  sortOrder: 'asc' | 'desc';
}

const DEFAULT_FILTERS: TopicFilters = {
  platform: undefined,
  category: undefined,
  keyword: '',
  range: null,
  sortBy: 'heat_score',
  sortOrder: 'desc',
};

const buildQuery = (filters: TopicFilters, page: number): TopicQuery => ({
  platform: filters.platform,
  category: filters.category,
  keyword: filters.keyword.trim() || undefined,
  start_time: filters.range?.[0]?.toISOString(),
  end_time: filters.range?.[1]?.toISOString(),
  sort_by: filters.sortBy,
  sort_order: filters.sortOrder,
  page,
  page_size: PAGE_SIZE,
});

/** 热榜列表 —— 筛选条 + 排名列表 + 平台分布/热度对比侧栏 + 话题详情 Drawer */
const TopicListView: React.FC<HotspotsViewProps> = ({ refreshKey, onSyncState }) => {
  const navigate = useNavigate();
  const [topics, setTopics] = useState<HotTopic[]>([]);
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [pagination, setPagination] = useState<PageInfo | null>(null);
  const [draft, setDraft] = useState<TopicFilters>(DEFAULT_FILTERS);
  const [applied, setApplied] = useState<TopicFilters>(DEFAULT_FILTERS);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTopic, setActiveTopic] = useState<HotTopic | null>(null);

  useEffect(() => {
    let mounted = true;
    getPlatforms()
      .then((res) => {
        if (mounted) setPlatforms(res.data || []);
      })
      .catch(() => undefined);
    return () => {
      mounted = false;
    };
  }, [refreshKey]);

  const fetchTopics = useCallback(async () => {
    try {
      setLoading(true);
      onSyncState({ refreshing: true });
      const res = await getTopics(buildQuery(applied, page));
      setTopics(res.data?.items || []);
      setPagination(res.data?.pagination || null);
      setError(null);
      onSyncState({ refreshing: false, lastUpdated: new Date().toISOString() });
    } catch (err) {
      setError(getErrorMessage(err));
      onSyncState({ refreshing: false });
    } finally {
      setLoading(false);
    }
  }, [applied, page, onSyncState]);

  useEffect(() => {
    fetchTopics();
  }, [fetchTopics, refreshKey]);

  /** 分类可选项从已加载数据去重 */
  const categories = useMemo(() => {
    const set = new Set<string>();
    topics.forEach((topic) => {
      if (topic.category) set.add(topic.category);
    });
    return Array.from(set).sort();
  }, [topics]);

  /** 平台分布：当前列表按平台聚合条数 */
  const platformStats = useMemo(() => {
    const map = new Map<string, number>();
    topics.forEach((topic) => {
      const key = topic.platform_name || `平台 ${topic.platform_id}`;
      map.set(key, (map.get(key) || 0) + 1);
    });
    return Array.from(map.entries())
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 6);
  }, [topics]);

  /** 热度 Top 对比：当前列表热度前 5 */
  const heatTop = useMemo(
    () => [...topics].sort((a, b) => (b.heat_score || 0) - (a.heat_score || 0)).slice(0, 5),
    [topics],
  );
  const heatMax = heatTop[0]?.heat_score || 1;

  const applyFilters = () => {
    setApplied(draft);
    setPage(1);
  };

  const resetFilters = () => {
    setDraft(DEFAULT_FILTERS);
    setApplied(DEFAULT_FILTERS);
    setPage(1);
  };

  const handleExport = async () => {
    try {
      setExporting(true);
      await exportTopicsCsv({ ...buildQuery(applied, 1), limit: 5000 });
      message.success('热榜 CSV 已开始下载');
    } catch (err) {
      message.error(getErrorMessage(err));
    } finally {
      setExporting(false);
    }
  };

  const rankOf = (index: number) => (page - 1) * (pagination?.page_size || PAGE_SIZE) + index + 1;

  return (
    <>
      <div className="psa-filter-bar">
        <Select
          allowClear
          value={draft.platform}
          onChange={(value) => setDraft((prev) => ({ ...prev, platform: value }))}
          placeholder="全部平台"
          style={{ width: 140 }}
          options={platforms.map((item) => ({ value: item.name, label: item.display_name }))}
        />
        <Select
          allowClear
          value={draft.category}
          onChange={(value) => setDraft((prev) => ({ ...prev, category: value }))}
          placeholder="全部分类"
          style={{ width: 130 }}
          options={categories.map((item) => ({ value: item, label: item }))}
        />
        <Input
          allowClear
          value={draft.keyword}
          onChange={(event) => setDraft((prev) => ({ ...prev, keyword: event.target.value }))}
          onPressEnter={applyFilters}
          placeholder="搜索话题关键词"
          style={{ width: 200 }}
        />
        <DatePicker.RangePicker
          showTime
          value={draft.range}
          onChange={(value) => setDraft((prev) => ({ ...prev, range: value }))}
          placeholder={['开始时间', '结束时间']}
        />
        <Select
          value={draft.sortBy}
          onChange={(value) => setDraft((prev) => ({ ...prev, sortBy: value }))}
          style={{ width: 130 }}
          options={[
            { value: 'heat_score', label: '按热度' },
            { value: 'crawl_time', label: '按采集时间' },
            { value: 'created_at', label: '按入库时间' },
          ]}
        />
        <Select
          value={draft.sortOrder}
          onChange={(value) => setDraft((prev) => ({ ...prev, sortOrder: value }))}
          style={{ width: 110 }}
          options={[
            { value: 'desc', label: '降序' },
            { value: 'asc', label: '升序' },
          ]}
        />
        <Button type="primary" icon={<SearchOutlined />} onClick={applyFilters} loading={loading}>
          查询
        </Button>
        <Button icon={<ReloadOutlined />} onClick={resetFilters}>
          重置
        </Button>
        <Button icon={<DownloadOutlined />} onClick={handleExport} loading={exporting}>
          导出 CSV
        </Button>
      </div>

      <DataState loading={loading} error={error} empty={topics.length === 0} emptyTitle="暂无热榜数据">
        <div className="psa-grid main-side" style={{ marginTop: 16 }}>
          <Panel title="热榜列表" eyebrow={pagination ? `共 ${formatNumber(pagination.total)} 条` : undefined}>
            <div className="psa-list">
              {topics.map((topic, index) => {
                const rank = rankOf(index);
                return (
                  <button
                    type="button"
                    className="psa-row hs-row-3"
                    key={topic.id}
                    onClick={() => setActiveTopic(topic)}
                  >
                    <span className={`hs-rank${rank <= 3 ? ` top-${rank}` : ''}`}>{rank}</span>
                    <div>
                      <p className="psa-row-title">{topic.title}</p>
                      <div className="psa-row-meta">
                        <PlatformBadge name={topic.platform_name} />
                        <Tag className="psa-tag muted">{topic.category || '未分类'}</Tag>
                        <span>{formatDateTime(topic.crawl_time)}</span>
                      </div>
                    </div>
                    <strong className="hs-heat">{formatNumber(topic.heat_score)}</strong>
                  </button>
                );
              })}
            </div>
            {pagination && pagination.total > 0 && (
              <div className="hs-pagination">
                <Pagination
                  size="small"
                  current={pagination.page}
                  pageSize={pagination.page_size}
                  total={pagination.total}
                  onChange={setPage}
                  showSizeChanger={false}
                />
              </div>
            )}
          </Panel>

          <div className="hs-side-stack">
            <Panel title="平台分布" eyebrow="当前列表">
              <DataState empty={platformStats.length === 0} emptyTitle="暂无平台数据">
                <div className="psa-score-bars">
                  {platformStats.map((item) => (
                    <div className="psa-score-line" key={item.name}>
                      <span>{item.name}</span>
                      <div className="psa-bar-track">
                        <div
                          className="psa-bar-fill"
                          style={{ width: `${Math.round((item.count / Math.max(1, topics.length)) * 100)}%` }}
                        />
                      </div>
                      <strong>{item.count}</strong>
                    </div>
                  ))}
                </div>
              </DataState>
            </Panel>
            <Panel title="热度 Top 对比" eyebrow="当前列表 TOP5">
              <DataState empty={heatTop.length === 0} emptyTitle="暂无热度数据">
                <div className="psa-score-bars">
                  {heatTop.map((topic) => (
                    <div className="psa-score-line" key={topic.id}>
                      <span>{topic.platform_name || topic.title.slice(0, 6)}</span>
                      <div className="psa-bar-track">
                        <div
                          className="psa-bar-fill negative"
                          style={{ width: `${Math.max(4, Math.round(((topic.heat_score || 0) / heatMax) * 100))}%` }}
                        />
                      </div>
                      <strong>{formatNumber(topic.heat_score)}</strong>
                    </div>
                  ))}
                </div>
              </DataState>
            </Panel>
          </div>
        </div>
      </DataState>

      <Drawer
        title="话题详情"
        width={420}
        open={activeTopic !== null}
        onClose={() => setActiveTopic(null)}
      >
        {activeTopic && (
          <div className="psa-detail-list">
            <div>
              <p className="psa-row-title" style={{ fontSize: 15 }}>{activeTopic.title}</p>
              <div className="psa-row-meta">
                <PlatformBadge name={activeTopic.platform_name} />
                <Tag className="psa-tag muted">{activeTopic.category || '未分类'}</Tag>
              </div>
            </div>
            <div className="psa-detail-item">
              <span>热度</span>
              <strong>{formatNumber(activeTopic.heat_score)}</strong>
            </div>
            <div className="psa-detail-item">
              <span>平台</span>
              <strong>{activeTopic.platform_name || `平台 ${activeTopic.platform_id}`}</strong>
            </div>
            <div className="psa-detail-item">
              <span>分类</span>
              <strong>{activeTopic.category || '未分类'}</strong>
            </div>
            <div className="psa-detail-item">
              <span>摘要</span>
              <strong style={{ fontWeight: 600 }}>{activeTopic.content_summary || '暂无摘要'}</strong>
            </div>
            <div className="psa-detail-item">
              <span>原文链接</span>
              <strong>
                {activeTopic.url ? (
                  <a className="hs-drawer-link" href={activeTopic.url} target="_blank" rel="noreferrer">
                    <LinkOutlined /> 打开原文
                  </a>
                ) : (
                  '暂无'
                )}
              </strong>
            </div>
            <div className="psa-detail-item">
              <span>采集时间</span>
              <strong>{formatDateTime(activeTopic.crawl_time)}</strong>
            </div>
            <Button
              type="primary"
              block
              onClick={() => navigate(`/topics/${activeTopic.id}`)}
            >
              查看完整详情
            </Button>
          </div>
        )}
      </Drawer>
    </>
  );
};

export default TopicListView;
