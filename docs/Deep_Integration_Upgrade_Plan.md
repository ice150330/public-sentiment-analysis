# 舆情系统深度整合升级方案

> 报告日期: 2026-07-10
> 核心思路: **不仅做可视化，更要学架构、算法、工程化**

---

## 一、现状分析：我们的系统缺什么

### 1.1 当前系统能力

| 模块 | 现状 | 问题 |
|------|------|------|
| 情感分析 | 简单规则/词典匹配 | 准确率有限，无法识别反讽、复杂语境 |
| 实体识别 | ❌ 无 | 无法提取人名、地名、机构名 |
| 话题聚类 | 简单关键词统计 | 无语义聚类，同话题分散 |
| 预警系统 | 基础阈值触发 | 无等级分类，无智能降噪 |
| 可视化 | 表格 + 简单卡片 | 无传播路径、无地域分布、无3D |
| 工程化 | 基础 React 组件 | 无主题系统、无自适应、无组件复用 |

### 1.2 参考项目核心能力对比

| 能力 | sentiment_monitor | DataV | big-screen-vue | iDataV | 我们 |
|------|-------------------|-------|----------------|--------|------|
| Transformers情感分析 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 实体识别(NER) | ✅ | ❌ | ❌ | ❌ | ❌ |
| 负面等级分类 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 飞线图(传播路径) | ❌ | ✅ | ❌ | ❌ | ❌ |
| 水位图(情感指数) | ❌ | ✅ | ❌ | ❌ | ❌ |
| 3D可视化 | ❌ | ❌ | ❌ | ✅ | ❌ |
| 地图可视化 | ❌ | ❌ | ❌ | ✅ | ❌ |
| 组件复用体系 | ❌ | ❌ | ✅ | ❌ | ❌ |
| 主题配置系统 | ❌ | ❌ | ✅ | ❌ | ❌ |
| 屏幕自适应 | ❌ | ❌ | ✅ | ❌ | ❌ |

---

## 二、深度学习方向

### 2.1 从 sentiment_monitor 学：NLP Pipeline 架构

sentiment_monitor 的核心价值不是它的代码量（1500+行），而是它的**NLP Pipeline 设计思想**。

#### A. 情感分析 Pipeline 设计

```python
# sentiment_monitor 的 Pipeline 设计（值得我们学习）
class SentimentAnalyzer:
    def analyze(self, text: str) -> Dict:
        # 1. 语言检测
        lang = self.detect_language(text)
        
        # 2. 文本分句（Spacy）
        sentences = self.split_sentences(text, lang)
        
        # 3. 逐句情感分析（Transformers）
        results = []
        for sent in sentences:
            result = self.model(sent)  # BERT/RoBERTa
            results.append(result)
        
        # 4. 综合评分
        sentiment = self.aggregate_results(results)
        
        # 5. 情绪识别（7维情绪）
        emotions = self.analyze_emotions(text)
        
        return {
            'sentiment': sentiment['label'],  # positive/negative/neutral
            'score': sentiment['score'],       # 0-1 置信度
            'confidence': sentiment['confidence'],
            'emotions': emotions,              # {joy: 0.8, anger: 0.1, ...}
            'entities': self.extract_entities(text),  # NER
        }
```

**我们能学到的**：
1. **分层处理**：语言检测 → 分句 → 逐句分析 → 综合评分
2. **多维度输出**：不只是正/负，还有情绪分布、实体提取
3. **置信度机制**：每个结果都有 confidence score

#### B. 负面等级分类体系

```python
# sentiment_monitor 的预警等级设计
class AlertLevel(Enum):
    LOW = 'low'           # 轻微负面，单条内容
    MEDIUM = 'medium'     # 一般负面，小范围传播
    HIGH = 'high'         # 严重负面，大范围传播
    CRITICAL = 'critical' # 紧急，病毒式传播

# 等级判定逻辑（多维度）
def classify_alert_level(content, context):
    score = 0
    
    # 维度1: 情感分数（负向程度）
    sentiment_score = content.sentiment_score  # -1 ~ 1
    if sentiment_score < -0.8: score += 40
    elif sentiment_score < -0.5: score += 25
    
    # 维度2: 传播范围
    if context.share_count > 10000: score += 30
    elif context.share_count > 1000: score += 15
    
    # 维度3: 涉及实体（政府/企业/名人）
    if any(e.type == 'ORG' or e.type == 'PERSON' 
           for e in content.entities):
        score += 20
    
    # 维度4: 时间集中度（短时间内爆发）
    if context.burst_rate > 0.8: score += 10
    
    return score_to_level(score)
```

