import React from 'react';
import { ClockCircleOutlined, SyncOutlined } from '@ant-design/icons';

interface MonitorHeaderProps {
  title?: string;
  lastUpdated?: Date | null;
  refreshing?: boolean;
}

const MonitorHeader: React.FC<MonitorHeaderProps> = ({
  title = '公众情绪智能分析监控中心',
  lastUpdated,
  refreshing = false,
}) => {
  const timeStr = lastUpdated
    ? lastUpdated.toLocaleString('zh-CN', { hour12: false })
    : '--';

  return (
    <div
      style={{
        height: 56,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        background: '#fff',
        borderRadius: 8,
        boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
        flexShrink: 0,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ width: 4, height: 24, background: '#1890ff', borderRadius: 2 }} />
        <h1 style={{ margin: 0, fontSize: 22, fontWeight: 600, color: '#1a1a2e' }}>{title}</h1>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 24, color: '#666' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <SyncOutlined spin={refreshing} style={{ color: '#1890ff' }} />
          <span>{refreshing ? '刷新中' : '自动刷新'}</span>
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <ClockCircleOutlined />
          <span style={{ fontSize: 16, fontWeight: 500, fontFamily: 'monospace' }}>{timeStr}</span>
        </span>
      </div>
    </div>
  );
};

export default MonitorHeader;
