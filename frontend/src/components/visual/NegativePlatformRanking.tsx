import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';

/* ───── 负面情感平台排行 ───── */

interface NegativePlatformRankingProps {
  data: Record<string, { negative: number; total: number }>;
  title?: string;
  height?: number;
}

const NegativePlatformRanking: React.FC<NegativePlatformRankingProps> = ({
  data,
  title = '负面情感平台排行',
  height = 280,
}) => {
  const option = useMemo(() => {
    const nameMap: Record<string, string> = {
      toutiao: '今日头条', bilibili: 'B站', douyin: '抖音',
      weibo: '微博', zhihu: '知乎', baidu: '百度',
    };
    const sorted = Object.entries(data)
      .map(([name, d]) => ({
        name: nameMap[name] || name,
        value: d.negative,
        pct: d.total > 0 ? ((d.negative / d.total) * 100).toFixed(1) : '0.0',
      }))
      .sort((a, b) => b.value - a.value);

    return {
      title: {
        text: title,
        left: 'center',
        top: 8,
        textStyle: { fontSize: 14, fontWeight: 'bold', color: '#1f2937' },
      },
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => `${params[0].name}<br/>负面: ${params[0].value} 条 (${params[0].data.pct}%)`,
      },
      grid: { left: '3%', right: '15%', bottom: '8%', top: '18%', containLabel: true },
      xAxis: { type: 'value', axisLabel: { color: '#4b5563' }, splitLine: { lineStyle: { type: 'dashed', color: '#e5e7eb' } } },
      yAxis: {
        type: 'category',
        data: sorted.map(d => d.name),
        axisLabel: { fontSize: 12, color: '#4b5563' },
        inverse: true,
      },
      series: [{
        type: 'bar',
        data: sorted.map(d => ({ value: d.value, pct: d.pct })),
        itemStyle: {
          color: (params: any) => {
            const colors = ['#f5222d', '#ff4d4f', '#ff7875', '#ffa39e', '#ffccc7', '#fff1f0'];
            return colors[params.dataIndex % colors.length];
          },
          borderRadius: [0, 4, 4, 0],
        },
        label: {
          show: true,
          position: 'right',
          formatter: (p: any) => `${p.value} (${p.data.pct}%)`,
          fontSize: 11,
          color: '#666',
        },
        barWidth: '50%',
      }],
    };
  }, [data, title]);

  return (
    <div style={{ width: '100%', height }}>
      <ReactECharts option={option} style={{ height: '100%', width: '100%' }} />
    </div>
  );
};

export default NegativePlatformRanking;
