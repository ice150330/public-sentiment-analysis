# 舆情系统整合升级方案 v2.1 — 白色大屏风格

> 版本: v2.1
> 日期: 2026-07-10
> 核心原则: **白色/浅灰背景 + 大屏信息密度 + 一屏展示 + 大数字大图表**

---

## 一、设计方向修正

### 1.1 之前的问题

v2 方案虽然保留了白色风格，但布局还是**后台管理系统模式**：
- ❌ 信息密度低，大量留白
- ❌ 需要滚动查看
- ❌ 卡片小，数字小
- ❌ 像在看报表，不像监控

### 1.2 正确的方向：白色大屏

参考现代 BI 大屏、医疗监控大屏、金融数据墙：
- ✅ 白色/浅灰背景（保留）
- ✅ **高信息密度**——一屏展示所有核心指标
- ✅ **大数字**——核心指标用 48-72px
- ✅ **大图表**——图表区域占满卡片
- ✅ **紧凑布局**——边距 12-16px，不浪费空间
- ✅ **层次分明**——用色块、边框、阴影区分区域

### 1.3 视觉参考

```
白色大屏（目标效果）:

┌────────────────────────────────────────────────────────────────────┐
│ 公众情绪智能分析监控中心                              2026-07-10 15:30  │
├──────────┬──────────┬──────────┬──────────┬──────────┬─────────────┤
│          │          │          │          │          │             │
│  1,234   │  86.0%   │   6.5%   │   12     │   45     │   [水位图]   │
│  总采集   │  正面    │  负面    │  预警    │  话题    │  情感健康度  │
│  ↑12%    │  ↑2.3%   │  ↓1.1%   │  持平    │  ↑5      │    86%      │
│          │          │          │          │          │             │
├──────────┴──────────┴──────────┴──────────┴──────────┴─────────────┤
│                                                                    │
│  ┌──────────────────────────┐  ┌──────────────────────────┐       │
│  │                          │  │                          │       │
│  │      情感趋势 (24h)       │  │      平台分布占比         │       │
│  │      [大折线图]           │  │      [大环形图]           │       │
│  │      高度: 280px          │  │      高度: 280px          │       │
│  │                          │  │                          │       │
│  └──────────────────────────┘  └──────────────────────────┘       │
│                                                                    │
│  ┌──────────────────────────┐  ┌──────────────────────────┐       │
│  │  热榜 TOP10              │  │  传播路径网络             │       │
│  │  ┌────────────────────┐  │  │                          │       │
│  │  │1 法国vs摩洛哥   4959万│  │  │      [SVG 网络图]         │       │
│  │  │2 福建晋江起火   4782万│  │  │      白色底+蓝线          │       │
│  │  │3 台风巴威改路线 4500万│  │  │      高度: 280px          │       │
│  │  │ ...                 │  │  │                          │       │
│  │  └────────────────────┘  │  └──────────────────────────┘       │
│  └──────────────────────────┘                                      │
│                                                                    │
│  ┌──────────────────────────┐  ┌──────────────────────────┐       │
│  │  话题词云                 │  │  地域分布                 │       │
│  │  [大词云图]               │  │  [地图热力]               │       │
│  │  高度: 200px              │  │  高度: 200px              │       │
│  └──────────────────────────┘  └──────────────────────────┘       │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘

特点:
- 白色背景 #f5f7fa
- 卡片白色 #fff，阴影分隔
- 大数字 48-72px
- 图表区域大，边距紧凑
- 一屏展示，无需滚动
- 信息密度高，监控感强
```

---

## 二、布局架构

### 2.1 屏幕适配方案

