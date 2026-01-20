"""
Celery 配置模块

通过 config_from_object 延迟加载，避免模块导入时就连接 Redis
"""

from app.core.settings import get_settings

settings = get_settings()

# Broker 和 Backend
broker_url = settings.celery_broker_url
result_backend = settings.celery_result_url

# 序列化配置
task_serializer = "json"
accept_content = ["json"]
result_serializer = "json"

# 时区
timezone = "Asia/Shanghai"
enable_utc = True

# 任务配置
task_track_started = True  # 追踪任务开始状态
task_time_limit = 600  # 任务最大执行时间 10 分钟
task_soft_time_limit = 540  # 软超时 9 分钟（允许清理）

# 重试配置
task_acks_late = True  # 任务完成后才确认（防止丢失）
task_reject_on_worker_lost = True  # Worker 丢失时拒绝任务

# Worker 配置
worker_prefetch_multiplier = 1  # 每次只取一个任务
worker_concurrency = 4  # 并发数
