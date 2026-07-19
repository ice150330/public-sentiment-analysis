import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Table, Tag } from 'antd';
import {
  ApiOutlined,
  CheckCircleOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import {
  CrawlStatus,
  getCrawlStatus,
  getDataFreshness,
  getErrorMessage,
  getPlatformMonitoringMatrix,
  PlatformMonitoringMatrix,
} from '@/services/api';
import {
  DataState,
  formatDateTime,
  formatNumber,
  MetricCard,
  Panel,
  PlatformBadge,
  SectionNotice,
} from '@/components/DesignSystem';
import { OverviewViewProps } from '../types';

type MatrixRow = PlatformMonitoringMatrix['matrix'][number];

interface FreshnessItem {
  platform_id?: number;
  platform_name?: string;
  display_name?: string;
  latest_topic_time?: string | null;
  delay_minutes?: number | null;
  gap_status?: string;
}

/** 矩阵状态：healthy 正常 / stale 延迟 / error 异常 / never 未采集 */
const STATUS_MAP: Record<string, { cls: string; text: string }> = {
  healthy: { cls: 'success', text: '正常' },
  stale: { cls: 'warning', text: '延迟' },
  error: { cls: 'danger', text: '异常' },
  never: { cls: 'muted', text: '未采集' },
};

const GAP_COLORS: Record<string, string> = {
  normal: 'var(--positive)',
  warning: 'var(--warning)',
  critical: 'var(--negative)',
  missing: 'var(--neutral)',
};

const GAP_LABELS: Record<string, string> = {
  normal: '整体正常',
  warning: '存在延迟',
  critical: '严重延迟',
};

const formatDelay = (minutes?: number | null) => {
  if (minutes === null || minutes === undefined) return '暂无数据';
  if (minutes < 60) return `${minutes} 分钟前`;
  if (minutes < 60 * 24) return `${Math.round(minutes / 60)} 小时前`;
  return `${Math.round(minutes / 60 / 24)} 天前`;
};

/** 数据新鲜度面板：优先按平台列表渲染延迟横条，退化为键值对，无法解析时给提示 */
const FreshnessPanel: React.FC<{ freshness: Record<string, unknown> | null }> = ({ freshness }) => {
  const items = useMemo(() => {
    const list = freshness?.freshness;
    return Array.isArray(list) ? (list as FreshnessItem[]) : null;
  }, [freshness]);

  const overallStatus = typeof freshness?.overall_status === 'string' ? freshness.overall_status : null;
  const maxDelay = useMemo(
    () => Math.max(1, ...(items || []).map((item) => item.delay_minutes || 0)),
    [items],
  );

  if (!freshness || typeof freshness !== 'object') {
    return <SectionNotice title="数据新鲜度不可用" description="后端暂未返回新鲜度数据。" />;
  }

  if (items) {
    return (
      <Panel
        title="数据新鲜度"
        eyebrow={overallStatus ? GAP_LABELS[overallStatus] || overallStatus : '各平台数据延迟'}
      >
        <DataState empty={items.length === 0} emptyTitle="暂无新鲜度数据">
          <div className="psa-score-bars">
            {items.map((item) => (
              <div className="psa-score-line" key={item.platform_id ?? item.platform_name}>
                <span>{item.display_name || item.platform_name || '未知平台'}</span>
                <div className="psa-bar-track">
                  <div
                    className="psa-bar-fill"
                    style={{
                      width: `${Math.max(4, Math.round(((item.delay_minutes || 0) / maxDelay) * 100))}%`,
                      background: GAP_COLORS[item.gap_status || 'normal'] || GAP_COLORS.normal,
                    }}
                  />
                </div>
                <strong>{formatDelay(item.delay_minutes)}</strong>
              </div>
            ))}
          </div>
        </DataState>
      </Panel>
    );
  }

  const entries = Object.entries(freshness).filter(([key]) => key !== 'overall_status');
  if (entries.length === 0) {
    return <SectionNotice title="数据新鲜度不可用" description="返回格式暂不支持展示。" />;
  }

  return (
    <Panel title="数据新鲜度" eyebrow="键值视图">
      <div className="psa-detail-list">
        {entries.map(([key, value]) => (
          <div className="psa-detail-item" key={key}>
            <span>{key}</span>
            <strong>
              {typeof value === 'number'
                ? formatNumber(value)
                : typeof value === 'string'
                  ? value
                  : JSON.stringify(value)}
            </strong>
          </div>
        ))}
      </div>
    </Panel>
  );
};

/** 平台监测 —— 指标卡 + 监测矩阵 + 数据新鲜度 */
const PlatformsView: React.FC<OverviewViewProps> = ({ refreshKey, onSyncState }) => {
  const [matrix, setMatrix] = useState<PlatformMonitoringMatrix | null>(null);
  const [freshness, setFreshness] = useState<Record<string, unknown> | null>(null);
  const [crawlStatus, setCrawlStatus] = useState<CrawlStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      onSyncState({ refreshing: true });
      const [matrixRes, freshnessRes, statusRes] = await Promise.all([
        getPlatformMonitoringMatrix(),
        getDataFreshness(),
        getCrawlStatus(),
      ]);
      setMatrix(matrixRes.data);
      setFreshness(freshnessRes.data);
      setCrawlStatus(statusRes.data);
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
    fetchData();
  }, [fetchData, refreshKey]);

  const running = crawlStatus?.is_running;
  const unhealthy = Math.max(0, (matrix?.total_platforms || 0) - (matrix?.healthy_count || 0));

  return (
    <DataState loading={loading} error={error} empty={!matrix} emptyTitle="平台监测数据不可用">
      <div className="ov-stack">
        <div className="ov-grid-3">
          <MetricCard
            label="接入平台"
            value={formatNumber(matrix?.total_platforms)}
            helper="已启用的采集平台"
            icon={<ApiOutlined />}
          />
          <MetricCard
            label="健康平台"
            value={formatNumber(matrix?.healthy_count)}
            helper={unhealthy > 0 ? `异常 ${formatNumber(unhealthy)} 个` : '全部平台运行正常'}
            icon={<CheckCircleOutlined />}
            tone={unhealthy > 0 ? 'warning' : 'positive'}
          />
          <MetricCard
            label="当前采集状态"
            value={running ? '采集中' : '空闲'}
            helper={`队列 ${formatNumber(crawlStatus?.queue_length ?? 0)} 个任务`}
            icon={<SyncOutlined spin={running} />}
            tone={running ? 'warning' : 'neutral'}
          />
        </div>

        <Panel title="平台监测矩阵" eyebrow="近 24 小时">
          <Table<MatrixRow>
            className="psa-table"
            size="middle"
            rowKey="platform_id"
            pagination={false}
            dataSource={matrix?.matrix || []}
            locale={{ emptyText: '暂无平台监测数据' }}
            columns={[
              {
                title: '平台',
                key: 'platform',
                render: (_, record) => (
                  <PlatformBadge name={record.display_name || record.platform_name} />
                ),
              },
              {
                title: '话题数',
                dataIndex: 'topic_count',
                align: 'right',
                render: (value) => formatNumber(value),
              },
              {
                title: '平均热度',
                dataIndex: 'avg_heat',
                align: 'right',
                render: (value) => formatNumber(Math.round(value || 0)),
              },
              {
                title: '负面占比',
                dataIndex: 'negative_ratio',
                align: 'right',
                render: (value) => `${Math.round(value || 0)}%`,
              },
              {
                title: '延迟',
                dataIndex: 'delay_minutes',
                align: 'right',
                render: (value) => formatDelay(value),
              },
              {
                title: '最近采集',
                dataIndex: 'last_crawl',
                render: (value) => formatDateTime(value),
              },
              {
                title: '状态',
                dataIndex: 'status',
                render: (value) => {
                  const meta = STATUS_MAP[value] || { cls: 'muted', text: value || '未知' };
                  return <Tag className={`psa-tag ${meta.cls}`}>{meta.text}</Tag>;
                },
              },
              {
                title: '健康',
                dataIndex: 'is_healthy',
                render: (value: boolean) => (
                  <span className="ov-health">
                    <span className={`ov-health-dot ${value ? 'ok' : 'bad'}`} />
                    {value ? '健康' : '异常'}
                  </span>
                ),
              },
            ]}
          />
        </Panel>

        <FreshnessPanel freshness={freshness} />
      </div>
    </DataState>
  );
};

export default PlatformsView;