**我们能学到的**：
1. **多维度评分**：不只靠情感分数，还要考虑传播、实体、时间
2. **实体敏感度**：提及政府/企业的负面内容权重更高
3. **爆发检测**：短时间内的集中传播要升级预警

#### C. 配置驱动架构

```python
# sentiment_monitor 的配置设计
class BaseConfig:
    # NLP 配置
    SENTIMENT_THRESHOLD = 0.6
    NLP_MODEL_PATH = 'models/'
    LANGUAGE_LIST = ['zh', 'en']
    
    # 预警配置
    ALERT_LEVELS = {
        'low': 1, 'medium': 2, 'high': 3, 'critical': 4
    }
    DEFAULT_ALERT_LEVEL = 'medium'
    
    # 采集配置
    COLLECTION_INTERVAL = 3600
    MAX_PAGES_PER_SOURCE = 10
```

**我们能学到的**：
1. **集中配置**：所有参数统一管理，便于调优
2. **环境分离**：BaseConfig / DevelopmentConfig / ProductionConfig
3. **可扩展性**：新增平台/模型只需改配置

---

### 2.2 从 DataV 学：SVG 动画与高级可视化

DataV 的核心价值不是边框装饰，而是**SVG 动画技术**和**特殊图表类型**。

#### A. 飞线图（传播路径可视化）

```javascript
// DataV 飞线图核心逻辑（简化版）
// 用于展示舆情从源头发散到各平台的路径

const flylineData = {
  center: { x: 960, y: 540 },  // 中心点（源头）
  points: [
    { x: 200, y: 200, name: '微博' },
    { x: 1700, y: 300, name: '抖音' },
    { x: 300, y: 800, name: 'B站' },
    { x: 1600, y: 900, name: '知乎' },
  ],
  lines: [
    { from: 'center', to: '微博', value: 5000 },
    { from: 'center', to: '抖音', value: 8000 },
    { from: '微博', to: 'B站', value: 2000 },
  ]
}

// SVG 飞线动画实现
function FlylineChart({ data }) {
  return (
    <svg viewBox="0 0 1920 1080">
      {/* 定义渐变 */}
      <defs>
        <linearGradient id="flyline-gradient">
          <stop offset="0%" stopColor="#00f2ff" stopOpacity="0" />
          <stop offset="50%" stopColor="#00f2ff" stopOpacity="1" />
          <stop offset="100%" stopColor="#00f2ff" stopOpacity="0" />
        </linearGradient>
      </defs>
      
      {/* 绘制飞线路径 */}
      {data.lines.map((line, i) => (
        <g key={i}>
          {/* 基础路径 */}
          <path
            d={calculatePath(line.from, line.to)}
            stroke="#1a3a5c"
            strokeWidth="2"
            fill="none"
          />
          {/* 动画飞线 */}
          <path
            d={calculatePath(line.from, line.to)}
            stroke="url(#flyline-gradient)"
            strokeWidth="3"
            fill="none"
            strokeDasharray="100 1000"
          >
            <animate
              attributeName="stroke-dashoffset"
              from="1000"
              to="-100"
              dur="2s"
              repeatCount="indefinite"
            />
          </path>
        </g>
      ))}
    </svg>
  )
}
```

**应用场景**：
- 展示一条舆情从微博首发，扩散到抖音、B站、知乎的传播路径
- 飞线粗细代表传播量级
- 动画方向代表传播方向

#### B. 水位图（情感指数仪表盘）

```javascript
// DataV 水位图（简化版）
// 用于展示整体情感健康度

function WaterLevelChart({ value, max }) {
  const percentage = (value / max) * 100;
  
  return (
    <div className="water-level-chart">
      <svg viewBox="0 0 200 200">
        {/* 外圆 */}
        <circle cx="100" cy="100" r="90" fill="none" stroke="#1a3a5c" strokeWidth="10" />
        
        {/* 水位 */}
        <clipPath id="wave-clip">
          <rect x="0" y={200 - percentage * 2} width="200" height={percentage * 2} />
        </clipPath>
        
        <circle cx="100" cy="100" r="85" fill="#00f2ff" clipPath="url(#wave-clip)" opacity="0.6">
          <animateTransform
            attributeName="transform"
            type="translate"
            values="-10,0; 10,0; -10,0"
            dur="3s"
            repeatCount="indefinite"
          />
        </circle>
        
        {/* 文字 */}
        <text x="100" y="100" textAnchor="middle" fill="#fff" fontSize="36">
          {percentage.toFixed(1)}%
        </text>
      </svg>
    </div>
  );
}
```

