import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button, Tag } from 'antd';
import { ArrowLeftOutlined, LinkOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import {
  forecastHeat,
  ForecastHeat,
  getErrorMessage,
  getRelatedTopics,
  getTopic,
  getTopicPropagation,
  getTopicSamples,
  HotTopic,
  TopicPropagation,
  TopicRelation,
  TopicSample,
} from '@/services/api';
import {
  DataState,
  formatDateTime,
  formatNumber,
  ModuleFrame,
  Panel,
  PlatformBadge,
  SectionNotice,
  SentimentBadge,
} from '@/components/DesignSystem';
import './hotspots.css';

/** 话题详情独立页 —— 概览头 + 内容样本 / 相关话题 / 传播路径 / 热度预测（挂 /topics/:id） */
const TopicDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const topicId = Number(id);
  const validId = Number.isInteger(topicId) && topicId > 0;

  const [topic, setTopic] = useState<HotTopic | null>(null);
  const [samples, setSamples] = useState<TopicSample[]>([]);
  const [relations, setRelations] = useState<TopicRelation[]>([]);
  const [propagation, setPropagation] = useState<TopicPropagation | null>(null);
  const [forecast, setForecast] = useState<ForecastHeat | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [partialError, setPartialError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const fetchDetail = useCallback(async () => {
    if (!validId) {
      setError('无效的话题 ID');
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setRefreshing(true);
      const topicRes = await getTopic(topicId);
      setTopic(topicRes.data);
      setError(null);

      /** 扩展数据允许部分失败：成功的照常渲染，失败的汇总提示 */
      const [sampleRes, relationRes, propagationRes, forecastRes] = await Promise.allSettled([
        getTopicSamples(topicId, { page: 1, page_size: 6 }),
        getRelatedTopics(topicId),
        getTopicPropagation(topicId),
        forecastHeat({ topic_id: topicId }),
      ]);

      setSamples(sampleRes.status === 'fulfilled' ? sampleRes.value.data?.items || [] : []);
      setRelations(relationRes.status === 'fulfilled' ? relationRes.value.data?.relations || [] : []);
      setPropagation(propagationRes.status === 'fulfilled' ? propagationRes.value.data : null);
      setForecast(forecastRes.status === 'fulfilled' ? forecastRes.value.data : null);

      const failed = [sampleRes, relationRes, propagationRes, forecastRes]
        .filter((item): item is PromiseRejectedResult => item.status === 'rejected');
      setPartialError(failed.length > 0 ? getErrorMessage(failed[0].reason) : null);
      setLastUpdated(new Date().toISOString());
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [topicId, validId]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail, refreshKey]);

  /** 热度预测：预测线 + 置信区间色带 + 当前热度标记线 */
  const forecastChart = useMemo(() => {
    if (!forecast || forecast.forecast.length === 0) return null;
    const points = forecast.forecast;
    const lower = points.map((point) => point.confidence_lower);
    const band = points.map((point) =>
      Math.max(0, point.confidence_upper - point.confidence_lower));
    return {
      tooltip: { trigger: 'axis' },
      grid: { left: 60, right: 20, top: 30, bottom: 30 },
      xAxis: {
        type: 'category',
        data: points.map((point) => point.date),
        axisLabel: { color: '#64748B' },
      },
      yAxis: {
        type: 'value',
        name: '热度',
        splitLine: { lineStyle: { color: '#E7EEF7' } },
      },
      series: [
        {
          name: '置信下界',
          type: 'line',
          stack: 'confidence',
          data: lower,
          symbol: 'none',
          silent: true,
          lineStyle: { opacity: 0 },
        },
        {
          name: '置信区间',
          type: 'line',
          stack: 'confidence',
          data: band,
          symbol: 'none',
          silent: true,
          lineStyle: { opacity: 0 },
          areaStyle: { color: 'rgba(37, 99, 235, 0.12)' },
        },
        {
          name: '预测热度',
          type: 'line',
          data: points.map((point) => point.predicted_heat),
          smooth: true,
          symbolSize: 6,
          itemStyle: { color: '#2563EB' },
          lineStyle: { width: 2.5 },
          markLine: {
            symbol: 'none',
            label: { formatter: '当前热度', color: '#E11D48' },
            lineStyle: { color: '#E11D48', type: 'dashed' },
            data: [{ yAxis: forecast.current_heat }],
          },
        },
      ],
    };
  }, [forecast]);

  const relationMax = useMemo(
    () => Math.max(1, ...relations.map((relation) => relation.score ?? 0)),
    [relations],
  );

  /** 传播节点按层级缩进展示（接口返回扁平节点） */
  const propagationNodes = useMemo(
    () => (propagation?.nodes || []).slice().sort((a, b) => a.level - b.level),
    [propagation],
  );

  return (
    <ModuleFrame
      moduleLabel="热点"
      activeView="detail"
      views={[]}
      onViewChange={() => undefined}
      onRefresh={() => setRefreshKey((key) => key + 1)}
      refreshing={refreshing}
      lastUpdated={lastUpdated}
    >
      <DataState loading={loading} error={error} empty={!topic} emptyTitle="话题不存在或已删除">
        {topic && (
          <div className="hs-side-stack">
            <Panel>
              <div className="hs-detail-hero">
                <div>
                  <h1 className="hs-detail-title">{topic.title}</h1>
                  <div className="psa-row-meta">
                    <PlatformBadge name={topic.platform_name} />
                    <Tag className="psa-tag muted">{topic.category || '未分类'}</Tag>
                    <span>采集于 {formatDateTime(topic.crawl_time)}</span>
                    {topic.url && (
                      <a className="hs-drawer-link" href={topic.url} target="_blank" rel="noreferrer">
                        <LinkOutlined /> 原文链接
                      </a>
                    )}
                  </div>
                  {topic.content_summary && (
                    <p className="psa-page-note" style={{ marginTop: 10 }}>{topic.content_summary}</p>
                  )}
                </div>
                <div className="hs-detail-heat">
                  <div className="value">{formatNumber(topic.heat_score)}</div>
                  <div className="label">当前热度</div>
                  <Button
                    icon={<ArrowLeftOutlined />}
                    style={{ marginTop: 12 }}
                    onClick={() => navigate('/topics')}
                  >
                    返回热榜
                  </Button>
                </div>
              </div>
            </Panel>

            {partialError && (
              <SectionNotice
                title="部分扩展数据加载失败"
                description={`${partialError}，其余内容不受影响。`}
              />
            )}

            <div className="psa-grid two">
              <Panel title="内容样本" eyebrow={samples.length > 0 ? `${samples.length} 条` : undefined}>
                <DataState empty={samples.length === 0} emptyTitle="暂无内容样本" minHeight={160}>
                  <div className="psa-list">
                    {samples.map((sample) => (
                      <div className="psa-row" key={sample.id}>
                        <div>
                          <p className="psa-row-title" style={{ fontWeight: 600 }}>{sample.content}</p>
                          <div className="psa-row-meta">
                            <PlatformBadge name={sample.platform_name} />
                            {sample.author && <span>作者 {sample.author}</span>}
                            <span>{formatDateTime(sample.created_at)}</span>
                            {sample.source_url && (
                              <a className="hs-drawer-link" href={sample.source_url} target="_blank" rel="noreferrer">
                                <LinkOutlined /> 来源
                              </a>
                            )}
                          </div>
                        </div>
                        <SentimentBadge
                          label={sample.sentiment_label || 'neutral'}
                          confidence={sample.confidence ?? undefined}
                        />
                      </div>
                    ))}
                  </div>
                </DataState>
              </Panel>

              <Panel title="相关话题" eyebrow={relations.length > 0 ? `${relations.length} 条` : undefined}>
                <DataState empty={relations.length === 0} emptyTitle="暂无相关话题" minHeight={160}>
                  <div className="psa-score-bars">
                    {relations.map((relation) => (
                      <div className="psa-score-line" key={relation.id}>
                        <span title={relation.target_title || `话题 #${relation.target_topic_id}`}>
                          {relation.target_title || `话题 #${relation.target_topic_id}`}
                        </span>
                        <div className="psa-bar-track">
                          <div
                            className="psa-bar-fill"
                            style={{ width: `${Math.max(4, Math.round(((relation.score ?? 0) / relationMax) * 100))}%` }}
                          />
                        </div>
                        <strong>{relation.relation_type || '关联'}</strong>
                      </div>
                    ))}
                  </div>
                </DataState>
              </Panel>
            </div>

            <div className="psa-grid two">
              <Panel
                title="传播路径"
                eyebrow={propagation ? `深度 ${propagation.path.depth} · ${formatNumber(propagation.path.total_nodes)} 节点` : undefined}
              >
                <DataState empty={!propagation || propagationNodes.length === 0} emptyTitle="暂无传播数据" minHeight={160}>
                  <div className="hs-tree-list">
                    {propagationNodes.map((node) => (
                      <div
                        className="hs-tree-node"
                        key={node.id}
                        style={{ marginLeft: Math.min(node.level, 6) * 20 }}
                      >
                        <div>
                          <p className="psa-row-title">{node.topic_title || `话题 #${node.topic_id}`}</p>
                          <div className="psa-row-meta">
                            <span className="hs-tree-level">L{node.level}</span>
                            <PlatformBadge name={node.platform_name} />
                            <span>热度 {formatNumber(node.heat_score)}</span>
                            {node.delay_hours !== null && node.delay_hours !== undefined && (
                              <span>延迟 {node.delay_hours}h</span>
                            )}
                          </div>
                        </div>
                        <SentimentBadge label={node.sentiment_label || 'neutral'} />
                      </div>
                    ))}
                  </div>
                </DataState>
              </Panel>

              <Panel
                title="热度预测"
                eyebrow={forecast ? `模型 ${forecast.model}` : undefined}
                className="psa-panel-flush"
              >
                <DataState empty={!forecastChart} emptyTitle="暂无热度预测" minHeight={160}>
                  <ReactECharts option={forecastChart || {}} className="psa-chart psa-chart-wide" />
                </DataState>
              </Panel>
            </div>
          </div>
        )}
      </DataState>
    </ModuleFrame>
  );
};

export default TopicDetailPage;
