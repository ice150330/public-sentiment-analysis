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

// 中文停用词列表（常见无意义词）
const STOP_WORDS = new Set([
  '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '那', '这些', '那些', '这个', '那个', '之', '与', '及', '等', '或', '但', '而', '如果', '因为', '所以', '虽然', '然而', '然后', '而且', '并且', '或者', '还是', '以及', '可以', '能够', '可能', '应该', '需要', '进行', '通过', '根据', '按照', '对于', '关于', '由于', '为了', '随着', '作为', '被', '把', '让', '给', '向', '从', '到', '在', '为', '以', '于', '则', '即', '若', '乃', '兮', '乎', '者', '所', '被', '将', '把', '被', '让', '给', '向', '从', '到', '在', '为', '以', '于',
  // 英文停用词
  'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'shall', 'should', 'can', 'could', 'may', 'might', 'must', 'ought', 'need', 'dare', 'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'between', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'and', 'but', 'if', 'or', 'because', 'until', 'while',
]);

// 简单情感关键词库（用于无 sentiment 数据时的推断）
const POSITIVE_WORDS = new Set([
  '好', '棒', '优秀', '成功', '突破', '创新', '增长', '提升', '改善', '利好', '赞', '喜', '赢', '胜', '夺冠', '晋升', '发财', '幸福', '快乐', '美丽', '精彩', '强大', '领先', '第一', '冠军', '金牌', '丰收', '顺利', '完美', '出色', '杰出', '卓越', '辉煌', '伟大', '光荣', '自豪', '激动', '感动', '温暖', '温馨', '和谐', '繁荣', '昌盛', '兴旺', '发达', '先进', '优质', '高效', '便捷', '舒适', '安全', '健康', '环保', '绿色', '美丽', '漂亮', '可爱', '迷人', '精彩', '有趣', '好玩', '开心', '高兴', '满意', '放心', '安心', '省心', '贴心', '用心', '专业', '敬业', '负责', '认真', '努力', '拼搏', '奋斗', '进取', '上进', '积极', '乐观', '向上', '阳光', '正能量',
]);

const NEGATIVE_WORDS = new Set([
  '坏', '差', '失败', '下降', '下跌', '暴跌', '崩盘', '危机', '风险', '问题', '困难', '挑战', '矛盾', '冲突', '纠纷', '争议', '丑闻', '腐败', '贪污', '受贿', '犯罪', '违法', '违规', '事故', '灾难', '灾害', '疫情', '病毒', '死亡', '伤亡', '损失', '破坏', '损害', '伤害', '袭击', '攻击', '战争', '恐怖', '暴力', '犯罪', '小偷', '骗子', '假货', '伪劣', '劣质', '差评', '投诉', '举报', '曝光', '揭露', '内幕', '黑幕', '潜规则', '不公', '不平', '不正', '腐败', '堕落', '颓废', '消极', '悲观', '失望', '绝望', '痛苦', '悲伤', '难过', '愤怒', '生气', '恼火', '烦躁', '焦虑', '担忧', '害怕', '恐惧', '惊慌', '震惊', '意外', '突然', '紧急', '危险', '警告', '警惕', '注意', '严重', '重大', '特大', '恶性', '残忍', '冷酷', '无情', '冷漠', '麻木', '迟钝', '愚蠢', '笨', '傻', '呆', '迂腐', '陈旧', '落后', '过时', '淘汰', '失业', '破产', '倒闭', '关门', '解散', '分裂', '解体', '崩溃', '瓦解', '毁灭', '灭亡', '绝迹', '消失', '失踪', '失联', '被困', '被围', '被堵', '被封', '被禁', '被删', '被屏蔽', '被限制', '被约束', '被控制', '被压迫', '被剥削', '被欺负', '被侮辱', '被伤害', '被损害', '被侵犯', '被侵害', '被盗', '被抢', '被骗', '被偷', '被拐', '被绑架', '被劫持', '被勒索', '被敲诈', '被威胁', '被恐吓', '被骚扰', '被跟踪', '被监视', '被监听', '被曝光', '被揭发', '被举报', '被投诉', '被批评', '被指责', '被谴责', '被惩罚', '被处罚', '被判刑', '被关押', '被囚禁', '被拘留', '被逮捕', '被通缉', '被追捕', '被追杀',
]);

const SEVERITY_WEIGHT: Record<string, number> = {
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

// 基于标题关键词推断情感倾向
function _inferSentiment(title: string): 'positive' | 'neutral' | 'negative' {
  let pos = 0;
  let neg = 0;
  for (const word of POSITIVE_WORDS) {
    if (title.includes(word)) pos++;
  }
  for (const word of NEGATIVE_WORDS) {
    if (title.includes(word)) neg++;
  }
  if (pos > neg) return 'positive';
  if (neg > pos) return 'negative';
  return 'neutral';
}

export const buildRankingData = (topics: HotTopic[]): RankingVisualItem[] =>
  topics.slice(0, 10).map((topic, index) => ({
    id: topic.id,
    rank: index + 1,
    title: topic.title,
    heat: toNumber(topic.heat_score),
    platform: displayPlatformName(topic.platform_name),
    sentiment: _inferSentiment(topic.title),
  }));

export const buildWordCloudData = (topics: HotTopic[]) => {
  const wordMap: Record<string, number> = {};
  topics.forEach((topic) => {
    const heat = Math.max(1, toNumber(topic.heat_score));
    const words = (topic.title || '')
      .replace(/[【】《》“”"'()[\]{}]/g, ' ')
      .split(/[\s,，.。!！?？;；:：#、|｜]+/)
      .map((word) => word.trim())
      .filter((word) => word.length >= 2 && word.length <= 12 && !STOP_WORDS.has(word));

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
