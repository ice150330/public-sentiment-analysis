# P2 趋势预测模型落地

本阶段补齐 P2「趋势预测模型」的可运行闭环，数据库继续使用现有 SQLite。

## 后端实现

- 新增 `TrendForecastService`，统一服务 `/trend-predictions` 与前端兼容 `/forecast/*` 接口。
- 历史序列来自 SQLite 中的 `hot_topics` 与 `sentiment_results`：
  - `heat`：按日聚合热度；指定话题时优先匹配同平台 `topic_id`，不足时回退同标题。
  - `sentiment`：按日聚合正向健康分，并保留负向占比。
  - `volume`：按日统计话题量，用于扩散信号。
- 预测策略优先使用 `statsmodels` ARIMA；数据点不足、依赖缺失或拟合失败时自动回退 EMA。
- 预测结果持久化到 `trend_predictions`，`params_json` 保存历史点、预测曲线、回测指标。
- `prediction_features` 保存特征贡献：近期趋势、波动率、话题量变化、负向动量、平台多样性。

## 接口变化

- `POST /api/v1/trend-predictions/predict`
  - 返回 `forecast`、`history`、`metrics`、`features`。
  - `model` 可能为 `arima`、`ema` 或 `baseline`。
- `GET /api/v1/trend-predictions/{id}`
  - 返回完整预测详情、回测指标和特征贡献。
- `POST /api/v1/forecast/heat`
  - 前端兼容接口已改用同一预测服务，返回置信区间、模型名、回测指标和预测信号。
- `GET /api/v1/forecast/signals`
  - 返回热度动量、负面压力、跨平台扩散信号。
- `GET /api/v1/forecast/scenarios`
  - 基于信号生成 baseline / risk / ease 场景概率。

## 前端展示

情感分析页「趋势预测」子视图已展示：

- 预测热度折线与上下置信区间。
- 当前热度、预测模型、回测 MAE、回测 MAPE。
- 热度动量、负面压力、跨平台扩散等预测信号。

## 验证

```powershell
python -m compileall backend\app backend\tests
pytest backend\tests\test_api.py::TestTrendForecastEndpoints -q
pytest backend\tests -q
npm run build
git diff --check
```

当前验证结果：

- `pytest backend\tests -q`：73 passed。
- `npm run build`：Compiled successfully。
- `git diff --check`：通过，仅有 Windows LF/CRLF 提示。