**应用场景**：
- 整体情感健康度仪表盘
- 水位越高 = 正面情绪越多
- 波浪动画增加视觉吸引力

#### C. 轮播表（热榜排名）

```javascript
// DataV 轮播表（简化版）
function ScrollRankingBoard({ data, rowNum = 5 }) {
  const [startIndex, setStartIndex] = useState(0);
  
  useEffect(() => {
    const timer = setInterval(() => {
      setStartIndex(prev => (prev + 1) % data.length);
    }, 3000);
    return () => clearInterval(timer);
  }, [data.length]);
  
  const visibleData = data.slice(startIndex, startIndex + rowNum);
  
  return (
    <div className="scroll-board">
      {visibleData.map((item, i) => (
        <div key={item.id} className="board-row" style={{ animationDelay: `${i * 0.1}s` }}>
          <span className="rank">{item.rank}</span>
          <span className="title">{item.title}</span>
          <span className="heat">{item.heat}</span>
        </div>
      ))}
    </div>
  );
}
```

---

### 2.3 从 big-screen-vue-datav 学：工程化与架构

这个项目的核心不是它用了什么技术，而是**如何组织一个大屏项目的代码**。

#### A. 组件化架构

```
big-screen-vue-datav/src/
├── components/
│   └── echart/
│       ├── center/
│       │   ├── centerChartRate/      ← 可复用组件
│       │   │   ├── index.vue         ← 数据处理
│       │   │   └── chart.vue         ← 图表渲染
│       ├── centerLeft/
│       ├── centerRight/
│       ├── bottom/
│       └── common/
│           └── echart/
│               ├── index.vue         ← ECharts 封装
│               └── theme.json        ← 主题配置
```

**关键设计模式**：
1. **分离数据与渲染**：index.vue 处理数据，chart.vue 负责渲染
2. **统一封装**：所有图表通过 common/echart/index.vue 统一初始化/销毁
3. **主题配置**：theme.json 统一配色，一处修改全局生效

#### B. 自适应方案（Scale）

```javascript
// 核心自适应逻辑
function useDraw() {
  const appRef = ref(null);
  
  const calcRate = () => {
    const baseWidth = 1920;
    const baseHeight = 1080;
    const dom = appRef.value;
    
    // 计算缩放比例
    const scaleX = document.body.clientWidth / baseWidth;
    const scaleY = document.body.clientHeight / baseHeight;
    
    // 等比例缩放（取最小值防止内容溢出）
    dom.style.transform = `scale(${Math.min(scaleX, scaleY)})`;
    dom.style.transformOrigin = '0 0';
  };
  
  onMounted(() => {
    window.addEventListener('resize', debounce(calcRate, 200));
    calcRate();
  });
}
```

**关键优化点**：
1. **防抖处理**：resize 事件用 debounce，避免频繁重绘
2. **等比例缩放**：保持内容比例，不变形
3. **基准尺寸**：1920x1080 作为设计基准

#### C. 数据动态刷新机制

```javascript
// 统一的数据刷新 Mixin
export default {
  data() {
    return {
      timer: null,
      refreshInterval: 30000,  // 30秒刷新
    };
  },
  mounted() {
    this.startRefresh();
  },
  beforeDestroy() {
    this.stopRefresh();
  },
  methods: {
    startRefresh() {
      this.fetchData();  // 首次加载
      this.timer = setInterval(() => {
        this.fetchData();
      }, this.refreshInterval);
    },
    stopRefresh() {
      if (this.timer) {
        clearInterval(this.timer);
        this.timer = null;
      }
    },
    async fetchData() {
      // 子组件重写此方法
    }
  }
};
```

---

### 2.4 从 iDataV 学：高级图表组合

iDataV 的核心价值是**展示 ECharts 的高级用法**。

#### A. 关系图谱（舆情传播网络）

