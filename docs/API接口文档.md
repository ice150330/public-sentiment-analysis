# API 接口设计文档

> 基于 FastAPI + SQLite 方案A（极简版）  
> 版本: v1.1
> 日期: 2026-07-08

---

## 1. 接口设计原则

| 原则 | 说明 | 示例 |
|------|------|------|
| **RESTful** | 资源名用复数，动作用 HTTP 方法 | `GET /api/v1/topics` 查询热榜 |
| **版本控制** | URL 中包含版本号 | `/api/v1/...` |
| **统一响应** | 所有接口返回统一包装格式 | `{"code": 200, "data": ..., "message": "..."}` |
| **标准分页** | 列表接口支持分页 | `page` + `page_size` |
| **时间格式** | ISO 8601 格式 | `2026-07-07T14:30:00+08:00` |

---

## 2. 接口总览

### 2.1 基础接口清单

> 下表为项目初始基础接口。UI.pen 对应的增量接口已在 v1.1 补齐，详见第 5 节。当前 FastAPI OpenAPI 共注册 122 个 method operation。

| 模块 | 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|------|
| **平台管理** | 查询平台列表 | GET | `/api/v1/platforms` | 获取所有平台配置 |
| | 查询平台详情 | GET | `/api/v1/platforms/{id}` | 获取单个平台 |
| | 切换平台状态 | PATCH | `/api/v1/platforms/{id}` | 启用/禁用采集 |
| **热榜数据** | 查询热榜列表 | GET | `/api/v1/topics` | 分页查询热榜 |
| | 查询热榜详情 | GET | `/api/v1/topics/{id}` | 获取单条热榜详情 |
| | 按平台查询 | GET | `/api/v1/topics?platform=weibo` | 筛选特定平台 |
| | 按时间查询 | GET | `/api/v1/topics?start_time=...&end_time=...` | 时间范围筛选 |
| **情感分析** | 分析单条文本 | POST | `/api/v1/sentiment/analyze` | 对文本做情感分析 |
| | 查询分析结果 | GET | `/api/v1/sentiment/results` | 获取分析结果列表 |
| | 按标签筛选 | GET | `/api/v1/sentiment/results?label=positive` | 筛选正面/负面/中性 |
| **统计分析** | 情感分布统计 | GET | `/api/v1/stats/sentiment-distribution` | 各情感占比 |
| | 平台热度趋势 | GET | `/api/v1/stats/heat-trend` | 热度时间趋势 |
| | 采集成功率 | GET | `/api/v1/stats/crawl-success-rate` | 采集成功率统计 |
| | 数据概览 | GET | `/api/v1/stats/overview` | 今日数据总览 |
| **爬虫控制** | 手动触发采集 | POST | `/api/v1/crawler/trigger` | 手动启动爬虫 |
| | 查询采集状态 | GET | `/api/v1/crawler/status` | 查看当前采集状态 |
| | 查询采集日志 | GET | `/api/v1/crawler/logs` | 分页查询采集日志 |
| | 查询定时配置 | GET | `/api/v1/crawler/schedule` | 获取定时任务配置 |
| | 修改定时配置 | PUT | `/api/v1/crawler/schedule` | 修改采集间隔 |

---

## 3. 请求/响应模型

### 3.1 统一响应包装

```json
{
  "code": 200,
  "data": { ... },
  "message": "success",
  "request_id": "req_abc123def456",
  "timestamp": "2026-07-07T14:30:00+08:00"
}
```

**错误响应：**

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

### 3.2 分页模型

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

## 4. 接口详细定义

### 4.1 平台管理模块

#### 4.1.1 查询平台列表

```
GET /api/v1/platforms
```

**请求参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| is_active | boolean | 否 | null | 按状态筛选 |
| page | integer | 否 | 1 | 页码 |
| page_size | integer | 否 | 20 | 每页数量 |

**响应示例：**

```json
{
  "code": 200,
  "data": {
    "items": [
      {
        "id": 1,
        "name": "weibo",
        "display_name": "微博",
        "base_url": "https://weibo.com",
        "is_active": true,
        "sort_order": 1,
        "created_at": "2026-07-01T00:00:00+08:00"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 6,
      "total_pages": 1,
      "has_next": false,
      "has_prev": false
    }
  },
  "message": "success"
}
```

#### 4.1.2 切换平台状态

```
PATCH /api/v1/platforms/{id}
```

**请求体：**

```json
{
  "is_active": false
}
```

**响应：**

```json
{
  "code": 200,
  "data": {
    "id": 1,
    "name": "weibo",
    "is_active": false
  },
  "message": "Platform updated successfully"
}
```

