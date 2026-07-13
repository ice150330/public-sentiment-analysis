# 舆情可视化大屏深度整合报告

> 报告日期: 2026-07-10
> 方向: 预选修改（非侵入式增量开发）
> 核心原则: **零影响现有逻辑，路由独立，纯增量**

---

## 一、现有系统架构快照

### 1.1 前端现状

| 维度 | 现状 |
|------|------|
| 框架 | React 18 + TypeScript |
| UI 库 | Ant Design |
| 路由 | react-router-dom (BrowserRouter) |
| 图表 | 当前无专用图表库（页面以表格/卡片为主） |
| 现有页面 | `/` Dashboard, `/topics` 热榜, `/analysis` 情感分析, `/management` 统计 |
| 导航 | 顶部 Navbar 水平菜单 |

### 1.2 后端现状

| 维度 | 现状 |
|------|------|
| 框架 | FastAPI |
| 数据库 | SQLite (SQLAlchemy ORM) |
| 已有端点 | `/api/v1/topics`, `/api/v1/sentiment`, `/api/v1/stats`, `/api/v1/alerts` 等 12 组路由 |
| 数据结构 | HotTopic, SentimentRecord, AlertEvent, DataQuality, TopicCluster 等 18 个模型 |

### 1.3 核心约束（不可违反）

1. **不修改现有页面代码**: Dashboard.tsx / Topics.tsx / Sentiment.tsx / Stats.tsx 保持原样
2. **不修改现有路由**: `/`, `/topics`, `/analysis`, `/management` 行为不变
3. **不修改后端逻辑**: 不新增数据库模型，不修改现有 API
4. **导航不冲突**: 新增入口需自然融入现有 Navbar

---

## 二、参考项目核心模式提取

### 2.1 sentiment_monitor — 舆情系统架构参考

**核心结构**:
```
sentiment_monitor/
├── data_collection/      ← 数据采集（我们已有 crawler_service）
├── text_analysis/        ← 文本分析（我们已有 sentiment_service）
├── video_analysis/       ← 视频分析（可预留扩展位）
├── case_labeling/        ← 负面案例标注（我们已有 alert_engine）
├── visualization/        ← 数据可视化 ← **重点借鉴**
├── alert/                ← 预警通知（我们已有 notification_service）
├── api/                  ← API 层（我们已有 FastAPI 路由）
├── frontend/             ← 前端界面 ← **重点借鉴**
```

**可借鉴模式**:
- **模块化分离**: 采集/分析/可视化/预警完全解耦
- **负面等级分类**: `NEGATIVE_LEVELS = ["轻微", "一般", "严重", "紧急"]`
- **实时监控面板**: WebSocket 推送 + 轮询兜底
- **视频分析预留**: 可作为 P2 扩展点

### 2.2 big-screen-vue-datav — 大屏工程化方案

**核心模式**:

#### A. 屏幕自适应方案 (Scale 方案)
```javascript
// src/utils/useDraw.js 核心逻辑
function useDraw() {
  const appRef = ref(null);
  const calcRate = () => {
    const baseWidth = 1920;
    const baseHeight = 1080;
    const dom = appRef.value;
    const currentWidth = document.body.clientWidth;
    const currentHeight = document.body.clientHeight;
    dom.style.transform = `scale(${currentWidth/baseWidth}, ${currentHeight/baseHeight})`;
    dom.style.transformOrigin = '0 0';
  };
  // 监听 resize + 防抖
  window.addEventListener('resize', debounce(calcRate, 200));
}
```

**适配 React 改造**:
```typescript
// hooks/useScreenScale.ts
import { useEffect, useRef } from 'react';

const BASE_WIDTH = 1920;
const BASE_HEIGHT = 1080;

export function useScreenScale() {
  const containerRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    const calcRate = () => {
      if (!containerRef.current) return;
      const w = window.innerWidth;
      const h = window.innerHeight;
      const scaleX = w / BASE_WIDTH;
      const scaleY = h / BASE_HEIGHT;
      // 等比例缩放，取较小值防止内容溢出
      const scale = Math.min(scaleX, scaleY);
      containerRef.current.style.transform = `scale(${scale})`;
      containerRef.current.style.transformOrigin = 'top center';
    };
    calcRate();
    window.addEventListener('resize', calcRate);
    return () => window.removeEventListener('resize', calcRate);
  }, []);
  
  return containerRef;
}
```

