"""Model version registry and routing helpers."""

from __future__ import annotations

import json
import random
from typing import Any

from sqlalchemy.orm import Session

from app.models import ModelVersion


DEFAULT_MODEL_VERSION_CONFIGS = [
    {
        "version": "classic-v1",
        "model_name": "Sklearn/Rule Sentiment",
        "task_type": "sentiment",
        "device": "cpu",
        "is_active": True,
        "description": "Fast local sentiment model with rule fallback.",
        "metrics": {"accuracy_target": 0.78, "latency_ms": 20},
        "config": {"provider": "classic", "batch_size": 32, "traffic_percent": 100},
    },
    {
        "version": "transformers-v2",
        "model_name": "Chinese Transformers Sentiment",
        "task_type": "sentiment",
        "device": "cpu",
        "is_active": False,
        "description": "Enhanced Transformers pipeline with local-cache fallback.",
        "metrics": {"accuracy_target": 0.85, "latency_ms": 180},
        "config": {"provider": "transformers", "batch_size": 32, "traffic_percent": 0},
    },
]


def _json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _json_dumps(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def ensure_default_model_versions(db: Session) -> int:
    """Seed default model versions when they are missing."""
    changed = 0
    for config in DEFAULT_MODEL_VERSION_CONFIGS:
        exists = db.query(ModelVersion).filter(ModelVersion.version == config["version"]).first()
        if exists:
            continue
        db.add(
            ModelVersion(
                version=config["version"],
                model_name=config["model_name"],
                task_type=config["task_type"],
                device=config["device"],
                metrics_json=_json_dumps(config["metrics"]),
                config_json=_json_dumps(config["config"]),
                is_active=config["is_active"],
                description=config["description"],
            )
        )
        changed += 1

    active_count = db.query(ModelVersion).filter(ModelVersion.is_active == True).count()
    if active_count == 0:
        fallback = db.query(ModelVersion).filter(ModelVersion.version == "classic-v1").first()
        if fallback:
            fallback.is_active = True
            config = _json_loads(fallback.config_json)
            config["traffic_percent"] = 100
            fallback.config_json = _json_dumps(config)
            changed += 1

    if changed:
        db.flush()
    return changed


def model_version_payload(version: ModelVersion) -> dict:
    config = _json_loads(version.config_json)
    metrics = _json_loads(version.metrics_json)
    return {
        "id": version.id,
        "version": version.version,
        "model_name": version.model_name,
        "task_type": version.task_type,
        "device": version.device,
        "metrics_json": version.metrics_json,
        "config_json": version.config_json,
        "metrics": metrics,
        "config": config,
        "traffic_percent": int(config.get("traffic_percent") or 0),
        "provider": config.get("provider") or "classic",
        "is_active": version.is_active,
        "description": version.description,
        "created_at": version.created_at.isoformat() if version.created_at else None,
        "updated_at": version.updated_at.isoformat() if version.updated_at else None,
    }


def activate_model_version(db: Session, version_id: int, *, traffic_percent: int = 100) -> ModelVersion:
    """Activate a model version and update routing weights."""
    traffic_percent = max(0, min(100, traffic_percent))
    target = db.query(ModelVersion).filter(ModelVersion.id == version_id).first()
    if not target:
        raise ValueError("Model version not found")

    versions = db.query(ModelVersion).filter(ModelVersion.task_type == target.task_type).all()
    if traffic_percent >= 100:
        for version in versions:
            config = _json_loads(version.config_json)
            config["traffic_percent"] = 100 if version.id == target.id else 0
            version.config_json = _json_dumps(config)
            version.is_active = version.id == target.id
        return target

    previous_primary = next((version for version in versions if version.is_active and version.id != target.id), None)
    if previous_primary is None:
        previous_primary = next((version for version in versions if version.id != target.id), None)

    for version in versions:
        config = _json_loads(version.config_json)
        if version.id == target.id:
            config["traffic_percent"] = traffic_percent
            version.is_active = True
        elif previous_primary and version.id == previous_primary.id:
            config["traffic_percent"] = 100 - traffic_percent
            version.is_active = True
        else:
            config["traffic_percent"] = 0
            version.is_active = False
        version.config_json = _json_dumps(config)
    return target


def select_sentiment_model_version(db: Session) -> ModelVersion:
    """Select a sentiment model according to active routing weights."""
    if ensure_default_model_versions(db):
        db.commit()
    active_versions = db.query(ModelVersion).filter(
        ModelVersion.task_type == "sentiment",
        ModelVersion.is_active == True,
    ).all()
    if not active_versions:
        fallback = db.query(ModelVersion).filter(ModelVersion.version == "classic-v1").first()
        if fallback:
            fallback.is_active = True
            return fallback
        raise RuntimeError("No sentiment model version available")

    weighted: list[tuple[ModelVersion, int]] = []
    for version in active_versions:
        traffic = int(_json_loads(version.config_json).get("traffic_percent") or 0)
        weighted.append((version, max(0, traffic)))

    total = sum(weight for _, weight in weighted)
    if total <= 0:
        return active_versions[0]

    point = random.randint(1, total)
    cumulative = 0
    for version, weight in weighted:
        cumulative += weight
        if point <= cumulative:
            return version
    return active_versions[0]
