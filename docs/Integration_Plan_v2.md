# 舆情系统整合升级方案（保留现有设计风格）

> 版本: v2.0
> 日期: 2026-07-10
> 核心原则: **保留现有白色 Ant Design 设计风格，只学习参考项目的架构、算法、工程化能力**

---

## 一、现有设计体系确认

### 1.1 当前视觉风格

| 维度 | 当前值 | 保留策略 |
|------|--------|----------|
| 背景色 | `#f0f2f5` 浅灰白 | ✅ 保留 |
| 卡片背景 | `#ffffff` 纯白 | ✅ 保留 |
| 主色 | `#1890ff` AntD蓝 | ✅ 保留 |
| 成功色 | `#52c41a` AntD绿 | ✅ 保留 |
| 警告色 | `#faad14` AntD黄 | ✅ 保留 |
| 错误色 | `#f5222d` AntD红 | ✅ 保留 |
| 文字主色 | `#333333` | ✅ 保留 |
| 圆角 | `2px-8px` | ✅ 保留 |
| 阴影 | `0 2px 8px rgba(0,0,0,0.09)` | ✅ 保留 |
| 字体 | `-apple-system, "Segoe UI", "PingFang SC"` | ✅ 保留 |

### 1.2 现有页面结构

```
┌──────────────────────────────────────────────┐
│  [Navbar] 总览 | 热榜数据 | 情感分析 | 统计   │  ← Ant Design Menu
├──────────────────────────────────────────────┤
│                                              │
│  ┌──────────────┐  ┌──────────────┐         │
│  │  统计卡片     │  │  统计卡片     │         │  ← AntD Card + Statistic
│  │  [数字]      │  │  [数字]      │         │
│  └──────────────┘  └──────────────┘         │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │  数据表格 / ECharts 图表               │   │  ← AntD Table / ECharts
│  │  ...                                 │   │
│  └──────────────────────────────────────┘   │
│                                              │
└──────────────────────────────────────────────┘
```

---

## 二、参考项目价值重定位

### 2.1 sentiment_monitor → 算法与架构

**学什么**：
- ✅ Transformers 情感分析 Pipeline
- ✅ 实体识别 (NER) 模块
- ✅ 多维度预警评分算法
- ✅ 7维情绪识别
- ✅ 配置驱动架构模式

**不学什么**：
- ❌ 它的暗色可视化界面
- ❌ 它的前端技术栈（如果是 Flask/Jinja）

### 2.2 big-screen-vue-datav → 工程化模式

**学什么**：
- ✅ ECharts 组件封装模式（数据层与渲染层分离）
- ✅ Scale 自适应方案（1920x1080 基准适配）
- ✅ 数据自动刷新机制（统一 Mixin/Hooks）
- ✅ 主题配置系统（改造为白色主题）
- ✅ 组件目录组织方式

**不学什么**：
- ❌ 暗色主题配色
- ❌ 科技感边框装饰
- ❌ 扫描线动画

### 2.3 DataV → 特殊图表类型

**学什么**：
- ✅ 飞线图 SVG 动画原理（改造为白色风格）
- ✅ 水位图实现方式（改造为蓝色系）
- ✅ 轮播表滚动机制
- ✅ 排名板动画效果

**不学什么**：
- ❌ 深色背景
- ❌ 发光边框
- ❌ 霓虹配色

### 2.4 iDataV → 高级图表组合

**学什么**：
- ✅ ECharts Graph（关系图谱）配置
- ✅ ECharts Sunburst（旭日图）配置
- ✅ ECharts Map（地图热力）配置
- ✅ 词云图配置
- ✅ 图表组合布局思路

**不学什么**：
- ❌ 暗色主题配置
- ❌ 3D 效果（非必需）

---

## 三、升级方案设计

### 3.1 整体架构

