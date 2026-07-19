import React, { useCallback, useEffect, useState } from 'react';
import { Table, Tag } from 'antd';
import {
  CrawlLog,
  CrawlSuccessRate,
  DataQualityCheck,
  DataQualityFunnel,
  DataQualityIssue,
  getCrawlLogs,
  getCrawlSuccessRate,
  getDataQualityChecks,
  getDataQualityFunnel,
  getErrorMessage,
  getTypedDataQualityIssues,
} from '@/services/api';
import {
  DataState,
  formatDateTime,
  formatNumber,
  Panel,
  StatusBadge,
} from '@/components/DesignSystem';
import { OverviewViewProps } from '../types';

/** 漏斗各阶段配色，按序循环 */
const FUNNEL_COLORS = [
  'var(--primary)',
  'var(--positive)',
  '#0ea5e9',
  'var(--warning)',
  'var(--negative)',
];

const CHECK_TAG: Record<string, { cls: string; text: string }> = {
  pass: { cls: 'success', text: '通过' },
  warning: { cls: 'warning', text: '警告' },
  fail: { cls: 'danger', text: '失败' },
};

const rateColor = (status: string) => {
  const lower = status.toLowerCase();
  if (lower.includes('success')) return 'var(--positive)';
  if (lower.includes('fail') || lower.includes('error')) return 'var(--negative)';
  return 'var(--primary)';
};

/** 数据质量 —— 处理漏斗 + 质量检查 + 问题表 + 采集成功率 + 采集日志 */
const QualityView: React.FC<OverviewViewProps> = ({ refreshKey, onSyncState }) => {
  const [funnel, setFunnel] = useState<DataQualityFunnel | null>(null);
  const [checks, setChecks] = useState<DataQualityCheck[]>([]);
  const [issues, setIssues] = useState<DataQualityIssue[]>([]);
  const [crawlRate, setCrawlRate] = useState<CrawlSuccessRate | null>(null);
  const [logs, setLogs] = useState<CrawlLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      onSyncState({ refreshing: true });
      const [funnelRes, checksRes, issuesRes, crawlRateRes, logsRes] = await Promise.all([
        getDataQualityFunnel(),
        getDataQualityChecks(),
        getTypedDataQualityIssues({ page: 1, page_size: 8 }),
        getCrawlSuccessRate({ days: 7 }),
        getCrawlLogs({ page: 1, page_size: 6 }),
      ]);
      setFunnel(funnelRes.data);
      setChecks(checksRes.data?.checks || []);
      setIssues(issuesRes.data?.items || []);
      setCrawlRate(crawlRateRes.data);
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

  const funnelBase = Math.max(1, funnel?.funnel[0]?.count || 0);

  return (
    <DataState loading={loading} error={error} empty={!funnel && !crawlRate} emptyTitle="数据质量不可用">
      <div className="ov-stack">
        <div className="psa-grid two-one">
          <div className="ov-stack">
            <Panel
              title="处理漏斗"
              eyebrow={funnel ? `${funnel.date} 留存 ${funnel.retention_rate}%` : undefined}
            >
              <DataState empty={!funnel || funnel.funnel.length === 0} emptyTitle="暂无处理漏斗">
                <div className="psa-score-bars">
                  {funnel?.funnel.map((stage, index) => (
                    <div className="psa-score-line ov-wide" key={stage.stage}>
                      <span>{stage.stage}</span>
                      <div className="psa-bar-track">
                        <div
                          className="psa-bar-fill"
                          style={{
                            width: `${Math.min(100, Math.round((stage.count / funnelBase) * 100))}%`,
                            background: FUNNEL_COLORS[index % FUNNEL_COLORS.length],
                          }}
                        />
                      </div>
                      <strong>{formatNumber(stage.count)}</strong>
                    </div>
                  ))}
                </div>
              </DataState>
            </Panel>
            <Panel title="质量检查">
              <DataState empty={checks.length === 0} emptyTitle="暂无质量检查项">
                <div className="psa-list">
                  {checks.map((check) => {
                    const meta = CHECK_TAG[check.status] || { cls: 'muted', text: check.status };
                    return (
                      <div className="psa-row" key={check.name}>
                        <div>
                          <p className="psa-row-title">{check.name}</p>
                          <div className="psa-row-meta">
                            <span>阈值 {formatNumber(check.threshold)}</span>
                            <span>
                              {check.pass_rate !== undefined
                                ? `通过率 ${check.pass_rate}%`
                                : `${formatNumber(check.count)} 项`}
                            </span>
                          </div>
                        </div>
                        <Tag className={`psa-tag ${meta.cls}`}>{meta.text}</Tag>
                      </div>
                    );
                  })}
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

        <div className="psa-grid two">
          <Panel title="采集成功率" eyebrow={crawlRate?.period}>
            <DataState empty={!crawlRate || crawlRate.total === 0} emptyTitle="暂无采集质量统计">
              <div className="psa-score-bars">
                {crawlRate?.rates.map((rate) => (
                  <div className="psa-score-line" key={rate.status}>
                    <span>{rate.status}</span>
                    <div className="psa-bar-track">
                      <div
                        className="psa-bar-fill"
                        style={{ width: `${Math.min(100, rate.percentage)}%`, background: rateColor(rate.status) }}
                      />
                    </div>
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
                { title: '记录数', dataIndex: 'records_count', align: 'right', render: (value) => formatNumber(value) },
                { title: '开始时间', dataIndex: 'started_at', render: (value) => formatDateTime(value) },
              ]}
            />
          </Panel>
        </div>
      </div>
    </DataState>
  );
};

export default QualityView;
