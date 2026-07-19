import React, { useCallback, useState } from 'react';
import {
  ExperimentOutlined,
  FileTextOutlined,
  SafetyOutlined,
  SettingOutlined,
  SyncOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { ModuleFrame, SubView } from '@/components/DesignSystem';
import { useSubView } from '@/hooks/useSubView';
import PlatformsView from './views/PlatformsView';
import CrawlerView from './views/CrawlerView';
import AlertRulesView from './views/AlertRulesView';
import LogsView from './views/LogsView';
import UsersView from './views/UsersView';
import ModelView from './views/ModelView';
import { AdminSyncState } from './types';
import './admin.css';

const views: SubView[] = [
  { key: 'platforms', label: '平台配置', icon: <SettingOutlined /> },
  { key: 'crawler', label: '采集任务', icon: <SyncOutlined /> },
  { key: 'rules', label: '预警规则', icon: <SafetyOutlined /> },
  { key: 'logs', label: '系统日志', icon: <FileTextOutlined /> },
  { key: 'users', label: '用户权限', icon: <TeamOutlined /> },
  { key: 'model', label: '模型管理', icon: <ExperimentOutlined /> },
];

type AdminViewKey = 'platforms' | 'crawler' | 'rules' | 'logs' | 'users' | 'model';

/** 管理模块壳：子视图切换 + 顶栏刷新信号分发 + 同步状态聚合（admin 权限由路由层保证） */
const AdminModule: React.FC = () => {
  const [activeView, setActiveView] = useSubView(['platforms', 'crawler', 'rules', 'logs', 'users', 'model'] as const);
  const [refreshKey, setRefreshKey] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const handleRefresh = useCallback(() => setRefreshKey((key) => key + 1), []);

  const handleSyncState = useCallback((state: AdminSyncState) => {
    setRefreshing(state.refreshing);
    if (state.lastUpdated) {
      setLastUpdated(state.lastUpdated);
    }
  }, []);

  return (
    <ModuleFrame
      moduleLabel="管理"
      activeView={activeView}
      views={views}
      onViewChange={(key) => setActiveView(key as AdminViewKey)}
      onRefresh={handleRefresh}
      refreshing={refreshing}
      lastUpdated={lastUpdated}
    >
      {activeView === 'platforms' && <PlatformsView refreshKey={refreshKey} onSyncState={handleSyncState} />}
      {activeView === 'crawler' && <CrawlerView refreshKey={refreshKey} onSyncState={handleSyncState} />}
      {activeView === 'rules' && <AlertRulesView refreshKey={refreshKey} onSyncState={handleSyncState} />}
      {activeView === 'logs' && <LogsView refreshKey={refreshKey} onSyncState={handleSyncState} />}
      {activeView === 'users' && <UsersView refreshKey={refreshKey} onSyncState={handleSyncState} />}
      {activeView === 'model' && <ModelView refreshKey={refreshKey} onSyncState={handleSyncState} />}
    </ModuleFrame>
  );
};

export default AdminModule;
