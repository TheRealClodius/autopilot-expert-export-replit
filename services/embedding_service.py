"""
Embedding Service - Generates embeddings and manages vector storage.
Handles text embedding generation and Pinecone operations using Google Gemini.
"""

import logging
from typing import List, Dict, Any, Optional
import asyncio
from google import genai
from pinecone import Pinecone

from config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Service for generating text embeddings and managing vector storage.
    Uses Google Gemini text-embedding-004 model for embedding generation and Pinecone for storage.
    """
    
    def __init__(self):
        self.embedding_model = "text-embedding-004"  # Google's latest embedding model
        self.client = None
        self.pc = None
        self.index = None
        self._initialize_services()
        
    def _initialize_services(self):
        """Initialize Gemini and Pinecone connection"""
        try:
            # Initialize Gemini client
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
            logger.info(f"Initialized Gemini client for embeddings")
            
            # Initialize Pinecone
            self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
            self.index = self.pc.Index(settings.PINECONE_INDEX_NAME)
            logger.info(f"Connected to Pinecone index: {settings.PINECONE_INDEX_NAME}")
            
        except Exception as e:
            logger.error(f"Error initializing embedding service: {e}")
            raise
    
    async def embed_text(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a single text string using Gemini.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        try:
            if not text or not text.strip():
                return None
            
            # Generate embedding using Gemini client
            from google.genai import types
            
            result = self.client.models.embed_content(
                model=self.embedding_model,
                contents=[types.Content(parts=[types.Part(text=text)])]
            )
            
            if result and hasattr(result, 'embeddings') and result.embeddings:
                # Extract first embedding from the batch response
                embedding = result.embeddings[0]
                if hasattr(embedding, 'values'):
                    return embedding.values
                else:
                    logger.warning(f"Embedding object has no values: {embedding}")
                    return None
            else:
                logger.warning(f"No embedding returned from Gemini API. Result: {result}")
                return None
            
        except Exception as e:
            logger.error(f"Error generating embedding with Gemini: {e}")
            return None
    
    async def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for a batch of texts using Gemini.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            if not texts:
                return []
            
            # Filter out empty texts
            valid_texts = [text for text in texts if text and text.strip()]
            
            if not valid_texts:
                return [None] * len(texts)
            
            logger.info(f"Generating embeddings for {len(valid_texts)} texts...")
            
            # Generate embeddings one by one (Gemini API limitation)
            embeddings = []
            for text in valid_texts:
                try:
                    embedding = await self.embed_text(text)
                    embeddings.append(embedding)
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.warning(f"Failed to embed text: {str(e)}")
                    embeddings.append(None)
            
            # Map back to original positions
            result = []
            valid_idx = 0
            
            for text in texts:
                if text and text.strip():
                    result.append(embeddings[valid_idx])
                    valid_idx += 1
                else:
                    result.append(None)
            
            successful_embeddings = len([e for e in embeddings if e is not None])
            logger.info(f"Generated {successful_embeddings}/{len(valid_texts)} embeddings successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            return [None] * len(texts)
    
    async def embed_and_store_messages(self, messages: List[Dict[str, Any]]) -> int:
        """
        Generate embeddings for messages and store them in Pinecone.
        
        Args:
            messages: List of processed messages
            
        Returns:
            Number of messages successfully embedded and stored
        """
        try:
            if not messages:
                return 0
            
            logger.info(f"Embedding and storing {len(messages)} messages...")
            
            # Extract texts for embedding
            texts = [msg.get("content", "") for msg in messages]
            
            # Generate embeddings in batches
            embeddings = await self.embed_batch(texts)
            
            # Prepare vectors for Pinecone
            vectors_to_upsert = []
            successful_embeddings = 0
            
            for i, (message, embedding) in enumerate(zip(messages, embeddings)):
                if embedding is None:
                    logger.warning(f"No embedding generated for message {message.get('id', i)}")
                    continue
                
                vector = {
                    "id": message["id"],
                    "values": embedding,
                    "metadata": self._prepare_metadata_for_pinecone(message)
                }
                
                vectors_to_upsert.append(vector)
                successful_embeddings += 1
            
            # Store vectors in Pinecone in batches
            if vectors_to_upsert:
                batch_size = 100  # Pinecone batch limit
                
                for i in range(0, len(vectors_to_upsert), batch_size):
                    batch = vectors_to_upsert[i:i + batch_size]
                    
                    try:
                        self.index.upsert(vectors=batch)
                        logger.info(f"Upserted batch {i//batch_size + 1}/{(len(vectors_to_upsert)-1)//batch_size + 1}")
                        
                        # Small delay to avoid rate limiting
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        logger.error(f"Error upserting batch {i//batch_size + 1}: {e}")
                        continue
            
            logger.info(f"Successfully embedded and stored {successful_embeddings} messages")
            return successful_embeddings
            
        except Exception as e:
            logger.error(f"Error in embed_and_store_messages: {e}")
            return 0
    
    def _prepare_metadata_for_pinecone(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare message metadata for Pinecone storage.
        
        Args:
            message: Processed message dictionary
            
        Returns:
            Metadata dictionary compatible with Pinecone
        """
        try:
            metadata = message.get("metadata", {}).copy()
            
            # Add essential fields
            metadata["content"] = message.get("content", "")[:1000]  # Limit content length
            metadata["text"] = message.get("text", "")[:1000]
            metadata["timestamp"] = message.get("timestamp", "")
            metadata["processed_at"] = message.get("processed_at", "")
            
            # Ensure all values are JSON serializable
            cleaned_metadata = {}
            for key, value in metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    cleaned_metadata[key] = value
                elif isinstance(value, list):
                    # Convert lists to strings for Pinecone
                    cleaned_metadata[key] = ",".join(str(v) for v in value)
                else:
                    # Convert other types to strings
                    cleaned_metadata[key] = str(value)
            
            return cleaned_metadata
            
        except Exception as e:
            logger.error(f"Error preparing metadata for Pinecone: {e}")
            return {"content": message.get("content", "")[:1000]}
    
    async def delete_vectors_by_filter(self, filter_dict: Dict[str, Any]) -> bool:
        """
        Delete vectors from Pinecone based on metadata filter.
        
        Args:
            filter_dict: Filter criteria for deletion
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Deleting vectors with filter: {filter_dict}")
            
            self.index.delete(filter=filter_dict)
            
            logger.info("Successfully deleted vectors")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting vectors: {e}")
            return False
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """Get Pinecone index statistics"""
        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vectors": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
                "namespaces": dict(stats.namespaces) if stats.namespaces else {}
            }
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {}
    
    async def test_connection(self) -> bool:
        """Test connection to Pinecone"""
        try:
            stats = await self.get_index_stats()
            if "total_vectors" in stats:
                logger.info("Pinecone connection test successful")
                return True
            return False
        except Exception as e:
            logger.error(f"Pinecone connection test failed: {e}")
            return False