---

### 4.2 热榜数据模块

#### 4.2.1 查询热榜列表

```
GET /api/v1/topics
```

**请求参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| platform | string | 否 | null | 平台名称: weibo/douyin/... |
| keyword | string | 否 | null | 标题关键词搜索 |
| start_time | string | 否 | null | 开始时间，ISO 8601 |
| end_time | string | 否 | null | 结束时间，ISO 8601 |
| category | string | 否 | null | 分类标签 |
| sort_by | string | 否 | "heat_score" | 排序字段: heat_score/crawl_time |
| sort_order | string | 否 | "desc" | 排序: asc/desc |
| page | integer | 否 | 1 | 页码 |
| page_size | integer | 否 | 20 | 每页数量，最大100 |

**响应示例：**

```json
{
  "code": 200,
  "data": {
    "items": [
      {
        "id": 1,
        "platform_id": 1,
        "platform_name": "微博",
        "topic_id": "K100001",
        "title": "某明星结婚",
        "url": "https://weibo.com/...",
        "heat_score": 5200000,
        "category": "娱乐",
        "content_summary": "某明星今日宣布结婚...",
        "crawl_time": "2026-07-07T14:00:00+08:00",
        "sentiment": {
          "label": "positive",
          "confidence": 0.92,
          "positive_score": 0.85,
          "negative_score": 0.05,
          "neutral_score": 0.10
        }
      }
    ],
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

**说明：** 响应中 `sentiment` 字段为关联查询，若尚未分析则为 `null`。

#### 4.2.2 查询热榜详情

```
GET /api/v1/topics/{id}
```

**响应：** 单条完整记录（含 raw_data 原始数据）。

---

### 4.3 情感分析模块

#### 4.3.1 分析单条文本

```
POST /api/v1/sentiment/analyze
```

**请求体：**

```json
{
  "text": "这个产品真的太棒了，非常好用！"
}
```

**响应示例：**

```json
{
  "code": 200,
  "data": {
    "text": "这个产品真的太棒了，非常好用！",
    "sentiment_label": "positive",
    "confidence": 0.95,
    "scores": {
      "positive": 0.93,
      "negative": 0.02,
      "neutral": 0.05
    },
    "model_version": "bert-base-chinese-v1",
    "analyzed_at": "2026-07-07T14:30:00+08:00"
  },
  "message": "success"
}
```

#### 4.3.2 批量分析

```
POST /api/v1/sentiment/analyze/batch
```

**请求体：**

```json
{
  "texts": [
    "这个产品太棒了！",
    "质量很差，不推荐。",
    "一般般，没什么感觉。"
  ]
}
```

**响应：** 返回列表，顺序与输入一致。

#### 4.3.3 查询分析结果

```
GET /api/v1/sentiment/results
```

**请求参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| label | string | 否 | null | 筛选: positive/negative/neutral |
| platform | string | 否 | null | 按平台筛选 |
| min_confidence | float | 否 | 0.0 | 最小置信度 |
| start_time | string | 否 | null | 开始时间 |
| end_time | string | 否 | null | 结束时间 |
| page | integer | 否 | 1 | 页码 |
| page_size | integer | 否 | 20 | 每页数量 |

---

### 4.4 统计分析模块

#### 4.4.1 情感分布统计

```
GET /api/v1/stats/sentiment-distribution
```

**请求参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| platform | string | 否 | null | 按平台筛选 |
| start_time | string | 否 | null | 开始时间 |
| end_time | string | 否 | null | 结束时间 |

**响应示例：**

```json
{
  "code": 200,
  "data": {
    "total": 1568,
    "distribution": [
      { "label": "positive", "count": 892, "percentage": 56.89 },
      { "label": "negative", "count": 312, "percentage": 19.90 },
      { "label": "neutral", "count": 364, "percentage": 23.21 }
    ],
    "by_platform": {
      "weibo": { "positive": 300, "negative": 100, "neutral": 150 },
      "douyin": { "positive": 200, "negative": 80, "neutral": 90 }
    }
  },
  "message": "success"
}
```

#### 4.4.2 平台热度趋势

```
GET /api/v1/stats/heat-trend
```

**请求参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| days | integer | 否 | 7 | 查询天数，1-365 |
| platform | string | 否 | null | 按平台筛选（不传则全部） |
| aggregation | string | 否 | "daily" | 聚合粒度: hourly/daily/weekly |

**响应示例：**

```json
{
  "code": 200,
  "data": {
    "period": "2026-07-01 ~ 2026-07-07",
    "aggregation": "daily",
    "series": [
      {
        "platform": "weibo",
        "data": [
          { "date": "2026-07-01", "avg_heat": 450000, "max_heat": 1200000, "topic_count": 50 },
          { "date": "2026-07-02", "avg_heat": 480000, "max_heat": 1500000, "topic_count": 52 }
        ]
      }
    ]
  },
  "message": "success"
}
```

#### 4.4.3 数据概览（Dashboard 用）

```
GET /api/v1/stats/overview
```

**响应示例：**

```json
{
  "code": 200,
  "data": {
    "today": {
      "total_topics": 1568,
      "active_platforms": 6,
      "sentiment_distribution": {
        "positive": 892,
        "negative": 312,
        "neutral": 364
      }
    },
    "crawler": {
      "last_run": "2026-07-07T14:00:00+08:00",
      "next_run": "2026-07-07T15:00:00+08:00",
      "today_success_rate": 98.5
    }
  },
  "message": "success"
}
```

---

### 4.5 爬虫控制模块

#### 4.5.1 手动触发采集

```
POST /api/v1/crawler/trigger
```

**请求体：**

```json
{
  "platforms": ["weibo", "douyin"],  // 不传则采集全部
  "is_async": true                      // true: 后台执行，false: 同步等待
}
```

**响应示例（异步）：**

```json
{
  "code": 202,
  "data": {
    "task_id": "task_abc123",
    "status": "running",
    "platforms": ["weibo", "douyin"],
    "started_at": "2026-07-07T14:30:00+08:00"
  },
  "message": "Crawler task started in background"
}
```

#### 4.5.2 查询采集状态

```
GET /api/v1/crawler/status
```

**响应示例：**

```json
{
  "code": 200,
  "data": {
    "is_running": true,
    "current_task": {
      "task_id": "task_abc123",
      "platforms": ["weibo"],
      "started_at": "2026-07-07T14:30:00+08:00",
      "elapsed_seconds": 45
    },
    "queue_length": 0
  },
  "message": "success"
}
```

#### 4.5.3 查询采集日志

```
GET /api/v1/crawler/logs
```

**请求参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| platform | string | 否 | null | 按平台筛选 |
| status | string | 否 | null | 按状态筛选: success/failed/partial |
| start_time | string | 否 | null | 开始时间 |
| end_time | string | 否 | null | 结束时间 |
| page | integer | 否 | 1 | 页码 |
| page_size | integer | 否 | 20 | 每页数量 |

**响应示例：**

```json
{
  "code": 200,
  "data": {
    "items": [
      {
        "id": 1,
        "platform_id": 1,
        "platform_name": "微博",
        "status": "success",
        "records_count": 50,
        "error_message": null,
        "started_at": "2026-07-07T14:00:00+08:00",
        "completed_at": "2026-07-07T14:02:30+08:00",
        "duration_seconds": 150
      }
    ],
    "pagination": { ... }
  },
  "message": "success"
}
```

#### 4.5.4 查询/修改定时配置

```
GET /api/v1/crawler/schedule
PUT /api/v1/crawler/schedule
```

**GET 响应：**

```json
{
  "code": 200,
  "data": {
    "interval_minutes": 60,
    "is_enabled": true,
    "next_run_time": "2026-07-07T15:00:00+08:00"
  },
  "message": "success"
}
```

**PUT 请求体：**

```json
{
  "interval_minutes": 30,
  "is_enabled": true
}
```

---

## 5. UI.pen 增量接口（v1.1）

### 5.1 增量接口分组

| 模块 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 通用 | GET | `/api/v1/sync/status` | 顶栏同步状态，包含最新数据时间、队列长度、活动任务 |
| 通用 | GET | `/api/v1/search` | 全局搜索，支持 `q/scope/page/page_size` |
| 总览 | GET | `/api/v1/dashboard/overview` | UI 看板聚合 KPI、昨日对比、采集和情感摘要 |
| 统计 | GET | `/api/v1/stats/kpi-deltas` | KPI 环比 |
| 统计 | GET | `/api/v1/stats/platform-distribution` | 平台话题量、情感量、热度占比 |
| 统计 | GET | `/api/v1/stats/platform-matrix` | 平台监测矩阵 |
| 平台 | GET | `/api/v1/platforms/monitoring` | 平台采集健康状态 |
| 平台 | GET | `/api/v1/platforms/monitoring/matrix` | 前端平台监测矩阵别名 |
| 平台 | GET | `/api/v1/platforms/monitoring/freshness` | 前端数据新鲜度别名 |
| 平台 | GET/PATCH | `/api/v1/platforms/{id}/config` | 平台请求配置、开关、抓取配置 |
| 预警 | GET | `/api/v1/alerts` | 预警事件队列别名 |
| 预警 | GET | `/api/v1/alerts/summary` | 未处理预警、级别分布、最近预警 |
| 预警 | GET/POST | `/api/v1/alerts/events` | 预警事件列表 |
| 预警 | GET/POST/PUT/PATCH/DELETE | `/api/v1/alerts/rules` | 前端预警规则管理路径 |
| 预警 | GET/POST/PUT/PATCH/DELETE | `/api/v1/alert-rules` | UI.pen 预警规则管理路径 |
| 数据质量 | GET | `/api/v1/data-quality/funnel` | 原始、清洗、去重、分析、展示漏斗 |
| 数据质量 | GET | `/api/v1/data-quality/checks` | 字段完整率、重复、异常热度、失败日志等检查项 |
| 数据质量 | GET | `/api/v1/data-quality/issues` | 数据质量问题列表 |
| 数据质量 | GET | `/api/v1/data-quality/summary` | 覆盖率、保留率、模型版本摘要 |
| 数据质量 | POST | `/api/v1/data-quality/run` | 手动执行质量检查 |
| 数据质量 | POST | `/api/v1/data/archive` | 非破坏式归档，生成 JSON 归档文件并写审计 |
| 热点 | GET | `/api/v1/topics/facets` | 分类、平台、情感筛选面板 |
| 热点 | GET | `/api/v1/topics/keywords/cloud` | 关键词云 |
| 热点 | GET | `/api/v1/topics/{id}/samples` | 话题样本 |
| 热点 | GET | `/api/v1/topics/{id}/related` | 关联话题 |
| 热点 | GET | `/api/v1/topics/{id}/propagation` | 传播节点和边 |
| 热点 | GET | `/api/v1/topics/propagation/strength` | 平台传播强度 |
| 热点 | GET | `/api/v1/topic-ext/{id}/samples` | 当前前端话题样本路径 |
| 热点 | GET | `/api/v1/topic-ext/{id}/related` | 当前前端关联话题路径 |
| 聚类 | GET/POST | `/api/v1/topic-clusters` | 主题聚类列表和运行入口 |
| 聚类 | GET | `/api/v1/topics/clusters` | UI.pen 主题簇地图 |
| 传播 | GET/POST | `/api/v1/propagation-paths` | 传播路径列表、详情、分析 |
| 分析 | GET | `/api/v1/sentiment/summary` | 今日分析、成功率、低置信、负向样本 |
| 分析 | GET/POST | `/api/v1/sentiment/jobs` | 情感分析任务队列 |
| 分析 | POST | `/api/v1/sentiment/jobs/{id}/retry` | 情感任务重试 |
| 分析 | GET | `/api/v1/sentiment/low-confidence` | 低置信复核列表 |
| 分析 | GET | `/api/v1/sentiment/trend` | 情感时间序列 |
| 分析 | POST | `/api/v1/sentiment/explain` | 文本解释性分析 |
| 预测 | POST | `/api/v1/forecast/heat` | 热度预测和置信区间 |
| 预测 | GET | `/api/v1/forecast/signals` | 热度、负面、跨平台扩散信号 |
| 预测 | GET | `/api/v1/forecast/scenarios` | 基准、风险、缓和情景 |
| 模型 | GET | `/api/v1/models/current` | 当前模型信息 |
| 模型 | GET | `/api/v1/models/{version}/metrics` | 模型评估指标和混淆矩阵 |
| 模型 | GET | `/api/v1/model/status` | 当前前端模型状态路径 |
| 模型 | GET | `/api/v1/model/versions` | 模型版本列表 |
| 模型解释 | GET/POST | `/api/v1/model-explanations` | 解释列表、详情、生成解释 |
| 采集任务 | GET | `/api/v1/crawler/tasks/summary` | 运行中、队列、完成、失败、平均耗时 |
| 采集任务 | GET | `/api/v1/crawler/tasks/{id}` | 任务详情和事件 |
| 采集任务 | POST | `/api/v1/crawler/tasks/{id}/retry` | 重试任务 |
| 采集任务 | POST | `/api/v1/crawler/tasks/{id}/pause` | 暂停任务 |
| 采集任务 | POST | `/api/v1/crawler/tasks/{id}/resume` | 恢复任务 |
| 采集任务 | POST | `/api/v1/crawler/tasks/{id}/cancel` | 取消任务 |
| 采集任务 | GET | `/api/v1/crawler/timeline` | 历史任务和采集日志时间线 |
| 系统 | GET | `/api/v1/system/health` | API、数据库、调度器、模型、爬虫健康 |
| 系统 | GET/POST | `/api/v1/system/logs` | 系统日志 |
| 系统 | GET/POST | `/api/v1/system/audit-logs` | 当前前端审计日志路径 |
| 系统 | GET | `/api/v1/audit-logs` | UI.pen 审计日志路径 |
| 系统 | GET | `/api/v1/system/errors/{id}` | 错误详情和重试建议 |

### 5.2 代表性请求/响应示例

**同步状态**

```
GET /api/v1/sync/status
```

```json
{
  "code": 200,
  "data": {
    "last_updated": "2026-07-08T15:30:04.084070",
    "sync_delay_seconds": 18,
    "is_syncing": false,
    "queue_length": 0,
    "active_task": null,
    "modules": {
      "hot_topics": { "last_updated": "2026-07-08T16:03:23.864941", "count": 419 },
      "sentiment": { "last_updated": "2026-07-08T16:04:28.237470", "count": 419 },
      "crawler": { "last_updated": "2026-07-08T15:30:04.084070", "today_count": 14 }
    }
  },
  "message": "success"
}
```

**采集任务详情**

```
GET /api/v1/crawler/tasks/current
```

```json
{
  "code": 200,
  "data": {
    "task_id": "current",
    "status": "idle",
    "progress": 0,
    "events": []
  },
  "message": "success"
}
```

**情感任务**

```
POST /api/v1/sentiment/jobs
Content-Type: application/json

