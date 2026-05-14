"""Celery app singleton."""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bluemetrics.settings.dev")

app = Celery("bluemetrics")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