#### B. ECharts 组件封装模式
```vue
<!-- Vue 原版: common/echart/index.vue -->
<template>
  <div :id="id" :style="{ height, width }" />
</template>
<script>
export default {
  props: ['id', 'width', 'height', 'options'],
  watch: {
    options: {
      handler(options) { this.chart.setOption(options, true) },
      deep: true
    }
  },
  mounted() { this.initChart() },
  beforeDestroy() { this.chart.dispose() }
}
</script>
```

**适配 React 改造**:
```typescript
// components/echarts/EChartBase.tsx
import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

interface Props {
  id: string;
  width?: string;
  height?: string;
  options: echarts.EChartsOption;
}

export const EChartBase: React.FC<Props> = ({ id, width = '100%', height = '100%', options }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  
  useEffect(() => {
    if (chartRef.current) {
      chartInstance.current = echarts.init(chartRef.current);
      chartInstance.current.setOption(options, true);
    }
    return () => {
      chartInstance.current?.dispose();
    };
  }, []);
  
  useEffect(() => {
    chartInstance.current?.setOption(options, true);
  }, [options]);
  
  return <div ref={chartRef} id={id} style={{ width, height }} />;
};
```

#### C. 布局结构模式
```
views/index.vue 布局:
┌──────────────────────────────────────────────┐
│ [header] 标题 + 装饰线 + 时间                  │
├──────────┬──────────────┬────────────────────┤
│          │              │                    │
│  left-1  │              │   right-1          │
│  left-2  │    center    │   right-2          │
│          │  (地图/核心)  │                    │
├──────────┴──────────────┴────────────────────┤
│ [bottom] 底部图表区                           │
└──────────────────────────────────────────────┘
```

### 2.3 DataV — 视觉组件库

**可用组件清单**:

| 组件 | 用途 | 迁移成本 |
|------|------|----------|
| `dv-border-box-1~13` | 面板边框装饰 | 中（需移植 SVG） |
| `dv-decoration-1~12` | 标题装饰/动态线 | 中 |
| `dv-loading` | 加载动画 | 低 |
| `dv-scroll-ranking-board` | 排名轮播板 | 低（可用 CSS 实现） |
| `dv-scroll-board` | 表格轮播 | 低 |
| `dv-flyline-chart` | 飞线图（传播路径） | 高 |
| `dv-water-level-pond` | 水位图（情感指数） | 中 |

**迁移策略**: 由于 DataV 是 Vue 组件库，需提取核心 SVG/Canvas 逻辑重写为 React 组件。优先移植边框装饰组件（纯 SVG，无状态逻辑）。

### 2.4 iDataV — 图表组合方案

**可参考案例**:
- **case01**: 上市公司全景概览 → 改造为 "舆情全景概览"
- **case03**: 地图热点 + 飞线 → 改造为 "舆情地域分布"
- **case07**: 词云 + 关系图谱 → 改造为 "话题关联分析"
- **tpl01~05**: 大屏模板布局参考

---

## 三、整合方案设计

### 3.1 整体架构

