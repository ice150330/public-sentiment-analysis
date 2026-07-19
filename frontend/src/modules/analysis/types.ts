/** 分析模块各子视图共享的 props：模块壳通过 refreshKey 触发刷新，子视图回同步加载状态。 */
export interface AnalysisSyncState {
  refreshing: boolean;
  lastUpdated?: string | null;
}

export interface AnalysisViewProps {
  refreshKey: number;
  onSyncState: (state: AnalysisSyncState) => void;
}
