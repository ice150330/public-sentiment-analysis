import axios from 'axios';

// API 基础配置
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// ==================== 平台管理 API ====================
export const getPlatforms = () => api.get('/platforms');
export const getPlatform = (id: number) => api.get(`/platforms/${id}`);

// ==================== 热榜数据 API ====================
export const getTopics = (params?: {
  platform_id?: number;
  start_time?: string;
  end_time?: string;
  category?: string;
  skip?: number;
  limit?: number;
}) => api.get('/topics', { params });

export const getTopic = (id: number) => api.get(`/topics/${id}`);

export const searchTopics = (keyword: string) =>
  api.get(`/topics/search?keyword=${encodeURIComponent(keyword)}`);

// ==================== 情感分析 API ====================
export const analyzeText = (text: string) =>
  api.post('/sentiment/analyze', { text });

export const analyzeBatch = (texts: string[]) =>
  api.post('/sentiment/analyze/batch', { texts });

export const getSentimentDistribution = (params?: {
  platform_id?: number;
  start_time?: string;
  end_time?: string;
}) => api.get('/sentiment/distribution', { params });

export const getSentimentTrend = (params?: {
  platform_id?: number;
  days?: number;
}) => api.get('/sentiment/trend', { params });

// ==================== 统计分析 API ====================
export const getHeatRanking = (params?: {
  platform_id?: number;
  start_time?: string;
  end_time?: string;
  limit?: number;
}) => api.get('/stats/heat-ranking', { params });

export const getCategoryDistribution = (params?: {
  platform_id?: number;
  start_time?: string;
  end_time?: string;
}) => api.get('/stats/category-distribution', { params });

export const getPlatformComparison = (params?: {
  start_time?: string;
  end_time?: string;
  metric?: string;
}) => api.get('/stats/platform-comparison', { params });

export const getCrawlStats = (params?: {
  platform_id?: number;
  start_time?: string;
  end_time?: string;
}) => api.get('/stats/crawl', { params });

export const getDashboardStats = () => api.get('/stats/dashboard');

// ==================== 爬虫控制 API ====================
export const triggerCrawl = (platformId?: number) =>
  api.post('/crawler/trigger', { platform_id: platformId });

export const getCrawlStatus = () => api.get('/crawler/status');

export const getCrawlLogs = (params?: {
  platform_id?: number;
  status?: string;
  skip?: number;
  limit?: number;
}) => api.get('/crawler/logs', { params });

export const analyzeSentiment = () => api.post('/crawler/analyze');

export default api;