```javascript
// 使用 ECharts Graph 展示舆情传播关系
const graphOption = {
  series: [{
    type: 'graph',
    layout: 'force',
    data: [
      { id: '0', name: '源头', symbolSize: 50, category: 0 },
      { id: '1', name: '大V-A', symbolSize: 30, category: 1 },
      { id: '2', name: '大V-B', symbolSize: 25, category: 1 },
      { id: '3', name: '用户-1', symbolSize: 10, category: 2 },
      // ...
    ],
    links: [
      { source: '0', target: '1', value: 100 },
      { source: '0', target: '2', value: 80 },
      { source: '1', target: '3', value: 20 },
      // ...
    ],
    categories: [
      { name: '源头' },
      { name: '关键传播者' },
      { name: '普通用户' },
    ],
    roam: true,
    label: { show: true },
    force: {
      repulsion: 1000,
      edgeLength: 200
    }
  }]
};
```

**应用场景**：
- 展示一条舆情的传播网络
- 节点大小 = 影响力
- 边的粗细 = 传播量
- 颜色 = 传播层级

#### B. 旭日图（话题层级分析）

```javascript
// ECharts Sunburst 展示话题层级
const sunburstOption = {
  series: [{
    type: 'sunburst',
    data: [{
      name: '体育',
      children: [{
        name: '足球',
        children: [
          { name: '国足', value: 10 },
          { name: '中超', value: 8 }
        ]
      }, {
        name: '篮球',
        children: [
          { name: 'CBA', value: 6 },
          { name: 'NBA', value: 12 }
        ]
      }]
    }, {
      name: '科技',
      children: [/* ... */]
    }],
    radius: [0, '90%'],
    label: { rotate: 'radial' }
  }]
};
```

#### C. 地图热力（地域分布）

```javascript
// ECharts Map + Heatmap
const mapOption = {
  series: [{
    type: 'map',
    map: 'china',
    data: [
      { name: '北京', value: 1000 },
      { name: '上海', value: 800 },
      { name: '广东', value: 1200 },
      // ...
    ],
    visualMap: {
      min: 0,
      max: 2000,
      inRange: {
        color: ['#e0f3f8', '#abd9e9', '#74add1', '#4575b4', '#313695']
      }
    }
  }]
};
```

---

## 三、全面升级方案

### 3.1 后端升级：NLP Pipeline 增强

#### A. 新增 Transformers 情感分析模块

```python
# app/ml/transformers_sentiment.py
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

class TransformersSentimentAnalyzer:
    """
    基于 Transformers 的情感分析器
    
    对比现有方案：
    - 现有：基于词典/规则，准确率 ~70%
    - 新方案：基于 BERT/RoBERTa，准确率 ~90%+
    """
    
    def __init__(self, model_name: str = "uer/roberta-base-finetuned-jd-binary-chinese"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.eval()
    
    def analyze(self, text: str) -> Dict:
        """分析文本情感"""
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            probabilities = torch.softmax(outputs.logits, dim=1)
        
        positive_prob = probabilities[0][1].item()
        negative_prob = probabilities[0][0].item()
        
        return {
            'sentiment': 'positive' if positive_prob > 0.5 else 'negative',
            'positive_score': positive_prob,
            'negative_score': negative_prob,
            'confidence': max(positive_prob, negative_prob),
        }
```

#### B. 新增实体识别模块

```python
# app/ml/ner_extractor.py
from transformers import AutoTokenizer, AutoModelForTokenClassification
import torch

class NERExtractor:
    """
    命名实体识别提取器
    
    提取文本中的人名、地名、机构名
    """
    
    def __init__(self, model_name: str = "shibing624/macbert4cner-base-chinese"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForTokenClassification.from_pretrained(model_name)
        self.model.eval()
        
        # 实体标签映射
        self.label_map = {
            'PER': '人名',
            'LOC': '地名', 
            'ORG': '机构名',
        }
    
    def extract(self, text: str) -> List[Dict]:
        """提取文本中的实体"""
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        predictions = torch.argmax(outputs.logits, dim=2)
        tokens = self.tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
        
        entities = []
        current_entity = None
        
        for token, pred in zip(tokens, predictions[0]):
            label = self.model.config.id2label[pred.item()]
            
            if label.startswith("B-"):
                if current_entity:
                    entities.append(current_entity)
                current_entity = {
                    'text': token,
                    'type': label.split("-")[1],
                    'type_name': self.label_map.get(label.split("-")[1], '其他'),
                }
            elif label.startswith("I-") and current_entity:
                current_entity['text'] += token
            else:
                if current_entity:
                    entities.append(current_entity)
                    current_entity = None
        
        return entities
```

#### C. 升级预警等级分类

