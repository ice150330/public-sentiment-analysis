"""
BERT 情感分析模型训练脚本

模块名称: train.py
模块职责: BERT 微调训练、评估、保存

使用方式:
    cd backend
    source venv/bin/activate
    python app/ml/train.py --dataset mock --epochs 3 --batch_size 8

作者: 码钉
日期: 2026-07-07
版本: 1.0.0
"""

import os
import sys
import argparse
import json
import time
from pathlib import Path
from typing import Dict, List, Optional

import torch
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
from transformers import (
    BertTokenizer,
    BertForSequenceClassification,
    Trainer,
    TrainingArguments,
    DataCollatorWithPadding,
    EarlyStoppingCallback,
)
from datasets import Dataset

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.ml.dataset import prepare_dataset


# 标签映射
LABEL_MAP = {"negative": 0, "neutral": 1, "positive": 2}
ID_MAP = {v: k for k, v in LABEL_MAP.items()}


def load_data(dataset_type: str = "mock", data_dir: Optional[str] = None) -> Dict[str, List[Dict]]:
    """加载数据集"""
    return prepare_dataset(dataset_type=dataset_type, data_dir=data_dir, output_dir="./data/dataset")


def create_dataset(data: List[Dict], tokenizer, max_length: int = 128) -> Dataset:
    """
    创建 HuggingFace Dataset
    
    Args:
        data: 数据列表 [{"text": ..., "label": ...}]
        tokenizer: BERT tokenizer
        max_length: 最大序列长度
        
    Returns:
        Dataset: HuggingFace Dataset 对象
    """
    texts = [item["text"] for item in data]
    labels = [LABEL_MAP[item["label"]] for item in data]
    
    # 创建 Dataset
    dataset = Dataset.from_dict({"text": texts, "label": labels})
    
    # Tokenize
    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            padding=False,  # 由 DataCollator 处理
            truncation=True,
            max_length=max_length,
        )
    
    dataset = dataset.map(tokenize_function, batched=True, remove_columns=["text"])
    dataset.set_format(type="torch", columns=["input_ids", "attention_mask", "label"])
    
    return dataset


def compute_metrics(eval_pred) -> Dict:
    """
    计算评估指标
    
    Args:
        eval_pred: Trainer 输出的预测结果
        
    Returns:
        Dict: 评估指标
    """
    predictions, labels = eval_pred
    preds = np.argmax(predictions, axis=-1)
    
    accuracy = accuracy_score(labels, preds)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, preds, average="weighted", zero_division=0
    )
    
    # 混淆矩阵
    cm = confusion_matrix(labels, preds)
    
    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def train_model(
    dataset_type: str = "mock",
    model_name: str = "bert-base-chinese",
    output_dir: str = "./model_output",
    epochs: int = 3,
    batch_size: int = 8,
    learning_rate: float = 2e-5,
    max_length: int = 128,
    warmup_ratio: float = 0.1,
    weight_decay: float = 0.01,
    early_stopping_patience: int = 2,
    seed: int = 42,
):
    """
    训练 BERT 情感分析模型
    
    Args:
        dataset_type: 数据集类型 (mock / chn_senticorp / weibo)
        model_name: HuggingFace 模型名称
        output_dir: 模型输出目录
        epochs: 训练轮数
        batch_size: 批大小
        learning_rate: 学习率
        max_length: 最大序列长度
        warmup_ratio: 预热比例
        weight_decay: 权重衰减
        early_stopping_patience: 早停耐心值
        seed: 随机种子
    """
    # 设置随机种子
    torch.manual_seed(seed)
    np.random.seed(seed)
    
    # 设备选择
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # 加载数据
    print(f"\nLoading dataset: {dataset_type}")
    data = load_data(dataset_type)
    
    print(f"Train: {len(data['train'])} samples")
    print(f"Val: {len(data['val'])} samples")
    print(f"Test: {len(data['test'])} samples")
    
    # 加载 tokenizer 和模型
    print(f"\nLoading model: {model_name}")
    tokenizer = BertTokenizer.from_pretrained(model_name)
    model = BertForSequenceClassification.from_pretrained(
        model_name,
        num_labels=3,  # negative, neutral, positive
    ).to(device)
    
    # 创建 Dataset
    print("\nCreating datasets...")
    train_dataset = create_dataset(data["train"], tokenizer, max_length)
    val_dataset = create_dataset(data["val"], tokenizer, max_length)
    test_dataset = create_dataset(data["test"], tokenizer, max_length)
    
    # 数据整理器
    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)
    
    # 计算训练步数
    total_steps = (len(train_dataset) // batch_size) * epochs
    warmup_steps = int(total_steps * warmup_ratio)
    
    # 训练参数
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=learning_rate,
        weight_decay=weight_decay,
        warmup_steps=warmup_steps,
        logging_dir=f"{output_dir}/logs",
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        seed=seed,
        report_to="none",  # 禁用 wandb/tensorboard
    )
    
    # 训练器
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=early_stopping_patience)],
    )
    
    # 训练
    print("\n" + "=" * 50)
    print("Starting training...")
    print("=" * 50)
    start_time = time.time()
    
    trainer.train()
    
    training_time = time.time() - start_time
    print(f"\nTraining completed in {training_time:.2f} seconds")
    
    # 保存最终模型
    print(f"\nSaving model to {output_dir}")
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    # 测试集评估
    print("\n" + "=" * 50)
    print("Evaluating on test set...")
    print("=" * 50)
    test_results = trainer.evaluate(test_dataset)
    
    print(f"\nTest Results:")
    print(f"  Accuracy: {test_results['eval_accuracy']:.4f}")
    print(f"  Precision: {test_results['eval_precision']:.4f}")
    print(f"  Recall: {test_results['eval_recall']:.4f}")
    print(f"  F1 Score: {test_results['eval_f1']:.4f}")
    
    # 保存评估结果
    results = {
        "model_name": model_name,
        "dataset_type": dataset_type,
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "max_length": max_length,
        "training_time_seconds": round(training_time, 2),
        "test_results": {
            "accuracy": round(test_results['eval_accuracy'], 4),
            "precision": round(test_results['eval_precision'], 4),
            "recall": round(test_results['eval_recall'], 4),
            "f1": round(test_results['eval_f1'], 4),
        },
    }
    
    results_path = Path(output_dir) / "training_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\nResults saved to {results_path}")
    
    return model, tokenizer, results


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="BERT Sentiment Analysis Training")
    parser.add_argument("--dataset", type=str, default="mock", choices=["mock", "chn_senticorp", "weibo"], help="Dataset type")
    parser.add_argument("--model", type=str, default="bert-base-chinese", help="Pretrained model name")
    parser.add_argument("--output", type=str, default="./model_output", help="Output directory")
    parser.add_argument("--epochs", type=int, default=3, help="Number of epochs")
    parser.add_argument("--batch_size", type=int, default=8, help="Batch size")
    parser.add_argument("--lr", type=float, default=2e-5, help="Learning rate")
    parser.add_argument("--max_length", type=int, default=128, help="Max sequence length")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    
    args = parser.parse_args()
    
    train_model(
        dataset_type=args.dataset,
        model_name=args.model,
        output_dir=args.output,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        max_length=args.max_length,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
