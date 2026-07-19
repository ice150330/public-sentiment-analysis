/** 总览模块各子视图共享的 props：模块壳通过 refreshKey 触发刷新，子视图回同步加载状态。 */
export interface OverviewSyncState {
  refreshing: boolean;
  lastUpdated?: string | null;
}

export interface OverviewViewProps {
  refreshKey: number;
  onSyncState: (state: OverviewSyncState) => void;
}
