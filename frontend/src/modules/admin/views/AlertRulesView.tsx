import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Button,
  Form,
  Input,
  InputNumber,
  message,
  Modal,
  Popconfirm,
  Select,
  Switch,
  Table,
  Tooltip,
} from 'antd';
import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  SafetyOutlined,
} from '@ant-design/icons';
import {
  AlertRule,
  createAlertRule,
  deleteAlertRule,
  getAlertRules,
  getErrorMessage,
  patchAlertRule,
  updateAlertRule,
} from '@/services/api';
import {
  DataState,
  formatNumber,
  MetricCard,
  Panel,
} from '@/components/DesignSystem';
import SeverityTag from '@/modules/overview/components/SeverityTag';
import { AdminViewProps } from '../types';

/** 后端 alert_engine 已知的条件类型 */
const CONDITION_TYPE_OPTIONS = [
  { value: 'heat_spike', label: 'heat_spike（热度飙升）' },
  { value: 'negative_ratio', label: 'negative_ratio（负面占比）' },
  { value: 'low_confidence', label: 'low_confidence（低置信聚集）' },
  { value: 'volume_spike', label: 'volume_spike（声量激增）' },
];

const SEVERITY_OPTIONS = ['P1', 'P2', 'P3', 'P4'].map((value) => ({ value, label: value }));

interface RuleFormValues {
  name: string;
  description?: string;
  severity: AlertRule['severity'];
  condition_type: string;
  condition_expr: string;
  platform_scope: string;
  cooldown_minutes: number;
  is_active: boolean;
}

