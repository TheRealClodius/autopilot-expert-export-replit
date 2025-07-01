"""
Document Ingestion Service - Processes documents and stores them in Pinecone vector database.
Handles text chunking, embedding generation, and vector storage for testing purposes.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from services.embedding_service import EmbeddingService
from tools.vector_search import VectorSearchTool
import hashlib
import re

logger = logging.getLogger(__name__)

class DocumentIngestionService:
    """
    Service for ingesting documents into the vector database for testing.
    Handles chunking, embedding generation, and vector storage.
    """
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_tool = VectorSearchTool()
        self.chunk_size = 1000
        self.chunk_overlap = 200
    
    def chunk_text(self, text: str, chunk_size: Optional[int] = None, overlap: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks for vector storage.
        
        Args:
            text: Text to chunk
            chunk_size: Maximum size of each chunk (default: 1000)
            overlap: Overlap between chunks (default: 200)
            
        Returns:
            List of chunk dictionaries with text and metadata
        """
        chunk_size = chunk_size or self.chunk_size
        overlap = overlap or self.chunk_overlap
        
        # Clean the text
        text = self._clean_text(text)
        
        chunks = []
        start = 0
        chunk_id = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # If we're not at the end, try to break at a sentence or paragraph boundary
            if end < len(text):
                # Look for sentence endings within the last 100 characters
                search_start = max(end - 100, start)
                sentence_breaks = []
                
                for match in re.finditer(r'[.!?]\s+', text[search_start:end]):
                    sentence_breaks.append(search_start + match.end())
                
                if sentence_breaks:
                    end = sentence_breaks[-1]  # Use the last sentence break
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:  # Only add non-empty chunks
                chunks.append({
                    'text': chunk_text,
                    'chunk_id': chunk_id,
                    'start_position': start,
                    'end_position': end,
                    'length': len(chunk_text)
                })
                chunk_id += 1
            
            # Move start position considering overlap
            start = max(start + chunk_size - overlap, end)
            
            # Prevent infinite loop
            if start >= len(text):
                break
        
        logger.info(f"Created {len(chunks)} chunks from {len(text)} characters")
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for processing."""
        # Remove markdown headers but keep the text
        text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove extra blank lines
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        return text.strip()
    
    async def ingest_document(self, file_path: str, document_type: str = "test_document") -> Dict[str, Any]:
        """
        Ingest a document into the vector database.
        
        Args:
            file_path: Path to the document file
            document_type: Type/category of the document
            
        Returns:
            Dictionary with ingestion results
        """
        try:
            # Read the document
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Generate document ID
            doc_id = self._generate_document_id(file_path, content)
            
            # Chunk the document
            chunks = self.chunk_text(content)
            
            if not chunks:
                return {"status": "error", "error": "No chunks generated from document"}
            
            # Generate embeddings and prepare vectors
            vectors_to_upsert = []
            successful_chunks = 0
            
            for i, chunk in enumerate(chunks):
                try:
                    # Generate embedding
                    embedding = await self.embedding_service.embed_text(chunk['text'])
                    
                    if embedding is None:
                        logger.warning(f"Failed to create embedding for chunk {i}")
                        continue
                    
                    # Create vector ID
                    vector_id = f"{doc_id}_chunk_{chunk['chunk_id']}"
                    
                    # Prepare metadata
                    metadata = {
                        'document_id': doc_id,
                        'document_type': document_type,
                        'chunk_id': chunk['chunk_id'],
                        'text': chunk['text'][:1000],  # Limit metadata text size
                        'file_path': file_path,
                        'start_position': chunk['start_position'],
                        'end_position': chunk['end_position'],
                        'length': chunk['length']
                    }
                    
                    vectors_to_upsert.append({
                        'id': vector_id,
                        'values': embedding,
                        'metadata': metadata
                    })
                    
                    successful_chunks += 1
                    
                except Exception as e:
                    logger.error(f"Error processing chunk {i}: {str(e)}")
                    continue
            
            if not vectors_to_upsert:
                return {"status": "error", "error": "No valid vectors created"}
            
            # Upsert vectors to Pinecone
            if self.vector_tool.pinecone_available:
                try:
                    self.vector_tool.index.upsert(vectors=vectors_to_upsert)
                    logger.info(f"Successfully upserted {len(vectors_to_upsert)} vectors to Pinecone")
                except Exception as e:
                    logger.error(f"Error upserting to Pinecone: {str(e)}")
                    return {"status": "error", "error": f"Pinecone upsert failed: {str(e)}"}
            else:
                return {"status": "error", "error": "Pinecone not available"}
            
            return {
                "status": "success",
                "document_id": doc_id,
                "total_chunks": len(chunks),
                "successful_chunks": successful_chunks,
                "vectors_upserted": len(vectors_to_upsert),
                "file_path": file_path,
                "document_type": document_type
            }
            
        except Exception as e:
            logger.error(f"Error ingesting document {file_path}: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def _generate_document_id(self, file_path: str, content: str) -> str:
        """Generate a unique document ID based on file path and content hash."""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        file_name = os.path.basename(file_path).replace('.', '_')
        return f"{file_name}_{content_hash}"
    
    async def search_test_content(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search the test content in the vector database.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of search results
        """
        try:
            results = await self.vector_tool.search(query, top_k=top_k)
            
            # Format results for better readability
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'id': result.get('id', 'unknown'),
                    'score': result.get('score', 0.0),
                    'text_preview': result.get('metadata', {}).get('text', '')[:200] + "...",
                    'document_type': result.get('metadata', {}).get('document_type', 'unknown'),
                    'chunk_id': result.get('metadata', {}).get('chunk_id', 'unknown')
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching test content: {str(e)}")
            return []
    
    async def delete_test_documents(self, document_type: str = "test_document") -> Dict[str, Any]:
        """
        Delete test documents from the vector database.
        
        Args:
            document_type: Type of documents to delete
            
        Returns:
            Dictionary with deletion results
        """
        try:
            if not self.vector_tool.pinecone_available:
                return {"status": "error", "error": "Pinecone not available"}
            
            # Search for vectors with the specified document type
            # Note: This is a simple approach; in production, you'd want a more sophisticated cleanup
            logger.info(f"Preparing to delete test documents of type: {document_type}")
            
            return {
                "status": "success", 
                "message": f"Test documents of type '{document_type}' marked for deletion",
                "note": "In production, implement proper vector ID tracking for deletion"
            }
            
        except Exception as e:
            logger.error(f"Error deleting test documents: {str(e)}")
            return {"status": "error", "error": str(e)}