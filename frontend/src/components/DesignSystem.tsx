import React from 'react';
import { Empty, Result, Skeleton, Tag } from 'antd';
import {
  AppstoreOutlined,
  DatabaseOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { platformTone, sentimentText } from '../utils/format';

// 壳层与格式化工具已拆出，这里保留统一出口以兼容既有引用。
export { ModuleFrame, FloatingDock } from '../layouts/AppShell';
export type { SubView } from '../layouts/AppShell';
export { formatDateTime, formatNumber, sentimentText, platformTone } from '../utils/format';

interface PanelProps {
  title?: string;
  eyebrow?: string;
  extra?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
}

export const Panel: React.FC<PanelProps> = ({ title, eyebrow, extra, className, children }) => (
  <section className={['psa-panel', 'psa-motion-card', className].filter(Boolean).join(' ')}>
    {(title || eyebrow || extra) && (
      <div className="psa-panel-head">
        <div>
          {eyebrow && <div className="psa-eyebrow">{eyebrow}</div>}
          {title && <h2>{title}</h2>}
        </div>
        {extra}
      </div>
    )}
    {children}
  </section>
);

interface MetricCardProps {
  label: string;
  value?: number | string | null;
  helper?: string;
  tone?: 'primary' | 'positive' | 'negative' | 'warning' | 'neutral';
  icon?: React.ReactNode;
}

export const MetricCard: React.FC<MetricCardProps> = ({ label, value, helper, tone = 'primary', icon }) => (
  <article className={`psa-metric-card psa-motion-card ${tone}`}>
    <div className="psa-metric-icon">{icon || <DatabaseOutlined />}</div>
    <div>
      <div className="psa-metric-label">{label}</div>
      <div className="psa-metric-value">{value ?? '暂无'}</div>
      {helper && <div className="psa-metric-helper">{helper}</div>}
    </div>
  </article>
);

interface DataStateProps {
  loading?: boolean;
  error?: string | null;
  empty?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  minHeight?: number;
  children: React.ReactNode;
}

export const DataState: React.FC<DataStateProps> = ({
  loading,
  error,
  empty,
  emptyTitle = '暂无数据',
  emptyDescription = '后端暂未返回可展示的数据。',
  minHeight,
  children,
}) => {
  if (loading) {
    return (
      <div className="psa-state psa-motion-state loading" style={{ minHeight }}>
        <Skeleton active paragraph={{ rows: 4 }} />
      </div>
    );
  }

  if (error) {
    return (
      <Result
        className="psa-result psa-motion-state"
        status="warning"
        icon={<ExclamationCircleOutlined />}
        title="数据加载失败"
        subTitle={error}
      />
    );
  }

  if (empty) {
    return (
      <div className="psa-state psa-motion-state empty" style={{ minHeight }}>
        <Empty description={<span>{emptyTitle}</span>} />
        <p className="psa-empty-copy">{emptyDescription}</p>
      </div>
    );
  }

  return <>{children}</>;
};

export const StatusBadge: React.FC<{ status?: string | boolean | null }> = ({ status }) => {
  if (typeof status === 'boolean') {
    return <Tag className={status ? 'psa-tag success' : 'psa-tag muted'}>{status ? '启用' : '停用'}</Tag>;
  }

  const value = status || 'unknown';
  const lower = value.toLowerCase();
  const type = lower.includes('success') || lower.includes('running') ? 'success'
    : lower.includes('fail') || lower.includes('error') ? 'danger'
      : lower.includes('partial') ? 'warning'
        : 'muted';

  return <Tag className={`psa-tag ${type}`}>{value}</Tag>;
};

export const PlatformBadge: React.FC<{ name?: string | null }> = ({ name }) => (
  <Tag className={`psa-platform ${platformTone(name)}`}>{name || '未知平台'}</Tag>
);

export const SentimentBadge: React.FC<{ label?: string; confidence?: number }> = ({ label, confidence }) => {
  const tone = label === 'positive' ? 'success' : label === 'negative' ? 'danger' : 'muted';
  return (
    <Tag className={`psa-tag ${tone}`}>
      {sentimentText(label)}
      {confidence !== undefined ? ` ${(confidence * 100).toFixed(1)}%` : ''}
    </Tag>
  );
};

export const SectionNotice: React.FC<{ title: string; description: string }> = ({ title, description }) => (
  <div className="psa-section-notice psa-motion-card">
    <AppstoreOutlined />
    <div>
      <strong>{title}</strong>
      <p>{description}</p>
    </div>
  </div>
);
