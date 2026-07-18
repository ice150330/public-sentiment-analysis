# P1 低置信情感复核队列

本阶段补齐 P1「低置信度样本人工复核队列」的可运行闭环，数据库继续使用现有 SQLite。

## 入队规则

- 默认阈值：`confidence < 0.6`
- 队列表：`sentiment_review_items`
- 每条 `sentiment_results` 最多生成一条复核记录
- 保留模型原始判断、建议标签、置信度快照和人工校正结果

## API

查询低置信复核队列：

```http
GET /api/v1/model/review-queue?status=pending&threshold=0.6
Authorization: Bearer <analyst_or_admin_token>
```

复核或忽略：

```http
PATCH /api/v1/model/review-queue/{review_id}
Authorization: Bearer <analyst_or_admin_token>
Content-Type: application/json

{
  "status": "reviewed",
  "corrected_label": "negative",
  "note": "人工复核确认负面"
}
```

忽略样本：

```json
{
  "status": "ignored",
  "note": "样本信息不足"
}
```

## 权限与审计

- 分析师及管理员可访问复核队列。
- 分析师受 `platform_scope` 限制，只能处理授权平台数据。
- 每次复核写入 `AuditLog`，action 为 `review_sentiment_result`。

## 前端入口

情感分析页新增「人工复核」子视图，展示待复核样本、模型判断、人工标签选择和忽略操作。