{ "texts": ["这个话题值得关注", "风险需要持续跟踪"] }
```

```json
{
  "code": 200,
  "data": {
    "job_id": "sentiment_20260708153000000000",
    "status": "completed",
    "total_count": 2,
    "success_count": 2,
    "failed_count": 0,
    "avg_latency_ms": 0
  },
  "message": "Job completed"
}
```

**数据归档**

```
POST /api/v1/data/archive
Content-Type: application/json

{ "retention_days": 3650 }
```

```json
{
  "code": 200,
  "data": {
    "archive_id": "archive_20260708153000000000",
    "status": "completed",
    "archived_count": 0,
    "retention_days": 3650,
    "archive_path": "backend/data/archives/archive_20260708153000000000.json"
  },
  "message": "Archive completed"
}
```

---

## 6. 状态码说明

| 状态码 | 含义 | 使用场景 |
|--------|------|---------|
| 200 | 成功 | 标准成功响应 |
| 202 | 已接受 | 异步任务已提交（如爬虫触发） |
| 400 | 请求参数错误 | 参数校验失败 |
| 404 | 资源不存在 | 查询的 ID 不存在 |
| 422 | 语义错误 | 参数类型正确但逻辑错误 |
| 429 | 请求过多 | 限流触发 |
| 500 | 服务器错误 | 内部异常 |

---

## 7. 接口路径汇总

```
# 平台管理
GET    /api/v1/platforms
GET    /api/v1/platforms/{id}
PATCH  /api/v1/platforms/{id}

