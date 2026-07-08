"""
UI.pen/backend contract compatibility tests.

These checks keep the documented UI endpoint map aligned with FastAPI routes
and verify representative compatibility endpoints return usable responses.
"""

import json
import os
import re
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault(
    "DATABASE_URL",
    f"sqlite:///{(Path(__file__).resolve().parents[1] / 'data' / 'sentiment.db').as_posix()}",
)

from app.main import app


async def _request(method: str, path: str, **kwargs):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


async def _get(path: str):
    return await _request("GET", path)


async def _post(path: str, **kwargs):
    return await _request("POST", path, **kwargs)


def _normalize_path(path: str) -> str:
    path = path.split("?")[0].rstrip("/")
    path = re.sub(r"\{[^}]+(:int)?\}", "{}", path)
    return path


def test_ui_contract_documented_paths_are_registered():
    repo_root = Path(__file__).resolve().parents[2]
    doc = (repo_root / "docs" / "UI后端功能映射清单.md").read_text(encoding="utf-8")
    pattern = re.compile(r"`([^`]*?/api/v1/[^`]*)`")

    documented_method_paths = set()
    documented_paths_without_method = set()
    for match in pattern.finditer(doc):
        value = match.group(1).strip()
        for part in re.split(r"、|，|\s+or\s+", value):
            part = part.strip()
            method_match = re.match(
                r"((?:GET|POST|PUT|PATCH|DELETE)(?:/(?:GET|POST|PUT|PATCH|DELETE))*)\s+(/api/v1/\S+)",
                part,
            )
            if method_match:
                path = _normalize_path(method_match.group(2))
                for method in method_match.group(1).split("/"):
                    documented_method_paths.add((method, path))
                continue

            path_match = re.search(r"(/api/v1/\S+)", part)
            if path_match:
                path = _normalize_path(path_match.group(1))
                if "*" not in path and not path.endswith(".py"):
                    documented_paths_without_method.add(path)

    openapi_method_paths = {
        (method.upper(), _normalize_path(path))
        for path, methods in app.openapi()["paths"].items()
        for method in methods
        if method != "parameters"
    }
    openapi_paths = {path for _, path in openapi_method_paths}
    missing_methods = sorted(documented_method_paths - openapi_method_paths)
    missing_paths = sorted(documented_paths_without_method - openapi_paths)

    assert documented_method_paths
    assert missing_methods == []
    assert missing_paths == []


def test_frontend_api_calls_are_registered():
    repo_root = Path(__file__).resolve().parents[2]
    api_source = (repo_root / "frontend" / "src" / "services" / "api.ts").read_text(encoding="utf-8")
    pattern = re.compile(r"api\.(get|post|put|patch|delete).*?\((`[^`]+`|'[^']+'|\"[^\"]+\")", re.DOTALL)

    frontend_paths = set()
    for match in pattern.finditer(api_source):
        raw_path = match.group(2)[1:-1]
        if not raw_path.startswith("/"):
            continue
        path = re.sub(r"\$\{[^}]+\}", "{}", raw_path)
        frontend_paths.add((match.group(1).upper(), _normalize_path(f"/api/v1{path}")))

    openapi_paths = {
        (method.upper(), _normalize_path(path))
        for path, methods in app.openapi()["paths"].items()
        for method in methods
        if method != "parameters"
    }
    missing = sorted(frontend_paths - openapi_paths)

    assert frontend_paths
    assert missing == []


def test_ui_contract_docs_do_not_report_stale_backend_gaps():
    repo_root = Path(__file__).resolve().parents[2]
    docs = [
        repo_root / "docs" / "UI后端功能映射清单.md",
        repo_root / "docs" / "后端缺口分析报告.md",
        repo_root / "docs" / "后端开发计划.md",
    ]
    stale_patterns = [
        "待新增",
        "部分支持",
        "已支持基础",
        "❌ 未实现",
        "待开始",
        "覆盖 UI.pen 需求的约",
    ]

    stale_hits = []
    for doc_path in docs:
        text = doc_path.read_text(encoding="utf-8")
        for pattern in stale_patterns:
            if pattern in text:
                stale_hits.append(f"{doc_path.name}: {pattern}")

    assert stale_hits == []


