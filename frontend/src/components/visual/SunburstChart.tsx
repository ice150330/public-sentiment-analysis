import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';

/* ───── 旭日图：平台 → 情感层级 ───── */

interface SunburstChartProps {
  data: Record<string, any>;
  title?: string;
  height?: number;
}

const SunburstChart: React.FC<SunburstChartProps> = ({
  data,
  title = '舆情层级分布',
  height = 280,
}) => {
  const option = useMemo(() => {
    const nameMap: Record<string, string> = {
      toutiao: '今日头条', bilibili: 'B站', douyin: '抖音',
      weibo: '微博', zhihu: '知乎', baidu: '百度',
    };

    const children = Object.entries(data).map(([name, dist]: [string, any]) => ({
      name: nameMap[name] || name,
      value: (dist.positive || 0) + (dist.negative || 0) + (dist.neutral || 0),
      children: [
        { name: '正面', value: dist.positive || 0, itemStyle: { color: '#52c41a' } },
        { name: '负面', value: dist.negative || 0, itemStyle: { color: '#f5222d' } },
        { name: '中性', value: dist.neutral || 0, itemStyle: { color: '#faad14' } },
      ],
    }));

    return {
      title: {
        text: title,
        left: 'center',
        top: 8,
        textStyle: { fontSize: 14, fontWeight: 'bold', color: '#1f2937' },
      },
      tooltip: {
        trigger: 'item',
        formatter: (p: any) => `${p.name}<br/>数量: ${p.value}`,
      },
      series: [{
        type: 'sunburst',
        data: children,
        radius: [20, '80%'],
        center: ['50%', '55%'],
        itemStyle: { borderRadius: 4, borderWidth: 1, borderColor: '#fff' },
        label: { rotate: 'radial', fontSize: 10 },
        emphasis: {
          focus: 'ancestor',
          itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.2)' },
        },
        levels: [
          {},
          { r0: '20%', r: '55%', label: { rotate: 'tangential', fontSize: 11 } },
          { r0: '55%', r: '80%', label: { position: 'outside', padding: 2, fontSize: 9 } },
        ],
      }],
    };
  }, [data, title]);

  return (
    <div style={{ width: '100%', height }}>
      <ReactECharts option={option} style={{ height: '100%', width: '100%' }} />
    </div>
  );
};

export default SunburstChart;
