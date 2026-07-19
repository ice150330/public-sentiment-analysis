import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Button,
  Checkbox,
  InputNumber,
  message,
  Select,
  Switch,
  Table,
  Tooltip,
} from 'antd';
import {
  ClockCircleOutlined,
  PlayCircleOutlined,
  ScheduleOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import {
  CrawlLog,
  CrawlStatus,
  CrawlerScheduleConfig,
  getCrawlLogs,
  getCrawlStatus,
  getCrawlerSchedule,
  getErrorMessage,
  getPlatforms,
  Platform,
  triggerCrawler,
  updateCrawlerSchedule,
} from '@/services/api';
import {
  DataState,
  formatDateTime,
  formatNumber,
  Panel,
  PlatformBadge,
  StatusBadge,
} from '@/components/DesignSystem';
import { AdminViewProps } from '../types';

const LOG_STATUS_OPTIONS = [
  { value: 'success', label: '成功' },
  { value: 'failed', label: '失败' },
  { value: 'partial', label: '部分成功' },
  { value: 'running', label: '运行中' },
];

/** 采集任务 —— 触发面板 + 实时状态秒表 + 调度配置 + 日志表（10s 轮询） */
const CrawlerView: React.FC<AdminViewProps> = ({ refreshKey, onSyncState }) => {
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [isAsync, setIsAsync] = useState(true);
  const [status, setStatus] = useState<CrawlStatus | null>(null);
  const [schedule, setSchedule] = useState<CrawlerScheduleConfig | null>(null);
  const [logs, setLogs] = useState<CrawlLog[]>([]);
  const [logsTotal, setLogsTotal] = useState(0);
  const [logsPage, setLogsPage] = useState(1);
  const [logPlatform, setLogPlatform] = useState<string>();
  const [logStatus, setLogStatus] = useState<string>();
  const [loading, setLoading] = useState(true);
  const [logsLoading, setLogsLoading] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [savingSchedule, setSavingSchedule] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = useCallback(
    async (silent = false) => {
      try {
        if (!silent) setLogsLoading(true);
        const res = await getCrawlLogs({
          page: logsPage,
          page_size: 10,
          platform: logPlatform || undefined,
          status: logStatus || undefined,
        });
        setLogs(res.data?.items || []);
        setLogsTotal(res.data?.pagination.total || 0);
      } catch (err) {
        if (!silent) message.error(getErrorMessage(err));
      } finally {
        if (!silent) setLogsLoading(false);
      }
    },
    [logsPage, logPlatform, logStatus],
  );

  const fetchBase = useCallback(async () => {
    try {
      setLoading(true);
      onSyncState({ refreshing: true });
      const [platformRes, statusRes, scheduleRes] = await Promise.all([
        getPlatforms(),
        getCrawlStatus(),
        getCrawlerSchedule(),
      ]);
      const platformList = platformRes.data || [];
      setPlatforms(platformList);
      setSelected((current) =>
        current.length > 0
          ? current.filter((name) => platformList.some((item) => item.name === name && item.is_active))
          : platformList.filter((item) => item.is_active).map((item) => item.name),
      );
      setStatus(statusRes.data);
      setSchedule(scheduleRes.data);
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
    fetchBase();
  }, [fetchBase, refreshKey]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs, refreshKey]);

  // 运行中 1s 轮询采集状态，空闲后停止
  useEffect(() => {
    if (!status?.is_running) return undefined;
    const timer = window.setInterval(async () => {
      try {
        const res = await getCrawlStatus();
        setStatus(res.data);
      } catch {
        // 静默失败，下一轮继续
      }
    }, 1000);
    return () => window.clearInterval(timer);
  }, [status?.is_running]);

  // 日志 10s 静默轮询
  useEffect(() => {
    const timer = window.setInterval(() => {
      fetchLogs(true);
    }, 10000);
    return () => window.clearInterval(timer);
  }, [fetchLogs]);

  const activeNames = useMemo(
    () => platforms.filter((item) => item.is_active).map((item) => item.name),
    [platforms],
  );

  const handleTrigger = useCallback(async () => {
    if (selected.length === 0) {
      message.warning('请先选择至少一个平台');
      return;
    }
    try {
      setTriggering(true);
      await triggerCrawler({ platforms: selected, is_async: isAsync });
      message.success(isAsync ? '采集任务已提交（异步执行）' : '采集任务执行完成');
      const statusRes = await getCrawlStatus();
      setStatus(statusRes.data);
      await fetchLogs(true);
      onSyncState({ refreshing: false, lastUpdated: new Date().toISOString() });
    } catch (err) {
      message.error(getErrorMessage(err));
    } finally {
      setTriggering(false);
    }
  }, [selected, isAsync, fetchLogs, onSyncState]);

  const saveSchedule = useCallback(async () => {
    if (!schedule) return;
    try {
      setSavingSchedule(true);
      const res = await updateCrawlerSchedule(schedule);
      setSchedule(res.data);
      message.success('调度配置已保存');
    } catch (err) {
      message.error(getErrorMessage(err));
    } finally {
      setSavingSchedule(false);
    }
  }, [schedule]);

  const runningTask = status?.current_task;

  return (
    <DataState loading={loading} error={error} empty={!status} emptyTitle="采集状态不可用">
      <div className="psa-grid two-one">
        <div className="ad-stack">
          <Panel title="手动采集" eyebrow="选择平台并触发">
            <Checkbox.Group
              value={selected}
              onChange={(values) => setSelected(values as string[])}
            >
              <div className="psa-list">
                {platforms.map((item) => (
                  <div className="psa-row" key={item.id}>
                    <div>
                      <p className="psa-row-title">
                        <Checkbox value={item.name} disabled={!item.is_active}>
                          {item.display_name}
                        </Checkbox>
                      </p>
                      <div className="psa-row-meta">
                        <PlatformBadge name={item.name} />
                        {!item.is_active && <span>已停用</span>}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Checkbox.Group>
            <div className="psa-actions" style={{ marginTop: 16 }}>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                loading={triggering}
                disabled={selected.length === 0}
                onClick={handleTrigger}
              >
                立即采集
              </Button>
              <span className="psa-inline-tools">
                <Switch checked={isAsync} onChange={setIsAsync} />
                <span className="psa-page-note" style={{ margin: 0 }}>{isAsync ? '异步执行' : '同步执行'}</span>
              </span>
              <Button size="small" type="text" onClick={() => setSelected(activeNames)}>
                全选启用平台
              </Button>
            </div>
          </Panel>

          <Panel
            title="当前状态"
            extra={<StatusBadge status={status?.is_running ? 'running' : 'success'} />}
          >
            {status?.is_running && runningTask ? (
              <div className="psa-detail-list">
                <div className="psa-detail-item">
                  <span>任务 ID</span>
                  <strong className="ad-code">{runningTask.task_id}</strong>
                </div>
                <div className="psa-detail-item">
                  <span>采集平台</span>
                  <strong>{runningTask.platforms.join('、') || '暂无'}</strong>
                </div>
                <div className="psa-detail-item">
                  <span>已运行</span>
                  <strong className="ad-elapsed">{formatNumber(runningTask.elapsed_seconds)}s</strong>
                </div>
                <div className="psa-detail-item">
                  <span>队列长度</span>
                  <strong>{formatNumber(status.queue_length)}</strong>
                </div>
              </div>
            ) : (
              <div className="psa-detail-list">
                <div className="psa-detail-item">
                  <span>运行状态</span>
                  <strong>空闲</strong>
                </div>
                <div className="psa-detail-item">
                  <span>队列长度</span>
                  <strong>{formatNumber(status?.queue_length)}</strong>
                </div>
                <p className="psa-page-note">当前没有运行中的采集任务，可在上方手动触发。</p>
              </div>
            )}
          </Panel>

          <Panel title="调度配置" eyebrow="定时自动采集" extra={<ScheduleOutlined />}>
            <div className="psa-detail-list">
              <div className="psa-detail-item">
                <span>采集间隔（分钟）</span>
                <InputNumber
                  min={1}
                  max={1440}
                  value={schedule?.interval_minutes}
                  onChange={(value) =>
                    setSchedule((current) => current && { ...current, interval_minutes: value ?? current.interval_minutes })
                  }
                />
              </div>
              <div className="psa-detail-item">
                <span>启用定时采集</span>
                <Switch
                  checked={schedule?.is_enabled}
                  onChange={(checked) =>
                    setSchedule((current) => current && { ...current, is_enabled: checked })
                  }
                />
              </div>
            </div>
            <div className="psa-actions" style={{ marginTop: 16 }}>
              <Button
                type="primary"
                icon={<ClockCircleOutlined />}
                loading={savingSchedule}
                disabled={!schedule}
                onClick={saveSchedule}
              >
                保存调度配置
              </Button>
            </div>
          </Panel>
        </div>

        <Panel
          title="采集日志"
          className="tall"
          eyebrow={`共 ${formatNumber(logsTotal)} 条`}
          extra={<SyncOutlined spin={status?.is_running} style={{ color: 'var(--primary)' }} />}
        >
          <div className="psa-filter-bar" style={{ marginBottom: 12 }}>
            <Select
              allowClear
              placeholder="平台筛选"
              style={{ width: 140 }}
              value={logPlatform}
              onChange={(value) => {
                setLogPlatform(value);
                setLogsPage(1);
              }}
              options={platforms.map((item) => ({ value: item.name, label: item.display_name }))}
            />
            <Select
              allowClear
              placeholder="状态筛选"
              style={{ width: 120 }}
              value={logStatus}
              onChange={(value) => {
                setLogStatus(value);
                setLogsPage(1);
              }}
              options={LOG_STATUS_OPTIONS}
            />
          </div>
          <Table<CrawlLog>
            className="psa-table"
            size="small"
            rowKey="id"
            loading={logsLoading}
            dataSource={logs}
            locale={{ emptyText: '暂无采集日志' }}
            pagination={{
              current: logsPage,
              total: logsTotal,
              pageSize: 10,
              size: 'small',
              showTotal: (total) => `共 ${formatNumber(total)} 条`,
              onChange: setLogsPage,
            }}
            columns={[
              {
                title: '平台',
                key: 'platform',
                render: (_, record) => <PlatformBadge name={record.platform_name || `平台 ${record.platform_id}`} />,
              },
              {
                title: '状态',
                dataIndex: 'status',
                render: (value) => <StatusBadge status={value} />,
              },
              {
                title: '记录数',
                dataIndex: 'records_count',
                align: 'right',
                render: (value) => formatNumber(value),
              },
              {
                title: '错误信息',
                dataIndex: 'error_message',
                ellipsis: true,
                render: (value) =>
                  value ? (
                    <Tooltip title={value}>
                      <span className="ad-code">{value}</span>
                    </Tooltip>
                  ) : (
                    '—'
                  ),
              },
              {
                title: '开始时间',
                dataIndex: 'started_at',
                render: (value) => formatDateTime(value),
              },
              {
                title: '耗时',
                dataIndex: 'duration_seconds',
                align: 'right',
                render: (value) => (value ? `${value}s` : '—'),
              },
            ]}
          />
        </Panel>
      </div>
    </DataState>
  );
};

export default CrawlerView;
