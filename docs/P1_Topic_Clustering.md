# P1 主题聚类模型落地

本阶段补齐 P1「主题聚类模型」的可运行闭环，数据库继续使用现有 SQLite。

## 后端

- 新增 `TopicClusteringService`，将聚类算法、关键词提取、成员权重和持久化逻辑从路由中拆出。
- `POST /api/v1/topic-clusters/run` 支持 `kmeans`、`hdbscan`、`dbscan` 参数。
- 嵌入策略优先尝试本地缓存的 `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`；无本地模型或依赖不可用时降级为 TF-IDF 向量。
- `hdbscan` 依赖不可用时自动降级到 sklearn `DBSCAN`，保证当前部署不因为可选模型环境缺失而中断。
- 聚类结果持久化到 `topic_clusters` 和 `cluster_members`，`params_json` 保存关键词、embedding provider、窗口和标签信息。
- 簇关键词通过 TF-IDF 从成员标题、摘要、分类和平台文本中提取。

## 前端

热点页「聚类主题」子视图已接入真实聚类 API：

- 可选择 K-Means / HDBSCAN / DBSCAN、簇数量和时间窗口，并触发后端聚类。
- 展示主题簇分布、簇列表、代表话题、关键词和主导情感。
- 簇详情从 `/api/v1/topic-clusters/{id}` 拉取真实成员数据，不再按当前页分类字段本地模拟。

## 验证

- `python -m compileall backend\app backend\tests`
- `pytest backend\tests\test_api.py::TestTopicClusterEndpoints -q`
- `pytest backend\tests\test_api.py -q`
- `pytest backend\tests -q`
- `npm run build`（在 `frontend` 目录）

## 下一步

- 增加聚类对比：不同时间窗口的主题簇演变。
- 将聚类结果接入传播路径分析，用标题 embedding 做跨平台相似话题匹配。
- 引入人工评估样本，衡量同簇话题相关性。
