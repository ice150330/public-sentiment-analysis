"""Small helper for writing audit log records."""

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog


def write_audit_log(
    db: Session,
    *,
    operator: str,
    action: str,
    target_type: str | None = None,
    target_id: str | int | None = None,
    before: Any = None,
    after: Any = None,
    note: str | None = None,
) -> AuditLog:
    log = AuditLog(
        operator=operator or "system",
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        before_json=json.dumps(before, ensure_ascii=False, default=str) if before is not None else None,
        after_json=json.dumps(after, ensure_ascii=False, default=str) if after is not None else None,
        note=note,
    )
    db.add(log)
    return log
