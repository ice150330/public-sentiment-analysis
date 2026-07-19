import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Input, InputNumber, message, Modal, Switch, Table, Tooltip } from 'antd';
import {
  ApiOutlined,
  CheckCircleOutlined,
  CodeOutlined,
  StopOutlined,
} from '@ant-design/icons';
import {
  getErrorMessage,
  getPlatforms,
  Platform,
  updatePlatform,
} from '@/services/api';
import {
  DataState,
  formatNumber,
  MetricCard,
  Panel,
  PlatformBadge,
} from '@/components/DesignSystem';
import { AdminViewProps } from '../types';

/** 平台配置 —— 指标卡 + 平台表格（开关 / 排序 / crawl_config JSON 编辑） */
const PlatformsView: React.FC<AdminViewProps> = ({ refreshKey, onSyncState }) => {
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [loading, setLoading] = useState(true);
  const [actingId, setActingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [configTarget, setConfigTarget] = useState<Platform | null>(null);
  const [configText, setConfigText] = useState('');
  const [configSaving, setConfigSaving] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      onSyncState({ refreshing: true });
      const res = await getPlatforms();
      setPlatforms(res.data || []);
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

  const activeCount = useMemo(() => platforms.filter((item) => item.is_active).length, [platforms]);

  const patchPlatform = useCallback(
    async (target: Platform, patch: Partial<Platform>, successText: string) => {
      try {
        setActingId(target.id);
        const res = await updatePlatform(target.id, patch);
        setPlatforms((current) => current.map((item) => (item.id === target.id ? res.data : item)));
        message.success(successText);
      } catch (err) {
        message.error(getErrorMessage(err));
      } finally {
        setActingId(null);
      }
    },
    [],
  );

  const openConfigModal = useCallback((target: Platform) => {
    setConfigTarget(target);
    setConfigText(target.crawl_config ? JSON.stringify(target.crawl_config, null, 2) : '');
  }, []);

  const saveConfig = useCallback(async () => {
    if (!configTarget) return;
    const trimmed = configText.trim();
    let parsed: Record<string, unknown> | null = null;
    if (trimmed) {
      try {
        parsed = JSON.parse(trimmed) as Record<string, unknown>;
      } catch {
        message.error('JSON 格式错误，请检查后再保存');
        return;
      }
    }
    try {
      setConfigSaving(true);
      const res = await updatePlatform(configTarget.id, { crawl_config: parsed });
      setPlatforms((current) => current.map((item) => (item.id === configTarget.id ? res.data : item)));
      message.success(`已保存「${configTarget.display_name}」的采集配置`);
      setConfigTarget(null);
    } catch (err) {
      message.error(getErrorMessage(err));
    } finally {
      setConfigSaving(false);
    }
  }, [configTarget, configText]);

  return (
    <DataState loading={loading} error={error} empty={platforms.length === 0} emptyTitle="暂无平台配置">
      <div className="ad-stack">
        <div className="ad-grid-3">
          <MetricCard
            label="接入平台"
            value={formatNumber(platforms.length)}
            helper="已配置的采集平台总数"
            icon={<ApiOutlined />}
          />
          <MetricCard
            label="启用平台"
            value={formatNumber(activeCount)}
            helper="正在参与采集"
            icon={<CheckCircleOutlined />}
            tone="positive"
          />
          <MetricCard
            label="停用平台"
            value={formatNumber(platforms.length - activeCount)}
            helper="已暂停采集"
            icon={<StopOutlined />}
            tone={platforms.length - activeCount > 0 ? 'warning' : 'neutral'}
          />
        </div>

        <Panel title="平台配置" eyebrow={`${formatNumber(activeCount)} 个平台启用中`}>
          <Table<Platform>
            className="psa-table"
            size="middle"
            rowKey="id"
            pagination={false}
            dataSource={platforms}
            locale={{ emptyText: '暂无平台配置' }}
            columns={[
              {
                title: '平台',
                key: 'platform',
                render: (_, record) => (
                  <div className="psa-inline-tools">
                    <PlatformBadge name={record.name} />
                    <strong>{record.display_name}</strong>
                  </div>
                ),
              },
              {
                title: '站点',
                dataIndex: 'base_url',
                ellipsis: true,
                render: (value) =>
                  value ? (
                    <Tooltip title={value}>
                      <span className="ad-code">{value}</span>
                    </Tooltip>
                  ) : (
                    '未配置'
                  ),
              },
              {
                title: '启用',
                dataIndex: 'is_active',
                width: 90,
                render: (value: boolean, record) => (
                  <Switch
                    checked={value}
                    loading={actingId === record.id}
                    onChange={(checked) =>
                      patchPlatform(record, { is_active: checked }, checked ? `已启用「${record.display_name}」` : `已停用「${record.display_name}」`)
                    }
                  />
                ),
              },
              {
                title: '排序',
                dataIndex: 'sort_order',
                width: 110,
                render: (value: number, record) => (
                  <InputNumber
                    key={`${record.id}-${value}`}
                    size="small"
                    min={0}
                    defaultValue={value}
                    disabled={actingId === record.id}
                    onBlur={(event) => {
                      const next = Number(event.target.value);
                      if (Number.isFinite(next) && next !== value) {
                        patchPlatform(record, { sort_order: next }, `已更新「${record.display_name}」排序`);
                      }
                    }}
                    onPressEnter={(event) => event.currentTarget.blur()}
                  />
                ),
              },
              {
                title: '采集配置',
                key: 'crawl_config',
                width: 130,
                render: (_, record) => (
                  <Button
                    size="small"
                    icon={<CodeOutlined />}
                    onClick={() => openConfigModal(record)}
                  >
                    {record.crawl_config ? '查看 / 编辑' : '配置'}
                  </Button>
                ),
              },
            ]}
          />
        </Panel>
      </div>

      <Modal
        title={configTarget ? `采集配置 — ${configTarget.display_name}` : '采集配置'}
        open={!!configTarget}
        onCancel={() => setConfigTarget(null)}
        onOk={saveConfig}
        okText="保存"
        cancelText="取消"
        confirmLoading={configSaving}
        destroyOnClose
      >
        <p className="psa-page-note">JSON 格式，留空表示清除自定义配置；保存时会校验格式。</p>
        <Input.TextArea
          className="ad-json-input"
          rows={10}
          value={configText}
          onChange={(event) => setConfigText(event.target.value)}
          placeholder={'{\n  "keywords": ["示例"],\n  "max_pages": 3\n}'}
        />
      </Modal>
    </DataState>
  );
};

export default PlatformsView;
