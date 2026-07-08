# UI.pen 后端功能映射清单

> 生成日期：2026-07-08  
> 补齐复核：2026-07-08
> 来源：`pen/UI.pen` 当前画板结构、`frontend/src` 页面实现、`backend/app/api/v1` 现有 FastAPI 路由、`docs/API接口文档.md`

> 注：本轮复核时 Pencil 编辑器未打开 `UI.pen`，无法直接读取画板；以下状态以本清单、当前 React 前端 API 调用和 FastAPI OpenAPI 为对照依据。前端 `frontend/src/services/api.ts` 中 57 个实际请求方法均已匹配到后端 OpenAPI，本文中标记为“已补齐”的能力均有对应 `/api/v1` 路由。

## 1. 目的

本文档用于把 `UI.pen` 中已经设计出来的前端功能，拆解为后端需要提供的接口、数据模型和服务能力，方便后续按模块迭代。

当前 UI 不是只覆盖现有 React 页面，而是包含更完整的产品形态：

| 一级模块 | UI.pen 子页面 |
|---|---|
| 总览 | 实时概览、平台监测、预警中心、数据质量、移动端总览 |
| 热点 | 热榜列表、聚类主题、传播路径、话题详情 |
| 分析 | 文本分析、批量结果、趋势预测、模型解释 |
| 管理 | 平台配置、采集任务、预警规则、系统日志 |

## 2. 当前后端已有能力

| 模块 | 已有接口 | UI 支持度 | 说明 |
|---|---|---|---|
| 平台管理 | `GET /api/v1/platforms`、`GET /api/v1/platforms/{id}`、`PATCH /api/v1/platforms/{id}`、`GET/PATCH /api/v1/platforms/{id}/config` | 已补齐 | 已覆盖平台列表、启停、平台健康、请求配置、采集配置详情 |
| 热榜数据 | `GET /api/v1/topics`、`GET /api/v1/topics/{id}`、`GET /api/v1/topics/{id}/samples`、`GET /api/v1/topics/{id}/propagation` | 已补齐 | 已覆盖列表、搜索、分页、情感联表、关键词、样本、传播、关联话题 |
| 情感分析 | `POST /api/v1/sentiment/analyze`、`POST /api/v1/sentiment/analyze/batch`、`GET /api/v1/sentiment/results`、`GET/POST /api/v1/sentiment/jobs` | 已补齐 | 已覆盖单条/批量分析、任务队列、低置信复核、解释性、模型评估 |
| 统计分析 | `GET /api/v1/stats/overview`、`/sentiment-distribution`、`/heat-trend`、`/crawl-success-rate`、`/platform-matrix` | 已补齐 | 已覆盖基础看板、昨日对比、平台监测矩阵、数据质量漏斗、预警统计 |
| 爬虫控制 | `POST /api/v1/crawler/trigger`、`GET /api/v1/crawler/status`、`GET /api/v1/crawler/logs`、`GET/PUT /api/v1/crawler/schedule`、`/crawler/tasks/*` | 已补齐 | 已覆盖触发、状态、日志、定时配置、任务队列、进度、暂停、重试、时间线 |

## 3. 通用后端能力

| 功能 | UI 入口 | 建议接口 | 状态 | 优先级 |
|---|---|---|---|---|
| 顶栏同步状态 | 所有桌面页显示“同步 46s” | `GET /api/v1/sync/status` 或复用各模块响应中的 `last_updated` | 已补齐 | P1 |
| 全局搜索 | 顶栏“搜索关键词” | `GET /api/v1/search?q=&scope=` | 已补齐 | P2 |
| 刷新数据 | 顶栏“刷新数据” | 各模块现有查询接口即可；建议统一返回 `timestamp` | 已补齐 | P0 |
| 统一分页 | 热榜、日志、情感结果、预警队列 | 所有列表统一返回 `{ items, pagination }` | 已补齐 | P0 |
| 统一筛选参数 | 平台、时间范围、关键词、状态、级别 | `platform/start_time/end_time/keyword/status/page/page_size` | 已补齐 | P0 |