```
sentiment-analysis/frontend/src/
├── pages/                          ← 现有页面（不变）
│   ├── Dashboard.tsx               ← 现有总览
│   ├── Topics.tsx                  ← 现有热榜
│   ├── Sentiment.tsx               ← 现有情感分析
│   ├── Stats.tsx                   ← 现有统计
│   └── Monitor.tsx                 ← 【新增】监控面板（白色风格）
│
├── components/
│   ├── Navbar.tsx                  ← 现有（仅加菜单项）
│   ├── common/                     ← 【新增】通用组件库
│   │   ├── ChartCard.tsx           ← 图表卡片（AntD Card 封装）
│   │   ├── StatCard.tsx            ← 统计卡片（AntD Statistic 封装）
│   │   ├── RankingList.tsx         ← 排名列表（轮播/静态）
│   │   └── RefreshBadge.tsx        ← 自动刷新状态标识
│   │
│   ├── charts/                     ← 【新增】ECharts 封装组件
│   │   ├── BaseChart.tsx           ← 基础图表封装
│   │   ├── PieChart.tsx            ← 饼图封装
│   │   ├── LineChart.tsx           ← 折线图封装
│   │   ├── BarChart.tsx            ← 柱状图封装
│   │   ├── GraphChart.tsx          ← 关系图谱（新增）
│   │   ├── SunburstChart.tsx       ← 旭日图（新增）
│   │   ├── WordCloudChart.tsx      ← 词云图（新增）
│   │   └── MapChart.tsx            ← 地图热力（新增）
│   │
│   └── visual/                     ← 【新增】特殊可视化组件
│       ├── FlylineMap.tsx          ← 传播路径飞线图（白色风格）
│       ├── LiquidGauge.tsx         ← 水位仪表盘（蓝色系）
│       └── ScrollTable.tsx         ← 滚动表格（轮播效果）
│
├── hooks/                          ← 【新增】复用 Hooks
│   ├── useAutoRefresh.ts           ← 自动数据刷新
│   ├── useScreenScale.ts           ← 大屏自适应
│   └── useChartTheme.ts            ← ECharts 主题配置
│
├── theme/                          ← 【新增】主题配置
│   └── index.ts                    ← 白色主题 + ECharts 主题
│
└── services/
    └── api.ts                      ← 现有（复用）
```

### 3.2 路由设计

```typescript
// App.tsx（仅新增一行）
<Route path="/" element={<Dashboard />} />
<Route path="/topics" element={<Topics />} />
<Route path="/sentiment" element={<Sentiment />} />
<Route path="/stats" element={<Stats />} />
<Route path="/monitor" element={<Monitor />} />  {/* 新增 */}
```

### 3.3 新增页面：Monitor（监控面板）

```
Monitor.tsx 布局（白色 AntD 风格）:

┌────────────────────────────────────────────────────────────────────┐
│  [Navbar] ... | 监控面板                                           │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐     │
│  │ 总采集   │ │ 正面情感 │ │ 负面情感 │ │ 预警数量 │ │ 活跃话题 │     │
│  │ 1,234   │ │  86.0%  │ │  6.5%   │ │   12    │ │   45    │     │
│  │ ↑ 12%   │ │ ↑ 2.3%  │ │ ↓ 1.1%  │ │  持平   │ │ ↑ 5    │     │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘     │
│                                                                    │
│  ┌──────────────────────┐  ┌──────────────────────┐               │
│  │                      │  │                      │               │
│  │   情感趋势折线图      │  │   平台分布饼图        │               │
│  │   (ECharts Line)     │  │   (ECharts Pie)      │               │
│  │                      │  │                      │               │
│  └──────────────────────┘  └──────────────────────┘               │
│                                                                    │
│  ┌──────────────────────┐  ┌──────────────────────┐               │
│  │                      │  │                      │               │
│  │   热榜排名轮播        │  │   传播路径飞线图      │               │
│  │   (ScrollTable)      │  │   (FlylineMap)       │               │
│  │                      │  │   白色底 + 蓝色线     │               │
│  └──────────────────────┘  └──────────────────────┘               │
│                                                                    │
│  ┌──────────────────────┐  ┌──────────────────────┐               │
│  │                      │  │                      │               │
│  │   话题关系图谱        │  │   地域分布地图        │               │
│  │   (GraphChart)       │  │   (MapChart)         │               │
│  │                      │  │                      │               │
│  └──────────────────────┘  └──────────────────────┘               │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

**设计要点**：
- 所有卡片使用 AntD Card 组件，白色背景
- 图表使用 ECharts，配置为白色主题
- 飞线图改为白色底 + 蓝色线（而非深色底 + 霓虹线）
- 数字使用 AntD Statistic，带趋势箭头
- 自动刷新显示在右上角（AntD Badge）

---

## 四、组件详细设计

### 4.1 ChartCard（图表卡片）

```typescript
// components/common/ChartCard.tsx
import React from 'react';
import { Card } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';

