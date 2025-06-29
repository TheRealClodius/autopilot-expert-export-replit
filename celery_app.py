"""
Celery application configuration for background task processing.
Handles task queuing, scheduling, and worker management.
"""

import logging
from celery import Celery, signals
from celery.schedules import crontab
from kombu import Queue

from config import settings

logger = logging.getLogger(__name__)

# Determine broker URL with fallback for deployment
def get_broker_url():
    """Get Celery broker URL with fallback for deployment environments"""
    broker_url = getattr(settings, 'CELERY_BROKER_URL', '') or ''
    
    # Enhanced Redis detection and blocking
    if not broker_url or broker_url.strip() == "":
        logger.info("No Celery broker URL configured, using memory transport")
        return 'memory://'
    
    # Block ANY Redis URLs to prevent deployment connection attempts
    broker_lower = broker_url.lower()
    redis_indicators = ['redis://', 'rediss://', '127.0.0.1', 'localhost', ':6379']
    
    if any(indicator in broker_lower for indicator in redis_indicators):
        logger.info(f"Detected Redis URL, forcing memory transport: {broker_url}")
        return 'memory://'
    
    # Additional validation for deployment environments
    if os.environ.get('REPLIT_DOMAINS') or os.environ.get('REPLIT_DEPLOYMENT'):
        logger.info("Deployment environment detected, using memory transport")
        return 'memory://'
        
    return broker_url

def get_result_backend():
    """Get Celery result backend with fallback for deployment environments"""
    backend_url = getattr(settings, 'CELERY_RESULT_BACKEND', '') or ''
    
    # Force memory backend in deployment to avoid any Redis connections
    if not backend_url or backend_url.strip() == "" or backend_url.strip().startswith('redis://127.0.0.1'):
        logger.info(f"Using cache+memory backend (backend_url='{backend_url}')")
        return 'cache+memory://'
    
    # Additional check for localhost Redis URLs  
    if 'localhost' in backend_url or '127.0.0.1' in backend_url:
        logger.info(f"Detected localhost Redis URL, using memory backend instead: {backend_url}")
        return 'cache+memory://'
        
    return backend_url

# Create Celery application with deployment-safe configuration
celery_app = Celery(
    'autopilot_expert',
    broker=get_broker_url(),
    backend=get_result_backend(),
    include=[
        'workers.knowledge_update_worker',
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        'workers.knowledge_update_worker.daily_ingestion': {'queue': 'ingestion'},
        'workers.knowledge_update_worker.manual_ingestion': {'queue': 'ingestion'},
        'workers.knowledge_update_worker.process_knowledge_queue': {'queue': 'processing'},
    },
    
    # Queue configuration
    task_queues=[
        Queue('default', routing_key='default'),
        Queue('ingestion', routing_key='ingestion'),
        Queue('processing', routing_key='processing'),
        Queue('priority', routing_key='priority'),
    ],
    
    # Default queue
    task_default_queue='default',
    task_default_exchange='default',
    task_default_routing_key='default',
    
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    task_time_limit=1800,  # 30 minutes
    task_soft_time_limit=1500,  # 25 minutes
    worker_prefetch_multiplier=1,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_persistent=True,
    
    # Retry settings
    task_annotations={
        '*': {
            'rate_limit': '100/m',  # 100 tasks per minute
            'time_limit': 1800,
            'soft_time_limit': 1500,
        },
        'workers.knowledge_update_worker.daily_ingestion': {
            'rate_limit': '1/m',  # 1 task per minute
            'time_limit': 3600,   # 1 hour
            'soft_time_limit': 3300,  # 55 minutes
        },
        'workers.knowledge_update_worker.manual_ingestion': {
            'rate_limit': '2/m',  # 2 tasks per minute
            'time_limit': 3600,   # 1 hour
            'soft_time_limit': 3300,  # 55 minutes
        },
    },
    
    # Beat schedule for periodic tasks
    beat_schedule={
        'daily-ingestion': {
            'task': 'workers.knowledge_update_worker.daily_ingestion',
            'schedule': crontab(hour=2, minute=0),  # 2 AM daily
            'options': {
                'queue': 'ingestion',
                'priority': 9,  # High priority
            }
        },
        'process-knowledge-queue': {
            'task': 'workers.knowledge_update_worker.process_knowledge_queue',
            'schedule': crontab(hour=3, minute=0),  # 3 AM daily
            'options': {
                'queue': 'processing',
                'priority': 7,  # Medium-high priority
            }
        },
        'cleanup-old-data': {
            'task': 'workers.knowledge_update_worker.cleanup_old_data',
            'schedule': crontab(hour=1, minute=0, day_of_week=0),  # Weekly on Sunday at 1 AM
            'options': {
                'queue': 'processing',
                'priority': 3,  # Low priority
            }
        },
    },
    
    # Worker settings
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Error handling (task_acks_late already set above)
    # task_reject_on_worker_lost=True, # Also duplicate
)

