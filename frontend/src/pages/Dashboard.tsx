import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Progress, Table } from 'antd';
import {
  AlertOutlined,
  ApiOutlined,
  BarChartOutlined,
  CheckCircleOutlined,
  DatabaseOutlined,
  RadarChartOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import {
  AlertEvent,
  AlertSummary,
  CrawlLog,
  CrawlSuccessRate,
  DataQualityCheck,
  DataQualityFunnel,
  DataQualityIssue,
  getAlertEvents,
  getAlertSummary,
  getCrawlLogs,
  getCrawlSuccessRate,
  getDataQualityChecks,
  getDataQualityFunnel,
  getErrorMessage,
  getTopics,
  getHeatTrend,
  getOverview,
  getPlatforms,
  getSentimentDistribution,
  getTypedDataQualityIssues,
  HeatTrend,
  HotTopic,
  Overview,
  Platform,
  SentimentDistribution,
} from '../services/api';
import {
  DataState,
  formatDateTime,
  formatNumber,
  MetricCard,
  ModuleFrame,
  Panel,
  PlatformBadge,
  StatusBadge,
  SubView,
} from '../components/DesignSystem';
import { RankingList } from '../components/common/RankingList';
import AlertTrendChart from '../components/visual/AlertTrendChart';
import GaugeChart from '../components/visual/GaugeChart';
import HeatmapChart from '../components/visual/HeatmapChart';
import NegativePlatformRanking from '../components/visual/NegativePlatformRanking';
import PlatformRadarChart from '../components/visual/PlatformRadarChart';
import PlatformSentimentBar from '../components/visual/PlatformSentimentBar';
import RelationGraph from '../components/visual/RelationGraph';
import SankeyChart from '../components/visual/SankeyChart';
import TimelineScatter from '../components/visual/TimelineScatter';
import TreemapChart from '../components/visual/TreemapChart';
import WordCloudChart from '../components/visual/WordCloudChart';
import {
  buildAlertTrendData,
  buildHealthScore,
  buildHeatmapData,
  buildHeatTrendOption,
  buildNegativeData,
  buildRadarData,
  buildRankingData,
  buildRelationData,
  buildSankeyData,
  buildSentimentPieOption,
  buildTimelineData,
  buildWordCloudData,
  normalizePlatformSentiment,
} from './dashboardVisualData';

const views: SubView[] = [
  { key: 'overview', label: '实时概览', icon: <BarChartOutlined /> },
  { key: 'visual', label: '可视研判', icon: <RadarChartOutlined /> },
  { key: 'platforms', label: '平台监测', icon: <ApiOutlined /> },
  { key: 'alerts', label: '预警中心', icon: <AlertOutlined /> },
  { key: 'quality', label: '数据质量', icon: <RadarChartOutlined /> },
];

const Dashboard: React.FC<{ initialView?: string }> = ({ initialView = 'overview' }) => {
  const [activeView, setActiveView] = useState(initialView);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [sentiment, setSentiment] = useState<SentimentDistribution | null>(null);
  const [heatTrend, setHeatTrend] = useState<HeatTrend | null>(null);
  const [crawlRate, setCrawlRate] = useState<CrawlSuccessRate | null>(null);
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [topics, setTopics] = useState<HotTopic[]>([]);
  const [alertSummary, setAlertSummary] = useState<AlertSummary | null>(null);
  const [alertEvents, setAlertEvents] = useState<AlertEvent[]>([]);
  const [logs, setLogs] = useState<CrawlLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [
        overviewRes,
        sentimentRes,
        trendRes,
        crawlRateRes,
        platformsRes,
        logsRes,
        topicsRes,
        alertSummaryRes,
        alertEventsRes,
      ] = await Promise.all([
        getOverview(),
        getSentimentDistribution(),
        getHeatTrend({ days: 7, aggregation: 'daily' }),
        getCrawlSuccessRate({ days: 7 }),
        getPlatforms(),
        getCrawlLogs({ page: 1, page_size: 6 }),
        getTopics({ page: 1, page_size: 24, sort_by: 'heat_score', sort_order: 'desc' }),
        getAlertSummary(),
        getAlertEvents({ page: 1, page_size: 24 }),
      ]);

      setOverview(overviewRes.data);
      setSentiment(sentimentRes.data);
      setHeatTrend(trendRes.data);
      setCrawlRate(crawlRateRes.data);
      setPlatforms(platformsRes.data || []);
      setLogs(logsRes.data?.items || []);
      setTopics(topicsRes.data?.items || []);
      setAlertSummary(alertSummaryRes.data);
      setAlertEvents(alertEventsRes.data?.items || []);
      setLastUpdated(new Date().toISOString());
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

  useEffect(() => {
    setActiveView(initialView);
  }, [initialView]);

  const heatChart = useMemo(() => buildHeatTrendOption(heatTrend), [heatTrend]);
  const sentimentChart = useMemo(() => buildSentimentPieOption(sentiment), [sentiment]);
  const platformSentiment = useMemo(() => normalizePlatformSentiment(sentiment), [sentiment]);
  const healthScore = useMemo(() => buildHealthScore(overview, sentiment), [overview, sentiment]);
  const rankingData = useMemo(() => buildRankingData(topics), [topics]);
  const wordCloudData = useMemo(() => buildWordCloudData(topics), [topics]);
  const relationData = useMemo(() => buildRelationData(topics), [topics]);
  const radarData = useMemo(() => buildRadarData(platformSentiment, alertSummary), [platformSentiment, alertSummary]);
  const negativeData = useMemo(() => buildNegativeData(platformSentiment), [platformSentiment]);
  const sankeyData = useMemo(() => buildSankeyData(topics), [topics]);
  const timelineData = useMemo(() => buildTimelineData(topics), [topics]);
  const heatmapData = useMemo(() => buildHeatmapData(topics), [topics]);
  const alertTrendData = useMemo(() => buildAlertTrendData(alertEvents), [alertEvents]);

  const renderContent = () => {
    if (activeView === 'platforms') {
      return <PlatformMonitor platforms={platforms} heatTrend={heatTrend} loading={loading} error={error} />;
    }

    if (activeView === 'alerts') {
      return <AlertCenter />;
    }

    if (activeView === 'visual') {
      return (
        <DashboardVisualMatrix
          loading={loading}
          error={error}
          heatChart={heatChart}
          sentimentChart={sentimentChart}
          platformSentiment={platformSentiment}
          rankingData={rankingData}
          wordCloudData={wordCloudData}
          relationData={relationData}
          radarData={radarData}
          negativeData={negativeData}
          sankeyData={sankeyData}
          timelineData={timelineData}
          heatmapData={heatmapData}
          alertTrendData={alertTrendData}
          healthScore={healthScore}
        />
      );
    }

    if (activeView === 'quality') {
      return <DataQuality crawlRate={crawlRate} logs={logs} loading={loading} error={error} />;
    }

    return (
      <DataState loading={loading} error={error} empty={!overview} emptyTitle="总览数据不可用">
        <div className="psa-grid metrics">
          <MetricCard
            label="今日热榜"
            value={formatNumber(overview?.today.total_topics)}
            helper="由 /stats/overview 返回"
            icon={<DatabaseOutlined />}
          />
          <MetricCard
            label="活跃平台"
            value={formatNumber(overview?.today.active_platforms)}
            helper={`${platforms.filter((item) => item.is_active).length} 个启用`}
            icon={<ApiOutlined />}
            tone="positive"
          />
          <MetricCard
            label="已分析情感"
            value={formatNumber(overview?.sentiment.total_analyzed)}
            helper="累计入库结果"
            icon={<RadarChartOutlined />}
          />
          <MetricCard
            label="今日采集成功率"
            value={`${overview?.crawler.today_success_rate ?? 0}%`}
            helper={`最近采集 ${formatDateTime(overview?.crawler.last_run)}`}
            icon={<CheckCircleOutlined />}
            tone="positive"
          />
        </div>

        <div className="psa-dashboard-lead">
          <Panel title="热度趋势" eyebrow={heatTrend?.period} className="psa-panel-flush">
            <DataState empty={!heatChart} emptyTitle="暂无热度趋势">
              <ReactECharts option={heatChart || {}} className="psa-chart psa-chart-wide" />
            </DataState>
          </Panel>
          <Panel title="舆情健康度" eyebrow="由情感分布计算">
            <GaugeChart score={healthScore} title="" height={210} />
          </Panel>
          <Panel title="情感分布" eyebrow={sentiment ? `样本 ${formatNumber(sentiment.total)}` : undefined}>
            <DataState empty={!sentimentChart} emptyTitle="暂无情感分布">
              <ReactECharts option={sentimentChart || {}} className="psa-chart psa-chart-compact" />
            </DataState>
          </Panel>
        </div>

        <div className="psa-dashboard-visual-grid">
          <Panel title="热榜 TOP10" eyebrow="按热度排序" className="psa-panel-tight">
            <DataState empty={rankingData.length === 0} emptyTitle="暂无热榜">
              <RankingList data={rankingData} visibleCount={8} title="" />
            </DataState>
          </Panel>
          <Panel title="关键词云" eyebrow="由热榜标题提取" className="psa-panel-tight">
            <DataState empty={wordCloudData.length === 0} emptyTitle="暂无关键词">
              <WordCloudChart data={wordCloudData} title="" height={250} />
            </DataState>
          </Panel>
          <Panel title="关系图谱" eyebrow="话题与平台关联" className="psa-panel-span-2">
            <DataState empty={relationData.nodes.length === 0} emptyTitle="暂无关系图谱">
              <RelationGraph nodes={relationData.nodes} links={relationData.links} categories={['话题', '平台']} title="" height={300} />
            </DataState>
          </Panel>
          <Panel title="平台情感分布" eyebrow="正负中性堆叠" className="psa-panel-span-2">
            <DataState empty={Object.keys(platformSentiment).length === 0} emptyTitle="暂无平台情感分布">
              <PlatformSentimentBar data={platformSentiment} title="" height={270} />
            </DataState>
          </Panel>
          <Panel title="负面平台排行" eyebrow="按负面样本数">
            <DataState empty={Object.keys(negativeData).length === 0} emptyTitle="暂无负面排行">
              <NegativePlatformRanking data={negativeData} title="" height={270} />
            </DataState>
          </Panel>
          <Panel title="预警趋势" eyebrow={`待处理 ${formatNumber(alertSummary?.pending_count)}`}>
            <DataState empty={alertTrendData.length === 0} emptyTitle="暂无预警趋势">
              <AlertTrendChart data={alertTrendData} title="" height={270} />
            </DataState>
          </Panel>
        </div>

        <div className="psa-grid two-one" style={{ marginTop: 16 }}>
          <Panel title="多维平台雷达" eyebrow="体量、情感与风险综合">
            <DataState empty={Object.keys(radarData).length === 0} emptyTitle="暂无平台雷达">
              <PlatformRadarChart data={radarData} title="" height={280} />
            </DataState>
          </Panel>
          <Panel title="最近采集">
            <DataState empty={logs.length === 0} emptyTitle="暂无采集日志">
              <div className="psa-list">
                {logs.slice(0, 5).map((log) => (
                  <div className="psa-row" key={log.id}>
                    <div>
                      <p className="psa-row-title">{log.platform_name || `平台 ${log.platform_id}`}</p>
                      <div className="psa-row-meta">
                        <span>{formatDateTime(log.started_at)}</span>
                        <span>{formatNumber(log.records_count)} 条</span>
                      </div>
                    </div>
                    <StatusBadge status={log.status} />
                  </div>
                ))}
              </div>
            </DataState>
          </Panel>
        </div>

        <div className="psa-dashboard-secondary-grid">
          <Panel title="平台话题流向" eyebrow="热度权重映射">
            <DataState empty={sankeyData.length === 0} emptyTitle="暂无流向数据">
              <SankeyChart data={sankeyData} title="" height={250} />
            </DataState>
          </Panel>
          <Panel title="时段热力矩阵" eyebrow="按采集时间与平台聚合">
            <DataState empty={heatmapData.length === 0} emptyTitle="暂无热力矩阵">
              <HeatmapChart data={heatmapData} title="" height={250} />
            </DataState>
          </Panel>
          <Panel title="话题热度演变" eyebrow="热榜采集时间线">
            <DataState empty={timelineData.length === 0} emptyTitle="暂无时间线">
              <TimelineScatter data={timelineData} title="" height={250} />
            </DataState>
          </Panel>
          <Panel title="舆情体量分布" eyebrow="平台与情感层级">
            <DataState empty={Object.keys(platformSentiment).length === 0} emptyTitle="暂无体量分布">
              <TreemapChart data={platformSentiment} title="" height={250} />
            </DataState>
          </Panel>
        </div>
      </DataState>
    );
  };

  return (
    <ModuleFrame
      moduleLabel="总览"
      activeView={activeView}
      views={views}
      onViewChange={setActiveView}
      onRefresh={fetchData}
      refreshing={loading}
      lastUpdated={lastUpdated}
    >
      {renderContent()}
    </ModuleFrame>
  );
};

const DashboardVisualMatrix: React.FC<{
  loading: boolean;
  error: string | null;
  heatChart: any;
  sentimentChart: any;
  platformSentiment: Record<string, { positive: number; negative: number; neutral: number }>;
  rankingData: Array<{ id: string | number; rank: number; title: string; heat: number; platform: string; sentiment: 'positive' | 'neutral' | 'negative' }>;
  wordCloudData: Array<{ name: string; value: number }>;
  relationData: {
    nodes: Array<{ id: string; name: string; category: number; value?: number; symbolSize?: number; itemStyle?: { color: string } }>;
    links: Array<{ source: string; target: string; value?: number }>;
  };
  radarData: Record<string, { heat: number; positive: number; negative: number; neutral: number; alert: number }>;
  negativeData: Record<string, { negative: number; total: number }>;
  sankeyData: Array<{ source: string; target: string; value: number }>;
  timelineData: Array<{ time: string; heat: number; title: string; platform: string }>;
  heatmapData: Array<[string, string, number]>;
  alertTrendData: Array<{ time: string; count: number; severity: 'P1' | 'P2' | 'P3' | 'P4' }>;
  healthScore: number;
}> = ({
  loading,
  error,
  heatChart,
  sentimentChart,
  platformSentiment,
  rankingData,
  wordCloudData,
  relationData,
  radarData,
  negativeData,
  sankeyData,
  timelineData,
  heatmapData,
  alertTrendData,
  healthScore,
}) => (
  <DataState loading={loading} error={error} empty={!heatChart && relationData.nodes.length === 0} emptyTitle="可视研判数据不可用">
    <div className="psa-visual-summary">
      <Panel title="实时热度主线" eyebrow="跨平台趋势">
        <DataState empty={!heatChart} emptyTitle="暂无热度主线">
          <ReactECharts option={heatChart || {}} className="psa-chart psa-chart-wide" />
        </DataState>
      </Panel>
      <Panel title="舆情健康度" eyebrow="综合情绪评分">
        <GaugeChart score={healthScore} title="" height={230} />
      </Panel>
      <Panel title="情感占比" eyebrow="整体样本">
        <DataState empty={!sentimentChart} emptyTitle="暂无情感占比">
          <ReactECharts option={sentimentChart || {}} className="psa-chart psa-chart-compact" />
        </DataState>
      </Panel>
    </div>

    <div className="psa-dashboard-visual-grid">
      <Panel title="舆情关系图谱" eyebrow="热点与平台网络" className="psa-panel-span-2">
        <DataState empty={relationData.nodes.length === 0} emptyTitle="暂无图谱数据">
          <RelationGraph nodes={relationData.nodes} links={relationData.links} categories={['话题', '平台']} title="" height={330} />
        </DataState>
      </Panel>
      <Panel title="热榜滚动排行" eyebrow="前 10 热点" className="psa-panel-tight">
        <DataState empty={rankingData.length === 0} emptyTitle="暂无热榜数据">
          <RankingList data={rankingData} visibleCount={10} title="" />
        </DataState>
      </Panel>
      <Panel title="关键词云" eyebrow="标题关键词聚合" className="psa-panel-tight">
        <DataState empty={wordCloudData.length === 0} emptyTitle="暂无关键词">
          <WordCloudChart data={wordCloudData} title="" height={290} />
        </DataState>
      </Panel>
      <Panel title="多维平台雷达" eyebrow="体量、情绪、风险">
        <DataState empty={Object.keys(radarData).length === 0} emptyTitle="暂无雷达数据">
          <PlatformRadarChart data={radarData} title="" height={300} />
        </DataState>
      </Panel>
      <Panel title="平台情感堆叠" eyebrow="平台样本结构" className="psa-panel-span-2">
        <DataState empty={Object.keys(platformSentiment).length === 0} emptyTitle="暂无平台情感">
          <PlatformSentimentBar data={platformSentiment} title="" height={300} />
        </DataState>
      </Panel>
      <Panel title="负面平台排行" eyebrow="风险排序">
        <DataState empty={Object.keys(negativeData).length === 0} emptyTitle="暂无负面排行">
          <NegativePlatformRanking data={negativeData} title="" height={300} />
        </DataState>
      </Panel>
      <Panel title="预警趋势" eyebrow="按触发时间聚合">
        <DataState empty={alertTrendData.length === 0} emptyTitle="暂无预警趋势">
          <AlertTrendChart data={alertTrendData} title="" height={280} />
        </DataState>
      </Panel>
      <Panel title="时段热力矩阵" eyebrow="时段 × 平台">
        <DataState empty={heatmapData.length === 0} emptyTitle="暂无热力矩阵">
          <HeatmapChart data={heatmapData} title="" height={280} />
        </DataState>
      </Panel>
      <Panel title="平台话题流向" eyebrow="热度权重">
        <DataState empty={sankeyData.length === 0} emptyTitle="暂无流向数据">
          <SankeyChart data={sankeyData} title="" height={280} />
        </DataState>
      </Panel>
      <Panel title="话题时间线" eyebrow="采集时间与热度">
        <DataState empty={timelineData.length === 0} emptyTitle="暂无时间线">
          <TimelineScatter data={timelineData} title="" height={280} />
        </DataState>
      </Panel>
      <Panel title="舆情体量树图" eyebrow="平台与情感层级">
        <DataState empty={Object.keys(platformSentiment).length === 0} emptyTitle="暂无体量树图">
          <TreemapChart data={platformSentiment} title="" height={280} />
        </DataState>
      </Panel>
    </div>
  </DataState>
);

const PlatformMonitor: React.FC<{
  platforms: Platform[];
  heatTrend: HeatTrend | null;
  loading: boolean;
  error: string | null;
}> = ({ platforms, heatTrend, loading, error }) => {
  const trendRows = heatTrend?.series || [];

  return (
    <DataState loading={loading} error={error} empty={platforms.length === 0} emptyTitle="暂无平台配置">
      <div className="psa-grid two-one">
        <Panel title="平台接入状态" className="tall">
          <div className="psa-list">
            {platforms.map((platform) => (
              <div className="psa-row" key={platform.id}>
                <div>
                  <p className="psa-row-title">{platform.display_name}</p>
                  <div className="psa-row-meta">
                    <PlatformBadge name={platform.name} />
                    <span>{platform.base_url || '未配置 URL'}</span>
                  </div>
                </div>
                <StatusBadge status={platform.is_active} />
              </div>
            ))}
          </div>
        </Panel>
        <Panel title="平台热度监测" eyebrow={heatTrend?.period}>
          <DataState empty={trendRows.length === 0} emptyTitle="暂无平台趋势">
            <div className="psa-list">
              {trendRows.map((series) => {
                const latest = series.data[series.data.length - 1];
                return (
                  <div className="psa-row" key={series.platform}>
                    <div>
                      <p className="psa-row-title">{series.platform}</p>
                      <div className="psa-row-meta">
                        <span>话题 {formatNumber(latest?.topic_count)}</span>
                        <span>最高热度 {formatNumber(latest?.max_heat)}</span>
                      </div>
                    </div>
                    <strong>{formatNumber(latest?.avg_heat)}</strong>
                  </div>
                );
              })}
            </div>
          </DataState>
        </Panel>
      </div>
    </DataState>
  );
};

const AlertCenter: React.FC = () => {
  const [summary, setSummary] = useState<AlertSummary | null>(null);
  const [events, setEvents] = useState<AlertEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAlerts = useCallback(async () => {
    try {
      setLoading(true);
      const [summaryRes, eventsRes] = await Promise.all([
        getAlertSummary(),
        getAlertEvents({ page: 1, page_size: 8 }),
      ]);
      setSummary(summaryRes.data);
      setEvents(eventsRes.data?.items || []);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  const severityRows = Object.entries(summary?.severity_distribution || {});

  return (
    <DataState loading={loading} error={error} empty={!summary} emptyTitle="暂无预警摘要">
      <div className="psa-grid two-one">
        <Panel title="预警队列" className="tall" eyebrow={`待处理 ${formatNumber(summary?.pending_count)}`}>
          <DataState empty={events.length === 0} emptyTitle="暂无预警事件" emptyDescription="当前没有待展示的预警事件。">
            <div className="psa-list">
              {events.map((event) => (
                <div className="psa-row" key={event.id}>
                  <div>
                    <p className="psa-row-title">{event.topic_title || event.rule_name || `预警 #${event.id}`}</p>
                    <div className="psa-row-meta">
                      <span>{event.rule_name || `规则 ${event.rule_id}`}</span>
                      <span>{formatDateTime(event.triggered_at)}</span>
                    </div>
                  </div>
                  <StatusBadge status={`${event.severity} ${event.status}`} />
                </div>
              ))}
            </div>
          </DataState>
        </Panel>
        <div className="psa-grid">
          <Panel title="级别分布" eyebrow={summary?.max_severity ? `最高 ${summary.max_severity}` : undefined}>
            <DataState empty={severityRows.length === 0} emptyTitle="暂无级别分布">
              <div className="psa-list">
                {severityRows.map(([severity, count]) => (
                  <div className="psa-score-line" key={severity}>
                    <span>{severity}</span>
                    <Progress
                      percent={Math.round((count / Math.max(1, summary?.pending_count || count)) * 100)}
                      showInfo={false}
                      strokeColor="#E11D48"
                    />
                    <strong>{formatNumber(count)}</strong>
                  </div>
                ))}
              </div>
            </DataState>
          </Panel>
          <Panel title="最近预警">
            <DataState empty={!summary?.latest_alert} emptyTitle="暂无最近预警">
              {summary?.latest_alert && (
                <div className="psa-detail-list">
                  <div className="psa-detail-item">
                    <span>事件 ID</span>
                    <strong>#{summary.latest_alert.id}</strong>
                  </div>
                  <div className="psa-detail-item">
                    <span>级别</span>
                    <strong>{summary.latest_alert.severity}</strong>
                  </div>
                  <div className="psa-detail-item">
                    <span>触发时间</span>
                    <strong>{formatDateTime(summary.latest_alert.triggered_at)}</strong>
                  </div>
                </div>
              )}
            </DataState>
          </Panel>
        </div>
      </div>
    </DataState>
  );
};

const DataQuality: React.FC<{
  crawlRate: CrawlSuccessRate | null;
  logs: CrawlLog[];
  loading: boolean;
  error: string | null;
}> = ({ crawlRate, logs, loading, error }) => {
  const [funnel, setFunnel] = useState<DataQualityFunnel | null>(null);
  const [checks, setChecks] = useState<DataQualityCheck[]>([]);
  const [issues, setIssues] = useState<DataQualityIssue[]>([]);
  const [qualityLoading, setQualityLoading] = useState(true);
  const [qualityError, setQualityError] = useState<string | null>(null);

  const fetchQuality = useCallback(async () => {
    try {
      setQualityLoading(true);
      const [funnelRes, checksRes, issuesRes] = await Promise.all([
        getDataQualityFunnel(),
        getDataQualityChecks(),
        getTypedDataQualityIssues({ page: 1, page_size: 6 }),
      ]);
      setFunnel(funnelRes.data);
      setChecks(checksRes.data?.checks || []);
      setIssues(issuesRes.data?.items || []);
      setQualityError(null);
    } catch (err) {
      setQualityError(getErrorMessage(err));
    } finally {
      setQualityLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchQuality();
  }, [fetchQuality]);

  return (
    <DataState loading={loading || qualityLoading} error={error || qualityError} empty={!crawlRate && !funnel} emptyTitle="数据质量不可用">
      <div className="psa-grid two-one">
        <div className="psa-grid">
          <Panel title="处理漏斗" eyebrow={funnel ? `${funnel.date} 留存 ${funnel.retention_rate}%` : undefined}>
            <DataState empty={!funnel || funnel.funnel.length === 0} emptyTitle="暂无处理漏斗">
              <div className="psa-list">
                {funnel?.funnel.map((stage) => (
                  <div className="psa-score-line" key={stage.stage}>
                    <span>{stage.stage}</span>
                    <Progress
                      percent={Math.min(100, Math.round((stage.count / Math.max(1, funnel.funnel[0]?.count || stage.count)) * 100))}
                      showInfo={false}
                      strokeColor="#2563EB"
                    />
                    <strong>{formatNumber(stage.count)}</strong>
                  </div>
                ))}
              </div>
            </DataState>
          </Panel>
          <Panel title="质量检查">
            <DataState empty={checks.length === 0} emptyTitle="暂无质量检查项">
              <div className="psa-list">
                {checks.map((check) => (
                  <div className="psa-row" key={check.name}>
                    <div>
                      <p className="psa-row-title">{check.name}</p>
                      <div className="psa-row-meta">
                        <span>阈值 {formatNumber(check.threshold)}</span>
                        <span>{check.pass_rate !== undefined ? `${check.pass_rate}%` : `${formatNumber(check.count)} 项`}</span>
                      </div>
                    </div>
                    <StatusBadge status={check.status} />
                  </div>
                ))}
              </div>
            </DataState>
          </Panel>
        </div>
        <Panel title="待处理问题" className="tall">
          <DataState empty={issues.length === 0} emptyTitle="暂无数据质量问题">
            <Table<DataQualityIssue>
              className="psa-table"
              size="small"
              rowKey="id"
              pagination={false}
              dataSource={issues}
              columns={[
                { title: '类型', dataIndex: 'issue_type' },
                { title: '平台', render: (_, record) => record.platform_name || '全部' },
                { title: '级别', render: (_, record) => <StatusBadge status={record.severity} /> },
                { title: '状态', render: (_, record) => <StatusBadge status={record.status} /> },
                { title: '时间', dataIndex: 'created_at', render: (value) => formatDateTime(value) },
              ]}
            />
          </DataState>
        </Panel>
      </div>
      <div className="psa-grid two" style={{ marginTop: 16 }}>
        <Panel title="采集成功率" eyebrow={crawlRate?.period}>
          <DataState empty={!crawlRate || crawlRate.total === 0} emptyTitle="暂无采集质量统计">
            <div className="psa-list">
              {crawlRate?.rates.map((rate) => (
                <div className="psa-score-line" key={rate.status}>
                  <span>{rate.status}</span>
                  <Progress percent={rate.percentage} showInfo={false} strokeColor="#2563EB" />
                  <strong>{rate.percentage}%</strong>
                </div>
              ))}
            </div>
          </DataState>
        </Panel>
        <Panel title="采集日志校验">
          <Table<CrawlLog>
            className="psa-table"
            size="small"
            rowKey="id"
            pagination={false}
            dataSource={logs}
            locale={{ emptyText: '暂无采集日志' }}
            columns={[
              { title: '平台', render: (_, record) => record.platform_name || `平台 ${record.platform_id}` },
              { title: '状态', render: (_, record) => <StatusBadge status={record.status} /> },
              { title: '记录数', dataIndex: 'records_count', render: (value) => formatNumber(value) },
              { title: '开始时间', dataIndex: 'started_at', render: (value) => formatDateTime(value) },
            ]}
          />
        </Panel>
      </div>
    </DataState>
  );
};

export default Dashboard;
