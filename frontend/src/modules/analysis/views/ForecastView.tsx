import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, InputNumber, message, Select, Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  AreaChartOutlined,
  FallOutlined,
  PlusOutlined,
  RiseOutlined,
  SwapRightOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import {
  createPrediction,
  forecastHeat,
  ForecastHeat,
  getErrorMessage,
  getTopics,
  getTrendPredictions,
  HotTopic,
} from '@/services/api';
import { DataState, formatDateTime, formatNumber, Panel } from '@/components/DesignSystem';
import { AnalysisViewProps } from '../types';

const PAGE_SIZE = 10;

const signalLabels: Record<string, string> = {
  heat_momentum: '热度动量',
  negative_momentum: '负面压力',
  cross_platform_spread: '跨平台扩散',
};

const directionMeta: Record<string, { icon: React.ReactNode; cls: string; text: string }> = {
  up: { icon: <RiseOutlined />, cls: 'up', text: '上升' },
  down: { icon: <FallOutlined />, cls: 'down', text: '下降' },
  stable: { icon: <SwapRightOutlined />, cls: 'stable', text: '平稳' },
};

/** 后端历史预测记录为 Record<string, unknown>，读取时做防御性解析 */
const asString = (value: unknown) => (value === null || value === undefined ? '' : String(value));

const asNumber = (value: unknown) => {
  const num = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(num) ? num : 0;
};

const predictionColumns: ColumnsType<Record<string, unknown>> = [
  { title: 'ID', width: 80, render: (_, record) => `#${asString(record.id) || '未知'}` },
  { title: '对象类型', width: 110, render: (_, record) => asString(record.target_type) || '未知' },
  { title: '对象 ID', width: 100, render: (_, record) => asString(record.target_id) || '未知' },
  { title: '模型类型', width: 120, render: (_, record) => asString(record.model_type) || '未知' },
  {
    title: '预测时长',
    width: 100,
    render: (_, record) => {
      const hours = asNumber(record.horizon_hours);
      return hours > 0 ? `${hours} 小时` : '暂无';
    },
  },
  { title: '创建时间', width: 140, render: (_, record) => formatDateTime(asString(record.created_at) || null) },
];

