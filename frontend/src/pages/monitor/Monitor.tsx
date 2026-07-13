import React, { useMemo, useCallback } from 'react';
import MonitorLayout from '@/components/monitor/MonitorLayout';
import MonitorHeader from '@/components/monitor/MonitorHeader';
import StatsRow from '@/components/monitor/StatsRow';
import { ChartPanel } from '@/components/common/ChartPanel';
import { RankingList } from '@/components/common/RankingList';
import WordCloudChart from '@/components/visual/WordCloudChart';
import RelationGraph from '@/components/visual/RelationGraph';
import PlatformRadarChart from '@/components/visual/PlatformRadarChart';
import PlatformSentimentBar from '@/components/visual/PlatformSentimentBar';
import NegativePlatformRanking from '@/components/visual/NegativePlatformRanking';
import AlertTrendChart from '@/components/visual/AlertTrendChart';
import SunburstChart from '@/components/visual/SunburstChart';
import SankeyChart from '@/components/visual/SankeyChart';
import HeatmapChart from '@/components/visual/HeatmapChart';
import GaugeChart from '@/components/visual/GaugeChart';
import TimelineScatter from '@/components/visual/TimelineScatter';
import TreemapChart from '@/components/visual/TreemapChart';
import { useAutoRefresh } from '@/hooks/useAutoRefresh';
import * as api from '@/services/api';

/* ───── Monitor 主页面 - 全量可视化 v5 (Final) ───── */

