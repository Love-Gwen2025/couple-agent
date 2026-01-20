"""
Celery 任务模块

导出所有异步任务，方便统一管理和导入
"""

from app.tasks.document_tasks import process_document_task
from app.tasks.embedding_tasks import store_message_embedding_task

__all__ = ["process_document_task", "store_message_embedding_task"]
