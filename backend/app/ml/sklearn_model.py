"""
轻量级情感分析模型（Sklearn 实现）

模块名称: sklearn_model.py
模块职责: 使用 TF-IDF + LogisticRegression 实现情感分析

适用场景:
- 无 GPU 环境快速验证
- 无网络环境（无法下载 BERT）
- 生产环境轻量级部署

与 BERT 模型的接口保持一致，方便切换。

作者: 码钉
日期: 2026-07-07
版本: 1.0.0
"""

import os
import sys

# 将 backend 目录加入 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import json
import pickle
from pathlib import Path
from typing import List, Dict, Optional

import jieba
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from app.ml.dataset import prepare_dataset


# 中文停用词（简化版）
STOP_WORDS = set([
    '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '那', '有', '个', '之', '为', '与', '及', '等', '或', '但', '而', '因为', '所以', '如果', '虽然', '那么', '然后', '可以', '就是', '不是', '这样', '那样', '这里', '那里', '什么', '怎么', '怎样', '如何', '谁', '哪', '哪个', '哪些', '哪里', '什么时候', '为什么',
])


class SklearnSentimentModel:
    """
    基于 Sklearn 的情感分析模型
    
    使用 TF-IDF + LogisticRegression，轻量快速。
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        初始化模型
        
        Args:
            model_path: 模型文件路径（可选）
        """
        self.pipeline: Optional[Pipeline] = None
        self.label_map = {0: "negative", 1: "neutral", 2: "positive"}
        self.id_map = {v: k for k, v in self.label_map.items()}
        
        if model_path and os.path.exists(model_path):
            self.load(model_path)
    
    def _tokenize(self, text: str) -> str:
        """中文分词"""
        words = jieba.lcut(text)
        # 过滤停用词和单字
        words = [w for w in words if w not in STOP_WORDS and len(w) > 1]
        return " ".join(words)
    
    def train(self, texts: List[str], labels: List[str]) -> Dict:
        """
        训练模型
        
        Args:
            texts: 训练文本列表
            labels: 标签列表 ("positive" / "negative" / "neutral")
            
        Returns:
            Dict: 训练结果
        """
        # 分词
        tokenized_texts = [self._tokenize(t) for t in texts]
        
        # 转换标签为 ID
        label_ids = [self.id_map[label] for label in labels]
        
        # 构建 Pipeline
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                max_features=5000,
                ngram_range=(1, 2),
                min_df=2,
                max_df=0.95,
            )),
            ('clf', LogisticRegression(
                max_iter=1000,
                random_state=42,
            )),
        ])
        
        # 训练
        self.pipeline.fit(tokenized_texts, label_ids)
        
        # 训练集评估
        train_preds = self.pipeline.predict(tokenized_texts)
        accuracy = (train_preds == np.array(label_ids)).mean()
        
        return {
            "accuracy": round(accuracy, 4),
            "model_type": "sklearn_logistic_regression",
            "feature_type": "tfidf",
        }
    
    def predict(self, texts: List[str]) -> List[Dict]:
        """
        批量预测
        
        Args:
            texts: 待分析文本列表
            
        Returns:
            List[Dict]: 预测结果
        """
        if self.pipeline is None:
            raise ValueError("Model not trained. Call train() first.")
        
        # 分词
        tokenized_texts = [self._tokenize(t) for t in texts]
        
        # 预测
        predictions = self.pipeline.predict(tokenized_texts)
        probabilities = self.pipeline.predict_proba(tokenized_texts)
        
        results = []
        for i, text in enumerate(texts):
            pred_id = predictions[i]
            probs = probabilities[i]
            
            results.append({
                "text": text,
                "sentiment_label": self.label_map[pred_id],
                "confidence": round(float(probs[pred_id]), 4),
                "scores": {
                    "negative": round(float(probs[self.id_map["negative"]]), 4),
                    "neutral": round(float(probs[self.id_map["neutral"]]), 4),
                    "positive": round(float(probs[self.id_map["positive"]]), 4),
                },
            })
        
        return results
    
    def evaluate(self, texts: List[str], labels: List[str]) -> Dict:
        """
        评估模型
        
        Args:
            texts: 测试文本
            labels: 真实标签
            
        Returns:
            Dict: 评估指标
        """
        from sklearn.metrics import accuracy_score, precision_recall_fscore_support
        
        predictions = self.predict(texts)
        pred_labels = [p["sentiment_label"] for p in predictions]
        
        accuracy = accuracy_score(labels, pred_labels)
        precision, recall, f1, _ = precision_recall_fscore_support(
            labels, pred_labels, average="weighted", zero_division=0
        )
        
        return {
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
        }
    
    def save(self, model_path: str):
        """保存模型"""
        Path(model_path).parent.mkdir(parents=True, exist_ok=True)
        with open(model_path, "wb") as f:
            pickle.dump({
                "pipeline": self.pipeline,
                "label_map": self.label_map,
            }, f)
        print(f"Model saved to {model_path}")
    
    def load(self, model_path: str):
        """加载模型"""
        with open(model_path, "rb") as f:
            data = pickle.load(f)
        self.pipeline = data["pipeline"]
        self.label_map = data["label_map"]
        self.id_map = {v: k for k, v in self.label_map.items()}
        print(f"Model loaded from {model_path}")


def train_sklearn_model(
    dataset_type: str = "mock",
    output_dir: str = "./model_output",
) -> Dict:
    """
    训练 Sklearn 情感分析模型
    
    Args:
        dataset_type: 数据集类型
        output_dir: 输出目录
        
    Returns:
        Dict: 训练结果
    """
    print("Loading dataset...")
    data = prepare_dataset(dataset_type=dataset_type, output_dir="./data/dataset")
    
    train_texts = [d["text"] for d in data["train"]]
    train_labels = [d["label"] for d in data["train"]]
    val_texts = [d["text"] for d in data["val"]]
    val_labels = [d["label"] for d in data["val"]]
    test_texts = [d["text"] for d in data["test"]]
    test_labels = [d["label"] for d in data["test"]]
    
    print(f"Train: {len(train_texts)} samples")
    print(f"Val: {len(val_texts)} samples")
    print(f"Test: {len(test_texts)} samples")
    
    # 训练
    print("\nTraining model...")
    model = SklearnSentimentModel()
    train_results = model.train(train_texts, train_labels)
    print(f"Train accuracy: {train_results['accuracy']}")
    
    # 验证集评估
    print("\nEvaluating on validation set...")
    val_results = model.evaluate(val_texts, val_labels)
    print(f"Val accuracy: {val_results['accuracy']}")
    print(f"Val f1: {val_results['f1_score']}")
    
    # 测试集评估
    print("\nEvaluating on test set...")
    test_results = model.evaluate(test_texts, test_labels)
    print(f"Test accuracy: {test_results['accuracy']}")
    print(f"Test precision: {test_results['precision']}")
    print(f"Test recall: {test_results['recall']}")
    print(f"Test f1: {test_results['f1_score']}")
    
    # 保存模型
    model_path = os.path.join(output_dir, "sklearn_model.pkl")
    model.save(model_path)
    
    # 保存结果
    results = {
        "model_type": "sklearn_logistic_regression",
        "feature_type": "tfidf",
        "dataset_type": dataset_type,
        "train_results": train_results,
        "val_results": val_results,
        "test_results": test_results,
    }
    
    results_path = os.path.join(output_dir, "training_results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\nResults saved to {results_path}")
    
    return results


if __name__ == "__main__":
    train_sklearn_model()
