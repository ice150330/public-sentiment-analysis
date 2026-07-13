import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';

/* ───── 平台多维雷达图 ───── */

interface PlatformRadarProps {
  data: Record<string, { heat: number; positive: number; negative: number; neutral: number; alert: number }>;
  title?: string;
  height?: number;
}

const PlatformRadarChart: React.FC<PlatformRadarProps> = ({
  data,
  title = '平台多维对比',
  height = 300,
}) => {
  const option = useMemo(() => {
    const platforms = Object.keys(data);
    const indicators = [
      { name: '热度', max: 100 },
      { name: '正面率', max: 100 },
      { name: '负面率', max: 100 },
      { name: '中性率', max: 100 },
      { name: '预警数', max: Math.max(10, ...Object.values(data).map(d => d.alert)) * 1.2 },
    ];

    const seriesData = platforms.map((name, idx) => {
      const d = data[name];
      const total = d.positive + d.negative + d.neutral || 1;
      return {
        name: name === 'toutiao' ? '今日头条' : name === 'bilibili' ? 'B站' : name === 'douyin' ? '抖音' : name === 'weibo' ? '微博' : name === 'zhihu' ? '知乎' : name === 'baidu' ? '百度' : name,
        value: [
          Math.min(100, d.heat),
          (d.positive / total) * 100,
          (d.negative / total) * 100,
          (d.neutral / total) * 100,
          d.alert,
        ],
        lineStyle: { width: 2 },
        areaStyle: { opacity: 0.15 },
        symbolSize: 4,
      };
    });

    return {
      title: {
        text: title,
        left: 'center',
        top: 8,
        textStyle: { fontSize: 14, fontWeight: 'bold', color: '#1f2937' },
      },
      tooltip: { trigger: 'item' },
      legend: {
        data: seriesData.map((d: any) => d.name),
        bottom: 0,
        textStyle: { fontSize: 10 },
        itemWidth: 12,
        itemHeight: 8,
      },
      radar: {
        indicator: indicators,
        center: ['50%', '50%'],
        radius: '55%',
        axisName: { color: '#4b5563', fontSize: 11 },
        splitArea: { areaStyle: { color: ['#fff', '#f8fafc', '#f1f5f9', '#e2e8f0'] } },
      },
      series: [{
        type: 'radar',
        data: seriesData,
        emphasis: { lineStyle: { width: 3 } },
      }],
    };
  }, [data, title]);

  return (
    <div style={{ width: '100%', height }}>
      <ReactECharts option={option} style={{ height: '100%', width: '100%' }} />
    </div>
  );
};

export default PlatformRadarChart;
