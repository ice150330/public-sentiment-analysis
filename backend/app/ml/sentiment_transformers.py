# Transformers 情感分析模块 - 懒加载 + 异步推理
# 支持可选导入：如果 transformers/torch 未安装，自动降级到模拟模式

from typing import Dict, List, Optional
import asyncio
import threading
import os

# 尝试导入 Transformers
try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch
    _TRANSFORMERS_AVAILABLE = True
except ImportError:
    _TRANSFORMERS_AVAILABLE = False
    print("[WARN] transformers/torch 未安装，sentiment_v2 将使用模拟模式")


class TransformersSentimentAnalyzer:
    """基于 Transformers 的深度学习情感分析器（支持模拟模式降级）"""

    _instance: Optional['TransformersSentimentAnalyzer'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._model = None
        self._tokenizer = None
        self._model_name = "uer/roberta-base-finetuned-jd-binary-chinese"
        self._device = None
        if _TRANSFORMERS_AVAILABLE:
            self._device = torch.device("cpu")
        self._initialized = True

    def _load_model(self) -> None:
        """懒加载模型（仅首次调用时触发）"""
        if self._model is not None:
            return
        if not _TRANSFORMERS_AVAILABLE:
            return
        # 检查本地缓存是否存在，不存在则跳过（避免联网下载阻塞）
        try:
            from transformers.utils.hub import cached_file
            cached_file(self._model_name, "config.json", local_files_only=True)
        except Exception:
            print(f"[INFO] 模型 {self._model_name} 未在本地缓存，使用模拟模式")
            self._model = None
            self._tokenizer = None
            return
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(self._model_name, local_files_only=True)
            self._model = AutoModelForSequenceClassification.from_pretrained(self._model_name, local_files_only=True)
            self._model.to(self._device)
            self._model.eval()
            print(f"[INFO] Transformers 模型加载成功: {self._model_name}")
        except Exception as e:
            print(f"[WARN] Transformers 模型加载失败: {e}, 使用模拟模式")
            self._model = None
            self._tokenizer = None

    def analyze(self, text: str) -> Dict:
        """分析单条文本情感"""
        if not text or not text.strip():
            return {
                "sentiment": "neutral",
                "positive_score": 0.5,
                "negative_score": 0.5,
                "confidence": 0.0,
                "model": "fallback",
            }

        self._load_model()

        if self._model is None or self._tokenizer is None:
            return self._mock_analyze(text)

        try:
            inputs = self._tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True,
            )
            inputs = {k: v.to(self._device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self._model(**inputs)
                probabilities = torch.softmax(outputs.logits, dim=1)

            pos_prob = probabilities[0][1].item()
            neg_prob = probabilities[0][0].item()
            sentiment = "positive" if pos_prob > 0.5 else "negative"

            return {
                "sentiment": sentiment,
                "positive_score": round(pos_prob, 4),
                "negative_score": round(neg_prob, 4),
                "confidence": round(max(pos_prob, neg_prob), 4),
                "model": self._model_name,
            }
        except Exception as e:
            print(f"[WARN] Transformers 推理失败: {e}, 使用模拟模式")
            return self._mock_analyze(text)

    def _mock_analyze(self, text: str) -> Dict:
        """模拟分析（兜底）"""
        positive_words = ['好', '棒', '优秀', '赞', '支持', '喜欢', '满意', '不错', '强', '厉害', '推荐', '完美']
        negative_words = ['差', '烂', '糟糕', '坏', '反对', '讨厌', '失望', '恶心', '垃圾', '坑', '差评', '失望']

        pos_count = sum(1 for w in positive_words if w in text)
        neg_count = sum(1 for w in negative_words if w in text)
        total = pos_count + neg_count

        if total == 0:
            return {
                "sentiment": "neutral",
                "positive_score": 0.5,
                "negative_score": 0.5,
                "confidence": 0.0,
                "model": "mock",
            }

        pos_score = pos_count / total if total > 0 else 0.5
        neg_score = neg_count / total if total > 0 else 0.5
        sentiment = "positive" if pos_score > neg_score else "negative"
        confidence = max(pos_score, neg_score)

        return {
            "sentiment": sentiment,
            "positive_score": round(pos_score, 4),
            "negative_score": round(neg_score, 4),
            "confidence": round(confidence, 4),
            "model": "mock",
        }

    def batch_analyze(self, texts: List[str]) -> List[Dict]:
        """批量分析"""
        return [self.analyze(text) for text in texts]

    async def analyze_async(self, text: str) -> Dict:
        """异步分析（将同步计算放入线程池）"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.analyze, text)

    async def analyze_batch_async(self, texts: List[str]) -> List[Dict]:
        """异步批量分析"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.batch_analyze, texts)


# 全局分析器实例
_analyzer: Optional[TransformersSentimentAnalyzer] = None


def get_analyzer() -> TransformersSentimentAnalyzer:
    """获取分析器单例"""
    global _analyzer
    if _analyzer is None:
        _analyzer = TransformersSentimentAnalyzer()
    return _analyzer
