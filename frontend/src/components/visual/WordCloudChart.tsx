import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';

/* ───── 词云图组件 ───── */

interface WordCloudData {
  name: string;
  value: number;
}

interface WordCloudChartProps {
  data: WordCloudData[];
  title?: string;
  height?: number;
}

const WordCloudChart: React.FC<WordCloudChartProps> = ({
  data,
  title = '关键词云',
  height = 300,
}) => {
  const option = useMemo(() => {
    const sorted = [...data].sort((a, b) => b.value - a.value).slice(0, 80);
    const maxVal = sorted[0]?.value || 1;

    return {
      title: {
        text: title,
        left: 'center',
        top: 8,
        textStyle: { fontSize: 14, fontWeight: 'bold', color: '#1f2937' },
      },
      tooltip: {
        show: true,
        formatter: (params: any) => `${params.name}: ${params.value}`,
      },
      series: [{
        type: 'scatter',
        symbolSize: (val: number[]) => Math.max(12, (val[2] / maxVal) * 60),
        data: sorted.map((item, index) => ({
          name: item.name,
          value: [index % 10, Math.floor(index / 10), item.value],
          itemStyle: {
            color: `hsl(${200 + (index * 137.5) % 60}, ${70 + (index % 20)}%, ${45 + (index % 15)}%)`,
          },
        })),
        label: {
          show: true,
          formatter: (p: any) => p.name,
          fontSize: 12,
          color: '#1f2937',
        },
        emphasis: {
          label: { fontSize: 16, fontWeight: 'bold' },
          itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.2)' },
        },
      }],
      grid: { top: 40, right: 10, bottom: 10, left: 10 },
      xAxis: { show: false, min: -1, max: 10 },
      yAxis: { show: false, min: -1, max: 8 },
    };
  }, [data, title]);

  return (
    <div style={{ width: '100%', height }}>
      <ReactECharts option={option} style={{ height: '100%', width: '100%' }} />
    </div>
  );
};

export default WordCloudChart;
