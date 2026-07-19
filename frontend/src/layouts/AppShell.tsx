import React from 'react';
import { Button, Tooltip } from 'antd';
import { useLocation, useNavigate } from 'react-router-dom';
import { gsap } from 'gsap';
import { useGSAP } from '@gsap/react';
import {
  CheckCircleFilled,
  DashboardOutlined,
  FireOutlined,
  LogoutOutlined,
  RadarChartOutlined,
  ReloadOutlined,
  SearchOutlined,
  SettingOutlined,
  SmileOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { useAuth } from '../auth/AuthContext';
import { NotifyBell } from './NotifyBell';

gsap.registerPlugin(useGSAP);

export interface SubView {
  key: string;
  label: string;
  icon?: React.ReactNode;
}

export interface ModuleFrameProps {
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
  { path: '/management', label: '管理', icon: <SettingOutlined />, adminOnly: true },
];

/**
 * 应用壳层 —— 对应 pen 组件 Top Function Bar + Floating Dock。
 * 顶栏：品牌 / 子视图切换 / 同步徽章 + 搜索 + 刷新 + 预警铃铛 + 用户区。
 * Dock：四模块快捷导航（管理仅 admin 可见）。
 */
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
  const location = useLocation();
  const motionScope = React.useRef<HTMLElement | null>(null);
  const previousPathRef = React.useRef<string | null>(null);

  useGSAP(() => {
    if (!motionScope.current) return undefined;

    const isRouteEntry = previousPathRef.current !== location.pathname;
    previousPathRef.current = location.pathname;

    const mm = gsap.matchMedia();
    mm.add(
      {
        isDesktop: '(min-width: 800px)',
        reduceMotion: '(prefers-reduced-motion: reduce)',
      },
      (context) => {
        const conditions = context.conditions as { isDesktop: boolean; reduceMotion: boolean };
        const shellTargets = [
          '.psa-topbar',
          '.psa-view-tab',
          '.psa-top-actions > *',
          '.psa-motion-card',
          '.psa-motion-state',
          '.psa-filter-bar',
          '.psa-floating-dock',
        ];

        if (conditions.reduceMotion) {
          gsap.set(shellTargets, { clearProps: 'all' });
          return undefined;
        }

        const contentTargets = gsap.utils.toArray<HTMLElement>(
          '.psa-motion-card, .psa-motion-state, .psa-filter-bar',
          motionScope.current,
        );
        const travel = conditions.isDesktop ? 10 : 6;
        const timeline = gsap.timeline({
          defaults: {
            ease: 'power2.out',
            overwrite: 'auto',
          },
        });

        if (isRouteEntry) {
          timeline
            .from('.psa-topbar', {
              autoAlpha: 0,
              y: -8,
              duration: 0.3,
              clearProps: 'transform,opacity,visibility',
            })
            .from('.psa-view-tab', {
              autoAlpha: 0,
              y: -4,
              duration: 0.18,
              stagger: 0.025,
              clearProps: 'transform,opacity,visibility',
            }, '-=0.16')
            .from('.psa-top-actions > *', {
              autoAlpha: 0,
              x: 6,
              duration: 0.22,
              stagger: 0.03,
              clearProps: 'transform,opacity,visibility',
            }, '-=0.14');
        }

        timeline.from(contentTargets, {
          autoAlpha: 0,
          y: travel,
          duration: 0.32,
          stagger: {
            each: 0.03,
            from: 'start',
          },
          clearProps: 'transform,opacity,visibility',
        }, isRouteEntry ? '-=0.06' : 0);

        if (isRouteEntry) {
          timeline.from('.psa-floating-dock', {
            autoAlpha: 0,
            y: 12,
            duration: 0.26,
            clearProps: 'transform,opacity,visibility',
          }, '-=0.18');
        }

        return undefined;
      },
      motionScope.current,
    );

    return () => mm.revert();
  }, {
    dependencies: [location.pathname, activeView],
    scope: motionScope,
    revertOnUpdate: true,
  });

  return (
    <main className="psa-screen" ref={motionScope}>
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
  const [localSearch, setLocalSearch] = React.useState('');
  const [now, setNow] = React.useState(() => Date.now());
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  React.useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 10000);
    return () => window.clearInterval(timer);
  }, []);

  const syncLabel = React.useMemo(() => {
    if (!lastUpdated) return '待同步';

    const updatedAt = new Date(lastUpdated).getTime();
    if (Number.isNaN(updatedAt)) return `同步 ${lastUpdated}`;

    const seconds = Math.max(0, Math.floor((now - updatedAt) / 1000));
    if (seconds < 60) return `同步 ${seconds}s`;

    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `同步 ${minutes}m`;

    return `同步 ${Math.floor(minutes / 60)}h`;
  }, [lastUpdated, now]);

  const searchValueToRender = onSearchChange ? (searchValue || '') : localSearch;
  const activeViewLabel = views.find((view) => view.key === activeView)?.label || moduleLabel;

  return (
    <header className="psa-topbar">
      <div className="psa-brand">
        <div className="psa-brand-mark">
          <RadarChartOutlined />
        </div>
        <div>
          <div className="psa-brand-title">公众情绪智能分析系统</div>
          <div className="psa-brand-subtitle">{activeViewLabel}</div>
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
          {syncLabel}
        </span>
        <label className="psa-search">
          <SearchOutlined />
          <input
            value={searchValueToRender}
            onChange={(event) => {
              if (onSearchChange) {
                onSearchChange(event.target.value);
                return;
              }

              setLocalSearch(event.target.value);
            }}
            placeholder="搜索关键词"
          />
        </label>
        {onRefresh && (
          <Button
            className="psa-dark-action"
            icon={<ReloadOutlined />}
            onClick={onRefresh}
            loading={refreshing}
          >
            刷新数据
          </Button>
        )}
        <NotifyBell />
        {user && (
          <>
            <button type="button" className="psa-user-chip" onClick={() => navigate('/profile')}>
              <UserOutlined />
              <span>{user.username}</span>
            </button>
            <Tooltip title="退出登录">
              <Button
                className="psa-icon-action"
                icon={<LogoutOutlined />}
                onClick={() => {
                  logout();
                  navigate('/login', { replace: true });
                }}
              />
            </Tooltip>
          </>
        )}
      </div>
    </header>
  );
};

export const FloatingDock: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const current = location.pathname === '/analysis' || location.pathname === '/sentiment'
    ? '/analysis'
    : location.pathname === '/management' || location.pathname === '/stats'
      ? '/management'
      : location.pathname === '/monitor' || location.pathname === '/screen'
        ? '/'
        : location.pathname;

  return (
    <nav className="psa-floating-dock" aria-label="主导航">
      {moduleRoutes.filter((item) => !item.adminOnly || user?.role === 'admin').map((item) => (
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
