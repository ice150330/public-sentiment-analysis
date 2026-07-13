import React from 'react';
import { StatCard } from '@/components/common/StatCard';
import { LiquidGauge } from '@/components/visual/LiquidGauge';

interface StatItem {
  label: string;
  value: string | number;
  unit?: string;
  trend?: 'up' | 'down' | 'flat';
  trendValue?: string;
  color: string;
}

interface StatsRowProps {
  stats: StatItem[];
  healthScore?: number;
}

const StatsRow: React.FC<StatsRowProps> = ({ stats, healthScore = 86 }) => {
  return (
    <div style={{ display: 'flex', gap: 16, height: 140, flexShrink: 0 }}>
      {stats.map((item, i) => (
        <StatCard key={i} item={item} />
      ))}
      <div
        style={{
          width: 180,
          background: '#fff',
          borderRadius: 8,
          padding: '8px 12px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        <LiquidGauge value={healthScore} size={100} />
      </div>
    </div>
  );
};

export default StatsRow;
