# 公众情绪智能分析系统 — 设计规约

> 版本: v1.0  
> 日期: 2026-07-07  
> 状态: 活跃

本文档定义本项目的整体设计范式、约束条件与协作规范。所有开发工作必须遵循此规约。

---

## 目录

1. [项目定位](#1-项目定位)
2. [设计范式](#2-设计范式)
3. [架构约束](#3-架构约束)
4. [编码规范](#4-编码规范)
5. [数据规范](#5-数据规范)
6. [接口规范](#6-接口规范)
7. [文档规范](#7-文档规范)
8. [协作流程](#8-协作流程)
9. [技术债务管理](#9-技术债务管理)

---

## 1. 项目定位

### 1.1 一句话定义

一套覆盖六大主流中文社交媒体平台、具备实时采集、智能分析、趋势预测与可视化展示能力的公众情绪智能分析系统。

### 1.2 核心属性

| 属性 | 定义 | 不可妥协 |
|------|------|---------|
| 学术性 | 本科毕业设计项目，需支撑 1.5-2 万字论文 | ✅ 是 |
| 完整性 | 端到端可运行系统，非概念原型 | ✅ 是 |
| 可展示性 | 具备可视化界面，可现场演示 | ✅ 是 |
| 技术深度 | 包含 BERT 情感分析、LSTM 预测、SHAP 可解释性 | ✅ 是 |
| 可扩展性 | 架构支持后续增加平台或分析模块 | ⚠️ 尽量 |

### 1.3 边界声明

**本项目不做的事：**
- ❌ 大规模分布式部署（单机 Docker Compose 即可）
- ❌ 高并发优化（目标用户量 < 10 人，演示场景）
- ❌ 商业级反爬策略（学术场景，控制频率即可）
- ❌ 实时毫秒级更新（小时级采集+分析足够）
- ❌ 多语言支持（仅限中文内容分析）
- ❌ 用户注册/权限管理（单用户演示，无需复杂 RBAC）

---

## 2. 设计范式

### 2.1 分层架构范式

**严格遵循四层分离：**

```
前端展示层 ←── REST API ──→ 后端服务层
                              ↓
                         分析引擎层
                              ↓
                         数据存储层
                              ↓
                         数据采集层
```

**核心原则：** 下层不依赖上层。数据采集层不知道分析引擎存在，分析引擎通过标准接口消费数据。

### 2.2 模块化设计范式

**高内聚、低耦合。** 每个模块有明确的接口契约，模块内部实现可替换。

```python
# 示例: 情感分析引擎的接口契约
class SentimentAnalyzer(Protocol):
    """
    情感分析引擎接口契约
    所有实现必须遵循此接口，确保可替换性
    """
    
    def analyze(self, text: str) -> SentimentResult:
        """
        分析单条文本的情感倾向
        
        Args:
            text: 待分析文本，长度不超过 4096 字符
            
        Returns:
            SentimentResult: 包含 label, confidence, scores
            
        Raises:
            TextTooLongError: 文本超过长度限制
            AnalysisError: 分析过程中发生错误
        """
        ...
    
    def batch_analyze(self, texts: List[str]) -> List[SentimentResult]:
        """批量分析，返回顺序与输入一致"""
        ...
    
    @property
    def model_info(self) -> ModelInfo:
        """返回模型元信息（名称、版本、训练日期）"""
        ...
```

### 2.3 数据流范式

**单向数据流，禁止环形依赖。**

```
采集器 → 清洗器 → 存储器 → 分析器 → 结果存储器 → API → 前端
   ↑___________________________________________________________↓
   (仅配置/调度信号，非数据流)
```

### 2.4 配置驱动范式

**所有可变行为必须配置化，禁止硬编码。**

```python
# ❌ 禁止
TIMEOUT = 10  # 硬编码

# ✅ 正确
TIMEOUT = settings.crawler.request_timeout  # 配置驱动
```

配置分层：
- `config/default.yaml` — 默认配置（提交到仓库）
- `config/local.yaml` — 本地覆盖（不提交，gitignore）
- `config/production.yaml` — 生产环境（可选）
- 环境变量 > 本地配置 > 默认配置

---

## 3. 架构约束

### 3.1 技术栈锁定

**以下技术选型已确定，非经充分论证不得更换：**

| 层级 | 技术 | 版本约束 | 更换门槛 |
|------|------|---------|---------|
| 前端框架 | React | 19.x | 不适用 |
| 前端语言 | TypeScript | 5.x | 不适用 |
| UI 库 | Ant Design | 5.x | 不适用 |
| 图表 | ECharts | 5.x | 不适用 |
| 后端框架 | FastAPI | 0.115+ | 不适用 |
| ORM | SQLAlchemy | 2.x | 不适用 |
| 任务队列 | Celery | 5.x | 不适用 |
| 主数据库 | PostgreSQL | 16+ | 不适用 |
| 缓存 | Redis | 7.x | 不适用 |
| 文档数据库 | MongoDB | 7.x | 不适用 |
| 深度学习 | PyTorch | 2.3+ | 不适用 |
| NLP | Transformers | 4.40+ | 不适用 |
| 爬虫 | Playwright | 1.45+ | 不适用 |
| 容器 | Docker | 26+ | 不适用 |
| 编排 | Docker Compose | 2.27+ | 不适用 |

### 3.2 数据库约束

**PostgreSQL 表设计约束：**

1. **所有表必须有主键** — 使用 `SERIAL` 或 `UUID`
2. **所有表必须有 `created_at` 字段** — `TIMESTAMP DEFAULT NOW()`
3. **外键必须建立索引** — 保证 JOIN 性能
4. **JSON 字段使用 `JSONB`** — 支持索引和查询
5. **文本字段使用 `TEXT` 而非 `VARCHAR(n)`** — PostgreSQL 无性能差异，TEXT 更灵活
6. **状态字段使用 `SMALLINT` + 枚举** — 不直接用字符串，节省空间且可索引
7. **时间字段带时区** — `TIMESTAMP WITH TIME ZONE`

**MongoDB 文档设计约束：**

1. **集合名使用小写+下划线** — 如 `raw_articles`
2. **每个文档必须有 `_id` 和 `created_at`**
3. **单文档不超过 16MB** — 大文本分片存储
4. **嵌套不超过 3 层** — 防止查询复杂化

### 3.3 API 约束

**REST API 设计约束：**

1. **URL 全小写，单词间用连字符** — `/api/v1/sentiment-analysis` 而非 `/api/v1/sentimentAnalysis`
2. **资源名用复数** — `/api/v1/articles` 而非 `/api/v1/article`
3. **动作通过 HTTP 方法表达** — GET / POST / PUT / DELETE / PATCH
4. **版本号在 URL 中** — `/api/v1/...`，支持多版本共存
5. **响应统一包装** — `{"code": 200, "data": ..., "message": "..."}`
6. **分页标准参数** — `page` (默认1), `page_size` (默认20, 最大100)
7. **时间范围参数** — `start_time` / `end_time`，ISO 8601 格式

### 3.4 安全约束

1. **密码/密钥绝不提交到仓库** — 使用环境变量或 `.env` 文件（gitignore）
2. **爬虫 Cookie 不提交** — 存储在 `secrets/` 目录（gitignore）
3. **数据库连接字符串不包含密码** — 使用环境变量注入
4. **所有用户输入做参数校验** — Pydantic 模型严格校验
5. **SQL 必须参数化** — 禁止字符串拼接 SQL

---

## 4. 编码规范

### 4.1 Python 规范

**遵循 PEP 8 + 项目补充规则：**

```python
# 文件头模板
"""
模块名称: sentiment_analyzer.py
模块职责: 情感分析引擎主模块
作者: [你的名字]
日期: 2026-07-07
版本: 1.0.0
"""

from typing import List, Dict, Optional, Protocol
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SentimentResult:
    """情感分析结果不可变对象"""
    label: str                    # 'positive', 'negative', 'neutral'
    confidence: float            # 0.0 ~ 1.0
    scores: Dict[str, float]    # 各分类分数
    model_version: str           # 模型版本号
    analyzed_at: datetime        # 分析时间


class SentimentAnalyzer:
    """
    情感分析引擎
    
    基于 BERT 预训练模型，支持单条和批量分析。
    
    使用示例:
        >>> analyzer = SentimentAnalyzer(model_path="models/bert-sentiment")
        >>> result = analyzer.analyze("这个产品太棒了！")
        >>> print(result.label)
        'positive'
    """
    
    def __init__(self, model_path: str, device: str = "auto") -> None:
        """
        初始化分析器
        
        Args:
            model_path: 模型文件路径或 HuggingFace 模型名
            device: 计算设备，'auto' 自动选择 (cuda > mps > cpu)
        """
        ...
    
    def analyze(self, text: str) -> SentimentResult:
        """分析单条文本"""
        ...
```

**补充规则：**

| 规则 | 说明 |
|------|------|
| 类型注解强制 | 所有函数参数和返回值必须有类型注解 |
| 文档字符串强制 | 所有模块、类、方法必须有 docstring |
| 日志使用 | 禁止 `print()` 用于日志，使用 `logging` 模块 |
| 异常处理 | 自定义异常继承自 `Exception`，命名以 `Error` 结尾 |
| 常量定义 | 模块级常量全大写，如 `MAX_BATCH_SIZE = 100` |
| 函数长度 | 单个函数不超过 50 行，超过必须拆分 |
| 类长度 | 单个类不超过 300 行，超过必须拆分 |
| 导入排序 | stdlib → 第三方 → 本地，每组空一行 |

### 4.2 TypeScript/React 规范

```typescript
// 文件头模板
/**
 * @file SentimentTrendChart.tsx
 * @description 情感趋势折线图组件
 * @author [你的名字]
 * @date 2026-07-07
 */

import React, { useEffect, useState, useCallback } from 'react';
import { Line } from 'echarts-for-react';
import { useDashboardStore } from '@/stores/dashboardStore';
import type { SentimentTrendData } from '@/types/dashboard';

interface SentimentTrendChartProps {
  /** 时间范围天数 */
  days: number;
  /** 平台筛选，空数组表示全部 */
  platforms?: string[];
  /** 数据加载完成回调 */
  onLoad?: (data: SentimentTrendData) => void;
}

/**
 * 情感趋势折线图
 * 
 * 展示指定时间范围内各平台的情感分数变化趋势。
 * 支持按平台筛选、悬停查看详情、点击下钻。
 */
export const SentimentTrendChart: React.FC<SentimentTrendChartProps> = ({
  days,
  platforms = [],
  onLoad,
}) => {
  const [loading, setLoading] = useState<boolean>(false);
  const { fetchTrendData, trendData } = useDashboardStore();

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchTrendData({ days, platforms });
      onLoad?.(data);
    } finally {
      setLoading(false);
    }
  }, [days, platforms, fetchTrendData, onLoad]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ... 渲染逻辑
};
```

**补充规则：**

| 规则 | 说明 |
|------|------|
| 组件命名 | PascalCase，如 `SentimentTrendChart` |
| 文件命名 | 与组件名一致，如 `SentimentTrendChart.tsx` |
|  Hooks 命名 | 以 `use` 开头，如 `useDashboardStore` |
| 类型定义 | 接口用 `interface`，类型别名用 `type` |
|  Props 文档 | 每个 props 必须有 JSDoc 注释 |
| 状态管理 | 使用 Zustand，禁止直接修改状态 |
| API 调用 | 统一封装在 `services/` 目录，禁止组件内直接 `fetch` |
| 错误处理 | API 错误统一在拦截器中处理，组件只处理 UI 状态 |

### 4.3 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 变量 | snake_case (Python) / camelCase (TS) | `article_count`, `articleCount` |
| 常量 | UPPER_SNAKE_CASE | `MAX_BATCH_SIZE` |
| 类 | PascalCase | `SentimentAnalyzer` |
| 函数 | snake_case / camelCase | `analyze_sentiment()`, `analyzeSentiment()` |
| 文件 | snake_case (Python) / PascalCase (组件) | `sentiment_analyzer.py`, `SentimentChart.tsx` |
| 数据库表 | snake_case, 复数 | `sentiment_results` |
| 数据库列 | snake_case | `created_at` |
| API 端点 | kebab-case, 复数 | `/api/v1/sentiment-results` |
| 环境变量 | UPPER_SNAKE_CASE | `DATABASE_URL` |
| Git 分支 | kebab-case | `feature/sentiment-engine` |

---

## 5. 数据规范

### 5.1 数据采集规范

1. **采集时间统一 UTC+8** — 所有 `crawl_time` 存储为 UTC+8
2. **原始数据必须保留** — 清洗后的数据存 PostgreSQL，原始 HTML/JSON 存 MongoDB
3. **去重策略** — 以 `platform + topic_id + crawl_date` 联合唯一键去重
4. **采集频率上限** — 单个平台每小时不超过 1 次（防封策略）
5. **失败重试** — 指数退避，最大 3 次重试
6. **采集日志** — 每次采集记录状态、耗时、数据量、错误信息

### 5.2 数据清洗规范

```python
# 清洗管道必须遵循此顺序
CLEAN_PIPELINE = [
    'remove_html_tags',      # 去除 HTML 标签
    'normalize_whitespace',   # 规范化空白字符
    'remove_urls',           # 去除 URL 链接
    'remove_at_mentions',    # 去除 @提及
    'remove_emojis',         # 去除表情符号（可选，分析时保留）
    'truncate_long_text',    # 截断超长文本
    'deduplicate',           # 去重
]
```

### 5.3 数据质量规范

| 指标 | 目标 | 检测方式 |
|------|------|---------|
| 采集成功率 | > 90% | 采集日志统计 |
| 数据完整率 | > 95% | 必填字段非空检查 |
| 去重准确率 | 100% | 联合唯一键约束 |
| 情感分析准确率 | > 85% | 人工抽样标注验证 |
| 预测准确率 | MAPE < 30% | 历史回测验证 |

---

## 6. 接口规范

### 6.1 API 响应格式

```json
{
  "code": 200,
  "data": { ... },
  "message": "success",
  "request_id": "req_abc123def456",
  "timestamp": "2026-07-07T14:30:00+08:00"
}
```

### 6.2 错误响应格式

```json
{
  "code": 400,
  "data": null,
  "message": "Invalid parameter: 'days' must be between 1 and 365",
  "error_type": "ValidationError",
  "request_id": "req_abc123def456",
  "timestamp": "2026-07-07T14:30:00+08:00"
}
```

### 6.3 状态码规范

| 状态码 | 使用场景 | 说明 |
|--------|---------|------|
| 200 | 成功 | 标准成功响应 |
| 201 | 创建成功 | 资源创建完成 |
| 204 | 无内容 | 删除成功 |
| 400 | 请求参数错误 | 客户端输入校验失败 |
| 401 | 未认证 | 需要登录（本项目极少使用） |
| 403 | 无权限 | 禁止访问 |
| 404 | 资源不存在 | 查询的 ID 不存在 |
| 422 | 语义错误 | 参数类型正确但逻辑错误 |
| 429 | 请求过多 | 限流触发 |
| 500 | 服务器错误 | 内部异常，需记录日志 |
| 502 | 网关错误 | 下游服务不可用 |
| 503 | 服务不可用 | 维护中或过载 |

### 6.4 分页规范

```json
{
  "code": 200,
  "data": {
    "items": [ ... ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 1568,
      "total_pages": 79,
      "has_next": true,
      "has_prev": false
    }
  },
  "message": "success"
}
```

---

## 7. 文档规范

### 7.1 文档类型

| 文档 | 位置 | 更新时机 | 负责人 |
|------|------|---------|--------|
| 设计规约 | `AGENT.md` | 架构变更时 | 架构负责人 |
| 项目说明 | `README.md` | 功能变更时 | 项目负责人 |
| 系统架构 | `docs/系统设计文档.md` | 架构变更时 | 架构负责人 |
| 需求规格 | `docs/需求规格说明书.md` | 需求变更时 | 产品负责人 |
| 数据库设计 | `docs/数据库设计文档.md` | Schema 变更时 | 后端负责人 |
| API 文档 | `docs/API接口文档.md` | 接口变更时 | 后端负责人 |
| 前端设计 | `docs/前端设计文档.md` | UI 变更时 | 前端负责人 |
| 模型设计 | `docs/模型设计文档.md` | 算法变更时 | AI 负责人 |
| 部署文档 | `docs/部署运维文档.md` | 部署变更时 | 运维负责人 |
| 测试计划 | `docs/测试计划.md` | 测试策略变更时 | 测试负责人 |

### 7.2 文档格式

- 使用 Markdown 格式
- 使用 `##` 作为一级标题，`###` 作为二级标题
- 表格用于对比和枚举
- 代码块标注语言类型
- 图表优先使用 ASCII 或 Mermaid
- 版本号使用语义化版本

### 7.3 变更记录

每个文档底部必须包含变更记录：

```markdown
## 变更记录

| 版本 | 日期 | 作者 | 变更内容 |
|------|------|------|---------|
| v1.0 | 2026-07-07 | [你的名字] | 初始版本 |
| v1.1 | 2026-07-10 | [你的名字] | 增加 API 鉴权章节 |
```

---

## 8. 协作流程

### 8.1 Git 分支模型

**采用 GitHub Flow 简化模型：**

```
main (保护分支)
  ↑
feature/sentiment-engine  ← 新功能开发
  ↓
Pull Request → Code Review → Merge
```

**分支命名：**

| 前缀 | 用途 | 示例 |
|------|------|------|
| `feature/` | 新功能 | `feature/sentiment-engine` |
| `bugfix/` | 缺陷修复 | `bugfix/api-timeout` |
| `docs/` | 文档更新 | `docs/api-guide` |
| `refactor/` | 重构 | `refactor/db-schema` |
| `hotfix/` | 紧急修复 | `hotfix/memory-leak` |

### 8.2 提交规范

**遵循 Conventional Commits：**

```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型：**

| 类型 | 用途 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(api): add sentiment batch analyze endpoint` |
| `fix` | 缺陷修复 | `fix(crawler): resolve weibo anti-crawl detection` |
| `docs` | 文档 | `docs(readme): update deployment instructions` |
| `style` | 格式调整 | `style(frontend): fix lint errors` |
| `refactor` | 重构 | `refactor(engine): extract base analyzer class` |
| `test` | 测试 | `test(api): add sentiment endpoint unit tests` |
| `chore` | 构建/工具 | `chore(deps): update fastapi to 0.115.0` |
| `perf` | 性能优化 | `perf(db): add index on crawl_time column` |

### 8.3 代码审查规范

**审查清单：**

- [ ] 是否遵循 AGENT.md 设计规约
- [ ] 是否有类型注解
- [ ] 是否有文档字符串
- [ ] 是否有单元测试
- [ ] 是否引入新依赖（需审查许可证）
- [ ] 是否有潜在安全问题
- [ ] 是否有性能问题（N+1 查询、大数据量全表扫描等）
- [ ] 是否更新了相关文档

---

## 9. 技术债务管理

### 9.1 债务标记

```python
# 使用 TODO/FIXME/HACK 标记，必须包含日期和原因

# TODO(2026-08-01): 当前使用 requests 同步请求，
# 后续升级为 aiohttp 异步请求以提升并发性能
# 相关 Issue: #42

# FIXME(2026-07-15): 抖音爬虫因反爬升级频繁失败，
# 需要调研新的 Cookie 获取策略
# 优先级: P1

# HACK(2026-07-10): 临时绕过 B站 API 频率限制，
# 使用固定间隔 2 秒，后续接入动态代理池
```

### 9.2 债务追踪

所有技术债务必须在项目跟踪中记录（建议使用 GitHub Issues），包含：
- 问题描述
- 产生原因
- 影响范围
- 修复方案
- 预计修复时间
- 优先级（P0/P1/P2）

### 9.3 债务清偿

**每个 Sprint/阶段 必须清偿至少 1 个技术债务。** 禁止无限累积。

---

## 变更记录

| 版本 | 日期 | 作者 | 变更内容 |
|------|------|------|---------|
| v1.0 | 2026-07-07 | 码钉 | 初始版本，定义完整设计规约 |

---

> 本规约是项目的"宪法"。所有开发工作、代码提交、文档撰写都必须遵循。  
> 如需修改规约，须经项目负责人同意，并更新此文档的变更记录。
