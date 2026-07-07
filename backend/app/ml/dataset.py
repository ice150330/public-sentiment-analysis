"""
情感分析数据集准备模块

模块名称: dataset.py
模块职责: 加载公开数据集、数据预处理、生成模拟数据

支持数据集:
- 模拟数据: 用于快速验证流程
- ChnSentiCorp: 中文情感分析数据集 (需下载)
- weibo_senti_100k: 微博情感数据集 (需下载)

作者: 码钉
日期: 2026-07-07
版本: 1.0.0
"""

import random
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import pandas as pd
from sklearn.model_selection import train_test_split


# 模拟数据模板（用于快速验证）
MOCK_POSITIVE_TEMPLATES = [
    "这个产品{adj}，非常{emotion}！",
    "{topic}真是太{adj}了，强烈推荐！",
    "用了{topic}之后，感觉{emotion}。",
    "{topic}的效果超出预期，{adj}！",
    "非常满意{topic}，{emotion}！",
    "{topic}值得五星好评，{adj}！",
    "用了{topic}，心情{emotion}。",
    "{topic}的品质一流，{adj}！",
]

MOCK_NEGATIVE_TEMPLATES = [
    "这个{topic}太{adj}了，非常{emotion}！",
    "{topic}的质量太差，{emotion}。",
    "用了{topic}之后，感觉{emotion}。",
    "{topic}完全不值这个价，{adj}！",
    "对{topic}非常失望，{emotion}！",
    "{topic}的体验极差，{adj}！",
    "{topic}让人{emotion}，不推荐。",
    "{topic}的问题太多了，{adj}！",
]

MOCK_NEUTRAL_TEMPLATES = [
    "{topic}发布了新款产品，售价{price}元。",
    "关于{topic}的最新动态。",
    "{topic}的市场表现{adj}。",
    "{topic}的用户数量为{num}万。",
    "{topic}今日上线，功能包括{feature}。",
    "{topic}的官方声明。",
    "{topic}的最新数据公布。",
    "{topic}行业的发展现状。",
]

MOCK_ADJECTIVES = {
    "positive": ["好用", "棒", "优秀", "出色", "完美", "赞", "给力", "nice"],
    "negative": ["差", "烂", "糟糕", "失望", "垃圾", "坑", "后悔", "无语"],
    "neutral": ["平稳", "正常", "一般", "稳定", "平均"],
}

MOCK_EMOTIONS = {
    "positive": ["满意", "开心", "高兴", "惊喜", "愉悦"],
    "negative": ["失望", "生气", "愤怒", "沮丧", "郁闷"],
}

MOCK_TOPICS = [
    "手机", "电脑", "耳机", "手表", "平板", "相机",
    "游戏", "电影", "音乐", "书籍", "美食", "旅游",
    "教育", "医疗", "交通", "住房", "就业", "环境",
    "科技", "金融", "体育", "娱乐", "时尚", "汽车",
]

MOCK_FEATURES = [
    "AI功能", "高清屏幕", "长续航", "快充", "多摄像头",
    "防水", "5G网络", "人脸识别", "语音助手",
]


def generate_mock_data(
    n_samples: int = 3000,
    seed: int = 42,
    output_dir: Optional[str] = None,
) -> Dict[str, List[Dict]]:
    """
    生成模拟情感分析数据集
    
    Args:
        n_samples: 总样本数（每类 n_samples/3）
        seed: 随机种子
        output_dir: 输出目录（可选）
        
    Returns:
        Dict: {"train": [...], "val": [...], "test": [...]}
    """
    random.seed(seed)
    
    samples_per_class = n_samples // 3
    all_data = []
    
    # 生成正面样本
    for _ in range(samples_per_class):
        template = random.choice(MOCK_POSITIVE_TEMPLATES)
        text = template.format(
            topic=random.choice(MOCK_TOPICS),
            adj=random.choice(MOCK_ADJECTIVES["positive"]),
            emotion=random.choice(MOCK_EMOTIONS["positive"]),
        )
        all_data.append({"text": text, "label": "positive"})
    
    # 生成负面样本
    for _ in range(samples_per_class):
        template = random.choice(MOCK_NEGATIVE_TEMPLATES)
        text = template.format(
            topic=random.choice(MOCK_TOPICS),
            adj=random.choice(MOCK_ADJECTIVES["negative"]),
            emotion=random.choice(MOCK_EMOTIONS["negative"]),
        )
        all_data.append({"text": text, "label": "negative"})
    
    # 生成中性样本
    for _ in range(samples_per_class):
        template = random.choice(MOCK_NEUTRAL_TEMPLATES)
        text = template.format(
            topic=random.choice(MOCK_TOPICS),
            price=random.randint(100, 9999),
            num=random.randint(1, 1000),
            adj=random.choice(MOCK_ADJECTIVES["neutral"]),
            feature=random.choice(MOCK_FEATURES),
        )
        all_data.append({"text": text, "label": "neutral"})
    
    # 随机打乱
    random.shuffle(all_data)
    
    # 划分训练/验证/测试集 (70%/15%/15%)
    train_data, temp_data = train_test_split(
        all_data, test_size=0.3, random_state=seed, stratify=[d["label"] for d in all_data]
    )
    val_data, test_data = train_test_split(
        temp_data, test_size=0.5, random_state=seed, stratify=[d["label"] for d in temp_data]
    )
    
    result = {
        "train": train_data,
        "val": val_data,
        "test": test_data,
    }
    
    # 保存到文件
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for split, data in result.items():
            file_path = output_path / f"{split}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Saved {split}: {len(data)} samples to {file_path}")
    
    # 统计信息
    print(f"\nDataset Statistics:")
    for split, data in result.items():
        labels = [d["label"] for d in data]
        print(f"  {split}: {len(data)} samples")
        print(f"    positive: {labels.count('positive')}")
        print(f"    negative: {labels.count('negative')}")
        print(f"    neutral: {labels.count('neutral')}")
    
    return result