```
新增模块（纯增量）:
sentiment-analysis/frontend/src/
├── pages/
│   ├── Dashboard.tsx          ← 现有（不变）
│   ├── Topics.tsx             ← 现有（不变）
│   ├── Sentiment.tsx          ← 现有（不变）
│   ├── Stats.tsx              ← 现有（不变）
│   └── BigScreen.tsx          ← 【新增】大屏主页面
├── components/
│   ├── Navbar.tsx             ← 现有（仅加菜单项）
│   ├── DesignSystem.tsx       ← 现有（不变）
│   └── bigscreen/             ← 【新增】大屏专用组件
│       ├── ScreenContainer.tsx    ← scale 自适应容器
│       ├── BorderBox.tsx          ← 边框装饰
│       ├── Header.tsx             ← 大屏顶部标题栏
│       ├── EChartBase.tsx         ← ECharts 封装
│       ├── modules/               ← 各区域模块
│       │   ├── PlatformStats.tsx   ← 平台采集统计
│       │   ├── SentimentPie.tsx    ← 情感分布饼图
│       │   ├── TopicRanking.tsx    ← 热榜排名
│       │   ├── TrendLine.tsx       ← 趋势折线
│       │   ├── AlertList.tsx       ← 预警列表
│       │   └── WordCloud.tsx       ← 词云
│       └── hooks/
│           ├── useScreenScale.ts   ← 自适应 hook
│           └── useAutoRefresh.ts   ← 自动刷新 hook
├── services/
│   └── api.ts                 ← 现有（复用已有接口）
└── App.tsx                    ← 现有（仅加路由）
```

### 3.2 路由设计（非侵入式）

```typescript
// App.tsx 修改（仅新增一行）
<Route path="/bigscreen" element={<BigScreen />} />
```

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | Dashboard | 现有总览（不变） |
| `/topics` | Topics | 现有热榜（不变） |
| `/analysis` | Sentiment | 现有情感分析（不变） |
| `/management` | Stats | 现有统计（不变） |
| **`/bigscreen`** | **BigScreen** | **【新增】大屏展示** |

### 3.3 Navbar 修改（仅加菜单项）

```typescript
// Navbar.tsx 修改（仅新增一个菜单项）
const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '总览' },
  { key: '/topics', icon: <FireOutlined />, label: '热榜数据' },
  { key: '/sentiment', icon: <SmileOutlined />, label: '情感分析' },
  { key: '/stats', icon: <BarChartOutlined />, label: '统计分析' },
  // 【新增】
  { key: '/bigscreen', icon: <MonitorOutlined />, label: '监控大屏' },
];
```

### 3.4 大屏布局设计

```
┌────────────────────────────────────────────────────────────────────┐
│  [Decoration-10]  公众情绪智能分析 · 实时监控大屏  [Decoration-10]  │
│  2026-07-10 14:30:00  星期五                                       │
├──────────────┬──────────────────────────────┬──────────────────────┤
│              │                              │                      │
│  平台分布     │                              │     情感分布         │
│  [环形图]     │                              │     [饼图]           │
│              │                              │                      │
├──────────────┤      热榜 TOP10               ├──────────────────────┤
│              │      [滚动排名板]              │                      │
│  采集趋势     │                              │     预警事件         │
│  [折线图]     │      今日采集: 523 条         │     [轮播列表]       │
│              │      正面: 86%                 │                      │
├──────────────┤      负面: 6.5%               ├──────────────────────┤
│              │      预警: 3 条                │                      │
│  话题聚类     │                              │     模型状态         │
│  [词云]       │      [地图/传播路径占位]       │     [状态卡片]       │
│              │                              │                      │
└──────────────┴──────────────────────────────┴──────────────────────┘
```

### 3.5 数据流设计（复用现有 API）

```
BigScreen.tsx
    ├── useEffect(() => {
    │   fetchDashboardData()     → GET /api/v1/topics?limit=10
    │   fetchSentimentStats()    → GET /api/v1/sentiment/stats
    │   fetchAlertList()         → GET /api/v1/alerts
    │   fetchStatsOverview()     → GET /api/v1/stats/overview
    │ })                        ← 30秒自动刷新
    │
    ├── PlatformStats.tsx        ← 饼图: 各平台数据量
    ├── SentimentPie.tsx         ← 饼图: 正/中/负占比
    ├── TopicRanking.tsx         ← 轮播表: TOP10 热榜
    ├── TrendLine.tsx            ← 折线图: 24h 采集趋势
    ├── AlertList.tsx            ← 列表: 最新预警
    └── WordCloud.tsx            ← 词云: 高频关键词
```

