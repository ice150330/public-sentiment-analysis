import React from 'react';
import { RankingList } from '@/components/common/RankingList';

const sampleData = [
  { id: 1, rank: 1, title: '法国vs摩洛哥晋级决赛', heat: 49590000, platform: '微博', sentiment: 'positive' as const },
  { id: 2, rank: 2, title: '福建晋江一厂房起火', heat: 47820000, platform: '抖音', sentiment: 'negative' as const },
  { id: 3, rank: 3, title: '台风巴威改变路线', heat: 45000000, platform: '头条', sentiment: 'neutral' as const },
  { id: 4, rank: 4, title: '高考录取分数线公布', heat: 42100000, platform: '知乎', sentiment: 'neutral' as const },
  { id: 5, rank: 5, title: '国产大飞机C919交付', heat: 39800000, platform: 'B站', sentiment: 'positive' as const },
  { id: 6, rank: 6, title: '新能源汽车补贴政策', heat: 36500000, platform: '头条', sentiment: 'positive' as const },
  { id: 7, rank: 7, title: '明星演唱会门票争议', heat: 34200000, platform: '微博', sentiment: 'negative' as const },
  { id: 8, rank: 8, title: 'AI技术突破新进展', heat: 31800000, platform: '知乎', sentiment: 'positive' as const },
  { id: 9, rank: 9, title: '城市交通拥堵治理', heat: 29500000, platform: '头条', sentiment: 'neutral' as const },
  { id: 10, rank: 10, title: '新片上映票房预测', heat: 27100000, platform: '抖音', sentiment: 'positive' as const },
];

export const TopicRankingPanel: React.FC = () => {
  return (
    <div style={{ background: '#fff', borderRadius: 8, padding: '12px 16px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <RankingList data={sampleData} title="热榜 TOP10" />
    </div>
  );
};
