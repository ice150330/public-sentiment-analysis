import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Input, Select, Switch, Table } from 'antd';
import {
  DatabaseOutlined,
  DownloadOutlined,
  FileTextOutlined,
  PlayCircleOutlined,
  SafetyOutlined,
  SettingOutlined,
  SyncOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import {
  AlertRule,
  AuditLogRecord,
  AuthUser,
  CrawlLog,
  CrawlStatus,
  createDatabaseBackup,
  DatabaseBackup,
  downloadDatabaseBackup,
  getAlertRules,
  getCrawlLogs,
  getCrawlStatus,
  getDatabaseBackups,
  getErrorMessage,
  getPlatforms,
  getTypedAuditLogs,
  getTypedSystemLogs,
  getUsers,
  Platform,
  SystemLogRecord,
  triggerCrawler,
  updatePlatform,
  updateUser,
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
  { key: 'users', label: '用户权限', icon: <TeamOutlined /> },
  { key: 'crawler', label: '采集任务', icon: <SyncOutlined /> },
  { key: 'rules', label: '预警规则', icon: <SafetyOutlined /> },
  { key: 'logs', label: '系统日志', icon: <FileTextOutlined /> },
  { key: 'database', label: '数据库', icon: <DatabaseOutlined /> },
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

    if (activeView === 'users') {
      return <UserManagement />;
    }

    if (activeView === 'logs') {
      return <SystemLogs />;
    }

    if (activeView === 'database') {
      return <DatabaseMaintenance />;
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

const formatBytes = (value?: number | null) => {
  const bytes = value || 0;
  if (bytes >= 1024 * 1024) {
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }
  if (bytes >= 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${formatNumber(bytes)} B`;
};

const DatabaseMaintenance: React.FC = () => {
  const [backups, setBackups] = useState<DatabaseBackup[]>([]);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchBackups = useCallback(async () => {
    try {
      setLoading(true);
      const response = await getDatabaseBackups();
      setBackups(response.data?.items || []);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBackups();
  }, [fetchBackups]);

  const createBackup = async () => {
    try {
      setActing(true);
      const response = await createDatabaseBackup();
      setBackups((current) => [
        response.data,
        ...current.filter((item) => item.filename !== response.data.filename),
      ]);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setActing(false);
    }
  };

  const downloadBackup = async (filename: string) => {
    try {
      setDownloading(filename);
      await downloadDatabaseBackup(filename);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="psa-grid two-one">
      <Panel title="备份文件" className="tall" eyebrow={`${formatNumber(backups.length)} 个文件`}>
        <DataState loading={loading} error={error}>
          <Table<DatabaseBackup>
            className="psa-table"
            size="small"
            rowKey="filename"
            pagination={{ pageSize: 8, size: 'small' }}
            dataSource={backups}
            locale={{ emptyText: '暂无备份文件' }}
            columns={[
              { title: '文件名', dataIndex: 'filename', ellipsis: true },
              { title: '大小', dataIndex: 'size_bytes', render: (value) => formatBytes(value) },
              { title: '创建时间', dataIndex: 'created_at', render: (value) => formatDateTime(value) },
              {
                title: '操作',
                render: (_, record) => (
                  <Button
                    size="small"
                    icon={<DownloadOutlined />}
                    loading={downloading === record.filename}
                    onClick={() => downloadBackup(record.filename)}
                  >
                    下载
                  </Button>
                ),
              },
            ]}
          />
        </DataState>
      </Panel>
      <Panel title="SQLite 维护">
        <div className="psa-detail-list">
          <div className="psa-detail-item">
            <span>数据库</span>
            <strong>SQLite</strong>
          </div>
          <div className="psa-detail-item">
            <span>索引状态</span>
            <strong>启动自动维护</strong>
          </div>
          <div className="psa-detail-item">
            <span>恢复方式</span>
            <strong>停机替换</strong>
          </div>
        </div>
        <div className="psa-actions" style={{ marginTop: 16 }}>
          <Button type="primary" icon={<DatabaseOutlined />} loading={acting} onClick={createBackup}>
            创建备份
          </Button>
          <Button icon={<SyncOutlined />} loading={loading} onClick={fetchBackups}>
            刷新
          </Button>
        </div>
      </Panel>
    </div>
  );
};

const UserManagement: React.FC = () => {
  const [users, setUsers] = useState<AuthUser[]>([]);
  const [keyword, setKeyword] = useState('');
  const [loading, setLoading] = useState(true);
  const [actingId, setActingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true);
      const response = await getUsers({ keyword: keyword.trim() || undefined, page: 1, page_size: 50 });
      setUsers(response.data?.items || []);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [keyword]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const updateUserRow = async (target: AuthUser, patch: Partial<Pick<AuthUser, 'role' | 'platform_scope' | 'is_active'>>) => {
    try {
      setActingId(target.id);
      const response = await updateUser(target.id, patch);
      setUsers((current) => current.map((item) => (item.id === target.id ? response.data : item)));
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setActingId(null);
    }
  };

  return (
    <DataState loading={loading} error={error} empty={users.length === 0} emptyTitle="暂无用户">
      <div className="psa-grid one-two">
        <Panel
          title="用户权限"
          className="tall"
          extra={
            <div className="psa-inline-tools">
              <Input.Search
                allowClear
                value={keyword}
                onChange={(event) => setKeyword(event.target.value)}
                onSearch={fetchUsers}
                placeholder="搜索用户名"
                style={{ width: 200 }}
              />
            </div>
          }
        >
          <Table<AuthUser>
            className="psa-table"
            size="small"
            rowKey="id"
            pagination={{ pageSize: 10, size: 'small' }}
            dataSource={users}
            columns={[
              { title: '用户', dataIndex: 'username', ellipsis: true },
              {
                title: '角色',
                render: (_, record) => (
                  <Select
                    size="small"
                    value={record.role}
                    style={{ width: 110 }}
                    loading={actingId === record.id}
                    onChange={(role) => updateUserRow(record, { role })}
                    options={[
                      { value: 'admin', label: '管理员' },
                      { value: 'analyst', label: '分析师' },
                      { value: 'visitor', label: '访客' },
                    ]}
                  />
                ),
              },
              {
                title: '平台范围',
                render: (_, record) => (
                  <Input
                    size="small"
                    defaultValue={record.platform_scope}
                    onPressEnter={(event) => updateUserRow(record, { platform_scope: event.currentTarget.value })}
                    onBlur={(event) => {
                      if (event.currentTarget.value !== record.platform_scope) {
                        updateUserRow(record, { platform_scope: event.currentTarget.value });
                      }
                    }}
                  />
                ),
              },
              {
                title: '启用',
                render: (_, record) => (
                  <Switch
                    size="small"
                    checked={record.is_active}
                    loading={actingId === record.id}
                    onChange={(is_active) => updateUserRow(record, { is_active })}
                  />
                ),
              },
            ]}
          />
        </Panel>
        <Panel title="权限说明">
          <div className="psa-detail-list">
            <div className="psa-detail-item">
              <span>admin</span>
              <strong>管理用户、系统日志、全部平台数据</strong>
            </div>
            <div className="psa-detail-item">
              <span>analyst</span>
              <strong>访问分析数据，按平台范围导出</strong>
            </div>
            <div className="psa-detail-item">
              <span>visitor</span>
              <strong>只读访问基础页面</strong>
            </div>
            <p className="psa-page-note">平台范围使用英文标识逗号分隔，例如 weibo,douyin；all 表示全部。</p>
          </div>
        </Panel>
      </div>
    </DataState>
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
