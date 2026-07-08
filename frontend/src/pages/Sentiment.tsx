import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Input, Table } from 'antd';
import {
  AreaChartOutlined,
  FileSearchOutlined,
  ScanOutlined,
  SendOutlined,
  TableOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import {
  analyzeBatch,
  analyzeText,
  forecastHeat,
  ForecastHeat,
  getErrorMessage,
  getHeatTrend,
  getSentimentSummary,
  getSentimentResults,
  HeatTrend,
  SentimentAnalyzeResult,
  SentimentResult,
  SentimentSummary,
} from '../services/api';
import {
  DataState,
  formatDateTime,
  ModuleFrame,
  Panel,
  SentimentBadge,
  sentimentText,
  SubView,
} from '../components/DesignSystem';

const views: SubView[] = [
  { key: 'text', label: '文本分析', icon: <FileSearchOutlined /> },
  { key: 'batch', label: '批量结果', icon: <TableOutlined /> },
  { key: 'forecast', label: '趋势预测', icon: <AreaChartOutlined /> },
  { key: 'explain', label: '模型解释', icon: <ScanOutlined /> },
];

const scoreLabels = [
  { key: 'positive', label: '正面', className: 'positive' },
  { key: 'negative', label: '负面', className: 'negative' },
  { key: 'neutral', label: '中性', className: 'neutral' },
] as const;

const Sentiment: React.FC = () => {
  const [activeView, setActiveView] = useState('text');
  const [text, setText] = useState('');
  const [batchText, setBatchText] = useState('');
  const [latestResult, setLatestResult] = useState<SentimentAnalyzeResult | null>(null);
  const [batchResults, setBatchResults] = useState<SentimentAnalyzeResult[]>([]);
  const [storedResults, setStoredResults] = useState<SentimentResult[]>([]);
  const [heatTrend, setHeatTrend] = useState<HeatTrend | null>(null);
  const [forecast, setForecast] = useState<ForecastHeat | null>(null);
  const [summary, setSummary] = useState<SentimentSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [pageLoading, setPageLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const fetchExisting = useCallback(async () => {
    try {
      setPageLoading(true);
      const [resultsRes, trendRes, forecastRes, summaryRes] = await Promise.all([
        getSentimentResults({ page: 1, page_size: 12 }),
        getHeatTrend({ days: 14, aggregation: 'daily' }),
        forecastHeat({ horizon_days: 7 }),
        getSentimentSummary(),
      ]);
      setStoredResults(resultsRes.data?.items || []);
      setHeatTrend(trendRes.data);
      setForecast(forecastRes.data);
      setSummary(summaryRes.data);
      setLastUpdated(new Date().toISOString());
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setPageLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchExisting();
  }, [fetchExisting]);

  const runSingleAnalyze = async () => {
    if (!text.trim()) return;
    try {
      setLoading(true);
      const res = await analyzeText(text.trim());
      setLatestResult(res.data);
      setActiveView('explain');
      setLastUpdated(new Date().toISOString());
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const runBatchAnalyze = async () => {
    const texts = batchText.split('\n').map((item) => item.trim()).filter(Boolean);
    if (texts.length === 0) return;
    try {
      setLoading(true);
      const res = await analyzeBatch(texts);
      setBatchResults(res.data || []);
      setActiveView('batch');
      setLastUpdated(new Date().toISOString());
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const forecastChart = useMemo(() => {
    if (forecast?.forecast?.length) {
      return {
        tooltip: { trigger: 'axis' },
        grid: { left: 48, right: 18, top: 30, bottom: 28 },
        xAxis: { type: 'category', data: forecast.forecast.map((point) => point.date), axisLabel: { color: '#64748B' } },
        yAxis: { type: 'value', splitLine: { lineStyle: { color: '#E7EEF7' } } },
        series: [
          {
            name: '预测热度',
            type: 'line',
            smooth: true,
            data: forecast.forecast.map((point) => point.predicted_heat),
          },
          {
            name: '置信上界',
            type: 'line',
            smooth: true,
            symbol: 'none',
            lineStyle: { type: 'dashed' },
            data: forecast.forecast.map((point) => point.confidence_upper),
          },
          {
            name: '置信下界',
            type: 'line',
            smooth: true,
            symbol: 'none',
            lineStyle: { type: 'dashed' },
            data: forecast.forecast.map((point) => point.confidence_lower),
          },
        ],
      };
    }

    const series = heatTrend?.series?.filter((item) => item.data.length > 0) || [];
    if (series.length === 0) return null;
    const dates = Array.from(new Set(series.flatMap((item) => item.data.map((point) => point.date))));
    return {
      tooltip: { trigger: 'axis' },
      legend: { top: 0, textStyle: { color: '#64748B', fontWeight: 700 } },
      grid: { left: 40, right: 18, top: 44, bottom: 28 },
      xAxis: { type: 'category', data: dates, axisLabel: { color: '#64748B' } },
      yAxis: { type: 'value', splitLine: { lineStyle: { color: '#E7EEF7' } } },
      series: series.map((item) => ({
        name: item.platform,
        type: 'line',
        smooth: true,
        data: dates.map((date) => item.data.find((point) => point.date === date)?.avg_heat ?? null),
      })),
    };
  }, [forecast, heatTrend]);

  const resultChart = useMemo(() => {
    if (!latestResult) return null;
    return {
      radar: {
        indicator: [
          { name: '正面', max: 1 },
          { name: '负面', max: 1 },
          { name: '中性', max: 1 },
        ],
        radius: '62%',
      },
      series: [
        {
          type: 'radar',
          areaStyle: { color: 'rgba(37, 99, 235, 0.18)' },
          lineStyle: { color: '#2563EB' },
          data: [
            {
              value: [
                latestResult.scores.positive,
                latestResult.scores.negative,
                latestResult.scores.neutral,
              ],
            },
          ],
        },
      ],
    };
  }, [latestResult]);

  const renderContent = () => {
    if (activeView === 'batch') {
      const data = batchResults.length > 0 ? batchResults : [];
      return (
        <div className="psa-grid one-two">
          <Panel title="批量输入">
            <div className="psa-input-panel">
              <Input.TextArea
                className="psa-textarea"
                value={batchText}
                onChange={(event) => setBatchText(event.target.value)}
                placeholder="每行输入一条待分析文本"
                rows={8}
              />
              <div className="psa-actions">
                <Button type="primary" icon={<SendOutlined />} onClick={runBatchAnalyze} loading={loading}>
                  批量分析
                </Button>
              </div>
            </div>
          </Panel>
          <Panel title="批量结果">
            <DataState loading={loading} error={error} empty={data.length === 0} emptyTitle="暂无批量分析结果">
              <Table<SentimentAnalyzeResult>
                className="psa-table"
                size="small"
                rowKey={(record) => `${record.text}-${record.analyzed_at}`}
                pagination={false}
                dataSource={data}
                columns={[
                  { title: '文本', dataIndex: 'text', ellipsis: true },
                  { title: '情感', render: (_, record) => <SentimentBadge label={record.sentiment_label} confidence={record.confidence} /> },
                  { title: '时间', dataIndex: 'analyzed_at', render: (value) => formatDateTime(value) },
                ]}
              />
            </DataState>
          </Panel>
        </div>
      );
    }

    if (activeView === 'forecast') {
      return (
        <div className="psa-grid two-one">
          <Panel title="趋势预测" eyebrow={forecast ? forecast.model : heatTrend?.period}>
            <DataState loading={pageLoading} error={error} empty={!forecastChart} emptyTitle="暂无趋势数据">
              <ReactECharts option={forecastChart || {}} className="psa-chart large" />
            </DataState>
          </Panel>
          <div className="psa-grid">
            <Panel title="分析摘要">
              <DataState loading={pageLoading} error={error} empty={!summary} emptyTitle="暂无分析摘要">
                <div className="psa-detail-list">
                  <div className="psa-detail-item">
                    <span>今日分析</span>
                    <strong>{summary?.today_analyzed ?? 0}</strong>
                  </div>
                  <div className="psa-detail-item">
                    <span>低置信</span>
                    <strong>{summary?.low_confidence ?? 0}</strong>
                  </div>
                  <div className="psa-detail-item">
                    <span>负向样本</span>
                    <strong>{summary?.negative_samples ?? 0}</strong>
                  </div>
                  <div className="psa-detail-item">
                    <span>平均置信</span>
                    <strong>{((summary?.avg_confidence || 0) * 100).toFixed(1)}%</strong>
                  </div>
                </div>
              </DataState>
            </Panel>
            <Panel title="已入库情感结果">
              <DataState loading={pageLoading} error={error} empty={storedResults.length === 0} emptyTitle="暂无入库情感结果">
                <div className="psa-list">
                  {storedResults.slice(0, 6).map((item) => (
                    <div className="psa-row" key={item.id}>
                      <div>
                        <p className="psa-row-title">Topic #{item.topic_id}</p>
                        <div className="psa-row-meta">
                          <span>{formatDateTime(item.analyzed_at)}</span>
                          <span>{item.model_version || '未标注模型'}</span>
                        </div>
                      </div>
                      <SentimentBadge label={item.sentiment_label} confidence={item.confidence} />
                    </div>
                  ))}
                </div>
              </DataState>
            </Panel>
          </div>
        </div>
      );
    }

    if (activeView === 'explain') {
      return (
        <div className="psa-grid two-one">
          <Panel title="模型解释">
            <DataState empty={!latestResult} emptyTitle="暂无可解释结果" emptyDescription="提交文本分析后，此处展示后端返回的真实概率分布。">
              {latestResult && (
                <div className="psa-detail-list">
                  <p className="psa-row-title">{latestResult.text}</p>
                  <SentimentBadge label={latestResult.sentiment_label} confidence={latestResult.confidence} />
                  <div className="psa-score-bars">
                    {scoreLabels.map((item) => (
                      <div className="psa-score-line" key={item.key}>
                        <span>{item.label}</span>
                        <div className="psa-bar-track">
                          <div
                            className={`psa-bar-fill ${item.className}`}
                            style={{ width: `${Math.round(latestResult.scores[item.key] * 100)}%` }}
                          />
                        </div>
                        <strong>{(latestResult.scores[item.key] * 100).toFixed(1)}%</strong>
                      </div>
                    ))}
                  </div>
                  <div className="psa-detail-item">
                    <span>模型版本</span>
                    <strong>{latestResult.model_version || '未返回'}</strong>
                  </div>
                </div>
              )}
            </DataState>
          </Panel>
          <Panel title="概率雷达">
            <DataState empty={!resultChart} emptyTitle="暂无概率图">
              <ReactECharts option={resultChart || {}} className="psa-chart" />
            </DataState>
          </Panel>
        </div>
      );
    }

    return (
      <div className="psa-grid one-two">
        <Panel title="文本输入" eyebrow="单条分析">
          <div className="psa-input-panel">
            <Input.TextArea
              className="psa-textarea"
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder="输入要分析的中文文本"
              rows={6}
              maxLength={4096}
              showCount
            />
            <div className="psa-actions">
              <Button type="primary" icon={<SendOutlined />} onClick={runSingleAnalyze} loading={loading}>
                分析文本
              </Button>
            </div>
          </div>
        </Panel>
        <Panel title="最近一次结果">
          <DataState loading={loading} error={error} empty={!latestResult} emptyTitle="暂无分析结果">
            {latestResult && (
              <div className="psa-detail-list">
                <SentimentBadge label={latestResult.sentiment_label} confidence={latestResult.confidence} />
                <p className="psa-page-note">{latestResult.text}</p>
                <div className="psa-detail-item">
                  <span>分析时间</span>
                  <strong>{formatDateTime(latestResult.analyzed_at)}</strong>
                </div>
                <div className="psa-detail-item">
                  <span>倾向</span>
                  <strong>{sentimentText(latestResult.sentiment_label)}</strong>
                </div>
              </div>
            )}
          </DataState>
        </Panel>
      </div>
    );
  };

  return (
    <ModuleFrame
      moduleLabel="分析"
      activeView={activeView}
      views={views}
      onViewChange={setActiveView}
      onRefresh={fetchExisting}
      refreshing={pageLoading || loading}
      lastUpdated={lastUpdated}
    >
      {renderContent()}
    </ModuleFrame>
  );
};

export default Sentiment;
