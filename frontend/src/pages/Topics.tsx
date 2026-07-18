import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Input, Pagination, Select } from 'antd';
import {
  BranchesOutlined,
  DownloadOutlined,
  FireOutlined,
  PartitionOutlined,
  ProfileOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import {
  getErrorMessage,
  exportTopicsCsv,
  getPlatforms,
  getPropagationPath,
  getPropagationPaths,
  getTopicCluster,
  getTopicClusters,
  getRelatedTopics,
  getTopicPropagation,
  getTopicSamples,
  getTopics,
  HotTopic,
  Pagination as PageInfo,
  Platform,
  analyzePropagation,
  PropagationPathDetail,
  PropagationPathSummary,
  runClustering,
  TopicClusterDetail,
  TopicClusterSummary,
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
  SentimentBadge,
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
  const [topicClusters, setTopicClusters] = useState<TopicClusterSummary[]>([]);
  const [clusterPagination, setClusterPagination] = useState<PageInfo | null>(null);
  const [selectedClusterId, setSelectedClusterId] = useState<number | null>(null);
  const [clusterDetail, setClusterDetail] = useState<TopicClusterDetail | null>(null);
  const [clusterAlgorithm, setClusterAlgorithm] = useState<'kmeans' | 'hdbscan' | 'dbscan'>('kmeans');
  const [clusterCount, setClusterCount] = useState(5);
  const [clusterWindow, setClusterWindow] = useState(24);
  const [propagationPaths, setPropagationPaths] = useState<PropagationPathSummary[]>([]);
  const [selectedPropagationId, setSelectedPropagationId] = useState<number | null>(null);
  const [propagationDetail, setPropagationDetail] = useState<PropagationPathDetail | null>(null);
  const [propagationWindow, setPropagationWindow] = useState(24);
  const [similarityThreshold, setSimilarityThreshold] = useState(0.18);
  const [keyword, setKeyword] = useState('');
  const [platform, setPlatform] = useState<string | undefined>();
  const [sortBy, setSortBy] = useState('heat_score');
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [clusterLoading, setClusterLoading] = useState(true);
  const [clusterRunning, setClusterRunning] = useState(false);
  const [propagationLoading, setPropagationLoading] = useState(true);
  const [propagationAnalyzing, setPropagationAnalyzing] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [clusterError, setClusterError] = useState<string | null>(null);
  const [propagationError, setPropagationError] = useState<string | null>(null);
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

  const fetchClusters = useCallback(async () => {
    try {
      setClusterLoading(true);
      const response = await getTopicClusters({ page: 1, page_size: 12 });
      const items = response.data?.items || [];
      setTopicClusters(items);
      setClusterPagination(response.data?.pagination || null);
      setSelectedClusterId((current) => {
        if (current && items.some((item) => item.id === current)) return current;
        return items[0]?.id ?? null;
      });
      setClusterError(null);
      setLastUpdated(new Date().toISOString());
    } catch (err) {
      setClusterError(getErrorMessage(err));
    } finally {
      setClusterLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchClusters();
  }, [fetchClusters]);

  useEffect(() => {
    if (!selectedClusterId) {
      setClusterDetail(null);
      return;
    }
    let mounted = true;
    getTopicCluster(selectedClusterId, { page: 1, page_size: 8 })
      .then((response) => {
        if (!mounted) return;
        setClusterDetail(response.data);
        setClusterError(null);
      })
      .catch((err) => {
        if (!mounted) return;
        setClusterError(getErrorMessage(err));
      });

    return () => {
      mounted = false;
    };
  }, [selectedClusterId]);

  const fetchPropagationPaths = useCallback(async () => {
    try {
      setPropagationLoading(true);
      const response = await getPropagationPaths({ page: 1, page_size: 10 });
      const items = response.data?.items || [];
      setPropagationPaths(items);
      setSelectedPropagationId((current) => {
        if (current && items.some((item) => item.id === current)) return current;
        return items[0]?.id ?? null;
      });
      setPropagationError(null);
      setLastUpdated(new Date().toISOString());
    } catch (err) {
      setPropagationError(getErrorMessage(err));
    } finally {
      setPropagationLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPropagationPaths();
  }, [fetchPropagationPaths]);

  useEffect(() => {
    if (!selectedPropagationId) {
      setPropagationDetail(null);
      return;
    }
    let mounted = true;
    getPropagationPath(selectedPropagationId)
      .then((response) => {
        if (!mounted) return;
        setPropagationDetail(response.data);
        setPropagationError(null);
      })
      .catch((err) => {
        if (!mounted) return;
        setPropagationError(getErrorMessage(err));
      });

    return () => {
      mounted = false;
    };
  }, [selectedPropagationId]);

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
    if (topicClusters.length === 0) return null;
    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 92, right: 18, top: 16, bottom: 28 },
      xAxis: { type: 'value', splitLine: { lineStyle: { color: '#E7EEF7' } } },
      yAxis: { type: 'category', data: topicClusters.map((item) => item.cluster_name), axisLabel: { color: '#64748B' } },
      series: [
        {
          type: 'bar',
          barWidth: 12,
          itemStyle: { color: '#2563EB', borderRadius: 999 },
          data: topicClusters.map((item) => item.topic_count),
        },
      ],
    };
  }, [topicClusters]);

  const spreadChart = useMemo(() => {
    if (!propagationDetail || propagationDetail.nodes.length === 0) return null;
    return {
      tooltip: {
        trigger: 'item',
        formatter: (params: { data?: { name?: string; value?: number; similarity?: number } }) => {
          if (params.data?.similarity !== undefined) {
            return `相似度 ${(params.data.similarity * 100).toFixed(1)}%`;
          }
          return params.data?.name || '';
        },
      },
      series: [
        {
          type: 'sankey',
          layout: 'none',
          nodeGap: 12,
          emphasis: { focus: 'adjacency' },
          data: propagationDetail.nodes.map((node) => ({
            name: `${node.id}`,
            label: { formatter: node.platform_name || node.topic_title || `#${node.topic_id}` },
            value: node.influence_score || 1,
          })),
          links: propagationDetail.edges.map((edge) => ({
            source: `${edge.source}`,
            target: `${edge.target}`,
            value: Math.max(1, Math.round((edge.similarity_score || 0.1) * 10)),
            similarity: edge.similarity_score || 0,
          })),
        },
      ],
    };
  }, [propagationDetail]);

  const resetFilters = () => {
    setKeyword('');
    setPlatform(undefined);
    setSortBy('heat_score');
    setPage(1);
  };

  const refreshAll = useCallback(() => {
    fetchData();
    fetchClusters();
    fetchPropagationPaths();
  }, [fetchClusters, fetchData, fetchPropagationPaths]);

  const handleRunClustering = useCallback(async () => {
    try {
      setClusterRunning(true);
      const response = await runClustering({
        algorithm: clusterAlgorithm,
        n_clusters: clusterCount,
        time_window_hours: clusterWindow,
      });
      if (response.code !== 200) {
        setClusterError(response.message);
        return;
      }
      await fetchClusters();
      setClusterError(null);
    } catch (err) {
      setClusterError(getErrorMessage(err));
    } finally {
      setClusterRunning(false);
    }
  }, [clusterAlgorithm, clusterCount, clusterWindow, fetchClusters]);

  const handleAnalyzePropagation = useCallback(async () => {
    if (!selectedTopic) return;
    try {
      setPropagationAnalyzing(true);
      const response = await analyzePropagation(selectedTopic.id, {
        time_window_hours: propagationWindow,
        similarity_threshold: similarityThreshold,
        max_nodes: 30,
      });
      setSelectedPropagationId(response.data.path_id);
      setPropagationDetail({
        path: response.data.path,
        tree: response.data.tree,
        nodes: response.data.nodes,
        edges: response.data.edges,
      });
      await fetchPropagationPaths();
      setPropagationError(null);
    } catch (err) {
      setPropagationError(getErrorMessage(err));
    } finally {
      setPropagationAnalyzing(false);
    }
  }, [fetchPropagationPaths, propagationWindow, selectedTopic, similarityThreshold]);

  const handleExport = useCallback(async () => {
    try {
      setExporting(true);
      await exportTopicsCsv({
        keyword: keyword.trim() || undefined,
        platform,
        sort_by: sortBy,
        sort_order: 'desc',
        limit: 5000,
      });
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setExporting(false);
    }
  }, [keyword, platform, sortBy]);

  const renderContent = () => {
    if (activeView === 'clusters') {
      const selectedCluster = clusterDetail?.cluster || topicClusters.find((item) => item.id === selectedClusterId) || null;
      const keywords = selectedCluster?.keywords || [];
      return (
        <>
          <div className="psa-filter-bar">
            <Select
              value={clusterAlgorithm}
              onChange={(value) => setClusterAlgorithm(value)}
              style={{ width: 150 }}
              options={[
                { value: 'kmeans', label: 'K-Means' },
                { value: 'hdbscan', label: 'HDBSCAN' },
                { value: 'dbscan', label: 'DBSCAN' },
              ]}
            />
            <Select
              value={clusterCount}
              onChange={setClusterCount}
              style={{ width: 130 }}
              options={[3, 5, 8, 12].map((value) => ({ value, label: `${value} 簇` }))}
            />
            <Select
              value={clusterWindow}
              onChange={setClusterWindow}
              style={{ width: 150 }}
              options={[
                { value: 24, label: '近 24 小时' },
                { value: 72, label: '近 3 天' },
                { value: 168, label: '近 7 天' },
              ]}
            />
            <Button
              type="primary"
              icon={<PartitionOutlined />}
              onClick={handleRunClustering}
              loading={clusterRunning}
            >
              运行聚类
            </Button>
            <Button icon={<ReloadOutlined />} onClick={fetchClusters} loading={clusterLoading}>
              刷新
            </Button>
          </div>
          <DataState loading={clusterLoading} error={clusterError} empty={topicClusters.length === 0} emptyTitle="暂无聚类结果">
            <div className="psa-grid two-one" style={{ marginTop: 16 }}>
              <Panel title="主题簇分布" eyebrow={selectedCluster?.embedding_provider || '未生成'}>
                <DataState empty={!clusterChart} emptyTitle="暂无聚类分布">
                  <ReactECharts option={clusterChart || {}} className="psa-chart large" />
                </DataState>
              </Panel>
              <Panel title="主题簇列表" eyebrow={clusterPagination ? `${clusterPagination.total} 个` : undefined}>
                <div className="psa-list">
                  {topicClusters.map((cluster) => (
                    <button
                      type="button"
                      className="psa-row"
                      key={cluster.id}
                      onClick={() => setSelectedClusterId(cluster.id)}
                    >
                      <div>
                        <p className="psa-row-title">{cluster.cluster_name}</p>
                        <div className="psa-row-meta">
                          <span>{cluster.topic_count} 个话题</span>
                          <span>{cluster.algorithm}</span>
                          <span>{cluster.embedding_provider || 'tfidf'}</span>
                        </div>
                      </div>
                      <SentimentBadge label={cluster.dominant_sentiment || 'neutral'} />
                    </button>
                  ))}
                </div>
              </Panel>
            </div>
            <div className="psa-grid two-one" style={{ marginTop: 16 }}>
              <Panel title="代表话题" className="tall" eyebrow={selectedCluster?.cluster_name}>
                <DataState empty={!clusterDetail || clusterDetail.members.length === 0} emptyTitle="暂无簇成员">
                  <div className="psa-list">
                    {(clusterDetail?.members || []).map((member) => (
                      <div className="psa-row" key={member.id}>
                        <div>
                          <p className="psa-row-title">{member.topic_title || `话题 #${member.topic_id}`}</p>
                          <div className="psa-row-meta">
                            <PlatformBadge name={member.platform_name} />
                            <span>权重 {(member.weight || 0).toFixed(3)}</span>
                            <span>距离 {(member.distance_to_center || 0).toFixed(3)}</span>
                          </div>
                        </div>
                        <strong>{formatNumber(member.heat_score)}</strong>
                      </div>
                    ))}
                  </div>
                </DataState>
              </Panel>
              <Panel title="关键词与情感">
                <div className="psa-detail-list">
                  <div className="psa-keyword-list">
                    {keywords.map((item) => (
                      <span className="psa-keyword-pill" key={item}>{item}</span>
                    ))}
                    {keywords.length === 0 && <span className="psa-page-note">暂无关键词</span>}
                  </div>
                  <div>
                    <p className="psa-row-title">代表话题（距质心最近）</p>
                    <div className="psa-list">
                      {(clusterDetail?.representative_members || []).map((member) => (
                        <div className="psa-row" key={`rep-${member.id}`}>
                          <div>
                            <p className="psa-row-title">{member.topic_title || `话题 #${member.topic_id}`}</p>
                            <div className="psa-row-meta">
                              <PlatformBadge name={member.platform_name} />
                              <span>距离 {(member.distance_to_center ?? 0).toFixed(3)}</span>
                            </div>
                          </div>
                          <strong>{formatNumber(member.heat_score)}</strong>
                        </div>
                      ))}
                      {(clusterDetail?.representative_members || []).length === 0 && (
                        <p className="psa-page-note">暂无代表话题</p>
                      )}
                    </div>
                  </div>
                  <div className="psa-detail-item">
                    <span>主导情感</span>
                    <SentimentBadge label={selectedCluster?.dominant_sentiment || 'neutral'} />
                  </div>
                  <div className="psa-detail-item">
                    <span>平均情感</span>
                    <strong>{((selectedCluster?.avg_sentiment ?? 0.5) * 100).toFixed(1)}%</strong>
                  </div>
                  <div className="psa-detail-item">
                    <span>时间窗口</span>
                    <strong>{selectedCluster?.start_time ? formatDateTime(selectedCluster.start_time) : '未生成'}</strong>
                  </div>
                  <div className="psa-detail-item">
                    <span>算法</span>
                    <strong>{selectedCluster?.algorithm || clusterAlgorithm}</strong>
                  </div>
                </div>
              </Panel>
            </div>
          </DataState>
        </>
      );
    }

    if (activeView === 'spread') {
      return (
        <>
          <div className="psa-filter-bar">
            <Select
              value={propagationWindow}
              onChange={setPropagationWindow}
              style={{ width: 150 }}
              options={[
                { value: 24, label: '近 24 小时' },
                { value: 72, label: '近 3 天' },
                { value: 168, label: '近 7 天' },
              ]}
            />
            <Select
              value={similarityThreshold}
              onChange={setSimilarityThreshold}
              style={{ width: 150 }}
              options={[
                { value: 0.12, label: '相似 12%' },
                { value: 0.18, label: '相似 18%' },
                { value: 0.28, label: '相似 28%' },
              ]}
            />
            <Button
              type="primary"
              icon={<BranchesOutlined />}
              onClick={handleAnalyzePropagation}
              loading={propagationAnalyzing}
              disabled={!selectedTopic}
            >
              分析当前话题
            </Button>
            <Button icon={<ReloadOutlined />} onClick={fetchPropagationPaths} loading={propagationLoading}>
              刷新
            </Button>
          </div>
          <DataState
            loading={propagationLoading}
            error={propagationError}
            empty={propagationPaths.length === 0}
            emptyTitle="暂无传播路径"
          >
            <div className="psa-grid two-one" style={{ marginTop: 16 }}>
              <Panel title="传播路径图" eyebrow={propagationDetail?.path.root_topic_title || selectedTopic?.title}>
                <DataState empty={!spreadChart} emptyTitle="暂无路径图">
                  <ReactECharts option={spreadChart || {}} className="psa-chart large" />
                </DataState>
              </Panel>
              <Panel title="路径列表" eyebrow={`${propagationPaths.length} 条`}>
                <div className="psa-list">
                  {propagationPaths.map((path) => (
                    <button
                      type="button"
                      className="psa-row"
                      key={path.id}
                      onClick={() => setSelectedPropagationId(path.id)}
                    >
                      <div>
                        <p className="psa-row-title">{path.root_topic_title || `话题 #${path.root_topic_id}`}</p>
                        <div className="psa-row-meta">
                          <span>{path.total_nodes} 节点</span>
                          <span>{path.platform_transitions} 次跨平台</span>
                          <span>{path.platforms_involved?.join(' / ') || '未知平台'}</span>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </Panel>
            </div>
            <div className="psa-grid two-one" style={{ marginTop: 16 }}>
              <Panel title="传播节点" className="tall" eyebrow={propagationDetail ? `${propagationDetail.path.depth} 层` : undefined}>
                <DataState empty={!propagationDetail || propagationDetail.nodes.length === 0} emptyTitle="暂无传播节点">
                  <div className="psa-list">
                    {(propagationDetail?.nodes || []).map((node) => (
                      <div className="psa-row" key={node.id}>
                        <div>
                          <p className="psa-row-title">{node.topic_title || `话题 #${node.topic_id}`}</p>
                          <div className="psa-row-meta">
                            <PlatformBadge name={node.platform_name} />
                            <span>L{node.level}</span>
                            <span>相似 {((node.similarity_score ?? 1) * 100).toFixed(1)}%</span>
                            <span>{formatDateTime(node.discovered_at)}</span>
                          </div>
                        </div>
                        <SentimentBadge label={node.sentiment_label || 'neutral'} />
                      </div>
                    ))}
                  </div>
                </DataState>
              </Panel>
              <Panel title="传播指标">
                <div className="psa-detail-list">
                  <div className="psa-detail-item">
                    <span>节点总数</span>
                    <strong>{propagationDetail?.path.total_nodes ?? 0}</strong>
                  </div>
                  <div className="psa-detail-item">
                    <span>传播深度</span>
                    <strong>{propagationDetail?.path.depth ?? 0}</strong>
                  </div>
                  <div className="psa-detail-item">
                    <span>最大广度</span>
                    <strong>{propagationDetail?.path.max_breadth ?? 0}</strong>
                  </div>
                  <div className="psa-detail-item">
                    <span>跨平台</span>
                    <strong>{propagationDetail?.path.platform_transitions ?? 0}</strong>
                  </div>
                  <div className="psa-detail-item">
                    <span>首次出现</span>
                    <strong>{formatDateTime(propagationDetail?.path.first_seen_at)}</strong>
                  </div>
                  <div className="psa-detail-item">
                    <span>最后出现</span>
                    <strong>{formatDateTime(propagationDetail?.path.last_seen_at)}</strong>
                  </div>
                </div>
              </Panel>
            </div>
          </DataState>
        </>
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
          onExport={handleExport}
          loading={loading}
          exporting={exporting}
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
      onRefresh={refreshAll}
      refreshing={loading || clusterLoading || clusterRunning || propagationLoading || propagationAnalyzing}
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
  exporting: boolean;
  onKeyword: (value: string) => void;
  onPlatform: (value?: string) => void;
  onSort: (value: string) => void;
  onReset: () => void;
  onRefresh: () => void;
  onExport: () => void;
}> = ({ keyword, platform, sortBy, platforms, loading, exporting, onKeyword, onPlatform, onSort, onReset, onRefresh, onExport }) => (
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
    <Button icon={<DownloadOutlined />} onClick={onExport} loading={exporting}>
      导出
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