interface ChartCardProps {
  title: string;
  children: React.ReactNode;
  loading?: boolean;
  extra?: React.ReactNode;
  onRefresh?: () => void;
}

export const ChartCard: React.FC<ChartCardProps> = ({
  title,
  children,
  loading = false,
  extra,
  onRefresh,
}) => {
  return (
    <Card
      title={title}
      loading={loading}
      extra={
        <>
          {extra}
          {onRefresh && (
            <ReloadOutlined
              onClick={onRefresh}
              style={{ marginLeft: 8, cursor: 'pointer' }}
            />
          )}
        </>
      }
      style={{ height: '100%' }}
      bodyStyle={{ padding: '12px 24px' }}
    >
      {children}
    </Card>
  );
};
```

### 4.2 BaseChart（ECharts 封装）

```typescript
// components/charts/BaseChart.tsx
import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { whiteTheme } from '@/theme';

interface BaseChartProps {
  id: string;
  options: echarts.EChartsOption;
  height?: string;
  onClick?: (params: any) => void;
}

export const BaseChart: React.FC<BaseChartProps> = ({
  id,
  options,
  height = '300px',
  onClick,
}) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  
  useEffect(() => {
    if (chartRef.current) {
      // 注册白色主题
      echarts.registerTheme('white', whiteTheme);
      chartInstance.current = echarts.init(chartRef.current, 'white');
      
      if (onClick) {
        chartInstance.current.on('click', onClick);
      }
      
      // 响应式
      const resize = () => chartInstance.current?.resize();
      window.addEventListener('resize', resize);
      
      return () => {
        window.removeEventListener('resize', resize);
        chartInstance.current?.dispose();
      };
    }
  }, []);
  
  useEffect(() => {
    chartInstance.current?.setOption(options, true);
  }, [options]);
  
  return <div ref={chartRef} id={id} style={{ width: '100%', height }} />;
};
```

### 4.3 ECharts 白色主题配置

```typescript
// theme/index.ts
export const whiteTheme = {
  // 调色盘（AntD 色系）
  color: [
    '#1890ff', '#52c41a', '#faad14', '#f5222d',
    '#722ed1', '#13c2c2', '#eb2f96', '#fadb14'
  ],
  
  backgroundColor: 'transparent',
  
  textStyle: {
    color: '#333333',
    fontFamily: '-apple-system, "Segoe UI", "PingFang SC", sans-serif',
  },
  
  title: {
    textStyle: { color: '#333333', fontSize: 16, fontWeight: 'bold' },
    subtextStyle: { color: '#666666' },
  },
  
  legend: {
    textStyle: { color: '#666666' },
  },
  
  tooltip: {
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    borderColor: '#e8e8e8',
    borderWidth: 1,
    textStyle: { color: '#333333' },
    extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.15); border-radius: 4px;',
  },
  
  categoryAxis: {
    axisLine: { lineStyle: { color: '#d9d9d9' } },
    axisTick: { lineStyle: { color: '#d9d9d9' } },
    axisLabel: { color: '#666666' },
    splitLine: { lineStyle: { color: '#f0f0f0' } },
  },
  
  valueAxis: {
    axisLine: { lineStyle: { color: '#d9d9d9' } },
    axisTick: { lineStyle: { color: '#d9d9d9' } },
    axisLabel: { color: '#666666' },
    splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
  },
  
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    containLabel: true,
  },
};
```

### 4.4 飞线图（白色风格改造）

```typescript
// components/visual/FlylineMap.tsx
import React from 'react';

