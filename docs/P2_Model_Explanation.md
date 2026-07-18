# P2 模型解释系统落地

本阶段补齐 P2「模型解释系统」，将早期的确定性假实现替换为真实的扰动式解释，数据库继续使用现有 SQLite。

## 后端实现

- 新增 `ModelExplanationService`（`backend/app/services/model_explanation_service.py`），in-house 实现 LIME 核心思想，仅依赖 numpy，不引入 shap/lime 等重依赖：
  - 中文分词使用 jieba，token 去重保序，上限 32 个以控制扰动成本。
  - 扰动采样：全保留 + 逐 token 留一（leave-one-out）+ 随机掩码（固定随机种子 42，保证可复现），`n_samples` 默认 200，可在 20-1000 间调整。
  - 打分函数走 `model_registry_service.select_sentiment_model_version`：classic provider 用 `SentimentService.analyze_batch`，transformers provider 用 `get_analyzer()`（未装 torch 或模型未缓存时自动降级规则模式，两种路径均可解释）。
  - 贡献值拟合：按 LIME 余弦距离核加权 + 岭回归拟合局部线性代理，`contribution = beta_positive - beta_negative`，正值推向正面、负值推向负面，`direction` 取 positive/negative。
  - 生成中文 summary（如「判定为负面（置信度100.0%），主要贡献词：糟糕（负向）、失望（负向）」）。
- 解释结果持久化：`sentiment_result_id` 模式写入 `model_explanations`（method="lime"）与 `feature_contributions`（token、贡献值、重要性排名）；text 即时模式受 `sentiment_result_id NOT NULL` 外键约束不落库，返回 `persisted=false`。
- 聚类解释：`TopicClusteringService.detail_payload` 新增 `representative_members`，取距质心最近（distance_to_center 升序）的最多 5 个成员话题（id + 标题 + 距离 + 平台 + 热度），基于已持久化的成员距离计算，不改变既有 `members` 契约。
- 预测解释：`trend_forecast_service` 已持久化 `prediction_features`，详情接口已返回 `features`，前端「预测信号」面板已展示热度动量、负面压力、跨平台扩散等特征贡献及方向，本阶段确认无需改动。

## 接口变化

- `POST /api/v1/model-explanations/generate`（新增，需 analyst 及以上权限，写审计日志 `generate_model_explanation`）
  - 入参：`sentiment_result_id`（解释已入库结果）或 `text`（即时解释），`n_samples` 可选。
  - 返回：`method`、`model_version`、`summary`、`sentiment_label`、`confidence`、`scores`、`tokens`（token/contribution/direction/rank，按 |贡献| 降序）、`persisted`、`explanation_id`。
  - 未认证返回 401，visitor 角色返回 403；结果不存在返回 code 404；参数缺失返回 code 400。
- `POST /api/v1/model-explanations/explain/{sentiment_result_id}`（兼容旧入口）
  - 内部改走真实扰动解释服务，响应结构保持不变。
- `GET /api/v1/model-explanations` / `GET /api/v1/model-explanations/{id}`
  - 列表/详情响应契约不变。
- `GET /api/v1/topic-clusters/{id}`
  - 新增 `representative_members` 字段，其余契约不变。

## 前端展示

- 情感分析页「模型解释」子视图：单条分析结果旁（「最近一次结果」面板）新增「查看解释」入口，点击调用 generate 接口；解释面板展示 summary 文案与关键词贡献度横向条形图（正向绿 / 负向红，按 |贡献| 归一化条宽），并标注解释方法与模型版本。低置信度标红逻辑不变。
- 热点页「聚类主题」：簇详情「关键词与情感」面板新增「代表话题（距质心最近）」列表，展示话题标题、平台与质心距离。
- 趋势预测视图：特征贡献已通过「预测信号」面板展示（数据来自预测服务的 signals/features），未做改动。

## 验证

```powershell
python -m pytest backend\tests -q
pytest backend\tests\test_api.py::TestModelExplanation -q
cd frontend; npx tsc --noEmit
git diff --check
```

当前验证结果：

- `pytest backend\tests -q`：79 passed（基线 73 + 新增 TestModelExplanation 6 个）。
- `npx tsc --noEmit`：零错误。
- `git diff --check`：通过。
- 新增测试覆盖：text / sentiment_result_id 两种生成模式（主要贡献词方向与文本情感一致）、未认证 401、visitor 403、404/400 分支、列表/详情/审计回归、聚类 representative_members 升序与数量上限。

## 已知限制与下一步

- classic provider 的 `model_output/sklearn_model.pkl` 由 sklearn 1.9 序列化，与当前环境的 sklearn 1.4 不兼容，`SentimentService` 会降级为随机 mock，此时解释结果无意义；需用当前 sklearn 版本重训模型后解释才可信（transformers provider 的规则/模型路径不受影响）。
- text 即时解释不落库（外键约束），如需留存解释历史，可考虑为 model_explanations 增加可空外键迁移或独立的即时解释表。
- 贡献值基于局部线性代理，属近似解释；后续可在拟合中加入 R² 拟合优度指标并在前端展示解释可信度。
