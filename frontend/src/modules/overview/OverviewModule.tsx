import React, { useCallback, useState } from 'react';
import {
  AlertOutlined,
  ApiOutlined,
  BarChartOutlined,
  RadarChartOutlined,
} from '@ant-design/icons';
import { ModuleFrame, SubView } from '@/components/DesignSystem';
import { useSubView } from '@/hooks/useSubView';
import RealtimeView from './views/RealtimeView';
import PlatformsView from './views/PlatformsView';
import AlertsView from './views/AlertsView';
import QualityView from './views/QualityView';
import { OverviewSyncState } from './types';
import './overview.css';

const views: SubView[] = [
  { key: 'realtime', label: '实时概览', icon: <BarChartOutlined /> },
  { key: 'platforms', label: '平台监测', icon: <ApiOutlined /> },
  { key: 'alerts', label: '预警中心', icon: <AlertOutlined /> },
  { key: 'quality', label: '数据质量', icon: <RadarChartOutlined /> },
];

type OverviewViewKey = 'realtime' | 'platforms' | 'alerts' | 'quality';

/** 总览模块壳：子视图切换 + 顶栏刷新信号分发 + 同步状态聚合 */
const OverviewModule: React.FC = () => {
  const [activeView, setActiveView] = useSubView(['realtime', 'platforms', 'alerts', 'quality'] as const);
  const [refreshKey, setRefreshKey] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const handleRefresh = useCallback(() => setRefreshKey((key) => key + 1), []);

  const handleSyncState = useCallback((state: OverviewSyncState) => {
    setRefreshing(state.refreshing);
    if (state.lastUpdated) {
      setLastUpdated(state.lastUpdated);
    }
  }, []);

  return (
    <ModuleFrame
      moduleLabel="总览"
      activeView={activeView}
      views={views}
      onViewChange={(key) => setActiveView(key as OverviewViewKey)}
      onRefresh={handleRefresh}
      refreshing={refreshing}
      lastUpdated={lastUpdated}
    >
      {activeView === 'realtime' && <RealtimeView refreshKey={refreshKey} onSyncState={handleSyncState} />}
      {activeView === 'platforms' && <PlatformsView refreshKey={refreshKey} onSyncState={handleSyncState} />}
      {activeView === 'alerts' && <AlertsView refreshKey={refreshKey} onSyncState={handleSyncState} />}
      {activeView === 'quality' && <QualityView refreshKey={refreshKey} onSyncState={handleSyncState} />}
    </ModuleFrame>
  );
};

export default OverviewModule;
