import React from 'react';
import BaseChart from '@/components/charts/BaseChart';

interface ChartPanelProps {
  title: string;
  options: any;
  height?: number;
  extra?: React.ReactNode;
}

export const ChartPanel: React.FC<ChartPanelProps> = ({ title, options, height = 280, extra }) => {
  return (
    <div style={{
      background: '#fff',
      borderRadius: 8,
      padding: '12px 16px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      minHeight: 0,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 3, height: 16, background: '#1890ff', borderRadius: 2 }} />
          <span style={{ fontSize: 15, fontWeight: 600, color: '#1a1a2e' }}>{title}</span>
        </div>
        {extra && <div>{extra}</div>}
      </div>
      <div style={{ flex: 1, minHeight: 0 }}>
        <BaseChart options={options} height={height} />
      </div>
    </div>
  );
};
