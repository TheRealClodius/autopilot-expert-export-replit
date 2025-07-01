#!/bin/bash
export REDIS_URL=redis://localhost:6379/0
exec celery -A celery_app beat --loglevel=info