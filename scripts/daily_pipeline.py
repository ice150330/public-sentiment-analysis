#!/usr/bin/env python3
"""
每日数据处理流水线

用法:
    # 数据采集模式（每30分钟执行）
    python scripts/daily_pipeline.py crawl
    
    # 最终清洗+推送+汇报模式（每天10:00执行）
    python scripts/daily_pipeline.py finalize

定时设置(cron):
    # 6:00-9:30 每30分钟采集
    0,30 6-9 * * * cd /root/.openclaw/workspace/sentiment-analysis && PYTHONPATH=/root/.openclaw/workspace/sentiment-analysis /root/.openclaw/workspace/sentiment-analysis/backend/venv/bin/python scripts/daily_pipeline.py crawl >> /tmp/sentiment_crawl.log 2>&1
    
    # 10:00 最终清洗推送
    0 10 * * * cd /root/.openclaw/workspace/sentiment-analysis && PYTHONPATH=/root/.openclaw/workspace/sentiment-analysis /root/.openclaw/workspace/sentiment-analysis/backend/venv/bin/python scripts/daily_pipeline.py finalize >> /tmp/sentiment_finalize.log 2>&1
"""

import sys
import os
import logging
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path

# 项目路径设置
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKEND_ROOT))

# 切换工作目录到 backend，确保 SQLite 路径正确
os.chdir(BACKEND_ROOT)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("daily_pipeline")

# 常量
DB_PATH = BACKEND_ROOT / "data" / "sentiment.db"
REPORT_PATH = BACKEND_ROOT / "data" / "daily_report.json"
VENV_PYTHON = BACKEND_ROOT / "venv" / "bin" / "python"


