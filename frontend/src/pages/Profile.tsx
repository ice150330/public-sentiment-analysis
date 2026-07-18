import React, { useState } from 'react';
import { Alert, Button, Form, Input, Table } from 'antd';
import { LockOutlined, SaveOutlined, UserOutlined } from '@ant-design/icons';
import { useAuth } from '../auth/AuthContext';
import { AuditLogRecord, changePassword, getErrorMessage, getMyAuditLogs } from '../services/api';
import { formatDateTime, ModuleFrame, Panel, StatusBadge } from '../components/DesignSystem';

const Profile: React.FC = () => {
  const { user, refresh } = useAuth();
  const [auditLogs, setAuditLogs] = useState<AuditLogRecord[]>([]);
  const [logsLoading, setLogsLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form] = Form.useForm();

  const fetchAuditLogs = React.useCallback(async () => {
    try {
      setLogsLoading(true);
      const response = await getMyAuditLogs({ page: 1, page_size: 10 });
      setAuditLogs(response.data?.items || []);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLogsLoading(false);
    }
  }, []);

  React.useEffect(() => {
    fetchAuditLogs();
  }, [fetchAuditLogs]);

  const handlePasswordChange = async (values: { current_password: string; new_password: string }) => {
    try {
      setSaving(true);
      setError(null);
      setMessage(null);
      await changePassword(values);
      form.resetFields();
      await refresh();
      await fetchAuditLogs();
      setMessage('密码已更新');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <ModuleFrame
      moduleLabel="个人中心"
      activeView="profile"
      views={[{ key: 'profile', label: '账号安全', icon: <UserOutlined /> }]}
      onViewChange={() => undefined}
    >
      <div className="psa-grid two-one">
        <Panel title="账号信息">
          <div className="psa-detail-list">
            <div className="psa-detail-item">
              <span>用户名</span>
              <strong>{user?.username}</strong>
            </div>
            <div className="psa-detail-item">
              <span>角色</span>
              <StatusBadge status={user?.role} />
            </div>
            <div className="psa-detail-item">
              <span>平台权限</span>
              <strong>{user?.platform_scope || 'all'}</strong>
            </div>
            <div className="psa-detail-item">
              <span>状态</span>
              <StatusBadge status={user?.is_active} />
            </div>
          </div>
        </Panel>
        <Panel title="修改密码">
          <div className="psa-profile-form">
            {message && <Alert type="success" showIcon message={message} />}
            {error && <Alert type="error" showIcon message={error} />}
            <Form form={form} layout="vertical" onFinish={handlePasswordChange} requiredMark={false}>
              <Form.Item name="current_password" label="当前密码" rules={[{ required: true, message: '请输入当前密码' }]}>
                <Input.Password prefix={<LockOutlined />} autoComplete="current-password" />
              </Form.Item>
              <Form.Item
                name="new_password"
                label="新密码"
                rules={[
                  { required: true, message: '请输入新密码' },
                  { min: 8, message: '密码至少 8 位' },
                ]}
              >
                <Input.Password prefix={<LockOutlined />} autoComplete="new-password" />
              </Form.Item>
              <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={saving}>
                保存
              </Button>
            </Form>
          </div>
        </Panel>
      </div>
      <div className="psa-grid" style={{ marginTop: 16 }}>
        <Panel title="最近操作日志">
          <Table<AuditLogRecord>
            className="psa-table"
            size="small"
            rowKey="id"
            loading={logsLoading}
            pagination={false}
            dataSource={auditLogs}
            locale={{ emptyText: '暂无操作日志' }}
            columns={[
              { title: '动作', dataIndex: 'action', render: (value) => value || '操作' },
              { title: '对象', render: (_, record) => `${record.target_type || 'system'} ${record.target_id || ''}` },
              { title: '说明', dataIndex: 'note', render: (value) => value || '暂无' },
              { title: '时间', dataIndex: 'created_at', render: (value) => formatDateTime(value) },
            ]}
          />
        </Panel>
      </div>
    </ModuleFrame>
  );
};

export default Profile;