@pytest.mark.asyncio
async def test_ui_contract_safe_get_endpoints_return_success():
    paths = [
        "/api/v1/sync/status",
        "/api/v1/search?q=%E6%AF%94%E8%B5%9B&scope=topics&page=1&page_size=3",
        "/api/v1/dashboard/overview",
        "/api/v1/platforms/monitoring",
        "/api/v1/stats/platform-matrix",
        "/api/v1/data-quality/freshness",
        "/api/v1/alerts?page=1&page_size=3",
        "/api/v1/alert-rules?page=1&page_size=3",
        "/api/v1/topics/facets",
        "/api/v1/topics/keywords/cloud?limit=10",
        "/api/v1/topics/clusters?page=1&page_size=3",
        "/api/v1/topics/propagation/strength",
        "/api/v1/models/current",
        "/api/v1/models/v1/metrics",
        "/api/v1/sentiment/trend?days=7",
        "/api/v1/sentiment/summary",
        "/api/v1/sentiment/jobs?page=1&page_size=3",
        "/api/v1/sentiment/jobs/current",
        "/api/v1/sentiment/low-confidence?page=1&page_size=3",
        "/api/v1/forecast/signals",
        "/api/v1/forecast/scenarios",
        "/api/v1/crawler/tasks/summary",
        "/api/v1/crawler/tasks/current",
        "/api/v1/crawler/timeline?days=7",
        "/api/v1/audit-logs?page=1&page_size=3",
    ]

    for path in paths:
        response = await _get(path)
        assert response.status_code == 200, path
        payload = response.json()
        assert payload["code"] == 200, path

    sync_payload = (await _get("/api/v1/sync/status")).json()["data"]
    assert "is_syncing" in sync_payload
    assert "queue_length" in sync_payload


@pytest.mark.asyncio
async def test_ui_contract_dynamic_topic_and_platform_aliases():
    topics_response = await _get("/api/v1/topics?page=1&page_size=1")
    assert topics_response.status_code == 200
    topics = topics_response.json()["data"]["items"]

    if topics:
        topic_id = topics[0]["id"]
        for path in [
            f"/api/v1/topics/{topic_id}/samples",
            f"/api/v1/topics/{topic_id}/related",
            f"/api/v1/topics/{topic_id}/propagation",
        ]:
            response = await _get(path)
            assert response.status_code == 200, path
            assert response.json()["code"] == 200, path

    platforms_response = await _get("/api/v1/platforms")
    assert platforms_response.status_code == 200
    platforms = platforms_response.json()["data"]

    if platforms:
        platform_id = platforms[0]["id"]
        response = await _get(f"/api/v1/platforms/{platform_id}/config")
        assert response.status_code == 200
        assert response.json()["code"] == 200


@pytest.mark.asyncio
async def test_ui_contract_non_destructive_post_endpoints_return_success():
    response = await _post("/api/v1/sentiment/explain", json={"text": "这个话题需要持续关注"})
    assert response.status_code == 200
    assert response.json()["code"] == 200

    response = await _post("/api/v1/forecast/heat", json={"horizon_days": 3})
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 200
    assert len(payload["data"]["forecast"]) == 3


@pytest.mark.asyncio
async def test_ui_contract_task_endpoints_are_stateful():
    sentiment_response = await _post("/api/v1/sentiment/jobs", json={"texts": ["很好", "需要关注"]})
    assert sentiment_response.status_code == 200
    sentiment_payload = sentiment_response.json()
    assert sentiment_payload["code"] == 200
    sentiment_job_id = sentiment_payload["data"]["job_id"]
    assert sentiment_payload["data"]["status"] == "completed"
    assert sentiment_payload["data"]["success_count"] == 2

    detail_response = await _get(f"/api/v1/sentiment/jobs/{sentiment_job_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["job_id"] == sentiment_job_id

    retry_response = await _post(f"/api/v1/sentiment/jobs/{sentiment_job_id}/retry")
    assert retry_response.status_code == 200
    assert retry_response.json()["data"]["status"] == "completed"

    crawler_response = await _post("/api/v1/crawler/trigger", json={"platforms": ["weibo"], "is_async": True})
    assert crawler_response.status_code == 202
    crawler_task_id = crawler_response.json()["data"]["task_id"]

    pause_response = await _post(f"/api/v1/crawler/tasks/{crawler_task_id}/pause")
    assert pause_response.status_code == 200
    assert pause_response.json()["data"]["status"] == "paused"

    resume_response = await _post(f"/api/v1/crawler/tasks/{crawler_task_id}/resume")
    assert resume_response.status_code == 200
    assert resume_response.json()["data"]["status"] == "queued"

    cancel_response = await _post(f"/api/v1/crawler/tasks/{crawler_task_id}/cancel")
    assert cancel_response.status_code == 200
    assert cancel_response.json()["data"]["status"] == "cancelled"


@pytest.mark.asyncio
async def test_ui_contract_archive_endpoint_records_non_destructive_archive():
    response = await _post("/api/v1/data/archive", json={"retention_days": 3650})
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 200
    assert payload["data"]["status"] == "completed"
    archive_path = payload["data"].get("archive_path")
    assert archive_path

    path = Path(archive_path)
    assert path.exists()
    path.unlink()