interface Node {
  id: string;
  name: string;
  x: number;
  y: number;
}

interface Edge {
  from: string;
  to: string;
  value: number;
}

interface Props {
  nodes: Node[];
  edges: Edge[];
  width?: number;
  height?: number;
}

export const FlylineMap: React.FC<Props> = ({
  nodes,
  edges,
  width = 600,
  height = 400,
}) => {
  return (
    <div style={{ width, height, background: '#fafafa', borderRadius: 4 }}>
      <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: '100%' }}>
        <defs>
          {/* 蓝色渐变 */}
          <linearGradient id="blue-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#1890ff" stopOpacity="0" />
            <stop offset="50%" stopColor="#1890ff" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#1890ff" stopOpacity="0" />
          </linearGradient>
          
          {/* 节点光晕 */}
          <filter id="node-glow">
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        
        {/* 绘制节点 */}
        {nodes.map(node => (
          <g key={node.id}>
            <circle
              cx={node.x}
              cy={node.y}
              r={8}
              fill="#1890ff"
              opacity="0.8"
              filter="url(#node-glow)"
            />
            <text
              x={node.x}
              y={node.y + 20}
              textAnchor="middle"
              fill="#333"
              fontSize="12"
            >
              {node.name}
            </text>
          </g>
        ))}
        
        {/* 绘制飞线 */}
        {edges.map((edge, i) => {
          const from = nodes.find(n => n.id === edge.from);
          const to = nodes.find(n => n.id === edge.to);
          if (!from || !to) return null;
          
          return (
            <g key={i}>
              {/* 基础线 */}
              <line
                x1={from.x}
                y1={from.y}
                x2={to.x}
                y2={to.y}
                stroke="#d9d9d9"
                strokeWidth="1"
              />
              {/* 动画飞线 - 蓝色 */}
              <line
                x1={from.x}
                y1={from.y}
                x2={to.x}
                y2={to.y}
                stroke="url(#blue-gradient)"
                strokeWidth="2"
                strokeDasharray="15 100"
              >
                <animate
                  attributeName="stroke-dashoffset"
                  from="115"
                  to="-15"
                  dur="2s"
                  repeatCount="indefinite"
                />
              </line>
            </g>
          );
        })}
      </svg>
    </div>
  );
};
```

### 4.5 水位仪表盘（蓝色系改造）

```typescript
// components/visual/LiquidGauge.tsx
import React from 'react';

interface Props {
  value: number;  // 0-100
  title: string;
}

export const LiquidGauge: React.FC<Props> = ({ value, title }) => {
  const waveHeight = 200 - (value / 100) * 160;
  
  return (
    <div style={{ textAlign: 'center' }}>
      <svg viewBox="0 0 200 200" style={{ width: 150, height: 150 }}>
        <defs>
          <clipPath id="wave-clip">
            <rect x="20" y={waveHeight} width="160" height={180 - waveHeight} />
          </clipPath>
          
          <linearGradient id="water-blue" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#69c0ff" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#1890ff" stopOpacity="0.4" />
          </linearGradient>
        </defs>
        
        {/* 外圆 */}
        <circle cx="100" cy="100" r="80" fill="none" stroke="#d9d9d9" strokeWidth="3" />
        
        {/* 水位 */}
        <circle cx="100" cy="100" r="76" fill="url(#water-blue)" clipPath="url(#wave-clip)">
          <animateTransform
            attributeName="transform"
            type="translate"
            values="-3,0; 3,0; -3,0"
            dur="3s"
            repeatCount="indefinite"
          />
        </circle>
        
        {/* 数值 */}
        <text x="100" y="95" textAnchor="middle" fill="#1890ff" fontSize="28" fontWeight="bold">
          {value}%
        </text>
        <text x="100" y="115" textAnchor="middle" fill="#666" fontSize="11">
          {title}
        </text>
      </svg>
    </div>
  );
};
```

### 4.6 滚动表格（轮播效果）

```typescript
// components/common/RankingList.tsx
import React, { useState, useEffect } from 'react';
import { Tag } from 'antd';
import { FireOutlined } from '@ant-design/icons';