## 4. 总览模块

### 4.1 实时概览

| UI 功能 | 后端能力 | 建议接口 | 状态 | 优先级 |
|---|---|---|---|---|
| 今日话题、活跃平台、负面占比、采集成功率 | 看板 KPI 聚合，支持昨日对比 | `GET /api/v1/dashboard/overview` 或扩展 `/stats/overview` | 已补齐 | P0 |
| 较昨日变化 | 按日环比计算 | `GET /api/v1/stats/kpi-deltas?date=` | 已补齐 | P1 |
| 热度与情感趋势 | 热度趋势 + 情感趋势双轴 | 扩展 `GET /api/v1/stats/heat-trend`，新增情感时间序列 | 已补齐 | P1 |
| 情感分布 | 正/中/负数量和占比 | `GET /api/v1/stats/sentiment-distribution` | 已支持 | P0 |
| 平台分布 | 各平台话题量/情感量/热度占比 | `GET /api/v1/stats/platform-distribution` | 已补齐 | P1 |
| 实时热榜 | 最新热榜、情感标签、置信度 | 扩展 `GET /api/v1/topics` 返回 `sentiment` | 已补齐 | P0 |
| 预警摘要 | 未处理预警数量、最高等级、最近预警 | `GET /api/v1/alerts/summary` | 已补齐 | P1 |
| 采集状态 | 最近各平台采集状态、下次采集时间 | 扩展 `/crawler/status` + `/crawler/schedule` | 已补齐 | P0 |

### 4.2 平台监测

| UI 功能 | 后端能力 | 建议接口 | 状态 | 优先级 |
|---|---|---|---|---|
| 六平台采集状态 | 平台状态、最近采集记录数、成功/失败 | `GET /api/v1/platforms/monitoring` | 已补齐 | P1 |
| 采集成功率趋势 | 按平台、按时间统计成功率 | `GET /api/v1/stats/crawl-success-rate?group_by=platform` | 已补齐 | P1 |
| 平台对比矩阵 | 话题数、平均热度、负面占比、延迟、状态 | `GET /api/v1/stats/platform-matrix` | 已补齐 | P1 |
| 数据新鲜度与缺口 | 最新采集时间、延迟分钟数、缺口状态 | `GET /api/v1/data-quality/freshness` | 已补齐 | P1 |

### 4.3 预警中心

| UI 功能 | 后端能力 | 建议接口 | 状态 | 优先级 |
|---|---|---|---|---|
| 预警队列 | 按级别、状态、平台、时间筛选预警 | `GET /api/v1/alerts` | 已补齐 | P1 |
| 严重程度分布 | P1/P2/P3/P4 统计 | `GET /api/v1/alerts/summary` | 已补齐 | P1 |
| 预警详情预览 | 触发规则、负面占比、热度增幅、平台数 | `GET /api/v1/alerts/{id}` | 已补齐 | P1 |
| 处理预警 | 确认、下钻、记录处理结果 | `POST /api/v1/alerts/{id}/ack`、`POST /api/v1/alerts/{id}/resolve` | 已补齐 | P1 |
| 处置记录 | 人工处理日志 | `GET /api/v1/alerts/{id}/actions` | 已补齐 | P2 |

### 4.4 数据质量

| UI 功能 | 后端能力 | 建议接口 | 状态 | 优先级 |
|---|---|---|---|---|
| 数据处理漏斗 | 原始采集、清洗后、去重后、已分析、入库展示 | `GET /api/v1/data-quality/funnel` | 已补齐 | P1 |
| 质量检查项 | 字段完整率、重复话题、异常热度、空摘要、失败日志、时间漂移 | `GET /api/v1/data-quality/checks` | 已补齐 | P1 |
| 待处理问题 | 问题列表、平台、类型、建议处理 | `GET /api/v1/data-quality/issues` | 已补齐 | P1 |
| 覆盖与保留 | 平台覆盖、数据保留、分页、文本长度、模型版本 | `GET /api/v1/data-quality/summary` | 已补齐 | P2 |