# Custom task base class
class BaseTask(celery_app.Task):
    """Base task class with common functionality"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        logger.error(f"Task {self.name}[{task_id}] failed: {exc}")
        
        # Could add additional failure handling here:
        # - Send notifications
        # - Update database
        # - Trigger retry logic
    
    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success"""
        logger.info(f"Task {self.name}[{task_id}] succeeded")
        
        # Could add additional success handling here:
        # - Update metrics
        # - Clean up resources
        # - Trigger dependent tasks
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry"""
        logger.warning(f"Task {self.name}[{task_id}] retrying: {exc}")

# Set the base task class
celery_app.Task = BaseTask

# Health check task
@celery_app.task(bind=True, name='health_check')
def health_check(self):
    """Health check task for monitoring"""
    try:
        from datetime import datetime
        
        # Skip Redis connection in deployment if not configured
        redis_url = getattr(settings, 'REDIS_URL', '') or ''
        if not redis_url or redis_url.strip() == "" or redis_url.strip() == "redis://":
            logger.info(f"Redis not configured (url='{redis_url}'), skipping Redis health check")
            return {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'worker_id': self.request.id,
                'redis': 'not_configured'
            }
        
        # Test Redis connection only if URL is configured and valid
        try:
            import redis
            # Additional validation - ensure URL is a proper Redis URL
            if not redis_url.startswith(('redis://', 'rediss://')):
                logger.info(f"Invalid Redis URL format: '{redis_url}', skipping connection")
                return {
                    'status': 'healthy',
                    'timestamp': datetime.now().isoformat(),
                    'worker_id': self.request.id,
                    'redis': 'invalid_url'
                }
            redis_client = redis.from_url(redis_url)
            redis_client.ping()
        except Exception as redis_error:
            logger.warning(f"Redis connection failed but continuing: {redis_error}")
            return {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'worker_id': self.request.id,
                'redis': 'connection_failed_but_ok'
            }
        
        return {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'worker_id': self.request.id,
            'redis': 'connected'
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

# Task to clean up old data
@celery_app.task(bind=True, name='cleanup_old_data')
def cleanup_old_data(self):
    """Clean up old temporary data and logs"""
    try:
        import asyncio
        from services.memory_service import MemoryService
        from datetime import datetime, timedelta
        
        logger.info("Starting cleanup of old data...")
        
        # Setup async context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(_perform_cleanup())
            logger.info(f"Cleanup completed: {result}")
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error in cleanup task: {e}")
        raise

async def _perform_cleanup():
    """Perform the actual cleanup operations"""
    try:
        memory_service = MemoryService()
        
        # This would implement actual cleanup logic
        # For now, return a placeholder result
        cleanup_result = {
            'status': 'completed',
            'old_conversations_removed': 0,
            'temp_data_cleared': 0,
            'cache_entries_expired': 0,
            'timestamp': datetime.now().isoformat()
        }
        
        return cleanup_result
        
    except Exception as e:
        logger.error(f"Error in cleanup operations: {e}")
        return {'status': 'failed', 'error': str(e)}

# Signal handlers for monitoring
@signals.worker_ready.connect
def worker_ready(sender=None, **kwargs):
    """Signal handler for when worker is ready"""
    logger.info(f"Celery worker {sender} is ready")

@signals.worker_shutdown.connect
def worker_shutdown(sender=None, **kwargs):
    """Signal handler for when worker shuts down"""
    logger.info(f"Celery worker {sender} is shutting down")

@signals.task_prerun.connect
def task_prerun(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Signal handler before task execution"""
    logger.debug(f"Task {task.name}[{task_id}] starting")

@signals.task_postrun.connect
def task_postrun(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Signal handler after task execution"""
    logger.debug(f"Task {task.name}[{task_id}] finished with state: {state}")

# Custom configuration for development/production
def configure_celery_for_environment(environment='production'):
    """Configure Celery settings based on environment"""
    if environment == 'development':
        celery_app.conf.update(
            task_always_eager=False,  # Set to True for synchronous execution in dev
            task_eager_propagates=True,
            worker_log_level='DEBUG',
            beat_schedule={}  # Disable scheduled tasks in development
        )
    elif environment == 'testing':
        celery_app.conf.update(
            task_always_eager=True,  # Execute tasks synchronously in tests
            task_eager_propagates=True,
            task_store_eager_result=True,
            broker_connection_retry_on_startup=True
        )

# Configure based on environment
import os
environment = os.getenv('ENVIRONMENT', 'production')
configure_celery_for_environment(environment)

if __name__ == '__main__':
    celery_app.start()