interface RankingItem {
  id: string;
  rank: number;
  title: string;
  heat: number;
  platform: string;
  sentiment: 'positive' | 'neutral' | 'negative';
}

interface Props {
  data: RankingItem[];
  visibleCount?: number;
  scrollInterval?: number;
}

export const RankingList: React.FC<Props> = ({
  data,
  visibleCount = 8,
  scrollInterval = 3000,
}) => {
  const [startIndex, setStartIndex] = useState(0);
  
  useEffect(() => {
    if (data.length <= visibleCount) return;
    
    const timer = setInterval(() => {
      setStartIndex(prev => (prev + 1) % (data.length - visibleCount + 1));
    }, scrollInterval);
    
    return () => clearInterval(timer);
  }, [data.length, visibleCount, scrollInterval]);
  
  const visibleData = data.slice(startIndex, startIndex + visibleCount);
  
  const sentimentColors = {
    positive: 'success',
    neutral: 'default',
    negative: 'error',
  };
  
  return (
    <div className="ranking-list">
      <div className="ranking-header" style={{ display: 'flex', padding: '8px 0', borderBottom: '1px solid #f0f0f0', color: '#999', fontSize: 12 }}>
        <span style={{ width: 40 }}>排名</span>
        <span style={{ flex: 1 }}>话题</span>
        <span style={{ width: 80 }}>平台</span>
        <span style={{ width: 80 }}>情感</span>
        <span style={{ width: 100, textAlign: 'right' }}>热度</span>
      </div>
      
      {visibleData.map((item, index) => (
        <div
          key={item.id}
          className="ranking-item"
          style={{
            display: 'flex',
            alignItems: 'center',
            padding: '10px 0',
            borderBottom: '1px solid #f5f5f5',
            transition: 'all 0.3s ease',
          }}
        >
          <span style={{ width: 40, fontWeight: 'bold', color: index + startIndex < 3 ? '#1890ff' : '#999' }}>
            {item.rank}
          </span>
          
          <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {item.title}
          </span>
          
          <span style={{ width: 80, fontSize: 12, color: '#666' }}>
            {item.platform}
          </span>
          
          <span style={{ width: 80 }}>
            <Tag color={sentimentColors[item.sentiment]} style={{ fontSize: 11 }}>
              {item.sentiment === 'positive' ? '正面' : item.sentiment === 'negative' ? '负面' : '中性'}
            </Tag>
          </span>
          
          <span style={{ width: 100, textAlign: 'right', color: '#ff4d4f', fontSize: 13 }}>
            <FireOutlined style={{ marginRight: 4 }} />
            {(item.heat / 10000).toFixed(1)}w
          </span>
        </div>
      ))}
    </div>
  );
};
```

---

## 五、后端升级方案

### 5.1 NLP Pipeline 增强（完全保留现有 API 风格）

```python
# app/ml/sentiment_transformers.py
"""
Transformers 情感分析模块

完全独立模块，不影响现有情感分析逻辑
新增 API: /api/v1/sentiment/v2/analyze
"""

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from typing import Dict, List
import asyncio