## 5. 热点模块

### 5.1 热榜列表

| UI 功能 | 后端能力 | 建议接口 | 状态 | 优先级 |
|---|---|---|---|---|
| 关键词、平台、日期、7/30 天筛选 | 热榜检索、分页、排序 | 扩展 `GET /api/v1/topics` | 已支持 | P0 |
| 分类统计标签 | 全部、科技、社会、娱乐、财经等 facet | `GET /api/v1/topics/facets` | 已补齐 | P1 |
| 跨平台重复、新增话题、负面高危 | 话题标签/风险标记 | 扩展 `topics` 响应字段 | 已补齐 | P1 |
| 热榜行情感标签 | 话题关联最新情感结果 | 扩展 `topics` 联表返回 `sentiment` | 已补齐 | P0 |
| 平台占比 | 当前筛选条件下平台分布 | `GET /api/v1/stats/platform-distribution` | 已补齐 | P1 |
| 关键词云 | 关键词抽取与频次 | `GET /api/v1/topics/keywords/cloud` | 已补齐 | P2 |
| 详情抽屉 | 话题详情、情感概率、平台扩散、采集来源 | 扩展 `GET /api/v1/topics/{id}` | 已补齐 | P0 |

### 5.2 聚类主题

| UI 功能 | 后端能力 | 建议接口 | 状态 | 优先级 |
|---|---|---|---|---|
| 聚类主题地图 | 主题簇、话题数、主情感、关键词 | `GET /api/v1/topics/clusters` | 已补齐 | P2 |
| 主题关键词矩阵 | 每个簇关键词权重 | `GET /api/v1/topics/clusters/{id}/keywords` | 已补齐 | P2 |
| 主题内话题 | 簇内话题列表 | `GET /api/v1/topics/clusters/{id}/topics` | 已补齐 | P2 |

### 5.3 传播路径

| UI 功能 | 后端能力 | 建议接口 | 状态 | 优先级 |
|---|---|---|---|---|
| 跨平台传播路径 | 传播节点、时间偏移、平台、事件类型 | `GET /api/v1/topics/{id}/propagation` | 已补齐 | P2 |
| 传播跳点 | 平台间边、关联话题数、说明 | 同上，返回 `edges` | 已补齐 | P2 |
| 平台关联强度 | 平台对之间的强度分数 | `GET /api/v1/topics/propagation/strength` | 已补齐 | P2 |

### 5.4 话题详情

| UI 功能 | 后端能力 | 建议接口 | 状态 | 优先级 |
|---|---|---|---|---|
| 基础详情 | 标题、平台、分类、热度、URL、摘要、原始字段 | `GET /api/v1/topics/{id}` | 已补齐 | P0 |
| 证据与样本 | 微博/知乎/B站/百度样本和样本情感 | `GET /api/v1/topics/{id}/samples` | 已补齐 | P1 |
| 关联话题 | 同主题、热度联动、评论聚集、数据缺口 | `GET /api/v1/topics/{id}/related` | 已补齐 | P2 |
| 平台数、排名、负面概率 | 聚合指标 | 扩展 `topics/{id}` | 已补齐 | P1 |

## 6. 分析模块

### 6.1 文本分析

