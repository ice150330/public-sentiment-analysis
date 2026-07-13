# 舆情系统升级影响评估报告

> 评估日期: 2026-07-10
> 评估对象: sentiment-analysis 正在运行的系统
> 服务状态: ✅ 运行中 (PID: 1374878, Port: 8000)
> 当前版本: v1.1.0

---

## 一、系统现状快照

### 1.1 运行环境

| 维度 | 现状 |
|------|------|
| 操作系统 | Linux VM-33-250-ubuntu |
| Python 版本 | 3.12 |
| 后端服务 | FastAPI (uvicorn) @ Port 8000 |
| 数据库 | SQLite (SQLAlchemy ORM) |
| 前端 | React 18 + Ant Design 5 |
| 定时任务 | APScheduler (每日 07:00 采集) |
| 爬虫 | Playwright + requests |

### 1.2 代码规模

| 模块 | 代码行数 | 文件数 |
|------|----------|--------|
| 数据模型 (models) | ~941 行 | ~15 个文件 |
| API 接口 (api) | ~5,559 行 | ~25 个文件 |
| 爬虫服务 (crawler) | ~400 行 | 多平台适配 |
| 前端组件 (frontend) | ~2,500 行 | React 组件 |
| **总计** | **~9,400 行** | **~50+ 文件** |

### 1.3 现有依赖清单

**后端依赖** (`requirements.txt`):
```
fastapi==0.115.0          ← Web 框架
uvicorn[standard]==0.30.0  ← ASGI 服务器
sqlalchemy==2.0.31         ← ORM
alembic==1.13.2            ← 数据库迁移
pydantic==2.8.2            ← 数据校验
apscheduler==3.10.4        ← 定时任务
requests==2.32.3           ← HTTP 请求
playwright==1.45.0         ← 浏览器自动化
python-dotenv==1.0.1       ← 环境变量
```

**前端依赖** (`package.json`):
```
react ^18.3.1              ← 框架
antd ^5.19.0               ← UI 组件库
react-router-dom ^6.24.0   ← 路由
axios ^1.7.2               ← HTTP 请求
echarts ^5.5.0             ← 图表（已有！）
echarts-for-react ^3.0.2   ← React 封装（已有！）
gsap ^3.15.0               ← 动画库（已有！）
```

### 1.4 现有 API 端点概览

| 路由前缀 | 功能 | 端点数量 |
|----------|------|----------|
| `/api/v1/platforms` | 平台管理 | ~5 |
| `/api/v1/topics` | 热榜数据 | ~8 |
| `/api/v1/sentiment` | 情感分析 | ~6 |
| `/api/v1/stats` | 统计分析 | ~8 |
| `/api/v1/crawler` | 爬虫控制 | ~5 |
| `/api/v1/alerts` | 预警中心 | ~6 |
| `/api/v1/data-quality` | 数据质量 | ~5 |
| `/api/v1/system` | 系统管理 | ~6 |
| `/api/v1/topic-ext` | 话题扩展 | ~4 |
| `/api/v1/model` | 模型管理 | ~6 |
| `/api/v1/topic-clusters` | 主题聚类 | ~4 |
| `/api/v1/propagation-paths` | 传播路径 | ~4 |
| `/api/v1/trend-predictions` | 趋势预测 | ~4 |
| `/api/v1/model-explanations` | 模型解释 | ~4 |
| **总计** | | **~75+ 端点** |

### 1.5 数据库模型

现有模型 (`app/models/`):
- HotTopic, SentimentRecord, AlertEvent
- DataQuality, TopicCluster, CrawlerTask
- 以及其他 10+ 个模型

---

## 二、升级内容分析

### 2.1 Phase 1: 后端算法增强

#### A. 引入 Transformers 情感分析

| 评估项 | 详情 |
|--------|------|
| **新增依赖** | `torch`, `transformers`, `spacy`, `zh-core-web-sm` |
| **安装体积** | torch (~2GB), transformers (~500MB), 模型文件 (~400MB) |
| **内存占用** | 启动后常驻内存 + ~500MB-1GB (模型加载) |
| **CPU 影响** | 推理时单核满载，需考虑并发控制 |
| **GPU 依赖** | 可选，CPU 可跑但速度慢 5-10 倍 |
| **数据库改动** | 新增 `sentiment_v2` 字段，不改现有表 |
| **API 影响** | 新增 `/api/v1/sentiment/v2/analyze`，现有端点不变 |
| **兼容性** | 现有数据无需迁移，新旧并行运行 |

