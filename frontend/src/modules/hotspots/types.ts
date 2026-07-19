/** 热点模块各子视图共享的 props：模块壳通过 refreshKey 触发刷新，子视图回同步加载状态。 */
export interface HotspotsSyncState {
  refreshing: boolean;
  lastUpdated?: string | null;
}

export interface HotspotsViewProps {
  refreshKey: number;
  onSyncState: (state: HotspotsSyncState) => void;
}
