"""
模型导出模块（延迟加载优化版）

模块名称: __init__.py
模块职责: 统一导出所有 ORM 模型，采用延迟导入减少启动内存
"""

# 核心模型（必须立即加载）
from app.models.platform import Platform
from app.models.hot_topic import HotTopic
from app.models.sentiment import SentimentResult
from app.models.crawl_log import CrawlLog

# 延迟加载装饰器
import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.system_config import SystemConfig
    from app.models.alert_rule import AlertRule
    from app.models.alert_event import AlertEvent
    from app.models.alert_action import AlertAction
    from app.models.data_quality import DataQualityRun, DataQualityIssue
    from app.models.system_log import SystemLog, AuditLog
    from app.models.topic_sample import TopicSample, TopicRelation
    from app.models.model_version import ModelVersion
    from app.models.topic_cluster import TopicCluster, ClusterMember
    from app.models.propagation_path import PropagationPath, PropagationNode
    from app.models.trend_prediction import TrendPrediction, PredictionFeature
    from app.models.model_explanation import ModelExplanation, FeatureContribution
    from app.models.task_state import CrawlerTask, CrawlerTaskEvent, SentimentJob, DataArchiveRun


class LazyModule:
    """延迟加载模块代理"""
    
    def __init__(self, module_path, names):
        self._module_path = module_path
        self._names = names
        self._module = None
    
    def _load(self):
        if self._module is None:
            self._module = importlib.import_module(self._module_path)
        return self._module
    
    def __getattr__(self, name):
        if name in self._names:
            module = self._load()
            return getattr(module, name)
        raise AttributeError(f"'{self._module_path}' has no attribute '{name}'")


# 非核心模型延迟加载
_system_config = LazyModule("app.models.system_config", ["SystemConfig"])
_alert = LazyModule("app.models.alert_rule", ["AlertRule"])
_alert_event = LazyModule("app.models.alert_event", ["AlertEvent"])
_alert_action = LazyModule("app.models.alert_action", ["AlertAction"])
_data_quality = LazyModule("app.models.data_quality", ["DataQualityRun", "DataQualityIssue"])
_system_log = LazyModule("app.models.system_log", ["SystemLog", "AuditLog"])
_topic_sample = LazyModule("app.models.topic_sample", ["TopicSample", "TopicRelation"])
_model_version = LazyModule("app.models.model_version", ["ModelVersion"])
_topic_cluster = LazyModule("app.models.topic_cluster", ["TopicCluster", "ClusterMember"])
_propagation = LazyModule("app.models.propagation_path", ["PropagationPath", "PropagationNode"])
_trend = LazyModule("app.models.trend_prediction", ["TrendPrediction", "PredictionFeature"])
_explanation = LazyModule("app.models.model_explanation", ["ModelExplanation", "FeatureContribution"])
_task_state = LazyModule("app.models.task_state", ["CrawlerTask", "CrawlerTaskEvent", "SentimentJob", "DataArchiveRun"])

# 保持兼容：直接访问时触发加载
SystemConfig = _system_config.SystemConfig
AlertRule = _alert.AlertRule
AlertEvent = _alert_event.AlertEvent
AlertAction = _alert_action.AlertAction
DataQualityRun = _data_quality.DataQualityRun
DataQualityIssue = _data_quality.DataQualityIssue
SystemLog = _system_log.SystemLog
AuditLog = _system_log.AuditLog
TopicSample = _topic_sample.TopicSample
TopicRelation = _topic_sample.TopicRelation
ModelVersion = _model_version.ModelVersion
TopicCluster = _topic_cluster.TopicCluster
ClusterMember = _topic_cluster.ClusterMember
PropagationPath = _propagation.PropagationPath
PropagationNode = _propagation.PropagationNode
TrendPrediction = _trend.TrendPrediction
PredictionFeature = _trend.PredictionFeature
ModelExplanation = _explanation.ModelExplanation
FeatureContribution = _explanation.FeatureContribution
CrawlerTask = _task_state.CrawlerTask
CrawlerTaskEvent = _task_state.CrawlerTaskEvent
SentimentJob = _task_state.SentimentJob
DataArchiveRun = _task_state.DataArchiveRun

__all__ = [
    "Platform", "HotTopic", "SentimentResult", "CrawlLog",
    "SystemConfig", "AlertRule", "AlertEvent", "AlertAction",
    "DataQualityRun", "DataQualityIssue",
    "SystemLog", "AuditLog",
    "TopicSample", "TopicRelation",
    "ModelVersion",
    "TopicCluster", "ClusterMember",
    "PropagationPath", "PropagationNode",
    "TrendPrediction", "PredictionFeature",
    "ModelExplanation", "FeatureContribution",
    "CrawlerTask", "CrawlerTaskEvent", "SentimentJob", "DataArchiveRun",
]