| UI 功能 | 后端能力 | 建议接口 | 状态 | 优先级 |
|---|---|---|---|---|
| 单条文本分析 | 中文三分类、置信度、三类分数、模型版本 | `POST /api/v1/sentiment/analyze` | 已支持 | P0 |
| 批量导入 | 多文本同步分析 | `POST /api/v1/sentiment/analyze/batch` | 已支持 | P0 |
| 模型状态 | 当前模型、任务类型、设备、准确率目标、平均耗时 | `GET /api/v1/models/current` | 已补齐 | P1 |
| 情感分数趋势 | 情感概率/数量时间序列 | `GET /api/v1/sentiment/trend` | 已补齐 | P1 |
| 平台情绪对比 | 按平台情感占比 | `GET /api/v1/stats/sentiment-distribution?group_by=platform` | 已补齐 | P1 |
| 分析结果列表 | 文本/话题、平台、情感、置信度、时间 | 扩展 `GET /api/v1/sentiment/results` | 已补齐 | P0 |

### 6.2 批量结果

| UI 功能 | 后端能力 | 建议接口 | 状态 | 优先级 |
|---|---|---|---|---|
| 今日分析、成功率、低置信、负向样本、平均耗时 | 分析任务和结果统计 | `GET /api/v1/sentiment/summary` | 已补齐 | P1 |
| 队列长度、当前任务、失败重试 | 异步分析任务队列 | `GET /api/v1/sentiment/jobs`、`GET /api/v1/sentiment/jobs/{id}` | 已补齐 | P2 |
| 低置信复核 | 低置信样本列表、人工复核建议 | `GET /api/v1/sentiment/low-confidence` | 已补齐 | P1 |
| 失败重试 | 失败项重试 | `POST /api/v1/sentiment/jobs/{id}/retry` | 已补齐 | P2 |

### 6.3 趋势预测

| UI 功能 | 后端能力 | 建议接口 | 状态 | 优先级 |
|---|---|---|---|---|
| 热度趋势预测 | 3/7/14 天预测、置信区间、回测 MAPE | `POST /api/v1/forecast/heat` | 已补齐 | P2 |
| 预测信号 | 热度动量、负面情绪动量、跨平台扩散、搜索指数、评论增长 | `GET /api/v1/forecast/signals?topic_id=` | 已补齐 | P2 |
| 情景判断 | 基准/风险/缓和情景 | `GET /api/v1/forecast/scenarios?topic_id=` | 已补齐 | P2 |

### 6.4 模型解释

| UI 功能 | 后端能力 | 建议接口 | 状态 | 优先级 |
|---|---|---|---|---|
| 模型与评估信息 | 模型名称、版本、任务、训练数据、设备、准确率 | `GET /api/v1/models/current` | 已补齐 | P1 |
| 混淆矩阵、评估指标 | 模型评估结果 | `GET /api/v1/models/{version}/metrics` | 已补齐 | P2 |
| 词级贡献解释 | 关键词贡献、正负向证据 | `POST /api/v1/sentiment/explain` 或 `GET /api/v1/sentiment/results/{id}/explanation` | 已补齐 | P2 |
| 人工复核条件 | 置信度阈值、P1 预警联动 | 配置项 + 预警规则 | 已补齐 | P1 |

## 7. 管理模块

### 7.1 平台配置

| UI 功能 | 后端能力 | 建议接口 | 状态 | 优先级 |
|---|---|---|---|---|
| 平台开关 | 启用/禁用采集 | `PATCH /api/v1/platforms/{id}` | 已支持 | P0 |
| 定时配置 | 采集间隔、下次运行、保存配置 | `GET/PUT /api/v1/crawler/schedule` | 已补齐 | P0 |
| 平台配置详情 | base_url、请求配置、headers/cookie 状态、频率限制 | `GET /api/v1/platforms/{id}/config`、`PATCH /api/v1/platforms/{id}/config` | 已补齐 | P1 |
| 爬虫状态卡片 | 任务 ID、平台、已运行、队列、进度 | 扩展 `GET /api/v1/crawler/status` | 已补齐 | P0 |
| 重试任务 | 对失败平台/任务重试 | `POST /api/v1/crawler/tasks/{id}/retry` | 已补齐 | P1 |
| 系统健康 | API、数据库、调度器、模型、爬虫状态 | `GET /api/v1/system/health` | 已补齐 | P1 |

