import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';

/* ───── 预警趋势时间轴 ───── */

interface AlertTrendChartProps {
  data: { time: string; count: number; severity: 'P1' | 'P2' | 'P3' | 'P4' }[];
  title?: string;
  height?: number;
}

const AlertTrendChart: React.FC<AlertTrendChartProps> = ({
  data,
  title = '预警趋势 (24h)',
  height = 260,
}) => {
  const option = useMemo(() => {
    // 如果没有数据，生成模拟数据
    const hasData = data && data.length > 0;
    const hours = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, '0')}:00`);
    const counts = hasData
      ? data.map(d => d.count)
      : hours.map(() => Math.floor(Math.random() * 20) + 2);

    return {
      title: {
        text: title,
        left: 'center',
        top: 8,
        textStyle: { fontSize: 14, fontWeight: 'bold', color: '#1f2937' },
      },
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '8%', top: '20%', containLabel: true },
      xAxis: {
        type: 'category',
        data: hours,
        axisLabel: { fontSize: 10, color: '#6b7280', interval: 2 },
        axisLine: { lineStyle: { color: '#e5e7eb' } },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#6b7280' },
        splitLine: { lineStyle: { type: 'dashed', color: '#f3f4f6' } },
      },
      visualMap: {
        show: false,
        dimension: 1,
        pieces: [
          { gt: 15, color: '#f5222d' },
          { gt: 8, lte: 15, color: '#faad14' },
          { lte: 8, color: '#52c41a' },
        ],
      },
      series: [{
        type: 'line',
        data: counts,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { width: 2 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(245, 34, 45, 0.2)' },
              { offset: 1, color: 'rgba(245, 34, 45, 0)' },
            ],
          },
        },
        markLine: {
          silent: true,
          data: [{ yAxis: 10, lineStyle: { color: '#faad14', type: 'dashed' }, label: { formatter: '警戒线' } }],
        },
      }],
    };
  }, [data, title]);

  return (
    <div style={{ width: '100%', height }}>
      <ReactECharts option={option} style={{ height: '100%', width: '100%' }} />
    </div>
  );
};

export default AlertTrendChart;
