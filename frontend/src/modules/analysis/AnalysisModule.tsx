import React, { useCallback, useState } from 'react';
import {
  AreaChartOutlined,
  FileSearchOutlined,
  ScanOutlined,
  TableOutlined,
} from '@ant-design/icons';
import { ModuleFrame, SubView } from '@/components/DesignSystem';
import { useSubView } from '@/hooks/useSubView';
import TextView from './views/TextView';
import BatchView from './views/BatchView';
import ForecastView from './views/ForecastView';
import ExplainView from './views/ExplainView';
import { AnalysisSyncState } from './types';
import './analysis.css';

const views: SubView[] = [
  { key: 'text', label: '文本分析', icon: <FileSearchOutlined /> },
  { key: 'batch', label: '批量结果', icon: <TableOutlined /> },
  { key: 'forecast', label: '趋势预测', icon: <AreaChartOutlined /> },
  { key: 'explain', label: '模型解释', icon: <ScanOutlined /> },
];

type AnalysisViewKey = 'text' | 'batch' | 'forecast' | 'explain';

/** 分析模块壳：子视图切换 + 顶栏刷新信号分发 + 同步状态聚合 */
const AnalysisModule: React.FC = () => {
  const [activeView, setActiveView] = useSubView(['text', 'batch', 'forecast', 'explain'] as const);
  const [refreshKey, setRefreshKey] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const handleRefresh = useCallback(() => setRefreshKey((key) => key + 1), []);

  const handleSyncState = useCallback((state: AnalysisSyncState) => {
    setRefreshing(state.refreshing);
    if (state.lastUpdated) {
      setLastUpdated(state.lastUpdated);
    }
  }, []);

  return (
    <ModuleFrame
      moduleLabel="分析"
      activeView={activeView}
      views={views}
      onViewChange={(key) => setActiveView(key as AnalysisViewKey)}
      onRefresh={handleRefresh}
      refreshing={refreshing}
      lastUpdated={lastUpdated}
    >
      {activeView === 'text' && <TextView refreshKey={refreshKey} onSyncState={handleSyncState} />}
      {activeView === 'batch' && <BatchView refreshKey={refreshKey} onSyncState={handleSyncState} />}
      {activeView === 'forecast' && <ForecastView refreshKey={refreshKey} onSyncState={handleSyncState} />}
      {activeView === 'explain' && <ExplainView refreshKey={refreshKey} onSyncState={handleSyncState} />}
    </ModuleFrame>
  );
};

export default AnalysisModule;
