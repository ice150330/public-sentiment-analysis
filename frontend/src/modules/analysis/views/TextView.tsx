import React, { useCallback, useEffect, useState } from 'react';
import { Button, Input, message, Switch, Tag, Tooltip } from 'antd';
import { ClearOutlined, SendOutlined } from '@ant-design/icons';
import {
  analyzeText,
  analyzeTextV2,
  getErrorMessage,
  SentimentAnalyzeResult,
} from '@/services/api';
import {
  DataState,
  formatDateTime,
  Panel,
  SentimentBadge,
} from '@/components/DesignSystem';
import { AnalysisViewProps } from '../types';

/** 本次会话内保留的分析记录（最多 10 条） */
interface HistoryItem {
  id: number;
  text: string;
  compare: boolean;
  classic: SentimentAnalyzeResult;
  v2: SentimentAnalyzeResult | null;
  time: string;
}

const scoreLabels = [
  { key: 'positive', label: '正面', className: 'positive' },
  { key: 'negative', label: '负面', className: 'negative' },
  { key: 'neutral', label: '中性', className: 'neutral' },
] as const;

const truncateText = (value: string, max: number) =>
  value.length > max ? `${value.slice(0, max)}…` : value;

/** 单张模型结果卡：大标签 + 置信度大数字 + 三分数横条 + 模型元信息 */
const ResultCard: React.FC<{ title: string; result: SentimentAnalyzeResult; warn?: boolean }> = ({
  title,
  result,
  warn,
}) => (
  <article className={warn ? 'an-result-card warn' : 'an-result-card'}>
    <div className="an-result-head">
      <span className="an-model-name">{title}</span>
      <SentimentBadge label={result.sentiment_label} />
    </div>
    <div className="an-confidence">
      <strong>{(result.confidence * 100).toFixed(1)}%</strong>
      <span>置信度</span>
    </div>
    <div className="psa-score-bars">
      {scoreLabels.map((item) => (
        <div className="psa-score-line" key={item.key}>
          <span>{item.label}</span>
          <div className="psa-bar-track">
            <div
              className={`psa-bar-fill ${item.className}`}
              style={{ width: `${Math.round((result.scores[item.key] || 0) * 100)}%` }}
            />
          </div>
          <strong>{((result.scores[item.key] || 0) * 100).toFixed(1)}%</strong>
        </div>
      ))}
    </div>
    <div className="an-result-meta">
      <span>模型版本 {result.model_version || '未知'}</span>
      <span>分析时间 {formatDateTime(result.analyzed_at)}</span>
    </div>
  </article>
);

