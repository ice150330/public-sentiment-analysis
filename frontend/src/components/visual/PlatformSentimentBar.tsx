import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';

/* ───── 各平台情感堆叠柱状图 ───── */

interface PlatformSentimentBarProps {
  data: Record<string, { positive: number; negative: number; neutral: number }>;
  title?: string;
  height?: number;
}

const PlatformSentimentBar: React.FC<PlatformSentimentBarProps> = ({
  data,
  title = '各平台情感分布',
  height = 280,
}) => {
  const option = useMemo(() => {
    const platforms = Object.keys(data);
    const nameMap: Record<string, string> = {
      toutiao: '今日头条', bilibili: 'B站', douyin: '抖音',
      weibo: '微博', zhihu: '知乎', baidu: '百度',
    };
    const labels = platforms.map(p => nameMap[p] || p);
    const posData = platforms.map(p => data[p].positive);
    const negData = platforms.map(p => data[p].negative);
    const neuData = platforms.map(p => data[p].neutral);

    return {
      title: {
        text: title,
        left: 'center',
        top: 8,
        textStyle: { fontSize: 14, fontWeight: 'bold', color: '#1f2937' },
      },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { data: ['正面', '负面', '中性'], bottom: 0 },
      grid: { left: '3%', right: '4%', bottom: '15%', top: '18%', containLabel: true },
      xAxis: { type: 'category', data: labels, axisLabel: { fontSize: 11, color: '#4b5563' } },
      yAxis: { type: 'value', axisLabel: { color: '#4b5563' }, splitLine: { lineStyle: { type: 'dashed', color: '#e5e7eb' } } },
      series: [
        { name: '正面', type: 'bar', stack: 'total', data: posData, itemStyle: { color: '#52c41a', borderRadius: [4, 4, 0, 0] } },
        { name: '负面', type: 'bar', stack: 'total', data: negData, itemStyle: { color: '#f5222d', borderRadius: [4, 4, 0, 0] } },
        { name: '中性', type: 'bar', stack: 'total', data: neuData, itemStyle: { color: '#faad14', borderRadius: [4, 4, 0, 0] } },
      ],
    };
  }, [data, title]);

  return (
    <div style={{ width: '100%', height }}>
      <ReactECharts option={option} style={{ height: '100%', width: '100%' }} />
    </div>
  );
};

export default PlatformSentimentBar;
