import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';

/* ───── 桑基图：平台 → 话题流向 ───── */

interface SankeyChartProps {
  data: Array<{ source: string; target: string; value: number }>;
  title?: string;
  height?: number;
}

const SankeyChart: React.FC<SankeyChartProps> = ({
  data,
  title = '平台话题流向',
  height = 280,
}) => {
  const option = useMemo(() => {
    const nameMap: Record<string, string> = {
      toutiao: '今日头条', bilibili: 'B站', douyin: '抖音',
      weibo: '微博', zhihu: '知乎', baidu: '百度',
    };

    // 提取所有节点
    const nodeSet = new Set<string>();
    data.forEach(d => { nodeSet.add(d.source); nodeSet.add(d.target); });
    const nodes = Array.from(nodeSet).map(name => ({
      name: nameMap[name] || name,
      itemStyle: { color: nameMap[name] ? '#1890ff' : undefined },
    }));

    const links = data.map(d => ({
      source: nameMap[d.source] || d.source,
      target: nameMap[d.target] || d.target,
      value: d.value,
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
        triggerOn: 'mousemove',
        formatter: (p: any) => {
          if (p.dataType === 'node') return `${p.name}<br/>热度: ${p.value}`;
          return `${p.data.source} → ${p.data.target}<br/>权重: ${p.data.value}`;
        },
      },
      series: [{
        type: 'sankey',
        data: nodes,
        links,
        emphasis: { focus: 'adjacency' },
        lineStyle: { color: 'gradient', curveness: 0.5, opacity: 0.3 },
        label: { fontSize: 10, color: '#4b5563' },
        itemStyle: { borderWidth: 1, borderColor: '#fff' },
        layoutIterations: 32,
      }],
    };
  }, [data, title]);

  return (
    <div style={{ width: '100%', height }}>
      <ReactECharts option={option} style={{ height: '100%', width: '100%' }} />
    </div>
  );
};

export default SankeyChart;