/** 文本分析 —— 左侧输入面板 + 会话历史，右侧单模型结果或双模型对比（对齐设计稿 LpTXH） */
const TextView: React.FC<AnalysisViewProps> = ({ refreshKey, onSyncState }) => {
  const [text, setText] = useState('');
  const [compare, setCompare] = useState(false);
  const [classic, setClassic] = useState<SentimentAnalyzeResult | null>(null);
  const [v2, setV2] = useState<SentimentAnalyzeResult | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>([]);

  const runAnalyze = useCallback(async () => {
    const value = text.trim();
    if (!value) {
      message.warning('请先输入待分析文本');
      return;
    }
    try {
      setAnalyzing(true);
      onSyncState({ refreshing: true });
      if (compare) {
        const [classicRes, v2Res] = await Promise.all([analyzeText(value), analyzeTextV2(value)]);
        setClassic(classicRes.data);
        setV2(v2Res.data);
        setHistory((prev) => [
          {
            id: Date.now(),
            text: value,
            compare: true,
            classic: classicRes.data,
            v2: v2Res.data,
            time: new Date().toISOString(),
          },
          ...prev,
        ].slice(0, 10));
      } else {
        const res = await analyzeText(value);
        setClassic(res.data);
        setV2(null);
        setHistory((prev) => [
          {
            id: Date.now(),
            text: value,
            compare: false,
            classic: res.data,
            v2: null,
            time: new Date().toISOString(),
          },
          ...prev,
        ].slice(0, 10));
      }
      message.success('分析完成');
      onSyncState({ refreshing: false, lastUpdated: new Date().toISOString() });
    } catch (err) {
      message.error(getErrorMessage(err));
      onSyncState({ refreshing: false });
    } finally {
      setAnalyzing(false);
    }
  }, [text, compare, onSyncState]);

  // 顶栏「刷新数据」：当前有文本时按所选模式重跑一次分析
  useEffect(() => {
    if (refreshKey > 0 && text.trim()) {
      void runAnalyze();
    }
    // 仅响应刷新信号；runAnalyze/text 取本次渲染的最新闭包
  }, [refreshKey]); // eslint-disable-line react-hooks/exhaustive-deps

  const mismatch = Boolean(compare && classic && v2 && classic.sentiment_label !== v2.sentiment_label);

  return (
    <div className="psa-grid one-two">
      <div className="an-stack">
        <Panel title="文本输入" eyebrow="情感倾向分析">
          <div className="psa-input-panel">
            <Input.TextArea
              className="psa-textarea"
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder="输入要分析的中文文本，支持新闻、评论等长文本"
              rows={9}
              maxLength={4096}
            />
            <div className="an-input-meta">
              <span>{text.length} / 4096 字</span>
              <label className="an-compare-toggle">
                <Switch size="small" checked={compare} onChange={setCompare} />
                对比分析（同时调用增强模型 v2）
              </label>
            </div>
            <div className="psa-actions">
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={runAnalyze}
                loading={analyzing}
                disabled={!text.trim()}
              >
                开始分析
              </Button>
              <Button icon={<ClearOutlined />} onClick={() => setText('')} disabled={analyzing || !text}>
                清空
              </Button>
            </div>
          </div>
        </Panel>

        <Panel title="分析历史" eyebrow={`本次会话 ${history.length} 条`}>
          <DataState
            empty={history.length === 0}
            emptyTitle="暂无分析记录"
            emptyDescription="本次会话完成的分析会保留最近 10 条，点击可回看。"
          >
            <div className="psa-list">
              {history.map((item) => (
                <button
                  type="button"
                  className="psa-row"
                  key={item.id}
                  onClick={() => {
                    setText(item.text);
                    setCompare(item.compare);
                    setClassic(item.classic);
                    setV2(item.v2);
                  }}
                >
                  <div>
                    <p className="psa-row-title">{truncateText(item.text, 30)}</p>
                    <div className="psa-row-meta">
                      <span>{formatDateTime(item.time)}</span>
                      <span>{item.compare ? '双模型对比' : '快速模型'}</span>
                    </div>
                  </div>
                  <SentimentBadge label={item.classic.sentiment_label} confidence={item.classic.confidence} />
                </button>
              ))}
            </div>
          </DataState>
        </Panel>
      </div>

      <Panel
        title="分析结果"
        eyebrow={compare ? '快速模型 vs 增强模型' : '快速模型 classic'}
        extra={mismatch ? <Tag className="psa-tag warning">两模型结论不一致</Tag> : undefined}
      >
        <DataState
          loading={analyzing}
          empty={!classic}
          emptyTitle="暂无分析结果"
          emptyDescription="在左侧输入文本并点击「开始分析」，此处展示情感标签与概率分布。"
        >
          {classic && (
            <div className="an-stack">
              {compare && v2 ? (
                <div className="an-compare-grid">
                  <ResultCard title="快速模型 classic" result={classic} warn={mismatch} />
                  <ResultCard title="增强模型 v2" result={v2} warn={mismatch} />
                </div>
              ) : (
                <ResultCard title="快速模型 classic" result={classic} />
              )}
              <Tooltip title={classic.text} placement="topLeft">
                <p className="an-source-text">{truncateText(classic.text, 120)}</p>
              </Tooltip>
            </div>
          )}
        </DataState>
      </Panel>
    </div>
  );
};

export default TextView;
