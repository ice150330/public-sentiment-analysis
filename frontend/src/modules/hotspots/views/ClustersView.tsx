import React, { useCallback, useEffect, useState } from 'react';
import { Button, Drawer, message, Pagination, Select, Tag } from 'antd';
import { PartitionOutlined } from '@ant-design/icons';
import {
  getErrorMessage,
  getTopicCluster,
  getTopicClusters,
  runClustering,
  TopicClusterDetail,
  TopicClusterSummary,
} from '@/services/api';
import {
  DataState,
  formatDateTime,
  formatNumber,
  PlatformBadge,
  SentimentBadge,
} from '@/components/DesignSystem';
import { HotspotsViewProps } from '../types';

const MEMBER_PAGE_SIZE = 8;

/** 聚类主题 —— 运行参数操作条 + 聚类卡片网格 + 成员列表 Drawer */
const ClustersView: React.FC<HotspotsViewProps> = ({ refreshKey, onSyncState }) => {
  const [clusters, setClusters] = useState<TopicClusterSummary[]>([]);
  const [algorithm, setAlgorithm] = useState<'kmeans' | 'hdbscan' | 'dbscan'>('kmeans');
  const [clusterCount, setClusterCount] = useState(5);
  const [timeWindow, setTimeWindow] = useState(24);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeCluster, setActiveCluster] = useState<TopicClusterSummary | null>(null);
  const [detail, setDetail] = useState<TopicClusterDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [memberPage, setMemberPage] = useState(1);

  const fetchClusters = useCallback(async () => {
    try {
      setLoading(true);
      onSyncState({ refreshing: true });
      const res = await getTopicClusters({ page: 1, page_size: 12 });
      setClusters(res.data?.items || []);
      setError(null);
      onSyncState({ refreshing: false, lastUpdated: new Date().toISOString() });
    } catch (err) {
      setError(getErrorMessage(err));
      onSyncState({ refreshing: false });
    } finally {
      setLoading(false);
    }
  }, [onSyncState]);

  useEffect(() => {
    fetchClusters();
  }, [fetchClusters, refreshKey]);

  /** 打开 Drawer 或翻页时加载簇成员 */
  useEffect(() => {
    if (!activeCluster) {
      setDetail(null);
      return;
    }
    let mounted = true;
    setDetailLoading(true);
    getTopicCluster(activeCluster.id, { page: memberPage, page_size: MEMBER_PAGE_SIZE })
      .then((res) => {
        if (!mounted) return;
        setDetail(res.data);
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
  }, [activeCluster, memberPage]);

  const handleRunClustering = async () => {
    try {
      setRunning(true);
      const res = await runClustering({
        algorithm,
        n_clusters: clusterCount,
        time_window_hours: timeWindow,
      });
      if (res.code !== 200) {
        message.error(res.message || '聚类运行失败');
        return;
      }
      message.success(`聚类完成：生成 ${res.data?.clusters?.length ?? 0} 个主题簇`);
      await fetchClusters();
    } catch (err) {
      message.error(getErrorMessage(err));
    } finally {
      setRunning(false);
    }
  };

  const openCluster = (cluster: TopicClusterSummary) => {
    setActiveCluster(cluster);
    setMemberPage(1);
  };

  return (
    <>
      <div className="psa-filter-bar">
        <Select
          value={algorithm}
          onChange={setAlgorithm}
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
          value={timeWindow}
          onChange={setTimeWindow}
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
          loading={running}
        >
          运行聚类
        </Button>
      </div>

      <div style={{ marginTop: 16 }}>
        <DataState loading={loading} error={error} empty={clusters.length === 0} emptyTitle="暂无聚类结果">
          <div className="hs-cluster-grid">
            {clusters.map((cluster) => (
              <button
                type="button"
                className="hs-cluster-card"
                key={cluster.id}
                onClick={() => openCluster(cluster)}
              >
                <div className="hs-cluster-card-head">
                  <p className="hs-cluster-name">{cluster.cluster_name}</p>
                  <SentimentBadge label={cluster.dominant_sentiment || 'neutral'} />
                </div>
                <div>
                  <span className="hs-cluster-count">{formatNumber(cluster.topic_count)}</span>
                  <span className="psa-page-note"> 个话题</span>
                </div>
                <div className="psa-keyword-list">
                  {(cluster.keywords || []).slice(0, 6).map((keyword) => (
                    <span className="psa-keyword-pill" key={keyword}>{keyword}</span>
                  ))}
                  {(cluster.keywords || []).length === 0 && <span className="psa-page-note">暂无关键词</span>}
                </div>
                <div className="hs-cluster-meta">
                  <Tag className="psa-tag muted">{cluster.algorithm}</Tag>
                  <span>{formatDateTime(cluster.start_time)} ~ {formatDateTime(cluster.end_time)}</span>
                </div>
              </button>
            ))}
          </div>
        </DataState>
      </div>

      <Drawer
        title={activeCluster?.cluster_name || '簇成员'}
        width={520}
        open={activeCluster !== null}
        onClose={() => setActiveCluster(null)}
      >
        {activeCluster && (
          <div className="psa-detail-list">
            <div className="psa-row-meta">
              <Tag className="psa-tag muted">{activeCluster.algorithm}</Tag>
              <SentimentBadge label={activeCluster.dominant_sentiment || 'neutral'} />
              <span>{formatNumber(activeCluster.topic_count)} 个话题</span>
            </div>
            {activeCluster.description && (
              <p className="psa-page-note">{activeCluster.description}</p>
            )}
            <DataState
              loading={detailLoading}
              error={detailError}
              empty={!detail || detail.members.length === 0}
              emptyTitle="暂无簇成员"
              minHeight={160}
            >
              <div className="psa-list">
                {(detail?.members || []).map((member) => (
                  <div className="psa-row" key={member.id}>
                    <div>
                      <p className="psa-row-title">{member.topic_title || `话题 #${member.topic_id}`}</p>
                      <div className="psa-row-meta">
                        <PlatformBadge name={member.platform_name} />
                        <span>权重 {(member.weight ?? 0).toFixed(3)}</span>
                        <span>{formatDateTime(member.crawl_time)}</span>
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <strong>{formatNumber(member.heat_score)}</strong>
                      <div className="psa-row-meta" style={{ justifyContent: 'flex-end' }}>
                        <SentimentBadge label={member.sentiment_label || 'neutral'} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              {detail && detail.pagination.total > MEMBER_PAGE_SIZE && (
                <div className="hs-pagination">
                  <Pagination
                    size="small"
                    current={detail.pagination.page}
                    pageSize={detail.pagination.page_size}
                    total={detail.pagination.total}
                    onChange={setMemberPage}
                    showSizeChanger={false}
                  />
                </div>
              )}
            </DataState>
          </div>
        )}
      </Drawer>
    </>
  );
};

export default ClustersView;
