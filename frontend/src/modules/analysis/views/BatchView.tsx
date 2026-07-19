import React, { useCallback, useEffect, useState } from 'react';
import { Button, DatePicker, Input, InputNumber, message, Select, Slider, Table, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { Dayjs } from 'dayjs';
import {
  ClearOutlined,
  DatabaseOutlined,
  ExclamationCircleOutlined,
  FileSearchOutlined,
  SearchOutlined,
  SendOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import {
  analyzeBatch,
  getErrorMessage,
  getPlatforms,
  getSentimentResults,
  getSentimentSummary,
  Platform,
  SentimentAnalyzeResult,
  SentimentResult,
  SentimentSummary,
} from '@/services/api';
import {
  DataState,
  formatDateTime,
  formatNumber,
  MetricCard,
  Panel,
  SentimentBadge,
} from '@/components/DesignSystem';
import { AnalysisViewProps } from '../types';

const PAGE_SIZE = 10;
const MAX_BATCH = 50;

type TimeRange = [Dayjs | null, Dayjs | null] | null;

/** 「查询」按钮生效的筛选条件（输入控件本身不触发请求） */
interface AppliedFilters {
  label: string;
  platform: string;
  minConfidence: number;
  start?: string;
  end?: string;
}

const EMPTY_FILTERS: AppliedFilters = { label: '', platform: '', minConfidence: 0 };

const truncateText = (value: string, max: number) =>
  value.length > max ? `${value.slice(0, max)}…` : value;

const percent = (value?: number | null) =>
  typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '暂无';

const batchColumns: ColumnsType<SentimentAnalyzeResult> = [
  {
    title: '文本',
    dataIndex: 'text',
    ellipsis: true,
    render: (value: string) => (
      <Tooltip title={value} placement="topLeft">{truncateText(value, 40)}</Tooltip>
    ),
  },
  { title: '标签', width: 100, render: (_, record) => <SentimentBadge label={record.sentiment_label} /> },
  { title: '置信度', width: 90, align: 'right', render: (_, record) => percent(record.confidence) },
  { title: '正面', width: 80, align: 'right', render: (_, record) => percent(record.scores?.positive) },
  { title: '负面', width: 80, align: 'right', render: (_, record) => percent(record.scores?.negative) },
  { title: '中性', width: 80, align: 'right', render: (_, record) => percent(record.scores?.neutral) },
];

const historyColumns: ColumnsType<SentimentResult> = [
  { title: '话题 ID', dataIndex: 'topic_id', width: 90, render: (value: number) => `#${value}` },
  { title: '情感标签', dataIndex: 'sentiment_label', width: 100, render: (value: string) => <SentimentBadge label={value} /> },
  { title: '置信度', dataIndex: 'confidence', width: 90, align: 'right', render: (value: number) => percent(value) },
  { title: '正面', dataIndex: 'positive_score', width: 80, align: 'right', render: (value: number) => percent(value) },
  { title: '负面', dataIndex: 'negative_score', width: 80, align: 'right', render: (value: number) => percent(value) },
  { title: '中性', dataIndex: 'neutral_score', width: 80, align: 'right', render: (value: number) => percent(value) },
  { title: '模型版本', dataIndex: 'model_version', width: 140, ellipsis: true, render: (value?: string | null) => value || '未知' },
  { title: '分析时间', dataIndex: 'analyzed_at', width: 130, render: (value: string) => formatDateTime(value) },
];

/** 批量结果 —— 摘要指标卡 + 批量分析面板 + 可筛选历史结果表（对齐设计稿 Ishyi） */
const BatchView: React.FC<AnalysisViewProps> = ({ refreshKey, onSyncState }) => {
  const [summary, setSummary] = useState<SentimentSummary | null>(null);
  const [history, setHistory] = useState<SentimentResult[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [batchText, setBatchText] = useState('');
  const [batchResults, setBatchResults] = useState<SentimentAnalyzeResult[]>([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [labelFilter, setLabelFilter] = useState('');
  const [platformFilter, setPlatformFilter] = useState('');
  const [minConfidence, setMinConfidence] = useState(0);
  const [range, setRange] = useState<TimeRange>(null);
  const [applied, setApplied] = useState<AppliedFilters>(EMPTY_FILTERS);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      onSyncState({ refreshing: true });
      const [summaryRes, historyRes] = await Promise.all([
        getSentimentSummary(),
        getSentimentResults({
          label: applied.label || undefined,
          platform: applied.platform || undefined,
          min_confidence: applied.minConfidence > 0 ? applied.minConfidence : undefined,
          start_time: applied.start,
          end_time: applied.end,
          page,
          page_size: PAGE_SIZE,
        }),
      ]);
      setSummary(summaryRes.data);
      setHistory(historyRes.data?.items || []);
      setHistoryTotal(historyRes.data?.pagination?.total || 0);
      setError(null);
      onSyncState({ refreshing: false, lastUpdated: new Date().toISOString() });
    } catch (err) {
      setError(getErrorMessage(err));
      onSyncState({ refreshing: false });
    } finally {
      setLoading(false);
    }
  }, [applied, page, onSyncState]);

  useEffect(() => {
    fetchData();
  }, [fetchData, refreshKey]);

  useEffect(() => {
    getPlatforms()
      .then((res) => setPlatforms(res.data || []))
      .catch(() => setPlatforms([]));
  }, []);

  const batchLines = batchText.split('\n').map((item) => item.trim()).filter(Boolean);
  const overLimit = batchLines.length > MAX_BATCH;

  const runBatch = async () => {
    if (batchLines.length === 0 || overLimit) return;
    try {
      setAnalyzing(true);
      const res = await analyzeBatch(batchLines);
      const items = res.data || [];
      setBatchResults(items);
      message.success(`已完成 ${items.length} 条文本分析`);
      fetchData();
    } catch (err) {
      message.error(getErrorMessage(err));
    } finally {
      setAnalyzing(false);
    }
  };

  const applyFilters = () => {
    setApplied({
      label: labelFilter,
      platform: platformFilter,
      minConfidence,
      start: range?.[0]?.startOf('day').toISOString(),
      end: range?.[1]?.endOf('day').toISOString(),
    });
    setPage(1);
  };

  const resetFilters = () => {
    setLabelFilter('');
    setPlatformFilter('');
    setMinConfidence(0);
    setRange(null);
    setApplied(EMPTY_FILTERS);
    setPage(1);
  };

  return (
    <div className="an-stack">
      <DataState
        loading={loading && !summary}
        error={summary ? null : error}
        empty={!summary && !loading}
        emptyTitle="摘要数据不可用"
      >
        <div className="psa-grid metrics">
          <MetricCard
            label="今日分析"
            value={formatNumber(summary?.today_analyzed)}
            helper="今日完成分析的文本"
            icon={<FileSearchOutlined />}
          />
          <MetricCard
            label="累计分析"
            value={formatNumber(summary?.total_analyzed)}
            helper={summary ? `成功率 ${(summary.success_rate * 100).toFixed(1)}%` : '历史入库结果'}
            icon={<DatabaseOutlined />}
            tone="positive"
          />
          <MetricCard
            label="平均置信度"
            value={summary ? `${(summary.avg_confidence * 100).toFixed(1)}%` : '暂无'}
            helper={summary ? `平均耗时 ${Math.round(summary.avg_latency_ms)}ms` : '暂无统计'}
            icon={<ThunderboltOutlined />}
            tone="warning"
          />
          <MetricCard
            label="低置信样本"
            value={formatNumber(summary?.low_confidence)}
            helper="需人工复核关注"
            icon={<ExclamationCircleOutlined />}
            tone="negative"
          />
        </div>
      </DataState>

      <Panel title="批量分析" eyebrow={`每行一条文本，单次最多 ${MAX_BATCH} 条`}>
        <div className="an-batch-grid">
          <div className="psa-input-panel">
            <Input.TextArea
              className="psa-textarea"
              value={batchText}
              onChange={(event) => setBatchText(event.target.value)}
              placeholder={'每行输入一条待分析文本，例如：\n今天天气真好，心情舒畅\n这个产品质量太差了'}
              rows={9}
            />
            <div className="an-input-meta">
              <span className={overLimit ? 'an-over' : ''}>
                {batchLines.length} / {MAX_BATCH} 条{overLimit ? '（超出上限）' : ''}
              </span>
              <Button
                size="small"
                type="text"
                icon={<ClearOutlined />}
                onClick={() => setBatchText('')}
                disabled={!batchText}
              >
                清空
              </Button>
            </div>
            <div className="psa-actions">
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={runBatch}
                loading={analyzing}
                disabled={batchLines.length === 0 || overLimit}
              >
                开始批量分析
              </Button>
            </div>
          </div>
          <DataState
            empty={batchResults.length === 0}
            emptyTitle="暂无批量结果"
            emptyDescription="提交批量文本后在此展示逐条分析结果。"
            minHeight={200}
          >
            <Table<SentimentAnalyzeResult>
              className="psa-table"
              size="small"
              rowKey={(record) => `${record.analyzed_at}-${record.text.slice(0, 16)}`}
              dataSource={batchResults}
              columns={batchColumns}
              loading={analyzing}
              pagination={{ pageSize: PAGE_SIZE, size: 'small', hideOnSinglePage: true }}
            />
          </DataState>
        </div>
      </Panel>

      <Panel title="历史结果" eyebrow={`共 ${formatNumber(historyTotal)} 条`}>
        <div className="psa-filter-bar" style={{ marginBottom: 12 }}>
          <Select<string>
            value={labelFilter}
            onChange={setLabelFilter}
            style={{ width: 110 }}
            options={[
              { label: '全部标签', value: '' },
              { label: '正面', value: 'positive' },
              { label: '中性', value: 'neutral' },
              { label: '负面', value: 'negative' },
            ]}
          />
          <Select<string>
            value={platformFilter}
            onChange={setPlatformFilter}
            style={{ width: 140 }}
            options={[
              { label: '全部平台', value: '' },
              ...platforms.map((item) => ({ label: item.display_name || item.name, value: item.name })),
            ]}
          />
          <span className="an-filter-label">最低置信度</span>
          <Slider
            style={{ width: 140 }}
            min={0}
            max={1}
            step={0.05}
            value={minConfidence}
            onChange={(value: number) => setMinConfidence(value)}
            tooltip={{ formatter: (value) => `${Math.round((value || 0) * 100)}%` }}
          />
          <InputNumber
            min={0}
            max={1}
            step={0.05}
            value={minConfidence}
            onChange={(value) => setMinConfidence(typeof value === 'number' ? value : 0)}
            style={{ width: 82 }}
          />
          <DatePicker.RangePicker value={range} onChange={(value) => setRange(value)} />
          <Button type="primary" icon={<SearchOutlined />} onClick={applyFilters}>
            查询
          </Button>
          <Button icon={<ClearOutlined />} onClick={resetFilters}>
            重置
          </Button>
        </div>
        <DataState
          loading={loading}
          error={error}
          empty={history.length === 0}
          emptyTitle="暂无历史结果"
          emptyDescription="调整筛选条件后重试。"
        >
          <Table<SentimentResult>
            className="psa-table"
            size="small"
            rowKey="id"
            dataSource={history}
            columns={historyColumns}
            pagination={{
              current: page,
              pageSize: PAGE_SIZE,
              total: historyTotal,
              size: 'small',
              showSizeChanger: false,
              showTotal: (total) => `共 ${formatNumber(total)} 条`,
            }}
            onChange={(pagination) => setPage(pagination.current || 1)}
          />
        </DataState>
      </Panel>
    </div>
  );
};

export default BatchView;
