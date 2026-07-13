import React from 'react';
import { FlylineMap } from '@/components/visual/FlylineMap';

const sampleNodes = [
  { id: 'weibo', name: '微博', x: 80, y: 60, size: 10 },
  { id: 'douyin', name: '抖音', x: 200, y: 40, size: 8 },
  { id: 'toutiao', name: '头条', x: 320, y: 70, size: 8 },
  { id: 'zhihu', name: '知乎', x: 120, y: 160, size: 6 },
  { id: 'bilibili', name: 'B站', x: 280, y: 150, size: 7 },
  { id: 'center', name: '话题中心', x: 200, y: 100, size: 12 },
];

const sampleEdges = [
  { from: 'center', to: 'weibo', value: 100 },
  { from: 'center', to: 'douyin', value: 80 },
  { from: 'center', to: 'toutiao', value: 60 },
  { from: 'center', to: 'zhihu', value: 40 },
  { from: 'center', to: 'bilibili', value: 50 },
  { from: 'weibo', to: 'douyin', value: 30 },
  { from: 'toutiao', to: 'bilibili', value: 25 },
];

export const PropagationNetwork: React.FC = () => {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <div style={{ width: 3, height: 16, background: '#1890ff', borderRadius: 2 }} />
        <span style={{ fontSize: 15, fontWeight: 600, color: '#1a1a2e' }}>传播路径网络</span>
      </div>
      <div style={{ flex: 1, minHeight: 0, background: '#fafafa', borderRadius: 4 }}>
        <FlylineMap nodes={sampleNodes} edges={sampleEdges} width={400} height={240} />
      </div>
    </div>
  );
};