def load_chn_senticorp(data_dir: str) -> Dict[str, List[Dict]]:
    """
    加载 ChnSentiCorp 数据集
    
    数据集说明:
    - 来源: 中文情感分析语料库
    - 类别: 正面/负面（二分类）
    - 下载: https://github.com/pengmiao/ChineseNlpCorpus
    
    Args:
        data_dir: 数据集目录
        
    Returns:
        Dict: {"train": [...], "val": [...], "test": [...]}
    """
    data_dir = Path(data_dir)
    
    result = {}
    for split in ["train", "val", "test"]:
        file_path = data_dir / f"{split}.csv"
        if not file_path.exists():
            print(f"Warning: {file_path} not found, skipping.")
            continue
        
        df = pd.read_csv(file_path)
        # ChnSentiCorp 格式: label, text
        # label: 1=positive, 0=negative
        data = []
        for _, row in df.iterrows():
            label = "positive" if row["label"] == 1 else "negative"
            data.append({"text": str(row["text"]), "label": label})
        
        result[split] = data
        print(f"Loaded {split}: {len(data)} samples from ChnSentiCorp")
    
    return result


def load_weibo_senti(data_dir: str) -> Dict[str, List[Dict]]:
    """
    加载微博情感数据集
    
    数据集说明:
    - 来源: 微博情感分析数据集 (100k)
    - 类别: 正面/负面（二分类）
    - 下载: https://github.com/duoergun0729/1book
    
    Args:
        data_dir: 数据集目录
        
    Returns:
        Dict: {"train": [...], "val": [...], "test": [...]}
    """
    data_dir = Path(data_dir)
    
    result = {}
    for split in ["train", "val", "test"]:
        file_path = data_dir / f"weibo_{split}.csv"
        if not file_path.exists():
            print(f"Warning: {file_path} not found, skipping.")
            continue
        
        df = pd.read_csv(file_path)
        # 微博数据集格式: label, text
        # label: 1=positive, 0=negative
        data = []
        for _, row in df.iterrows():
            label = "positive" if row["label"] == 1 else "negative"
            data.append({"text": str(row["text"]), "label": label})
        
        result[split] = data
        print(f"Loaded {split}: {len(data)} samples from Weibo Senti")
    
    return result


def prepare_dataset(
    dataset_type: str = "mock",
    data_dir: Optional[str] = None,
    n_samples: int = 3000,
    output_dir: str = "./data/dataset",
) -> Dict[str, List[Dict]]:
    """
    准备数据集（统一入口）
    
    Args:
        dataset_type: 数据集类型 (mock / chn_senticorp / weibo)
        data_dir: 原始数据目录（用于真实数据集）
        n_samples: 模拟数据样本数
        output_dir: 输出目录
        
    Returns:
        Dict: {"train": [...], "val": [...], "test": [...]}
    """
    if dataset_type == "mock":
        return generate_mock_data(n_samples=n_samples, output_dir=output_dir)
    elif dataset_type == "chn_senticorp":
        return load_chn_senticorp(data_dir or "./data/chn_senticorp")
    elif dataset_type == "weibo":
        return load_weibo_senti(data_dir or "./data/weibo_senti")
    else:
        raise ValueError(f"Unknown dataset type: {dataset_type}")


if __name__ == "__main__":
    # 生成模拟数据用于测试
    dataset = prepare_dataset("mock", n_samples=300, output_dir="./data/dataset")
    print("\nDataset prepared successfully!")