# 热榜数据
GET    /api/v1/topics
GET    /api/v1/topics/{id}

# 情感分析
POST   /api/v1/sentiment/analyze
POST   /api/v1/sentiment/analyze/batch
GET    /api/v1/sentiment/results

# 统计分析
GET    /api/v1/stats/sentiment-distribution
GET    /api/v1/stats/heat-trend
GET    /api/v1/stats/crawl-success-rate
GET    /api/v1/stats/overview

# 爬虫控制
POST   /api/v1/crawler/trigger
GET    /api/v1/crawler/status
GET    /api/v1/crawler/logs
GET    /api/v1/crawler/schedule
PUT    /api/v1/crawler/schedule
```

**总计:** 基础接口 18 个；当前 OpenAPI 注册 122 个 method operation，包含 UI.pen 增量能力。

---

## 8. 变更记录

| 版本 | 日期 | 作者 | 变更内容 |
|------|------|------|---------|
| v1.1 | 2026-07-08 | Codex | 补充 UI.pen 增量接口分组、任务/质量/预警/模型/系统等接口示例 |
| v1.0 | 2026-07-07 | 码钉 | 初始版本，18个接口完整定义 |

---

> 本 API 文档可直接用于前端对接，每个接口均包含请求/响应示例。  
> FastAPI 将自动根据 Pydantic 模型生成 Swagger 文档，路径: `/docs`。
