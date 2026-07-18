"""SQLite maintenance helpers for existing local databases."""

from sqlalchemy import text
from sqlalchemy.engine import Engine


SQLITE_INDEX_STATEMENTS: tuple[tuple[str, str], ...] = (
    (
        "idx_hot_topics_platform_crawl_time",
        "CREATE INDEX IF NOT EXISTS idx_hot_topics_platform_crawl_time "
        "ON hot_topics(platform_id, crawl_time)",
    ),
    (
        "idx_hot_topics_crawl_time",
        "CREATE INDEX IF NOT EXISTS idx_hot_topics_crawl_time ON hot_topics(crawl_time)",
    ),
    (
        "idx_hot_topics_heat_score",
        "CREATE INDEX IF NOT EXISTS idx_hot_topics_heat_score ON hot_topics(heat_score)",
    ),
    (
        "idx_hot_topics_category_crawl_time",
        "CREATE INDEX IF NOT EXISTS idx_hot_topics_category_crawl_time ON hot_topics(category, crawl_time)",
    ),
    (
        "idx_hot_topics_crawl_date",
        "CREATE INDEX IF NOT EXISTS idx_hot_topics_crawl_date ON hot_topics(crawl_date)",
    ),
    (
        "idx_sentiment_label_analyzed_at",
        "CREATE INDEX IF NOT EXISTS idx_sentiment_label_analyzed_at "
        "ON sentiment_results(sentiment_label, analyzed_at)",
    ),
    (
        "idx_sentiment_analyzed_at",
        "CREATE INDEX IF NOT EXISTS idx_sentiment_analyzed_at ON sentiment_results(analyzed_at)",
    ),
    (
        "idx_sentiment_confidence",
        "CREATE INDEX IF NOT EXISTS idx_sentiment_confidence ON sentiment_results(confidence)",
    ),
    (
        "idx_crawl_logs_platform_started_at",
        "CREATE INDEX IF NOT EXISTS idx_crawl_logs_platform_started_at "
        "ON crawl_logs(platform_id, started_at)",
    ),
    (
        "idx_crawl_logs_status_started_at",
        "CREATE INDEX IF NOT EXISTS idx_crawl_logs_status_started_at ON crawl_logs(status, started_at)",
    ),
    (
        "idx_crawl_logs_completed_at",
        "CREATE INDEX IF NOT EXISTS idx_crawl_logs_completed_at ON crawl_logs(completed_at)",
    ),
    (
        "idx_alert_events_status_severity_triggered_at",
        "CREATE INDEX IF NOT EXISTS idx_alert_events_status_severity_triggered_at "
        "ON alert_events(status, severity, triggered_at)",
    ),
    (
        "idx_alert_events_rule_triggered_at",
        "CREATE INDEX IF NOT EXISTS idx_alert_events_rule_triggered_at ON alert_events(rule_id, triggered_at)",
    ),
    (
        "idx_alert_events_topic_id",
        "CREATE INDEX IF NOT EXISTS idx_alert_events_topic_id ON alert_events(topic_id)",
    ),
    (
        "idx_alert_events_triggered_at",
        "CREATE INDEX IF NOT EXISTS idx_alert_events_triggered_at ON alert_events(triggered_at)",
    ),
    (
        "idx_users_role_active",
        "CREATE INDEX IF NOT EXISTS idx_users_role_active ON users(role, is_active)",
    ),
    (
        "idx_users_created_at",
        "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at)",
    ),
    (
        "idx_propagation_paths_root_created",
        "CREATE INDEX IF NOT EXISTS idx_propagation_paths_root_created "
        "ON propagation_paths(root_topic_id, created_at)",
    ),
    (
        "idx_propagation_nodes_path_level",
        "CREATE INDEX IF NOT EXISTS idx_propagation_nodes_path_level "
        "ON propagation_nodes(path_id, level)",
    ),
)

SQLITE_COLUMN_STATEMENTS: tuple[tuple[str, str, str], ...] = (
    (
        "propagation_nodes",
        "features_json",
        "ALTER TABLE propagation_nodes ADD COLUMN features_json TEXT",
    ),
)


def ensure_sqlite_indexes(engine: Engine) -> list[str]:
    """Create performance indexes and lightweight columns on existing SQLite databases."""
    if not engine.url.drivername.startswith("sqlite"):
        return []

    ensured: list[str] = []
    with engine.begin() as connection:
        for table_name, column_name, statement in SQLITE_COLUMN_STATEMENTS:
            columns = {
                row[1]
                for row in connection.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
            }
            if column_name not in columns:
                connection.execute(text(statement))
                ensured.append(f"{table_name}.{column_name}")

        for name, statement in SQLITE_INDEX_STATEMENTS:
            connection.execute(text(statement))
            ensured.append(name)
    return ensured