```typescript
// hooks/useScreenAdapt.ts
// 采用 scale 缩放方案（参考 big-screen-vue-datav）
// 但基准改为 1920x1080，适配白色大屏

import { useEffect, useRef } from 'react';

const DESIGN_WIDTH = 1920;
const DESIGN_HEIGHT = 1080;

export function useScreenAdapt() {
  const containerRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    const calcScale = () => {
      if (!containerRef.current) return;
      
      const w = window.innerWidth;
      const h = window.innerHeight;
      
      // 等比例缩放，保持内容比例
      const scaleX = w / DESIGN_WIDTH;
      const scaleY = h / DESIGN_HEIGHT;
      const scale = Math.min(scaleX, scaleY);
      
      // 居中显示
      const offsetX = (w - DESIGN_WIDTH * scale) / 2;
      const offsetY = (h - DESIGN_HEIGHT * scale) / 2;
      
      containerRef.current.style.transform = `scale(${scale})`;
      containerRef.current.style.transformOrigin = '0 0';
      containerRef.current.style.position = 'absolute';
      containerRef.current.style.left = `${offsetX}px`;
      containerRef.current.style.top = `${offsetY}px`;
    };
    
    calcScale();
    window.addEventListener('resize', calcScale);
    return () => window.removeEventListener('resize', calcScale);
  }, []);
  
  return containerRef;
}
```

### 2.2 大屏布局组件

```tsx
// components/monitor/MonitorLayout.tsx
import React from 'react';
import { useScreenAdapt } from '@/hooks/useScreenAdapt';

interface Props {
  children: React.ReactNode;
}

export const MonitorLayout: React.FC<Props> = ({ children }) => {
  const containerRef = useScreenAdapt();
  
  return (
    <div style={{
      width: '100vw',
      height: '100vh',
      background: '#e8ecf1',  // 浅灰背景，衬托白色卡片
      overflow: 'hidden',
      position: 'relative',
    }}>
      <div
        ref={containerRef}
        style={{
          width: DESIGN_WIDTH,
          height: DESIGN_HEIGHT,
          background: '#f5f7fa',
          padding: '16px',
          boxSizing: 'border-box',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
        }}
      >
        {children}
      </div>
    </div>
  );
};
```

### 2.3 区域划分

```tsx
// Monitor.tsx 布局结构
<MonitorLayout>
  {/* 头部 */}
  <MonitorHeader />
  
  {/* 核心指标行 */}
  <StatsRow />
  
  {/* 主内容区 - 左右分栏 */}
  <div style={{ display: 'flex', gap: '16px', flex: 1 }}>
    {/* 左侧 60% */}
    <div style={{ flex: '1.5', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <TrendCharts />      {/* 趋势图 + 饼图 */}
      <TopicRanking />     {/* 热榜排名 */}
    </div>
    
    {/* 右侧 40% */}
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <SentimentGauge />   {/* 情感仪表盘 */}
      <PropagationMap />   {/* 传播网络 */}
      <WordCloud />        {/* 词云 */}
    </div>
  </div>
</MonitorLayout>
```

---

## 三、核心组件设计

### 3.1 头部区域

```tsx
// components/monitor/MonitorHeader.tsx
import React from 'react';
import { ClockCircleOutlined, SyncOutlined } from '@ant-design/icons';

export const MonitorHeader: React.FC = () => {
  return (
    <div style={{
      height: '60px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 24px',
      background: '#fff',
      borderRadius: '8px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{
          width: '4px',
          height: '24px',
          background: '#1890ff',
          borderRadius: '2px',
        }} />
        <h1 style={{
          margin: 0,
          fontSize: '24px',
          fontWeight: 600,
          color: '#1a1a2e',
        }}>
          公众情绪智能分析监控中心
        </h1>
      </div>
      
      <div style={{ display: 'flex', alignItems: 'center', gap: '24px', color: '#666' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <SyncOutlined spin style={{ color: '#1890ff' }} />
          <span>自动刷新中</span>
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <ClockCircleOutlined />
          <span style={{ fontSize: '18px', fontWeight: 500, fontFamily: 'monospace' }}>
            2026-07-10 15:30:00
          </span>
        </span>
      </div>
    </div>
  );
};
```

### 3.2 核心指标行