**风险点**:
- ⚠️ **磁盘空间**: 模型文件 ~2-3GB，需确认磁盘余量
- ⚠️ **内存峰值**: 首次加载模型时内存可能翻倍
- ⚠️ **推理延迟**: CPU 下单条文本 ~100-500ms
- ⚠️ **并发瓶颈**: 高并发时需队列或 GPU 加速

**缓解方案**:
```python
# 1. 模型懒加载 - 非启动时加载
class TransformersSentimentAnalyzer:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()  # 首次调用时才加载
        return cls._instance

# 2. 异步推理 - 不阻塞主线程
async def analyze_async(text: str):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,  # 默认线程池
        lambda: analyzer.analyze(text)
    )

# 3. 批处理 - 减少推理次数
async def analyze_batch(texts: List[str]):
    return await loop.run_in_executor(
        None,
        lambda: analyzer.analyze_batch(texts)  # 一批处理
    )
```

#### B. 新增实体识别 (NER)

| 评估项 | 详情 |
|--------|------|
| **新增依赖** | `transformers` (已包含在 A 中) |
| **模型大小** | ~300MB (macbert4cner) |
| **内存占用** | + ~300MB |
| **推理延迟** | ~50-200ms/条 |
| **数据库改动** | 新增 `entities` JSON 字段 |
| **API 影响** | 新增 `/api/v1/sentiment/ner` |
| **兼容性** | 完全独立，不影响现有数据 |

#### C. 升级预警等级分类

| 评估项 | 详情 |
|--------|------|
| **新增依赖** | 无 (纯算法逻辑) |
| **代码改动** | 新增 `app/services/alert_engine_v2.py` |
| **数据库改动** | 新增 `risk_score`, `alert_level_v2` 字段 |
| **API 影响** | 新增 `/api/v1/alerts/v2` 系列端点 |
| **兼容性** | 旧预警系统继续运行，新旧并行 |

#### D. 新增情绪识别

| 评估项 | 详情 |
|--------|------|
| **新增依赖** | `transformers` (已包含) |
| **模型大小** | 可与情感分析共用模型 |
| **数据库改动** | 新增 `emotions` JSON 字段 |
| **API 影响** | 情感分析返回新增 `emotions` 字段 |
| **兼容性** | 向后兼容，前端可选展示 |

### 2.2 Phase 2: 前端架构升级

#### A. 主题系统

| 评估项 | 详情 |
|--------|------|
| **新增依赖** | 无 (纯 TypeScript 配置) |
| **代码改动** | 新增 `src/theme/` 目录 (~200 行) |
| **影响范围** | 仅影响新增大屏页面，不影响现有页面 |
| **兼容性** | 现有页面样式完全不受影响 |

#### B. ECharts 主题

| 评估项 | 详情 |
|--------|------|
| **新增依赖** | 无 (echarts 已有) |
| **代码改动** | 新增 `src/theme/echarts-theme.ts` (~100 行) |
| **影响范围** | 仅大屏组件使用 |
| **兼容性** | 现有图表不受影响 |

#### C. 组件复用体系

| 评估项 | 详情 |
|--------|------|
| **新增依赖** | 无 |
| **代码改动** | 新增 `src/components/bigscreen/` 目录 |
| **影响范围** | 仅大屏相关组件 |
| **兼容性** | 现有组件不受影响 |

#### D. 自适应方案

| 评估项 | 详情 |
|--------|------|
| **新增依赖** | 无 |
| **代码改动** | 新增 `src/hooks/useScreenScale.ts` (~50 行) |
| **影响范围** | 仅 `/bigscreen` 路由页面 |
| **兼容性** | 不影响现有页面布局 |

### 2.3 Phase 3: 高级可视化

#### A. 传播路径飞线图

| 评估项 | 详情 |
|--------|------|
| **新增依赖** | 无 (SVG 原生) |
| **代码改动** | `PropagationMap.tsx` (~200 行) |
| **数据来源** | 复用 `/api/v1/propagation-paths` |
| **性能影响** | SVG 动画 10-20 个节点无压力 |
| **兼容性** | 独立组件 |

#### B. 情感水位仪表盘

