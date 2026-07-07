# 公众情绪智能分析系统

> **Public Sentiment Intelligent Analysis System**
>
> 一套覆盖六大主流中文社交媒体平台的舆情智能分析系统，
> 具备实时采集、情感分析、热点聚类、趋势预测与可视化展示能力。

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![React](https://img.shields.io/badge/React-19-61DAFB)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.3-EE4C2C)](https://pytorch.org)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 系统概述

### 核心能力

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  数据采集   │  │  智能分析    │  │  趋势预测    │  │  可视化展示  │
│  6大平台    │  │  BERT情感   │  │  LSTM预测   │  │  实时大屏    │
│  定时增量   │  │  LDA聚类    │  │  异常检测   │  │  交互图表    │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

| 能力 | 说明 |
|------|------|
| **多平台采集** | 微博、抖音、今日头条、百度、B站、知乎 6 大平台热榜+正文+评论 |
| **情感分析** | 基于 BERT 的中文情感分类，支持正面/负面/中性三分类 |
| **热点聚类** | 自动发现每日热点话题，跨平台关联分析 |
| **趋势预测** | LSTM/Prophet 预测热度走势，提前 3-7 天预警 |
| **异常检测** | 实时监测舆情异常飙升，自动触发告警 |
| **可解释性** | SHAP 解释模型预测原因，让 AI 决策透明化 |
| **可视化** | React + ECharts 实时数据大屏，支持多维度交互分析 |

### 技术架构

```
前端层 (React 19 + TypeScript 5 + ECharts 5 + Ant Design 5)
                    ↑ REST API / WebSocket
后端层 (FastAPI 0.115 + Celery 5 + SQLAlchemy 2)
                    ↑
分析层 (PyTorch 2.3 + Transformers 4.40 + scikit-learn 1.5 + SHAP)
                    ↑
存储层 (PostgreSQL 16 + MongoDB 7 + Redis 7 + InfluxDB 3)
                    ↑
采集层 (requests + Playwright + APScheduler + Celery)
```

---

## 快速开始

### 环境要求

| 环境 | 最低版本 | 推荐版本 |
|------|---------|---------|
| Python | 3.11 | 3.12 |
| Node.js | 20.0 | 22.0 |
| Docker | 24.0 | 26.0 |
| Docker Compose | 2.20 | 2.27 |

### 1. 克隆仓库

```bash
git clone https://github.com/ice150330/public-sentiment-analysis.git
cd public-sentiment-analysis
```

### 2. 启动依赖服务

```bash
docker-compose up -d postgres redis mongodb influxdb
```

### 3. 安装后端依赖

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. 初始化数据库

```bash
python scripts/init_db.py
python scripts/run_migrations.py
```

### 5. 启动后端服务

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. 安装前端依赖

```bash
cd frontend
npm install
```

### 7. 启动前端开发服务器

```bash
npm run dev
```

### 8. 访问系统

- 前端界面: http://localhost:5173
- API 文档: http://localhost:8000/docs
- 管理后台: http://localhost:8000/admin

---

## 项目结构

```
public-sentiment-analysis/
├── AGENT.md                    # 项目设计规约（必读）
├── README.md                   # 本文件
├── docker-compose.yml          # 容器编排配置
├── .gitignore                  # Git 忽略配置
│
├── docs/                       # 设计文档
│   ├── README.md               # 文档目录索引
│   ├── 系统设计文档_v1.0.md     # 完整系统架构设计
│   ├── 需求规格说明书.md        # 功能需求详细说明
│   ├── 数据库设计文档.md        # ER图、表结构、索引
│   ├── API接口文档.md           # 接口定义与示例
│   ├── 前端设计文档.md          # 页面原型与交互规范
│   ├── 模型设计文档.md          # 算法选型与训练方案
│   ├── 部署运维文档.md          # 部署架构与监控
│   └── 测试计划.md              # 测试策略与用例
│
├── backend/                    # 后端代码
│   ├── app/                    # 主应用
│   │   ├── api/                # API 路由
│   │   ├── core/               # 核心配置
│   │   ├── models/             # 数据模型
│   │   ├── schemas/            # Pydantic 模型
│   │   ├── services/           # 业务逻辑
│   │   ├── tasks/              # Celery 异步任务
│   │   └── main.py             # 应用入口
│   ├── alembic/                # 数据库迁移
│   ├── tests/                  # 单元测试
│   └── requirements.txt        # Python 依赖
│
├── frontend/                   # 前端代码
│   ├── src/                    # 源代码
│   │   ├── components/         # 公共组件
│   │   ├── pages/              # 页面组件
│   │   ├── stores/             # 状态管理
│   │   ├── services/           # API 服务
│   │   ├── types/              # TypeScript 类型
│   │   └── App.tsx             # 应用入口
│   ├── package.json            # Node 依赖
│   └── vite.config.ts          # 构建配置
│
├── crawler/                    # 数据采集
│   ├── spiders/                # 各平台爬虫
│   ├── pipeline/               # 数据清洗管道
│   ├── scheduler/              # 调度器
│   └── config/                 # 爬虫配置
│
├── engine/                     # 分析引擎
│   ├── sentiment/              # 情感分析
│   ├── clustering/             # 热点聚类
│   ├── forecasting/            # 趋势预测
│   ├── anomaly/                # 异常检测
│   └── explainability/         # 可解释性
│
├── models/                     # 预训练模型
│   ├── bert-sentiment/          # 情感分析模型
│   ├── lda-topic/               # 主题聚类模型
│   └── lstm-forecast/           # 预测模型
│
├── scripts/                    # 工具脚本
│   ├── init_db.py              # 数据库初始化
│   ├── run_migrations.py        # 执行迁移
│   └── seed_data.py            # 测试数据
│
├── config/                     # 配置文件
│   ├── default.yaml            # 默认配置
│   ├── local.yaml.example      # 本地配置模板
│   └── production.yaml         # 生产配置
│
└── data/                       # 数据目录（gitignore）
    ├── raw/                    # 原始采集数据
    ├── processed/              # 清洗后数据
    └── models/                 # 训练好的模型
```

---

## 功能模块

### 数据采集模块

- 微博热搜榜单与话题评论采集
- 抖音热榜话题与视频元数据采集
- 今日头条热榜事件与文章正文采集
- 百度实时热搜数据采集
- B站热搜词与热门视频/评论采集
- 知乎热榜问答与回答摘要采集

### 分析引擎模块

- **情感分析**: 基于 BERT/RoBERTa 的中文情感三分类
- **热点聚类**: LDA 主题模型 + HDBSCAN 密度聚类
- **趋势预测**: LSTM + Prophet 集成预测，带置信区间
- **异常检测**: Isolation Forest + Z-score 多策略检测
- **可解释性**: SHAP 值解释模型预测原因

### 后端服务模块

- RESTful API 接口（20+ 接口覆盖全量功能）
- Celery 异步任务队列（批量分析、定时调度）
- WebSocket 实时推送（预警通知）
- JWT 认证（可选）
- 自动 API 文档生成（Swagger/OpenAPI）

### 前端可视化模块

- 舆情总览大屏（KPI 卡片 + 趋势图 + 分布图 + 词云）
- 热点分析看板（聚类列表 + 演化时序 + 平台对比）
- 预警中心（预警列表 + 趋势统计 + 规则配置）
- 系统管理（采集状态 + 任务监控 + 日志查看）

---

## 技术栈

### 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 19.0 | UI 框架 |
| TypeScript | 5.5 | 类型安全 |
| Ant Design | 5.20 | 组件库 |
| ECharts | 5.5 | 图表可视化 |
| Zustand | 4.5 | 状态管理 |
| Axios | 1.7 | HTTP 请求 |
| Vite | 5.3 | 构建工具 |

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| FastAPI | 0.115 | Web 框架 |
| SQLAlchemy | 2.0 | ORM |
| Celery | 5.4 | 异步任务 |
| Pydantic | 2.8 | 数据校验 |
| Alembic | 1.13 | 数据库迁移 |
| Uvicorn | 0.30 | ASGI 服务器 |
| Gunicorn | 23 | WSGI 服务器 |
| APScheduler | 3.10 | 定时调度 |

### AI / 数据科学

| 技术 | 版本 | 用途 |
|------|------|------|
| PyTorch | 2.3 | 深度学习框架 |
| Transformers | 4.40 | 预训练模型 |
| scikit-learn | 1.5 | 机器学习 |
| SHAP | 0.46 | 可解释性分析 |
| pandas | 2.2 | 数据处理 |
| numpy | 2.0 | 数值计算 |
| jieba | 0.42 | 中文分词 |
| Prophet | 1.1 | 时序预测 |

### 数据存储

| 技术 | 版本 | 用途 |
|------|------|------|
| PostgreSQL | 16 | 结构化数据主存储 |
| MongoDB | 7.0 | 原始文本/非结构化数据 |
| Redis | 7.2 | 缓存、消息队列、会话 |
| InfluxDB | 3.0 | 时序指标数据 |

### 基础设施

| 技术 | 版本 | 用途 |
|------|------|------|
| Docker | 26.0 | 容器化 |
| Docker Compose | 2.27 | 多容器编排 |
| Nginx | 1.26 | 反向代理、静态资源 |
| Playwright | 1.45 | 浏览器自动化爬虫 |
| GitHub Actions | — | CI/CD（可选） |

---

## 开发文档

所有设计文档位于 `docs/` 目录：

| 文档 | 说明 |
|------|------|
| [系统设计文档](docs/系统设计文档_v1.0.md) | 完整系统架构、模块设计、技术选型、实施计划 |
| [需求规格说明书](docs/需求规格说明书.md) | 功能需求与非功能需求详细说明 |
| [数据库设计文档](docs/数据库设计文档.md) | ER图、表结构、索引设计 |
| [API接口文档](docs/API接口文档.md) | 所有接口详细定义、请求/响应示例 |
| [前端设计文档](docs/前端设计文档.md) | 页面原型、组件设计、交互规范 |
| [模型设计文档](docs/模型设计文档.md) | 算法选型、训练方案、评估指标 |
| [部署运维文档](docs/部署运维文档.md) | 部署架构、环境配置、监控告警 |
| [测试计划](docs/测试计划.md) | 测试策略、用例设计、验收标准 |

**开发前必读：**
1. [AGENT.md](AGENT.md) — 项目设计规约与编码规范
2. [docs/系统设计文档_v1.0.md](docs/系统设计文档_v1.0.md) — 整体架构设计

---

## 贡献指南

### 开发流程

1. 阅读 [AGENT.md](AGENT.md) 了解设计规约
2. 从 `main` 分支创建功能分支：`git checkout -b feature/xxx`
3. 遵循 Conventional Commits 规范提交代码
4. 确保代码通过类型检查与单元测试
5. 提交 Pull Request，等待 Code Review
6. Review 通过后合并到 `main`

### 提交规范

```bash
# 类型: feat(新功能), fix(修复), docs(文档), refactor(重构), test(测试), chore(构建)
git commit -m "feat(api): add sentiment batch analyze endpoint"
```

---

## 许可证

本项目采用 [MIT License](LICENSE) 开源许可证。

---

## 联系方式

- 项目作者: [ice150330](https://github.com/ice150330)
- 项目仓库: https://github.com/ice150330/public-sentiment-analysis
- 问题反馈: [GitHub Issues](https://github.com/ice150330/public-sentiment-analysis/issues)

---

> 本项目为本科毕业设计作品，仅供学术研究使用。  
> 数据采集遵循各平台 robots.txt 与 API 使用规范，不做商业用途。

*最后更新: 2026-07-07*