```tsx
// components/monitor/StatsRow.tsx
import React from 'react';
import { ArrowUpOutlined, ArrowDownOutlined, MinusOutlined } from '@ant-design/icons';

interface StatItem {
  label: string;
  value: string | number;
  unit?: string;
  trend?: 'up' | 'down' | 'flat';
  trendValue?: string;
  color?: string;
}

const stats: StatItem[] = [
  { label: '总采集', value: '1,234', unit: '条', trend: 'up', trendValue: '12%', color: '#1890ff' },
  { label: '正面情感', value: '86.0', unit: '%', trend: 'up', trendValue: '2.3%', color: '#52c41a' },
  { label: '负面情感', value: '6.5', unit: '%', trend: 'down', trendValue: '1.1%', color: '#f5222d' },
  { label: '预警事件', value: '12', unit: '条', trend: 'flat', trendValue: '持平', color: '#faad14' },
  { label: '活跃话题', value: '45', unit: '个', trend: 'up', trendValue: '5', color: '#722ed1' },
];

export const StatsRow: React.FC = () => {
  return (
    <div style={{ display: 'flex', gap: '16px', height: '140px' }}>
      {stats.map((stat, i) => (
        <div
          key={i}
          style={{
            flex: 1,
            background: '#fff',
            borderRadius: '8px',
            padding: '20px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            borderTop: `3px solid ${stat.color}`,
          }}
        >
          <div style={{ color: '#666', fontSize: '14px' }}>{stat.label}</div>
          
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
            <span style={{
              fontSize: '40px',
              fontWeight: 'bold',
              color: stat.color,
              fontFamily: '"DIN Alternate", "Roboto", monospace',
            }}>
              {stat.value}
            </span>
            {stat.unit && (
              <span style={{ fontSize: '16px', color: '#999' }}>{stat.unit}</span>
            )}
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px' }}>
            {stat.trend === 'up' && <ArrowUpOutlined style={{ color: '#52c41a' }} />}
            {stat.trend === 'down' && <ArrowDownOutlined style={{ color: '#f5222d' }} />}
            {stat.trend === 'flat' && <MinusOutlined style={{ color: '#999' }} />}
            <span style={{ color: stat.trend === 'up' ? '#52c41a' : stat.trend === 'down' ? '#f5222d' : '#999' }}>
              {stat.trendValue}
            </span>
            <span style={{ color: '#999' }}>较昨日</span>
          </div>
        </div>
      ))}
      
      {/* 情感健康度仪表盘 */}
      <div style={{
        width: '180px',
        background: '#fff',
        borderRadius: '8px',
        padding: '12px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        <LiquidGauge value={86} size={100} />
        <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>情感健康度</div>
      </div>
    </div>
  );
};
```

### 3.3 白色风格 ECharts 主题

```typescript
// theme/echarts-white.ts
export const echartsWhiteTheme = {
  color: ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2', '#eb2f96', '#fadb14'],
  
  backgroundColor: 'transparent',
  
  textStyle: {
    color: '#333',
    fontSize: 12,
  },
  
  title: {
    textStyle: { color: '#1a1a2e', fontSize: 16, fontWeight: 'bold' },
    subtextStyle: { color: '#666' },
    top: 8,
    left: 16,
  },
  
  legend: {
    top: 8,
    right: 16,
    textStyle: { color: '#666', fontSize: 11 },
    itemWidth: 12,
    itemHeight: 8,
  },
  
  tooltip: {
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    borderColor: '#e8e8e8',
    borderWidth: 1,
    textStyle: { color: '#333', fontSize: 12 },
    padding: [8, 12],
    extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.1); border-radius: 4px;',
  },
  
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    top: '15%',
    containLabel: true,
  },
  
  categoryAxis: {
    axisLine: { show: true, lineStyle: { color: '#e8e8e8' } },
    axisTick: { show: false },
    axisLabel: { color: '#999', fontSize: 11 },
    splitLine: { show: true, lineStyle: { color: '#f0f0f0', type: 'dashed' } },
  },
  
  valueAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: '#999', fontSize: 11 },
    splitLine: { show: true, lineStyle: { color: '#f0f0f0', type: 'dashed' } },
  },
  
  // 饼图专用
  pie: {
    radius: ['45%', '70%'],
    center: ['50%', '55%'],
    label: { color: '#666', fontSize: 11 },
    emphasis: {
      label: { fontSize: 14, fontWeight: 'bold' },
      itemStyle: {
        shadowBlur: 10,
        shadowOffsetX: 0,
        shadowColor: 'rgba(0, 0, 0, 0.1)',
      },
    },
  },
};
```