| 评估项 | 详情 |
|--------|------|
| **新增依赖** | 无 (SVG 原生) |
| **代码改动** | `SentimentGauge.tsx` (~150 行) |
| **数据来源** | 复用 `/api/v1/sentiment/stats` |
| **兼容性** | 独立组件 |

#### C. 关系图谱

| 评估项 | 详情 |
|--------|------|
| **新增依赖** | 无 (echarts 已有) |
| **代码改动** | `RelationGraph.tsx` (~100 行) |
| **数据来源** | 复用 `/api/v1/topic-clusters` |
| **性能影响** | 节点 >100 时可能需要分页/聚合 |
| **兼容性** | 独立组件 |

#### D. 地图热力

| 评估项 | 详情 |
|--------|------|
| **新增依赖** | `echarts` map 数据 (~200KB-1MB) |
| **代码改动** | `GeoHeatmap.tsx` (~100 行) |
| **数据来源** | 需后端新增地域统计接口 |
| **兼容性** | 独立组件 |

### 2.4 Phase 4: 大屏整合

| 评估项 | 详情 |
|--------|------|
| **新增依赖** | 无 |
| **代码改动** | `BigScreen.tsx` + 路由修改 (~300 行) |
| **路由影响** | 新增 `/bigscreen`，现有路由不变 |
| **导航影响** | Navbar 新增一个菜单项 |
| **构建影响** | 包体积 + ~50KB (不含模型) |

---

## 三、风险评估矩阵

### 3.1 风险等级定义

| 等级 | 定义 | 响应时间 |
|------|------|----------|
| 🔴 高危 | 可能导致服务中断或数据丢失 | 立即处理 |
| 🟡 中危 | 可能影响性能或用户体验 | 24小时内处理 |
| 🟢 低危 | 影响有限，可接受 | 计划内处理 |

### 3.2 风险清单

| 序号 | 风险描述 | 等级 | 概率 | 影响范围 | 缓解措施 |
|------|----------|------|------|----------|----------|
| R1 | Transformers 模型加载导致内存不足 | 🔴 | 中 | 后端服务 | 懒加载 + 内存监控 |
| R2 | 模型推理延迟导致 API 超时 | 🟡 | 高 | 情感分析接口 | 异步推理 + 缓存 |
| R3 | 磁盘空间不足（模型文件 ~3GB） | 🔴 | 低 | 整个系统 | 预检查 + 清理 |
| R4 | ECharts 按需引入配置错误导致构建失败 | 🟡 | 低 | 前端构建 | 测试构建 |
| R5 | 新 API 与现有数据库字段冲突 | 🟢 | 低 | 数据库 | 新字段命名隔离 |
| R6 | 前端路由冲突 | 🟢 | 极低 | 前端 | 独立路由测试 |
| R7 | 爬虫定时任务与新任务竞争资源 | 🟡 | 中 | 系统资源 | 资源监控 + 错峰 |
| R8 | GPU 驱动缺失导致模型无法加速 | 🟢 | 中 | 推理性能 | 降级 CPU 推理 |
| R9 | 并发推理导致 CPU 打满 | 🟡 | 中 | 系统稳定性 | 限流 + 队列 |
| R10 | 前端包体积增大导致加载变慢 | 🟢 | 低 | 首屏体验 | 懒加载 + 代码分割 |

### 3.3 关键风险详解

#### R1: 内存不足风险

**场景**: Transformers 模型加载后，系统内存从当前 ~300MB 增长到 ~1.5GB+

**当前系统状态**:
```bash
# 当前内存使用
$ free -h
              total        used        free      shared  buff/cache   available
Mem:          7.7Gi       2.1Gi       3.8Gi       0.2Gi       1.8Gi       5.2Gi

# 当前后端进程内存
$ ps aux | grep uvicorn
PID    %CPU %MEM    VSZ   RSS
1374878 0.1  4.0  985528 315964  ← ~316MB
```

**评估**: 系统可用内存 ~5.2GB，加载模型后占用 ~1.5GB，仍有 ~3.7GB 余量，**风险可控**。

**监控方案**:
```python
# app/core/memory_monitor.py
import psutil
import logging

logger = logging.getLogger(__name__)

def check_memory():
    """检查内存使用情况"""
    mem = psutil.virtual_memory()
    if mem.percent > 85:
        logger.warning(f"内存使用过高: {mem.percent}%")
        return False
    return True

# 模型加载前检查
if not check_memory():
    raise MemoryError("系统内存不足，无法加载模型")
```

