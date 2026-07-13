import {
  AlertEvent,
  AlertSummary,
  HeatTrend,
  HotTopic,
  Overview,
  SentimentDistribution,
} from '../services/api';

export type PlatformSentiment = Record<string, { positive: number; negative: number; neutral: number }>;

export interface RankingVisualItem {
  id: string | number;
  rank: number;
  title: string;
  heat: number;
  platform: string;
  sentiment: 'positive' | 'neutral' | 'negative';
}

export interface GraphVisualData {
  nodes: Array<{
    id: string;
    name: string;
    category: number;
    value?: number;
    symbolSize?: number;
    itemStyle?: { color: string };
  }>;
  links: Array<{ source: string; target: string; value?: number }>;
}

export interface AlertTrendPoint {
  time: string;
  count: number;
  severity: 'P1' | 'P2' | 'P3' | 'P4';
}

const PLATFORM_NAMES: Record<string, string> = {
  toutiao: '今日头条',
  bilibili: 'B站',
  douyin: '抖音',
  weibo: '微博',
  zhihu: '知乎',
  baidu: '百度',
};

const SEVERITY_WEIGHT: Record<string, number> = {
  P1: 4,
  P2: 3,
  P3: 2,
  P4: 1,
};

export const displayPlatformName = (name?: string | null) => {
  if (!name) return '未知平台';
  return PLATFORM_NAMES[name] || name;
};

const toNumber = (value?: number | null) => (Number.isFinite(value) ? Number(value) : 0);

export const normalizePlatformSentiment = (sentiment?: SentimentDistribution | null): PlatformSentiment => {
  const source = sentiment?.by_platform || {};
  return Object.fromEntries(
    Object.entries(source).map(([platform, value]) => [
      platform,
      {
        positive: toNumber(value.positive),
        negative: toNumber(value.negative),
        neutral: toNumber(value.neutral),
      },
    ]),
  );
};

export const buildHealthScore = (overview?: Overview | null, sentiment?: SentimentDistribution | null) => {
  const source = sentiment?.distribution?.length
    ? Object.fromEntries(sentiment.distribution.map((item) => [item.label, item.count]))
    : overview?.today?.sentiment_distribution || {};
  const positive = toNumber(source.positive);
  const negative = toNumber(source.negative);
  const neutral = toNumber(source.neutral);
  const total = positive + negative + neutral;
  if (total <= 0) return 0;
  return Math.round(((positive + neutral * 0.45) / total) * 100);
};

export const buildRankingData = (topics: HotTopic[]): RankingVisualItem[] =>
  topics.slice(0, 10).map((topic, index) => ({
    id: topic.id,
    rank: index + 1,
    title: topic.title,
    heat: toNumber(topic.heat_score),
    platform: displayPlatformName(topic.platform_name),
    sentiment: 'neutral',
  }));

