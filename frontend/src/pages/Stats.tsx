import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Switch, Table } from 'antd';
import {
  FileTextOutlined,
  PlayCircleOutlined,
  SafetyOutlined,
  SettingOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import {
  AlertRule,
  AuditLogRecord,
  CrawlLog,
  CrawlStatus,
  getAlertRules,
  getCrawlLogs,
  getCrawlStatus,
  getErrorMessage,
  getPlatforms,
  getTypedAuditLogs,
  getTypedSystemLogs,
  Platform,
  SystemLogRecord,
  triggerCrawler,
  updatePlatform,
} from '../services/api';
import {
  DataState,
  formatDateTime,
  formatNumber,
  ModuleFrame,
  Panel,
  PlatformBadge,
  StatusBadge,
  SubView,
} from '../components/DesignSystem';

const views: SubView[] = [
  { key: 'platforms', label: '平台配置', icon: <SettingOutlined /> },
  { key: 'crawler', label: '采集任务', icon: <SyncOutlined /> },
  { key: 'rules', label: '预警规则', icon: <SafetyOutlined /> },
  { key: 'logs', label: '系统日志', icon: <FileTextOutlined /> },
];

const Stats: React.FC = () => {
  const [activeView, setActiveView] = useState('platforms');
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [status, setStatus] = useState<CrawlStatus | null>(null);
  const [logs, setLogs] = useState<CrawlLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [platformRes, statusRes, logsRes] = await Promise.all([
        getPlatforms(),
        getCrawlStatus(),
        getCrawlLogs({ page: 1, page_size: 20 }),
      ]);
      setPlatforms(platformRes.data || []);
      setStatus(statusRes.data);
      setLogs(logsRes.data?.items || []);
      setLastUpdated(new Date().toISOString());
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const activePlatforms = useMemo(() => platforms.filter((item) => item.is_active), [platforms]);

  const togglePlatform = async (platform: Platform, isActive: boolean) => {
    try {
      setActing(true);
      const res = await updatePlatform(platform.id, { is_active: isActive });
      setPlatforms((current) => current.map((item) => (item.id === platform.id ? res.data : item)));
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setActing(false);
    }
  };

  const triggerActiveCrawler = async () => {
    try {
      setActing(true);
      await triggerCrawler({
        platforms: activePlatforms.map((item) => item.name),
        is_async: true,
      });
      await fetchData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setActing(false);
    }
  };

  const renderContent = () => {
    if (activeView === 'crawler') {
      return (
        <CrawlerTasks
          status={status}
          logs={logs}
          activePlatforms={activePlatforms}
          loading={loading}
          acting={acting}
          error={error}
          onTrigger={triggerActiveCrawler}
        />
      );
    }

    if (activeView === 'rules') {
      return <AlertRules />;
    }

    if (activeView === 'logs') {
      return <SystemLogs />;
    }

    return (
      <DataState loading={loading} error={error} empty={platforms.length === 0} emptyTitle="暂无平台配置">
        <div className="psa-grid one-two">
          <Panel title="平台开关" className="tall">
            <div className="psa-list">
              {platforms.map((platform) => (
                <div className="psa-row" key={platform.id}>
                  <div>
                    <p className="psa-row-title">{platform.display_name}</p>
                    <div className="psa-row-meta">
                      <PlatformBadge name={platform.name} />
                      <span>{platform.base_url || '未配置 URL'}</span>
                    </div>
                  </div>
                  <Switch
                    checked={platform.is_active}
                    loading={acting}
                    onChange={(checked) => togglePlatform(platform, checked)}
                  />
                </div>
              ))}
            </div>
          </Panel>
          <Panel title="平台配置明细">
            <Table<Platform>
              className="psa-table"
              size="small"
              rowKey="id"
              pagination={false}
              dataSource={platforms}
              columns={[
                { title: '平台', render: (_, record) => <PlatformBadge name={record.display_name} /> },
                { title: '标识', dataIndex: 'name' },
                { title: '状态', render: (_, record) => <StatusBadge status={record.is_active} /> },
                { title: '排序', dataIndex: 'sort_order' },
              ]}
            />
          </Panel>
        </div>
      </DataState>
    );
  };

  return (
    <ModuleFrame
      moduleLabel="管理"
      activeView={activeView}
      views={views}
      onViewChange={setActiveView}
      onRefresh={fetchData}
      refreshing={loading || acting}
      lastUpdated={lastUpdated}
    >
      {renderContent()}
    </ModuleFrame>
  );
};

const CrawlerTasks: React.FC<{
  status: CrawlStatus | null;
  logs: CrawlLog[];
  activePlatforms: Platform[];
  loading: boolean;
  acting: boolean;
  error: string | null;
  onTrigger: () => void;
}> = ({ status, logs, activePlatforms, loading, acting, error, onTrigger }) => (
  <DataState loading={loading} error={error} empty={!status} emptyTitle="暂无采集状态">
    <div className="psa-grid two-one">
      <div className="psa-grid">
        <Panel title="采集任务">
          <div className="psa-detail-list">
            <div className="psa-detail-item">
              <span>运行状态</span>
              <strong>{status?.is_running ? '运行中' : '空闲'}</strong>
            </div>
            <div className="psa-detail-item">
              <span>队列长度</span>
              <strong>{formatNumber(status?.queue_length)}</strong>
            </div>
            <div className="psa-detail-item">
              <span>启用平台</span>
              <strong>{activePlatforms.map((item) => item.display_name).join('、') || '暂无'}</strong>
            </div>
          </div>
          <div className="psa-actions" style={{ marginTop: 16 }}>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={onTrigger}
              loading={acting}
              disabled={activePlatforms.length === 0}
            >
              触发采集
            </Button>
          </div>
        </Panel>
        <Panel title="当前任务">
          <DataState empty={!status?.current_task} emptyTitle="暂无运行中的任务">
            {status?.current_task && (
              <div className="psa-detail-list">
                <div className="psa-detail-item">
                  <span>任务 ID</span>
                  <strong>{status.current_task.task_id}</strong>
                </div>
                <div className="psa-detail-item">
                  <span>平台</span>
                  <strong>{status.current_task.platforms.join('、') || '暂无'}</strong>
                </div>
                <div className="psa-detail-item">
                  <span>已运行</span>
                  <strong>{status.current_task.elapsed_seconds}s</strong>
                </div>
              </div>
            )}
          </DataState>
        </Panel>
      </div>
      <Panel title="采集日志">
        <CrawlerLogTable logs={logs} />
      </Panel>
    </div>
  </DataState>
);

const CrawlerLogTable: React.FC<{ logs: CrawlLog[] }> = ({ logs }) => (
  <Table<CrawlLog>
    className="psa-table"
    size="small"
    rowKey="id"
    pagination={{ pageSize: 8, size: 'small' }}
    dataSource={logs}
    locale={{ emptyText: '暂无采集日志' }}
    columns={[
      { title: '平台', render: (_, record) => record.platform_name || `平台 ${record.platform_id}` },
      { title: '状态', render: (_, record) => <StatusBadge status={record.status} /> },
      { title: '记录数', dataIndex: 'records_count', render: (value) => formatNumber(value) },
      { title: '开始时间', dataIndex: 'started_at', render: (value) => formatDateTime(value) },
      { title: '耗时', render: (_, record) => (record.duration_seconds ? `${record.duration_seconds}s` : '暂无') },
    ]}
  />
);

const AlertRules: React.FC = () => {
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRules = useCallback(async () => {
    try {
      setLoading(true);
      const res = await getAlertRules({ page: 1, page_size: 20 });
      setRules(res.data?.items || []);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRules();
  }, [fetchRules]);

  const activeCount = rules.filter((rule) => rule.is_active).length;
  const severityCounts = rules.reduce<Record<string, number>>((acc, rule) => {
    acc[rule.severity] = (acc[rule.severity] || 0) + 1;
    return acc;
  }, {});

  return (
    <DataState loading={loading} error={error} empty={rules.length === 0} emptyTitle="暂无预警规则">
      <div className="psa-grid two-one">
        <Panel title="预警规则" className="tall" eyebrow={`${formatNumber(activeCount)} 条启用`}>
          <Table<AlertRule>
            className="psa-table"
            size="small"
            rowKey="id"
            pagination={{ pageSize: 8, size: 'small' }}
            dataSource={rules}
            columns={[
              { title: '规则', dataIndex: 'name', ellipsis: true },
              { title: '等级', dataIndex: 'severity', render: (value) => <StatusBadge status={value} /> },
              { title: '类型', dataIndex: 'condition_type' },
              { title: '状态', render: (_, record) => <StatusBadge status={record.is_active} /> },
              { title: '冷却', dataIndex: 'cooldown_minutes', render: (value) => `${value}m` },
            ]}
          />
        </Panel>
        <Panel title="规则运行状态">
          <div className="psa-detail-list">
            <div className="psa-detail-item">
              <span>规则总数</span>
              <strong>{formatNumber(rules.length)}</strong>
            </div>
            <div className="psa-detail-item">
              <span>启用规则</span>
              <strong>{formatNumber(activeCount)}</strong>
            </div>
            {Object.entries(severityCounts).map(([severity, count]) => (
              <div className="psa-detail-item" key={severity}>
                <span>{severity}</span>
                <strong>{formatNumber(count)}</strong>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </DataState>
  );
};

const SystemLogs: React.FC = () => {
  const [logs, setLogs] = useState<SystemLogRecord[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = useCallback(async () => {
    try {
      setLoading(true);
      const [systemRes, auditRes] = await Promise.all([
        getTypedSystemLogs({ page: 1, page_size: 20 }),
        getTypedAuditLogs({ page: 1, page_size: 12 }),
      ]);
      setLogs(systemRes.data?.items || []);
      setAuditLogs(auditRes.data?.items || []);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  return (
    <DataState loading={loading} error={error} empty={logs.length === 0 && auditLogs.length === 0} emptyTitle="暂无系统日志">
      <div className="psa-grid two-one">
        <Panel title="系统日志" className="tall">
          <Table<SystemLogRecord>
            className="psa-table"
            size="small"
            rowKey="id"
            pagination={{ pageSize: 8, size: 'small' }}
            dataSource={logs}
            locale={{ emptyText: '暂无系统日志' }}
            columns={[
              { title: '级别', dataIndex: 'level', render: (value) => <StatusBadge status={value} /> },
              { title: '模块', dataIndex: 'module', render: (value) => value || 'system' },
              { title: '事件', dataIndex: 'event', render: (value) => value || '未标注' },
              { title: '时间', dataIndex: 'created_at', render: (value) => formatDateTime(value) },
            ]}
          />
        </Panel>
        <Panel title="审计记录">
          <DataState empty={auditLogs.length === 0} emptyTitle="暂无审计记录">
            <div className="psa-list">
              {auditLogs.map((item) => (
                <div className="psa-row" key={item.id}>
                  <div>
                    <p className="psa-row-title">{item.action || '操作记录'}</p>
                    <div className="psa-row-meta">
                      <span>{item.operator}</span>
                      <span>{item.target_type || 'system'} {item.target_id || ''}</span>
                      <span>{formatDateTime(item.created_at)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </DataState>
        </Panel>
      </div>
    </DataState>
  );
};

export default Stats;
