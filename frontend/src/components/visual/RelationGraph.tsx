import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';

/* ───── 关系图谱组件（ECharts Graph） ───── */

interface GraphNode {
  id: string;
  name: string;
  category: number;
  value?: number;
  symbolSize?: number;
}

interface GraphLink {
  source: string;
  target: string;
  value?: number;
}

interface RelationGraphProps {
  nodes: GraphNode[];
  links: GraphLink[];
  categories?: string[];
  title?: string;
  height?: number;
}

const RelationGraph: React.FC<RelationGraphProps> = ({
  nodes,
  links,
  categories = ['话题', '实体', '关键词'],
  title = '舆情关系图谱',
  height = 400,
}) => {
  const option = useMemo(() => {
    const catList = categories.map((name, index) => ({ name, itemStyle: { color: ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de'][index % 5] } }));

    return {
      title: {
        text: title,
        left: 'center',
        top: 8,
        textStyle: { fontSize: 14, fontWeight: 'bold', color: '#1f2937' },
      },
      tooltip: {
        formatter: (params: any) => {
          if (params.dataType === 'node') {
            return `${params.name}<br/>关联度: ${params.value || 0}`;
          }
          return `${params.data.source} → ${params.data.target}<br/>权重: ${params.data.value || 0}`;
        },
      },
      legend: {
        data: categories,
        bottom: 0,
        textStyle: { color: '#4b5563' },
      },
      series: [{
        type: 'graph',
        layout: 'circular',
        circular: { rotateLabel: false },
        data: nodes.map(n => ({
          ...n,
          symbolSize: n.symbolSize || 30 + (n.value || 0) * 2,
          label: { show: true, fontSize: 11, color: '#1f2937' },
        })),
        links: links.map(l => ({
          ...l,
          lineStyle: { width: Math.min(4, Math.max(1, (l.value || 1) / 4)), curveness: 0.2, opacity: 0.18 },
        })),
        categories: catList,
        roam: false,
        draggable: false,
        focusNodeAdjacency: true,
        emphasis: {
          focus: 'adjacency',
          lineStyle: { width: 4 },
        },
      }],
    };
  }, [nodes, links, categories, title]);

  return (
    <div style={{ width: '100%', height }}>
      <ReactECharts option={option} style={{ height: '100%', width: '100%' }} />
    </div>
  );
};

export default RelationGraph;