export const buildWordCloudData = (topics: HotTopic[]) => {
  const wordMap: Record<string, number> = {};
  topics.forEach((topic) => {
    const heat = Math.max(1, toNumber(topic.heat_score));
    const words = (topic.title || '')
      .replace(/[【】《》“”"'()[\]{}]/g, ' ')
      .split(/[\s,，.。!！?？;；:：#、|｜]+/)
      .map((word) => word.trim())
      .filter((word) => word.length >= 2 && word.length <= 12);

    words.forEach((word) => {
      wordMap[word] = (wordMap[word] || 0) + heat;
    });
  });

  return Object.entries(wordMap)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 50);
};

export const buildRelationData = (topics: HotTopic[]): GraphVisualData => {
  const nodes: GraphVisualData['nodes'] = [];
  const links: GraphVisualData['links'] = [];
  const platformSet = new Set<string>();

  topics.slice(0, 14).forEach((topic, index) => {
    const platform = displayPlatformName(topic.platform_name);
    const topicNodeId = `topic-${topic.id}`;
    const platformNodeId = `platform-${platform}`;
    const heat = Math.max(1, toNumber(topic.heat_score));

    platformSet.add(platform);
    nodes.push({
      id: topicNodeId,
      name: topic.title.length > 12 ? `${topic.title.slice(0, 12)}...` : topic.title,
      category: 0,
      value: heat,
      symbolSize: 18 + Math.min(28, Math.log10(heat + 10) * 5),
      itemStyle: { color: index < 3 ? '#E11D48' : '#2563EB' },
    });
    links.push({ source: topicNodeId, target: platformNodeId, value: Math.max(1, Math.round(heat / 100000)) });
  });

  platformSet.forEach((platform) => {
    nodes.push({
      id: `platform-${platform}`,
      name: platform,
      category: 1,
      value: 80,
      symbolSize: 34,
      itemStyle: { color: '#16A34A' },
    });
  });

  return { nodes, links };
};

export const buildRadarData = (
  platformSentiment: PlatformSentiment,
  alertSummary?: AlertSummary | null,
) => {
  const totals = Object.values(platformSentiment).map((value) => value.positive + value.negative + value.neutral);
  const maxTotal = Math.max(1, ...totals);
  const alertPressure = Math.min(100, (toNumber(alertSummary?.pending_count) / Math.max(1, maxTotal)) * 10);

  return Object.fromEntries(
    Object.entries(platformSentiment).map(([platform, value]) => {
      const total = value.positive + value.negative + value.neutral || 1;
      return [
        platform,
        {
          heat: Math.round((total / maxTotal) * 100),
          positive: value.positive,
          negative: value.negative,
          neutral: value.neutral,
          alert: Math.round(((value.negative / total) * 70) + alertPressure * 0.3),
        },
      ];
    }),
  );
};

export const buildNegativeData = (platformSentiment: PlatformSentiment) =>
  Object.fromEntries(
    Object.entries(platformSentiment).map(([platform, value]) => [
      platform,
      {
        negative: value.negative,
        total: value.positive + value.negative + value.neutral,
      },
    ]),
  );

export const buildSankeyData = (topics: HotTopic[]) =>
  topics.slice(0, 12).map((topic) => ({
    source: displayPlatformName(topic.platform_name),
    target: topic.title.length > 10 ? `${topic.title.slice(0, 10)}...` : topic.title,
    value: Math.max(1, Math.round(toNumber(topic.heat_score) / 100000)),
  }));

export const buildTimelineData = (topics: HotTopic[]) =>
  topics.slice(0, 24).map((topic) => ({
    time: topic.crawl_time,
    heat: toNumber(topic.heat_score),
    title: topic.title,
    platform: displayPlatformName(topic.platform_name),
  }));

export const buildHeatmapData = (topics: HotTopic[]): Array<[string, string, number]> => {
  const maxHeat = Math.max(1, ...topics.map((topic) => toNumber(topic.heat_score)));
  const buckets = new Map<string, number>();

  topics.forEach((topic) => {
    const date = new Date(topic.crawl_time);
    if (Number.isNaN(date.getTime())) return;

    const hour = Math.floor(date.getHours() / 2) * 2;
    const time = `${String(hour).padStart(2, '0')}:00`;
    const platform = displayPlatformName(topic.platform_name);
    const key = `${time}|${platform}`;
    const score = Math.round((toNumber(topic.heat_score) / maxHeat) * 100);
    buckets.set(key, Math.max(buckets.get(key) || 0, score));
  });

  return Array.from(buckets.entries()).map(([key, value]) => {
    const [time, platform] = key.split('|');
    return [time, platform, value];
  });
};

export const buildAlertTrendData = (events: AlertEvent[]): AlertTrendPoint[] => {
  const buckets = new Map<string, { count: number; severity: 'P1' | 'P2' | 'P3' | 'P4' }>();

  events.forEach((event) => {
    const date = new Date(event.triggered_at);
    if (Number.isNaN(date.getTime())) return;

    const time = `${String(date.getHours()).padStart(2, '0')}:00`;
    const severity = (event.severity || 'P4') as 'P1' | 'P2' | 'P3' | 'P4';
    const existing = buckets.get(time);
    if (!existing) {
      buckets.set(time, { count: 1, severity });
      return;
    }

    existing.count += 1;
    if (SEVERITY_WEIGHT[severity] > SEVERITY_WEIGHT[existing.severity]) {
      existing.severity = severity;
    }
  });

  return Array.from(buckets.entries())
    .map(([time, value]) => ({ time, ...value }))
    .sort((a, b) => a.time.localeCompare(b.time));
};

export const buildHeatTrendOption = (heatTrend?: HeatTrend | null) => {
  const series = heatTrend?.series?.filter((item) => item.data.length > 0) || [];
  if (series.length === 0) return null;

  const dates = Array.from(new Set(series.flatMap((item) => item.data.map((point) => point.date))));
  return {
    tooltip: { trigger: 'axis' },
    legend: { top: 0, textStyle: { color: '#64748B', fontWeight: 700 } },
    grid: { left: 66, right: 18, top: 44, bottom: 30 },
    xAxis: { type: 'category', data: dates, axisLabel: { color: '#64748B' } },
    yAxis: { type: 'value', axisLabel: { color: '#64748B' }, splitLine: { lineStyle: { color: '#E7EEF7' } } },
    series: series.map((item) => ({
      name: displayPlatformName(item.platform),
      type: 'line',
      smooth: true,
      symbolSize: 6,
      data: dates.map((date) => item.data.find((point) => point.date === date)?.avg_heat ?? null),
    })),
  };
};

export const buildSentimentPieOption = (sentiment?: SentimentDistribution | null) => {
  if (!sentiment || sentiment.total === 0) return null;

  return {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, textStyle: { color: '#64748B', fontWeight: 700 } },
    color: ['#16A34A', '#E11D48', '#64748B'],
    series: [
      {
        type: 'pie',
        radius: ['48%', '72%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: true,
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        emphasis: { label: { show: true, formatter: '{b} {d}%', color: '#152033', fontWeight: 700 } },
        data: sentiment.distribution.map((item) => ({
          name: item.label === 'positive' ? '正面' : item.label === 'negative' ? '负面' : '中性',
          value: item.count,
        })),
      },
    ],
  };
};
