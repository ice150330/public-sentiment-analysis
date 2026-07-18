# SQLite 备份与恢复预案

本项目继续使用 SQLite 作为默认数据库。当前策略是：应用启动时自动补齐查询索引，管理员可以在线创建一致性备份；恢复操作保持为人工停机流程，不提供线上覆盖数据库的 API。

## 自动索引

后端启动时会执行：

```python
Base.metadata.create_all(bind=engine)
ensure_sqlite_indexes(engine)
```

`ensure_sqlite_indexes` 使用 `CREATE INDEX IF NOT EXISTS`，因此已有 `backend/data/sentiment.db` 也会补齐热点查询索引。

覆盖的主要查询场景：

- 热榜列表：平台、采集时间、热度、分类、采集日期。
- 情感统计：情感标签、分析时间、置信度。
- 采集日志：平台、状态、开始时间、完成时间。
- 预警事件：状态、等级、规则、话题、触发时间。
- 用户管理：角色、启用状态、创建时间。

## 创建备份

脚本方式：

```powershell
cd backend
python scripts/backup_sqlite.py
```

指定目录：

```powershell
cd backend
python scripts/backup_sqlite.py --backup-dir .\backups
```

API 方式：

```http
POST /api/v1/system/database/backup
Authorization: Bearer <admin_token>
```

备份文件默认写入：

```text
backend/backups/sentiment-backup-YYYYmmdd-HHMMSS.db
```

该目录已加入 `.gitignore`，不要把运行时备份提交到仓库。

## 下载备份

查询备份列表：

```http
GET /api/v1/system/database/backups
Authorization: Bearer <admin_token>
```

下载指定文件：

```http
GET /api/v1/system/database/backups/{filename}
Authorization: Bearer <admin_token>
```

## 恢复流程

恢复会覆盖当前数据库文件，必须停机执行。

1. 停止后端 API、采集任务和所有会写数据库的进程。
2. 先为当前库创建一次恢复前备份：

```powershell
cd backend
python scripts/backup_sqlite.py --backup-dir .\backups\before-restore
```

3. 确认待恢复文件存在且大小正常：

```powershell
Get-Item .\backups\sentiment-backup-YYYYmmdd-HHMMSS.db
```

4. 覆盖当前 SQLite 文件：

```powershell
Copy-Item -LiteralPath .\backups\sentiment-backup-YYYYmmdd-HHMMSS.db -Destination .\data\sentiment.db -Force
```

5. 启动后端，应用会自动补齐缺失索引。
6. 验证健康检查和核心页面：

```powershell
Invoke-RestMethod http://localhost:8000/health
```

如果恢复后发现数据不符合预期，停止后端，用第 2 步生成的 `before-restore` 备份按同样方式覆盖回去。