### 7.2 采集任务

| UI 功能 | 后端能力 | 建议接口 | 状态 | 优先级 |
|---|---|---|---|---|
| 运行中、队列、成功/失败、平均耗时、下次运行 | 采集任务统计 | `GET /api/v1/crawler/tasks/summary` | 已补齐 | P1 |
| 当前任务进度 | task 进度百分比、当前平台、耗时 | `GET /api/v1/crawler/tasks/{id}` | 已补齐 | P1 |
| 采集全部 | 启动全平台任务 | `POST /api/v1/crawler/trigger` | 已支持 | P0 |
| 暂停/恢复/取消 | 任务控制 | `POST /api/v1/crawler/tasks/{id}/pause`、`/resume`、`/cancel` | 已补齐 | P2 |
| 调度时间线 | 历史任务和未来计划 | `GET /api/v1/crawler/timeline` | 已补齐 | P1 |
| 质量检查、数据归档 | 后处理任务 | `POST /api/v1/data-quality/run`、`POST /api/v1/data/archive` | 已补齐 | P2 |
| 请求配置 | 平台请求参数、限流、重试策略 | `GET/PATCH /api/v1/platforms/{id}/config` | 已补齐 | P1 |

### 7.3 预警规则

| UI 功能 | 后端能力 | 建议接口 | 状态 | 优先级 |
|---|---|---|---|---|
| 规则列表 | 规则名称、等级、启停、条件 | `GET /api/v1/alert-rules` | 已补齐 | P1 |
| 规则编辑器 | 创建/更新阈值、适用平台、冷却时间、处理方式 | `POST /api/v1/alert-rules`、`PUT /api/v1/alert-rules/{id}` | 已补齐 | P1 |
| 启停规则 | 单独启用/停用 | `PATCH /api/v1/alert-rules/{id}` | 已补齐 | P1 |
| 规则模拟 | 样本数、命中数、误报估计、召回目标 | `POST /api/v1/alert-rules/{id}/simulate` | 已补齐 | P2 |
| 触发历史 | 规则命中日志 | `GET /api/v1/alert-rules/{id}/history` | 已补齐 | P2 |

### 7.4 系统日志

| UI 功能 | 后端能力 | 建议接口 | 状态 | 优先级 |
|---|---|---|---|---|
| 系统日志与审计 | 时间、级别、模块、事件、请求参数 | `GET /api/v1/system/logs` | 已补齐 | P1 |
| 运行健康 | API、DB、调度器、爬虫、模型状态 | `GET /api/v1/system/health` | 已补齐 | P1 |
| 配置变更审计 | 平台开关、规则修改、调度配置变更 | `GET /api/v1/audit-logs` | 已补齐 | P1 |
| 错误详情 | 异常类型、上下文、重试策略、建议 | `GET /api/v1/system/errors/{id}` | 已补齐 | P2 |

## 8. 建议新增数据模型

