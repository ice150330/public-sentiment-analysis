import React, { useCallback, useEffect, useState } from 'react';
import {
  Button,
  DatePicker,
  Input,
  message,
  Select,
  Table,
  Tabs,
  Tooltip,
} from 'antd';
import {
  DatabaseOutlined,
  DownloadOutlined,
  FileTextOutlined,
  HeartOutlined,
  SafetyOutlined,
} from '@ant-design/icons';
import type { Dayjs } from 'dayjs';
import {
  AuditLogRecord,
  createDatabaseBackup,
  DatabaseBackup,
  downloadDatabaseBackup,
  getDatabaseBackups,
  getErrorMessage,
  getSystemHealth,
  getTypedAuditLogs,
  getTypedSystemLogs,
  SystemHealth,
  SystemLogRecord,
} from '@/services/api';
import {
  DataState,
  formatDateTime,
  formatNumber,
  Panel,
  StatusBadge,
} from '@/components/DesignSystem';
import { AdminViewProps } from '../types';

const LEVEL_OPTIONS = ['INFO', 'WARNING', 'ERROR', 'DEBUG'].map((value) => ({ value, label: value }));

const formatBytes = (value?: number | null) => {
  const bytes = value || 0;
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${formatNumber(bytes)} B`;
};

type LogTabKey = 'system' | 'audit' | 'backup';

/** 系统日志 —— 系统健康面板 + 系统日志 / 审计日志 / 数据库备份三页签 */
const LogsView: React.FC<AdminViewProps> = ({ refreshKey, onSyncState }) => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<LogTabKey>('system');

  const fetchHealth = useCallback(async () => {
    try {
      setLoading(true);
      onSyncState({ refreshing: true });
      const res = await getSystemHealth();
      setHealth(res.data);
      setHealthError(null);
      onSyncState({ refreshing: false, lastUpdated: new Date().toISOString() });
    } catch (err) {
      setHealthError(getErrorMessage(err));
      onSyncState({ refreshing: false });
    } finally {
      setLoading(false);
    }
  }, [onSyncState]);

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth, refreshKey]);

  const components = Object.entries(health?.components || {});

  return (
    <div className="ad-stack">
      <Panel
        title="系统健康"
        eyebrow={health?.checked_at ? `检测于 ${formatDateTime(health.checked_at)}` : undefined}
        extra={<StatusBadge status={health?.overall_status} />}
      >
        <DataState loading={loading} error={healthError} empty={components.length === 0} emptyTitle="暂无组件状态">
          <div className="psa-list">
            {components.map(([name, item]) => (
              <div className="psa-row ad-health-row" key={name}>
                <div>
                  <p className="psa-row-title">{name}</p>
                  <div className="psa-row-meta">
                    <span className="ad-health-message">{item.message || '运行正常'}</span>
                  </div>
                </div>
                <StatusBadge status={item.status} />
                <HeartOutlined style={{ color: item.status === 'healthy' || item.status === 'ok' ? 'var(--positive)' : 'var(--negative)' }} />
              </div>
            ))}
          </div>
        </DataState>
      </Panel>

      <Panel>
        <Tabs
          activeKey={tab}
          onChange={(key) => setTab(key as LogTabKey)}
          items={[
            { key: 'system', label: '系统日志', icon: <FileTextOutlined /> },
            { key: 'audit', label: '审计日志', icon: <SafetyOutlined /> },
            { key: 'backup', label: '数据库备份', icon: <DatabaseOutlined /> },
          ]}
        />
        {tab === 'system' && <SystemLogTab refreshKey={refreshKey} />}
        {tab === 'audit' && <AuditLogTab refreshKey={refreshKey} />}
        {tab === 'backup' && <BackupTab refreshKey={refreshKey} />}
      </Panel>
    </div>
  );
};

/** 系统日志页签：级别 / 模块 / 时间范围筛选 + 分页表格 */
const SystemLogTab: React.FC<{ refreshKey: number }> = ({ refreshKey }) => {
  const [items, setItems] = useState<SystemLogRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [level, setLevel] = useState<string>();
  const [module, setModule] = useState('');
  const [moduleDraft, setModuleDraft] = useState('');
  const [range, setRange] = useState<[Dayjs, Dayjs] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = useCallback(async () => {
    try {
      setLoading(true);
      const res = await getTypedSystemLogs({
        page,
        page_size: 10,
        level: level || undefined,
        module: module.trim() || undefined,
        start_time: range?.[0]?.startOf('day').toISOString(),
        end_time: range?.[1]?.endOf('day').toISOString(),
      });
      setItems(res.data?.items || []);
      setTotal(res.data?.pagination.total || 0);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [page, level, module, range]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs, refreshKey]);

  return (
    <DataState loading={loading} error={error} empty={items.length === 0} emptyTitle="暂无系统日志">
      <div className="psa-filter-bar" style={{ marginBottom: 12 }}>
        <Select
          allowClear
          placeholder="级别"
          style={{ width: 110 }}
          value={level}
          onChange={(value) => {
            setLevel(value);
            setPage(1);
          }}
          options={LEVEL_OPTIONS}
        />
        <Input.Search
          allowClear
          placeholder="模块名，如 crawler"
          style={{ width: 180 }}
          value={moduleDraft}
          onChange={(event) => setModuleDraft(event.target.value)}
          onSearch={(value) => {
            setModule(value);
            setPage(1);
          }}
        />
        <DatePicker.RangePicker
          value={range}
          onChange={(value) => {
            setRange(value as [Dayjs, Dayjs] | null);
            setPage(1);
          }}
        />
      </div>
      <Table<SystemLogRecord>
        className="psa-table"
        size="small"
        rowKey="id"
        dataSource={items}
        locale={{ emptyText: '暂无系统日志' }}
        pagination={{
          current: page,
          total,
          pageSize: 10,
          size: 'small',
          showTotal: (value) => `共 ${formatNumber(value)} 条`,
          onChange: setPage,
        }}
        columns={[
          {
            title: '级别',
            dataIndex: 'level',
            width: 100,
            render: (value) => <StatusBadge status={value} />,
          },
          {
            title: '模块',
            dataIndex: 'module',
            width: 120,
            render: (value) => value || 'system',
          },
          {
            title: '事件',
            dataIndex: 'event',
            width: 160,
            ellipsis: true,
            render: (value) => value || '未标注',
          },
          {
            title: '内容',
            dataIndex: 'message',
            ellipsis: true,
            render: (value) =>
              value ? (
                <Tooltip title={value} placement="topLeft">
                  {value}
                </Tooltip>
              ) : (
                '—'
              ),
          },
          {
            title: '时间',
            dataIndex: 'created_at',
            width: 130,
            render: (value) => formatDateTime(value),
          },
        ]}
      />
    </DataState>
  );
};

/** 审计日志页签：操作人筛选 + 分页表格 */
const AuditLogTab: React.FC<{ refreshKey: number }> = ({ refreshKey }) => {
  const [items, setItems] = useState<AuditLogRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [operator, setOperator] = useState('');
  const [operatorDraft, setOperatorDraft] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = useCallback(async () => {
    try {
      setLoading(true);
      const res = await getTypedAuditLogs({
        page,
        page_size: 10,
        operator: operator.trim() || undefined,
      });
      setItems(res.data?.items || []);
      setTotal(res.data?.pagination.total || 0);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [page, operator]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs, refreshKey]);

  return (
    <DataState loading={loading} error={error} empty={items.length === 0} emptyTitle="暂无审计日志">
      <div className="psa-filter-bar" style={{ marginBottom: 12 }}>
        <Input.Search
          allowClear
          placeholder="操作人用户名"
          style={{ width: 180 }}
          value={operatorDraft}
          onChange={(event) => setOperatorDraft(event.target.value)}
          onSearch={(value) => {
            setOperator(value);
            setPage(1);
          }}
        />
      </div>
      <Table<AuditLogRecord>
        className="psa-table"
        size="small"
        rowKey="id"
        dataSource={items}
        locale={{ emptyText: '暂无审计日志' }}
        pagination={{
          current: page,
          total,
          pageSize: 10,
          size: 'small',
          showTotal: (value) => `共 ${formatNumber(value)} 条`,
          onChange: setPage,
        }}
        columns={[
          { title: '操作人', dataIndex: 'operator', width: 110 },
          {
            title: '动作',
            dataIndex: 'action',
            width: 150,
            ellipsis: true,
            render: (value) => value || '—',
          },
          {
            title: '对象类型',
            dataIndex: 'target_type',
            width: 110,
            render: (value) => value || 'system',
          },
          {
            title: '对象 ID',
            dataIndex: 'target_id',
            width: 100,
            render: (value) => value || '—',
          },
          {
            title: '备注',
            dataIndex: 'note',
            ellipsis: true,
            render: (value) =>
              value ? (
                <Tooltip title={value} placement="topLeft">
                  {value}
                </Tooltip>
              ) : (
                '—'
              ),
          },
          {
            title: '时间',
            dataIndex: 'created_at',
            width: 130,
            render: (value) => formatDateTime(value),
          },
        ]}
      />
    </DataState>
  );
};

/** 数据库备份页签：立即备份 + 备份文件列表 + 下载 */
const BackupTab: React.FC<{ refreshKey: number }> = ({ refreshKey }) => {
  const [items, setItems] = useState<DatabaseBackup[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchBackups = useCallback(async () => {
    try {
      setLoading(true);
      const res = await getDatabaseBackups();
      setItems(res.data?.items || []);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBackups();
  }, [fetchBackups, refreshKey]);

  const handleCreate = useCallback(async () => {
    try {
      setCreating(true);
      const res = await createDatabaseBackup();
      message.success(`备份已创建：${res.data.filename}`);
      await fetchBackups();
    } catch (err) {
      message.error(getErrorMessage(err));
    } finally {
      setCreating(false);
    }
  }, [fetchBackups]);

  const handleDownload = useCallback(async (filename: string) => {
    try {
      setDownloading(filename);
      await downloadDatabaseBackup(filename);
      message.success(`备份 ${filename} 已开始下载`);
    } catch (err) {
      message.error(getErrorMessage(err));
    } finally {
      setDownloading(null);
    }
  }, []);

  return (
    <DataState loading={loading} error={error} empty={items.length === 0} emptyTitle="暂无备份文件">
      <div className="psa-actions" style={{ marginBottom: 12 }}>
        <Button
          type="primary"
          icon={<DatabaseOutlined />}
          loading={creating}
          onClick={handleCreate}
        >
          立即备份
        </Button>
        <span className="psa-page-note" style={{ margin: 0 }}>
          共 {formatNumber(items.length)} 个备份文件
        </span>
      </div>
      <Table<DatabaseBackup>
        className="psa-table"
        size="small"
        rowKey="filename"
        dataSource={items}
        locale={{ emptyText: '暂无备份文件' }}
        pagination={{ pageSize: 8, size: 'small' }}
        columns={[
          {
            title: '文件名',
            dataIndex: 'filename',
            ellipsis: true,
            render: (value) => <span className="ad-code">{value}</span>,
          },
          {
            title: '大小',
            dataIndex: 'size_bytes',
            width: 100,
            align: 'right',
            render: (value) => formatBytes(value),
          },
          {
            title: '创建时间',
            dataIndex: 'created_at',
            width: 130,
            render: (value) => formatDateTime(value),
          },
          {
            title: '操作',
            key: 'actions',
            width: 100,
            render: (_, record) => (
              <Button
                size="small"
                icon={<DownloadOutlined />}
                loading={downloading === record.filename}
                onClick={() => handleDownload(record.filename)}
              >
                下载
              </Button>
            ),
          },
        ]}
      />
    </DataState>
  );
};

export default LogsView;
