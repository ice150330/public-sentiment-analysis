import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, message, Segmented, Select, Tag } from 'antd';
import {
  AlertOutlined,
  BellOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import {
  acknowledgeAlert,
  AlertEvent,
  AlertSummary,
  exportAlertEventsCsv,
  getAlertEvents,
  getAlertSummary,
  getErrorMessage,
  ignoreAlert,
  resolveAlert,
} from '@/services/api';
import {
  DataState,
  formatDateTime,
  formatNumber,
  MetricCard,
  Panel,
} from '@/components/DesignSystem';
import SeverityTag, { severityColor } from '../components/SeverityTag';
import { OverviewViewProps } from '../types';

type StatusFilter = 'all' | 'pending' | 'acknowledged' | 'resolved' | 'ignored';
type SeverityFilter = 'all' | 'P1' | 'P2' | 'P3' | 'P4';

const STATUS_TAG: Record<string, { cls: string; text: string }> = {
  pending: { cls: 'danger', text: '待处理' },
  acknowledged: { cls: 'warning', text: '已确认' },
  resolved: { cls: 'success', text: '已解决' },
  ignored: { cls: 'muted', text: '已忽略' },
};

type AlertAction = 'ack' | 'resolve' | 'ignore';

const ACTION_TEXT: Record<AlertAction, string> = {
  ack: '已确认该预警',
  resolve: '已解决该预警',
  ignore: '已忽略该预警',
};

/** 预警中心 —— 指标卡 + 级别分布 + 可筛选事件队列 */
const AlertsView: React.FC<OverviewViewProps> = ({ refreshKey, onSyncState }) => {
  const [summary, setSummary] = useState<AlertSummary | null>(null);
  const [events, setEvents] = useState<AlertEvent[]>([]);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('pending');
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [acting, setActing] = useState<{ id: number; action: AlertAction } | null>(null);

  const fetchAlerts = useCallback(async () => {
    try {
      setLoading(true);
      onSyncState({ refreshing: true });
      const [summaryRes, eventsRes] = await Promise.all([
        getAlertSummary(),
        getAlertEvents({
          page: 1,
          page_size: 20,
          status: statusFilter === 'all' ? undefined : statusFilter,
          severity: severityFilter === 'all' ? undefined : severityFilter,
        }),
      ]);
      setSummary(summaryRes.data);
      setEvents(eventsRes.data?.items || []);
      setError(null);
      onSyncState({ refreshing: false, lastUpdated: new Date().toISOString() });
    } catch (err) {
      setError(getErrorMessage(err));
      onSyncState({ refreshing: false });
    } finally {
      setLoading(false);
    }
  }, [onSyncState, statusFilter, severityFilter]);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts, refreshKey]);

  const severityRows = useMemo(() => {
    const entries = Object.entries(summary?.severity_distribution || {});
    const total = Math.max(1, entries.reduce((sum, [, count]) => sum + count, 0));
    return entries
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([severity, count]) => ({
        severity,
        count,
        percent: Math.round((count / total) * 100),
      }));
  }, [summary]);

  const handleAction = useCallback(
    async (event: AlertEvent, action: AlertAction) => {
      try {
        setActing({ id: event.id, action });
        if (action === 'ack') await acknowledgeAlert(event.id);
        else if (action === 'resolve') await resolveAlert(event.id);
        else await ignoreAlert(event.id);
        message.success(ACTION_TEXT[action]);
        await fetchAlerts();
      } catch (err) {
        message.error(getErrorMessage(err));
      } finally {
        setActing(null);
      }
    },
    [fetchAlerts],
  );

  const handleExport = useCallback(async () => {
    try {
      setExporting(true);
      await exportAlertEventsCsv({ limit: 5000 });
      message.success('预警事件 CSV 已开始下载');
    } catch (err) {
      message.error(getErrorMessage(err));
    } finally {
      setExporting(false);
    }
  }, []);

  return (
    <DataState loading={loading} error={error} empty={!summary} emptyTitle="预警数据不可用">
      <div className="ov-stack">
        <div className="psa-grid metrics">
          <MetricCard
            label="待处理预警"
            value={formatNumber(summary?.pending_count)}
            helper="需要尽快处置"
            icon={<AlertOutlined />}
            tone="negative"
          />
          <MetricCard
            label="今日新增"
            value={formatNumber(summary?.today_count)}
            helper="今日触发的预警"
            icon={<BellOutlined />}
            tone="warning"
          />
          <MetricCard
            label="最高级别"
            value={summary?.max_severity || '暂无'}
            helper="当前待处理最高级别"
            icon={<CheckCircleOutlined />}
            tone={summary?.max_severity === 'P1' ? 'negative' : 'primary'}
          />
          <MetricCard
            label="最近预警时间"
            value={summary?.latest_alert ? formatDateTime(summary.latest_alert.triggered_at) : '暂无'}
            helper={summary?.latest_alert ? `事件 #${summary.latest_alert.id}` : '暂无预警记录'}
            icon={<ClockCircleOutlined />}
            tone="neutral"
          />
        </div>

        <div className="psa-grid two-one">
          <Panel
            title="预警事件"
            className="tall"
            eyebrow={`当前筛选 ${formatNumber(events.length)} 条`}
            extra={(
              <Button
                size="small"
                icon={<DownloadOutlined />}
                onClick={handleExport}
                loading={exporting}
              >
                导出 CSV
              </Button>
            )}
          >
            <div className="ov-filter-row">
              <Segmented<StatusFilter>
                value={statusFilter}
                onChange={setStatusFilter}
                options={[
                  { label: '待处理', value: 'pending' },
                  { label: '已确认', value: 'acknowledged' },
                  { label: '已解决', value: 'resolved' },
                  { label: '已忽略', value: 'ignored' },
                  { label: '全部', value: 'all' },
                ]}
              />
              <Select<SeverityFilter>
                value={severityFilter}
                onChange={setSeverityFilter}
                style={{ width: 120 }}
                options={[
                  { label: '全部级别', value: 'all' },
                  { label: 'P1', value: 'P1' },
                  { label: 'P2', value: 'P2' },
                  { label: 'P3', value: 'P3' },
                  { label: 'P4', value: 'P4' },
                ]}
              />
            </div>
            <DataState empty={events.length === 0} emptyTitle="暂无预警事件" emptyDescription="当前筛选条件下没有预警事件。">
              <div className="psa-list">
                {events.map((event) => {
                  const statusMeta = STATUS_TAG[event.status] || { cls: 'muted', text: event.status };
                  return (
                    <div className="psa-row ov-row-3" key={event.id}>
                      <SeverityTag severity={event.severity} />
                      <div>
                        <p className="psa-row-title">{event.topic_title || event.rule_name || `预警 #${event.id}`}</p>
                        <div className="psa-row-meta">
                          <span>{event.rule_name || `规则 ${event.rule_id}`}</span>
                          <span>{formatDateTime(event.triggered_at)}</span>
                        </div>
                      </div>
                      <div className="ov-alert-actions">
                        <Tag className={`psa-tag ${statusMeta.cls}`}>{statusMeta.text}</Tag>
                        {event.status === 'pending' && (
                          <>
                            <Button
                              size="small"
                              type="text"
                              loading={acting?.id === event.id && acting.action === 'ack'}
                              onClick={() => handleAction(event, 'ack')}
                            >
                              确认
                            </Button>
                            <Button
                              size="small"
                              type="text"
                              loading={acting?.id === event.id && acting.action === 'resolve'}
                              onClick={() => handleAction(event, 'resolve')}
                            >
                              解决
                            </Button>
                            <Button
                              size="small"
                              type="text"
                              danger
                              loading={acting?.id === event.id && acting.action === 'ignore'}
                              onClick={() => handleAction(event, 'ignore')}
                            >
                              忽略
                            </Button>
                          </>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </DataState>
          </Panel>

          <div className="ov-stack">
            <Panel title="级别分布" eyebrow={summary?.max_severity ? `最高 ${summary.max_severity}` : undefined}>
              <DataState empty={severityRows.length === 0} emptyTitle="暂无级别分布">
                <div className="psa-score-bars">
                  {severityRows.map((row) => (
                    <div className="psa-score-line" key={row.severity}>
                      <span>{row.severity}</span>
                      <div className="psa-bar-track">
                        <div
                          className="psa-bar-fill"
                          style={{ width: `${row.percent}%`, background: severityColor(row.severity) }}
                        />
                      </div>
                      <strong>{formatNumber(row.count)}</strong>
                    </div>
                  ))}
                </div>
              </DataState>
            </Panel>
            <Panel title="最近预警">
              <DataState empty={!summary?.latest_alert} emptyTitle="暂无最近预警">
                {summary?.latest_alert && (
                  <div className="psa-detail-list">
                    <div className="psa-detail-item">
                      <span>事件 ID</span>
                      <strong>#{summary.latest_alert.id}</strong>
                    </div>
                    <div className="psa-detail-item">
                      <span>级别</span>
                      <strong>{summary.latest_alert.severity}</strong>
                    </div>
                    <div className="psa-detail-item">
                      <span>触发时间</span>
                      <strong>{formatDateTime(summary.latest_alert.triggered_at)}</strong>
                    </div>
                  </div>
                )}
              </DataState>
            </Panel>
          </div>
        </div>
      </div>
    </DataState>
  );
};

export default AlertsView;