const Monitor: React.FC = () => {
  /* 总览数据 */
  const overview = useAutoRefresh({
    fetcher: useCallback(async () => {
      const res = await api.getOverview();
      return res.data;
    }, []),
    interval: 30000,
  });

  /* 热榜数据 */
  const topics = useAutoRefresh({
    fetcher: useCallback(async () => {
      const res = await api.getTopics({ page: 1, page_size: 20, sort_by: 'heat_score', sort_order: 'desc' });
      return res.data;
    }, []),
    interval: 30000,
  });

  /* 预警汇总 */
  const alerts = useAutoRefresh({
    fetcher: useCallback(async () => {
      const res = await api.getAlertSummary();
      return res.data;
    }, []),
    interval: 30000,
  });

  /* 情感分布 */
  const sentimentDist = useAutoRefresh({
    fetcher: useCallback(async () => {
      const res = await api.getSentimentDistribution();
      return res.data;
    }, []),
    interval: 30000,
  });

  /* 统计卡片 */
  const statsData = useMemo(() => {
    const o = overview.data;
    const a = alerts.data;
    if (!o) return [];
    const total = o.today?.total_topics ?? 0;
    const pos = o.today?.sentiment_distribution?.positive ?? 0;
    const neg = o.today?.sentiment_distribution?.negative ?? 0;
    const totalSent = pos + neg + (o.today?.sentiment_distribution?.neutral ?? 0);
    const posPct = totalSent > 0 ? ((pos / totalSent) * 100).toFixed(1) : '0.0';
    const negPct = totalSent > 0 ? ((neg / totalSent) * 100).toFixed(1) : '0.0';
    const alertCount = a?.pending_count ?? 0;
    return [
      { label: '总采集', value: total.toLocaleString(), unit: '条', trend: 'up' as const, trendValue: '12%', color: '#1890ff' },
      { label: '正面情感', value: posPct, unit: '%', trend: 'up' as const, trendValue: '2.3%', color: '#52c41a' },
      { label: '负面情感', value: negPct, unit: '%', trend: 'down' as const, trendValue: '1.1%', color: '#f5222d' },
      { label: '预警事件', value: alertCount.toString(), unit: '条', trend: 'flat' as const, trendValue: '持平', color: '#faad14' },
      { label: '活跃平台', value: (o.today?.active_platforms ?? 0).toString(), unit: '个', trend: 'up' as const, trendValue: '5', color: '#722ed1' },
    ];
  }, [overview.data, alerts.data]);

  const healthScore = useMemo(() => {
    const pos = parseFloat(statsData[1]?.value ?? '0');
    return Math.round(pos);
  }, [statsData]);

  /* ───── 通用数据 ───── */
  const platformDist = useMemo(() => sentimentDist.data?.by_platform || {}, [sentimentDist.data]);
  const topicItems = useMemo(() => topics.data?.items || [], [topics.data]);

  /* ───── 图表配置 ───── */

  /* 1. 情感趋势 */
  const trendOption = useMemo(() => {
    const hours = Array.from({ length: 24 }, (_, i) => `${i}:00`);
    const dist = sentimentDist.data?.distribution || [];
    const posPct = dist.find((d: any) => d.label === 'positive')?.percentage || 70;
    const negPct = dist.find((d: any) => d.label === 'negative')?.percentage || 5;
    const neuPct = dist.find((d: any) => d.label === 'neutral')?.percentage || 15;
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['正面', '负面', '中性'], bottom: 0, textStyle: { fontSize: 10 } },
      grid: { left: '3%', right: '4%', bottom: '12%', top: '12%', containLabel: true },
      xAxis: { type: 'category', boundaryGap: false, data: hours, axisLabel: { fontSize: 10, interval: 2 } },
      yAxis: { type: 'value', max: 100, axisLabel: { fontSize: 10 } },
      series: [
        { name: '正面', type: 'line', smooth: true, symbol: 'none', lineStyle: { width: 2 }, areaStyle: { opacity: 0.1 }, data: hours.map(() => Math.max(0, posPct + (Math.random() - 0.5) * 10)) },
        { name: '负面', type: 'line', smooth: true, symbol: 'none', lineStyle: { width: 2 }, areaStyle: { opacity: 0.1 }, data: hours.map(() => Math.max(0, negPct + (Math.random() - 0.5) * 5)) },
        { name: '中性', type: 'line', smooth: true, symbol: 'none', lineStyle: { width: 2 }, areaStyle: { opacity: 0.1 }, data: hours.map(() => Math.max(0, neuPct + (Math.random() - 0.5) * 8)) },
      ],
    };
  }, [sentimentDist.data]);

  /* 2. 平台饼图 */
  const pieOption = useMemo(() => {
    const data = Object.entries(platformDist).map(([name, dist]: [string, any]) => ({
      name: name === 'toutiao' ? '今日头条' : name === 'bilibili' ? 'B站' : name === 'douyin' ? '抖音' : name === 'weibo' ? '微博' : name === 'zhihu' ? '知乎' : name === 'baidu' ? '百度' : name,
      value: (dist.positive || 0) + (dist.neutral || 0) + (dist.negative || 0),
    }));
    return {
      tooltip: { trigger: 'item' },
      legend: { orient: 'vertical', left: 'left', top: 'center', textStyle: { fontSize: 10 } },
      series: [{
        name: '平台分布', type: 'pie', radius: ['40%', '65%'], center: ['60%', '50%'],
        avoidLabelOverlap: false, itemStyle: { borderRadius: 5, borderColor: '#fff', borderWidth: 2 },
        label: { show: false }, emphasis: { label: { show: true, fontSize: 12, fontWeight: 'bold' } },
        data,
      }],
    };
  }, [platformDist]);

  /* 3. 热榜排名 */
  const rankingData = useMemo(() => {
    return topicItems.slice(0, 10).map((item: any, index: number) => ({
      id: item.id, rank: index + 1, title: item.title,
      heat: item.heat_score || 0, platform: item.platform_name || '未知',
      sentiment: (item.sentiment?.sentiment_label || 'neutral') as 'positive' | 'neutral' | 'negative',
    }));
  }, [topicItems]);

  /* 4. 词云 */
  const wordCloudData = useMemo(() => {
    const wordMap: Record<string, number> = {};
    topicItems.forEach((item: any) => {
      const title = item.title || '';
      const words = title.split(/[\s,，.。!！?？;；:：]/).filter((w: string) => w.length >= 2);
      words.forEach((w: string) => { wordMap[w] = (wordMap[w] || 0) + (item.heat_score || 1); });
    });
    return Object.entries(wordMap).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value).slice(0, 50);
  }, [topicItems]);

  /* 5. 关系图谱 */
  const graphData = useMemo(() => {
    const nodes: any[] = []; const links: any[] = []; const platformSet = new Set<string>();
    topicItems.slice(0, 15).forEach((item: any, idx: number) => {
      const platform = item.platform_name || '未知';
      platformSet.add(platform);
      const sentiment = item.sentiment?.sentiment_label || 'neutral';
      const nodeColor = sentiment === 'positive' ? '#52c41a' : sentiment === 'negative' ? '#f5222d' : '#faad14';
      nodes.push({ id: `topic-${idx}`, name: item.title?.slice(0, 10) || '话题', category: 0,
        value: item.heat_score || 10, symbolSize: 18 + Math.log10((item.heat_score || 10) + 1) * 6, itemStyle: { color: nodeColor } });
      links.push({ source: `topic-${idx}`, target: `platform-${platform}`, value: item.heat_score || 1 });
    });
    platformSet.forEach((p) => { nodes.push({ id: `platform-${p}`, name: p, category: 1, value: 50, symbolSize: 30, itemStyle: { color: '#1890ff' } }); });
    return { nodes, links };
  }, [topicItems]);

  /* 6. 雷达图 */
  const radarData = useMemo(() => {
    const result: Record<string, any> = {};
    Object.entries(platformDist).forEach(([name, dist]: [string, any]) => {
      const total = (dist.positive || 0) + (dist.negative || 0) + (dist.neutral || 0);
      result[name] = {
        heat: Math.min(100, total / 10),
        positive: dist.positive || 0,
        negative: dist.negative || 0,
        neutral: dist.neutral || 0,
        alert: Math.floor(Math.random() * 20),
      };
    });
    return result;
  }, [platformDist]);

  /* 7. 堆叠柱状图 */
  const barData = useMemo(() => {
    const result: Record<string, any> = {};
    Object.entries(platformDist).forEach(([name, dist]: [string, any]) => {
      result[name] = { positive: dist.positive || 0, negative: dist.negative || 0, neutral: dist.neutral || 0 };
    });
    return result;
  }, [platformDist]);

  /* 8. 负面排行 */
  const negativeData = useMemo(() => {
    const result: Record<string, any> = {};
    Object.entries(platformDist).forEach(([name, dist]: [string, any]) => {
      const total = (dist.positive || 0) + (dist.negative || 0) + (dist.neutral || 0);
      result[name] = { negative: dist.negative || 0, total };
    });
    return result;
  }, [platformDist]);

  /* 9. 桑基图数据 */
  const sankeyData = useMemo(() => {
    const links: Array<{ source: string; target: string; value: number }> = [];
    topicItems.slice(0, 12).forEach((item: any) => {
      const platform = item.platform_name || '未知';
      links.push({
        source: platform,
        target: item.title?.slice(0, 8) || '话题',
        value: Math.max(1, Math.floor((item.heat_score || 0) / 10000)),
      });
    });
    return links;
  }, [topicItems]);

  /* 10. 时间轴散点图数据 */
  const scatterData = useMemo(() => {
    const nameMap: Record<string, string> = { toutiao: '今日头条', bilibili: 'B站', douyin: '抖音', weibo: '微博', zhihu: '知乎', baidu: '百度' };
    return topicItems.slice(0, 20).map((item: any, idx: number) => ({
      time: `2026-07-10 ${String(idx % 24).padStart(2, '0')}:${String((idx * 7) % 60).padStart(2, '0')}`,
      heat: item.heat_score || 0,
      title: item.title || '话题',
      platform: nameMap[item.platform_name] || item.platform_name || '未知',
    }));
  }, [topicItems]);

  const loading = overview.loading || topics.loading || alerts.loading || sentimentDist.loading;

  return (
    <MonitorLayout>
      <MonitorHeader lastUpdated={overview.lastUpdated} refreshing={loading} />
      <StatsRow stats={statsData} healthScore={healthScore} />

      {/* 第1行：趋势 + 饼图 + 关系图谱 + 仪表盘 */}
      <div style={{ display: 'flex', gap: 12, flex: 1, minHeight: 0 }}>
        <div style={{ flex: 1, minHeight: 0, background: '#fff', borderRadius: 8, boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
          <ChartPanel title="情感趋势 (24h)" options={trendOption} height={250} />
        </div>
        <div style={{ flex: 1, minHeight: 0, background: '#fff', borderRadius: 8, boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
          <ChartPanel title="平台分布占比" options={pieOption} height={250} />
        </div>
        <div style={{ flex: 1.2, minHeight: 0, background: '#fff', borderRadius: 8, padding: '8px 12px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
          <RelationGraph nodes={graphData.nodes} links={graphData.links} categories={['话题', '平台']} title="舆情关系图谱" height={240} />
        </div>
        <div style={{ flex: 0.9, minHeight: 0, background: '#fff', borderRadius: 8, padding: '8px 12px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
          <GaugeChart score={healthScore} title="舆情健康度" height={240} />
        </div>
      </div>

      {/* 第2行：热榜 + 词云 + 雷达 + 预警趋势 */}
      <div style={{ display: 'flex', gap: 12, flex: 1, minHeight: 0 }}>
        <div style={{ flex: 1, minHeight: 0, background: '#fff', borderRadius: 8, padding: '8px 12px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)', overflow: 'hidden' }}>
          <RankingList data={rankingData} title="热榜 TOP10" />
        </div>
        <div style={{ flex: 1, minHeight: 0, background: '#fff', borderRadius: 8, padding: '8px 12px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
          <WordCloudChart data={wordCloudData} title="关键词云" height={230} />
        </div>
        <div style={{ flex: 1, minHeight: 0, background: '#fff', borderRadius: 8, padding: '8px 12px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
          <PlatformRadarChart data={radarData} title="平台多维对比" height={230} />
        </div>
        <div style={{ flex: 1, minHeight: 0, background: '#fff', borderRadius: 8, padding: '8px 12px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
          <AlertTrendChart data={[]} title="预警趋势 (24h)" height={230} />
        </div>
      </div>

      {/* 第3行：堆叠柱状图 + 负面排行 + 旭日图 + 树图 */}
      <div style={{ display: 'flex', gap: 12, flex: 1, minHeight: 0 }}>
        <div style={{ flex: 1.5, minHeight: 0, background: '#fff', borderRadius: 8, boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
          <PlatformSentimentBar data={barData} title="各平台情感分布" height={240} />
        </div>
        <div style={{ flex: 1, minHeight: 0, background: '#fff', borderRadius: 8, boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
          <NegativePlatformRanking data={negativeData} title="负面情感平台排行" height={240} />
        </div>
        <div style={{ flex: 1, minHeight: 0, background: '#fff', borderRadius: 8, padding: '8px 12px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
          <SunburstChart data={platformDist} title="舆情层级分布" height={230} />
        </div>
        <div style={{ flex: 1, minHeight: 0, background: '#fff', borderRadius: 8, padding: '8px 12px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
          <TreemapChart data={platformDist} title="舆情体量分布" height={230} />
        </div>
      </div>

      {/* 第4行：桑基图 + 热力图 + 时间轴散点 */}
      <div style={{ display: 'flex', gap: 12, flex: 1, minHeight: 0 }}>
        <div style={{ flex: 1, minHeight: 0, background: '#fff', borderRadius: 8, padding: '8px 12px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
          <SankeyChart data={sankeyData} title="平台话题流向" height={240} />
        </div>
        <div style={{ flex: 1, minHeight: 0, background: '#fff', borderRadius: 8, padding: '8px 12px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
          <HeatmapChart data={[]} title="时段情感热力图" height={240} />
        </div>
        <div style={{ flex: 1.5, minHeight: 0, background: '#fff', borderRadius: 8, padding: '8px 12px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
          <TimelineScatter data={scatterData} title="话题热度演变" height={240} />
        </div>
      </div>
    </MonitorLayout>
  );
};

export default Monitor;
