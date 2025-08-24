import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")  # 실제 프로젝트명

app = Celery("project")

# Django settings.py에서 CELERY_로 시작하는 설정 가져오기
app.config_from_object("django.conf:settings", namespace="CELERY")

# Django 앱의 tasks.py 자동으로 탐지
app.autodiscover_tasks()

# stdout / stderr 리디렉션
app.conf.update(
    worker_redirect_stdouts=True,
    worker_redirect_stdouts_level="INFO",
)