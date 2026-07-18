"""LIME 风格扰动式模型解释服务

模块名称: model_explanation_service.py
模块职责: 基于 token 扰动采样的情感模型解释、贡献度计算与持久化

实现说明:
    不引入 shap/lime 等外部依赖，仅使用 numpy 实现 LIME 核心思想：
    对输入文本做 token 级留一(leave-one-out)与随机掩码采样，
    调用当前激活情感模型对扰动样本打分，再以核加权岭回归拟合
    局部线性代理，回归系数即为各 token 对 positive/negative 分数的贡献。
"""

from __future__ import annotations

import json
import logging
import random
import re
from typing import Any, Callable

import numpy as np
from sqlalchemy.orm import Session

from app.models import FeatureContribution, ModelExplanation, SentimentResult
from app.services.model_registry_service import (
    model_version_payload,
    select_sentiment_model_version,
)

logger = logging.getLogger(__name__)

DEFAULT_N_SAMPLES = 200
MIN_N_SAMPLES = 20
MAX_N_SAMPLES = 1000
MAX_EXPLAINED_TOKENS = 32
TOP_TOKEN_LIMIT = 12
KERNEL_WIDTH = 0.75
RIDGE_ALPHA = 1e-3
RANDOM_SEED = 42

METHOD = "lime"
LABEL_ZH = {"positive": "正面", "negative": "负面", "neutral": "中性"}
TOKEN_PATTERN = re.compile(r"[一-鿿A-Za-z0-9]+")

ScoreFn = Callable[[list[str]], list[dict[str, float]]]


def _tokenize(text: str) -> list[str]:
    """中文分词并去重（保序），限制最大 token 数以控制扰动成本。"""
    try:
        import jieba

        raw_tokens = jieba.lcut(text)
    except Exception:
        raw_tokens = TOKEN_PATTERN.findall(text)

    tokens: list[str] = []
    seen: set[str] = set()
    for raw in raw_tokens:
        cleaned = raw.strip()
        if not cleaned or not TOKEN_PATTERN.fullmatch(cleaned) or cleaned in seen:
            continue
        seen.add(cleaned)
        tokens.append(cleaned)
        if len(tokens) >= MAX_EXPLAINED_TOKENS:
            break
    return tokens


def _build_masks(n_tokens: int, n_samples: int) -> np.ndarray:
    """构造扰动掩码矩阵：全保留 + 逐 token 留一 + 随机掩码。"""
    rng = random.Random(RANDOM_SEED)
    rows = [[1] * n_tokens]
    for index in range(n_tokens):
        row = [1] * n_tokens
        row[index] = 0
        rows.append(row)
    while len(rows) < n_samples:
        row = [1 if rng.random() < 0.5 else 0 for _ in range(n_tokens)]
        if any(row):
            rows.append(row)
    return np.asarray(rows, dtype=float)


def _fit_contributions(masks: np.ndarray, scores: list[dict[str, float]]) -> np.ndarray:
    """核加权岭回归拟合局部线性代理，返回各 token 的 (beta_pos - beta_neg)。"""
    n_samples, n_tokens = masks.shape
    design = np.hstack([np.ones((n_samples, 1)), masks])
    distances = 1.0 - np.sqrt(masks.sum(axis=1) / n_tokens)
    weights = np.exp(-(distances**2) / (KERNEL_WIDTH**2))
    targets = np.column_stack([
        [score["positive"] for score in scores],
        [score["negative"] for score in scores],
    ])
    weighted_x = design * weights[:, None]
    reg = RIDGE_ALPHA * np.eye(n_tokens + 1)
    reg[0, 0] = 0.0
    try:
        beta = np.linalg.solve(weighted_x.T @ design + reg, weighted_x.T @ targets)
    except np.linalg.LinAlgError:
        beta = np.linalg.pinv(weighted_x.T @ design + reg) @ (weighted_x.T @ targets)
    return beta[1:, 0] - beta[1:, 1]


def _normalize_scores(raw: dict[str, Any], *, provider: str) -> dict[str, float]:
    """统一 classic / transformers 输出为 positive/negative/neutral 分数字典。"""
    if provider == "transformers":
        positive = float(raw.get("positive_score") or 0.0)
        negative = float(raw.get("negative_score") or 0.0)
        neutral = float(raw.get("neutral_score") or max(0.0, 1.0 - positive - negative))
    else:
        scores = raw.get("scores") or {}
        positive = float(scores.get("positive") or 0.0)
        negative = float(scores.get("negative") or 0.0)
        neutral = float(scores.get("neutral") or max(0.0, 1.0 - positive - negative))
    clamp = lambda value: round(max(0.0, min(1.0, value)), 4)
    return {"positive": clamp(positive), "negative": clamp(negative), "neutral": clamp(neutral)}


