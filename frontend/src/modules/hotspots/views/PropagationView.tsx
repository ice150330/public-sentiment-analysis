import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, InputNumber, message, Pagination, Select, Tag } from 'antd';
import { BranchesOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import {
  analyzePropagation,
  getErrorMessage,
  getPropagationPath,
  getPropagationPaths,
  PropagationNode,
  PropagationPathDetail,
  PropagationPathSummary,
} from '@/services/api';
import {
  DataState,
  formatDateTime,
  formatNumber,
  Panel,
  PlatformBadge,
  SentimentBadge,
} from '@/components/DesignSystem';
import { HotspotsViewProps } from '../types';

interface FlatTreeNode {
  node: PropagationNode;
  level: number;
}

/** 深度优先展开传播树，保留父子顺序并记录缩进层级 */
const flattenTree = (nodes: PropagationNode[], level = 0): FlatTreeNode[] =>
  nodes.flatMap((node) => [
    { node, level },
    ...flattenTree(node.children || [], level + 1),
  ]);

interface TreeChartDatum {
  name: string;
  value?: number;
  platform?: string | null;
  sentiment?: string | null;
  level?: number;
  delay?: number | null;
  children?: TreeChartDatum[];
}

const toChartTree = (nodes: PropagationNode[]): TreeChartDatum[] =>
  nodes.map((node) => ({
    name: node.topic_title || node.platform_name || `话题 #${node.topic_id}`,
    value: node.heat_score ?? undefined,
    platform: node.platform_name,
    sentiment: node.sentiment_label,
    level: node.level,
    delay: node.delay_hours,
    children: node.children && node.children.length > 0 ? toChartTree(node.children) : undefined,
  }));

/** 传播路径 —— 话题分析操作区 + 路径列表 + ECharts 传播树 + 节点缩进列表 */
const PropagationView: React.FC<HotspotsViewProps> = ({ refreshKey, onSyncState }) => {
  const [paths, setPaths] = useState<PropagationPathSummary[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [pageSize, setPageSize] = useState(8);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<PropagationPathDetail | null>(null);
  const [topicIdInput, setTopicIdInput] = useState<number | null>(null);
  const [timeWindow, setTimeWindow] = useState(24);
  const [similarity, setSimilarity] = useState(0.18);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  const fetchPaths = useCallback(async () => {
    try {
      setLoading(true);
      onSyncState({ refreshing: true });
      const res = await getPropagationPaths({ page, page_size: 8 });
      const items = res.data?.items || [];
      setPaths(items);
      setTotal(res.data?.pagination?.total || 0);
      setPageSize(res.data?.pagination?.page_size || 8);
      setSelectedId((current) => {
        if (current && items.some((item) => item.id === current)) return current;
        return items[0]?.id ?? null;
      });
      setError(null);
      onSyncState({ refreshing: false, lastUpdated: new Date().toISOString() });
    } catch (err) {
      setError(getErrorMessage(err));
      onSyncState({ refreshing: false });
    } finally {
      setLoading(false);
    }
  }, [page, onSyncState]);

  useEffect(() => {
    fetchPaths();
  }, [fetchPaths, refreshKey]);

  /** 选中路径后加载传播详情（树 + 节点 + 边） */
  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    let mounted = true;
    setDetailLoading(true);
    getPropagationPath(selectedId)
      .then((res) => {
        if (!mounted) return;
        setDetail(res.data);
        setDetailError(null);
      })
      .catch((err) => {
        if (!mounted) return;
        setDetail(null);
        setDetailError(getErrorMessage(err));
      })
      .finally(() => {
        if (mounted) setDetailLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [selectedId]);

  const handleAnalyze = async () => {
    if (!topicIdInput) return;
    try {
      setAnalyzing(true);
      const res = await analyzePropagation(topicIdInput, {
        time_window_hours: timeWindow,
        similarity_threshold: similarity,
        max_nodes: 30,
      });
      if (res.code !== 200) {
        message.error(res.message || '传播分析失败');
        return;
      }
      setDetail({
        path: res.data.path,
        tree: res.data.tree,
        nodes: res.data.nodes,
        edges: res.data.edges,
      });
      message.success(`传播分析完成：${formatNumber(res.data.total_nodes)} 个节点`);
      setSelectedId(res.data.path_id);
      await fetchPaths();
    } catch (err) {
      message.error(getErrorMessage(err));
    } finally {
      setAnalyzing(false);
    }
  };

  const treeChart = useMemo(() => {
    if (!detail || !detail.tree || detail.tree.length === 0) return null;
    return {
      tooltip: {
        trigger: 'item',
        triggerOn: 'mousemove',
        formatter: (params: { data?: TreeChartDatum }) => {
          const data = params.data;
          if (!data) return '';
          const lines = [
            `<strong>${data.name}</strong>`,
            `平台：${data.platform || '未知'}`,
            `热度：${data.value ?? '暂无'}`,
            `层级：L${data.level ?? 0}`,
          ];
          if (data.delay !== null && data.delay !== undefined) {
            lines.push(`延迟：${data.delay}h`);
          }
          return lines.join('<br/>');
        },
      },
      series: [
        {
          type: 'tree',
          data: toChartTree(detail.tree),
          top: '4%',
          left: '16%',
          bottom: '4%',
          right: '28%',
          symbolSize: 10,
          itemStyle: { color: '#2563EB', borderColor: '#1E3A8A' },
          lineStyle: { color: '#B9CCE4', width: 1.5 },
          label: {
            position: 'left',
            verticalAlign: 'middle',
            align: 'right',
            fontSize: 11,
            fontWeight: 700,
            color: '#152033',
          },
          leaves: {
            label: {
              position: 'right',
              align: 'left',
            },
          },
          emphasis: { focus: 'descendant' },
          expandAndCollapse: false,
          animationDuration: 400,
        },
      ],
    };
  }, [detail]);

  const flatNodes = useMemo(() => {
    if (!detail) return [];
    if (detail.tree && detail.tree.length > 0) return flattenTree(detail.tree);
    return (detail.nodes || [])
      .slice()
      .sort((a, b) => a.level - b.level)
      .map((node) => ({ node, level: node.level }));
  }, [detail]);

  return (
    <>
      <div className="psa-filter-bar">
        <InputNumber
          min={1}
          precision={0}
          value={topicIdInput}
          onChange={(value) => setTopicIdInput(value)}
          placeholder="输入话题 ID"
          style={{ width: 140 }}
        />
        <Select
          value={timeWindow}
          onChange={setTimeWindow}
          style={{ width: 140 }}
          options={[
            { value: 24, label: '近 24 小时' },
            { value: 72, label: '近 3 天' },
            { value: 168, label: '近 7 天' },
          ]}
        />
        <Select
          value={similarity}
          onChange={setSimilarity}
          style={{ width: 140 }}
          options={[
            { value: 0.12, label: '相似度 12%' },
            { value: 0.18, label: '相似度 18%' },
            { value: 0.28, label: '相似度 28%' },
          ]}
        />
        <Button
          type="primary"
          icon={<BranchesOutlined />}
          onClick={handleAnalyze}
          loading={analyzing}
          disabled={!topicIdInput}
        >
          分析传播路径
        </Button>
      </div>

      <DataState loading={loading} error={error} empty={paths.length === 0} emptyTitle="暂无传播路径">
        <div className="psa-grid two-one" style={{ marginTop: 16 }}>
          <Panel
            title="传播树"
            eyebrow={detail?.path.root_topic_title || undefined}
            className="psa-panel-flush"
          >
            <DataState
              loading={detailLoading}
              error={detailError}
              empty={!treeChart}
              emptyTitle="选择路径后展示传播树"
              minHeight={240}
            >
              <ReactECharts option={treeChart || {}} className="psa-chart large" />
            </DataState>
          </Panel>
          <Panel title="路径列表" eyebrow={`共 ${formatNumber(total)} 条`}>
            <div className="psa-list">
              {paths.map((path) => (
                <button
                  type="button"
                  className="psa-row"
                  key={path.id}
                  onClick={() => setSelectedId(path.id)}
                >
                  <div>
                    <p className="psa-row-title">{path.root_topic_title || `话题 #${path.root_topic_id}`}</p>
                    <div className="psa-row-meta">
                      <span>深度 {path.depth}</span>
                      <span>{formatNumber(path.total_nodes)} 节点</span>
                      <span>跨平台 {path.platform_transitions} 次</span>
                    </div>
                    <div className="psa-row-meta">
                      {(path.platforms_involved || []).map((platform) => (
                        <Tag className="psa-platform neutral" key={platform}>{platform}</Tag>
                      ))}
                      {(path.platforms_involved || []).length === 0 && <span>未知平台</span>}
                    </div>
                  </div>
                </button>
              ))}
            </div>
            {total > pageSize && (
              <div className="hs-pagination">
                <Pagination
                  size="small"
                  current={page}
                  pageSize={pageSize}
                  total={total}
                  onChange={setPage}
                  showSizeChanger={false}
                />
              </div>
            )}
          </Panel>
        </div>

        <div className="psa-grid two-one" style={{ marginTop: 16 }}>
          <Panel
            title="传播节点"
            eyebrow={detail ? `深度 ${detail.path.depth} 层` : undefined}
          >
            <DataState
              loading={detailLoading}
              error={detailError}
              empty={flatNodes.length === 0}
              emptyTitle="暂无传播节点"
              minHeight={200}
            >
              <div className="hs-tree-list">
                {flatNodes.map(({ node, level }) => (
                  <div
                    className="hs-tree-node"
                    key={node.id}
                    style={{ marginLeft: Math.min(level, 6) * 20 }}
                  >
                    <div>
                      <p className="psa-row-title">{node.topic_title || `话题 #${node.topic_id}`}</p>
                      <div className="psa-row-meta">
                        <span className="hs-tree-level">L{level}</span>
                        <PlatformBadge name={node.platform_name} />
                        {node.delay_hours !== null && node.delay_hours !== undefined && (
                          <span>延迟 {node.delay_hours}h</span>
                        )}
                        {node.similarity_score !== null && node.similarity_score !== undefined && (
                          <span>相似 {(node.similarity_score * 100).toFixed(1)}%</span>
                        )}
                        <span>热度 {formatNumber(node.heat_score)}</span>
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
                <span>根话题</span>
                <strong>{detail?.path.root_topic_title || '未选择'}</strong>
              </div>
              <div className="psa-detail-item">
                <span>节点总数</span>
                <strong>{formatNumber(detail?.path.total_nodes)}</strong>
              </div>
              <div className="psa-detail-item">
                <span>传播深度</span>
                <strong>{formatNumber(detail?.path.depth)}</strong>
              </div>
              <div className="psa-detail-item">
                <span>最大广度</span>
                <strong>{formatNumber(detail?.path.max_breadth)}</strong>
              </div>
              <div className="psa-detail-item">
                <span>跨平台次数</span>
                <strong>{formatNumber(detail?.path.platform_transitions)}</strong>
              </div>
              <div className="psa-detail-item">
                <span>首次出现</span>
                <strong>{formatDateTime(detail?.path.first_seen_at)}</strong>
              </div>
              <div className="psa-detail-item">
                <span>最后出现</span>
                <strong>{formatDateTime(detail?.path.last_seen_at)}</strong>
              </div>
            </div>
          </Panel>
        </div>
      </DataState>
    </>
  );
};

export default PropagationView;
