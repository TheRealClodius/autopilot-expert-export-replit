"""
Knowledge Update Worker - Handles daily Slack data ingestion and processing.
Runs as Celery tasks for background processing.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import asyncio

from celery import Celery
from celery.schedules import crontab

from config import settings
from services.slack_connector import SlackConnector
from services.data_processor import DataProcessor
from services.embedding_service import EmbeddingService
from services.memory_service import MemoryService
from celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3)
def daily_ingestion(self):
    """
    Daily task to ingest Slack data and update the knowledge base.
    Scheduled to run daily at 2 AM.
    """
    try:
        logger.info("Starting daily Slack data ingestion...")
        
        # Run the async ingestion process
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(_perform_daily_ingestion())
            logger.info(f"Daily ingestion completed: {result}")
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error in daily ingestion: {e}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            delay = 2 ** self.request.retries * 60  # 1, 2, 4 minutes
            logger.info(f"Retrying daily ingestion in {delay} seconds...")
            raise self.retry(countdown=delay, exc=e)
        else:
            logger.error("Daily ingestion failed after all retries")
            raise

@celery_app.task(bind=True)
def manual_ingestion(self):
    """
    Manual task to trigger immediate data ingestion.
    Can be called via API for on-demand updates.
    """
    try:
        logger.info("Starting manual Slack data ingestion...")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(_perform_manual_ingestion())
            logger.info(f"Manual ingestion completed: {result}")
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error in manual ingestion: {e}")
        raise

@celery_app.task
def process_knowledge_queue():
    """
    Process items in the knowledge update queue.
    Handles research tasks and knowledge gaps identified by Observer Agent.
    """
    try:
        logger.info("Processing knowledge update queue...")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(_process_knowledge_queue())
            logger.info(f"Knowledge queue processing completed: {result}")
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error processing knowledge queue: {e}")
        raise

async def _perform_daily_ingestion() -> Dict[str, Any]:
    """
    Perform the actual daily ingestion process.
    
    Returns:
        Dictionary containing ingestion results
    """
    try:
        # Initialize services
        slack_connector = SlackConnector()
        data_processor = DataProcessor()
        embedding_service = EmbeddingService()
        memory_service = MemoryService()
        
        # Get channels to monitor
        channels = settings.get_monitored_channels()
        if not channels:
            logger.warning("No channels configured for monitoring")
            return {"status": "skipped", "reason": "no_channels_configured"}
        
        # Calculate time range (last 24 hours with some overlap)
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=25)  # 1 hour overlap
        
        total_processed = 0
        total_embedded = 0
        errors = []
        
        for channel in channels:
            try:
                logger.info(f"Processing channel: {channel}")
                
                # Extract messages from channel
                messages = await slack_connector.extract_channel_messages(
                    channel_id=channel,
                    start_time=start_time,
                    end_time=end_time
                )
                
                if not messages:
                    logger.info(f"No new messages found in channel {channel}")
                    continue
                
                # Process and clean messages
                processed_messages = await data_processor.process_messages(messages)
                
                # Generate embeddings and store
                embedded_count = await embedding_service.embed_and_store_messages(processed_messages)
                
                total_processed += len(processed_messages)
                total_embedded += embedded_count
                
                logger.info(f"Channel {channel}: processed {len(processed_messages)}, embedded {embedded_count}")
                
            except Exception as e:
                error_msg = f"Error processing channel {channel}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue
        
        # Update ingestion metadata
        ingestion_metadata = {
            "timestamp": datetime.now().isoformat(),
            "channels_processed": len(channels),
            "total_messages_processed": total_processed,
            "total_messages_embedded": total_embedded,
            "errors": errors,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            }
        }
        
        await memory_service.store_ingestion_metadata("daily_ingestion", ingestion_metadata)
        
        result = {
            "status": "completed",
            "processed": total_processed,
            "embedded": total_embedded,
            "errors": len(errors),
            "channels": len(channels)
        }
        
        logger.info(f"Daily ingestion result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Fatal error in daily ingestion: {e}")
        return {"status": "failed", "error": str(e)}

async def _perform_manual_ingestion() -> Dict[str, Any]:
    """
    Perform manual ingestion with broader time range.
    
    Returns:
        Dictionary containing ingestion results
    """
    try:
        # Initialize services
        slack_connector = SlackConnector()
        data_processor = DataProcessor()
        embedding_service = EmbeddingService()
        memory_service = MemoryService()
        
        # Get channels to monitor
        channels = settings.get_monitored_channels()
        if not channels:
            return {"status": "skipped", "reason": "no_channels_configured"}
        
        # Manual ingestion covers last 7 days
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)
        
        total_processed = 0
        total_embedded = 0
        errors = []
        
        for channel in channels:
            try:
                logger.info(f"Manual processing channel: {channel}")
                
                # Extract messages with larger batch size for manual ingestion
                messages = await slack_connector.extract_channel_messages(
                    channel_id=channel,
                    start_time=start_time,
                    end_time=end_time,
                    batch_size=200
                )
                
                if not messages:
                    continue
                
                # Process in batches to avoid memory issues
                batch_size = 50
                for i in range(0, len(messages), batch_size):
                    batch = messages[i:i + batch_size]
                    
                    processed_batch = await data_processor.process_messages(batch)
                    embedded_count = await embedding_service.embed_and_store_messages(processed_batch)
                    
                    total_processed += len(processed_batch)
                    total_embedded += embedded_count
                    
                    logger.info(f"Processed batch {i//batch_size + 1} for channel {channel}")
                
            except Exception as e:
                error_msg = f"Error in manual processing of channel {channel}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue
        
        # Update ingestion metadata
        ingestion_metadata = {
            "timestamp": datetime.now().isoformat(),
            "type": "manual",
            "channels_processed": len(channels),
            "total_messages_processed": total_processed,
            "total_messages_embedded": total_embedded,
            "errors": errors,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            }
        }
        
        await memory_service.store_ingestion_metadata("manual_ingestion", ingestion_metadata)
        
        result = {
            "status": "completed",
            "processed": total_processed,
            "embedded": total_embedded,
            "errors": len(errors),
            "channels": len(channels),
            "days_covered": 7
        }
        
        logger.info(f"Manual ingestion result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Fatal error in manual ingestion: {e}")
        return {"status": "failed", "error": str(e)}

async def _process_knowledge_queue() -> Dict[str, Any]:
    """
    Process knowledge update queue items.
    
    Returns:
        Dictionary containing processing results
    """
    try:
        memory_service = MemoryService()
        
        # Get today's knowledge queue
        queue_key = f"knowledge_queue:{datetime.now().strftime('%Y%m%d')}"
        queue_items = await memory_service.get_queue_items(queue_key)
        
        if not queue_items:
            return {"status": "completed", "processed": 0, "message": "no_items_in_queue"}
        
        processed_items = 0
        errors = []
        
        for item in queue_items:
            try:
                item_type = item.get("type")
                
                if item_type == "knowledge_gap":
                    # Handle knowledge gaps - could trigger additional research
                    await _handle_knowledge_gap(item)
                elif item_type == "entity_research":
                    # Handle entity research requests
                    await _handle_entity_research(item)
                else:
                    logger.warning(f"Unknown queue item type: {item_type}")
                    continue
                
                processed_items += 1
                
            except Exception as e:
                error_msg = f"Error processing queue item {item.get('id', 'unknown')}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue
        
        # Clear processed items from queue
        await memory_service.clear_queue(queue_key)
        
        result = {
            "status": "completed",
            "processed": processed_items,
            "errors": len(errors),
            "total_items": len(queue_items)
        }
        
        logger.info(f"Knowledge queue processing result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing knowledge queue: {e}")
        return {"status": "failed", "error": str(e)}

async def _handle_knowledge_gap(item: Dict[str, Any]):
    """Handle knowledge gap items"""
    try:
        gap_description = item.get("description", "")
        logger.info(f"Handling knowledge gap: {gap_description}")
        
        # For now, just log the gap
        # In a full implementation, this could trigger:
        # - Additional Slack searches
        # - External API calls
        # - Manual research requests
        
    except Exception as e:
        logger.error(f"Error handling knowledge gap: {e}")

async def _handle_entity_research(item: Dict[str, Any]):
    """Handle entity research items"""
    try:
        entity = item.get("entity", "")
        logger.info(f"Handling entity research: {entity}")
        
        # For now, just log the research request
        # In a full implementation, this could trigger:
        # - Targeted Slack searches for the entity
        # - Profile lookups
        # - Project information gathering
        
    except Exception as e:
        logger.error(f"Error handling entity research: {e}")

# Set up periodic tasks
celery_app.conf.beat_schedule = {
    'daily-ingestion': {
        'task': 'workers.knowledge_update_worker.daily_ingestion',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
    'process-knowledge-queue': {
        'task': 'workers.knowledge_update_worker.process_knowledge_queue',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily
    },
}

celery_app.conf.timezone = 'UTC'
