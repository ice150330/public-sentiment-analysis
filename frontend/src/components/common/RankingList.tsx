import React, { useState, useEffect } from 'react';

interface RankingItem {
  id: string | number;
  rank: number;
  title: string;
  heat: number;
  platform: string;
  sentiment: 'positive' | 'neutral' | 'negative';
}

interface RankingListProps {
  data: RankingItem[];
  visibleCount?: number;
  scrollInterval?: number;
  title?: string;
}

const sentimentConfig: Record<string, { color: string; bg: string; text: string }> = {
  positive: { color: '#52c41a', bg: '#f6ffed', text: '正面' },
  neutral: { color: '#999', bg: '#fafafa', text: '中性' },
  negative: { color: '#f5222d', bg: '#fff1f0', text: '负面' },
};

export const RankingList: React.FC<RankingListProps> = ({
  data,
  visibleCount = 10,
  scrollInterval = 3000,
  title = '热榜 TOP10',
}) => {
  const [startIndex, setStartIndex] = useState(0);
  const total = data.length;
  const maxStart = Math.max(0, total - visibleCount);

  useEffect(() => {
    if (total <= visibleCount) return;
    const timer = setInterval(() => {
      setStartIndex((prev) => (prev + 1) % (maxStart + 1));
    }, scrollInterval);
    return () => clearInterval(timer);
  }, [total, visibleCount, maxStart, scrollInterval]);

  const visible = data.slice(startIndex, startIndex + visibleCount);

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <div style={{ width: 3, height: 16, background: '#1890ff', borderRadius: 2 }} />
        <span style={{ fontSize: 15, fontWeight: 600, color: '#1a1a2e' }}>{title}</span>
      </div>
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {visible.map((item) => {
          const sc = sentimentConfig[item.sentiment] || sentimentConfig.neutral;
          return (
            <div
              key={item.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: '6px 0',
                borderBottom: '1px solid #f5f5f5',
                fontSize: 13,
                gap: 8,
              }}
            >
              <span
                style={{
                  width: 22,
                  height: 22,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  borderRadius: 4,
                  fontSize: 12,
                  fontWeight: 'bold',
                  flexShrink: 0,
                  ...(item.rank <= 3
                    ? {
                        background: item.rank === 1 ? '#fff1f0' : item.rank === 2 ? '#fff7e6' : '#e6f7ff',
                        color: item.rank === 1 ? '#f5222d' : item.rank === 2 ? '#fa8c16' : '#1890ff',
                      }
                    : { color: '#999' }),
                }}
              >
                {item.rank}
              </span>
              <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#333' }}>
                {item.title}
              </span>
              <span style={{ width: 50, color: '#999', fontSize: 11, flexShrink: 0 }}>{item.platform}</span>
              <span
                style={{
                  width: 36,
                  height: 18,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  borderRadius: 2,
                  fontSize: 11,
                  flexShrink: 0,
                  background: sc.bg,
                  color: sc.color,
                }}
              >
                {sc.text}
              </span>
              <span style={{ width: 65, textAlign: 'right', color: '#f5222d', fontWeight: 500, fontSize: 12, flexShrink: 0 }}>
                {(item.heat / 10000).toFixed(0)}万
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
