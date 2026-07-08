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
  CrawlLog,
  CrawlSuccessRate,
  getCrawlLogs,
  getCrawlSuccessRate,
  getErrorMessage,
  getHeatTrend,
  getOverview,
  getPlatforms,
  getSentimentDistribution,
  HeatTrend,
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
  SectionNotice,
  StatusBadge,
  SubView,
} from '../components/DesignSystem';

const views: SubView[] = [
  { key: 'overview', label: '实时概览', icon: <BarChartOutlined /> },
  { key: 'platforms', label: '平台监测', icon: <ApiOutlined /> },
  { key: 'alerts', label: '预警中心', icon: <AlertOutlined /> },
  { key: 'quality', label: '数据质量', icon: <RadarChartOutlined /> },
];

const Dashboard: React.FC = () => {
  const [activeView, setActiveView] = useState('overview');
  const [overview, setOverview] = useState<Overview | null>(null);
  const [sentiment, setSentiment] = useState<SentimentDistribution | null>(null);
  const [heatTrend, setHeatTrend] = useState<HeatTrend | null>(null);
  const [crawlRate, setCrawlRate] = useState<CrawlSuccessRate | null>(null);
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [logs, setLogs] = useState<CrawlLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [overviewRes, sentimentRes, trendRes, crawlRateRes, platformsRes, logsRes] = await Promise.all([
        getOverview(),
        getSentimentDistribution(),
        getHeatTrend({ days: 7, aggregation: 'daily' }),
        getCrawlSuccessRate({ days: 7 }),
        getPlatforms(),
        getCrawlLogs({ page: 1, page_size: 6 }),
      ]);

      setOverview(overviewRes.data);
      setSentiment(sentimentRes.data);
      setHeatTrend(trendRes.data);
      setCrawlRate(crawlRateRes.data);
      setPlatforms(platformsRes.data || []);
      setLogs(logsRes.data || []);
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

  const sentimentChart = useMemo(() => {
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
          itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
          label: { formatter: '{b} {d}%', color: '#152033', fontWeight: 700 },
          data: sentiment.distribution.map((item) => ({
            name: item.label,
            value: item.count,
          })),
        },
      ],
    };
  }, [sentiment]);

  const heatChart = useMemo(() => {
    const series = heatTrend?.series?.filter((item) => item.data.length > 0) || [];
    if (series.length === 0) return null;

    const dates = Array.from(new Set(series.flatMap((item) => item.data.map((point) => point.date))));

    return {
      tooltip: { trigger: 'axis' },
      legend: { top: 0, textStyle: { color: '#64748B', fontWeight: 700 } },
      grid: { left: 36, right: 16, top: 44, bottom: 26 },
      xAxis: { type: 'category', data: dates, axisLabel: { color: '#64748B' } },
      yAxis: { type: 'value', axisLabel: { color: '#64748B' }, splitLine: { lineStyle: { color: '#E7EEF7' } } },
      series: series.map((item) => ({
        name: item.platform,
        type: 'line',
        smooth: true,
        symbolSize: 6,
        data: dates.map((date) => item.data.find((point) => point.date === date)?.avg_heat ?? null),
      })),
    };
  }, [heatTrend]);

  const platformChart = useMemo(() => {
    if (!sentiment?.by_platform) return null;
    const names = Object.keys(sentiment.by_platform);
    if (names.length === 0) return null;

    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 72, right: 18, top: 16, bottom: 24 },
      xAxis: { type: 'value', splitLine: { lineStyle: { color: '#E7EEF7' } } },
      yAxis: { type: 'category', data: names, axisLabel: { color: '#64748B', fontWeight: 700 } },
      series: [
        {
          name: '情感记录',
          type: 'bar',
          barWidth: 10,
          itemStyle: { color: '#2563EB', borderRadius: 999 },
          data: names.map((name) => {
            const item = sentiment.by_platform?.[name] || {};
            return Object.values(item).reduce((sum, value) => sum + value, 0);
          }),
        },
      ],
    };
  }, [sentiment]);

  const renderContent = () => {
    if (activeView === 'platforms') {
      return <PlatformMonitor platforms={platforms} heatTrend={heatTrend} loading={loading} error={error} />;
    }

    if (activeView === 'alerts') {
      return <AlertCenter />;
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

        <div className="psa-grid two" style={{ marginTop: 16 }}>
          <Panel title="热度趋势" eyebrow={heatTrend?.period}>
            <DataState empty={!heatChart} emptyTitle="暂无热度趋势">
              <ReactECharts option={heatChart || {}} className="psa-chart" />
            </DataState>
          </Panel>
          <Panel title="情感分布" eyebrow={sentiment ? `样本 ${formatNumber(sentiment.total)}` : undefined}>
            <DataState empty={!sentimentChart} emptyTitle="暂无情感分布">
              <ReactECharts option={sentimentChart || {}} className="psa-chart" />
            </DataState>
          </Panel>
        </div>

        <div className="psa-grid two-one" style={{ marginTop: 16 }}>
          <Panel title="平台分布" eyebrow="按真实情感记录聚合">
            <DataState empty={!platformChart} emptyTitle="暂无平台分布">
              <ReactECharts option={platformChart || {}} className="psa-chart" />
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

const AlertCenter: React.FC = () => (
  <div className="psa-grid two-one">
    <Panel title="预警中心" className="tall">
      <SectionNotice
        title="后端尚未提供预警列表接口"
        description="UI.pen 中包含预警中心页面，但当前 FastAPI 只有统计、热榜、情感和爬虫控制接口；这里保留页面结构，不填充虚构预警。"
      />
      <DataState empty emptyTitle="暂无预警数据" emptyDescription="接入真实预警接口后，此处展示按级别排序的事件列表。">
        <div />
      </DataState>
    </Panel>
    <Panel title="处置记录">
      <DataState empty emptyTitle="暂无处置记录" emptyDescription="当前没有可查询的预警处置 API。">
        <div />
      </DataState>
    </Panel>
  </div>
);

const DataQuality: React.FC<{
  crawlRate: CrawlSuccessRate | null;
  logs: CrawlLog[];
  loading: boolean;
  error: string | null;
}> = ({ crawlRate, logs, loading, error }) => (
  <DataState loading={loading} error={error} empty={!crawlRate} emptyTitle="数据质量不可用">
    <div className="psa-grid one-two">
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

export default Dashboard;
