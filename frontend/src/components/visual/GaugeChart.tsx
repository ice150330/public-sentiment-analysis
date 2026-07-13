import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';

/* ───── 仪表盘：健康度环形进度 ───── */

interface GaugeChartProps {
  score: number; // 0-100
  title?: string;
  height?: number;
}

const GaugeChart: React.FC<GaugeChartProps> = ({
  score,
  title = '舆情健康度',
  height = 240,
}) => {
  const option = useMemo(() => {
    const color = score >= 70 ? '#52c41a' : score >= 40 ? '#faad14' : '#f5222d';
    return {
      title: {
        text: title,
        left: 'center',
        top: 8,
        textStyle: { fontSize: 14, fontWeight: 'bold', color: '#1f2937' },
      },
      series: [{
        type: 'gauge',
        startAngle: 200,
        endAngle: -20,
        radius: '75%',
        center: ['50%', '55%'],
        min: 0,
        max: 100,
        splitNumber: 10,
        axisLine: {
          lineStyle: {
            width: 18,
            color: [
              [0.3, '#f5222d'],
              [0.7, '#faad14'],
              [1, '#52c41a'],
            ],
          },
        },
        pointer: { length: '60%', width: 5, itemStyle: { color: color } },
        axisTick: { length: 10, lineStyle: { color: 'auto', width: 2 } },
        splitLine: { length: 16, lineStyle: { color: 'auto', width: 3 } },
        axisLabel: { color: '#6b7280', fontSize: 10, distance: 22 },
        title: { offsetCenter: [0, '70%'], fontSize: 12, color: '#4b5563' },
        detail: {
          fontSize: 28,
          offsetCenter: [0, '40%'],
          valueAnimation: true,
          formatter: '{value}%',
          color: color,
          fontWeight: 'bold',
        },
        data: [{ value: score, name: score >= 70 ? '健康' : score >= 40 ? '一般' : '预警' }],
      }],
    };
  }, [score, title]);

  return (
    <div style={{ width: '100%', height }}>
      <ReactECharts option={option} style={{ height: '100%', width: '100%' }} />
    </div>
  );
};

export default GaugeChart;