class ModelExplanationService:
    """对当前激活情感模型执行 LIME 风格的扰动解释并持久化结果。"""

    def __init__(self, db: Session):
        self.db = db

    def explain_sentiment_result(
        self,
        sentiment_result_id: int,
        *,
        n_samples: int = DEFAULT_N_SAMPLES,
    ) -> dict[str, Any] | None:
        """解释已入库的情感分析结果，结果不存在时返回 None。"""
        sentiment = self.db.query(SentimentResult).filter(
            SentimentResult.id == sentiment_result_id,
        ).first()
        if not sentiment:
            return None
        topic = sentiment.hot_topic
        parts = [topic.title if topic else "", topic.content_summary if topic else ""]
        text = " ".join(part for part in parts if part).strip()
        if not text:
            raise ValueError("关联话题缺少可解释的文本内容")
        return self.explain_text(text, n_samples=n_samples, sentiment_result_id=sentiment_result_id)

    def explain_text(
        self,
        text: str,
        *,
        n_samples: int = DEFAULT_N_SAMPLES,
        sentiment_result_id: int | None = None,
    ) -> dict[str, Any]:
        """对单条文本执行扰动解释；关联结果时持久化到解释表。"""
        text = (text or "").strip()
        if not text:
            raise ValueError("text 不能为空")
        tokens = _tokenize(text)
        if not tokens:
            raise ValueError("文本中没有可解释的 token")

        n_samples = max(MIN_N_SAMPLES, min(MAX_N_SAMPLES, int(n_samples or DEFAULT_N_SAMPLES)))
        score_fn, model_version = self._build_score_fn()
        masks = _build_masks(len(tokens), max(n_samples, len(tokens) + 1))
        perturbed = [" ".join(token for token, keep in zip(tokens, row) if keep) for row in masks]
        scores = score_fn(perturbed)
        contributions = _fit_contributions(masks, scores)
        token_items = self._build_token_items(tokens, contributions)

        base = scores[0]
        label = max(base, key=base.get)
        summary = self._build_summary(label, base[label], token_items)
        explanation_id = None
        if sentiment_result_id is not None:
            explanation_id = self._persist(
                sentiment_result_id, text, base, model_version, len(masks), token_items, summary,
            )
        return {
            "explanation_id": explanation_id,
            "sentiment_result_id": sentiment_result_id,
            "method": METHOD,
            "model_version": model_version,
            "summary": summary,
            "text": text,
            "sentiment_label": label,
            "confidence": base[label],
            "scores": base,
            "n_samples": len(masks),
            "persisted": explanation_id is not None,
            "tokens": token_items,
        }

    def _build_score_fn(self) -> tuple[ScoreFn, str]:
        """按模型注册表选择当前激活版本，返回批量打分函数与版本号。"""
        model_version = select_sentiment_model_version(self.db)
        payload = model_version_payload(model_version)
        if payload["provider"] == "transformers":
            from app.ml.sentiment_transformers import get_analyzer

            analyzer = get_analyzer()

            def score_transformers(texts: list[str]) -> list[dict[str, float]]:
                return [_normalize_scores(analyzer.analyze(text), provider="transformers") for text in texts]

            return score_transformers, model_version.version

        from app.services.sentiment_service import SentimentService

        service = SentimentService(db=None)

        def score_classic(texts: list[str]) -> list[dict[str, float]]:
            return [_normalize_scores(item, provider="classic") for item in service.analyze_batch(texts)]

        return score_classic, model_version.version

    def _build_token_items(
        self,
        tokens: list[str],
        contributions: np.ndarray,
    ) -> list[dict[str, Any]]:
        """整理 token 贡献列表，按 |贡献| 降序并标注方向。"""
        items = []
        for token, contribution in zip(tokens, contributions):
            value = round(float(contribution), 4)
            items.append({
                "token": token,
                "contribution": value,
                "direction": "positive" if value >= 0 else "negative",
            })
        items.sort(key=lambda item: abs(item["contribution"]), reverse=True)
        return [
            {**item, "rank": rank}
            for rank, item in enumerate(items[:TOP_TOKEN_LIMIT], start=1)
        ]

    def _build_summary(
        self,
        label: str,
        confidence: float,
        token_items: list[dict[str, Any]],
    ) -> str:
        """生成中文解释摘要。"""
        label_zh = LABEL_ZH.get(label, label)
        significant = [item for item in token_items if abs(item["contribution"]) > 1e-4][:3]
        if not significant:
            return f"判定为{label_zh}（置信度{confidence:.1%}），未识别出显著贡献词。"
        parts = "、".join(
            f"{item['token']}（{'正向' if item['direction'] == 'positive' else '负向'}）"
            for item in significant
        )
        return f"判定为{label_zh}（置信度{confidence:.1%}），主要贡献词：{parts}。"

    def _persist(
        self,
        sentiment_result_id: int,
        text: str,
        base: dict[str, float],
        model_version: str,
        n_samples: int,
        token_items: list[dict[str, Any]],
        summary: str,
    ) -> int:
        """将解释与特征贡献写入 model_explanations / feature_contributions。"""
        explanation = ModelExplanation(
            sentiment_result_id=sentiment_result_id,
            method=METHOD,
            summary=summary,
            input_features_json=json.dumps(
                {"text": text, "scores": base, "model_version": model_version, "n_samples": n_samples},
                ensure_ascii=False,
            ),
            explanation_json=json.dumps({"tokens": token_items}, ensure_ascii=False),
        )
        self.db.add(explanation)
        self.db.flush()
        for item in token_items:
            self.db.add(FeatureContribution(
                explanation_id=explanation.id,
                feature_name=item["token"],
                feature_value=item["token"],
                contribution=item["contribution"],
                importance_rank=item["rank"],
            ))
        self.db.commit()
        logger.info("Persisted model explanation %s for sentiment result %s", explanation.id, sentiment_result_id)
        return explanation.id
