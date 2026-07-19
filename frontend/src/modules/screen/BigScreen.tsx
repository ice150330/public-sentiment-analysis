/**
 * @file BigScreen.tsx
 * @description 暗色数据大屏 —— 公众情绪监测指挥舱
 * 1920×1080 设计画布 + useScreenAdapt 等比缩放，独立于浅色工作台壳层。
 * 所有样式见同目录 screen.css（.bs-*），ECharts 使用暗色主题 psa-dark。
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as echarts from 'echarts';
import ReactECharts from 'echarts-for-react';
import dayjs from 'dayjs';
import { useRealtime } from '@/hooks/useRealtime';
import { useScreenAdapt } from '@/hooks/useScreenAdapt';
import { registerDarkTheme } from '@/theme/echartsDark';
import {
  AlertEvent,
  AlertSummary,
  getAlertEvents,
  getAlertSummary,
  getAuthToken,
  getErrorMessage,
  getHeatTrend,
  getOverview,
  getPlatformMonitoringMatrix,
  getSentimentDistribution,
  getTopics,
  HeatTrend,
  HotTopic,
  Overview,
  PlatformMonitoringMatrix,
  SentimentDistribution,
} from '@/services/api';
import {
  AlertTrendPoint,
  buildAlertTrendData,
  buildHealthScore,
  buildHeatmapData,
  buildNegativeData,
  buildRankingData,
  displayPlatformName,
  normalizePlatformSentiment,
  PlatformSentiment,
} from '@/utils/visualData';
import './screen.css';

registerDarkTheme(echarts);

const MONO_FONT = '"JetBrains Mono", "SFMono-Regular", Consolas, monospace';
const REFRESH_INTERVAL = 60_000;
const RANK_ROTATE_INTERVAL = 5_000;
const MAX_ALERT_EVENTS = 24;

/** 平台折线/柱条用色（暗色背景下对品牌色做了可见性适配） */
const PLATFORM_CHART_COLORS: Record<string, string> = {
  weibo: '#F43F5E',
  douyin: '#22D3EE',
  toutiao: '#EF4444',
  baidu: '#818CF8',
  bilibili: '#38BDF8',
  zhihu: '#3B82F6',
};
const FALLBACK_COLORS = ['#3B82F6', '#22C55E', '#F59E0B', '#F43F5E', '#38BDF8', '#94A3B8', '#818CF8', '#FB7185'];

/** 头部/热榜圆点用色，按平台中文名索引 */
const PLATFORM_DOT_COLORS: Record<string, string> = {
  微博: '#F43F5E',
  抖音: '#22D3EE',
  今日头条: '#EF4444',
  百度: '#818CF8',
  B站: '#38BDF8',
  知乎: '#3B82F6',
};

const SIX_PLATFORMS = [
  { key: 'weibo', name: '微博', color: '#F43F5E' },
  { key: 'douyin', name: '抖音', color: '#22D3EE' },
  { key: 'toutiao', name: '今日头条', color: '#EF4444' },
  { key: 'baidu', name: '百度', color: '#818CF8' },
  { key: 'bilibili', name: 'B站', color: '#38BDF8' },
  { key: 'zhihu', name: '知乎', color: '#3B82F6' },
];

/** 严重程度色板（兼容 P1-P4 与 critical/high/medium/low 两种写法） */
const SEVERITY_COLORS: Record<string, string> = {
  P1: '#F43F5E',
  P2: '#F59E0B',
  P3: '#3B82F6',
  P4: '#64748B',
  critical: '#F43F5E',
  high: '#F59E0B',
  medium: '#3B82F6',
  low: '#64748B',
};

const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六'];

const severityColor = (severity?: string | null) =>
  (severity && SEVERITY_COLORS[severity]) || '#64748B';

const healthColor = (score: number) =>
  score >= 75 ? '#22C55E' : score >= 55 ? '#38BDF8' : score >= 35 ? '#F59E0B' : '#F43F5E';

const healthBand = (score: number) =>
  score >= 75 ? '优' : score >= 55 ? '良' : score >= 35 ? '中' : '差';