/** 趋势预测 —— 操作条 + 预测折线（含置信区间带）+ 信号卡 + 历史预测记录（对齐设计稿 VVXTe） */
const ForecastView: React.FC<AnalysisViewProps> = ({ refreshKey, onSyncState }) => {
  const [topics, setTopics] = useState<HotTopic[]>([]);
  const [topicId, setTopicId] = useState<number | undefined>(undefined);
  const [horizon, setHorizon] = useState(7);
  const [forecast, setForecast] = useState<ForecastHeat | null>(null);
  const [forecastLoading, setForecastLoading] = useState(true);
  const [forecastError, setForecastError] = useState<string | null>(null);
  const [predictions, setPredictions] = useState<Record<string, unknown>[]>([]);
  const [predTotal, setPredTotal] = useState(0);
  const [predPage, setPredPage] = useState(1);
  const [predLoading, setPredLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  const runForecast = useCallback(async () => {
    try {
      setForecastLoading(true);
      onSyncState({ refreshing: true });
      const res = await forecastHeat({ topic_id: topicId, horizon_days: horizon });
      setForecast(res.data);
      setForecastError(null);
      onSyncState({ refreshing: false, lastUpdated: new Date().toISOString() });
    } catch (err) {
      setForecastError(getErrorMessage(err));
      onSyncState({ refreshing: false });
    } finally {
      setForecastLoading(false);
    }
  }, [topicId, horizon, onSyncState]);

  const fetchPredictions = useCallback(async () => {
    try {
      setPredLoading(true);
      const res = await getTrendPredictions({ page: predPage, page_size: PAGE_SIZE });
      setPredictions(res.data?.items || []);
      setPredTotal(res.data?.pagination?.total || 0);
    } catch {
      setPredictions([]);
      setPredTotal(0);
    } finally {
      setPredLoading(false);
    }
  }, [predPage]);

  // 首次进入与顶栏刷新：按当前话题/周期生成预测
  useEffect(() => {
    void runForecast();
    // 仅响应刷新信号；runForecast 取本次渲染的最新闭包
  }, [refreshKey]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    void fetchPredictions();
  }, [fetchPredictions, refreshKey]);

  useEffect(() => {
    getTopics({ page: 1, page_size: 50, sort_by: 'heat_score', sort_order: 'desc' })
      .then((res) => setTopics(res.data?.items || []))
      .catch(() => setTopics([]));
  }, []);

  const handleCreate = async () => {
    if (!topicId) {
      message.warning('请先选择话题或输入话题 ID');
      return;
    }
    try {
      setCreating(true);
      await createPrediction({
        target_type: 'topic',
        target_id: topicId,
        model_type: 'heat',
        horizon_hours: horizon * 24,
      });
      message.success('预测任务已创建');
      await fetchPredictions();
    } catch (err) {
      message.error(getErrorMessage(err));
    } finally {
      setCreating(false);
    }
  };

  const chartOption = useMemo<EChartsOption | null>(() => {
    if (!forecast || !forecast.forecast?.length) return null;
    const points = forecast.forecast;
    const categories = ['当前', ...points.map((point) => point.date)];
    return {
      tooltip: { trigger: 'axis' },
      legend: { top: 0, textStyle: { color: '#64748B', fontWeight: 700 } },
      grid: { left: 48, right: 18, top: 34, bottom: 28 },
      xAxis: {
        type: 'category',
        data: categories,
        axisLabel: { color: '#64748B' },
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: '#E7EEF7' } },
      },
      series: [
        {
          name: '置信区间',
          type: 'line',
          data: [null, ...points.map((point) => point.confidence_lower)],
          stack: 'band',
          symbol: 'none',
          lineStyle: { opacity: 0 },
        },
        {
          name: '置信区间',
          type: 'line',
          data: [null, ...points.map((point) => Math.max(0, point.confidence_upper - point.confidence_lower))],
          stack: 'band',
          symbol: 'none',
          lineStyle: { opacity: 0 },
          areaStyle: { color: 'rgba(37, 99, 235, 0.12)' },
        },
        {
          name: '预测热度',
          type: 'line',
          smooth: true,
          data: [forecast.current_heat, ...points.map((point) => point.predicted_heat)],
          lineStyle: { color: '#2563EB', width: 3 },
          itemStyle: { color: '#2563EB' },
          areaStyle: { color: 'rgba(37, 99, 235, 0.08)' },
          z: 3,
        },
      ],
    };
  }, [forecast]);

  const signals = forecast?.signals || [];

  return (
    <div className="an-stack">
      <div className="psa-filter-bar">
        <Select<number>
          showSearch
          allowClear
          placeholder="选择热点话题（默认全部）"
          optionFilterProp="label"
          style={{ minWidth: 280 }}
          value={topicId}
          onChange={(value) => setTopicId(value)}
          options={topics.map((topic) => ({
            label: topic.title,
            value: topic.id,
          }))}
        />
        <InputNumber
          min={1}
          placeholder="或输入话题 ID"
          value={topicId ?? null}
          onChange={(value) => setTopicId(typeof value === 'number' ? value : undefined)}
          style={{ width: 140 }}
        />
        <Select<number>
          value={horizon}
          onChange={setHorizon}
          style={{ width: 120 }}
          options={[
            { label: '未来 3 天', value: 3 },
            { label: '未来 7 天', value: 7 },
            { label: '未来 14 天', value: 14 },
          ]}
        />
        <Button type="primary" icon={<AreaChartOutlined />} loading={forecastLoading} onClick={runForecast}>
          生成预测
        </Button>
        <Button icon={<PlusOutlined />} loading={creating} onClick={handleCreate}>
          创建预测记录
        </Button>
      </div>

      <div className="psa-grid two-one">
        <Panel title="热度预测" eyebrow={forecast ? `${forecast.model} · 未来 ${horizon} 天` : undefined}>
          <DataState
            loading={forecastLoading}
            error={forecastError}
            empty={!chartOption}
            emptyTitle="暂无预测数据"
            emptyDescription="选择话题后点击「生成预测」。"
          >
            <ReactECharts option={chartOption || {}} className="psa-chart large" />
            {forecast && (
              <div className="an-metrics-line">
                <span>预测模型<strong>{forecast.model || '未知'}</strong></span>
                <span>当前热度<strong>{formatNumber(forecast.current_heat)}</strong></span>
                <span>
                  MAE
                  <strong>{forecast.metrics?.mae != null ? formatNumber(Number(forecast.metrics.mae.toFixed(2))) : '暂无'}</strong>
                </span>
                <span>
                  MAPE
                  <strong>{forecast.metrics?.mape != null ? `${(forecast.metrics.mape * 100).toFixed(1)}%` : '暂无'}</strong>
                </span>
                <span>
                  R²<strong>{forecast.metrics?.r2_score != null ? forecast.metrics.r2_score.toFixed(3) : '暂无'}</strong>
                </span>
              </div>
            )}
          </DataState>
        </Panel>

        <Panel title="预测信号" eyebrow={signals.length > 0 ? `${signals.length} 项` : undefined}>
          <DataState
            loading={forecastLoading}
            empty={signals.length === 0}
            emptyTitle="暂无预测信号"
            emptyDescription="生成预测后展示模型使用的关键信号。"
          >
            <div className="an-signal-grid">
              {signals.map((item) => {
                const meta = directionMeta[item.direction] || directionMeta.stable;
                return (
                  <article className={`an-signal-card ${meta.cls}`} key={item.name}>
                    <div className="an-signal-head">
                      <span>{signalLabels[item.name] || item.name}</span>
                      {meta.icon}
                    </div>
                    <strong>{formatNumber(item.value)}</strong>
                    <div className="an-signal-meta">
                      <span>{meta.text}</span>
                      <span>
                        {item.change_rate != null
                          ? `${item.change_rate >= 0 ? '+' : ''}${(item.change_rate * 100).toFixed(1)}%`
                          : '暂无'}
                      </span>
                    </div>
                  </article>
                );
              })}
            </div>
          </DataState>
        </Panel>
      </div>

      <Panel title="历史预测记录" eyebrow={`共 ${formatNumber(predTotal)} 条`}>
        <DataState loading={predLoading} empty={predictions.length === 0} emptyTitle="暂无预测记录">
          <Table<Record<string, unknown>>
            className="psa-table"
            size="small"
            rowKey={(record, index) => asString(record.id) || String(index)}
            dataSource={predictions}
            columns={predictionColumns}
            pagination={{
              current: predPage,
              pageSize: PAGE_SIZE,
              total: predTotal,
              size: 'small',
              showSizeChanger: false,
            }}
            onChange={(pagination) => setPredPage(pagination.current || 1)}
          />
        </DataState>
      </Panel>
    </div>
  );
};

export default ForecastView;
