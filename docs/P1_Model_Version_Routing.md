# P1 模型版本管理与灰度路由

本阶段补齐 P1「模型版本管理（A/B 测试、灰度发布）」的可运行闭环，数据库继续使用现有 SQLite。

## 后端

- 新增默认模型版本种子：`classic-v1` 和 `transformers-v2`。
- `GET /api/v1/model/versions` 会返回版本、provider、流量比例、指标和激活状态。
- `GET /api/v1/model/status` 会返回当前主版本、活跃版本列表、24 小时分析量、平均置信度和待复核数量。
- `POST /api/v1/model/versions/{version_id}/activate` 支持管理员切换主版本或设置灰度流量比例，并写入审计日志。
- `POST /api/v1/sentiment/analyze` 与 `/api/v1/sentiment/analyze/batch` 默认跟随当前激活版本；`classic` 走原有本地服务，`transformers` 走增强模型兜底链路。

## 前端

情感分析页新增「模型版本」子视图：

- 表格展示版本、模型名称、provider、流量比例和启停状态。
- 管理员可将某个版本切为 100% 主用，或对未激活版本开启 20% 灰度。
- 右侧状态面板展示当前路由、24 小时分析量、平均置信度和待复核数量。

## 验证

- `python -m compileall backend\app backend\tests`
- `pytest backend\tests\test_api.py -q`
- `pytest backend\tests -q`
- `npm run build`（在 `frontend` 目录）
- `git diff --check`

## 下一步

继续推进 P1 的「主题聚类模型」：补充 embedding 服务、聚类结果持久化、关键词提取和聚类结果页面。