### 3.4 紧凑图表卡片

```tsx
// components/monitor/ChartPanel.tsx
import React from 'react';
import { BaseChart } from '@/components/charts/BaseChart';

interface Props {
  title: string;
  options: any;
  height?: number;
  extra?: React.ReactNode;
}

export const ChartPanel: React.FC<Props> = ({ title, options, height = 260, extra }) => {
  return (
    <div style={{
      background: '#fff',
      borderRadius: '8px',
      padding: '16px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '12px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{
            width: '3px',
            height: '16px',
            background: '#1890ff',
            borderRadius: '2px',
          }} />
          <span style={{ fontSize: '15px', fontWeight: 600, color: '#1a1a2e' }}>
            {title}
          </span>
        </div>
        {extra && <div>{extra}</div>}
      </div>
      
      <div style={{ flex: 1 }}>
        <BaseChart options={options} height={height} />
      </div>
    </div>
  );
};
```

### 3.5 热榜排名（紧凑版）

```tsx
// components/monitor/TopicRanking.tsx
import React from 'react';
import { Tag } from 'antd';

interface TopicItem {
  rank: number;
  title: string;
  heat: number;
  platform: string;
  sentiment: 'positive' | 'neutral' | 'negative';
}

interface Props {
  data: TopicItem[];
}

const sentimentConfig = {
  positive: { color: '#52c41a', text: '正面' },
  neutral: { color: '#999', text: '中性' },
  negative: { color: '#f5222d', text: '负面' },
};

export const TopicRanking: React.FC<Props> = ({ data }) => {
  return (
    <div style={{
      background: '#fff',
      borderRadius: '8px',
      padding: '16px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        marginBottom: '12px',
      }}>
        <div style={{ width: '3px', height: '16px', background: '#1890ff', borderRadius: '2px' }} />
        <span style={{ fontSize: '15px', fontWeight: 600, color: '#1a1a2e' }}>热榜 TOP10</span>
      </div>
      
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {data.map((item) => (
          <div
            key={item.rank}
            style={{
              display: 'flex',
              alignItems: 'center',
              padding: '8px 0',
              borderBottom: '1px solid #f5f5f5',
              fontSize: '13px',
            }}
          >
            {/* 排名 */}
            <span style={{
              width: '22px',
              height: '22px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: 'bold',
              marginRight: '12px',
              ...(item.rank <= 3 ? {
                background: item.rank === 1 ? '#fff1f0' : item.rank === 2 ? '#fff7e6' : '#e6f7ff',
                color: item.rank === 1 ? '#f5222d' : item.rank === 2 ? '#fa8c16' : '#1890ff',
              } : {
                color: '#999',
              }),
            }}>
              {item.rank}
            </span>
            
            {/* 标题 */}
            <span style={{
              flex: 1,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              color: '#333',
            }}>
              {item.title}
            </span>
            
            {/* 平台 */}
            <span style={{ width: '50px', color: '#999', fontSize: '11px' }}>
              {item.platform}
            </span>
            
            {/* 情感 */}
            <span style={{
              width: '36px',
              height: '18px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: '2px',
              fontSize: '11px',
              marginRight: '12px',
              background: `${sentimentConfig[item.sentiment].color}15`,
              color: sentimentConfig[item.sentiment].color,
            }}>
              {sentimentConfig[item.sentiment].text}
            </span>
            
            {/* 热度 */}
            <span style={{
              width: '70px',
              textAlign: 'right',
              color: '#f5222d',
              fontWeight: 500,
              fontSize: '12px',
            }}>
              {(item.heat / 10000).toFixed(0)}万
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
```

