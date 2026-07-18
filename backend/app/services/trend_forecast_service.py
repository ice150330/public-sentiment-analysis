"""Trend forecasting service backed by SQLite time series."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from statistics import mean, pstdev
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from app.models import HotTopic, PredictionFeature, SentimentResult, TrendPrediction

try:  # statsmodels is optional at runtime; EMA remains the safe fallback.
    from statsmodels.tsa.arima.model import ARIMA
except Exception:  # pragma: no cover - exercised only when dependency is absent
    ARIMA = None


@dataclass
class SeriesPoint:
    timestamp: datetime
    value: float
    volume: int = 1
    negative_ratio: float = 0.0
    platform_count: int = 1


class TrendForecastService:
    """Build heat, volume, and sentiment forecasts from persisted topic data."""

    def __init__(self, history_days: int = 30):
        self.history_days = history_days

    def create_prediction(
        self,
        db: Session,
        target_type: str = "sentiment",
        target_id: int | None = None,
        model_type: str = "auto",
        horizon_hours: int = 24,
    ) -> dict[str, Any]:
        target_type = self._normalize_target_type(target_type)
        horizon_hours = max(1, min(int(horizon_hours or 24), 24 * 30))
        horizon_steps = max(1, math.ceil(horizon_hours / 24))
        points = self.get_series(db, target_type=target_type, target_id=target_id)
        if not points:
            raise ValueError("No historical data found for prediction")

        result = self.forecast_points(points, horizon_steps=horizon_steps, model_type=model_type, target_type=target_type)
        current_value = points[-1].value
        final_point = result["forecast"][-1]
        trend_direction, trend_strength = self._trend(current_value, final_point["predicted_value"], target_type)

        prediction = TrendPrediction(
            target_type=target_type,
            target_id=target_id,
            model_type=result["model"],
            horizon_hours=horizon_hours,
            params_json=json.dumps(
                {
                    "requested_model": model_type,
                    "history_points": len(points),
                    "history": self._history_payload(points),
                    "forecast": result["forecast"],
                    "metrics": result["metrics"],
                    "generated_at": datetime.now().isoformat(),
                },
                ensure_ascii=False,
                default=str,
            ),
            current_value=current_value,
            predicted_value=final_point["predicted_value"],
            confidence_lower=final_point["confidence_lower"],
            confidence_upper=final_point["confidence_upper"],
            confidence_level=0.95,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            mse=result["metrics"].get("mse"),
            mae=result["metrics"].get("mae"),
            r2_score=result["metrics"].get("r2_score"),
        )
        db.add(prediction)
        db.flush()

        for item in result["features"]:
            db.add(
                PredictionFeature(
                    prediction_id=prediction.id,
                    feature_name=item["feature_name"],
                    feature_value=item["feature_value"],
                    importance_score=item["importance_score"],
                )
            )

        db.commit()
        db.refresh(prediction)
        return self.serialize_prediction(prediction, features=result["features"])

    def get_prediction_detail(self, db: Session, prediction_id: int) -> dict[str, Any] | None:
        prediction = db.query(TrendPrediction).filter(TrendPrediction.id == prediction_id).first()
        if not prediction:
            return None
        features = db.query(PredictionFeature).filter(
            PredictionFeature.prediction_id == prediction_id
        ).order_by(PredictionFeature.importance_score.desc()).all()
        return self.serialize_prediction(
            prediction,
            features=[
                {
                    "id": feature.id,
                    "feature_name": feature.feature_name,
                    "feature_value": feature.feature_value,
                    "importance_score": feature.importance_score,
                }
                for feature in features
            ],
        )

    def forecast_heat(self, db: Session, topic_id: int | None = None, horizon_days: int = 7) -> dict[str, Any]:
        horizon_days = max(1, min(int(horizon_days or 7), 30))
        points = self.get_series(db, target_type="heat", target_id=topic_id)
        if not points:
            return {
                "topic_id": topic_id,
                "current_heat": 0,
                "forecast": [],
                "model": "no-data",
                "metrics": {},
                "signals": [],
            }
        result = self.forecast_points(points, horizon_steps=horizon_days, model_type="auto", target_type="heat")
        return {
            "topic_id": topic_id,
            "current_heat": round(points[-1].value, 2),
            "forecast": result["forecast"],
            "model": result["model"],
            "metrics": result["metrics"],
            "signals": self.forecast_signals(db, topic_id=topic_id)["signals"],
        }

    def forecast_signals(self, db: Session, topic_id: int | None = None) -> dict[str, Any]:
        heat_points = self.get_series(db, target_type="heat", target_id=topic_id, days=14)
        sentiment_points = self.get_series(db, target_type="sentiment", target_id=topic_id, days=14)
        volume_points = self.get_series(db, target_type="volume", target_id=None, days=14)
        signals = [
            self._signal_from_points("heat_momentum", heat_points, "Heat momentum"),
            self._signal_from_points("negative_momentum", sentiment_points, "Negative sentiment pressure", invert=True),
            self._signal_from_points("cross_platform_spread", volume_points, "Cross-platform spread"),
        ]
        return {"topic_id": topic_id, "signals": signals}

    def forecast_scenarios(self, db: Session, topic_id: int | None = None) -> dict[str, Any]:
        signals = self.forecast_signals(db, topic_id=topic_id)["signals"]
        heat_signal = next((item for item in signals if item["name"] == "heat_momentum"), {})
        negative_signal = next((item for item in signals if item["name"] == "negative_momentum"), {})
        risk_score = 0.25
        if heat_signal.get("direction") == "up":
            risk_score += 0.15
        if negative_signal.get("direction") == "up":
            risk_score += 0.15
        risk_score = min(0.75, risk_score)
        ease_score = max(0.1, 0.35 - risk_score / 3)
        baseline = max(0.1, 1 - risk_score - ease_score)
        total = baseline + risk_score + ease_score
        scenarios = [
            {
                "name": "baseline",
                "probability": round(baseline / total, 3),
                "description": "Current heat and sentiment continue near the recent trend.",
            },
            {
                "name": "risk",
                "probability": round(risk_score / total, 3),
                "description": "Heat or negative sentiment accelerates and may trigger earlier alerts.",
            },
            {
                "name": "ease",
                "probability": round(ease_score / total, 3),
                "description": "Heat cools down and sentiment pressure returns toward neutral.",
            },
        ]
        return {"topic_id": topic_id, "scenarios": scenarios, "signals": signals}

    def get_series(
        self,
        db: Session,
        target_type: str,
        target_id: int | None = None,
        days: int | None = None,
    ) -> list[SeriesPoint]:
        target_type = self._normalize_target_type(target_type)
        days = days or self.history_days
        if target_type == "heat":
            return self._heat_series(db, target_id=target_id, days=days)
        if target_type == "volume":
            return self._volume_series(db, days=days)
        return self._sentiment_series(db, target_id=target_id, days=days)

    def forecast_points(
        self,
        points: list[SeriesPoint],
        horizon_steps: int,
        model_type: str = "auto",
        target_type: str = "heat",
    ) -> dict[str, Any]:
        values = [max(0.0, float(point.value or 0)) for point in points]
        model, predictions, lower, upper = self._forecast_values(values, horizon_steps, model_type, target_type)
        last_date = points[-1].timestamp.date()
        forecast = []
        for index, value in enumerate(predictions):
            forecast.append(
                {
                    "date": (last_date + timedelta(days=index + 1)).isoformat(),
                    "predicted_heat": round(value, 2),
                    "predicted_value": round(value, 4),
                    "confidence_lower": round(lower[index], 4),
                    "confidence_upper": round(upper[index], 4),
                }
            )
        return {
            "model": model,
            "forecast": forecast,
            "metrics": self._rolling_metrics(values, model_type=model_type, target_type=target_type),
            "features": self._feature_importance(points),
        }

    def serialize_prediction(self, prediction: TrendPrediction, features: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        params = self._json_loads(prediction.params_json)
        return {
            "prediction_id": prediction.id,
            "id": prediction.id,
            "target_type": prediction.target_type,
            "target_id": prediction.target_id,
            "model_type": prediction.model_type,
            "model": prediction.model_type,
            "horizon_hours": prediction.horizon_hours,
            "current_value": prediction.current_value,
            "predicted_value": prediction.predicted_value,
            "confidence_lower": prediction.confidence_lower,
            "confidence_upper": prediction.confidence_upper,
            "confidence_level": prediction.confidence_level,
            "trend_direction": prediction.trend_direction,
            "trend_strength": prediction.trend_strength,
            "mse": prediction.mse,
            "mae": prediction.mae,
            "r2_score": prediction.r2_score,
            "metrics": params.get("metrics") or {
                "mse": prediction.mse,
                "mae": prediction.mae,
                "r2_score": prediction.r2_score,
            },
            "forecast": params.get("forecast", []),
            "history": params.get("history", []),
            "features": features or [],
            "created_at": prediction.created_at.isoformat() if prediction.created_at else None,
        }

    def _heat_series(self, db: Session, target_id: int | None, days: int) -> list[SeriesPoint]:
        since = datetime.now() - timedelta(days=days)
        query = db.query(HotTopic).filter(HotTopic.crawl_time >= since)
        if target_id:
            root = db.query(HotTopic).filter(HotTopic.id == target_id).first()
            if not root:
                return []
            rows = query.filter(
                HotTopic.platform_id == root.platform_id,
                HotTopic.topic_id == root.topic_id,
            ).order_by(HotTopic.crawl_time).all()
            if len(rows) < 3:
                rows = db.query(HotTopic).filter(
                    HotTopic.crawl_time >= since,
                    HotTopic.title == root.title,
                ).order_by(HotTopic.crawl_time).all()
        else:
            rows = query.order_by(HotTopic.crawl_time).limit(5000).all()
        return self._aggregate_topics(rows, mode="average" if not target_id else "max")

    def _volume_series(self, db: Session, days: int) -> list[SeriesPoint]:
        since = datetime.now() - timedelta(days=days)
        rows = db.query(HotTopic).filter(HotTopic.crawl_time >= since).order_by(HotTopic.crawl_time).limit(5000).all()
        return self._aggregate_topics(rows, mode="count")

    def _sentiment_series(self, db: Session, target_id: int | None, days: int) -> list[SeriesPoint]:
        since = datetime.now() - timedelta(days=days)
        query = db.query(SentimentResult).join(HotTopic).filter(SentimentResult.analyzed_at >= since)
        if target_id:
            root = db.query(HotTopic).filter(HotTopic.id == target_id).first()
            if not root:
                return []
            query = query.filter(HotTopic.title == root.title)
        results = query.order_by(SentimentResult.analyzed_at).limit(5000).all()
        buckets: dict[date, list[SentimentResult]] = defaultdict(list)
        for result in results:
            timestamp = result.analyzed_at or result.created_at or datetime.now()
            buckets[timestamp.date()].append(result)

        points = []
        for day in sorted(buckets):
            items = buckets[day]
            values = [self._sentiment_value(item) for item in items]
            negative_count = sum(1 for item in items if item.sentiment_label == "negative")
            points.append(
                SeriesPoint(
                    timestamp=datetime.combine(day, datetime.min.time()),
                    value=mean(values) if values else 0.5,
                    volume=len(items),
                    negative_ratio=negative_count / len(items) if items else 0.0,
                    platform_count=len({item.hot_topic.platform_id for item in items if item.hot_topic}),
                )
            )
        return points

    def _aggregate_topics(self, rows: list[HotTopic], mode: str) -> list[SeriesPoint]:
        buckets: dict[date, list[HotTopic]] = defaultdict(list)
        for row in rows:
            timestamp = row.crawl_time or row.created_at or datetime.now()
            buckets[timestamp.date()].append(row)

        points = []
        for day in sorted(buckets):
            items = buckets[day]
            heats = [float(item.heat_score or 0) for item in items]
            if mode == "count":
                value = float(len(items))
            elif mode == "max":
                value = max(heats) if heats else 0.0
            else:
                value = mean(heats) if heats else 0.0
            points.append(
                SeriesPoint(
                    timestamp=datetime.combine(day, datetime.min.time()),
                    value=value,
                    volume=len(items),
                    platform_count=len({item.platform_id for item in items}),
                )
            )
        return points

    def _forecast_values(
        self,
        values: list[float],
        steps: int,
        model_type: str,
        target_type: str,
    ) -> tuple[str, list[float], list[float], list[float]]:
        if len(values) == 1:
            predictions = [values[0] for _ in range(steps)]
            lower, upper = self._confidence_bounds(values, predictions, target_type)
            return "baseline", predictions, lower, upper

        use_arima = model_type in {"auto", "arima"} and ARIMA is not None and len(values) >= 6 and len(set(values)) > 1
        if use_arima:
            try:
                fit = ARIMA(values, order=(1, 1, 1)).fit()
                forecast_result = fit.get_forecast(steps=steps)
                predictions = [float(item) for item in forecast_result.predicted_mean]
                conf_int = np.asarray(forecast_result.conf_int(alpha=0.05))
                lower = [float(row[0]) for row in conf_int]
                upper = [float(row[1]) for row in conf_int]
                return "arima", *self._clamp_forecast(predictions, lower, upper, target_type)
            except Exception:
                pass

        predictions = self._ema_predictions(values, steps)
        lower, upper = self._confidence_bounds(values, predictions, target_type)
        return "ema", predictions, lower, upper

    def _ema_predictions(self, values: list[float], steps: int, alpha: float = 0.35) -> list[float]:
        ema = values[0]
        for value in values[1:]:
            ema = alpha * value + (1 - alpha) * ema
        recent = values[-min(5, len(values)) :]
        trend = (recent[-1] - recent[0]) / max(1, len(recent) - 1)
        return [ema + trend * (step + 1) for step in range(steps)]

    def _confidence_bounds(
        self,
        values: list[float],
        predictions: list[float],
        target_type: str,
    ) -> tuple[list[float], list[float]]:
        residual_std = pstdev(values) if len(values) > 1 else 0.0
        baseline = max(abs(values[-1]) * 0.05, 0.02 if target_type == "sentiment" else 1.0)
        sigma = max(residual_std, baseline)
        lower = [value - 1.96 * sigma * math.sqrt(index + 1) for index, value in enumerate(predictions)]
        upper = [value + 1.96 * sigma * math.sqrt(index + 1) for index, value in enumerate(predictions)]
        return self._clamp_forecast(predictions, lower, upper, target_type)[1:]

    def _clamp_forecast(
        self,
        predictions: list[float],
        lower: list[float],
        upper: list[float],
        target_type: str,
    ) -> tuple[list[float], list[float], list[float]]:
        max_value = 1.0 if target_type == "sentiment" else None

        def clamp(value: float) -> float:
            value = max(0.0, float(value))
            return min(max_value, value) if max_value is not None else value

        predictions = [clamp(value) for value in predictions]
        lower = [clamp(value) for value in lower]
        upper = [max(predictions[index], clamp(value)) for index, value in enumerate(upper)]
        return predictions, lower, upper

    def _rolling_metrics(self, values: list[float], model_type: str, target_type: str) -> dict[str, float | int | None]:
        if len(values) < 4:
            return {"mse": None, "mae": None, "mape": None, "r2_score": None, "backtest_points": 0}
        holdout = min(5, max(1, len(values) // 4))
        train = values[:-holdout]
        actual = values[-holdout:]
        if not train:
            return {"mse": None, "mae": None, "mape": None, "r2_score": None, "backtest_points": 0}
        _, predicted, _, _ = self._forecast_values(train, holdout, model_type, target_type)
        errors = [predicted[index] - actual[index] for index in range(holdout)]
        mse = mean([error * error for error in errors])
        mae = mean([abs(error) for error in errors])
        non_zero_actual = [abs(item) for item in actual if abs(item) > 1e-9]
        if non_zero_actual:
            mape = mean([abs(errors[index]) / max(abs(actual[index]), 1e-9) for index in range(holdout)])
        else:
            mape = None
        variance = sum((item - mean(actual)) ** 2 for item in actual)
        r2 = 1 - (sum(error * error for error in errors) / variance) if variance > 1e-9 else None
        return {
            "mse": round(mse, 6),
            "mae": round(mae, 6),
            "mape": round(mape, 6) if mape is not None else None,
            "r2_score": round(r2, 6) if r2 is not None else None,
            "backtest_points": holdout,
        }

    def _feature_importance(self, points: list[SeriesPoint]) -> list[dict[str, float | str]]:
        values = [point.value for point in points]
        recent = values[-min(3, len(values)) :]
        previous = values[-min(6, len(values)) : -min(3, len(values))] if len(values) > 3 else values[:1]
        recent_mean = mean(recent) if recent else 0.0
        previous_mean = mean(previous) if previous else recent_mean
        scale = max(abs(previous_mean), 1.0)
        recent_trend = (recent_mean - previous_mean) / scale
        volatility = (pstdev(values) / max(abs(mean(values)), 1.0)) if len(values) > 1 else 0.0
        volume_change = (points[-1].volume - points[0].volume) / max(points[0].volume, 1)
        negative_momentum = points[-1].negative_ratio
        platform_diversity = max(point.platform_count for point in points) / 6
        raw = [
            ("recent_trend", recent_trend, min(abs(recent_trend), 1.0) * 0.32 + 0.08),
            ("volatility", volatility, min(abs(volatility), 1.0) * 0.24 + 0.06),
            ("volume_change", volume_change, min(abs(volume_change), 1.0) * 0.18 + 0.05),
            ("negative_momentum", negative_momentum, min(abs(negative_momentum), 1.0) * 0.16 + 0.04),
            ("platform_diversity", platform_diversity, min(abs(platform_diversity), 1.0) * 0.10 + 0.03),
        ]
        total = sum(item[2] for item in raw) or 1.0
        return [
            {
                "feature_name": name,
                "feature_value": round(float(value), 6),
                "importance_score": round(float(weight / total), 6),
            }
            for name, value, weight in raw
        ]

    def _signal_from_points(
        self,
        name: str,
        points: list[SeriesPoint],
        description: str,
        invert: bool = False,
    ) -> dict[str, Any]:
        if len(points) < 2:
            return {"name": name, "value": 0, "direction": "stable", "description": description}
        first = points[0].value
        last = points[-1].value
        change = (last - first) / max(abs(first), 1.0)
        if invert:
            change = -change
            value = points[-1].negative_ratio
        else:
            value = last
        direction = "stable"
        if abs(change) >= 0.08:
            direction = "up" if change > 0 else "down"
        return {
            "name": name,
            "value": round(float(value), 4),
            "change_rate": round(float(change), 4),
            "direction": direction,
            "description": description,
        }

    def _trend(self, current: float, predicted: float, target_type: str) -> tuple[str, float]:
        threshold = 0.04 if target_type == "sentiment" else 0.08
        change = (predicted - current) / max(abs(current), 1.0)
        if abs(change) < threshold:
            return "stable", round(abs(change), 6)
        return ("up" if change > 0 else "down"), round(min(abs(change), 1.0), 6)

    def _sentiment_value(self, result: SentimentResult) -> float:
        if result.positive_score is not None or result.neutral_score is not None or result.negative_score is not None:
            return max(0.0, min(1.0, float(result.positive_score or 0) + 0.5 * float(result.neutral_score or 0)))
        if result.sentiment_label == "positive":
            return float(result.confidence or 0.5)
        if result.sentiment_label == "negative":
            return 1 - float(result.confidence or 0.5)
        return 0.5

    def _history_payload(self, points: list[SeriesPoint]) -> list[dict[str, Any]]:
        return [
            {
                "date": point.timestamp.date().isoformat(),
                "value": round(point.value, 4),
                "volume": point.volume,
                "negative_ratio": round(point.negative_ratio, 4),
                "platform_count": point.platform_count,
            }
            for point in points
        ]

    def _normalize_target_type(self, target_type: str) -> str:
        if target_type not in {"sentiment", "heat", "volume"}:
            return "sentiment"
        return target_type

    def _json_loads(self, value: str | None) -> dict[str, Any]:
        if not value:
            return {}
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
