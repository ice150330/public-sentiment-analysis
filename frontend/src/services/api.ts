import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export interface UnifiedResponse<T> {
  code: number;
  data: T;
  message: string;
  request_id?: string | null;
}

export type AuthRole = 'admin' | 'analyst' | 'visitor';

export interface AuthUser {
  id: number;
  username: string;
  email?: string | null;
  role: AuthRole;
  platform_scope: string;
  is_active: boolean;
}

export interface AuthSession {
  access_token: string;
  token_type: 'bearer' | string;
  expires_at: string;
  user: AuthUser;
}

export interface Platform {
  id: number;
  name: string;
  display_name: string;
  base_url?: string | null;
  crawl_config?: Record<string, unknown> | null;
  is_active: boolean;
  sort_order: number;
  created_at?: string;
  updated_at?: string;
}

export interface Pagination {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface HotTopic {
  id: number;
  platform_id: number;
  topic_id: string;
  title: string;
  url?: string | null;
  heat_score?: number | null;
  category?: string | null;
  content_summary?: string | null;
  raw_data?: Record<string, unknown> | null;
  crawl_time: string;
  created_at: string;
  platform_name?: string | null;
}

export interface HotTopicList {
  items: HotTopic[];
  pagination: Pagination;
}

export interface TopicClusterSummary {
  id: number;
  cluster_name: string;
  description?: string | null;
  algorithm: string;
  params?: Record<string, unknown>;
  keywords?: string[];
  embedding_provider?: string | null;
  topic_count: number;
  avg_sentiment?: number | null;
  dominant_sentiment?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  created_at?: string | null;
}

export interface TopicClusterMember {
  id: number;
  topic_id: number;
  topic_title?: string | null;
  platform_name?: string | null;
  weight?: number | null;
  distance_to_center?: number | null;
  features?: Record<string, unknown>;
  heat_score?: number | null;
  sentiment_label?: string | null;
  crawl_time?: string | null;
}

export interface TopicClusterDetail {
  cluster: TopicClusterSummary;
  members: TopicClusterMember[];
  representative_members?: TopicClusterMember[];
  pagination: Pagination;
}

export interface TopicClusterRunResult {
  clusters: Array<{
    id: number;
    name?: string;
    cluster_name: string;
    topic_count: number;
    keywords?: string[];
    dominant_sentiment?: string | null;
  }>;
  total_topics: number;
  algorithm: string;
  embedding_provider?: string | null;
  keywords_method?: string | null;
}

export interface TopicQuery {
  platform?: string;
  keyword?: string;
  start_time?: string;
  end_time?: string;
  category?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

export interface SentimentScores {
  positive: number;
  negative: number;
  neutral: number;
}

export interface SentimentAnalyzeResult {
  text: string;
  sentiment_label: 'positive' | 'negative' | 'neutral' | string;
  confidence: number;
  scores: SentimentScores;
  model_version?: string | null;
  analyzed_at: string;
}

export interface SentimentResult {
  id: number;
  topic_id: number;
  sentiment_label: string;
  confidence: number;
  positive_score: number;
  negative_score: number;
  neutral_score: number;
  model_version?: string | null;
  analyzed_at: string;
  created_at: string;
}

export interface AlertRule {
  id: number;
  name: string;
  description?: string | null;
  condition_type: string;
  condition_expr: string;
  severity: 'P1' | 'P2' | 'P3' | 'P4';
  platform_scope: string;
  cooldown_minutes: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AlertEvent {
  id: number;
  rule_id: number;
  rule_name?: string | null;
  topic_id?: number | null;
  topic_title?: string | null;
  severity: string;
  status: 'pending' | 'acknowledged' | 'resolved' | 'ignored';
  trigger_payload?: string | null;
  triggered_at: string;
  acknowledged_at?: string | null;
  resolved_at?: string | null;
}

export interface AlertSummary {
  pending_count: number;
  severity_distribution: Record<string, number>;
  max_severity?: string | null;
  today_count: number;
  latest_alert?: {
    id: number;
    severity: string;
    triggered_at: string;
  } | null;
}

export interface PlatformMonitoringMatrix {
  matrix: Array<{
    platform_id: number;
    platform_name: string;
    display_name: string;
    topic_count: number;
    avg_heat: number;
    negative_ratio: number;
    delay_minutes?: number | null;
    last_crawl?: string | null;
    status: string;
    is_healthy: boolean;
  }>;
  total_platforms: number;
  healthy_count: number;
}

export interface DataQualityFunnel {
  date: string;
  funnel: Array<{
    stage: string;
    count: number;
    loss: number;
    loss_rate: number;
  }>;
  retention_rate: number;
}

export interface DataQualityCheck {
  name: string;
  pass_rate?: number;
  count?: number;
  threshold: number;
  status: 'pass' | 'warning' | 'fail';
}

export interface DataQualityIssue {
  id: number;
  issue_type: string;
  platform_name?: string | null;
  topic_title?: string | null;
  severity: string;
  status: string;
  description?: string | null;
  suggestion?: string | null;
  created_at?: string | null;
  resolved_at?: string | null;
}

export interface SystemHealth {
  overall_status: string;
  components: Record<string, { status: string; message: string }>;
  checked_at: string;
}

export interface SystemLogRecord {
  id: number;
  level: string;
  module?: string | null;
  event?: string | null;
  message?: string | null;
  payload_json?: string | null;
  request_id?: string | null;
  created_at?: string | null;
}

export interface AuditLogRecord {
  id: number;
  operator: string;
  action?: string | null;
  target_type?: string | null;
  target_id?: string | null;
  before_json?: string | null;
  after_json?: string | null;
  note?: string | null;
  created_at?: string | null;
}

export interface DatabaseBackup {
  filename: string;
  size_bytes: number;
  created_at: string;
  download_url: string;
}

export interface ModelStatus {
  model: {
    version?: string | null;
    model_name?: string | null;
    device: string;
    is_loaded: boolean;
    provider?: string | null;
    traffic_percent?: number;
  };
  active_versions?: ModelVersion[];
  recent_analyzed: number;
  avg_confidence: number;
  confidence_distribution: {
    high: number;
    medium: number;
    low: number;
  };
  pending_review: number;
  status: string;
}

export interface ModelVersion {
  id: number;
  version: string;
  model_name: string;
  task_type?: string | null;
  device?: string | null;
  metrics_json?: string | null;
  config_json?: string | null;
  metrics?: Record<string, unknown>;
  config?: Record<string, unknown>;
  provider?: string;
  traffic_percent?: number;
  is_active: boolean;
  description?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SentimentReviewItem {
  id: number;
  sentiment_result_id: number;
  topic_id?: number | null;
  topic_title?: string | null;
  platform_name?: string | null;
  sentiment_label: string;
  original_label: string;
  suggested_label: string;
  corrected_label?: string | null;
  confidence: number;
  confidence_snapshot: number;
  status: 'pending' | 'reviewed' | 'ignored' | string;
  reviewer?: string | null;
  note?: string | null;
  analyzed_at?: string | null;
  reviewed_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  pagination: Pagination;
}

export interface TopicSample {
  id: number;
  platform_name?: string | null;
  sample_type?: string | null;
  content: string;
  sentiment_label?: string | null;
  confidence?: number | null;
  source_url?: string | null;
  author?: string | null;
  created_at: string;
}

export interface TopicRelation {
  id: number;
  target_topic_id: number;
  target_title?: string | null;
  relation_type?: string | null;
  score?: number | null;
  description?: string | null;
}

export interface PropagationNode {
  id: number | string;
  topic_id: number;
  topic_title?: string | null;
  platform_name?: string | null;
  level: number;
  parent_node_id?: number | string | null;
  heat_score?: number | null;
  sentiment_label?: string | null;
  influence_score?: number | null;
  similarity_score?: number | null;
  delay_hours?: number | null;
  match_method?: string | null;
  discovered_at?: string | null;
  children?: PropagationNode[];
}

export interface TopicPropagation {
  path: {
    id?: number | null;
    root_topic_id: number;
    root_topic_title?: string | null;
    depth: number;
    total_nodes: number;
    platforms_involved?: unknown;
  };
  nodes: PropagationNode[];
  edges: Array<Record<string, unknown>>;
}

export interface PropagationPathSummary {
  id: number;
  root_topic_id: number;
  root_topic_title?: string | null;
  depth: number;
  total_nodes: number;
  max_breadth: number;
  platforms_involved?: string[];
  platform_transitions: number;
  first_seen_at?: string | null;
  last_seen_at?: string | null;
  created_at?: string | null;
}

export interface PropagationPathDetail {
  path: PropagationPathSummary;
  tree: PropagationNode[];
  nodes: PropagationNode[];
  edges: Array<{
    source: number | string;
    target: number | string;
    similarity_score?: number | null;
    delay_hours?: number | null;
  }>;
}

export interface PropagationAnalyzeResult extends PropagationPathDetail {
  path_id: number;
  root_topic_id: number;
  root_topic_title?: string | null;
  depth: number;
  total_nodes: number;
  platforms_involved?: string[];
  platform_transitions: number;
}

export interface SentimentSummary {
  today_analyzed: number;
  total_analyzed: number;
  success_rate: number;
  low_confidence: number;
  negative_samples: number;
  avg_confidence: number;
  avg_latency_ms: number;
}

export interface ForecastHeatPoint {
  date: string;
  predicted_heat: number;
  predicted_value?: number;
  confidence_lower: number;
  confidence_upper: number;
}

export interface ForecastHeat {
  topic_id?: number | null;
  current_heat: number;
  forecast: ForecastHeatPoint[];
  model: string;
  metrics?: {
    mse?: number | null;
    mae?: number | null;
    mape?: number | null;
    r2_score?: number | null;
    backtest_points?: number;
  };
  signals?: Array<{
    name: string;
    value: number;
    change_rate?: number;
    direction: 'up' | 'down' | 'stable' | string;
    description?: string;
  }>;
}

export interface SentimentDistributionItem {
  label: string;
  count: number;
  percentage: number;
}

export interface SentimentDistribution {
  total: number;
  distribution: SentimentDistributionItem[];
  by_platform?: Record<string, Record<string, number>> | null;
}

export interface HeatTrendPoint {
  date: string;
  avg_heat: number;
  max_heat: number;
  topic_count: number;
}

export interface HeatTrendSeries {
  platform: string;
  data: HeatTrendPoint[];
}

export interface HeatTrend {
  period: string;
  aggregation: string;
  series: HeatTrendSeries[];
}

export interface CrawlSuccessRateItem {
  status: string;
  count: number;
  percentage: number;
}

export interface CrawlSuccessRate {
  period: string;
  total: number;
  rates: CrawlSuccessRateItem[];
}

export interface Overview {
  today: {
    total_topics: number;
    active_platforms: number;
    sentiment_distribution: Record<string, number>;
  };
  crawler: {
    last_run?: string | null;
    today_success_rate: number;
  };
  sentiment: {
    total_analyzed: number;
  };
}

export interface CrawlStatus {
  is_running: boolean;
  current_task?: {
    task_id: string;
    platforms: string[];
    started_at?: string | null;
    elapsed_seconds: number;
  } | null;
  queue_length: number;
}

export interface CrawlLog {
  id: number;
  platform_id: number;
  platform_name?: string | null;
  status: string;
  records_count: number;
  error_message?: string | null;
  started_at: string;
  completed_at?: string | null;
  duration_seconds?: number | null;
  created_at: string;
}

export interface CrawlerTriggerResult {
  task_id: string;
  status: string;
  platforms: string[];
  started_at: string;
  results?: Record<string, unknown>;
}

export interface CrawlerScheduleConfig {
  interval_minutes: number;
  is_enabled: boolean;
}

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 12000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const AUTH_TOKEN_KEY = 'psa_access_token';

export const getAuthToken = () => {
  if (typeof window === 'undefined') return null;
  return window.localStorage.getItem(AUTH_TOKEN_KEY);
};

export const saveAuthToken = (token: string) => {
  window.localStorage.setItem(AUTH_TOKEN_KEY, token);
};

export const clearAuthToken = () => {
  window.localStorage.removeItem(AUTH_TOKEN_KEY);
};

api.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response.data,
  (error) => Promise.reject(error)
);

export const getPlatforms = () =>
  api.get<unknown, UnifiedResponse<Platform[]>>('/platforms');

export const updatePlatform = (id: number, update: Partial<Platform>) =>
  api.patch<unknown, UnifiedResponse<Platform>>(`/platforms/${id}`, update);

export const getTopics = (params?: TopicQuery) =>
  api.get<unknown, UnifiedResponse<HotTopicList>>('/topics', { params });

export const getTopic = (id: number) =>
  api.get<unknown, UnifiedResponse<HotTopic>>(`/topics/${id}`);

const compactParams = (params?: object) =>
  Object.fromEntries(
    Object.entries(params || {}).filter(([, value]) => value !== undefined && value !== null && value !== '')
  );

const downloadCsv = async (path: string, params: object | undefined, filenamePrefix: string) => {
  const token = getAuthToken();
  const response = await axios.get<Blob>(`${API_BASE_URL}/api/v1${path}`, {
    params: compactParams(params),
    responseType: 'blob',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  const timestamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
  const url = window.URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${filenamePrefix}-${timestamp}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

export const exportTopicsCsv = (params?: TopicQuery & { limit?: number }) =>
  downloadCsv('/exports/topics.csv', params, 'hot-topics');

export const exportAlertEventsCsv = (params?: {
  status?: string;
  severity?: string;
  rule_id?: number;
  start_time?: string;
  end_time?: string;
  limit?: number;
}) => downloadCsv('/exports/alerts.csv', params, 'alert-events');

export const exportSentimentReportPdf = async (params?: {
  platform?: string;
  start_time?: string;
  end_time?: string;
  topic_limit?: number;
}) => {
  const token = getAuthToken();
  const response = await axios.get<Blob>(`${API_BASE_URL}/api/v1/exports/sentiment-report.pdf`, {
    params: compactParams(params),
    responseType: 'blob',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  const timestamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
  const url = window.URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = url;
  link.download = `sentiment-report-${timestamp}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

export const login = (payload: { username: string; password: string }) =>
  api.post<unknown, UnifiedResponse<AuthSession>>('/auth/login', payload);

export const register = (payload: { username: string; password: string; email?: string }) =>
  api.post<unknown, UnifiedResponse<AuthSession>>('/auth/register', payload);

export const getCurrentUser = () =>
  api.get<unknown, UnifiedResponse<AuthUser>>('/auth/me');

export const changePassword = (payload: { current_password: string; new_password: string }) =>
  api.post<unknown, UnifiedResponse<{ id: number }>>('/auth/password', payload);

export const requestPasswordReset = (payload: { username?: string; email?: string }) =>
  api.post<unknown, UnifiedResponse<{ reset_token?: string | null; expires_at?: string | null }>>('/auth/password/reset/request', payload);

export const confirmPasswordReset = (payload: { token: string; new_password: string }) =>
  api.post<unknown, UnifiedResponse<{ id: number }>>('/auth/password/reset/confirm', payload);

export const getMyAuditLogs = (params?: { page?: number; page_size?: number }) =>
  api.get<unknown, UnifiedResponse<PaginatedResponse<AuditLogRecord>>>('/auth/audit-logs', { params });

export const getUsers = (params?: {
  role?: string;
  is_active?: boolean;
  keyword?: string;
  page?: number;
  page_size?: number;
}) => api.get<unknown, UnifiedResponse<PaginatedResponse<AuthUser>>>('/auth/users', { params });

export const updateUser = (id: number, payload: Partial<Pick<AuthUser, 'role' | 'platform_scope' | 'is_active'>>) =>
  api.patch<unknown, UnifiedResponse<AuthUser>>(`/auth/users/${id}`, payload);

export const analyzeText = (text: string) =>
  api.post<unknown, UnifiedResponse<SentimentAnalyzeResult>>('/sentiment/analyze', { text });

export const analyzeBatch = (texts: string[]) =>
  api.post<unknown, UnifiedResponse<SentimentAnalyzeResult[]>>('/sentiment/analyze/batch', { texts });

export const analyzeTextV2 = (text: string) =>
  api.post<unknown, UnifiedResponse<SentimentAnalyzeResult>>('/sentiment/v2/analyze', { text });

export const analyzeBatchV2 = (texts: string[]) =>
  api.post<unknown, UnifiedResponse<SentimentAnalyzeResult[]>>('/sentiment/v2/batch', { texts });

export const getSentimentResults = (params?: {
  label?: string;
  platform?: string;
  min_confidence?: number;
  start_time?: string;
  end_time?: string;
  page?: number;
  page_size?: number;
}) => api.get<unknown, UnifiedResponse<PaginatedResponse<SentimentResult>>>('/sentiment/results', { params });

export const getOverview = () =>
  api.get<unknown, UnifiedResponse<Overview>>('/stats/overview');

export const getSentimentDistribution = (params?: {
  platform?: string;
  start_time?: string;
  end_time?: string;
}) => api.get<unknown, UnifiedResponse<SentimentDistribution>>('/stats/sentiment-distribution', { params });

export const getHeatTrend = (params?: {
  days?: number;
  platform?: string;
  aggregation?: 'hourly' | 'daily' | 'weekly';
}) => api.get<unknown, UnifiedResponse<HeatTrend>>('/stats/heat-trend', { params });

export const getCrawlSuccessRate = (params?: { days?: number }) =>
  api.get<unknown, UnifiedResponse<CrawlSuccessRate>>('/stats/crawl-success-rate', { params });

export const triggerCrawler = (payload: { platforms?: string[]; is_async?: boolean }) =>
  api.post<unknown, UnifiedResponse<CrawlerTriggerResult>>('/crawler/trigger', payload);

export const getCrawlStatus = () =>
  api.get<unknown, UnifiedResponse<CrawlStatus>>('/crawler/status');

export const getCrawlLogs = (params?: {
  platform?: string;
  status?: string;
  start_time?: string;
  end_time?: string;
  page?: number;
  page_size?: number;
}) => api.get<unknown, UnifiedResponse<PaginatedResponse<CrawlLog>>>('/crawler/logs', { params });

export const getCrawlerSchedule = () =>
  api.get<unknown, UnifiedResponse<CrawlerScheduleConfig>>('/crawler/schedule');

export const updateCrawlerSchedule = (config: CrawlerScheduleConfig) =>
  api.put<unknown, UnifiedResponse<CrawlerScheduleConfig>>('/crawler/schedule', config);

// ========== 预警中心 ==========

export const getAlertRules = (params?: {
  is_active?: boolean;
  severity?: string;
  page?: number;
  page_size?: number;
}) => api.get<unknown, UnifiedResponse<PaginatedResponse<AlertRule>>>('/alerts/rules', { params });

export const getAlertRule = (id: number) =>
  api.get<unknown, UnifiedResponse<AlertRule>>(`/alerts/rules/${id}`);

export const createAlertRule = (data: Partial<AlertRule>) =>
  api.post<unknown, UnifiedResponse<{ id: number; name: string }>>('/alerts/rules', data);

export const updateAlertRule = (id: number, data: Partial<AlertRule>) =>
  api.put<unknown, UnifiedResponse<{ id: number; name: string }>>(`/alerts/rules/${id}`, data);

export const patchAlertRule = (id: number, data: Partial<AlertRule>) =>
  api.patch<unknown, UnifiedResponse<{ id: number; is_active: boolean }>>(`/alerts/rules/${id}`, data);

export const deleteAlertRule = (id: number) =>
  api.delete<unknown, UnifiedResponse<{ id: number }>>(`/alerts/rules/${id}`);

export const getAlertEvents = (params?: {
  status?: string;
  severity?: string;
  rule_id?: number;
  start_time?: string;
  end_time?: string;
  page?: number;
  page_size?: number;
}) => api.get<unknown, UnifiedResponse<PaginatedResponse<AlertEvent>>>('/alerts/events', { params });

export const getAlertEvent = (id: number) =>
  api.get<unknown, UnifiedResponse<AlertEvent>>(`/alerts/events/${id}`);

export const getAlertSummary = () =>
  api.get<unknown, UnifiedResponse<AlertSummary>>('/alerts/summary');

export const acknowledgeAlert = (id: number, note?: string) =>
  api.post<unknown, UnifiedResponse<{ id: number; status: string }>>(`/alerts/events/${id}/ack`, { note });

export const resolveAlert = (id: number, note?: string) =>
  api.post<unknown, UnifiedResponse<{ id: number; status: string }>>(`/alerts/events/${id}/resolve`, { note });

export const ignoreAlert = (id: number, note?: string) =>
  api.post<unknown, UnifiedResponse<{ id: number; status: string }>>(`/alerts/events/${id}/ignore`, { note });

// ========== 平台监测 ==========

export const getPlatformMonitoringMatrix = () =>
  api.get<unknown, UnifiedResponse<PlatformMonitoringMatrix>>('/platforms/monitoring/matrix');

export const getDataFreshness = () =>
  api.get<unknown, UnifiedResponse<Record<string, unknown>>>('/platforms/monitoring/freshness');

// ========== 数据质量 ==========

export const getDataQualityFunnel = (date?: string) =>
  api.get<unknown, UnifiedResponse<DataQualityFunnel>>('/data-quality/funnel', { params: { date } });

export const getDataQualityChecks = () =>
  api.get<unknown, UnifiedResponse<{ checks: DataQualityCheck[]; overall_score: number }>>('/data-quality/checks');

export const getDataQualityIssues = (params?: {
  issue_type?: string;
  severity?: string;
  status?: string;
  platform?: string;
  page?: number;
  page_size?: number;
}) => api.get<unknown, UnifiedResponse<PaginatedResponse<Record<string, unknown>>>>('/data-quality/issues', { params });

export const getTypedDataQualityIssues = (params?: {
  issue_type?: string;
  severity?: string;
  status?: string;
  platform?: string;
  page?: number;
  page_size?: number;
}) => api.get<unknown, UnifiedResponse<PaginatedResponse<DataQualityIssue>>>('/data-quality/issues', { params });

export const getDataQualitySummary = () =>
  api.get<unknown, UnifiedResponse<Record<string, unknown>>>('/data-quality/summary');

// ========== 系统管理 ==========

export const getSystemHealth = () =>
  api.get<unknown, UnifiedResponse<SystemHealth>>('/system/health');

export const getSystemLogs = (params?: {
  level?: string;
  module?: string;
  start_time?: string;
  end_time?: string;
  page?: number;
  page_size?: number;
}) => api.get<unknown, UnifiedResponse<PaginatedResponse<Record<string, unknown>>>>('/system/logs', { params });

export const getTypedSystemLogs = (params?: {
  level?: string;
  module?: string;
  start_time?: string;
  end_time?: string;
  page?: number;
  page_size?: number;
}) => api.get<unknown, UnifiedResponse<PaginatedResponse<SystemLogRecord>>>('/system/logs', { params });

export const getAuditLogs = (params?: {
  operator?: string;
  action?: string;
  target_type?: string;
  start_time?: string;
  end_time?: string;
  page?: number;
  page_size?: number;
}) => api.get<unknown, UnifiedResponse<PaginatedResponse<Record<string, unknown>>>>('/system/audit-logs', { params });

export const getTypedAuditLogs = (params?: {
  operator?: string;
  action?: string;
  target_type?: string;
  start_time?: string;
  end_time?: string;
  page?: number;
  page_size?: number;
}) => api.get<unknown, UnifiedResponse<PaginatedResponse<AuditLogRecord>>>('/system/audit-logs', { params });

export const createDatabaseBackup = () =>
  api.post<unknown, UnifiedResponse<DatabaseBackup>>('/system/database/backup');

export const getDatabaseBackups = () =>
  api.get<unknown, UnifiedResponse<{ items: DatabaseBackup[]; total: number }>>('/system/database/backups');

export const downloadDatabaseBackup = async (filename: string) => {
  const token = getAuthToken();
  const response = await axios.get<Blob>(
    `${API_BASE_URL}/api/v1/system/database/backups/${encodeURIComponent(filename)}`,
    {
      responseType: 'blob',
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    }
  );
  const url = window.URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

// ========== 模型管理 ==========

export const getModelStatus = () =>
  api.get<unknown, UnifiedResponse<ModelStatus>>('/model/status');

export const getModelVersions = (params?: { is_active?: boolean }) =>
  api.get<unknown, UnifiedResponse<{ items: ModelVersion[]; total: number }>>('/model/versions', { params });

export const activateModelVersion = (id: number, payload?: { traffic_percent?: number }) =>
  api.post<unknown, UnifiedResponse<ModelVersion>>(`/model/versions/${id}/activate`, payload || { traffic_percent: 100 });

export const getLowConfidenceResults = (params?: {
  threshold?: number;
  page?: number;
  page_size?: number;
}) => api.get<unknown, UnifiedResponse<PaginatedResponse<Record<string, unknown>>>>('/model/low-confidence', { params });

export const getSentimentReviewQueue = (params?: {
  threshold?: number;
  status?: string;
  page?: number;
  page_size?: number;
}) => api.get<unknown, UnifiedResponse<PaginatedResponse<SentimentReviewItem> & { threshold: number; created: number }>>('/model/review-queue', { params });

export const updateSentimentReviewItem = (
  id: number,
  payload: { status: 'pending' | 'reviewed' | 'ignored'; corrected_label?: string | null; note?: string | null }
) => api.patch<unknown, UnifiedResponse<SentimentReviewItem>>(`/model/review-queue/${id}`, payload);

// ========== 话题扩展 ==========

export const getTopicSamples = (topicId: number, params?: {
  platform?: string;
  sample_type?: string;
  page?: number;
  page_size?: number;
}) => api.get<unknown, UnifiedResponse<{ topic_id: number; topic_title: string; items: TopicSample[]; pagination: Pagination }>>(`/topic-ext/${topicId}/samples`, { params });

export const getRelatedTopics = (topicId: number, params?: { relation_type?: string }) =>
  api.get<unknown, UnifiedResponse<{ topic_id: number; topic_title: string; relations: TopicRelation[] }>>(`/topic-ext/${topicId}/related`, { params });

export const getTopicPropagation = (topicId: number) =>
  api.get<unknown, UnifiedResponse<TopicPropagation>>(`/topics/${topicId}/propagation`);

// ========== 主题聚类 ==========

export const getTopicClusters = (params?: {
  start_time?: string;
  end_time?: string;
  algorithm?: string;
  page?: number;
  page_size?: number;
}) => api.get<unknown, UnifiedResponse<PaginatedResponse<TopicClusterSummary>>>('/topic-clusters', { params });

export const getTopicCluster = (id: number, params?: { page?: number; page_size?: number }) =>
  api.get<unknown, UnifiedResponse<TopicClusterDetail>>(`/topic-clusters/${id}`, { params });

export const runClustering = (params?: {
  algorithm?: string;
  n_clusters?: number;
  time_window_hours?: number;
}) => api.post<unknown, UnifiedResponse<TopicClusterRunResult>>('/topic-clusters/run', { params });

// ========== 传播路径 ==========

export const getPropagationPaths = (params?: {
  root_topic_id?: number;
  platform?: string;
  start_time?: string;
  end_time?: string;
  page?: number;
  page_size?: number;
}) => api.get<unknown, UnifiedResponse<PaginatedResponse<PropagationPathSummary>>>('/propagation-paths', { params });

export const getPropagationPath = (id: number) =>
  api.get<unknown, UnifiedResponse<PropagationPathDetail>>(`/propagation-paths/${id}`);

export const analyzePropagation = (topicId: number, params?: {
  time_window_hours?: number;
  similarity_threshold?: number;
  max_nodes?: number;
}) => api.post<unknown, UnifiedResponse<PropagationAnalyzeResult>>(`/propagation-paths/analyze/${topicId}`, { params });

// ========== 趋势预测 ==========

export const getTrendPredictions = (params?: {
  target_type?: string;
  target_id?: number;
  model_type?: string;
  page?: number;
  page_size?: number;
}) => api.get<unknown, UnifiedResponse<PaginatedResponse<Record<string, unknown>>>>('/trend-predictions', { params });

export const getTrendPrediction = (id: number) =>
  api.get<unknown, UnifiedResponse<Record<string, unknown>>>(`/trend-predictions/${id}`);

export const createPrediction = (params?: {
  target_type?: string;
  target_id?: number;
  model_type?: string;
  horizon_hours?: number;
}) => api.post<unknown, UnifiedResponse<Record<string, unknown>>>('/trend-predictions/predict', { params });

export const getSentimentSummary = () =>
  api.get<unknown, UnifiedResponse<SentimentSummary>>('/sentiment/summary');

export const forecastHeat = (payload: { topic_id?: number; horizon_days?: number }) =>
  api.post<unknown, UnifiedResponse<ForecastHeat>>('/forecast/heat', payload);

// ========== 模型解释 ==========

export const getModelExplanations = (params?: {
  sentiment_result_id?: number;
  method?: string;
  page?: number;
  page_size?: number;
}) => api.get<unknown, UnifiedResponse<PaginatedResponse<Record<string, unknown>>>>('/model-explanations', { params });

export const getModelExplanation = (id: number) =>
  api.get<unknown, UnifiedResponse<Record<string, unknown>>>(`/model-explanations/${id}`);

export interface ModelExplanationToken {
  token: string;
  contribution: number;
  direction: 'positive' | 'negative' | string;
  rank: number;
}

export interface ModelExplanationResult {
  explanation_id?: number | null;
  sentiment_result_id?: number | null;
  method: string;
  model_version?: string | null;
  summary?: string | null;
  text?: string | null;
  sentiment_label?: string | null;
  confidence?: number | null;
  scores?: { positive: number; negative: number; neutral: number };
  n_samples?: number;
  persisted?: boolean;
  tokens: ModelExplanationToken[];
}

export const generateModelExplanation = (payload: {
  sentiment_result_id?: number;
  text?: string;
  n_samples?: number;
}) => api.post<unknown, UnifiedResponse<ModelExplanationResult>>('/model-explanations/generate', payload);

export const explainSentiment = (sentimentResultId: number, params?: { method?: string }) =>
  api.post<unknown, UnifiedResponse<Record<string, unknown>>>(`/model-explanations/explain/${sentimentResultId}`, { params });

export const getErrorMessage = (error: unknown) => {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data as { message?: string; detail?: string } | undefined;
    return detail?.message || detail?.detail || error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return '请求失败';
};

export default api;