class TransformersSentimentAnalyzer:
    """
    基于 Transformers 的情感分析器
    
    特点:
    - 懒加载: 首次调用时才加载模型
    - 异步推理: 不阻塞主线程
    - 批处理: 减少推理开销
    """
    
    _instance = None
    _model = None
    _tokenizer = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def _load_model(self):
        """懒加载模型"""
        if self._model is None:
            model_name = "uer/roberta-base-finetuned-jd-binary-chinese"
            self._tokenizer = AutoTokenizer.from_pretrained(model_name)
            self._model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self._model.eval()
    
    def analyze(self, text: str) -> Dict:
        """分析单条文本"""
        self._load_model()
        
        inputs = self._tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        
        with torch.no_grad():
            outputs = self._model(**inputs)
            probabilities = torch.softmax(outputs.logits, dim=1)
        
        pos_prob = probabilities[0][1].item()
        neg_prob = probabilities[0][0].item()
        
        return {
            "sentiment": "positive" if pos_prob > 0.5 else "negative",
            "positive_score": round(pos_prob, 4),
            "negative_score": round(neg_prob, 4),
            "confidence": round(max(pos_prob, neg_prob), 4),
        }
    
    def analyze_batch(self, texts: List[str]) -> List[Dict]:
        """批量分析"""
        return [self.analyze(t) for t in texts]
    
    async def analyze_async(self, text: str) -> Dict:
        """异步分析"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.analyze, text)


# API 端点（新增，不影响现有）
from fastapi import APIRouter
from app.ml.sentiment_transformers import TransformersSentimentAnalyzer

router = APIRouter()
analyzer = TransformersSentimentAnalyzer()

@router.post("/v2/analyze", tags=["情感分析"])
async def analyze_v2(text: str):
    """
    Transformers 情感分析（增强版）
    
    对比现有 /analyze:
    - 现有: 基于规则/词典，速度快
    - 本接口: 基于 BERT，准确率高
    """
    result = await analyzer.analyze_async(text)
    return {
        "code": 200,
        "data": result,
        "message": "success",
    }
```

### 5.2 新增 API 端点清单

| 端点 | 方法 | 功能 | 状态 |
|------|------|------|------|
| `/api/v1/sentiment/v2/analyze` | POST | Transformers 情感分析 | 🆕 新增 |
| `/api/v1/sentiment/v2/batch` | POST | 批量情感分析 | 🆕 新增 |
| `/api/v1/sentiment/ner` | POST | 实体识别 | 🆕 新增 |
| `/api/v1/sentiment/emotions` | POST | 7维情绪识别 | 🆕 新增 |
| `/api/v1/alerts/v2/classify` | POST | 多维度预警评分 | 🆕 新增 |
| `/api/v1/monitor/overview` | GET | 监控面板汇总数据 | 🆕 新增 |

---

## 六、实施计划

### 6.1 任务清单

| 阶段 | 任务 | 时间 | 优先级 |
|------|------|------|--------|
| **Phase 1** | 后端 NLP 模块 | 2-3天 | P0 |
| 1.1 | Transformers 情感分析 | 1天 | P0 |
| 1.2 | 实体识别 (NER) | 0.5天 | P0 |
| 1.3 | 情绪识别 | 0.5天 | P0 |
| 1.4 | 预警升级 | 1天 | P0 |
| **Phase 2** | 前端基础组件 | 2天 | P0 |
| 2.1 | ECharts 白色主题 | 0.5天 | P0 |
| 2.2 | BaseChart 封装 | 0.5天 | P0 |
| 2.3 | ChartCard / StatCard | 0.5天 | P0 |
| 2.4 | useAutoRefresh Hook | 0.5天 | P0 |
| **Phase 3** | 特殊可视化组件 | 2-3天 | P1 |
| 3.1 | 飞线图（白色风格） | 1天 | P1 |
| 3.2 | 水位仪表盘 | 0.5天 | P1 |
| 3.3 | 滚动排名列表 | 0.5天 | P1 |
| 3.4 | 关系图谱 | 0.5天 | P1 |
| 3.5 | 旭日图 | 0.5天 | P1 |
| **Phase 4** | 监控面板页面 | 2天 | P1 |
| 4.1 | Monitor.tsx 布局 | 1天 | P1 |
| 4.2 | 数据对接 | 0.5天 | P1 |
| 4.3 | 自适应/响应式 | 0.5天 | P1 |
| **Phase 5** | 测试与调优 | 1-2天 | P2 |
| 5.1 | 功能测试 | 1天 | P2 |
| 5.2 | 性能调优 | 0.5天 | P2 |
| 5.3 | 兼容性测试 | 0.5天 | P2 |

### 6.2 关键决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 新增页面路由 | `/monitor` | 与现有风格一致，命名直观 |
| 图表库 | ECharts（已有） | 无需新增依赖 |
| 飞线图实现 | SVG 原生 | 轻量，白色风格易改造 |
| 数据刷新 | 30秒轮询 | 平衡实时性与性能 |
| 模型加载 | 懒加载 | 避免启动时内存峰值 |
| 主题方案 | ECharts 白色主题配置 | 与 AntD 风格统一 |

---

## 七、风险与缓解

| 风险 | 等级 | 缓解方案 |
|------|------|----------|
| Transformers 模型加载内存不足 | 🟡 | 懒加载 + 内存监控 |
| 推理延迟导致 API 超时 | 🟡 | 异步线程池 |
| 前端包体积增大 | 🟢 | 无新增大型依赖 |
| SVG 动画性能问题 | 🟢 | 节点数控制 < 50 |
| 现有页面样式冲突 | 🟢 | 独立组件，CSS 隔离 |

---

## 八、预期效果

### 8.1 新增 Monitor 页面预览

```
访问 /monitor 将看到：

┌─────────────────────────────────────────────────────────────┐
│  [Navbar] 总览 | 热榜 | 情感分析 | 统计 | 监控面板          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐   │
│  │  采集  │ │ 正面   │ │ 负面   │ │ 预警   │ │ 话题   │   │
│  │ 1,234  │ │ 86.0%  │ │  6.5%  │ │  12   │ │  45   │   │
│  │ ↑ 12%  │ │ ↑ 2.3% │ │ ↓ 1.1% │ │ 持平  │ │ ↑ 5   │   │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘   │
│                                                             │
│  ┌────────────────────┐  ┌────────────────────┐            │
│  │   情感趋势          │  │   平台分布          │            │
│  │   [ECharts Line]   │  │   [ECharts Pie]    │            │
│  │                    │  │                    │            │
│  └────────────────────┘  └────────────────────┘            │
│                                                             │
│  ┌────────────────────┐  ┌────────────────────┐            │
│  │   热榜排名          │  │   传播路径          │            │
│  │   [滚动列表]        │  │   [SVG 飞线图]      │            │
│  │                    │  │   白色底+蓝色线     │            │
│  └────────────────────┘  └────────────────────┘            │
│                                                             │
│  ┌────────────────────┐  ┌────────────────────┐            │
│  │   话题关系图谱      │  │   地域分布          │            │
│  │   [ECharts Graph]  │  │   [ECharts Map]    │            │
│  │                    │  │                    │            │
│  └────────────────────┘  └────────────────────┘            │
│                                                             │
└─────────────────────────────────────────────────────────────┘

风格：白色背景、Ant Design Card、蓝色系图表、圆角阴影
与现有页面完全一致的设计语言
```

### 8.2 算法能力提升

| 能力 | 升级前 | 升级后 |
|------|--------|--------|
| 情感分析 | 规则匹配 | Transformers BERT |
| 实体识别 | ❌ 无 | ✅ 人名/地名/机构 |
| 预警评分 | 阈值触发 | 多维度评分 |
| 情绪维度 | 3维 | 7维 |

---

## 九、总结

| 维度 | 决策 |
|------|------|
| **设计风格** | ✅ 完全保留现有白色 Ant Design 风格 |
| **新增内容** | Monitor 监控面板 + 后端 NLP 算法升级 |
| **参考项目** | 学架构/算法/工程化，不学暗色主题 |
| **影响范围** | 纯增量，现有页面零改动 |
| **实施周期** | 预估 7-10 天 |
| **风险等级** | 🟢 低 |

**核心原则**: 让系统能力变强，但看起来还是原来的样子。

---

*方案版本: v2.0*
*更新日期: 2026-07-10 16:00 CST*
*设计风格: 保留现有白色 Ant Design 体系*