const fmtInt = (value?: number | null) =>
  value == null || !Number.isFinite(value) ? '—' : Math.round(value).toLocaleString('zh-CN');

const fmtCompact = (value?: number | null) => {
  if (value == null || !Number.isFinite(value)) return '—';
  if (Math.abs(value) >= 10000) return `${(value / 10000).toFixed(1)}万`;
  return `${Math.round(value)}`;
};

const fmtHHMM = (iso?: string | null) => {
  if (!iso) return '--:--';
  const parsed = dayjs(iso);
  return parsed.isValid() ? parsed.format('HH:mm') : '--:--';
};

/* ========== 暗色 ECharts option 本地构建（不复用浅色 builder 的 option） ========== */

/** 舆情健康度环形仪表 */
const makeGaugeOption = (score: number) => {
  const color = healthColor(score);
  return {
    series: [
      {
        type: 'gauge',
        startAngle: 90,
        endAngle: -270,
        min: 0,
        max: 100,
        radius: '100%',
        center: ['50%', '50%'],
        progress: {
          show: true,
          width: 7,
          roundCap: true,
          itemStyle: { color, shadowBlur: 8, shadowColor: color },
        },
        axisLine: { lineStyle: { width: 7, color: [[1, 'rgba(59, 130, 246, 0.14)']] } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        pointer: { show: false },
        anchor: { show: false },
        title: { show: false },
        detail: {
          valueAnimation: true,
          formatter: '{value}',
          color: '#F1F5F9',
          fontSize: 22,
          fontWeight: 700,
          fontFamily: MONO_FONT,
          offsetCenter: [0, 0],
        },
        data: [{ value: score }],
      },
    ],
  };
};

const DONUT_META: Record<string, { name: string; color: string }> = {
  positive: { name: '正面', color: '#22C55E' },
  negative: { name: '负面', color: '#F43F5E' },
  neutral: { name: '中性', color: '#64748B' },
};

/** 情感分布环形图（数据参考 buildSentimentPieOption，暗色化本地构建） */
const makeDonutOption = (sentiment?: SentimentDistribution | null) => {
  if (!sentiment || !sentiment.total) return null;
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: {
      bottom: 0,
      left: 'center',
      icon: 'circle',
      itemWidth: 8,
      itemHeight: 8,
      textStyle: { color: '#94A3B8', fontSize: 11 },
    },
    series: [
      {
        type: 'pie',
        radius: ['54%', '74%'],
        center: ['50%', '42%'],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: '#0B1220', borderWidth: 2, borderRadius: 5 },
        label: { show: false },
        emphasis: { scale: true, scaleSize: 4 },
        data: sentiment.distribution.map((item) => ({
          name: DONUT_META[item.label]?.name || item.label,
          value: item.count,
          itemStyle: { color: DONUT_META[item.label]?.color || '#94A3B8' },
        })),
      },
    ],
  };
};