| 模型 | 作用 | 关键字段 |
|---|---|---|
| `alert_rules` | 预警规则配置 | `name`、`condition_expr`、`severity`、`platform_scope`、`cooldown_minutes`、`is_active` |
| `alert_events` | 预警事件队列 | `rule_id`、`topic_id`、`severity`、`status`、`trigger_payload`、`triggered_at`、`resolved_at` |
| `alert_actions` | 预警处置记录 | `alert_id`、`action_type`、`operator`、`note`、`created_at` |
| `topic_clusters` | 聚类主题 | `name`、`category`、`keywords`、`main_sentiment`、`topic_count`、`generated_at` |
| `topic_cluster_members` | 主题簇成员 | `cluster_id`、`topic_id`、`score` |
| `topic_samples` | 话题证据样本 | `topic_id`、`platform_id`、`sample_type`、`content`、`sentiment_label`、`confidence`、`source_url` |
| `topic_relations` | 关联话题 | `source_topic_id`、`target_topic_id`、`relation_type`、`score` |
| `propagation_edges` | 传播路径 | `topic_id`、`from_platform_id`、`to_platform_id`、`event_time`、`lag_minutes`、`strength`、`description` |
| `data_quality_runs` | 质量检查批次 | `run_type`、`started_at`、`completed_at`、`summary_json` |
| `data_quality_issues` | 数据质量问题 | `issue_type`、`platform_id`、`topic_id`、`severity`、`status`、`suggestion` |
| `crawler_tasks` | 采集任务 | `task_id`、`status`、`progress`、`platforms_json`、`started_at`、`completed_at` |
| `crawler_task_events` | 采集任务事件 | `task_id`、`event_type`、`message`、`created_at` |
| `sentiment_jobs` | 异步分析任务 | `job_id`、`status`、`total_count`、`success_count`、`failed_count`、`avg_latency_ms` |
| `sentiment_explanations` | 模型解释 | `sentiment_result_id`、`tokens_json`、`explanation_text`、`method` |
| `model_versions` | 模型版本 | `version`、`model_name`、`task_type`、`device`、`metrics_json`、`is_active` |
| `system_logs` | 系统日志 | `level`、`module`、`event`、`payload_json`、`request_id`、`created_at` |
| `audit_logs` | 操作审计 | `operator`、`action`、`target_type`、`target_id`、`before_json`、`after_json`、`created_at` |

## 9. 迭代优先级建议

### P0：补齐当前页面真实数据闭环

- 扩展 `GET /api/v1/topics` 和 `GET /api/v1/topics/{id}`，返回情感标签、置信度、排名、平台名、基础聚合指标。
- 统一列表响应分页格式，至少覆盖 `sentiment/results` 和 `crawler/logs`。
- 扩展 `/stats/overview`，补充负面占比、昨日对比、下次采集时间。
- 扩展 `/crawler/status`，补充 `progress`、当前平台、队列长度真实值。
- 修正实现细节风险：`backend/app/api/v1/topics.py` 中 `HTTPException` 被使用但未导入。

### P1：支撑 UI.pen 中明显的一线业务功能

- 新增预警事件和预警规则模块：`alerts`、`alert-rules`。
- 新增平台监测矩阵和数据新鲜度接口。
- 新增数据质量漏斗、质量检查项、待处理问题接口。
- 新增话题样本和关联话题接口。
- 新增系统健康、系统日志、审计日志接口。
- 新增模型当前状态、分析统计、低置信复核接口。

### P2：支撑高级分析和展示能力

- 新增主题聚类、关键词矩阵、关键词云。
- 新增跨平台传播路径、传播强度。
- 新增热度预测、预测信号、情景判断。
- 新增词级贡献解释、模型评估矩阵、异步批处理任务队列。
- 新增采集任务暂停/恢复/取消、数据归档、质量检查任务化。

## 10. API 命名建议

建议保持现有 `/api/v1` 风格，不把所有功能塞进 `stats`：

```text
/api/v1/dashboard/*
/api/v1/topics/*
/api/v1/sentiment/*
/api/v1/forecast/*
/api/v1/models/*
/api/v1/alerts/*
/api/v1/alert-rules/*
/api/v1/data-quality/*
/api/v1/crawler/*
/api/v1/system/*
/api/v1/audit-logs
```

## 11. 后续验收标准

- UI.pen 中每个真实数据区域都有明确接口来源，前端不再依赖静态占位数据。
- 列表类接口全部支持分页、筛选、排序，并返回统一响应结构。
- 所有“处理/编辑/启停/重试/保存配置”操作都有对应写接口和审计记录。
- 统计接口返回 `period`、`last_updated` 或 `timestamp`，支撑顶栏同步状态。
- 新增接口在 `docs/API接口文档.md` 中补充请求/响应示例。
- 每个新增接口至少有 1 个正常用例和 1 个错误/空数据用例测试。
