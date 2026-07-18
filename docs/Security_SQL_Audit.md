# SQL 注入防护审计记录

审计时间：2026-07-13

## 结论

当前 API 主路径未发现用户输入直接拼接 SQL 的用法。查询主要通过 SQLAlchemy ORM 构造，筛选值以参数绑定方式进入数据库。

本轮已收口：

- `GET /api/v1/topics` 的 `sort_by` 改为字段白名单，避免用户输入触碰 ORM 模型任意属性。
- `sort_order` 只接受 `asc` 的显式升序，其余值统一按降序兜底。
- 系统健康检查的 `SELECT 1` 改为 `text("SELECT 1")` 常量表达式。
- 增加异常排序参数回归测试，覆盖类似 `desc;DROP TABLE` 的输入形态。

## 扫描范围

- `backend/app/api/v1`
- `backend/app/services`
- `backend/app/core`
- `backend/scripts`

重点检查：

- `.execute()` / `cursor.execute()`
- `text()`
- `order_by()` 与用户参数
- `getattr()` / `setattr()` 动态属性访问
- `contains()` / `like()` 查询

## 保留项

以下原始 SQL 为常量 SQL，不包含用户输入：

- `backend/scripts/migrate_dedup.py`：一次性 SQLite 去重迁移脚本。
- `backend/app/core/database.py`：`PRAGMA foreign_keys=ON`。
- `backend/app/services/sqlite_maintenance.py`：固定索引维护语句。

## 后续建议

- 新增可排序字段时必须加入白名单映射，不直接使用 `getattr(Model, user_input)`。
- 新增原始 SQL 时只允许常量 SQL 或参数绑定 SQL，并补对应测试。
- 对管理类动态更新接口继续使用 Pydantic schema 控制字段集合。