/** 跨平台热度主线（数据整形参考 buildHeatTrendOption，暗色坐标轴本地构建） */
const makeHeatLineOption = (heatTrend?: HeatTrend | null) => {
  const series = heatTrend?.series?.filter((item) => item.data.length > 0) || [];
  if (series.length === 0) return null;
  const dates = Array.from(new Set(series.flatMap((item) => item.data.map((point) => point.date)))).sort();
  return {
    tooltip: { trigger: 'axis' },
    legend: { top: 0, left: 'center', textStyle: { color: '#94A3B8', fontSize: 11 } },
    grid: { left: 12, right: 20, top: 36, bottom: 6, containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates,
      axisLabel: { color: '#64748B', fontSize: 11, formatter: (value: string) => value.slice(5) },
      axisLine: { lineStyle: { color: '#1E3A5F' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        color: '#64748B',
        fontSize: 11,
        formatter: (value: number) => fmtCompact(value),
      },
      splitLine: { lineStyle: { color: 'rgba(30, 58, 95, 0.45)', type: 'dashed' } },
    },
    series: series.map((item, index) => {
      const color = PLATFORM_CHART_COLORS[item.platform] || FALLBACK_COLORS[index % FALLBACK_COLORS.length];
      return {
        name: displayPlatformName(item.platform),
        type: 'line',
        smooth: true,
        showSymbol: false,
        symbol: 'circle',
        symbolSize: 5,
        lineStyle: { width: 2, color },
        itemStyle: { color },
        emphasis: { focus: 'series' },
        data: dates.map((date) => item.data.find((point) => point.date === date)?.avg_heat ?? null),
      };
    }),
  };
};

/** 负面平台横向条形排行 */
const makeNegativeBarOption = (negativeData: Record<string, { negative: number; total: number }>) => {
  const entries = Object.entries(negativeData)
    .map(([platform, value]) => ({
      name: displayPlatformName(platform),
      negative: value.negative,
      total: value.total,
    }))
    .filter((item) => item.total > 0)
    .sort((a, b) => b.negative - a.negative)
    .slice(0, 6);
  if (entries.length === 0) return null;
  const max = Math.max(...entries.map((item) => item.negative), 1);
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 8, right: 46, top: 8, bottom: 8, containLabel: true },
    xAxis: { type: 'value', show: false, max: Math.round(max * 1.15) },
    yAxis: {
      type: 'category',
      inverse: true,
      data: entries.map((item) => item.name),
      axisLabel: { color: '#94A3B8', fontSize: 11 },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        type: 'bar',
        barWidth: 10,
        showBackground: true,
        backgroundStyle: { color: 'rgba(59, 130, 246, 0.08)', borderRadius: [0, 5, 5, 0] },
        itemStyle: {
          borderRadius: [0, 5, 5, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: 'rgba(244, 63, 94, 0.3)' },
            { offset: 1, color: '#F43F5E' },
          ]),
        },
        label: { show: true, position: 'right', color: '#FB7185', fontSize: 11, fontFamily: MONO_FONT },
        data: entries.map((item) => item.negative),
      },
    ],
  };
};