---

## 四、技术选型与依赖

### 4.1 新增依赖

| 依赖 | 版本 | 用途 | 安装命令 |
|------|------|------|----------|
| echarts | ^5.4.3 | 图表渲染 | `npm install echarts` |
| echarts-wordcloud | ^2.1.0 | 词云图 | `npm install echarts-wordcloud` |

### 4.2 现有依赖复用

| 依赖 | 已有版本 | 用途 |
|------|----------|------|
| react | ^18.x | 框架 |
| react-router-dom | ^6.x | 路由 |
| antd | ^5.x | UI 组件（可复用图标） |
| axios | ^1.x | HTTP 请求 |

### 4.3 不引入的依赖（避免冗余）

| 依赖 | 原因 |
|------|------|
| DataV React 版 | 组件过重，仅需要边框装饰可自行实现 |
| D3.js | 学习成本高，ECharts 已覆盖需求 |
| Three.js | 3D 效果非必需，增加包体积 |

---

## 五、组件详细设计

### 5.1 ScreenContainer（自适应容器）

```typescript
// components/bigscreen/ScreenContainer.tsx
import React from 'react';
import { useScreenScale } from './hooks/useScreenScale';

interface Props {
  children: React.ReactNode;
}

export const ScreenContainer: React.FC<Props> = ({ children }) => {
  const containerRef = useScreenScale();
  
  return (
    <div style={{ width: '100vw', height: '100vh', background: '#0a1a2f', overflow: 'hidden' }}>
      <div
        ref={containerRef}
        style={{
          width: 1920,
          height: 1080,
          position: 'relative',
        }}
      >
        {children}
      </div>
    </div>
  );
};
```

### 5.2 BorderBox（边框装饰）

```typescript
// components/bigscreen/BorderBox.tsx
import React from 'react';

interface Props {
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export const BorderBox: React.FC<Props> = ({ title, children, className }) => {
  return (
    <div className={`border-box ${className || ''}`} style={{ position: 'relative', padding: 16 }}>
      {/* SVG 边框 - 简化版 */}
      <svg style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }}>
        <defs>
          <linearGradient id="borderGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#00f2ff" />
            <stop offset="50%" stopColor="#00c6ff" stopOpacity="0" />
            <stop offset="100%" stopColor="#00f2ff" />
          </linearGradient>
        </defs>
        <rect x="1" y="1" width="calc(100%-2px)" height="calc(100%-2px)" 
              fill="none" stroke="url(#borderGradient)" strokeWidth="1" 
              rx="4" />
        {/* 四角装饰 */}
        <path d="M 0 20 L 0 0 L 20 0" stroke="#00f2ff" strokeWidth="2" fill="none" />
        <path d="M calc(100%-20px) 0 L 100% 0 L 100% 20" stroke="#00f2ff" strokeWidth="2" fill="none" />
      </svg>
      {title && (
        <div style={{ color: '#00f2ff', fontSize: 18, fontWeight: 'bold', marginBottom: 12, paddingLeft: 8 }}>
          {title}
        </div>
      )}
      {children}
    </div>
  );
};
```

### 5.3 各模块组件接口

```typescript
// 统一数据接口（复用现有 API 返回格式）
interface PlatformStat {
  name: string;      // 平台名: "微博" | "抖音" | ...
  value: number;     // 数据量
  color: string;     // 配色
}

interface SentimentDistribution {
  positive: number;
  neutral: number;
  negative: number;
}

interface HotTopicItem {
  rank: number;
  title: string;
  heat: number;
  platform: string;
}

interface AlertEvent {
  id: string;
  level: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  timestamp: string;
}
```

---

## 六、实施计划

### Phase 1: 基础设施（预估 2h）

