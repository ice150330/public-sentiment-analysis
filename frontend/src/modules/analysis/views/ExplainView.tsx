import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Input, InputNumber, message, Pagination, Select, Tag, Tooltip } from 'antd';
import { ScanOutlined } from '@ant-design/icons';
import {
  generateModelExplanation,
  getErrorMessage,
  getModelExplanations,
  ModelExplanationResult,
} from '@/services/api';
import {
  DataState,
  formatDateTime,
  formatNumber,
  Panel,
  SentimentBadge,
} from '@/components/DesignSystem';
import { AnalysisViewProps } from '../types';

const PAGE_SIZE = 10;

const POSITIVE_RGB = '22, 163, 74';
const NEGATIVE_RGB = '225, 29, 72';

/** 后端解释历史为 Record<string, unknown>，读取时做防御性解析 */
const asString = (value: unknown) => (value === null || value === undefined ? '' : String(value));

/** 模型解释 —— 输入区 + 摘要 + token 贡献度可视化 + 解释历史（对齐设计稿 Cn9iT） */
const ExplainView: React.FC<AnalysisViewProps> = ({ refreshKey, onSyncState }) => {
  const [text, setText] = useState('');
  const [resultId, setResultId] = useState<number | null>(null);
  const [nSamples, setNSamples] = useState(256);
  const [explanation, setExplanation] = useState<ModelExplanationResult | null>(null);
  const [generating, setGenerating] = useState(false);
  const [history, setHistory] = useState<Record<string, unknown>[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyPage, setHistoryPage] = useState(1);
  const [historyLoading, setHistoryLoading] = useState(true);

  const fetchHistory = useCallback(async () => {
    try {
      setHistoryLoading(true);
      const res = await getModelExplanations({ page: historyPage, page_size: PAGE_SIZE });
      setHistory(res.data?.items || []);
      setHistoryTotal(res.data?.pagination?.total || 0);
    } catch {
      setHistory([]);
      setHistoryTotal(0);
    } finally {
      setHistoryLoading(false);
    }
  }, [historyPage]);

  useEffect(() => {
    void fetchHistory();
  }, [fetchHistory, refreshKey]);

  const runGenerate = async () => {
    const value = text.trim();
    if (!resultId && !value) {
      message.warning('请输入待解释文本或情感结果 ID');
      return;
    }
    try {
      setGenerating(true);
      onSyncState({ refreshing: true });
      const res = await generateModelExplanation(
        resultId
          ? { sentiment_result_id: resultId, n_samples: nSamples }
          : { text: value, n_samples: nSamples },
      );
      setExplanation(res.data);
      message.success('解释已生成');
      onSyncState({ refreshing: false, lastUpdated: new Date().toISOString() });
      if (historyPage === 1) {
        void fetchHistory();
      } else {
        setHistoryPage(1);
      }
    } catch (err) {
      message.error(getErrorMessage(err));
      onSyncState({ refreshing: false });
    } finally {
      setGenerating(false);
    }
  };

  const tokens = useMemo(() => explanation?.tokens || [], [explanation]);

  const maxAbs = useMemo(
    () => Math.max(1e-6, ...tokens.map((item) => Math.abs(item.contribution))),
    [tokens],
  );

  const topTokens = useMemo(
    () => [...tokens]
      .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
      .slice(0, 15),
    [tokens],
  );

  return (
    <div className="an-stack">
      <div className="psa-grid one-two">
        <div className="an-stack">
          <Panel title="解释输入" eyebrow="LIME 局部解释">
            <div className="psa-input-panel">
              <Input.TextArea
                className="psa-textarea"
                value={text}
                onChange={(event) => setText(event.target.value)}
                placeholder="输入要解释的文本（或在下方填写情感结果 ID）"
                rows={6}
                maxLength={4096}
              />
              <div className="an-input-meta">
                <span>{text.length} / 4096 字</span>
              </div>
              <div className="an-field-row">
                <span className="an-field-label">情感结果 ID</span>
                <InputNumber
                  min={1}
                  value={resultId}
                  onChange={(value) => setResultId(typeof value === 'number' ? value : null)}
                  placeholder="可选"
                  style={{ width: 160 }}
                />
              </div>
              <div className="an-field-row">
                <span className="an-field-label">采样次数</span>
                <Select<number>
                  value={nSamples}
                  onChange={setNSamples}
                  style={{ width: 160 }}
                  options={[128, 256, 512, 1024].map((value) => ({ label: `${value} 次`, value }))}
                />
              </div>
              <div className="psa-actions">
                <Button type="primary" icon={<ScanOutlined />} onClick={runGenerate} loading={generating}>
                  生成解释
                </Button>
              </div>
              <p className="psa-page-note">填写情感结果 ID 时优先解释已入库结果，否则按输入文本实时解释。</p>
            </div>
          </Panel>

          <Panel title="解释摘要">
            <DataState
              empty={!explanation}
              emptyTitle="暂无解释结果"
              emptyDescription="生成解释后在此展示摘要信息。"
            >
              {explanation && (
                <div className="psa-detail-list">
                  <SentimentBadge
                    label={explanation.sentiment_label || undefined}
                    confidence={explanation.confidence ?? undefined}
                  />
                  <div className="psa-detail-item">
                    <span>解释方法</span>
                    <strong>{explanation.method || '未知'}</strong>
                  </div>
                  <div className="psa-detail-item">
                    <span>模型版本</span>
                    <strong>{explanation.model_version || '未知'}</strong>
                  </div>
                  <div className="psa-detail-item">
                    <span>采样次数</span>
                    <strong>{explanation.n_samples ?? nSamples}</strong>
                  </div>
                  {explanation.summary && <p className="psa-page-note">{explanation.summary}</p>}
                </div>
              )}
            </DataState>
          </Panel>
        </div>

        <Panel title="Token 贡献度" eyebrow={tokens.length > 0 ? `${tokens.length} 个 token` : undefined}>
          <DataState
            loading={generating}
            empty={tokens.length === 0}
            emptyTitle="暂无 token 数据"
            emptyDescription="生成解释后，按 token 展示对结论的正负贡献。"
          >
            <div className="an-stack">
              {explanation?.text && <p className="an-source-text">{explanation.text}</p>}
              <div className="an-token-legend">
                <span><i className="pos" />正向贡献</span>
                <span><i className="neg" />负向贡献</span>
                <span>颜色深浅表示贡献强度</span>
              </div>
              <div className="an-token-flow">
                {tokens.map((token) => {
                  const negative = token.direction === 'negative' || token.contribution < 0;
                  const alpha = 0.1 + 0.55 * (Math.abs(token.contribution) / maxAbs);
                  return (
                    <Tooltip title={`贡献 ${token.contribution.toFixed(3)}`} key={`${token.token}-${token.rank}`}>
                      <span
                        className="an-token"
                        style={{ background: `rgba(${negative ? NEGATIVE_RGB : POSITIVE_RGB}, ${alpha.toFixed(3)})` }}
                      >
                        {token.token}
                      </span>
                    </Tooltip>
                  );
                })}
              </div>
              <div className="an-token-bars">
                {topTokens.map((token) => {
                  const negative = token.contribution < 0;
                  const width = Math.max(3, (Math.abs(token.contribution) / maxAbs) * 50);
                  return (
                    <div className="an-token-bar-row" key={`${token.token}-${token.rank}`}>
                      <span className="an-token-bar-label">{token.token}</span>
                      <div className="an-token-bar-track">
                        <div
                          className={`an-token-bar-fill ${negative ? 'neg' : 'pos'}`}
                          style={{ width: `${width}%` }}
                        />
                      </div>
                      <strong className={negative ? 'neg' : 'pos'}>{token.contribution.toFixed(3)}</strong>
                    </div>
                  );
                })}
              </div>
            </div>
          </DataState>
        </Panel>
      </div>

      <Panel title="解释历史" eyebrow={`共 ${formatNumber(historyTotal)} 条`}>
        <DataState loading={historyLoading} empty={history.length === 0} emptyTitle="暂无解释历史">
          <div className="psa-list">
            {history.map((item, index) => {
              const id = asString(item.id) || String(index + 1);
              const method = asString(item.method) || 'lime';
              const version = asString(item.model_version);
              const srId = asString(item.sentiment_result_id);
              return (
                <div className="psa-row" key={id}>
                  <div>
                    <p className="psa-row-title">解释 #{id}</p>
                    <div className="psa-row-meta">
                      <span>{version ? `模型版本 ${version}` : '模型版本未知'}</span>
                      {srId && <span>关联结果 #{srId}</span>}
                      <span>{formatDateTime(asString(item.created_at) || null)}</span>
                    </div>
                  </div>
                  <Tag className="psa-tag muted">{method}</Tag>
                </div>
              );
            })}
          </div>
          {historyTotal > PAGE_SIZE && (
            <div className="an-pagination">
              <Pagination
                size="small"
                current={historyPage}
                pageSize={PAGE_SIZE}
                total={historyTotal}
                onChange={setHistoryPage}
                showSizeChanger={false}
              />
            </div>
          )}
        </DataState>
      </Panel>
    </div>
  );
};

export default ExplainView;