```python
# app/services/alert_engine_v2.py
from enum import Enum
from typing import List, Dict
from datetime import datetime, timedelta

class AlertLevelV2(Enum):
    """预警等级（升级版）"""
    INFO = 'info'           # 信息级：轻微负面，无需处理
    LOW = 'low'             # 低级：一般负面，关注即可
    MEDIUM = 'medium'       # 中级：较严重，需要跟进
    HIGH = 'high'           # 高级：严重，需要紧急处理
    CRITICAL = 'critical'   # 紧急：极其严重，需要立即处理

class AlertEngineV2:
    """
    智能预警引擎（升级版）
    
    对比现有方案：
    - 现有：简单阈值触发（情感分数 < -0.5）
    - 新方案：多维度评分 + 智能降噪 + 等级分类
    """
    
    def __init__(self):
        self.scoring_weights = {
            'sentiment': 0.3,      # 情感分数权重
            'spread': 0.25,         # 传播范围权重
            'entity': 0.2,          # 实体敏感度权重
            'velocity': 0.15,       # 传播速度权重
            'source': 0.1,          # 来源可信度权重
        }
    
    def calculate_risk_score(self, content, context) -> float:
        """
        计算风险评分（0-100）
        """
        score = 0
        
        # 1. 情感分数（负向程度）
        sentiment_score = abs(content.sentiment_score)
        score += sentiment_score * 100 * self.scoring_weights['sentiment']
        
        # 2. 传播范围
        spread_score = min(context.share_count / 10000, 1.0)
        score += spread_score * 100 * self.scoring_weights['spread']
        
        # 3. 实体敏感度
        sensitive_entities = [
            e for e in content.entities
            if e['type'] in ['ORG', 'GOV', 'PERSON']
        ]
        entity_score = min(len(sensitive_entities) / 3, 1.0)
        score += entity_score * 100 * self.scoring_weights['entity']
        
        # 4. 传播速度（爆发率）
        velocity_score = context.burst_rate
        score += velocity_score * 100 * self.scoring_weights['velocity']
        
        # 5. 来源可信度（官方媒体权重更高）
        trusted_sources = ['新华社', '人民日报', '央视']
        source_score = 1.0 if content.source in trusted_sources else 0.5
        score += source_score * 100 * self.scoring_weights['source']
        
        return min(score, 100)
    
    def classify_level(self, score: float) -> AlertLevelV2:
        """根据评分分类等级"""
        if score >= 80: return AlertLevelV2.CRITICAL
        if score >= 60: return AlertLevelV2.HIGH
        if score >= 40: return AlertLevelV2.MEDIUM
        if score >= 20: return AlertLevelV2.LOW
        return AlertLevelV2.INFO
    
    def should_alert(self, content, context) -> bool:
        """
        智能降噪：判断是否需要预警
        
        过滤条件：
        1. 广告/营销内容
        2. 重复内容（相似度 > 0.8）
        3. 历史已处理过的类似事件
        """
        # 过滤广告
        if self.is_ads(content):
            return False
        
        # 过滤重复
        if self.is_duplicate(content):
            return False
        
        # 过滤历史已处理
        if self.is_historically_handled(content):
            return False
        
        return True
```

### 3.2 前端升级：架构重构

#### A. 主题系统

```typescript
// src/theme/bigscreen.ts
export const bigScreenTheme = {
  // 色彩
  colors: {
    primary: '#00f2ff',
    secondary: '#0066ff',
    success: '#00ff88',
    warning: '#ffaa00',
    danger: '#ff4444',
    background: '#0a1a2f',
    surface: '#112240',
    text: '#e6f7ff',
    textMuted: '#8b9dc3',
  },
  
  // 字体
  fonts: {
    title: '24px',
    subtitle: '18px',
    body: '14px',
    small: '12px',
  },
  
  // 边框
  borders: {
    default: '1px solid rgba(0, 242, 255, 0.2)',
    glow: '0 0 10px rgba(0, 242, 255, 0.3)',
  },
  
  // 动画
  animations: {
    fadeIn: 'fadeIn 0.5s ease-in',
    slideUp: 'slideUp 0.3s ease-out',
    pulse: 'pulse 2s infinite',
  }
};

// ECharts 主题配置
export const echartsTheme = {
  color: ['#00f2ff', '#0066ff', '#00ff88', '#ffaa00', '#ff4444'],
  backgroundColor: 'transparent',
  textStyle: { color: '#e6f7ff' },
  title: { textStyle: { color: '#00f2ff', fontSize: 18 } },
  legend: { textStyle: { color: '#8b9dc3' } },
  tooltip: {
    backgroundColor: 'rgba(10, 26, 47, 0.9)',
    borderColor: '#00f2ff',
    textStyle: { color: '#e6f7ff' },
  },
};
```

