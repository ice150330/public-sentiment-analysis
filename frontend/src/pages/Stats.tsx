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
  CrawlLog,
  CrawlStatus,
  getCrawlLogs,
  getCrawlStatus,
  getErrorMessage,
  getPlatforms,
  Platform,
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
  SectionNotice,
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
      setLogs(logsRes.data || []);
      setLastUpdated(new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }));
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

const AlertRules: React.FC = () => (
  <div className="psa-grid two-one">
    <Panel title="预警规则" className="tall">
      <SectionNotice
        title="后端尚未提供预警规则接口"
        description="UI.pen 中包含规则配置页面；当前接口集中在平台、热榜、情感、统计和爬虫控制，不能填充虚构规则。"
      />
      <DataState empty emptyTitle="暂无预警规则" emptyDescription="接入真实规则 API 后，此处提供规则列表、阈值与启停控制。">
        <div />
      </DataState>
    </Panel>
    <Panel title="规则运行状态">
      <DataState empty emptyTitle="暂无规则运行数据" emptyDescription="当前没有规则执行日志接口。">
        <div />
      </DataState>
    </Panel>
  </div>
);

const SystemLogs: React.FC = () => (
  <div className="psa-grid two-one">
    <Panel title="系统日志" className="tall">
      <SectionNotice
        title="后端尚未提供系统日志接口"
        description="当前可查询的是采集日志；系统级日志、审计日志和操作记录尚未在 API 中暴露。"
      />
      <DataState empty emptyTitle="暂无系统日志" emptyDescription="接入真实日志 API 后，此处展示日志级别、来源模块和时间线。">
        <div />
      </DataState>
    </Panel>
    <Panel title="日志筛选">
      <DataState empty emptyTitle="暂无筛选项" emptyDescription="筛选条件需要与真实日志字段保持一致。">
        <div />
      </DataState>
    </Panel>
  </div>
);

export default Stats;
