import React, { useCallback, useEffect, useState } from 'react';
import {
  Button,
  InputNumber,
  message,
  Popconfirm,
  Segmented,
  Slider,
  Table,
  Tooltip,
} from 'antd';
import {
  CheckCircleOutlined,
  ExperimentOutlined,
  StopOutlined,
} from '@ant-design/icons';
import {
  activateModelVersion,
  getErrorMessage,
  getModelStatus,
  getModelVersions,
  getSentimentReviewQueue,
  ModelStatus,
  ModelVersion,
  SentimentReviewItem,
  updateSentimentReviewItem,
} from '@/services/api';
import {
  DataState,
  formatDateTime,
  formatNumber,
  MetricCard,
  Panel,
  PlatformBadge,
  SentimentBadge,
  sentimentText,
  StatusBadge,
} from '@/components/DesignSystem';
import { AdminViewProps } from '../types';

type ReviewStatusFilter = 'pending' | 'reviewed' | 'ignored' | 'all';

const REVIEW_STATUS_TAG: Record<string, { cls: string; text: string }> = {
  pending: { cls: 'warning', text: '待复核' },
  reviewed: { cls: 'success', text: '已复核' },
  ignored: { cls: 'muted', text: '已忽略' },
};

/** 模型管理 —— 运行状态 + 指标卡 + 版本表（流量/激活） + 低置信复核队列 */
const ModelView: React.FC<AdminViewProps> = ({ refreshKey, onSyncState }) => {
  const [status, setStatus] = useState<ModelStatus | null>(null);
  const [versions, setVersions] = useState<ModelVersion[]>([]);
  const [trafficDraft, setTrafficDraft] = useState<Record<number, number>>({});
  const [activatingId, setActivatingId] = useState<number | null>(null);
  const [threshold, setThreshold] = useState(0.6);
  const [thresholdDraft, setThresholdDraft] = useState(0.6);
  const [reviewStatus, setReviewStatus] = useState<ReviewStatusFilter>('pending');
  const [reviewItems, setReviewItems] = useState<SentimentReviewItem[]>([]);
  const [reviewTotal, setReviewTotal] = useState(0);
  const [reviewPage, setReviewPage] = useState(1);
  const [reviewLoading, setReviewLoading] = useState(true);
  const [reviewingId, setReviewingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchBase = useCallback(async () => {
    try {
      setLoading(true);
      onSyncState({ refreshing: true });
      const [statusRes, versionsRes] = await Promise.all([getModelStatus(), getModelVersions()]);
      setStatus(statusRes.data || null);
      setVersions(versionsRes.data?.items || []);
      setError(null);
      onSyncState({ refreshing: false, lastUpdated: new Date().toISOString() });
    } catch (err) {
      setError(getErrorMessage(err));
      onSyncState({ refreshing: false });
    } finally {
      setLoading(false);
    }
  }, [onSyncState]);

  const fetchReviewQueue = useCallback(async () => {
    try {
      setReviewLoading(true);
      const res = await getSentimentReviewQueue({
        threshold,
        status: reviewStatus === 'all' ? undefined : reviewStatus,
        page: reviewPage,
        page_size: 10,
      });
      setReviewItems(res.data?.items || []);
      setReviewTotal(res.data?.pagination.total || 0);
    } catch (err) {
      message.error(getErrorMessage(err));
    } finally {
      setReviewLoading(false);
    }
  }, [threshold, reviewStatus, reviewPage]);

  useEffect(() => {
    fetchBase();
  }, [fetchBase, refreshKey]);

  useEffect(() => {
    fetchReviewQueue();
  }, [fetchReviewQueue, refreshKey]);

  const handleActivate = useCallback(
    async (record: ModelVersion) => {
      const trafficPercent = trafficDraft[record.id] ?? record.traffic_percent ?? 100;
      try {
        setActivatingId(record.id);
        await activateModelVersion(record.id, { traffic_percent: trafficPercent });
        message.success(`已激活版本 ${record.version}（流量 ${trafficPercent}%）`);
        await fetchBase();
      } catch (err) {
        message.error(getErrorMessage(err));
      } finally {
        setActivatingId(null);
      }
    },
    [trafficDraft, fetchBase],
  );

  const handleReview = useCallback(
    async (item: SentimentReviewItem, action: 'reviewed' | 'ignored') => {
      try {
        setReviewingId(item.id);
        await updateSentimentReviewItem(item.id, {
          status: action,
          corrected_label: action === 'reviewed' ? item.suggested_label : undefined,
        });
        message.success(action === 'reviewed' ? '已确认为建议标签' : '已标记忽略');
        await Promise.all([fetchReviewQueue(), fetchBase()]);
      } catch (err) {
        message.error(getErrorMessage(err));
      } finally {
        setReviewingId(null);
      }
    },
    [fetchReviewQueue, fetchBase],
  );

  const model = status?.model;

  return (
    <DataState loading={loading} error={error} empty={!status} emptyTitle="模型状态不可用">
      <div className="ad-stack">
        <div className="ad-grid-3">
          <MetricCard
            label="近期分析量"
            value={formatNumber(status?.recent_analyzed)}
            helper="近 24 小时完成的情绪分析"
            icon={<ExperimentOutlined />}
          />
          <MetricCard
            label="平均置信度"
            value={status ? `${((status.avg_confidence || 0) * 100).toFixed(1)}%` : '暂无'}
            helper="近期分析结果的平均置信度"
            tone={(status?.avg_confidence || 0) >= 0.8 ? 'positive' : 'warning'}
          />
          <MetricCard
            label="待复核样本"
            value={formatNumber(status?.pending_review)}
            helper="低置信结果等待人工复核"
            tone={(status?.pending_review || 0) > 0 ? 'negative' : 'positive'}
          />
        </div>

        <div className="psa-grid two-one">
          <Panel title="模型版本" eyebrow={`共 ${formatNumber(versions.length)} 个版本`}>
            <Table<ModelVersion>
              className="psa-table"
              size="middle"
              rowKey="id"
              pagination={false}
              dataSource={versions}
              locale={{ emptyText: '暂无模型版本' }}
              columns={[
                { title: '版本', dataIndex: 'version', ellipsis: true },
                { title: '模型', dataIndex: 'model_name', ellipsis: true },
                {
                  title: '任务类型',
                  dataIndex: 'task_type',
                  width: 110,
                  render: (value) => value || 'sentiment',
                },
                {
                  title: 'Provider',
                  dataIndex: 'provider',
                  width: 100,
                  render: (value) => value || 'classic',
                },
                {
                  title: '流量 %',
                  key: 'traffic_percent',
                  width: 100,
                  render: (_, record) => (
                    <InputNumber
                      size="small"
                      min={0}
                      max={100}
                      value={trafficDraft[record.id] ?? record.traffic_percent ?? 0}
                      disabled={activatingId === record.id}
                      onChange={(next) =>
                        setTrafficDraft((current) => ({ ...current, [record.id]: next ?? 0 }))
                      }
                    />
                  ),
                },
                {
                  title: '状态',
                  dataIndex: 'is_active',
                  width: 90,
                  render: (value: boolean) => <StatusBadge status={value} />,
                },
                {
                  title: '操作',
                  key: 'actions',
                  width: 100,
                  render: (_, record) => {
                    const isPrimary = record.is_active && (record.traffic_percent ?? 0) >= 100;
                    return (
                      <Popconfirm
                        title="激活模型版本"
                        description={`确定将 ${record.version} 的流量设为 ${trafficDraft[record.id] ?? record.traffic_percent ?? 100}% 吗？`}
                        okText="激活"
                        cancelText="取消"
                        onConfirm={() => handleActivate(record)}
                        disabled={isPrimary}
                      >
                        <Button
                          size="small"
                          type={isPrimary ? 'primary' : 'default'}
                          loading={activatingId === record.id}
                          disabled={isPrimary}
                        >
                          {isPrimary ? '主用中' : '激活'}
                        </Button>
                      </Popconfirm>
                    );
                  },
                },
                {
                  title: '创建时间',
                  dataIndex: 'created_at',
                  width: 130,
                  render: (value) => formatDateTime(value),
                },
              ]}
            />
          </Panel>

          <Panel
            title="当前模型状态"
            extra={<StatusBadge status={status?.status || 'unknown'} />}
          >
            <div className="psa-detail-list">
              <div className="psa-detail-item">
                <span>模型名称</span>
                <strong>{model?.model_name || '未加载'}</strong>
              </div>
              <div className="psa-detail-item">
                <span>当前版本</span>
                <strong>{model?.version || '未加载'}</strong>
              </div>
              <div className="psa-detail-item">
                <span>运行设备</span>
                <strong>{model?.device || '未知'}</strong>
              </div>
              <div className="psa-detail-item">
                <span>加载状态</span>
                <strong>{model?.is_loaded ? '已加载' : '未加载'}</strong>
              </div>
              <div className="psa-detail-item">
                <span>Provider</span>
                <strong>{model?.provider || 'classic'}</strong>
              </div>
              <div className="psa-detail-item">
                <span>流量比例</span>
                <strong>{model?.traffic_percent ?? 0}%</strong>
              </div>
            </div>
            <p className="psa-page-note">
              置信度分布：高 {formatNumber(status?.confidence_distribution?.high)} / 中 {formatNumber(status?.confidence_distribution?.medium)} / 低 {formatNumber(status?.confidence_distribution?.low)}
            </p>
          </Panel>
        </div>

        <Panel
          title="低置信复核队列"
          eyebrow={`阈值 ${(threshold * 100).toFixed(0)}% 以下 · 共 ${formatNumber(reviewTotal)} 条`}
        >
          <div className="psa-filter-bar" style={{ marginBottom: 12 }}>
            <span className="psa-inline-tools" style={{ flex: 1, minWidth: 220 }}>
              <span className="psa-page-note" style={{ margin: 0 }}>置信度阈值</span>
              <Slider
                style={{ flex: 1 }}
                min={0.5}
                max={0.9}
                step={0.05}
                value={thresholdDraft}
                tooltip={{ formatter: (value) => `${((value || 0) * 100).toFixed(0)}%` }}
                onChange={(value) => setThresholdDraft(value as number)}
                onChangeComplete={(value) => {
                  setThreshold(value as number);
                  setReviewPage(1);
                }}
              />
            </span>
            <Segmented<ReviewStatusFilter>
              value={reviewStatus}
              onChange={(value) => {
                setReviewStatus(value);
                setReviewPage(1);
              }}
              options={[
                { label: '待复核', value: 'pending' },
                { label: '已复核', value: 'reviewed' },
                { label: '已忽略', value: 'ignored' },
                { label: '全部', value: 'all' },
              ]}
            />
          </div>

          <DataState
            loading={reviewLoading}
            empty={reviewItems.length === 0}
            emptyTitle="暂无复核样本"
            emptyDescription="当前阈值与状态下没有需要复核的低置信结果。"
          >
            <div className="psa-list">
              {reviewItems.map((item) => {
                const statusMeta = REVIEW_STATUS_TAG[item.status] || { cls: 'muted', text: item.status };
                const percent = Math.round((item.confidence || 0) * 100);
                return (
                  <div className="psa-row" key={item.id}>
                    <div>
                      <p className="psa-row-title">
                        <Tooltip title={item.topic_title || undefined}>
                          {item.topic_title || '未命名话题'}
                        </Tooltip>
                      </p>
                      <div className="psa-row-meta">
                        <PlatformBadge name={item.platform_name} />
                        <span>
                          原标签 {sentimentText(item.original_label)} → 建议 {sentimentText(item.suggested_label)}
                        </span>
                        {item.status !== 'pending' && (
                          <span>
                            {statusMeta.text}
                            {item.corrected_label ? ` · 修正为${sentimentText(item.corrected_label)}` : ''}
                            {item.reviewer ? ` · ${item.reviewer}` : ''}
                            {item.reviewed_at ? ` · ${formatDateTime(item.reviewed_at)}` : ''}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="psa-row-action">
                      <div className="ad-confidence">
                        <div className="psa-bar-track">
                          <div
                            className="psa-bar-fill"
                            style={{
                              width: `${Math.max(4, percent)}%`,
                              background: percent < 60 ? 'var(--negative)' : 'var(--warning)',
                            }}
                          />
                        </div>
                        <strong>{percent}%</strong>
                      </div>
                      {item.status === 'pending' ? (
                        <div className="psa-inline-tools">
                          <SentimentBadge label={item.suggested_label} />
                          <Button
                            size="small"
                            icon={<CheckCircleOutlined />}
                            loading={reviewingId === item.id}
                            onClick={() => handleReview(item, 'reviewed')}
                          >
                            确认建议
                          </Button>
                          <Button
                            size="small"
                            icon={<StopOutlined />}
                            loading={reviewingId === item.id}
                            onClick={() => handleReview(item, 'ignored')}
                          >
                            忽略
                          </Button>
                        </div>
                      ) : (
                        <SentimentBadge label={item.corrected_label || item.suggested_label} />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
            {reviewTotal > 10 && (
              <div className="psa-actions" style={{ marginTop: 12, justifyContent: 'flex-end' }}>
                <Button size="small" disabled={reviewPage <= 1} onClick={() => setReviewPage((page) => page - 1)}>
                  上一页
                </Button>
                <span className="psa-page-note" style={{ margin: 0 }}>
                  第 {reviewPage} 页 / 共 {formatNumber(reviewTotal)} 条
                </span>
                <Button
                  size="small"
                  disabled={reviewPage * 10 >= reviewTotal}
                  onClick={() => setReviewPage((page) => page + 1)}
                >
                  下一页
                </Button>
              </div>
            )}
          </DataState>
        </Panel>
      </div>
    </DataState>
  );
};

export default ModelView;