### 3.6 传播网络图（白色风格）

```tsx
// components/monitor/PropagationNetwork.tsx
import React from 'react';

interface Node {
  id: string;
  name: string;
  x: number;
  y: number;
  size: number;
}

interface Edge {
  from: string;
  to: string;
  value: number;
}

interface Props {
  nodes: Node[];
  edges: Edge[];
}

export const PropagationNetwork: React.FC<Props> = ({ nodes, edges }) => {
  return (
    <div style={{
      background: '#fff',
      borderRadius: '8px',
      padding: '16px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        marginBottom: '12px',
      }}>
        <div style={{ width: '3px', height: '16px', background: '#1890ff', borderRadius: '2px' }} />
        <span style={{ fontSize: '15px', fontWeight: 600, color: '#1a1a2e' }}>传播路径网络</span>
      </div>
      
      <div style={{ flex: 1, position: 'relative' }}>
        <svg viewBox="0 0 400 240" style={{ width: '100%', height: '100%' }}>
          <defs>
            <linearGradient id="flyline-blue" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#1890ff" stopOpacity="0" />
              <stop offset="50%" stopColor="#1890ff" stopOpacity="0.6" />
              <stop offset="100%" stopColor="#1890ff" stopOpacity="0" />
            </linearGradient>
          </defs>
          
          {/* 绘制边 */}
          {edges.map((edge, i) => {
            const from = nodes.find(n => n.id === edge.from);
            const to = nodes.find(n => n.id === edge.to);
            if (!from || !to) return null;
            
            return (
              <g key={i}>
                <line
                  x1={from.x} y1={from.y}
                  x2={to.x} y2={to.y}
                  stroke="#e8e8e8"
                  strokeWidth="1"
                />
                <line
                  x1={from.x} y1={from.y}
                  x2={to.x} y2={to.y}
                  stroke="url(#flyline-blue)"
                  strokeWidth="2"
                  strokeDasharray="10 50"
                >
                  <animate
                    attributeName="stroke-dashoffset"
                    from="60"
                    to="-10"
                    dur={`${2 + i * 0.5}s`}
                    repeatCount="indefinite"
                  />
                </line>
              </g>
            );
          })}
          
          {/* 绘制节点 */}
          {nodes.map(node => (
            <g key={node.id}>
              <circle
                cx={node.x}
                cy={node.y}
                r={node.size}
                fill="#1890ff"
                opacity="0.15"
              />
              <circle
                cx={node.x}
                cy={node.y}
                r={node.size * 0.4}
                fill="#1890ff"
              />
              <text
                x={node.x}
                y={node.y + node.size + 14}
                textAnchor="middle"
                fill="#666"
                fontSize="10"
              >
                {node.name}
              </text>
            </g>
          ))}
        </svg>
      </div>
    </div>
  );
};
```

---

## 四、后端升级（不变）

后端升级方案与 v2 一致，包括：
- Transformers 情感分析
- 实体识别 (NER)
- 7维情绪识别
- 多维度预警评分

详见 `Integration_Plan_v2.md` 第 5 节。

---

## 五、实施计划

| 阶段 | 任务 | 时间 |
|------|------|------|
| **Phase 1** | 后端 NLP 模块 | 2-3天 |
| **Phase 2** | 大屏基础架构 | 1-2天 |
| | - useScreenAdapt Hook | 0.5天 |
| | - MonitorLayout 组件 | 0.5天 |
| | - ECharts 白色主题 | 0.5天 |
| | - BaseChart 封装 | 0.5天 |
| **Phase 3** | 大屏组件开发 | 2-3天 |
| | - MonitorHeader | 0.5天 |
| | - StatsRow（大数字） | 0.5天 |
| | - ChartPanel | 0.5天 |
| | - TopicRanking | 0.5天 |
| | - PropagationNetwork | 1天 |
| | - 其他图表组件 | 1天 |
| **Phase 4** | Monitor 页面整合 | 1-2天 |
| **Phase 5** | 测试调优 | 1天 |