/** 时段热力矩阵（时段 × 平台） */
const makeHeatmapOption = (cells: Array<[string, string, number]>) => {
  if (cells.length === 0) return null;
  const times = Array.from(new Set(cells.map((cell) => cell[0]))).sort();
  const platforms = Array.from(new Set(cells.map((cell) => cell[1])));
  return {
    tooltip: {
      position: 'top',
      formatter: (params: { value: [number, number, number] }) =>
        `${platforms[params.value[1]]} ${times[params.value[0]]} · 热度 ${params.value[2]}`,
    },
    grid: { left: 8, right: 12, top: 6, bottom: 30, containLabel: true },
    xAxis: {
      type: 'category',
      data: times,
      axisLabel: { color: '#64748B', fontSize: 10 },
      axisLine: { lineStyle: { color: '#1E3A5F' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'category',
      data: platforms,
      axisLabel: { color: '#94A3B8', fontSize: 10 },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    visualMap: {
      min: 0,
      max: 100,
      calculable: false,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      itemWidth: 10,
      itemHeight: 120,
      textStyle: { color: '#64748B', fontSize: 10 },
      inRange: { color: ['#10203A', '#1E3A5F', '#2563EB', '#38BDF8', '#A5F3FC'] },
    },
    series: [
      {
        type: 'heatmap',
        data: cells.map(([time, platform, value]) => [times.indexOf(time), platforms.indexOf(platform), value]),
        itemStyle: { borderColor: '#0B1220', borderWidth: 1 },
        emphasis: { itemStyle: { shadowBlur: 8, shadowColor: 'rgba(56, 189, 248, 0.6)' } },
      },
    ],
  };
};

/** 预警趋势柱线图（柱色按该时段最高严重程度着色） */
const makeAlertTrendOption = (points: AlertTrendPoint[]) => {
  if (points.length === 0) return null;
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 8, right: 12, top: 12, bottom: 4, containLabel: true },
    xAxis: {
      type: 'category',
      data: points.map((point) => point.time),
      axisLabel: { color: '#64748B', fontSize: 10 },
      axisLine: { lineStyle: { color: '#1E3A5F' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { color: '#64748B', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(30, 58, 95, 0.45)', type: 'dashed' } },
    },
    series: [
      {
        name: '预警数',
        type: 'bar',
        barWidth: '52%',
        data: points.map((point) => ({
          value: point.count,
          itemStyle: { color: severityColor(point.severity), borderRadius: [3, 3, 0, 0] },
        })),
      },
      {
        name: '趋势',
        type: 'line',
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2, color: '#38BDF8' },
        itemStyle: { color: '#38BDF8' },
        data: points.map((point) => point.count),
      },
    ],
  };
};

/** 平台情感结构堆叠条 */
const makeStackedOption = (platformSentiment: PlatformSentiment) => {
  const entries = Object.entries(platformSentiment).filter(
    ([, value]) => value.positive + value.negative + value.neutral > 0,
  );
  if (entries.length === 0) return null;
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: {
      top: 0,
      left: 'center',
      icon: 'circle',
      itemWidth: 8,
      itemHeight: 8,
      textStyle: { color: '#94A3B8', fontSize: 11 },
    },
    grid: { left: 8, right: 12, top: 28, bottom: 4, containLabel: true },
    xAxis: {
      type: 'category',
      data: entries.map(([platform]) => displayPlatformName(platform)),
      axisLabel: { color: '#94A3B8', fontSize: 10, interval: 0 },
      axisLine: { lineStyle: { color: '#1E3A5F' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#64748B', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(30, 58, 95, 0.45)', type: 'dashed' } },
    },
    series: [
      {
        name: '正面',
        type: 'bar',
        stack: 'sentiment',
        barWidth: 18,
        itemStyle: { color: '#22C55E' },
        data: entries.map(([, value]) => value.positive),
      },
      {
        name: '中性',
        type: 'bar',
        stack: 'sentiment',
        itemStyle: { color: '#64748B' },
        data: entries.map(([, value]) => value.neutral),
      },
      {
        name: '负面',
        type: 'bar',
        stack: 'sentiment',
        itemStyle: { color: '#F43F5E', borderRadius: [3, 3, 0, 0] },
        data: entries.map(([, value]) => value.negative),
      },
    ],
  };
};

/* ========== 局部展示组件 ========== */

/** 面板状态视图：加载 / 错误 / 空态（暗色本地实现，不依赖浅色 DataState） */
const BsState: React.FC<{
  loading?: boolean;
  error?: string | null;
  empty?: boolean;
  emptyText?: string;
  onRetry?: () => void;
  children: React.ReactNode;
}> = ({ loading, error, empty, emptyText = '暂无数据', onRetry, children }) => {
  if (loading) {
    return (
      <div className="bs-state">
        <span className="bs-state-spinner" />
        <span>数据加载中…</span>
      </div>
    );
  }
  if (error) {
    return (
      <div className="bs-state bs-state-error">
        <span>{error}</span>
        {onRetry && (
          <button type="button" className="bs-state-retry" onClick={onRetry}>
            重试
          </button>
        )}
      </div>
    );
  }
  if (empty) {
    return <div className="bs-state">{emptyText}</div>;
  }
  return <>{children}</>;
};

/** 玻璃拟态面板 */
const Panel: React.FC<{
  title: string;
  eyebrow: string;
  children: React.ReactNode;
}> = ({ title, eyebrow, children }) => (
  <section className="bs-panel">
    <div className="bs-panel-head">
      <div className="bs-panel-heading">
        <div className="bs-panel-eyebrow">{eyebrow}</div>
        <h3 className="bs-panel-title">{title}</h3>
      </div>
      <i className="bs-panel-corner" />
    </div>
    <div className="bs-panel-body">{children}</div>
  </section>
);

/* ========== 大屏主组件 ========== */

const BigScreen: React.FC = () => {
  const navigate = useNavigate();
  const canvasRef = useScreenAdapt();

  const [overview, setOverview] = useState<Overview | null>(null);
  const [sentiment, setSentiment] = useState<SentimentDistribution | null>(null);
  const [heatTrend, setHeatTrend] = useState<HeatTrend | null>(null);
  const [topics, setTopics] = useState<HotTopic[]>([]);
  const [alertSummary, setAlertSummary] = useState<AlertSummary | null>(null);
  const [alertEvents, setAlertEvents] = useState<AlertEvent[]>([]);
  const [matrix, setMatrix] = useState<PlatformMonitoringMatrix | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /** 初次全量加载；silent=true 时后台静默刷新，不打扰大屏展示 */
  const fetchData = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const [
        overviewRes,
        sentimentRes,
        trendRes,
        topicsRes,
        alertSummaryRes,
        alertEventsRes,
        matrixRes,
      ] = await Promise.all([
        getOverview(),
        getSentimentDistribution(),
        getHeatTrend({ days: 7, aggregation: 'daily' }),
        getTopics({ page: 1, page_size: 24, sort_by: 'heat_score', sort_order: 'desc' }),
        getAlertSummary(),
        getAlertEvents({ page: 1, page_size: MAX_ALERT_EVENTS }),
        getPlatformMonitoringMatrix(),
      ]);

      setOverview(overviewRes.data);
      setSentiment(sentimentRes.data);
      setHeatTrend(trendRes.data);
      setTopics(topicsRes.data?.items || []);
      setAlertSummary(alertSummaryRes.data);
      setAlertEvents(alertEventsRes.data?.items || []);
      setMatrix(matrixRes.data);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // 60s 轮询
  useEffect(() => {
    const timer = window.setInterval(() => {
      fetchData(true);
    }, REFRESH_INTERVAL);
    return () => window.clearInterval(timer);
  }, [fetchData]);

  // WebSocket 实时链路：alert 即刻插入预警流并闪烁，随后静默全量刷新
  const { connected, lastMessage } = useRealtime({ token: getAuthToken() });
  const [flashIds, setFlashIds] = useState<Set<number>>(new Set());
  const flashTimerRef = useRef<number | null>(null);

  useEffect(() => {
    if (!lastMessage) return;
    if (lastMessage.type === 'alert') {
      const payload = lastMessage.payload || {};
      const event: AlertEvent = {
        id: typeof payload.event_id === 'number' ? payload.event_id : Date.now(),
        rule_id: payload.rule_id ?? 0,
        rule_name: payload.rule_name ?? null,
        topic_id: payload.topic_id ?? null,
        topic_title: payload.topic_title ?? null,
        severity: payload.severity || 'P3',
        status: 'pending',
        triggered_at: payload.triggered_at || lastMessage.timestamp || new Date().toISOString(),
      };
      setAlertEvents((prev) => [event, ...prev.filter((item) => item.id !== event.id)].slice(0, MAX_ALERT_EVENTS));
      setFlashIds((prev) => new Set(prev).add(event.id));
      if (flashTimerRef.current) window.clearTimeout(flashTimerRef.current);
      flashTimerRef.current = window.setTimeout(() => setFlashIds(new Set()), 3200);
    }
    if (lastMessage.type === 'alert' || lastMessage.type === 'crawl_complete') {
      fetchData(true);
    }
  }, [lastMessage, fetchData]);

  useEffect(
    () => () => {
      if (flashTimerRef.current) window.clearTimeout(flashTimerRef.current);
    },
    [],
  );

  // 实时时钟（1s 跳动）
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  const pad = (n: number) => String(n).padStart(2, '0');
  const clockText = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
  const dateText = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} 星期${WEEKDAYS[now.getDay()]}`;

  // 数据整形（复用 utils/visualData 的纯数据部分）
  const ranking = useMemo(() => buildRankingData(topics), [topics]);
  const platformSentiment = useMemo(() => normalizePlatformSentiment(sentiment), [sentiment]);
  const negativeData = useMemo(() => buildNegativeData(platformSentiment), [platformSentiment]);
  const healthScore = useMemo(() => buildHealthScore(overview, sentiment), [overview, sentiment]);
  const heatmapData = useMemo(() => buildHeatmapData(topics), [topics]);
  const alertTrendData = useMemo(() => buildAlertTrendData(alertEvents), [alertEvents]);

  // 暗色 option 本地构建
  const gaugeOption = useMemo(() => makeGaugeOption(healthScore), [healthScore]);
  const donutOption = useMemo(() => makeDonutOption(sentiment), [sentiment]);
  const heatLineOption = useMemo(() => makeHeatLineOption(heatTrend), [heatTrend]);
  const negativeBarOption = useMemo(() => makeNegativeBarOption(negativeData), [negativeData]);
  const heatmapOption = useMemo(() => makeHeatmapOption(heatmapData), [heatmapData]);
  const alertTrendOption = useMemo(() => makeAlertTrendOption(alertTrendData), [alertTrendData]);
  const stackedOption = useMemo(() => makeStackedOption(platformSentiment), [platformSentiment]);

  // 热榜高亮自动轮换（5s，hover 暂停）
  const [rankActive, setRankActive] = useState(0);
  const rankHoverRef = useRef(false);
  useEffect(() => {
    const timer = window.setInterval(() => {
      if (rankHoverRef.current || ranking.length === 0) return;
      setRankActive((prev) => (prev + 1) % ranking.length);
    }, RANK_ROTATE_INTERVAL);
    return () => window.clearInterval(timer);
  }, [ranking.length]);

  const activePlatforms = overview?.today?.active_platforms ?? 0;
  const pendingCount = alertSummary?.pending_count ?? 0;
  const sentimentPct = (label: string) =>
    Math.round(sentiment?.distribution?.find((item) => item.label === label)?.percentage ?? 0);
  const matrixRows = matrix?.matrix || [];

  const kpis = [
    {
      key: 'topics',
      label: '今日热榜',
      value: fmtInt(overview?.today?.total_topics),
      unit: '条',
      sub: `活跃平台 ${activePlatforms}/6`,
      alert: false,
    },
    {
      key: 'analyzed',
      label: '累计已分析',
      value: fmtInt(overview?.sentiment?.total_analyzed),
      unit: '条',
      sub: `正面 ${sentimentPct('positive')}% · 负面 ${sentimentPct('negative')}%`,
      alert: false,
    },
    {
      key: 'pending',
      label: '待处理预警',
      value: fmtInt(alertSummary?.pending_count),
      unit: '条',
      sub: `今日新增 ${alertSummary?.today_count ?? 0}`,
      alert: pendingCount > 0,
    },
    {
      key: 'crawl',
      label: '今日采集成功率',
      value: overview ? fmtInt(overview.crawler.today_success_rate) : '—',
      unit: '%',
      sub: `最近采集 ${overview?.crawler?.last_run ? fmtHHMM(overview.crawler.last_run) : '—'}`,
      alert: false,
    },
  ];

  return (
    <div className="bs-screen">
      <div className="bs-canvas" ref={canvasRef}>
        {/* 头部条 */}
        <header className="bs-header">
          <div className="bs-brand">
            <span className="bs-brand-mark" />
            <div className="bs-brand-text">
              <h1>公众情绪监测指挥舱</h1>
              <p>PUBLIC SENTIMENT COMMAND CENTER</p>
            </div>
          </div>
          <div className="bs-header-platforms">
            <div className="bs-platform-dots">
              {SIX_PLATFORMS.map((platform) => (
                <span
                  key={platform.key}
                  className="bs-platform-dot"
                  style={{ background: platform.color, boxShadow: `0 0 8px ${platform.color}80` }}
                  title={platform.name}
                />
              ))}
            </div>
            <span className="bs-platform-count">活跃平台 {activePlatforms}/6</span>
          </div>
          <div className="bs-header-right">
            <div className="bs-ws" title={connected ? '实时链路已连接' : '实时链路未连接'}>
              <span className={`bs-ws-dot${connected ? ' is-on' : ''}`} />
              <span className="bs-ws-text">实时链路</span>
            </div>
            <div className="bs-clock">
              <span className="bs-clock-time">{clockText}</span>
              <span className="bs-clock-date">{dateText}</span>
            </div>
            <button type="button" className="bs-back-btn" onClick={() => navigate('/')}>
              返回工作台
            </button>
          </div>
        </header>

        {/* KPI 指标带 */}
        <section className="bs-kpis">
          {kpis.map((kpi) => (
            <div key={kpi.key} className={`bs-kpi${kpi.alert ? ' bs-kpi--alert' : ''}`}>
              <div className="bs-kpi-label">{kpi.label}</div>
              <div className="bs-kpi-value">
                {kpi.value}
                <em>{kpi.unit}</em>
              </div>
              <div className="bs-kpi-sub">{kpi.sub}</div>
            </div>
          ))}
          <div className="bs-kpi bs-kpi--gauge">
            <div className="bs-kpi-text">
              <div className="bs-kpi-label">舆情健康度</div>
              <div className="bs-kpi-band" style={{ color: healthColor(healthScore) }}>
                状态 · {healthBand(healthScore)}
              </div>
              <div className="bs-kpi-sub">综合情绪评分</div>
            </div>
            <div className="bs-kpi-gauge">
              <ReactECharts
                option={gaugeOption}
                theme="psa-dark"
                notMerge
                style={{ width: '100%', height: '100%' }}
              />
            </div>
          </div>
        </section>

        {/* 主区三列 */}
        <main className="bs-main">
          <div className="bs-col bs-col-left">
            <Panel title="热榜 TOP10" eyebrow="HOT RANKING">
              <BsState loading={loading} error={error} empty={ranking.length === 0} emptyText="暂无热榜数据" onRetry={() => fetchData()}>
                <div
                  className="bs-rank-list"
                  onMouseEnter={() => {
                    rankHoverRef.current = true;
                  }}
                  onMouseLeave={() => {
                    rankHoverRef.current = false;
                  }}
                >
                  {ranking.map((item) => (
                    <div
                      key={item.id}
                      className={`bs-rank-item${item.rank - 1 === rankActive ? ' is-active' : ''}`}
                    >
                      <span className={`bs-rank-badge r${item.rank}`}>{item.rank}</span>
                      <span
                        className="bs-rank-dot"
                        style={{ background: PLATFORM_DOT_COLORS[item.platform] || '#3B82F6' }}
                      />
                      <span className="bs-rank-title" title={item.title}>
                        {item.title}
                      </span>
                      <span className="bs-rank-heat">{fmtCompact(item.heat)}</span>
                    </div>
                  ))}
                </div>
              </BsState>
            </Panel>
            <Panel title="情感分布" eyebrow="SENTIMENT">
              <BsState loading={loading} error={error} empty={!donutOption} emptyText="暂无情感数据" onRetry={() => fetchData()}>
                <div className="bs-donut-wrap">
                  <ReactECharts className="bs-chart" option={donutOption || {}} theme="psa-dark" notMerge />
                  <div className="bs-donut-center">
                    <strong>{fmtInt(sentiment?.total)}</strong>
                    <span>总样本</span>
                  </div>
                </div>
              </BsState>
            </Panel>
          </div>

          <div className="bs-col bs-col-center">
            <Panel title="跨平台热度主线" eyebrow="HEAT TREND · 7D">
              <BsState loading={loading} error={error} empty={!heatLineOption} emptyText="暂无热度趋势" onRetry={() => fetchData()}>
                <ReactECharts className="bs-chart" option={heatLineOption || {}} theme="psa-dark" notMerge />
              </BsState>
            </Panel>
            <Panel title="平台监测矩阵" eyebrow="PLATFORM MATRIX">
              <BsState loading={loading} error={error} empty={matrixRows.length === 0} emptyText="暂无监测数据" onRetry={() => fetchData()}>
                <div className="bs-matrix">
                  <div className="bs-matrix-row bs-matrix-head">
                    <span>平台</span>
                    <span className="bs-matrix-num">话题数</span>
                    <span className="bs-matrix-num">平均热度</span>
                    <span className="bs-matrix-num">负面占比</span>
                    <span className="bs-matrix-status">状态</span>
                  </div>
                  {matrixRows.map((row) => (
                    <div className="bs-matrix-row" key={row.platform_id}>
                      <span className="bs-matrix-name">
                        <i style={{ background: PLATFORM_DOT_COLORS[row.display_name] || '#3B82F6' }} />
                        {row.display_name}
                      </span>
                      <span className="bs-matrix-num">{fmtInt(row.topic_count)}</span>
                      <span className="bs-matrix-num">{fmtCompact(row.avg_heat)}</span>
                      <span className={`bs-matrix-num${row.negative_ratio > 30 ? ' is-danger' : ''}`}>
                        {row.negative_ratio.toFixed(1)}%
                      </span>
                      <span className="bs-matrix-status">
                        <i className={row.is_healthy ? 'ok' : 'bad'} />
                        {row.is_healthy ? '正常' : '异常'}
                      </span>
                    </div>
                  ))}
                </div>
              </BsState>
            </Panel>
          </div>

          <div className="bs-col bs-col-right">
            <Panel title="负面平台排行" eyebrow="NEGATIVE RANK">
              <BsState loading={loading} error={error} empty={!negativeBarOption} emptyText="暂无负面数据" onRetry={() => fetchData()}>
                <ReactECharts className="bs-chart" option={negativeBarOption || {}} theme="psa-dark" notMerge />
              </BsState>
            </Panel>
            <Panel title="实时预警流" eyebrow="LIVE ALERTS">
              <BsState loading={loading} error={error} empty={alertEvents.length === 0} emptyText="暂无预警" onRetry={() => fetchData()}>
                <div className="bs-alert-list">
                  {alertEvents.map((event) => (
                    <div
                      key={event.id}
                      className={`bs-alert-item${flashIds.has(event.id) ? ' is-flash' : ''}`}
                    >
                      <i className="bs-alert-sev" style={{ background: severityColor(event.severity) }} />
                      <div className="bs-alert-main">
                        <div className="bs-alert-title" title={event.topic_title || event.rule_name || '预警事件'}>
                          {event.topic_title || event.rule_name || '预警事件'}
                        </div>
                        <div className="bs-alert-meta">
                          <span
                            className="bs-alert-sev-tag"
                            style={{ color: severityColor(event.severity), borderColor: severityColor(event.severity) }}
                          >
                            {event.severity || 'P4'}
                          </span>
                          <span className="bs-alert-rule">{event.rule_name || '未知规则'}</span>
                        </div>
                      </div>
                      <span className="bs-alert-time">{fmtHHMM(event.triggered_at)}</span>
                    </div>
                  ))}
                </div>
              </BsState>
            </Panel>
          </div>
        </main>

        {/* 底部带 */}
        <footer className="bs-bottom">
          <Panel title="时段热力矩阵" eyebrow="TIME × PLATFORM">
            <BsState loading={loading} error={error} empty={!heatmapOption} emptyText="暂无热力数据" onRetry={() => fetchData()}>
              <ReactECharts className="bs-chart" option={heatmapOption || {}} theme="psa-dark" notMerge />
            </BsState>
          </Panel>
          <Panel title="预警趋势" eyebrow="ALERT TREND">
            <BsState loading={loading} error={error} empty={!alertTrendOption} emptyText="暂无预警趋势" onRetry={() => fetchData()}>
              <ReactECharts className="bs-chart" option={alertTrendOption || {}} theme="psa-dark" notMerge />
            </BsState>
          </Panel>
          <Panel title="平台情感结构" eyebrow="SENTIMENT STRUCTURE">
            <BsState loading={loading} error={error} empty={!stackedOption} emptyText="暂无平台情感" onRetry={() => fetchData()}>
              <ReactECharts className="bs-chart" option={stackedOption || {}} theme="psa-dark" notMerge />
            </BsState>
          </Panel>
        </footer>
      </div>
    </div>
  );
};

export default BigScreen;
