#!/usr/bin/env python
"""
Helper script to run the Celery worker
"""
from app.tasks import celery_app

if __name__ == '__main__':
    celery_app.start()
