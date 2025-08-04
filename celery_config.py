from celery import Celery
import os

# Redis配置
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')

# 創建Celery實例
celery_app = Celery(
    'ocr_service',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['celery_tasks']
)

# Celery配置
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Taipei',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5分鐘超時
    task_soft_time_limit=600,  # 10分鐘軟超時
    worker_prefetch_multiplier=1,
    result_expires=3600,  # 結果保存1小時
)