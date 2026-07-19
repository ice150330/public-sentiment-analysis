import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Tag } from 'antd';
import ReactECharts from 'echarts-for-react';
import {
  ApiOutlined,
  CheckCircleOutlined,
  DatabaseOutlined,
  FrownOutlined,
} from '@ant-design/icons';
import { useAuth } from '@/auth/AuthContext';
import { useRealtime } from '@/hooks/useRealtime';
import {
  AlertEvent,
  AlertSummary,
  CrawlLog,
  getAlertEvents,
  getAlertSummary,
  getAuthToken,
  getCrawlLogs,
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
  DataState,
  formatDateTime,
  formatNumber,
  MetricCard,
  Panel,
  PlatformBadge,
  StatusBadge,
} from '@/components/DesignSystem';
import { buildHeatTrendOption, buildSentimentPieOption } from '@/utils/visualData';
import SeverityTag from '../components/SeverityTag';
import { OverviewViewProps } from '../types';

/** 实时概览 —— 指标卡 + 热度趋势/情感分布/平台摘要 + 预警/热榜/采集三栏 */
const RealtimeView: React.FC<OverviewViewProps> = ({ refreshKey, onSyncState }) => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [sentiment, setSentiment] = useState<SentimentDistribution | null>(null);
  const [heatTrend, setHeatTrend] = useState<HeatTrend | null>(null);
  const [topics, setTopics] = useState<HotTopic[]>([]);
  const [alertSummary, setAlertSummary] = useState<AlertSummary | null>(null);
  const [alertEvents, setAlertEvents] = useState<AlertEvent[]>([]);
  const [matrix, setMatrix] = useState<PlatformMonitoringMatrix | null>(null);
  const [logs, setLogs] = useState<CrawlLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      onSyncState({ refreshing: true });
      const [
        overviewRes,
        sentimentRes,
        trendRes,
        topicsRes,
        alertSummaryRes,
        alertEventsRes,
        matrixRes,
        logsRes,
      ] = await Promise.all([
        getOverview(),
        getSentimentDistribution(),
        getHeatTrend({ days: 7, aggregation: 'daily' }),
        getTopics({ page: 1, page_size: 10, sort_by: 'heat_score', sort_order: 'desc' }),
        getAlertSummary(),
        getAlertEvents({ page: 1, page_size: 5, status: 'pending' }),
        getPlatformMonitoringMatrix(),
        getCrawlLogs({ page: 1, page_size: 5 }),
      ]);

      setOverview(overviewRes.data);
      setSentiment(sentimentRes.data);
      setHeatTrend(trendRes.data);
      setTopics(topicsRes.data?.items || []);
      setAlertSummary(alertSummaryRes.data);
      setAlertEvents(alertEventsRes.data?.items || []);
      setMatrix(matrixRes.data);
      setLogs(logsRes.data?.items || []);
      setError(null);
      onSyncState({ refreshing: false, lastUpdated: new Date().toISOString() });
    } catch (err) {
      setError(getErrorMessage(err));
      onSyncState({ refreshing: false });
    } finally {
      setLoading(false);
    }
  }, [onSyncState]);

  useEffect(() => {
    fetchData();
  }, [fetchData, refreshKey]);

  const { lastMessage } = useRealtime({
    token: user ? getAuthToken() || '' : '',
  });

  useEffect(() => {
    if (!lastMessage) return;
    if (lastMessage.type === 'alert' || lastMessage.type === 'crawl_complete') {
      fetchData();
    }
  }, [lastMessage, fetchData]);

  const heatChart = useMemo(() => buildHeatTrendOption(heatTrend), [heatTrend]);
  const sentimentChart = useMemo(() => buildSentimentPieOption(sentiment), [sentiment]);

  const negativePercent = useMemo(() => {
    if (!sentiment || sentiment.total === 0) return null;
    const item = sentiment.distribution.find((entry) => entry.label === 'negative');
    if (!item) return 0;
    return typeof item.percentage === 'number'
      ? item.percentage
      : (item.count / sentiment.total) * 100;
  }, [sentiment]);

  const platformBars = useMemo(() => (matrix?.matrix || []).slice(0, 5), [matrix]);

  return (
    <DataState loading={loading} error={error} empty={!overview} emptyTitle="总览数据不可用">
      <div className="ov-stack">
        <div className="psa-grid metrics">
          <MetricCard
            label="今日热榜"
            value={formatNumber(overview?.today.total_topics)}
            helper="今日采集话题总量"
            icon={<DatabaseOutlined />}
          />
          <MetricCard
            label="活跃平台"
            value={formatNumber(overview?.today.active_platforms)}
            helper={`接入 ${formatNumber(matrix?.total_platforms)} 个平台`}
            icon={<ApiOutlined />}
            tone="positive"
          />
          <MetricCard
            label="负面占比"
            value={negativePercent === null ? '暂无' : `${negativePercent.toFixed(1)}%`}
            helper={`情感样本 ${formatNumber(sentiment?.total)} 条`}
            icon={<FrownOutlined />}
            tone="negative"
          />
          <MetricCard
            label="今日采集成功率"
            value={`${overview?.crawler.today_success_rate ?? 0}%`}
            helper={`最近采集 ${formatDateTime(overview?.crawler.last_run)}`}
            icon={<CheckCircleOutlined />}
            tone="positive"
          />
        </div>

        <div className="psa-dashboard-lead" style={{ marginTop: 0 }}>
          <Panel title="热度趋势" eyebrow={heatTrend?.period} className="psa-panel-flush">
            <DataState empty={!heatChart} emptyTitle="暂无热度趋势">
              <ReactECharts option={heatChart || {}} className="psa-chart psa-chart-wide" />
            </DataState>
          </Panel>
          <Panel title="情感分布" eyebrow={sentiment ? `样本 ${formatNumber(sentiment.total)}` : undefined}>
            <DataState empty={!sentimentChart} emptyTitle="暂无情感分布">
              <ReactECharts option={sentimentChart || {}} className="psa-chart psa-chart-compact" />
            </DataState>
          </Panel>
          <Panel title="平台监测摘要" eyebrow="负面占比 TOP5">
            <DataState empty={platformBars.length === 0} emptyTitle="暂无平台监测数据">
              <div className="psa-score-bars">
                {platformBars.map((item) => (
                  <div className="psa-score-line" key={item.platform_id}>
                    <span>{item.display_name}</span>
                    <div className="psa-bar-track">
                      <div
                        className="psa-bar-fill negative"
                        style={{ width: `${Math.min(100, Math.max(0, item.negative_ratio))}%` }}
                      />
                    </div>
                    <strong>{Math.round(item.negative_ratio)}%</strong>
                  </div>
                ))}
              </div>
            </DataState>
          </Panel>
        </div>

        <div className="ov-grid-3">
          <Panel
            title="实时预警"
            eyebrow={`待处理 ${formatNumber(alertSummary?.pending_count)}`}
            className="psa-panel-tight"
          >
            <DataState empty={alertEvents.length === 0} emptyTitle="暂无待处理预警">
              <div className="psa-list">
                {alertEvents.map((event) => (
                  <button
                    type="button"
                    className="psa-row ov-row-3"
                    key={event.id}
                    onClick={() => navigate('/?view=alerts')}
                  >
                    <SeverityTag severity={event.severity} />
                    <div>
                      <p className="psa-row-title">{event.topic_title || event.rule_name || `预警 #${event.id}`}</p>
                      <div className="psa-row-meta">
                        <span>{event.rule_name || `规则 ${event.rule_id}`}</span>
                        <span>{formatDateTime(event.triggered_at)}</span>
                      </div>
                    </div>
                    <Tag className="psa-tag danger">待处理</Tag>
                  </button>
                ))}
              </div>
            </DataState>
          </Panel>

          <Panel title="热榜 TOP10" eyebrow="按热度排序" className="psa-panel-tight">
            <DataState empty={topics.length === 0} emptyTitle="暂无热榜数据">
              <div className="psa-list">
                {topics.map((topic, index) => (
                  <button
                    type="button"
                    className="psa-row ov-row-3"
                    key={topic.id}
                    onClick={() => navigate('/topics')}
                  >
                    <span className={`ov-rank${index < 3 ? ` top-${index + 1}` : ''}`}>{index + 1}</span>
                    <div>
                      <p className="psa-row-title">{topic.title}</p>
                      <div className="psa-row-meta">
                        <PlatformBadge name={topic.platform_name} />
                        <span>{formatDateTime(topic.crawl_time)}</span>
                      </div>
                    </div>
                    <strong>{formatNumber(topic.heat_score)}</strong>
                  </button>
                ))}
              </div>
            </DataState>
          </Panel>

          <Panel title="最近采集" className="psa-panel-tight">
            <DataState empty={logs.length === 0} emptyTitle="暂无采集日志">
              <div className="psa-list">
                {logs.map((log) => (
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
      </div>
    </DataState>
  );
};

export default RealtimeView;
