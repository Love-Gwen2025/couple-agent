"""
Celery 应用配置

使用 Redis 作为 Broker 和 Result Backend
配置复用 settings.py 中的属性
"""

from celery import Celery

from app.core.settings import get_settings

# 获取配置
settings = get_settings()

# 创建 Celery 实例
celery_app = Celery(
    "couple_agent",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_url,
)

celery_app.conf.update(
    # 序列化配置
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # 时区
    timezone="Asia/Shanghai",
    enable_utc=True,
    # 任务配置
    task_track_started=True,
    task_time_limit=600,
    task_soft_time_limit=540,
    # 重试配置
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Worker 配置
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
    # 连接重试
    broker_connection_retry_on_startup=True,
)