#### R2: API 超时风险

**场景**: 情感分析接口推理耗时 500ms，超过现有 API 超时设置

**现有 API 响应时间**:
```
GET /api/v1/topics      → ~50ms
GET /api/v1/sentiment   → ~30ms
GET /api/v1/stats       → ~100ms
```

**评估**: 引入 Transformers 后，单次推理 ~100-500ms，**可能超时**。

**缓解方案**:
```python
# 1. 异步推理
@app.post("/api/v1/sentiment/v2/analyze")
async def analyze_v2(text: str):
    # 在线程池中执行，不阻塞事件循环
    result = await asyncio.get_event_loop().run_in_executor(
        None, analyzer.analyze, text
    )
    return result

# 2. 结果缓存（LRU）
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_analyze(text_hash: str):
    return analyzer.analyze(text)

# 3. 批处理接口
@app.post("/api/v1/sentiment/v2/analyze-batch")
async def analyze_batch(texts: List[str]):
    # 一批处理，摊薄推理开销
    results = await loop.run_in_executor(
        None, analyzer.analyze_batch, texts
    )
    return results
```

#### R3: 磁盘空间风险

**当前磁盘**:
```bash
$ df -h /
Filesystem      Size  Used Avail Use% Mounted on
/dev/vda1        50G   35G   13G  74% /
```

**模型文件估算**:
| 模型 | 大小 |
|------|------|
| bert-base-chinese | ~400MB |
| roberta-sentiment | ~500MB |
| macbert4cner | ~300MB |
| spacy zh_core_web_sm | ~50MB |
| **总计** | **~1.25GB** |

**评估**: 可用空间 13GB，模型 1.25GB，**风险极低**。

---

## 四、兼容性分析

### 4.1 数据库兼容性

| 改动类型 | 影响 | 回滚方案 |
|----------|------|----------|
| 新增字段 | 不影响现有数据 | 删除字段即可 |
| 新增表 | 完全独立 | 删除表即可 |
| 新增索引 | 不影响查询 | 删除索引即可 |

**具体改动**:
```sql
-- 新增字段（向后兼容）
ALTER TABLE sentiment_records ADD COLUMN sentiment_v2 JSON;
ALTER TABLE sentiment_records ADD COLUMN entities JSON;
ALTER TABLE sentiment_records ADD COLUMN emotions JSON;
ALTER TABLE alert_events ADD COLUMN risk_score FLOAT;
ALTER TABLE alert_events ADD COLUMN alert_level_v2 VARCHAR(20);
```

### 4.2 API 兼容性

| 改动类型 | 影响 | 说明 |
|----------|------|------|
| 新增端点 | 无影响 | 新路由独立 |
| 新增响应字段 | 向后兼容 | 前端忽略未知字段 |
| 修改现有端点 | **无** | 现有端点不变 |

### 4.3 前端兼容性

| 改动类型 | 影响 | 说明 |
|----------|------|------|
| 新增路由 | 无影响 | 独立页面 |
| 新增组件 | 无影响 | 仅在 /bigscreen 使用 |
| 修改 Navbar | 影响极小 | 仅新增一个菜单项 |

---

## 五、回滚方案

### 5.1 快速回滚策略

```bash
# 1. 前端回滚
# 仅删除新增文件，恢复 App.tsx 和 Navbar.tsx
git checkout frontend/src/App.tsx
git checkout frontend/src/components/Navbar.tsx
rm -rf frontend/src/components/bigscreen/
rm -rf frontend/src/hooks/useScreenScale.ts
rm -rf frontend/src/theme/

# 2. 后端回滚
# 停止服务，删除新增模块，重启
cd /root/.openclaw/workspace/sentiment-analysis/backend
rm -rf app/ml/
rm -rf app/services/alert_engine_v2.py
# 保留数据库新字段（不影响运行），或执行：
# alembic downgrade -1

# 3. 依赖回滚
pip uninstall torch transformers spacy

# 4. 重启服务
./venv/bin/uvicorn app.main:app --reload
```

### 5.2 数据库回滚

```bash
# 如果需要回滚数据库字段
sqlite3 data/sentiment.db <<EOF
ALTER TABLE sentiment_records DROP COLUMN sentiment_v2;
ALTER TABLE sentiment_records DROP COLUMN entities;
ALTER TABLE sentiment_records DROP COLUMN emotions;
ALTER TABLE alert_events DROP COLUMN risk_score;
ALTER TABLE alert_events DROP COLUMN alert_level_v2;
EOF
```