#### B. 组件复用体系

```typescript
// src/components/bigscreen/BaseChart.tsx
import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { echartsTheme } from '@/theme/bigscreen';

interface BaseChartProps {
  id: string;
  options: echarts.EChartsOption;
  width?: string;
  height?: string;
  onClick?: (params: any) => void;
}

export const BaseChart: React.FC<BaseChartProps> = ({
  id,
  options,
  width = '100%',
  height = '100%',
  onClick,
}) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  
  useEffect(() => {
    if (chartRef.current) {
      // 注册主题
      echarts.registerTheme('bigscreen', echartsTheme);
      chartInstance.current = echarts.init(chartRef.current, 'bigscreen');
      
      if (onClick) {
        chartInstance.current.on('click', onClick);
      }
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

#### C. 数据管理（Hooks）

```typescript
// src/hooks/useAutoRefresh.ts
import { useState, useEffect, useCallback } from 'react';

interface UseAutoRefreshOptions<T> {
  fetcher: () => Promise<T>;
  interval?: number;  // 默认 30秒
  immediate?: boolean; // 是否立即执行
}

export function useAutoRefresh<T>({
  fetcher,
  interval = 30000,
  immediate = true,
}: UseAutoRefreshOptions<T>) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  
  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetcher();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  }, [fetcher]);
  
  useEffect(() => {
    if (immediate) {
      refresh();
    }
    
    const timer = setInterval(refresh, interval);
    return () => clearInterval(timer);
  }, [refresh, interval, immediate]);
  
  return { data, loading, error, refresh };
}

// 使用示例
function PlatformStats() {
  const { data, loading } = useAutoRefresh({
    fetcher: () => api.getPlatformStats(),
    interval: 30000,
  });
  
  if (loading) return <Loading />;
  
  return (
    <BaseChart
      id="platform-stats"
      options={generatePieOption(data)}
    />
  );
}
```

### 3.3 高级可视化模块

#### A. 传播路径飞线图

```typescript
// src/components/bigscreen/modules/PropagationMap.tsx
import React from 'react';

