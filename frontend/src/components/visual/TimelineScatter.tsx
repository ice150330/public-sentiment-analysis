import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';

/* ───── 时间轴散点图：话题热度随时间演变 ───── */

interface TimelineScatterProps {
  data: Array<{ time: string; heat: number; title: string; platform: string }>;
  title?: string;
  height?: number;
}

const TimelineScatter: React.FC<TimelineScatterProps> = ({
  data,
  title = '话题热度演变',
  height = 240,
}) => {
  const option = useMemo(() => {
    const platformColors: Record<string, string> = {
      微博: '#f5222d', 抖音: '#722ed1', B站: '#1890ff',
      知乎: '#52c41a', 今日头条: '#faad14', 百度: '#13c2c2',
    };
    const platforms = [...new Set(data.map(d => d.platform))];

    const series = platforms.map(platform => ({
      name: platform,
      type: 'scatter',
      symbolSize: (val: number) => Math.max(8, Math.min(40, val / 5000)),
      data: data
        .filter(d => d.platform === platform)
        .map(d => ({ value: [d.time, d.heat], title: d.title })),
      itemStyle: { color: platformColors[platform] || '#1890ff' },
      emphasis: { focus: 'series', itemStyle: { borderColor: '#fff', borderWidth: 2 } },
    }));

    return {
      title: title ? {
        text: title,
        left: 'center',
        top: 8,
        textStyle: { fontSize: 14, fontWeight: 'bold', color: '#1f2937' },
      } : undefined,
      tooltip: {
        trigger: 'item',
        formatter: (p: any) => {
          const titleText = p.data?.title || '';
          return `${titleText.slice(0, 18)}${titleText.length > 18 ? '...' : ''}<br/>时间: ${p.value[0]}<br/>热度: ${Number(p.value[1]).toLocaleString()}`;
        },
      },
      legend: { data: platforms, bottom: 0, textStyle: { fontSize: 10 } },
      grid: { left: '8%', right: '8%', bottom: '15%', top: title ? '18%' : '8%', containLabel: true },
      xAxis: { type: 'time', axisLabel: { fontSize: 10, color: '#6b7280' }, splitLine: { show: false } },
      yAxis: { type: 'value', name: '热度', nameTextStyle: { fontSize: 10, color: '#6b7280' }, axisLabel: { fontSize: 10, color: '#6b7280' }, splitLine: { lineStyle: { type: 'dashed', color: '#f3f4f6' } } },
      series,
    };
  }, [data, title]);

  return (
    <div style={{ width: '100%', height }}>
      <ReactECharts option={option} style={{ height: '100%', width: '100%' }} />
    </div>
  );
};

export default TimelineScatter;
