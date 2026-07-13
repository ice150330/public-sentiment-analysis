import React, { useMemo } from 'react';

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
  height = 300,
}) => {
  const words = useMemo(() => {
    const sorted = [...data].sort((a, b) => b.value - a.value).slice(0, 80);
    const maxVal = sorted[0]?.value || 1;
    return sorted.map((item, index) => ({
      ...item,
      size: 12 + Math.round((item.value / maxVal) * 14),
      color: ['#2563EB', '#16A34A', '#E11D48', '#F59E0B', '#0EA5E9', '#64748B'][index % 6],
    }));
  }, [data]);

  return (
    <div className="psa-word-cloud" style={{ height }}>
      {words.map((word) => (
        <span
          key={word.name}
          className="psa-word-chip"
          style={{
            color: word.color,
            fontSize: word.size,
          }}
          title={`${word.name}: ${word.value.toLocaleString()}`}
        >
          {word.name}
        </span>
      ))}
    </div>
  );
};

export default WordCloudChart;