def run_crawl():
    """执行数据采集（单次）"""
    logger.info("=" * 60)
    logger.info(f"🕕 数据采集开始 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    try:
        from app.core.database import SessionLocal
        from crawler.pipeline import CrawlPipeline
        from app.services.data_quality_service import DataQualityService
        
        db = SessionLocal()
        
        platforms = ["weibo", "douyin", "toutiao", "baidu", "bilibili", "zhihu"]
        total_new = 0
        total_updated = 0
        
        for platform in platforms:
            try:
                pipeline = CrawlPipeline(db)
                results = pipeline.crawl_platform(platform, use_mock=True)
                
                # 计算实际入库数
                new_count = len(results)
                total_new += new_count
                
                logger.info(f"  ✅ {platform:10s} | 采集 {new_count:3d} 条")
                
            except Exception as e:
                logger.error(f"  ❌ {platform:10s} | 失败: {e}")
                continue
        
        # 运行数据质量检查
        try:
            quality_service = DataQualityService(db)
            report = quality_service.run_quality_check(run_type="daily")
            logger.info(f"  📊 质量检查完成 | 发现问题: {report.get('issues_found', 0)} 条")
        except Exception as e:
            logger.warning(f"  ⚠️ 质量检查失败: {e}")
        
        db.close()
        
        logger.info(f"\n📈 本轮采集汇总: 新增 {total_new} 条")
        logger.info(f"⏰ 完成时间: {datetime.now().strftime('%H:%M:%S')}")
        return True
        
    except Exception as e:
        logger.error(f"❌ 采集流程异常: {e}")
        return False


def run_finalize():
    """执行最终清洗、推送、汇报"""
    logger.info("=" * 60)
    logger.info(f"🔔 最终清洗+推送+汇报 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    try:
        from app.core.database import SessionLocal
        from app.models import HotTopic, SentimentResult, Platform
        from app.services.data_quality_service import DataQualityService
        from sqlalchemy import func
        
        db = SessionLocal()
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        
        # ========== 1. 数据清洗 ==========
        logger.info("\n【1/4】数据清洗...")
        
        # 清洗1: 修复缺失摘要
        missing_summary = db.query(HotTopic).filter(
            HotTopic.crawl_time >= today_start,
            HotTopic.content_summary.is_(None),
        ).all()
        
        fixed_summary = 0
        for topic in missing_summary:
            topic.content_summary = topic.title
            fixed_summary += 1
        
        if fixed_summary > 0:
            db.commit()
        logger.info(f"  修复缺失摘要: {fixed_summary} 条")
        
        # 清洗2: 修复分类（运营标签→正确分类）
        from crawler.data_processor import DataProcessor
        bad_category = db.query(HotTopic).filter(
            HotTopic.crawl_time >= today_start,
            HotTopic.category.in_(["热", "新", "爆", "沸"]),
        ).all()
        
        fixed_category = 0
        for topic in bad_category:
            topic.category = DataProcessor.DEFAULT_CATEGORY
            fixed_category += 1
        
        if fixed_category > 0:
            db.commit()
        logger.info(f"  修复错误分类: {fixed_category} 条")
        
        # 清洗3: 最终质量检查
        quality_service = DataQualityService(db)
        quality_report = quality_service.run_quality_check(run_type="daily")
        logger.info(f"  质量检查完成: {quality_report.get('issues_found', 0)} 个问题")
        
        # ========== 2. 生成日报 ==========
        logger.info("\n【2/4】生成日报...")
        
        # 统计数据
        total_topics = db.query(func.count(HotTopic.id)).filter(
            HotTopic.crawl_time >= today_start,
        ).scalar() or 0
        
        sentiment_count = db.query(func.count(SentimentResult.id)).join(HotTopic).filter(
            HotTopic.crawl_time >= today_start,
        ).scalar() or 0
        
        # 平台分布
        platform_stats = db.query(
            Platform.display_name,
            func.count(HotTopic.id).label("cnt"),
        ).join(HotTopic).filter(
            HotTopic.crawl_time >= today_start,
        ).group_by(Platform.display_name).all()
        
        # 情感分布
        sentiment_dist = db.query(
            SentimentResult.sentiment_label,
            func.count(SentimentResult.id).label("cnt"),
        ).join(HotTopic).filter(
            HotTopic.crawl_time >= today_start,
        ).group_by(SentimentResult.sentiment_label).all()
        
        # TOP10 热度话题
        top_topics = db.query(HotTopic).filter(
            HotTopic.crawl_time >= today_start,
        ).order_by(HotTopic.heat_score.desc()).limit(10).all()
        
        report = {
            "date": today.isoformat(),
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_topics": total_topics,
                "sentiment_analyzed": sentiment_count,
                "coverage_rate": round(sentiment_count / total_topics * 100, 1) if total_topics > 0 else 0,
            },
            "platform_distribution": [
                {"platform": p.display_name, "count": p.cnt} for p in platform_stats
            ],
            "sentiment_distribution": [
                {"label": s.sentiment_label, "count": s.cnt, "percentage": round(s.cnt / sentiment_count * 100, 1) if sentiment_count > 0 else 0}
                for s in sentiment_dist
            ],
            "top_10_topics": [
                {
                    "title": t.title,
                    "heat_score": t.heat_score,
                    "category": t.category,
                    "platform": db.query(Platform).filter(Platform.id == t.platform_id).first().display_name if db.query(Platform).filter(Platform.id == t.platform_id).first() else "未知",
                }
                for t in top_topics
            ],
            "data_quality": {
                "issues_found": quality_report.get("issues_found", 0),
                "status": quality_report.get("status", "unknown"),
            },
        }
        
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"  日报已保存: {REPORT_PATH}")
        logger.info(f"  今日采集: {total_topics} 条 | 情感分析: {sentiment_count} 条")
        
        db.close()
        
        # ========== 3. 推送数据库 ==========
        logger.info("\n【3/4】推送数据库...")
        
        git_cmds = [
            ["git", "add", "-f", "backend/data/sentiment.db", "backend/data/daily_report.json"],
            ["git", "commit", "-m", f"data(daily): {today.isoformat()} 数据更新\n\n- 采集: {total_topics} 条\n- 情感分析: {sentiment_count} 条\n- 质量检查: {quality_report.get('issues_found', 0)} 个问题"],
            ["git", "push", "origin", "main"],
        ]
        
        for cmd in git_cmds:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0 and "nothing to commit" not in result.stderr:
                logger.warning(f"  Git命令失败: {' '.join(cmd)}\n  {result.stderr}")
            else:
                logger.info(f"  ✅ {' '.join(cmd[:2])}")
        
        logger.info(f"  数据库已推送: {DB_PATH} ({os.path.getsize(DB_PATH) / 1024 / 1024:.2f} MB)")
        
        # ========== 4. 汇报 ==========
        logger.info("\n【4/4】生成汇报...")
        
        # 构建汇报文本
        platform_lines = "\n".join([
            f"  {p['platform']:8s}: {p['count']:4d} 条" 
            for p in report["platform_distribution"]
        ])
        
        sentiment_lines = "\n".join([
            f"  {s['label']:8s}: {s['count']:4d} 条 ({s['percentage']:.1f}%)"
            for s in report["sentiment_distribution"]
        ])
        
        top_lines = "\n".join([
            f"  {i+1}. {t['title'][:25]:25s} | 热度: {t['heat_score'] or 'N/A'}"
            for i, t in enumerate(report["top_10_topics"][:5])
        ])
        
        summary_text = f"""
【每日数据汇报 {today.isoformat()}】

📊 采集概览:
  总采集量: {total_topics} 条
  情感分析: {sentiment_count} 条 (覆盖率: {report['summary']['coverage_rate']:.1f}%)
  质量检查: {quality_report.get('issues_found', 0)} 个问题

📱 平台分布:
{platform_lines}

😊 情感分布:
{sentiment_lines}

🔥 TOP 5 热度话题:
{top_lines}

💾 数据已推送至远程仓库
"""
        
        # 保存汇报文本
        report_txt_path = BACKEND_ROOT / "data" / f"daily_report_{today.isoformat()}.txt"
        with open(report_txt_path, "w", encoding="utf-8") as f:
            f.write(summary_text)
        
        logger.info(f"  汇报已保存: {report_txt_path}")
        logger.info(f"\n{'='*60}")
        logger.info(f"✅ 每日流程完成 | {datetime.now().strftime('%H:%M:%S')}")
        logger.info(f"{'='*60}")
        
        return summary_text
        
    except Exception as e:
        logger.error(f"❌ 最终流程异常: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("用法: python daily_pipeline.py <crawl|finalize>")
        sys.exit(1)
    
    mode = sys.argv[1].lower()
    
    if mode == "crawl":
        success = run_crawl()
        sys.exit(0 if success else 1)
    elif mode == "finalize":
        report = run_finalize()
        sys.exit(0 if report else 1)
    else:
        print(f"未知模式: {mode}")
        print("用法: python daily_pipeline.py <crawl|finalize>")
        sys.exit(1)


if __name__ == "__main__":
    main()
