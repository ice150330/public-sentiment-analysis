"""Propagation path analysis based on text similarity and event timing."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models import HotTopic, PropagationNode, PropagationPath
from app.services.topic_clustering_service import _tokenize


@dataclass
class CandidateMatch:
    topic: HotTopic
    similarity: float
    delay_hours: float


class PropagationAnalysisService:
    """Analyze cross-platform propagation with vector similarity."""

    def __init__(self, db: Session):
        self.db = db

    def analyze(
        self,
        topic_id: int,
        *,
        time_window_hours: int = 24,
        similarity_threshold: float = 0.18,
        max_nodes: int = 30,
    ) -> dict[str, Any]:
        root_topic = self.db.query(HotTopic).filter(HotTopic.id == topic_id).first()
        if not root_topic:
            raise ValueError("Topic not found")

        time_window_hours = max(1, min(24 * 30, int(time_window_hours or 24)))
        similarity_threshold = max(0.0, min(1.0, float(similarity_threshold)))
        max_nodes = max(2, min(100, int(max_nodes or 30)))

        window_start = root_topic.crawl_time - timedelta(hours=6)
        window_end = root_topic.crawl_time + timedelta(hours=time_window_hours)
        candidates = (
            self.db.query(HotTopic)
            .filter(
                HotTopic.crawl_time >= window_start,
                HotTopic.crawl_time <= window_end,
                HotTopic.id != root_topic.id,
            )
            .order_by(HotTopic.crawl_time.asc(), HotTopic.heat_score.desc())
            .all()
        )

        documents = [self._topic_document(root_topic)] + [self._topic_document(topic) for topic in candidates]
        vectors, provider = self._build_vectors(documents)
        similarity_matrix = self._cosine_similarity(vectors)
        root_similarities = similarity_matrix[0]

        matches: list[CandidateMatch] = []
        for index, topic in enumerate(candidates, start=1):
            similarity = float(root_similarities[index])
            overlap_bonus = self._token_overlap(documents[0], documents[index])
            similarity = min(1.0, max(similarity, overlap_bonus))
            if similarity < similarity_threshold:
                continue
            delay = (topic.crawl_time - root_topic.crawl_time).total_seconds() / 3600
            matches.append(CandidateMatch(topic=topic, similarity=round(similarity, 4), delay_hours=round(delay, 3)))

        matches = sorted(matches, key=lambda item: (item.topic.crawl_time, -item.similarity, -(item.topic.heat_score or 0)))
        matches = matches[: max_nodes - 1]
        path = self._persist_path(
            root_topic,
            matches,
            similarity_matrix,
            documents,
            provider=provider,
            time_window_hours=time_window_hours,
            similarity_threshold=similarity_threshold,
        )
        return self.detail_payload(path)

    def list_payload(self, path: PropagationPath) -> dict[str, Any]:
        platforms = self._json_loads(path.platforms_involved, fallback=[])
        return {
            "id": path.id,
            "root_topic_id": path.root_topic_id,
            "root_topic_title": path.root_topic.title if path.root_topic else None,
            "depth": path.depth,
            "total_nodes": path.total_nodes,
            "max_breadth": path.max_breadth,
            "platforms_involved": platforms,
            "platform_transitions": path.platform_transitions,
            "first_seen_at": path.first_seen_at.isoformat() if path.first_seen_at else None,
            "last_seen_at": path.last_seen_at.isoformat() if path.last_seen_at else None,
            "created_at": path.created_at.isoformat() if path.created_at else None,
        }

    def detail_payload(self, path: PropagationPath) -> dict[str, Any]:
        nodes = (
            self.db.query(PropagationNode)
            .filter(PropagationNode.path_id == path.id)
            .order_by(PropagationNode.level.asc(), PropagationNode.discovered_at.asc(), PropagationNode.id.asc())
            .all()
        )
        node_map: dict[int, dict[str, Any]] = {}
        flat_nodes: list[dict[str, Any]] = []
        root_nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        for node in nodes:
            features = self._json_loads(node.features_json, fallback={})
            node_data = {
                "id": node.id,
                "topic_id": node.topic_id,
                "topic_title": node.topic.title if node.topic else None,
                "platform_name": node.platform.display_name if node.platform else None,
                "level": node.level,
                "parent_node_id": node.parent_node_id,
                "heat_score": node.heat_score,
                "sentiment_label": node.sentiment_label,
                "influence_score": node.influence_score,
                "similarity_score": features.get("similarity_score"),
                "delay_hours": features.get("delay_hours"),
                "match_method": features.get("match_method"),
                "discovered_at": node.discovered_at.isoformat() if node.discovered_at else None,
                "children": [],
            }
            node_map[node.id] = node_data
            flat_nodes.append(node_data)

        for node in nodes:
            node_data = node_map[node.id]
            if node.parent_node_id and node.parent_node_id in node_map:
                parent = node_map[node.parent_node_id]
                parent["children"].append(node_data)
                edges.append({
                    "source": node.parent_node_id,
                    "target": node.id,
                    "similarity_score": node_data["similarity_score"],
                    "delay_hours": node_data["delay_hours"],
                })
            else:
                root_nodes.append(node_data)

        return {
            "path": self.list_payload(path),
            "tree": root_nodes,
            "nodes": flat_nodes,
            "edges": edges,
        }

    def _persist_path(
        self,
        root_topic: HotTopic,
        matches: list[CandidateMatch],
        similarity_matrix,
        documents: list[str],
        *,
        provider: str,
        time_window_hours: int,
        similarity_threshold: float,
    ) -> PropagationPath:
        existing = self.db.query(PropagationPath).filter(PropagationPath.root_topic_id == root_topic.id).all()
        for item in existing:
            self.db.delete(item)
        if existing:
            self.db.flush()

        ordered_topics = [root_topic] + [match.topic for match in matches]
        platforms = []
        for topic in ordered_topics:
            platform_name = topic.platform.display_name if topic.platform else "未知平台"
            if platform_name not in platforms:
                platforms.append(platform_name)

        levels = self._assign_levels(root_topic, matches, similarity_matrix)
        max_level = max(levels.values(), default=0)
        breadth = Counter(levels.values())
        transitions = self._count_platform_transitions(ordered_topics)

        path = PropagationPath(
            root_topic_id=root_topic.id,
            depth=max_level,
            total_nodes=len(ordered_topics),
            max_breadth=max(breadth.values(), default=1),
            first_seen_at=min(topic.crawl_time for topic in ordered_topics),
            last_seen_at=max(topic.crawl_time for topic in ordered_topics),
            platforms_involved=json.dumps(platforms, ensure_ascii=False),
            platform_transitions=transitions,
        )
        self.db.add(path)
        self.db.flush()

        root_node = PropagationNode(
            path_id=path.id,
            topic_id=root_topic.id,
            level=0,
            parent_node_id=None,
            platform_id=root_topic.platform_id,
            heat_score=root_topic.heat_score,
            sentiment_label=root_topic.sentiment_result.sentiment_label if root_topic.sentiment_result else None,
            influence_score=100.0,
            features_json=json.dumps({
                "similarity_score": 1.0,
                "delay_hours": 0,
                "match_method": provider,
                "keywords": _top_tokens(documents[0]),
                "time_window_hours": time_window_hours,
                "similarity_threshold": similarity_threshold,
            }, ensure_ascii=False, sort_keys=True),
            discovered_at=root_topic.crawl_time,
        )
        self.db.add(root_node)
        self.db.flush()

        db_nodes = {root_topic.id: root_node}
        for match_index, match in enumerate(matches, start=1):
            parent_topic_id = self._select_parent_topic(root_topic, matches, match_index, similarity_matrix)
            parent_node = db_nodes.get(parent_topic_id, root_node)
            level = levels.get(match.topic.id, parent_node.level + 1)
            influence = self._influence_score(match, root_topic)
            node = PropagationNode(
                path_id=path.id,
                topic_id=match.topic.id,
                level=level,
                parent_node_id=parent_node.id,
                platform_id=match.topic.platform_id,
                heat_score=match.topic.heat_score,
                sentiment_label=match.topic.sentiment_result.sentiment_label if match.topic.sentiment_result else None,
                influence_score=influence,
                features_json=json.dumps({
                    "similarity_score": match.similarity,
                    "delay_hours": match.delay_hours,
                    "match_method": provider,
                    "keywords": _top_tokens(documents[match_index]),
                    "parent_topic_id": parent_topic_id,
                }, ensure_ascii=False, sort_keys=True),
                discovered_at=match.topic.crawl_time,
            )
            self.db.add(node)
            self.db.flush()
            db_nodes[match.topic.id] = node

        self.db.commit()
        self.db.refresh(path)
        return path

    def _assign_levels(self, root_topic: HotTopic, matches: list[CandidateMatch], similarity_matrix) -> dict[int, int]:
        levels = {root_topic.id: 0}
        for index, match in enumerate(matches, start=1):
            parent_topic_id = self._select_parent_topic(root_topic, matches, index, similarity_matrix)
            parent_level = levels.get(parent_topic_id, 0)
            parent_topic = root_topic if parent_topic_id == root_topic.id else next(
                (item.topic for item in matches if item.topic.id == parent_topic_id),
                root_topic,
            )
            is_cross_platform = parent_topic.platform_id != match.topic.platform_id
            levels[match.topic.id] = min(6, parent_level + (1 if is_cross_platform else 0))
        return levels

    def _select_parent_topic(
        self,
        root_topic: HotTopic,
        matches: list[CandidateMatch],
        match_index: int,
        similarity_matrix,
    ) -> int:
        target = matches[match_index - 1].topic
        best_topic_id = root_topic.id
        best_score = float(similarity_matrix[0][match_index])
        for previous_index, previous in enumerate(matches[: match_index - 1], start=1):
            if previous.topic.crawl_time > target.crawl_time:
                continue
            score = float(similarity_matrix[previous_index][match_index])
            if previous.topic.platform_id != target.platform_id:
                score += 0.08
            if score > best_score:
                best_score = score
                best_topic_id = previous.topic.id
        return best_topic_id

    def _influence_score(self, match: CandidateMatch, root_topic: HotTopic) -> float:
        root_heat = max(1, root_topic.heat_score or 1)
        heat_ratio = min(1.0, (match.topic.heat_score or 0) / root_heat)
        recency_penalty = max(0.0, abs(match.delay_hours) * 0.4)
        score = match.similarity * 70 + heat_ratio * 30 - recency_penalty
        return round(max(0.0, min(100.0, score)), 3)

    def _count_platform_transitions(self, topics: list[HotTopic]) -> int:
        ordered = sorted(topics, key=lambda item: item.crawl_time)
        transitions = 0
        previous = None
        for topic in ordered:
            platform_id = topic.platform_id
            if previous is not None and platform_id != previous:
                transitions += 1
            previous = platform_id
        return transitions

    def _build_vectors(self, documents: list[str]):
        embedding = self._try_sentence_transformers(documents)
        if embedding is not None:
            return embedding, "sentence-transformers"

        from sklearn.feature_extraction.text import TfidfVectorizer

        vectorizer = TfidfVectorizer(tokenizer=_tokenize, token_pattern=None, lowercase=False, min_df=1)
        try:
            return vectorizer.fit_transform(documents), "tfidf"
        except ValueError:
            fallback = [doc or f"topic-{index}" for index, doc in enumerate(documents)]
            return vectorizer.fit_transform(fallback), "tfidf"

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

    def _cosine_similarity(self, vectors):
        from sklearn.metrics.pairwise import cosine_similarity

        return cosine_similarity(vectors)

    def _token_overlap(self, left: str, right: str) -> float:
        left_tokens = set(_tokenize(left))
        right_tokens = set(_tokenize(right))
        if not left_tokens or not right_tokens:
            return 0.0
        return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)

    def _topic_document(self, topic: HotTopic) -> str:
        return topic.title or ""

    def _json_loads(self, value: str | None, *, fallback):
        if not value:
            return fallback
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return fallback


def _top_tokens(text: str, limit: int = 6) -> list[str]:
    return [token for token, _ in Counter(_tokenize(text)).most_common(limit)]
