/** 管理模块各子视图共享的 props：模块壳通过 refreshKey 触发刷新，子视图回同步加载状态。 */
export interface AdminSyncState {
  refreshing: boolean;
  lastUpdated?: string | null;
}

export interface AdminViewProps {
  refreshKey: number;
  onSyncState: (state: AdminSyncState) => void;
}