/** 预警规则 —— 规则表格 + 新建/编辑 Modal + 启停开关 + 删除 */
const AlertRulesView: React.FC<AdminViewProps> = ({ refreshKey, onSyncState }) => {
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [actingId, setActingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<AlertRule | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm<RuleFormValues>();

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      onSyncState({ refreshing: true });
      const res = await getAlertRules({ page: 1, page_size: 100 });
      setRules(res.data?.items || []);
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

  const activeCount = useMemo(() => rules.filter((rule) => rule.is_active).length, [rules]);

  // 编辑时若规则类型不在已知列表，动态补入选项，保证旧数据可见
  const conditionTypeOptions = useMemo(() => {
    if (editing && !CONDITION_TYPE_OPTIONS.some((item) => item.value === editing.condition_type)) {
      return [...CONDITION_TYPE_OPTIONS, { value: editing.condition_type, label: `${editing.condition_type}（自定义）` }];
    }
    return CONDITION_TYPE_OPTIONS;
  }, [editing]);

  const openCreate = useCallback(() => {
    setEditing(null);
    setModalOpen(true);
  }, []);

  const openEdit = useCallback((rule: AlertRule) => {
    setEditing(rule);
    setModalOpen(true);
  }, []);

  const handleSave = useCallback(async () => {
    let values: RuleFormValues;
    try {
      values = await form.validateFields();
    } catch {
      return; // 校验失败，antd 已在表单项上展示错误
    }
    try {
      setSaving(true);
      const payload: Partial<AlertRule> = {
        name: values.name.trim(),
        description: values.description?.trim() || null,
        severity: values.severity,
        condition_type: values.condition_type,
        condition_expr: values.condition_expr.trim(),
        platform_scope: values.platform_scope.trim() || 'all',
        cooldown_minutes: values.cooldown_minutes,
        is_active: values.is_active,
      };
      if (editing) {
        await updateAlertRule(editing.id, payload);
        message.success(`规则「${payload.name}」已更新`);
      } else {
        await createAlertRule(payload);
        message.success(`规则「${payload.name}」已创建`);
      }
      setModalOpen(false);
      await fetchData();
    } catch (err) {
      message.error(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }, [editing, form, fetchData]);

  const toggleActive = useCallback(
    async (rule: AlertRule, isActive: boolean) => {
      try {
        setActingId(rule.id);
        await patchAlertRule(rule.id, { is_active: isActive });
        setRules((current) =>
          current.map((item) => (item.id === rule.id ? { ...item, is_active: isActive } : item)),
        );
        message.success(isActive ? `已启用「${rule.name}」` : `已停用「${rule.name}」`);
      } catch (err) {
        message.error(getErrorMessage(err));
      } finally {
        setActingId(null);
      }
    },
    [],
  );

  const handleDelete = useCallback(
    async (rule: AlertRule) => {
      try {
        setActingId(rule.id);
        await deleteAlertRule(rule.id);
        message.success(`规则「${rule.name}」已删除`);
        await fetchData();
      } catch (err) {
        message.error(getErrorMessage(err));
      } finally {
        setActingId(null);
      }
    },
    [fetchData],
  );

  return (
    <DataState loading={loading} error={error} empty={rules.length === 0} emptyTitle="暂无预警规则">
      <div className="ad-stack">
        <div className="ad-grid-3">
          <MetricCard
            label="规则总数"
            value={formatNumber(rules.length)}
            helper="已配置的预警规则"
            icon={<SafetyOutlined />}
          />
          <MetricCard
            label="启用规则"
            value={formatNumber(activeCount)}
            helper="正在参与实时评估"
            tone="positive"
          />
          <MetricCard
            label="停用规则"
            value={formatNumber(rules.length - activeCount)}
            helper="已暂停评估"
            tone={rules.length - activeCount > 0 ? 'warning' : 'neutral'}
          />
        </div>

        <Panel
          title="预警规则"
          eyebrow={`${formatNumber(activeCount)} 条启用`}
          extra={(
            <Button type="primary" size="small" icon={<PlusOutlined />} onClick={openCreate}>
              新建规则
            </Button>
          )}
        >
          <Table<AlertRule>
            className="psa-table"
            size="middle"
            rowKey="id"
            pagination={false}
            dataSource={rules}
            locale={{ emptyText: '暂无预警规则' }}
            columns={[
              {
                title: '规则名称',
                dataIndex: 'name',
                ellipsis: true,
                render: (value, record) => (
                  <Tooltip title={record.description || undefined}>{value}</Tooltip>
                ),
              },
              {
                title: '级别',
                dataIndex: 'severity',
                width: 80,
                render: (value) => <SeverityTag severity={value} />,
              },
              {
                title: '条件类型',
                dataIndex: 'condition_type',
                render: (value) => <span className="ad-code">{value}</span>,
              },
              {
                title: '条件表达式',
                dataIndex: 'condition_expr',
                ellipsis: true,
                render: (value) => (
                  <Tooltip title={<span className="ad-code">{value}</span>}>
                    <span className="ad-code">{value}</span>
                  </Tooltip>
                ),
              },
              {
                title: '平台范围',
                dataIndex: 'platform_scope',
                width: 110,
                render: (value) => value || 'all',
              },
              {
                title: '冷却',
                dataIndex: 'cooldown_minutes',
                width: 80,
                align: 'right',
                render: (value) => `${value}m`,
              },
              {
                title: '启用',
                dataIndex: 'is_active',
                width: 80,
                render: (value: boolean, record) => (
                  <Switch
                    checked={value}
                    loading={actingId === record.id}
                    onChange={(checked) => toggleActive(record, checked)}
                  />
                ),
              },
              {
                title: '操作',
                key: 'actions',
                width: 130,
                render: (_, record) => (
                  <div className="psa-inline-tools">
                    <Button size="small" type="text" icon={<EditOutlined />} onClick={() => openEdit(record)}>
                      编辑
                    </Button>
                    <Popconfirm
                      title="删除规则"
                      description={`确定删除「${record.name}」吗？`}
                      okText="删除"
                      cancelText="取消"
                      okButtonProps={{ danger: true, loading: actingId === record.id }}
                      onConfirm={() => handleDelete(record)}
                    >
                      <Button size="small" type="text" danger icon={<DeleteOutlined />} />
                    </Popconfirm>
                  </div>
                ),
              },
            ]}
          />
        </Panel>
      </div>

      <Modal
        title={editing ? `编辑规则 — ${editing.name}` : '新建预警规则'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSave}
        okText={editing ? '保存' : '创建'}
        cancelText="取消"
        confirmLoading={saving}
        destroyOnClose
        width={560}
      >
        <Form<RuleFormValues>
          form={form}
          layout="vertical"
          requiredMark={false}
          preserve={false}
          initialValues={
            editing
              ? {
                  name: editing.name,
                  description: editing.description || '',
                  severity: editing.severity,
                  condition_type: editing.condition_type,
                  condition_expr: editing.condition_expr,
                  platform_scope: editing.platform_scope,
                  cooldown_minutes: editing.cooldown_minutes,
                  is_active: editing.is_active,
                }
              : {
                  name: '',
                  description: '',
                  severity: 'P3',
                  condition_type: 'heat_spike',
                  condition_expr: '',
                  platform_scope: 'all',
                  cooldown_minutes: 60,
                  is_active: true,
                }
          }
        >
          <Form.Item
            name="name"
            label="规则名称"
            rules={[{ required: true, message: '请输入规则名称' }]}
          >
            <Input placeholder="例如：微博负面舆情飙升" maxLength={64} />
          </Form.Item>
          <Form.Item name="description" label="规则描述">
            <Input.TextArea rows={2} placeholder="规则的用途说明（可选）" maxLength={200} />
          </Form.Item>
          <div className="psa-inline-tools" style={{ gap: 16, alignItems: 'flex-start' }}>
            <Form.Item
              name="severity"
              label="预警级别"
              rules={[{ required: true, message: '请选择级别' }]}
              style={{ flex: 1 }}
            >
              <Select options={SEVERITY_OPTIONS} />
            </Form.Item>
            <Form.Item
              name="condition_type"
              label="条件类型"
              rules={[{ required: true, message: '请选择条件类型' }]}
              style={{ flex: 2 }}
            >
              <Select options={conditionTypeOptions} />
            </Form.Item>
          </div>
          <Form.Item
            name="condition_expr"
            label="条件表达式（JSON）"
            rules={[
              { required: true, message: '请输入条件表达式' },
              {
                validator: (_, value: string) => {
                  if (!value?.trim()) return Promise.resolve();
                  try {
                    JSON.parse(value);
                    return Promise.resolve();
                  } catch {
                    return Promise.reject(new Error('JSON 格式错误'));
                  }
                },
              },
            ]}
          >
            <Input.TextArea
              className="ad-json-input"
              rows={4}
              placeholder={'{"threshold": 80, "window_minutes": 30}'}
            />
          </Form.Item>
          <div className="psa-inline-tools" style={{ gap: 16, alignItems: 'flex-start' }}>
            <Form.Item
              name="platform_scope"
              label="平台范围"
              tooltip="英文标识逗号分隔，all 表示全部平台"
              style={{ flex: 2 }}
            >
              <Input placeholder="all 或 weibo,douyin" />
            </Form.Item>
            <Form.Item
              name="cooldown_minutes"
              label="冷却时间（分钟）"
              rules={[{ required: true, message: '请设置冷却时间' }]}
              style={{ flex: 1 }}
            >
              <InputNumber min={0} max={10080} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="is_active" label="启用" valuePropName="checked" style={{ flex: 1 }}>
              <Switch />
            </Form.Item>
          </div>
        </Form>
      </Modal>
    </DataState>
  );
};

export default AlertRulesView;
