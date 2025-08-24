import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")  

app = Celery("project")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

# stdout / stderr 리디렉션
app.conf.update(
    worker_redirect_stdouts=True,
    worker_redirect_stdouts_level="INFO",
)