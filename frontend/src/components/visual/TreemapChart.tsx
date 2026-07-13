import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';

/* ───── 树图：按平台-情感层级展示体量 ───── */

interface TreemapChartProps {
  data: Record<string, any>;
  title?: string;
  height?: number;
}

const TreemapChart: React.FC<TreemapChartProps> = ({
  data,
  title = '舆情体量分布',
  height = 240,
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
        type: 'treemap',
        data: children,
        width: '90%',
        height: '75%',
        top: '15%',
        roam: false,
        nodeClick: false,
        breadcrumb: { show: false },
        label: { show: true, fontSize: 12, formatter: '{b}\n{c}' },
        itemStyle: { borderColor: '#fff', borderWidth: 2, gapWidth: 2 },
        levels: [
          { itemStyle: { borderColor: '#fff', borderWidth: 4, gapWidth: 4 } },
          { colorSaturation: [0.35, 0.5], itemStyle: { borderColorSaturation: 0.6, gapWidth: 2 } },
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

export default TreemapChart;
