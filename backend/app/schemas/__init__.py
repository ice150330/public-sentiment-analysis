"""
Schemas 导出模块

模块名称: __init__.py
模块职责: 统一导出所有 Pydantic schemas
"""

from app.schemas.common import (
    Pagination,
    PaginatedResponse,
    UnifiedResponse,
    ErrorResponse,
)
from app.schemas.platform import (
    PlatformBase,
    PlatformCreate,
    PlatformUpdate,
    PlatformResponse,
    PlatformListResponse,
)
from app.schemas.hot_topic import (
    HotTopicBase,
    HotTopicCreate,
    HotTopicResponse,
    HotTopicListResponse,
    HotTopicQueryParams,
)
from app.schemas.sentiment import (
    SentimentAnalyzeRequest,
    SentimentAnalyzeBatchRequest,
    SentimentScores,
    SentimentResultResponse,
    SentimentAnalyzeResponse,
    SentimentQueryParams,
)
from app.schemas.stats import (
    SentimentDistributionResponse,
    HeatTrendResponse,
    CrawlSuccessRateResponse,
    CrawlerStatus,
    CrawlerScheduleConfig,
    OverviewResponse,
)
from app.schemas.crawler import (
    CrawlerTriggerRequest,
    CrawlerTriggerResponse,
    CrawlLogResponse,
)
from app.schemas.auth import (
    LoginRequest,
    PasswordChangeRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RegisterRequest,
    TokenResponse,
    UserUpdateRequest,
    UserResponse,
)