| 序号 | 任务 | 文件 | 说明 |
|------|------|------|------|
| 1 | 安装 ECharts | `package.json` | `npm install echarts echarts-wordcloud` |
| 2 | 新增路由 | `App.tsx` | 添加 `/bigscreen` 路由 |
| 3 | 新增导航 | `Navbar.tsx` | 添加 "监控大屏" 菜单项 |
| 4 | 创建目录 | `src/components/bigscreen/` | 初始化组件目录结构 |
| 5 | 自适应 Hook | `hooks/useScreenScale.ts` | scale 缩放方案 |

### Phase 2: 基础组件（预估 3h）

| 序号 | 任务 | 文件 | 说明 |
|------|------|------|------|
| 6 | 容器组件 | `ScreenContainer.tsx` | 1920x1080 基准容器 |
| 7 | 边框装饰 | `BorderBox.tsx` | SVG 边框 + 标题 |
| 8 | ECharts 封装 | `EChartBase.tsx` | 统一图表初始化/销毁 |
| 9 | 头部组件 | `Header.tsx` | 标题 + 时间 + 装饰线 |

### Phase 3: 业务模块（预估 4h）

| 序号 | 任务 | 文件 | 数据源 |
|------|------|------|--------|
| 10 | 平台分布 | `PlatformStats.tsx` | `/api/v1/stats/platforms` |
| 11 | 情感分布 | `SentimentPie.tsx` | `/api/v1/sentiment/stats` |
| 12 | 热榜排名 | `TopicRanking.tsx` | `/api/v1/topics?limit=10` |
| 13 | 采集趋势 | `TrendLine.tsx` | `/api/v1/stats/trend` |
| 14 | 预警列表 | `AlertList.tsx` | `/api/v1/alerts` |
| 15 | 词云 | `WordCloud.tsx` | `/api/v1/topic-clusters` |

### Phase 4: 整合与调优（预估 2h）

| 序号 | 任务 | 说明 |
|------|------|------|
| 16 | 页面整合 | `BigScreen.tsx` 组装所有模块 |
| 17 | 自动刷新 | 30秒轮询 + 加载动画 |
| 18 | 响应式调优 | 多分辨率测试 |
| 19 | 颜色统一 | 科技蓝主题色 `#00f2ff` |

---

## 七、风险与规避

| 风险 | 影响 | 规避方案 |
|------|------|----------|
| ECharts 包体积增大 | 首屏加载变慢 | 按需引入图表类型，非全部导入 |
| 大屏与现有样式冲突 | 全局 CSS 污染 | 所有大屏组件使用 CSS Module 或 scoped style |
| 自动刷新导致性能问题 | 内存泄漏 | 严格清理定时器 + ECharts dispose |
| 数据接口格式变更 | 大屏显示异常 | 封装统一的数据适配层，隔离接口变化 |

---

## 八、预期效果

### 新增页面预览

访问 `/bigscreen` 将展示：
- **1920x1080 基准分辨率**的监控大屏
- **科技蓝暗色主题**（`#0a1a2f` 背景 + `#00f2ff` 强调色）
- **30秒自动刷新**实时数据
- **6大核心模块**：平台分布、情感分析、热榜排名、采集趋势、预警事件、话题词云
- **全屏自适应**：任意分辨率通过 scale 缩放适配

### 性能指标

| 指标 | 目标 |
|------|------|
| 首屏加载 | < 3s |
| 数据刷新 | 30s 间隔 |
| 内存占用 | 无泄漏（ECharts 正确销毁） |
| 浏览器兼容 | Chrome/Edge/Firefox 最新版 |

---

## 九、后续扩展点

| 优先级 | 扩展项 | 参考来源 |
|--------|--------|----------|
| P1 | 传播路径飞线图 | DataV `dv-flyline-chart` |
| P2 | 地图地域分布 | iDataV case03 |
| P3 | 视频内容分析 | sentiment_monitor |
| P4 | WebSocket 实时推送 | sentiment_monitor |
| P5 | 3D 情感地形图 | ECharts GL |

---

> 本方案严格遵循"零侵入"原则，所有修改均为新增文件或最小化修改现有文件（仅路由和导航）。现有 Dashboard/Topics/Sentiment/Stats 页面逻辑完全不受影响。
