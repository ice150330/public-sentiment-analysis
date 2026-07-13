import React from 'react';
import { ArrowUpOutlined, ArrowDownOutlined, MinusOutlined } from '@ant-design/icons';

interface StatItem {
  label: string;
  value: string | number;
  unit?: string;
  trend?: 'up' | 'down' | 'flat';
  trendValue?: string;
  color: string;
}

interface StatCardProps {
  item: StatItem;
}

export const StatCard: React.FC<StatCardProps> = ({ item }) => {
  const trendColor = item.trend === 'up' ? '#52c41a' : item.trend === 'down' ? '#f5222d' : '#999';
  return (
    <div
      style={{
        flex: 1,
        background: '#fff',
        borderRadius: 8,
        padding: '16px 20px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        borderTop: `3px solid ${item.color}`,
        minWidth: 0,
      }}
    >
      <div style={{ color: '#666', fontSize: 14 }}>{item.label}</div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, margin: '8px 0' }}>
        <span style={{ fontSize: 40, fontWeight: 'bold', color: item.color, fontFamily: 'DIN Alternate, Roboto, monospace' }}>
          {item.value}
        </span>
        {item.unit && <span style={{ fontSize: 14, color: '#999' }}>{item.unit}</span>}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12 }}>
        {item.trend === 'up' && <ArrowUpOutlined style={{ color: '#52c41a' }} />}
        {item.trend === 'down' && <ArrowDownOutlined style={{ color: '#f5222d' }} />}
        {item.trend === 'flat' && <MinusOutlined style={{ color: '#999' }} />}
        <span style={{ color: trendColor }}>{item.trendValue}</span>
        <span style={{ color: '#999' }}>较昨日</span>
      </div>
    </div>
  );
};
