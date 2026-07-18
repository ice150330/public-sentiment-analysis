"""Topic clustering service with optional embedding and deterministic fallback."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models import ClusterMember, HotTopic, TopicCluster


SENTIMENT_SCORE = {
    "negative": 0.0,
    "neutral": 0.5,
    "positive": 1.0,
}

STOP_WORDS = {
    "一个", "一些", "我们", "你们", "他们", "这个", "那个", "这些", "那些",
    "今日", "最新", "回应", "官方", "网友", "热议", "相关", "表示", "成为",
    "the", "and", "for", "with", "this", "that",
}


@dataclass
class ClusterDraft:
    label: int
    name: str
    description: str
    keywords: list[str]
    members: list[dict[str, Any]]
    dominant_sentiment: str
    avg_sentiment: float


class TopicClusteringService:
    """Build and persist topic clusters from recent hot topics."""

    def __init__(self, db: Session):
        self.db = db

    def run(
        self,
        *,
        algorithm: str = "kmeans",
        n_clusters: int = 5,
        time_window_hours: int = 24,
    ) -> dict[str, Any]:
        algorithm = algorithm.lower().strip()
        if algorithm not in {"kmeans", "hdbscan", "dbscan"}:
            raise ValueError("Unsupported clustering algorithm")

        n_clusters = max(1, min(20, int(n_clusters or 5)))
        time_window_hours = max(1, min(24 * 30, int(time_window_hours or 24)))
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=time_window_hours)
        topics = (
            self.db.query(HotTopic)
            .filter(HotTopic.crawl_time >= start_time)
            .order_by(HotTopic.heat_score.desc(), HotTopic.crawl_time.desc())
            .all()
        )
        if not topics:
            return {
                "clusters": [],
                "total_topics": 0,
                "algorithm": algorithm,
                "embedding_provider": None,
                "keywords_method": "tfidf",
                "message": "No topics found in the specified time window",
            }

        documents = [self._topic_document(topic) for topic in topics]
        vectors, embedding_provider = self._build_vectors(documents)
        labels, distances = self._assign_labels(vectors, algorithm=algorithm, n_clusters=n_clusters)
        drafts = self._build_cluster_drafts(topics, documents, labels, distances)
        clusters = self._persist_clusters(
            drafts,
            algorithm=algorithm,
            n_clusters=n_clusters,
            time_window_hours=time_window_hours,
            start_time=start_time,
            end_time=end_time,
            embedding_provider=embedding_provider,
        )
        return {
            "clusters": clusters,
            "total_topics": len(topics),
            "algorithm": algorithm,
            "embedding_provider": embedding_provider,
            "keywords_method": "tfidf",
        }

    def list_payload(self, cluster: TopicCluster) -> dict[str, Any]:
        params = self._json_loads(cluster.params_json)
        return {
            "id": cluster.id,
            "cluster_name": cluster.cluster_name,
            "description": cluster.description,
            "algorithm": cluster.algorithm,
            "params": params,
            "keywords": params.get("keywords", []),
            "embedding_provider": params.get("embedding_provider"),
            "topic_count": cluster.topic_count,
            "avg_sentiment": cluster.avg_sentiment,
            "dominant_sentiment": cluster.dominant_sentiment,
            "start_time": cluster.start_time.isoformat() if cluster.start_time else None,
            "end_time": cluster.end_time.isoformat() if cluster.end_time else None,
            "created_at": cluster.created_at.isoformat() if cluster.created_at else None,
        }

    def detail_payload(self, cluster: TopicCluster, page: int, page_size: int) -> dict[str, Any]:
        query = self.db.query(ClusterMember).filter(ClusterMember.cluster_id == cluster.id)
        total_members = query.count()
        members = (
            query.join(HotTopic)
            .order_by(ClusterMember.weight.desc(), HotTopic.heat_score.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        member_items = []
        for member in members:
            topic = member.topic
            member_items.append({
                "id": member.id,
                "topic_id": member.topic_id,
                "topic_title": topic.title if topic else None,
                "platform_name": topic.platform.display_name if topic and topic.platform else None,
                "weight": member.weight,
                "distance_to_center": member.distance_to_center,
                "features": self._json_loads(member.features_json),
                "heat_score": topic.heat_score if topic else None,
                "sentiment_label": topic.sentiment_result.sentiment_label if topic and topic.sentiment_result else None,
                "crawl_time": topic.crawl_time.isoformat() if topic and topic.crawl_time else None,
            })

        total_pages = (total_members + page_size - 1) // page_size
        return {
            "cluster": self.list_payload(cluster),
            "members": member_items,
            "representative_members": self._representative_members(cluster.id),
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total_members,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        }

    def _representative_members(self, cluster_id: int, *, limit: int = 5) -> list[dict[str, Any]]:
        """返回距质心最近的成员话题，作为聚类解释的代表性文档。"""
        members = (
            self.db.query(ClusterMember)
            .filter(ClusterMember.cluster_id == cluster_id)
            .join(HotTopic)
            .all()
        )
        ranked = sorted(
            (member for member in members if member.distance_to_center is not None),
            key=lambda member: member.distance_to_center,
        )[:limit]
        items = []
        for member in ranked:
            topic = member.topic
            items.append({
                "id": member.id,
                "topic_id": member.topic_id,
                "topic_title": topic.title if topic else None,
                "platform_name": topic.platform.display_name if topic and topic.platform else None,
                "distance_to_center": member.distance_to_center,
                "heat_score": topic.heat_score if topic else None,
            })
        return items

    def _build_vectors(self, documents: list[str]):
        embedding = self._try_sentence_transformers(documents)
        if embedding is not None:
            return embedding, "sentence-transformers"

        from sklearn.feature_extraction.text import TfidfVectorizer

        vectorizer = TfidfVectorizer(
            tokenizer=_tokenize,
            token_pattern=None,
            lowercase=False,
            max_features=512,
            min_df=1,
        )
        try:
            return vectorizer.fit_transform(documents), "tfidf"
        except ValueError:
            fallback_docs = [doc or f"topic-{index}" for index, doc in enumerate(documents)]
            return vectorizer.fit_transform(fallback_docs), "tfidf"

    def _try_sentence_transformers(self, documents: list[str]):
        try:
            from transformers.utils.hub import cached_file
            from sentence_transformers import SentenceTransformer
        except Exception:
            return None

        model_name = "paraphrase-multilingual-MiniLM-L12-v2"
        try:
            cached_file(model_name, "config.json", local_files_only=True)
            model = SentenceTransformer(model_name, local_files_only=True)
            return model.encode(documents, normalize_embeddings=True)
        except Exception:
            return None

    def _assign_labels(self, vectors, *, algorithm: str, n_clusters: int) -> tuple[list[int], list[float]]:
        topic_count = vectors.shape[0]
        if topic_count == 1:
            return [0], [0.0]

        if algorithm == "kmeans":
            from sklearn.cluster import KMeans

            effective_clusters = min(n_clusters, topic_count)
            model = KMeans(n_clusters=effective_clusters, random_state=42, n_init=10)
            raw_labels = model.fit_predict(vectors)
            distances_matrix = model.transform(vectors)
            distances = [
                float(distances_matrix[index][label]) if label >= 0 else 0.0
                for index, label in enumerate(raw_labels)
            ]
            return [int(label) for label in raw_labels], distances

        labels = self._density_labels(vectors, algorithm=algorithm, topic_count=topic_count)
        distances = self._centroid_distances(vectors, labels)
        return labels, distances

    def _density_labels(self, vectors, *, algorithm: str, topic_count: int) -> list[int]:
        if algorithm == "hdbscan":
            try:
                import hdbscan

                min_cluster_size = max(2, min(8, math.ceil(topic_count * 0.15)))
                model = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, metric="euclidean")
                return [int(label) for label in model.fit_predict(_to_dense(vectors))]
            except Exception:
                pass

        from sklearn.cluster import DBSCAN

        model = DBSCAN(eps=0.72, min_samples=2, metric="cosine")
        labels = [int(label) for label in model.fit_predict(vectors)]
        if all(label == -1 for label in labels):
            return [index % min(3, topic_count) for index in range(topic_count)]
        return labels

    def _centroid_distances(self, vectors, labels: list[int]) -> list[float]:
        dense = _to_dense(vectors)
        centroids = {}
        for label in sorted(set(labels)):
            if label == -1:
                continue
            rows = [dense[index] for index, current in enumerate(labels) if current == label]
            if rows:
                centroids[label] = sum(rows) / len(rows)

        distances = []
        for index, label in enumerate(labels):
            if label == -1 or label not in centroids:
                distances.append(1.0)
                continue
            diff = dense[index] - centroids[label]
            distances.append(float((diff * diff).sum() ** 0.5))
        return distances

    def _build_cluster_drafts(
        self,
        topics: list[HotTopic],
        documents: list[str],
        labels: list[int],
        distances: list[float],
    ) -> list[ClusterDraft]:
        grouped: dict[int, list[tuple[int, HotTopic, str, float]]] = {}
        for index, (topic, document, label, distance) in enumerate(zip(topics, documents, labels, distances)):
            grouped.setdefault(label, []).append((index, topic, document, distance))

        drafts = []
        for label, rows in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0])):
            keywords = self._extract_keywords([row[2] for row in rows], limit=8)
            dominant, average = self._sentiment_summary([row[1] for row in rows])
            name = " / ".join(keywords[:3]) if keywords else ("离群话题" if label == -1 else f"主题簇 {label + 1}")
            members = []
            for _, topic, _, distance in sorted(rows, key=lambda row: row[1].heat_score or 0, reverse=True):
                weight = round(1 / (1 + max(0.0, distance)), 4)
                members.append({
                    "topic_id": topic.id,
                    "weight": weight,
                    "distance": round(float(distance), 4),
                    "features": {
                        "title": topic.title,
                        "platform": topic.platform.name if topic.platform else None,
                        "heat_score": topic.heat_score,
                    },
                })
            drafts.append(ClusterDraft(
                label=label,
                name=name[:128],
                description=f"{len(rows)} 个话题聚合；关键词：{', '.join(keywords[:5])}" if keywords else f"{len(rows)} 个话题聚合",
                keywords=keywords,
                members=members,
                dominant_sentiment=dominant,
                avg_sentiment=average,
            ))
        return drafts

    def _persist_clusters(
        self,
        drafts: list[ClusterDraft],
        *,
        algorithm: str,
        n_clusters: int,
        time_window_hours: int,
        start_time: datetime,
        end_time: datetime,
        embedding_provider: str,
    ) -> list[dict[str, Any]]:
        self._replace_existing_run(algorithm=algorithm, start_time=start_time)
        created = []
        for draft in drafts:
            params = {
                "n_clusters": n_clusters,
                "time_window_hours": time_window_hours,
                "embedding_provider": embedding_provider,
                "keywords": draft.keywords,
                "label": draft.label,
            }
            cluster = TopicCluster(
                cluster_name=draft.name,
                description=draft.description,
                algorithm=algorithm,
                params_json=json.dumps(params, ensure_ascii=False, sort_keys=True),
                topic_count=len(draft.members),
                avg_sentiment=draft.avg_sentiment,
                dominant_sentiment=draft.dominant_sentiment,
                start_time=start_time,
                end_time=end_time,
            )
            self.db.add(cluster)
            self.db.flush()
            for member_data in draft.members:
                self.db.add(ClusterMember(
                    cluster_id=cluster.id,
                    topic_id=member_data["topic_id"],
                    weight=member_data["weight"],
                    distance_to_center=member_data["distance"],
                    features_json=json.dumps(member_data["features"], ensure_ascii=False, sort_keys=True),
                ))
            created.append({
                "id": cluster.id,
                "name": cluster.cluster_name,
                "cluster_name": cluster.cluster_name,
                "topic_count": cluster.topic_count,
                "keywords": draft.keywords,
                "dominant_sentiment": cluster.dominant_sentiment,
            })
        self.db.commit()
        return created

    def _replace_existing_run(self, *, algorithm: str, start_time: datetime) -> None:
        existing = (
            self.db.query(TopicCluster)
            .filter(TopicCluster.algorithm == algorithm, TopicCluster.start_time >= start_time)
            .all()
        )
        for cluster in existing:
            self.db.delete(cluster)
        if existing:
            self.db.flush()

    def _extract_keywords(self, documents: list[str], *, limit: int) -> list[str]:
        tokens = [token for doc in documents for token in _tokenize(doc)]
        if not tokens:
            return []

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer

            vectorizer = TfidfVectorizer(
                tokenizer=_tokenize,
                token_pattern=None,
                lowercase=False,
                max_features=80,
            )
            matrix = vectorizer.fit_transform(documents)
            scores = matrix.sum(axis=0).A1
            names = vectorizer.get_feature_names_out()
            ranked = sorted(zip(names, scores), key=lambda item: item[1], reverse=True)
            return [name for name, _ in ranked[:limit]]
        except Exception:
            return [token for token, _ in Counter(tokens).most_common(limit)]

    def _sentiment_summary(self, topics: list[HotTopic]) -> tuple[str, float]:
        labels = [
            topic.sentiment_result.sentiment_label
            for topic in topics
            if topic.sentiment_result and topic.sentiment_result.sentiment_label
        ]
        if not labels:
            return "neutral", 0.5
        dominant = Counter(labels).most_common(1)[0][0]
        average = sum(SENTIMENT_SCORE.get(label, 0.5) for label in labels) / len(labels)
        return dominant, round(average, 4)

    def _topic_document(self, topic: HotTopic) -> str:
        parts = [
            topic.title,
            topic.content_summary or "",
            topic.category or "",
            topic.platform.display_name if topic.platform else "",
        ]
        return " ".join(part for part in parts if part).strip()

    def _json_loads(self, value: str | None) -> dict[str, Any]:
        if not value:
            return {}
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}


def _tokenize(text: str) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    try:
        import jieba

        raw_tokens = jieba.lcut(text)
    except Exception:
        raw_tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9]{2,}", text)

    tokens = []
    for token in raw_tokens:
        cleaned = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", token).strip()
        if len(cleaned) < 2 or cleaned.lower() in STOP_WORDS:
            continue
        tokens.append(cleaned)
    if tokens:
        return tokens

    return re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9]{2,}", text)


def _to_dense(vectors):
    if hasattr(vectors, "toarray"):
        return vectors.toarray()
    return vectors