interface Node {
  id: string;
  name: string;
  x: number;
  y: number;
  value: number;
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

export const PropagationMap: React.FC<Props> = ({ nodes, edges }) => {
  return (
    <div className="propagation-map">
      <svg viewBox="0 0 800 600">
        <defs>
          {/* 飞线渐变 */}
          <linearGradient id="flyline-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#00f2ff" stopOpacity="0" />
            <stop offset="50%" stopColor="#00f2ff" stopOpacity="1" />
            <stop offset="100%" stopColor="#00f2ff" stopOpacity="0" />
          </linearGradient>
          
          {/* 发光滤镜 */}
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        
        {/* 绘制节点 */}
        {nodes.map(node => (
          <g key={node.id}>
            <circle
              cx={node.x}
              cy={node.y}
              r={Math.sqrt(node.value) / 5}
              fill="#00f2ff"
              opacity="0.6"
              filter="url(#glow)"
            />
            <text
              x={node.x}
              y={node.y + Math.sqrt(node.value) / 5 + 15}
              textAnchor="middle"
              fill="#e6f7ff"
              fontSize="12"
            >
              {node.name}
            </text>
          </g>
        ))}
        
        {/* 绘制飞线 */}
        {edges.map((edge, i) => {
          const fromNode = nodes.find(n => n.id === edge.from);
          const toNode = nodes.find(n => n.id === edge.to);
          if (!fromNode || !toNode) return null;
          
          return (
            <g key={i}>
              {/* 基础线 */}
              <line
                x1={fromNode.x}
                y1={fromNode.y}
                x2={toNode.x}
                y2={toNode.y}
                stroke="#1a3a5c"
                strokeWidth="1"
              />
              {/* 动画飞线 */}
              <line
                x1={fromNode.x}
                y1={fromNode.y}
                x2={toNode.x}
                y2={toNode.y}
                stroke="url(#flyline-gradient)"
                strokeWidth="2"
                strokeDasharray="20 100"
              >
                <animate
                  attributeName="stroke-dashoffset"
                  from="120"
                  to="-20"
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

#### B. 情感水位仪表盘

```typescript
// src/components/bigscreen/modules/SentimentGauge.tsx
import React from 'react';

interface Props {
  value: number;  // 0-100，正面情感指数
}

export const SentimentGauge: React.FC<Props> = ({ value }) => {
  const waveHeight = 200 - (value / 100) * 180;
  
  return (
    <div className="sentiment-gauge">
      <svg viewBox="0 0 200 200" className="gauge-svg">
        <defs>
          <clipPath id="wave-clip">
            <rect x="10" y={waveHeight} width="180" height={190 - waveHeight} />
          </clipPath>
          
          <linearGradient id="water-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#00f2ff" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#0066ff" stopOpacity="0.4" />
          </linearGradient>
        </defs>
        
        {/* 外圆 */}
        <circle
          cx="100"
          cy="100"
          r="90"
          fill="none"
          stroke="#1a3a5c"
          strokeWidth="8"
        />
        
        {/* 水位 */}
        <circle
          cx="100"
          cy="100"
          r="86"
          fill="url(#water-gradient)"
          clipPath="url(#wave-clip)"
        >
          <animateTransform
            attributeName="transform"
            type="translate"
            values="-5,0; 5,0; -5,0"
            dur="3s"
            repeatCount="indefinite"
          />
        </circle>
        
        {/* 刻度 */}
        {[0, 25, 50, 75, 100].map(tick => {
          const angle = (tick / 100) * Math.PI - Math.PI / 2;
          const x1 = 100 + 70 * Math.cos(angle);
          const y1 = 100 + 70 * Math.sin(angle);
          const x2 = 100 + 80 * Math.cos(angle);
          const y2 = 100 + 80 * Math.sin(angle);
          return (
            <g key={tick}>
              <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="#1a3a5c" strokeWidth="2" />
              <text
                x={100 + 60 * Math.cos(angle)}
                y={100 + 60 * Math.sin(angle)}
                textAnchor="middle"
                fill="#8b9dc3"
                fontSize="10"
              >
                {tick}
              </text>
            </g>
          );
        })}
        
        {/* 数值 */}
        <text x="100" y="95" textAnchor="middle" fill="#00f2ff" fontSize="32" fontWeight="bold">
          {value}%
        </text>
        <text x="100" y="115" textAnchor="middle" fill="#8b9dc3" fontSize="12">
          正面情感指数
        </text>
      </svg>
    </div>
  );
};
```

#### C. 关系图谱

```typescript
// src/components/bigscreen/modules/RelationGraph.tsx
import React from 'react';
import { BaseChart } from '../BaseChart';

interface Node {
  id: string;
  name: string;
  symbolSize: number;
  category: number;
}

interface Edge {
  source: string;
  target: string;
  value: number;
}

interface Props {
  nodes: Node[];
  edges: Edge[];
  categories: string[];
}

export const RelationGraph: React.FC<Props> = ({ nodes, edges, categories }) => {
  const options: echarts.EChartsOption = {
    series: [{
      type: 'graph',
      layout: 'force',
      data: nodes,
      links: edges,
      categories: categories.map(name => ({ name })),
      roam: true,
      label: {
        show: true,
        position: 'right',
        color: '#e6f7ff',
      },
      force: {
        repulsion: 1000,
        edgeLength: [100, 300],
        gravity: 0.1,
      },
      lineStyle: {
        color: 'source',
        curveness: 0.3,
        opacity: 0.6,
      },
      emphasis: {
        focus: 'adjacency',
        lineStyle: {
          width: 4,
          opacity: 1,
        },
      },
    }],
  };
  
  return <BaseChart id="relation-graph" options={options} height="500px" />;
};
```

---

## 四、实施路线图

### Phase 1: 后端算法增强（2-3天）

| 序号 | 任务 | 说明 | 参考来源 |
|------|------|------|----------|
| 1 | 引入 Transformers 情感分析 | 替换现有规则匹配，准确率从70%→90%+ | sentiment_monitor |
| 2 | 新增实体识别(NER) | 提取人名、地名、机构名 | sentiment_monitor |
| 3 | 升级预警等级分类 | 多维度评分（情感/传播/实体/速度） | sentiment_monitor |
| 4 | 新增情绪识别 | 7维情绪分析（喜/怒/哀/惧/惊/厌/中性） | sentiment_monitor |
| 5 | 配置驱动架构 | 所有参数集中管理，支持环境分离 | sentiment_monitor |

### Phase 2: 前端架构升级（2-3天）

| 序号 | 任务 | 说明 | 参考来源 |
|------|------|------|----------|
| 6 | 主题系统 | 统一色彩/字体/动画配置 | big-screen-vue |
| 7 | ECharts 主题 | 自定义 bigscreen 主题 | big-screen-vue |
| 8 | 组件复用体系 | BaseChart / BorderBox / Header 统一封装 | big-screen-vue |
| 9 | 自适应方案 | scale 缩放 + 防抖 | big-screen-vue |
| 10 | 数据管理 Hooks | useAutoRefresh / useScreenScale | big-screen-vue |

### Phase 3: 高级可视化（3-4天）

| 序号 | 任务 | 说明 | 参考来源 |
|------|------|------|----------|
| 11 | 传播路径飞线图 | SVG 动画展示舆情扩散 | DataV |
| 12 | 情感水位仪表盘 | 波浪动画 + 刻度 | DataV |
| 13 | 热榜轮播表 | 自动滚动 + 排名 | DataV |
| 14 | 关系图谱 | ECharts Graph 展示传播网络 | iDataV |
| 15 | 旭日图 | 话题层级分析 | iDataV |
| 16 | 地图热力 | 地域分布可视化 | iDataV |

### Phase 4: 大屏整合（2天）

| 序号 | 任务 | 说明 |
|------|------|------|
| 17 | 大屏布局 | Left-Center-Right 经典布局 |
| 18 | 数据对接 | 所有模块接入现有 API |
| 19 | 自动刷新 | 30秒轮询 + 加载动画 |
| 20 | 性能优化 | ECharts 按需引入 + 正确销毁 |

---

## 五、预期收益

### 5.1 算法层面

| 指标 | 现有 | 升级后 | 提升 |
|------|------|--------|------|
| 情感分析准确率 | ~70% | ~90% | +20% |
| 实体识别 | ❌ 无 | ✅ 支持 | 新增 |
| 预警准确度 | 阈值触发 | 多维度评分 | 质的飞跃 |
| 情绪维度 | 3维（正/中/负） | 7维 | +4维 |

### 5.2 可视化层面

| 能力 | 现有 | 升级后 |
|------|------|--------|
| 传播路径 | ❌ 无 | ✅ 飞线图 |
| 情感指数 | ❌ 无 | ✅ 水位仪表盘 |
| 传播网络 | ❌ 无 | ✅ 关系图谱 |
| 话题层级 | ❌ 无 | ✅ 旭日图 |
| 地域分布 | ❌ 无 | ✅ 地图热力 |
| 主题切换 | ❌ 无 | ✅ 配置驱动 |

### 5.3 工程化层面

| 能力 | 现有 | 升级后 |
|------|------|--------|
| 组件复用 | 低 | 高（统一封装） |
| 主题管理 | 硬编码 | 配置驱动 |
| 自适应 | ❌ 无 | ✅ scale 方案 |
| 数据刷新 | 手动 | 自动（Hooks） |
| 性能优化 | 无 | 防抖 + 按需加载 |

---

## 六、风险与规避

| 风险 | 影响 | 规避方案 |
|------|------|----------|
| Transformers 模型体积大 | 部署困难 | 使用轻量级模型（DistilBERT） |
| GPU 依赖 | 服务器无 GPU | 支持 CPU 推理，牺牲部分速度 |
| 前端包体积增大 | 首屏加载慢 | ECharts 按需引入，懒加载大屏 |
| SVG 动画性能 | 低端设备卡顿 | 提供降级方案（静态图表） |
| 地图数据缺失 | 地图无法显示 | 使用 ECharts 官方地图数据 |

---

## 七、总结

这次升级不只是"加个大屏"，而是：

1. **算法升级**：从规则匹配 → Transformers 深度学习
2. **架构升级**：从硬编码 → 配置驱动 + 模块化
3. **可视化升级**：从表格 → 飞线图/水位图/关系图谱
4. **工程化升级**：从随意编码 → 组件复用 + 主题系统

**核心学习成果**：
- sentiment_monitor → NLP Pipeline 设计 + 多维度预警
- DataV → SVG 动画技术 + 特殊图表类型
- big-screen-vue → 工程化架构 + 自适应方案
- iDataV → 高级图表组合 + 3D/地图可视化

这是一个从"能用"到"好用"再到"专业"的跨越。