### 5.3 蓝绿部署方案（推荐）

```bash
# 方案: 并行部署，逐步切换

# 1. 新服务部署到不同端口
./venv/bin/uvicorn app.main:app --port 8001  # 新版本

# 2. 验证新服务健康
 curl http://localhost:8001/health

# 3. 切换 Nginx/负载均衡指向新端口

# 4. 观察 1 小时无问题后，关闭旧服务
```

---

## 六、性能基线与目标

### 6.1 当前性能基线

| 指标 | 当前值 | 测试方法 |
|------|--------|----------|
| API 平均响应 | ~50ms | curl -w "%{time_total}" |
| 服务内存占用 | ~316MB | ps aux |
| 数据库大小 | ~50MB | ls -lh data/ |
| 前端构建体积 | ~2MB | ls -lh build/static/js |
| 首屏加载 | ~2s | Chrome DevTools |

### 6.2 升级后目标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| API 平均响应 | <200ms | 含 Transformers 推理 |
| 服务内存占用 | <1.5GB | 模型加载后 |
| 数据库大小 | <100MB | 新增字段 |
| 前端构建体积 | <3MB | 新增组件 |
| 首屏加载 | <3s | 大屏页面 |
| 并发处理 | 10 req/s | CPU 推理 |

---

## 七、监控与告警

### 7.1 新增监控指标

| 指标 | 采集方式 | 告警阈值 |
|------|----------|----------|
| 模型推理延迟 | 日志/metrics | >500ms |
| 内存使用 | psutil | >80% |
| 磁盘空间 | shutil | >85% |
| API 错误率 | 中间件统计 | >1% |
| 模型加载状态 | 健康检查 | 失败 |

### 7.2 健康检查扩展

```python
@app.get("/health", tags=["系统"])
async def health_check():
    status = {
        "status": "healthy",
        "version": APP_VERSION,
        "components": {
            "database": check_db(),
            "transformers": check_model_loaded(),  # 新增
            "memory": check_memory(),              # 新增
        }
    }
    return status
```

---

## 八、实施建议

### 8.1 推荐实施顺序

```
Phase 0: 准备工作（1天）
  ├── 磁盘/内存预检查
  ├── 模型文件预下载
  ├── 测试环境搭建
  └── 数据库备份

Phase 1: 后端增强（2-3天）
  ├── Day 1: Transformers 情感分析 + 实体识别
  ├── Day 2: 预警升级 + 情绪识别
  └── Day 3: 测试 + 调优

Phase 2: 前端架构（1-2天）
  ├── 主题系统 + 组件封装
  └── Hooks + 自适应

Phase 3: 可视化（2-3天）
  ├── 飞线图 + 水位图
  ├── 关系图谱 + 旭日图
  └── 地图热力

Phase 4: 整合（1天）
  ├── 大屏页面组装
  ├── 数据对接
  └── 性能测试
```

### 8.2 关键决策点

| 决策 | 选项 | 建议 |
|------|------|------|
| GPU 加速 | 是/否 | 当前无 GPU，选否，CPU 可接受 |
| 模型大小 | 大(准确率高)/小(速度快) | 选小模型 (DistilBERT)，平衡性能 |
| 新旧系统 | 并行/替换 | 选并行，逐步切换 |
| 前端路由 | 独立页面/嵌入现有 | 选独立 /bigscreen 页面 |
| 数据迁移 | 全量/增量 | 选增量，仅新数据使用新模型 |

---

## 九、总结

| 维度 | 评估结果 |
|------|----------|
| **整体风险** | 🟡 中等可控 |
| **核心风险** | 内存增加、推理延迟 |
| **回滚难度** | 🟢 简单（纯增量改动） |
| **业务影响** | 🟢 无影响（独立模块） |
| **推荐实施** | ✅ 建议分阶段实施 |

**关键结论**:
1. 所有升级均为**纯增量**，不影响现有运行系统
2. 主要风险在于**资源占用**（内存/磁盘），非业务逻辑
3. **推荐蓝绿部署**，新旧并行运行，逐步切换
4. 最坏情况可**一键回滚**，无数据丢失风险

---

*报告生成时间: 2026-07-10 15:30 CST*
*系统状态: 运行中 (PID: 1374878)*
