import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';

/* ───── 热力图：时段 × 平台情感矩阵 ───── */

interface HeatmapChartProps {
  data: Array<[string, string, number]>; // [时段, 平台, 值]
  title?: string;
  height?: number;
}

const HeatmapChart: React.FC<HeatmapChartProps> = ({
  data,
  title = '时段情感热力图',
  height = 280,
}) => {
  const option = useMemo(() => {
    const hours = Array.from(new Set(data.map((item) => item[0]))).sort();
    const platforms = Array.from(new Set(data.map((item) => item[1])));
    const chartData = data;

    return {
      title: title ? {
        text: title,
        left: 'center',
        top: 8,
        textStyle: { fontSize: 14, fontWeight: 'bold', color: '#1f2937' },
      } : undefined,
      tooltip: {
        position: 'top',
        formatter: (p: any) => `${p.data[1]} ${p.data[0]}<br/>情感指数: ${p.data[2]}`,
      },
      grid: { left: '12%', right: '8%', bottom: '15%', top: title ? '18%' : '8%' },
      xAxis: {
        type: 'category',
        data: hours,
        splitArea: { show: true },
        axisLabel: { fontSize: 10, color: '#6b7280' },
      },
      yAxis: {
        type: 'category',
        data: platforms,
        splitArea: { show: true },
        axisLabel: { fontSize: 10, color: '#6b7280' },
      },
      visualMap: {
        min: 0,
        max: 100,
        calculable: true,
        show: chartData.length > 0,
        orient: 'horizontal',
        left: 'center',
        bottom: '0%',
        itemWidth: 12,
        itemHeight: 80,
        textStyle: { fontSize: 10 },
        inRange: {
          color: ['#e6f7ff', '#1890ff', '#096dd9', '#002c8c'],
        },
      },
      series: [{
        type: 'heatmap',
        data: chartData,
        label: { show: false },
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.2)' },
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

export default HeatmapChart;
