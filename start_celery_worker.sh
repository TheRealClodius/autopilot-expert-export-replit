#!/bin/bash
export REDIS_URL=redis://localhost:6379/0
exec celery -A celery_app worker --loglevel=info --queues=default,ingestion,summarization,processing,priority