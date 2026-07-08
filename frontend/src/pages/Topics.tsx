import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Input, Pagination, Select } from 'antd';
import {
  BranchesOutlined,
  FireOutlined,
  PartitionOutlined,
  ProfileOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import {
  getErrorMessage,
  getPlatforms,
  getRelatedTopics,
  getTopicPropagation,
  getTopicSamples,
  getTopics,
  HotTopic,
  Pagination as PageInfo,
  Platform,
  TopicPropagation,
  TopicRelation,
  TopicSample,
} from '../services/api';
import {
  DataState,
  formatDateTime,
  formatNumber,
  ModuleFrame,
  Panel,
  PlatformBadge,
  SubView,
} from '../components/DesignSystem';

const views: SubView[] = [
  { key: 'list', label: '热榜列表', icon: <FireOutlined /> },
  { key: 'clusters', label: '聚类主题', icon: <PartitionOutlined /> },
  { key: 'spread', label: '传播路径', icon: <BranchesOutlined /> },
  { key: 'detail', label: '话题详情', icon: <ProfileOutlined /> },
];

const Topics: React.FC = () => {
  const [activeView, setActiveView] = useState('list');
  const [topics, setTopics] = useState<HotTopic[]>([]);
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [pagination, setPagination] = useState<PageInfo | null>(null);
  const [selectedTopicId, setSelectedTopicId] = useState<number | null>(null);
  const [keyword, setKeyword] = useState('');
  const [platform, setPlatform] = useState<string | undefined>();
  const [sortBy, setSortBy] = useState('heat_score');
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const selectedTopic = topics.find((topic) => topic.id === selectedTopicId) || null;

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [platformRes, topicRes] = await Promise.all([
        getPlatforms(),
        getTopics({
          keyword: keyword.trim() || undefined,
          platform,
          sort_by: sortBy,
          sort_order: 'desc',
          page,
          page_size: 12,
        }),
      ]);

      const items = topicRes.data.items || [];
      setPlatforms(platformRes.data || []);
      setTopics(items);
      setPagination(topicRes.data.pagination);
      setSelectedTopicId((current) => {
        if (current && items.some((item) => item.id === current)) return current;
        return items[0]?.id ?? null;
      });
      setLastUpdated(new Date().toISOString());
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [keyword, page, platform, sortBy]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const clusters = useMemo(() => {
    const map = new Map<string, { name: string; count: number; heat: number }>();
    topics.forEach((topic) => {
      const key = topic.category || '未分类';
      const current = map.get(key) || { name: key, count: 0, heat: 0 };
      current.count += 1;
      current.heat += topic.heat_score || 0;
      map.set(key, current);
    });
    return Array.from(map.values()).sort((a, b) => b.heat - a.heat);
  }, [topics]);

  const platformStats = useMemo(() => {
    const map = new Map<string, { name: string; count: number; heat: number }>();
    topics.forEach((topic) => {
      const key = topic.platform_name || String(topic.platform_id);
      const current = map.get(key) || { name: key, count: 0, heat: 0 };
      current.count += 1;
      current.heat += topic.heat_score || 0;
      map.set(key, current);
    });
    return Array.from(map.values()).sort((a, b) => b.heat - a.heat);
  }, [topics]);

  const clusterChart = useMemo(() => {
    if (clusters.length === 0) return null;
    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 92, right: 18, top: 16, bottom: 28 },
      xAxis: { type: 'value', splitLine: { lineStyle: { color: '#E7EEF7' } } },
      yAxis: { type: 'category', data: clusters.map((item) => item.name), axisLabel: { color: '#64748B' } },
      series: [
        {
          type: 'bar',
          barWidth: 12,
          itemStyle: { color: '#2563EB', borderRadius: 999 },
          data: clusters.map((item) => item.heat),
        },
      ],
    };
  }, [clusters]);

  const spreadChart = useMemo(() => {
    if (platformStats.length === 0) return null;
    return {
      tooltip: { trigger: 'item' },
      color: ['#F43F5E', '#111827', '#EF4444', '#2563EB', '#0EA5E9', '#3B82F6'],
      series: [
        {
          type: 'pie',
          radius: ['44%', '72%'],
          itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
          data: platformStats.map((item) => ({ name: item.name, value: item.count })),
        },
      ],
    };
  }, [platformStats]);

  const resetFilters = () => {
    setKeyword('');
    setPlatform(undefined);
    setSortBy('heat_score');
    setPage(1);
  };

  const renderContent = () => {
    if (activeView === 'clusters') {
      return (
        <DataState loading={loading} error={error} empty={topics.length === 0} emptyTitle="暂无可聚类话题">
          <div className="psa-grid two-one">
            <Panel title="聚类主题" eyebrow="按真实分类字段聚合">
              <DataState empty={!clusterChart} emptyTitle="暂无分类聚合">
                <ReactECharts option={clusterChart || {}} className="psa-chart large" />
              </DataState>
            </Panel>
            <Panel title="主题簇列表">
              <div className="psa-list">
                {clusters.map((cluster) => (
                  <div className="psa-row" key={cluster.name}>
                    <div>
                      <p className="psa-row-title">{cluster.name}</p>
                      <div className="psa-row-meta">
                        <span>{cluster.count} 个话题</span>
                        <span>热度 {formatNumber(cluster.heat)}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Panel>
          </div>
        </DataState>
      );
    }

    if (activeView === 'spread') {
      return (
        <DataState loading={loading} error={error} empty={topics.length === 0} emptyTitle="暂无传播数据">
          <div className="psa-grid two-one">
            <Panel title="平台传播占比">
              <DataState empty={!spreadChart} emptyTitle="暂无平台占比">
                <ReactECharts option={spreadChart || {}} className="psa-chart large" />
              </DataState>
            </Panel>
            <Panel title="传播来源">
              <div className="psa-list">
                {platformStats.map((item) => (
                  <div className="psa-row" key={item.name}>
                    <div>
                      <p className="psa-row-title">{item.name}</p>
                      <div className="psa-row-meta">
                        <span>{item.count} 条话题</span>
                        <span>累计热度 {formatNumber(item.heat)}</span>
                      </div>
                    </div>
                    <PlatformBadge name={item.name} />
                  </div>
                ))}
              </div>
            </Panel>
          </div>
        </DataState>
      );
    }

    if (activeView === 'detail') {
      return <TopicDetail topic={selectedTopic} loading={loading} error={error} />;
    }

    return (
      <>
        <FilterBar
          keyword={keyword}
          platform={platform}
          sortBy={sortBy}
          platforms={platforms}
          onKeyword={setKeyword}
          onPlatform={(value) => {
            setPlatform(value);
            setPage(1);
          }}
          onSort={(value) => {
            setSortBy(value);
            setPage(1);
          }}
          onReset={resetFilters}
          onRefresh={fetchData}
          loading={loading}
        />
        <DataState loading={loading} error={error} empty={topics.length === 0} emptyTitle="暂无热榜数据">
          <div className="psa-grid main-side" style={{ marginTop: 16 }}>
            <Panel title="热榜列表">
              <div className="psa-list">
                {topics.map((topic, index) => (
                  <button
                    type="button"
                    className="psa-row"
                    key={topic.id}
                    onClick={() => {
                      setSelectedTopicId(topic.id);
                      setActiveView('detail');
                    }}
                  >
                    <div>
                      <span className="psa-heat-rank">#{(pagination?.page || 1) * 12 - 11 + index}</span>
                      <p className="psa-row-title">{topic.title}</p>
                      <div className="psa-row-meta">
                        <PlatformBadge name={topic.platform_name} />
                        <span>{topic.category || '未分类'}</span>
                        <span>{formatDateTime(topic.crawl_time)}</span>
                      </div>
                    </div>
                    <strong>{formatNumber(topic.heat_score)}</strong>
                  </button>
                ))}
              </div>
              {pagination && (
                <Pagination
                  size="small"
                  current={pagination.page}
                  pageSize={pagination.page_size}
                  total={pagination.total}
                  onChange={setPage}
                  style={{ marginTop: 14 }}
                />
              )}
            </Panel>
            <div className="psa-grid">
              <Panel title="平台洞察">
                <DataState empty={platformStats.length === 0} emptyTitle="暂无平台洞察">
                  <div className="psa-list">
                    {platformStats.slice(0, 6).map((item) => (
                      <div className="psa-score-line" key={item.name}>
                        <span>{item.name}</span>
                        <div className="psa-bar-track">
                          <div
                            className="psa-bar-fill"
                            style={{
                              width: `${Math.min(100, Math.round((item.count / Math.max(1, topics.length)) * 100))}%`,
                            }}
                          />
                        </div>
                        <strong>{item.count}</strong>
                      </div>
                    ))}
                  </div>
                </DataState>
              </Panel>
              <Panel title="当前话题">
                <TopicDetailCompact topic={selectedTopic} />
              </Panel>
            </div>
          </div>
        </DataState>
      </>
    );
  };

  return (
    <ModuleFrame
      moduleLabel="热点"
      activeView={activeView}
      views={views}
      onViewChange={setActiveView}
      searchValue={keyword}
      onSearchChange={(value) => {
        setKeyword(value);
        setPage(1);
      }}
      onRefresh={fetchData}
      refreshing={loading}
      lastUpdated={lastUpdated}
    >
      {renderContent()}
    </ModuleFrame>
  );
};

const FilterBar: React.FC<{
  keyword: string;
  platform?: string;
  sortBy: string;
  platforms: Platform[];
  loading: boolean;
  onKeyword: (value: string) => void;
  onPlatform: (value?: string) => void;
  onSort: (value: string) => void;
  onReset: () => void;
  onRefresh: () => void;
}> = ({ keyword, platform, sortBy, platforms, loading, onKeyword, onPlatform, onSort, onReset, onRefresh }) => (
  <div className="psa-filter-bar">
    <Input
      allowClear
      value={keyword}
      onChange={(event) => onKeyword(event.target.value)}
      placeholder="搜索话题标题"
      style={{ width: 240 }}
    />
    <Select
      allowClear
      value={platform}
      onChange={onPlatform}
      placeholder="全部平台"
      style={{ width: 160 }}
      options={platforms.map((item) => ({ value: item.name, label: item.display_name }))}
    />
    <Select
      value={sortBy}
      onChange={onSort}
      style={{ width: 160 }}
      options={[
        { value: 'heat_score', label: '按热度' },
        { value: 'crawl_time', label: '按采集时间' },
        { value: 'created_at', label: '按入库时间' },
      ]}
    />
    <Button onClick={onReset}>重置</Button>
    <Button icon={<ReloadOutlined />} onClick={onRefresh} loading={loading}>
      刷新
    </Button>
  </div>
);

const TopicDetailCompact: React.FC<{ topic: HotTopic | null }> = ({ topic }) => {
  if (!topic) {
    return (
      <DataState empty emptyTitle="未选择话题" emptyDescription="从左侧真实热榜列表选择话题后显示详情。">
        <div />
      </DataState>
    );
  }

  return (
    <div className="psa-detail-list">
      <div>
        <p className="psa-row-title">{topic.title}</p>
        <div className="psa-row-meta">
          <PlatformBadge name={topic.platform_name} />
          <span>{topic.category || '未分类'}</span>
        </div>
      </div>
      <div className="psa-detail-item">
        <span>热度</span>
        <strong>{formatNumber(topic.heat_score)}</strong>
      </div>
      <div className="psa-detail-item">
        <span>采集时间</span>
        <strong>{formatDateTime(topic.crawl_time)}</strong>
      </div>
    </div>
  );
};

const TopicDetail: React.FC<{ topic: HotTopic | null; loading: boolean; error: string | null }> = ({
  topic,
  loading,
  error,
}) => {
  const [samples, setSamples] = useState<TopicSample[]>([]);
  const [relations, setRelations] = useState<TopicRelation[]>([]);
  const [propagation, setPropagation] = useState<TopicPropagation | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    if (!topic) {
      setSamples([]);
      setRelations([]);
      setPropagation(null);
      return;
    }

    let mounted = true;
    setDetailLoading(true);
    Promise.all([
      getTopicSamples(topic.id, { page: 1, page_size: 5 }),
      getRelatedTopics(topic.id),
      getTopicPropagation(topic.id),
    ])
      .then(([sampleRes, relationRes, propagationRes]) => {
        if (!mounted) return;
        setSamples(sampleRes.data?.items || []);
        setRelations(relationRes.data?.relations || []);
        setPropagation(propagationRes.data);
        setDetailError(null);
      })
      .catch((err) => {
        if (!mounted) return;
        setDetailError(getErrorMessage(err));
      })
      .finally(() => {
        if (mounted) setDetailLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [topic]);

  return (
    <DataState loading={loading} error={error} empty={!topic} emptyTitle="暂无话题详情">
      <div className="psa-grid one-two">
        <Panel title="话题详情" className="tall">
          {topic && (
            <div className="psa-detail-list">
              <h2 style={{ margin: 0 }}>{topic.title}</h2>
              <div className="psa-row-meta">
                <PlatformBadge name={topic.platform_name} />
                <span>{topic.category || '未分类'}</span>
                <span>{formatDateTime(topic.crawl_time)}</span>
              </div>
              <div className="psa-detail-item">
                <span>平台话题 ID</span>
                <strong>{topic.topic_id}</strong>
              </div>
              <div className="psa-detail-item">
                <span>热度</span>
                <strong>{formatNumber(topic.heat_score)}</strong>
              </div>
              <div className="psa-detail-item">
                <span>链接</span>
                <strong>{topic.url || '暂无'}</strong>
              </div>
              <div className="psa-detail-item">
                <span>摘要</span>
                <strong>{topic.content_summary || '暂无摘要'}</strong>
              </div>
            </div>
          )}
        </Panel>
        <Panel title="扩展信息">
          <DataState
            loading={detailLoading}
            error={detailError}
            empty={samples.length === 0 && relations.length === 0 && !propagation}
            emptyTitle="暂无扩展信息"
          >
            <div className="psa-detail-list">
              <div className="psa-detail-item">
                <span>传播深度</span>
                <strong>{formatNumber(propagation?.path.depth)}</strong>
              </div>
              <div className="psa-detail-item">
                <span>传播节点</span>
                <strong>{formatNumber(propagation?.path.total_nodes)}</strong>
              </div>
              <div>
                <p className="psa-row-title">证据样本</p>
                <div className="psa-list">
                  {samples.slice(0, 3).map((sample) => (
                    <div className="psa-row" key={sample.id}>
                      <div>
                        <p className="psa-row-title">{sample.content}</p>
                        <div className="psa-row-meta">
                          <span>{sample.platform_name || '未知平台'}</span>
                          <span>{sample.sample_type || '样本'}</span>
                          <span>{formatDateTime(sample.created_at)}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                  {samples.length === 0 && <p className="psa-page-note">暂无样本</p>}
                </div>
              </div>
              <div>
                <p className="psa-row-title">关联话题</p>
                <div className="psa-list">
                  {relations.slice(0, 4).map((relation) => (
                    <div className="psa-row" key={relation.id}>
                      <div>
                        <p className="psa-row-title">{relation.target_title || `话题 #${relation.target_topic_id}`}</p>
                        <div className="psa-row-meta">
                          <span>{relation.relation_type || '关联'}</span>
                          <span>强度 {relation.score ?? 0}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                  {relations.length === 0 && <p className="psa-page-note">暂无关联话题</p>}
                </div>
              </div>
              <DataState
                empty={!topic?.raw_data || Object.keys(topic.raw_data).length === 0}
                emptyTitle="暂无原始扩展字段"
              >
                <pre className="psa-page-note">{JSON.stringify(topic?.raw_data, null, 2)}</pre>
              </DataState>
            </div>
          </DataState>
        </Panel>
      </div>
    </DataState>
  );
};

export default Topics;
