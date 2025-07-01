#!/usr/bin/env python3
"""
Debug script to check Celery beat task scheduling and execution.
"""

import asyncio
import logging
from datetime import datetime
from celery_app import celery_app
from workers.hourly_embedding_worker import hourly_embedding_check

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_celery_configuration():
    """Debug Celery configuration to see if tasks are properly registered."""
    logger.info("=== Celery Configuration Debug ===")
    
    # Check registered tasks
    all_tasks = list(celery_app.tasks.keys())
    logger.info(f"All registered tasks ({len(all_tasks)}):")
    for task in sorted(all_tasks):
        logger.info(f"  - {task}")
    
    # Check beat schedule
    beat_schedule = celery_app.conf.beat_schedule
    logger.info(f"\nBeat schedule ({len(beat_schedule)} entries):")
    for name, config in beat_schedule.items():
        logger.info(f"  - {name}: {config['task']} at {config['schedule']}")
    
    # Check if our hourly task is registered
    hourly_task_name = 'hourly_embedding_check'
    if hourly_task_name in all_tasks:
        logger.info(f"\n✅ Task '{hourly_task_name}' is registered")
    else:
        logger.error(f"\n❌ Task '{hourly_task_name}' is NOT registered")
        # Check for similar names
        similar = [t for t in all_tasks if 'hourly' in t or 'embedding' in t]
        if similar:
            logger.info(f"Similar tasks found: {similar}")
    
    # Check if hourly task is in beat schedule
    hourly_beat_entry = None
    for name, config in beat_schedule.items():
        if 'hourly' in name.lower() and 'embedding' in config['task']:
            hourly_beat_entry = (name, config)
            break
    
    if hourly_beat_entry:
        name, config = hourly_beat_entry
        logger.info(f"✅ Hourly embedding task found in beat schedule: '{name}' -> {config['task']}")
    else:
        logger.error("❌ Hourly embedding task NOT found in beat schedule")

def test_manual_task_execution():
    """Test manual execution of the hourly embedding task."""
    logger.info("\n=== Manual Task Execution Test ===")
    try:
        # Try to execute the task directly
        logger.info("Executing hourly_embedding_check task manually...")
        
        # Create task instance and run
        result = hourly_embedding_check.apply()
        logger.info(f"Task result: {result.result}")
        logger.info("✅ Manual task execution succeeded")
        return True
        
    except Exception as e:
        logger.error(f"❌ Manual task execution failed: {e}")
        return False

def test_celery_delay():
    """Test sending task to Celery queue."""
    logger.info("\n=== Celery Queue Test ===")
    try:
        # Send task to queue
        logger.info("Sending hourly_embedding_check to Celery queue...")
        result = hourly_embedding_check.delay()
        logger.info(f"Task queued with ID: {result.id}")
        
        # Wait a bit and check result
        logger.info("Waiting for task to complete...")
        try:
            task_result = result.get(timeout=60)  # Wait up to 60 seconds
            logger.info(f"Task completed: {task_result}")
            logger.info("✅ Celery queue execution succeeded")
            return True
        except Exception as e:
            logger.error(f"❌ Task execution failed: {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to queue task: {e}")
        return False

def check_beat_schedule_file():
    """Check the beat schedule file for any issues."""
    logger.info("\n=== Beat Schedule File Check ===")
    try:
        import os
        from celery.beat import PersistentScheduler
        
        # Check if schedule file exists
        schedule_file = "celerybeat-schedule"
        if os.path.exists(schedule_file):
            stat = os.stat(schedule_file)
            logger.info(f"Schedule file exists: {schedule_file}")
            logger.info(f"File size: {stat.st_size} bytes")
            logger.info(f"Last modified: {datetime.fromtimestamp(stat.st_mtime)}")
        else:
            logger.warning("Schedule file does not exist")
        
        return True
    except Exception as e:
        logger.error(f"Error checking schedule file: {e}")
        return False

def main():
    """Run all debug checks."""
    logger.info("Starting Celery beat debugging...")
    
    # Run all checks
    debug_celery_configuration()
    check_beat_schedule_file()
    
    # Test manual execution
    manual_success = test_manual_task_execution()
    
    # Test Celery queue (only if manual works)
    if manual_success:
        queue_success = test_celery_delay()
    else:
        logger.warning("Skipping queue test due to manual execution failure")
    
    logger.info("\n=== Summary ===")
    logger.info("Check the output above for any issues with task registration or scheduling.")

if __name__ == "__main__":
    main()