import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export interface UnifiedResponse<T> {
  code: number;
  data: T;
  message: string;
  request_id?: string | null;
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

export const analyzeText = (text: string) =>
  api.post<unknown, UnifiedResponse<SentimentAnalyzeResult>>('/sentiment/analyze', { text });

export const analyzeBatch = (texts: string[]) =>
  api.post<unknown, UnifiedResponse<SentimentAnalyzeResult[]>>('/sentiment/analyze/batch', { texts });

export const getSentimentResults = (params?: {
  label?: string;
  platform?: string;
  min_confidence?: number;
  start_time?: string;
  end_time?: string;
  page?: number;
  page_size?: number;
}) => api.get<unknown, UnifiedResponse<SentimentResult[]>>('/sentiment/results', { params });

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
}) => api.get<unknown, UnifiedResponse<CrawlLog[]>>('/crawler/logs', { params });

export const getCrawlerSchedule = () =>
  api.get<unknown, UnifiedResponse<CrawlerScheduleConfig>>('/crawler/schedule');

export const updateCrawlerSchedule = (config: CrawlerScheduleConfig) =>
  api.put<unknown, UnifiedResponse<CrawlerScheduleConfig>>('/crawler/schedule', config);

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
