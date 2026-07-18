# P1 遗留增强与修复

## 已修复：情感分析经典模型降级为随机 mock 的问题

### 问题

`backend/app/services/sentiment_service.py` 的 `_mock_analyze` 使用 `random.choice` 随机返回 positive/negative/neutral：

- 当 `model_output/sklearn_model.pkl` 与当前环境 scikit-learn 版本不兼容（当前环境 1.4.2，模型由 1.9.0 序列化）时，模型预测抛 `NotFittedError`。
- 服务捕获异常后回退到 `_mock_analyze`，导致**默认经典链路的情感标签是随机数**。
- 历史 13k+ 情感分析结果可能受此污染。

### 修复

- 移除所有 `random` 依赖，删除 `_mock_analyze`。
- 新增 `_rule_fallback`：基于 jieba 分词 + 内置轻量正负面词库，确定性计算情感标签与分数。
- 兜底模型版本从 `mock-v1` 改为 `rule-fallback-v1`。
- `analyze_unprocessed_topics` 保存结果时使用实际模型版本，不再硬编码 `sklearn-v1`。

### 影响

- 情感分析结果现在稳定可复现。
- 建议后续在 torch 环境修复后启用 transformers provider；或重新训练 sklearn 模型并更新文件。

## 验证

```bash
python -m pytest backend\tests\test_api.py::TestSentimentEndpoints -q
python -m pytest backend\tests -q
cd frontend && npx tsc --noEmit
git diff --check
```

当前结果：

- `pytest backend\tests -q`：**86 passed**。
- `npx tsc --noEmit`：零错误。
- `git diff --check`：通过。

## 仍剩余（可选）

- 聚类对比：不同时间窗口的主题簇演变视图（路线图 P1.2 下一步）。
- 真实 transformers 推理：依赖本机 torch DLL 问题修复。
