import React, { useCallback, useState } from 'react';
import {
  BranchesOutlined,
  FireOutlined,
  PartitionOutlined,
} from '@ant-design/icons';
import { ModuleFrame, SubView } from '@/components/DesignSystem';
import { useSubView } from '@/hooks/useSubView';
import TopicListView from './views/TopicListView';
import ClustersView from './views/ClustersView';
import PropagationView from './views/PropagationView';
import { HotspotsSyncState } from './types';
import './hotspots.css';

const views: SubView[] = [
  { key: 'list', label: '热榜列表', icon: <FireOutlined /> },
  { key: 'clusters', label: '聚类主题', icon: <PartitionOutlined /> },
  { key: 'spread', label: '传播路径', icon: <BranchesOutlined /> },
];

type HotspotsViewKey = 'list' | 'clusters' | 'spread';

/** 热点模块壳：子视图切换 + 顶栏刷新信号分发 + 同步状态聚合 */
const HotspotsModule: React.FC = () => {
  const [activeView, setActiveView] = useSubView(['list', 'clusters', 'spread'] as const);
  const [refreshKey, setRefreshKey] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const handleRefresh = useCallback(() => setRefreshKey((key) => key + 1), []);

  const handleSyncState = useCallback((state: HotspotsSyncState) => {
    setRefreshing(state.refreshing);
    if (state.lastUpdated) {
      setLastUpdated(state.lastUpdated);
    }
  }, []);

  return (
    <ModuleFrame
      moduleLabel="热点"
      activeView={activeView}
      views={views}
      onViewChange={(key) => setActiveView(key as HotspotsViewKey)}
      onRefresh={handleRefresh}
      refreshing={refreshing}
      lastUpdated={lastUpdated}
    >
      {activeView === 'list' && <TopicListView refreshKey={refreshKey} onSyncState={handleSyncState} />}
      {activeView === 'clusters' && <ClustersView refreshKey={refreshKey} onSyncState={handleSyncState} />}
      {activeView === 'spread' && <PropagationView refreshKey={refreshKey} onSyncState={handleSyncState} />}
    </ModuleFrame>
  );
};

export default HotspotsModule;