---

## 六、预期效果

### 6.1 1920x1080 效果

```
┌────────────────────────────────────────────────────────────────────┐
│ 公众情绪智能分析监控中心                              15:30:00 ■   │
├──────────┬──────────┬──────────┬──────────┬──────────┬─────────────┤
│  1,234   │  86.0%   │   6.5%   │   12     │   45     │    [86%]    │
│  总采集   │  正面    │  负面    │  预警    │  话题    │  情感健康度  │
│  ↑12%    │  ↑2.3%   │  ↓1.1%   │  持平    │  ↑5      │             │
├──────────┴──────────┴──────────┴──────────┴──────────┴─────────────┤
│                                                                    │
│  ┌────────────────────────────┐  ┌──────────────────────────┐     │
│  │  情感趋势 (24h)             │  │  平台分布                 │     │
│  │                            │  │                          │     │
│  │      ˜˜˜˜˜˜˜˜˜˜˜˜˜˜˜       │  │        ┌───┐             │     │
│  │    ˜˜˜˜˜˜˜˜˜˜˜˜˜˜˜˜˜˜      │  │       /     \  微博 35%  │     │
│  │  ˜˜˜˜˜˜˜˜˜˜˜˜˜˜˜˜˜˜˜˜˜    │  │      │  45%  │ 抖音 28% │     │
│  │                            │  │       \     /  其他...  │     │
│  └────────────────────────────┘  └──────────────────────────┘     │
│                                                                    │
│  ┌────────────────────────────┐  ┌──────────────────────────┐     │
│  │  热榜 TOP10                 │  │  传播路径网络             │     │
│  │  ┌──────────────────────┐  │  │                          │     │
│  │  │1 法国vs摩洛哥  4959万 │  │  │      ○──→──○           │     │
│  │  │2 福建晋江起火  4782万 │  │  │     / \    /            │     │
│  │  │3 台风巴威...   4500万 │  │  │    ○   ○──○            │     │
│  │  │ ...                  │  │  │                          │     │
│  │  └──────────────────────┘  │  └──────────────────────────┘     │
│  └────────────────────────────┘                                    │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘

白色背景 #f5f7fa
卡片白色 #fff + 浅阴影
大数字 40px 蓝色/绿色/红色
图表区域大，边距紧凑
一屏展示，信息密度高
```

### 6.2 与现有页面对比

| 维度 | 现有页面 (Dashboard) | 新增页面 (Monitor) |
|------|---------------------|-------------------|
| 背景 | 白色 #f0f2f5 | 浅灰 #f5f7fa |
| 信息密度 | 低，大量留白 | 高，紧凑布局 |
| 数字大小 | 24px | 40px |
| 图表高度 | 200px | 280px |
| 展示方式 | 需要滚动 | 一屏全览 |
| 刷新机制 | 手动 | 自动 30s |
| 适用场景 | 后台管理 | 监控大屏 |

---

## 七、总结

| 维度 | 决策 |
|------|------|
| **背景色** | 浅灰白 #f5f7fa（比纯灰更干净） |
| **卡片** | 纯白 #fff + 浅阴影 |
| **数字** | 40px+，等宽字体，带颜色 |
| **布局** | 1920x1080 基准，scale 缩放适配 |
| **密度** | 高，一屏展示所有核心信息 |
| **风格** | 白色大屏，非深色科技 |
| **动画** | 飞线流动、数字刷新，克制使用 |

**核心原则**: 白色背景 + 大屏信息密度 + 监控感。

---

*版本: v2.1*
*更新: 2026-07-10 16:00 CST*
