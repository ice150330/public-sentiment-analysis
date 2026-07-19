import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Input,
  message,
  Popconfirm,
  Select,
  Switch,
  Table,
} from 'antd';
import {
  CrownOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons';
import {
  AuthRole,
  AuthUser,
  getErrorMessage,
  getUsers,
  updateUser,
} from '@/services/api';
import {
  DataState,
  formatNumber,
  MetricCard,
  Panel,
} from '@/components/DesignSystem';
import { AdminViewProps } from '../types';

const ROLE_OPTIONS: { value: AuthRole; label: string }[] = [
  { value: 'admin', label: '管理员' },
  { value: 'analyst', label: '分析师' },
  { value: 'visitor', label: '访客' },
];

const ROLE_LABELS: Record<AuthRole, string> = {
  admin: '管理员',
  analyst: '分析师',
  visitor: '访客',
};

const STATUS_OPTIONS = [
  { value: 'all', label: '全部状态' },
  { value: 'active', label: '启用' },
  { value: 'inactive', label: '停用' },
];

type StatusFilter = 'all' | 'active' | 'inactive';

/** 用户权限 —— 角色统计指标卡 + 筛选 + 用户表格（角色改选需确认） */
const UsersView: React.FC<AdminViewProps> = ({ refreshKey, onSyncState }) => {
  const [users, setUsers] = useState<AuthUser[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [roleFilter, setRoleFilter] = useState<AuthRole | 'all'>('all');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [keyword, setKeyword] = useState('');
  const [keywordDraft, setKeywordDraft] = useState('');
  const [stats, setStats] = useState<{ total: number; admin: number; analyst: number; visitor: number } | null>(null);
  const [roleDraft, setRoleDraft] = useState<{ id: number; role: AuthRole } | null>(null);
  const [loading, setLoading] = useState(true);
  const [actingId, setActingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    try {
      const res = await getUsers({ page: 1, page_size: 500 });
      const all = res.data?.items || [];
      setStats({
        total: res.data?.pagination.total ?? all.length,
        admin: all.filter((item) => item.role === 'admin').length,
        analyst: all.filter((item) => item.role === 'analyst').length,
        visitor: all.filter((item) => item.role === 'visitor').length,
      });
    } catch {
      // 统计失败不阻断列表
    }
  }, []);

  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true);
      onSyncState({ refreshing: true });
      const res = await getUsers({
        page,
        page_size: 10,
        role: roleFilter === 'all' ? undefined : roleFilter,
        is_active: statusFilter === 'all' ? undefined : statusFilter === 'active',
        keyword: keyword.trim() || undefined,
      });
      setUsers(res.data?.items || []);
      setTotal(res.data?.pagination.total || 0);
      setError(null);
      onSyncState({ refreshing: false, lastUpdated: new Date().toISOString() });
    } catch (err) {
      setError(getErrorMessage(err));
      onSyncState({ refreshing: false });
    } finally {
      setLoading(false);
    }
  }, [onSyncState, page, roleFilter, statusFilter, keyword]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers, refreshKey]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats, refreshKey]);

  const patchUser = useCallback(
    async (target: AuthUser, patch: Partial<Pick<AuthUser, 'role' | 'platform_scope' | 'is_active'>>, successText: string) => {
      try {
        setActingId(target.id);
        const res = await updateUser(target.id, patch);
        setUsers((current) => current.map((item) => (item.id === target.id ? res.data : item)));
        message.success(successText);
        if (patch.role) fetchStats();
      } catch (err) {
        message.error(getErrorMessage(err));
      } finally {
        setActingId(null);
      }
    },
    [fetchStats],
  );

  const confirmRoleChange = useCallback(async () => {
    const target = users.find((item) => item.id === roleDraft?.id);
    if (!target || !roleDraft) {
      setRoleDraft(null);
      return;
    }
    setRoleDraft(null);
    await patchUser(target, { role: roleDraft.role }, `已将「${target.username}」的角色改为${ROLE_LABELS[roleDraft.role]}`);
  }, [roleDraft, users, patchUser]);

  const filterBar = useMemo(
    () => (
      <div className="psa-filter-bar" style={{ marginBottom: 12 }}>
        <Select<AuthRole | 'all'>
          value={roleFilter}
          style={{ width: 120 }}
          onChange={(value) => {
            setRoleFilter(value);
            setPage(1);
          }}
          options={[{ value: 'all', label: '全部角色' }, ...ROLE_OPTIONS]}
        />
        <Select<StatusFilter>
          value={statusFilter}
          style={{ width: 110 }}
          onChange={(value) => {
            setStatusFilter(value);
            setPage(1);
          }}
          options={STATUS_OPTIONS}
        />
        <Input.Search
          allowClear
          placeholder="搜索用户名"
          style={{ width: 180 }}
          value={keywordDraft}
          onChange={(event) => setKeywordDraft(event.target.value)}
          onSearch={(value) => {
            setKeyword(value);
            setPage(1);
          }}
        />
      </div>
    ),
    [roleFilter, statusFilter, keywordDraft],
  );

  return (
    <DataState loading={loading} error={error} empty={users.length === 0 && !keyword && roleFilter === 'all' && statusFilter === 'all'} emptyTitle="暂无用户">
      <div className="ad-stack">
        <div className="psa-grid metrics">
          <MetricCard
            label="总用户"
            value={formatNumber(stats?.total)}
            helper="系统注册账号总数"
            icon={<TeamOutlined />}
          />
          <MetricCard
            label="管理员"
            value={formatNumber(stats?.admin)}
            helper="拥有全部管理权限"
            icon={<CrownOutlined />}
            tone="warning"
          />
          <MetricCard
            label="分析师"
            value={formatNumber(stats?.analyst)}
            helper="可访问分析与导出"
            icon={<UserOutlined />}
            tone="positive"
          />
          <MetricCard
            label="访客"
            value={formatNumber(stats?.visitor)}
            helper="只读访问基础页面"
            icon={<UserOutlined />}
            tone="neutral"
          />
        </div>

        <Panel title="用户列表" eyebrow={`共 ${formatNumber(total)} 个账号`}>
          {filterBar}
          <Table<AuthUser>
            className="psa-table"
            size="middle"
            rowKey="id"
            dataSource={users}
            locale={{ emptyText: '当前筛选条件下暂无用户' }}
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
                title: '用户名',
                dataIndex: 'username',
                render: (value, record) => (
                  <span>
                    <strong>{value}</strong>
                    <span className="psa-page-note" style={{ margin: '0 0 0 8px' }}>#{record.id}</span>
                  </span>
                ),
              },
              {
                title: '邮箱',
                dataIndex: 'email',
                ellipsis: true,
                render: (value) => value || '未绑定',
              },
              {
                title: '角色',
                dataIndex: 'role',
                width: 130,
                render: (value: AuthRole, record) => (
                  <Popconfirm
                    title="变更用户角色"
                    description={roleDraft ? `确定将「${record.username}」改为${ROLE_LABELS[roleDraft.role]}吗？` : ''}
                    open={roleDraft?.id === record.id}
                    onOpenChange={(next) => {
                      if (!next) setRoleDraft(null);
                    }}
                    onConfirm={confirmRoleChange}
                    okText="确定"
                    cancelText="取消"
                    okButtonProps={{ loading: actingId === record.id }}
                  >
                    <Select<AuthRole>
                      size="small"
                      value={value}
                      style={{ width: 110 }}
                      loading={actingId === record.id}
                      onChange={(role) => setRoleDraft({ id: record.id, role })}
                      options={ROLE_OPTIONS}
                    />
                  </Popconfirm>
                ),
              },
              {
                title: '平台范围',
                dataIndex: 'platform_scope',
                width: 170,
                render: (value: string, record) => (
                  <Input
                    key={`${record.id}-${value}`}
                    size="small"
                    defaultValue={value}
                    disabled={actingId === record.id}
                    onBlur={(event) => {
                      const next = event.target.value.trim();
                      if (next && next !== value) {
                        patchUser(record, { platform_scope: next }, `已更新「${record.username}」的平台范围`);
                      }
                    }}
                    onPressEnter={(event) => event.currentTarget.blur()}
                  />
                ),
              },
              {
                title: '启用',
                dataIndex: 'is_active',
                width: 80,
                render: (value: boolean, record) => (
                  <Switch
                    checked={value}
                    loading={actingId === record.id}
                    onChange={(checked) =>
                      patchUser(record, { is_active: checked }, checked ? `已启用「${record.username}」` : `已停用「${record.username}」`)
                    }
                  />
                ),
              },
            ]}
          />
          <p className="psa-page-note">平台范围使用英文标识逗号分隔，例如 weibo,douyin；all 表示全部平台。</p>
        </Panel>
      </div>
    </DataState>
  );
};

export default UsersView;
