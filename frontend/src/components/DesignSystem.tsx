import React from 'react';
import { Button, Empty, Result, Skeleton, Tag } from 'antd';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  AppstoreOutlined,
  BarChartOutlined,
  CheckCircleFilled,
  DashboardOutlined,
  DatabaseOutlined,
  ExclamationCircleOutlined,
  FireOutlined,
  ReloadOutlined,
  SearchOutlined,
  SettingOutlined,
  SmileOutlined,
} from '@ant-design/icons';

export interface SubView {
  key: string;
  label: string;
  icon?: React.ReactNode;
}

interface ModuleFrameProps {
  moduleLabel: string;
  activeView: string;
  views: SubView[];
  onViewChange: (key: string) => void;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  onRefresh?: () => void;
  refreshing?: boolean;
  lastUpdated?: string | null;
  children: React.ReactNode;
}

const moduleRoutes = [
  { path: '/', label: '总览', icon: <DashboardOutlined /> },
  { path: '/topics', label: '热点', icon: <FireOutlined /> },
  { path: '/analysis', label: '分析', icon: <SmileOutlined /> },
  { path: '/management', label: '管理', icon: <SettingOutlined /> },
];

export const formatDateTime = (value?: string | null) => {
  if (!value) return '暂无';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
};

export const formatNumber = (value?: number | null) => {
  if (value === null || value === undefined) return '暂无';
  return new Intl.NumberFormat('zh-CN').format(value);
};

export const sentimentText = (label?: string) => {
  if (label === 'positive') return '正面';
  if (label === 'negative') return '负面';
  if (label === 'neutral') return '中性';
  return label || '未知';
};

export const platformTone = (name?: string | null) => {
  const normalized = (name || '').toLowerCase();
  if (normalized.includes('微博') || normalized.includes('weibo')) return 'weibo';
  if (normalized.includes('抖音') || normalized.includes('douyin')) return 'douyin';
  if (normalized.includes('头条') || normalized.includes('toutiao')) return 'toutiao';
  if (normalized.includes('百度') || normalized.includes('baidu')) return 'baidu';
  if (normalized.includes('b站') || normalized.includes('bilibili')) return 'bilibili';
  if (normalized.includes('知乎') || normalized.includes('zhihu')) return 'zhihu';
  return 'neutral';
};

export const ModuleFrame: React.FC<ModuleFrameProps> = ({
  moduleLabel,
  activeView,
  views,
  onViewChange,
  searchValue,
  onSearchChange,
  onRefresh,
  refreshing,
  lastUpdated,
  children,
}) => {
  return (
    <main className="psa-screen">
      <section className="psa-screen-inner">
        <TopFunctionBar
          moduleLabel={moduleLabel}
          activeView={activeView}
          views={views}
          onViewChange={onViewChange}
          searchValue={searchValue}
          onSearchChange={onSearchChange}
          onRefresh={onRefresh}
          refreshing={refreshing}
          lastUpdated={lastUpdated}
        />
        <div className="psa-content">{children}</div>
      </section>
      <FloatingDock />
    </main>
  );
};

const TopFunctionBar: React.FC<Omit<ModuleFrameProps, 'children'>> = ({
  moduleLabel,
  activeView,
  views,
  onViewChange,
  searchValue,
  onSearchChange,
  onRefresh,
  refreshing,
  lastUpdated,
}) => {
  return (
    <header className="psa-topbar">
      <div className="psa-brand">
        <div className="psa-brand-mark">
          <BarChartOutlined />
        </div>
        <div>
          <div className="psa-brand-title">公众情绪分析</div>
          <div className="psa-brand-subtitle">{moduleLabel}</div>
        </div>
      </div>

      <nav className="psa-view-tabs" aria-label={`${moduleLabel}子页面`}>
        {views.map((view) => (
          <button
            type="button"
            key={view.key}
            className={view.key === activeView ? 'psa-view-tab active' : 'psa-view-tab'}
            onClick={() => onViewChange(view.key)}
          >
            {view.icon}
            <span>{view.label}</span>
          </button>
        ))}
      </nav>

      <div className="psa-top-actions">
        <span className="psa-sync-badge">
          <CheckCircleFilled />
          {lastUpdated ? `同步 ${lastUpdated}` : '待同步'}
        </span>
        {onSearchChange && (
          <label className="psa-search">
            <SearchOutlined />
            <input
              value={searchValue || ''}
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder="搜索关键词"
            />
          </label>
        )}
        {onRefresh && (
          <Button
            className="psa-dark-action"
            icon={<ReloadOutlined />}
            onClick={onRefresh}
            loading={refreshing}
          >
            刷新
          </Button>
        )}
      </div>
    </header>
  );
};

export const FloatingDock: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const current = location.pathname === '/analysis' || location.pathname === '/sentiment'
    ? '/analysis'
    : location.pathname === '/management' || location.pathname === '/stats'
      ? '/management'
      : location.pathname;

  return (
    <nav className="psa-floating-dock" aria-label="主导航">
      {moduleRoutes.map((item) => (
        <button
          type="button"
          key={item.path}
          className={item.path === current ? 'psa-dock-item active' : 'psa-dock-item'}
          onClick={() => navigate(item.path)}
        >
          {item.icon}
          <span>{item.label}</span>
        </button>
      ))}
    </nav>
  );
};

interface PanelProps {
  title?: string;
  eyebrow?: string;
  extra?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
}

export const Panel: React.FC<PanelProps> = ({ title, eyebrow, extra, className, children }) => (
  <section className={`psa-panel ${className || ''}`}>
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
  <article className={`psa-metric-card ${tone}`}>
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
      <div className="psa-state" style={{ minHeight }}>
        <Skeleton active paragraph={{ rows: 4 }} />
      </div>
    );
  }

  if (error) {
    return (
      <Result
        className="psa-result"
        status="warning"
        icon={<ExclamationCircleOutlined />}
        title="数据加载失败"
        subTitle={error}
      />
    );
  }

  if (empty) {
    return (
      <div className="psa-state" style={{ minHeight }}>
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
  <div className="psa-section-notice">
    <AppstoreOutlined />
    <div>
      <strong>{title}</strong>
      <p>{description}</p>
    </div>
  </div>
);
