import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Input, Segmented, Select, Table } from 'antd';
import {
  AreaChartOutlined,
  CheckCircleOutlined,
  DownloadOutlined,
  FileSearchOutlined,
  ScanOutlined,
  SendOutlined,
  SettingOutlined,
  StopOutlined,
  TableOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import {
  analyzeBatch,
  analyzeBatchV2,
  analyzeText,
  analyzeTextV2,
  activateModelVersion,
  exportSentimentReportPdf,
  forecastHeat,
  ForecastHeat,
  getErrorMessage,
  getHeatTrend,
  getModelStatus,
  getModelVersions,
  getSentimentReviewQueue,
  getSentimentSummary,
  getSentimentResults,
  HeatTrend,
  ModelStatus,
  ModelVersion,
  SentimentReviewItem,
  SentimentAnalyzeResult,
  SentimentResult,
  SentimentSummary,
  updateSentimentReviewItem,
} from '../services/api';
import {
  DataState,
  formatDateTime,
  formatNumber,
  ModuleFrame,
  Panel,
  SentimentBadge,
  sentimentText,
  StatusBadge,
  SubView,
} from '../components/DesignSystem';

const views: SubView[] = [
  { key: 'text', label: '文本分析', icon: <FileSearchOutlined /> },
  { key: 'batch', label: '批量结果', icon: <TableOutlined /> },
  { key: 'review', label: '人工复核', icon: <CheckCircleOutlined /> },
  { key: 'models', label: '模型版本', icon: <SettingOutlined /> },
  { key: 'forecast', label: '趋势预测', icon: <AreaChartOutlined /> },
  { key: 'explain', label: '模型解释', icon: <ScanOutlined /> },
];

const scoreLabels = [
  { key: 'positive', label: '正面', className: 'positive' },
  { key: 'negative', label: '负面', className: 'negative' },
  { key: 'neutral', label: '中性', className: 'neutral' },
] as const;

const modelModeOptions = [
  { label: '快速模型', value: 'classic' },
  { label: '增强模型', value: 'v2' },
] as const;

const reviewLabelOptions = [
  { label: '正面', value: 'positive' },
  { label: '中性', value: 'neutral' },
  { label: '负面', value: 'negative' },
];

const forecastSignalLabels: Record<string, string> = {
  heat_momentum: '热度动量',
  negative_momentum: '负面压力',
  cross_platform_spread: '跨平台扩散',
};

const forecastDirectionLabels: Record<string, string> = {
  up: '上升',
  down: '下降',
  stable: '稳定',
};

const Sentiment: React.FC = () => {
  const [activeView, setActiveView] = useState('text');
  const [text, setText] = useState('');
  const [batchText, setBatchText] = useState('');
  const [latestResult, setLatestResult] = useState<SentimentAnalyzeResult | null>(null);
  const [batchResults, setBatchResults] = useState<SentimentAnalyzeResult[]>([]);
  const [modelMode, setModelMode] = useState<'classic' | 'v2'>('classic');
  const [storedResults, setStoredResults] = useState<SentimentResult[]>([]);
  const [heatTrend, setHeatTrend] = useState<HeatTrend | null>(null);
  const [forecast, setForecast] = useState<ForecastHeat | null>(null);
  const [summary, setSummary] = useState<SentimentSummary | null>(null);
  const [reviewItems, setReviewItems] = useState<SentimentReviewItem[]>([]);
  const [modelStatus, setModelStatus] = useState<ModelStatus | null>(null);
  const [modelVersions, setModelVersions] = useState<ModelVersion[]>([]);
  const [loading, setLoading] = useState(false);
  const [pageLoading, setPageLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [reviewingId, setReviewingId] = useState<number | null>(null);
  const [activatingVersionId, setActivatingVersionId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const fetchExisting = useCallback(async () => {
    try {
      setPageLoading(true);
      const [resultsRes, trendRes, forecastRes, summaryRes, reviewRes, modelStatusRes, modelVersionsRes] = await Promise.all([
        getSentimentResults({ page: 1, page_size: 12 }),
        getHeatTrend({ days: 14, aggregation: 'daily' }),
        forecastHeat({ horizon_days: 7 }),
        getSentimentSummary(),
        getSentimentReviewQueue({ status: 'pending', threshold: 0.6, page: 1, page_size: 12 }),
        getModelStatus(),
        getModelVersions(),
      ]);
      setStoredResults(resultsRes.data?.items || []);
      setHeatTrend(trendRes.data);
      setForecast(forecastRes.data);
      setSummary(summaryRes.data);
      setReviewItems(reviewRes.data?.items || []);
      setModelStatus(modelStatusRes.data || null);
      setModelVersions(modelVersionsRes.data?.items || []);
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
      const res = modelMode === 'v2'
        ? await analyzeTextV2(text.trim())
        : await analyzeText(text.trim());
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
      const res = modelMode === 'v2'
        ? await analyzeBatchV2(texts)
        : await analyzeBatch(texts);
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

  const exportReport = useCallback(async () => {
    try {
      setExporting(true);
      await exportSentimentReportPdf({ topic_limit: 12 });
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setExporting(false);
    }
  }, []);

  const updateReview = async (item: SentimentReviewItem, status: 'reviewed' | 'ignored', correctedLabel?: string) => {
    try {
      setReviewingId(item.id);
      await updateSentimentReviewItem(item.id, {
        status,
        corrected_label: status === 'reviewed' ? correctedLabel || item.suggested_label : undefined,
      });
      const response = await getSentimentReviewQueue({ status: 'pending', threshold: 0.6, page: 1, page_size: 12 });
      setReviewItems(response.data?.items || []);
      setLastUpdated(new Date().toISOString());
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setReviewingId(null);
    }
  };

  const activateVersion = async (item: ModelVersion, trafficPercent = 100) => {
    try {
      setActivatingVersionId(item.id);
      await activateModelVersion(item.id, { traffic_percent: trafficPercent });
      const [statusRes, versionsRes] = await Promise.all([
        getModelStatus(),
        getModelVersions(),
      ]);
      setModelStatus(statusRes.data || null);
      setModelVersions(versionsRes.data?.items || []);
      setLastUpdated(new Date().toISOString());
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setActivatingVersionId(null);
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
              <Segmented
                size="small"
                value={modelMode}
                options={[...modelModeOptions]}
                onChange={(value) => setModelMode(value as 'classic' | 'v2')}
              />
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

    if (activeView === 'review') {
      return (
        <div className="psa-grid two-one">
          <Panel title="低置信复核队列" className="tall" eyebrow={`待复核 ${reviewItems.length}`}>
            <DataState loading={pageLoading} error={error} empty={reviewItems.length === 0} emptyTitle="暂无待复核样本">
              <Table<SentimentReviewItem>
                className="psa-table"
                size="small"
                rowKey="id"
                pagination={{ pageSize: 8, size: 'small' }}
                dataSource={reviewItems}
                columns={[
                  { title: '话题', dataIndex: 'topic_title', ellipsis: true, render: (value) => value || '未命名话题' },
                  { title: '平台', dataIndex: 'platform_name', render: (value) => value || '未知平台' },
                  {
                    title: '模型判断',
                    render: (_, record) => (
                      <SentimentBadge label={record.suggested_label} confidence={record.confidence_snapshot} />
                    ),
                  },
                  {
                    title: '人工标签',
                    render: (_, record) => (
                      <Select
                        size="small"
                        defaultValue={record.suggested_label}
                        style={{ width: 90 }}
                        options={reviewLabelOptions}
                        onChange={(value) => updateReview(record, 'reviewed', value)}
                        disabled={reviewingId === record.id}
                      />
                    ),
                  },
                  {
                    title: '操作',
                    render: (_, record) => (
                      <div className="psa-inline-tools">
                        <Button
                          size="small"
                          icon={<CheckCircleOutlined />}
                          loading={reviewingId === record.id}
                          onClick={() => updateReview(record, 'reviewed', record.suggested_label)}
                        >
                          通过
                        </Button>
                        <Button
                          size="small"
                          icon={<StopOutlined />}
                          loading={reviewingId === record.id}
                          onClick={() => updateReview(record, 'ignored')}
                        >
                          忽略
                        </Button>
                      </div>
                    ),
                  },
                ]}
              />
            </DataState>
          </Panel>
          <Panel title="复核说明">
            <div className="psa-detail-list">
              <div className="psa-detail-item">
                <span>入队条件</span>
                <strong>置信度低于 60%</strong>
              </div>
              <div className="psa-detail-item">
                <span>处理方式</span>
                <strong>人工确认或忽略</strong>
              </div>
              <div className="psa-detail-item">
                <span>状态</span>
                <StatusBadge status={reviewItems.length > 0 ? 'pending' : 'success'} />
              </div>
              <p className="psa-page-note">复核结果会写入审计日志，保留原始模型判断和人工校正标签。</p>
            </div>
          </Panel>
        </div>
      );
    }

    if (activeView === 'models') {
      const activeVersions = modelStatus?.active_versions || modelVersions.filter((item) => item.is_active);

      return (
        <div className="psa-grid two-one">
          <Panel title="模型版本" className="tall" eyebrow={`活跃 ${activeVersions.length}`}>
            <DataState loading={pageLoading} error={error} empty={modelVersions.length === 0} emptyTitle="暂无模型版本">
              <Table<ModelVersion>
                className="psa-table"
                size="small"
                rowKey="id"
                pagination={false}
                dataSource={modelVersions}
                columns={[
                  { title: '版本', dataIndex: 'version', ellipsis: true },
                  { title: '模型', dataIndex: 'model_name', ellipsis: true },
                  { title: 'Provider', dataIndex: 'provider', render: (value) => value || 'classic' },
                  {
                    title: '流量',
                    render: (_, record) => `${record.traffic_percent ?? 0}%`,
                  },
                  {
                    title: '状态',
                    render: (_, record) => <StatusBadge status={record.is_active} />,
                  },
                  {
                    title: '操作',
                    render: (_, record) => (
                      <div className="psa-inline-tools">
                        <Button
                          size="small"
                          type={record.is_active && (record.traffic_percent ?? 0) >= 100 ? 'primary' : 'default'}
                          icon={<SettingOutlined />}
                          loading={activatingVersionId === record.id}
                          disabled={record.is_active && (record.traffic_percent ?? 0) >= 100}
                          onClick={() => activateVersion(record, 100)}
                        >
                          主用
                        </Button>
                        {!record.is_active && (
                          <Button
                            size="small"
                            loading={activatingVersionId === record.id}
                            onClick={() => activateVersion(record, 20)}
                          >
                            20%
                          </Button>
                        )}
                      </div>
                    ),
                  },
                ]}
              />
            </DataState>
          </Panel>
          <Panel title="当前路由" eyebrow={modelStatus?.status || 'unknown'}>
            <div className="psa-detail-list">
              <div className="psa-detail-item">
                <span>当前版本</span>
                <strong>{modelStatus?.model?.version || '未加载'}</strong>
              </div>
              <div className="psa-detail-item">
                <span>Provider</span>
                <strong>{modelStatus?.model?.provider || 'classic'}</strong>
              </div>
              <div className="psa-detail-item">
                <span>流量比例</span>
                <strong>{modelStatus?.model?.traffic_percent ?? 0}%</strong>
              </div>
              <div className="psa-detail-item">
                <span>24h 分析</span>
                <strong>{modelStatus?.recent_analyzed ?? 0}</strong>
              </div>
              <div className="psa-detail-item">
                <span>平均置信</span>
                <strong>{((modelStatus?.avg_confidence || 0) * 100).toFixed(1)}%</strong>
              </div>
              <div className="psa-detail-item">
                <span>待复核</span>
                <strong>{modelStatus?.pending_review ?? reviewItems.length}</strong>
              </div>
              <div className="psa-detail-item">
                <span>运行状态</span>
                <StatusBadge status={modelStatus?.status || 'unknown'} />
              </div>
            </div>
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
            <Panel
              title="分析摘要"
              extra={<Button size="small" icon={<DownloadOutlined />} onClick={exportReport} loading={exporting}>导出报告</Button>}
            >
              <DataState loading={pageLoading} error={error} empty={!summary} emptyTitle="暂无分析摘要">
                <div className="psa-detail-list">
                  <div className="psa-detail-item">
                    <span>预测模型</span>
                    <strong>{forecast?.model || '未生成'}</strong>
                  </div>
                  <div className="psa-detail-item">
                    <span>当前热度</span>
                    <strong>{formatNumber(forecast?.current_heat)}</strong>
                  </div>
                  <div className="psa-detail-item">
                    <span>回测 MAE</span>
                    <strong>{forecast?.metrics?.mae != null ? formatNumber(forecast.metrics.mae) : '暂无'}</strong>
                  </div>
                  <div className="psa-detail-item">
                    <span>回测 MAPE</span>
                    <strong>{forecast?.metrics?.mape != null ? `${(forecast.metrics.mape * 100).toFixed(1)}%` : '暂无'}</strong>
                  </div>
                  <div className="psa-detail-item">
                    <span>今日分析</span>
                    <strong>{summary?.today_analyzed ?? 0}</strong>
                  </div>
                  <div className="psa-detail-item">
                    <span>入库结果</span>
                    <strong>{storedResults.length}</strong>
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
            <Panel title="预测信号">
              <DataState loading={pageLoading} error={error} empty={!forecast?.signals?.length} emptyTitle="暂无预测信号">
                <div className="psa-list">
                  {(forecast?.signals || []).map((item) => (
                    <div className="psa-row" key={item.name}>
                      <div>
                        <p className="psa-row-title">{forecastSignalLabels[item.name] || item.name}</p>
                        <div className="psa-row-meta">
                          <span>{item.description || '预测特征'}</span>
                          <span>变化 {item.change_rate != null ? `${(item.change_rate * 100).toFixed(1)}%` : '暂无'}</span>
                        </div>
                      </div>
                      <strong>{forecastDirectionLabels[item.direction] || item.direction}</strong>
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
            <Segmented
              size="small"
              value={modelMode}
              options={[...modelModeOptions]}
              onChange={(value) => setModelMode(value as 'classic' | 'v2')}
            />
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
