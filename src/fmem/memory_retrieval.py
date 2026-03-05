"""
MemoryRetrieval - Refactored Composition Root (Phase 8)

Facade class that wires together all service components.
Maintains backward-compatible public API while delegating to specialized services.

Architecture:
- MemoryRetrieval: Composition root (this file)
- ConfigService: Configuration management (Phase 1)
- EmbeddingService: Embedding generation with LRU + rate limiting (Phase 2)
- SearchIndex: FAISS operations (Phase 3)
- DatabaseService: SQLite storage (Phase 4)
- ResultEnhancer: Recency + location ranking (Phase 5)
- FileSummarizer: Summary extraction (Phase 6)
- DocumentManager: Document lifecycle (Phase 7)
"""

import datetime
import logging
import os
from pathlib import Path
from typing import List, Dict, Optional, Any

import numpy as np

from .config import ConfigService
from .embedding_service import EmbeddingService
from .search_index import SearchIndex
from .database_service import DatabaseService
from .result_enhancer import ResultEnhancer, EnhancerConfig
from .file_summarizer import FileSummarizer
from .document_manager import DocumentManager
from .fmem import FastEmbedClient

logger = logging.getLogger(__name__)


class MemoryRetrieval:
    """
    FAISS-based Memory Search System - Refactored with Dependency Injection.
    
    This class is now a composition root that wires together specialized services.
    All business logic has been extracted to service classes following SRP.
    
    Public API remains backward-compatible with v3.0.
    
    Services:
    - config: Configuration management
    - embeddings: Embedding generation (Ollama + cache + rate limiting)
    - index: FAISS vector search operations
    - database: SQLite persistence
    - enhancer: Result ranking (recency + location)
    - summarizer: File summary extraction
    - documents: Document lifecycle management
    """
    
    def __init__(self, config: ConfigService = None):
        """
        Initialize MemoryRetrieval with dependency injection.
        
        Args:
            config: ConfigService instance or None to create default
        """
        # Phase 1: Configuration
        self._config = config or ConfigService()
        
        # Phase 2: Embedding Service
        embedding_client = FastEmbedClient()
        self._embedding_service = EmbeddingService(embedding_client, self._config)
        
        # Phase 3: Search Index
        self._search_index = SearchIndex(
            dimension=self._config.embedding_dim,
            data_dir=self._config.data_dir
        )
        
        # Phase 4: Database Service
        db_path = os.path.join(self._config.data_dir, 'metadata.db')
        self._database_service = DatabaseService(db_path)
        
        # Phase 5: Result Enhancer
        enhancer_config = EnhancerConfig(
            enable_recency_ranking=self._config.enable_recency_ranking,
            enable_location_ranking=self._config.enable_location_ranking,
            recency_weight=self._config.recency_weight,
            location_weight=self._config.location_weight,
            recency_threshold_days=self._config.recency_threshold_days,
            min_recency_score=self._config.min_recency_score,
            append_only_recency_factor=self._config.append_only_recency_factor,
            location_weights=self._config.location_weights
        )
        self._result_enhancer = ResultEnhancer(enhancer_config)
        
        # Phase 6: File Summarizer
        self._file_summarizer = FileSummarizer()
        
        # Phase 7: Document Manager (depends on all above)
        self._document_manager = DocumentManager(
            embedding_service=self._embedding_service,
            search_index=self._search_index,
            database_service=self._database_service,
            file_summarizer=self._file_summarizer,
            config=self._config
        )
        
        # Load persisted data
        self._search_index.load()
        self._document_manager.load_from_database()
        
        logger.info(f"MemoryRetrieval initialized with {self._document_manager.doc_count} documents")
    
    # =========================================================================
    # Public API (Backward Compatible)
    # =========================================================================
    
    def add_document(self, filepath: str, content: Optional[str] = None,
                     chunk_by_sections: bool = True) -> bool:
        """
        Add a document to memory. Delegates to DocumentManager.
        
        Args:
            filepath: Path to file
            content: File content (reads from disk if None)
            chunk_by_sections: Split markdown by ## headings
            
        Returns:
            True if successful
        """
        return self._document_manager.add_document(filepath, content, chunk_by_sections)
    
    def add_documents_batch(self, files: List[str],
                          use_progress: bool = False) -> Dict[str, bool]:
        """
        Add multiple documents. Delegates to DocumentManager.
        
        Args:
            files: List of file paths
            use_progress: Show progress
            
        Returns:
            Dict mapping filepath to success
        """
        return self._document_manager.add_documents_batch(files, use_progress)
    
    def search(self, query: str, top_k: int = 5,
               chunk_mode: str = "chunk") -> List[Dict]:
        """
        Search memory for relevant documents.
        
        Flow:
        1. Generate query embedding (EmbeddingService)
        2. Search FAISS index (SearchIndex)
        3. Enhance results with recency/location (ResultEnhancer)
        4. Return formatted results
        
        Args:
            query: Search query
            top_k: Max results
            chunk_mode: "chunk", "document", or "hybrid"
            
        Returns:
            List of result dicts
        """
        # Validate query
        valid, msg = self._config.validate_query(query)
        if not valid:
            logger.warning(f"Invalid query: {msg}")
            return []
        
        # Generate embedding
        query_embedding = self._embedding_service.get_embedding(query)
        if query_embedding is None:
            logger.error("Failed to generate query embedding")
            return []
        
        # Search FAISS
        min_score = getattr(self._config, 'min_similarity_score', 0.3)
        raw_results = self._search_index.search(
            query_embedding, top_k=top_k, min_score=min_score
        )
        
        if not raw_results:
            return []
        
        # Build result dicts
        results = []
        for r in raw_results:
            filepath = r['filepath']
            chunk_id = r['chunk_id']
            
            # Get document metadata
            doc = self._document_manager.get_document(filepath)
            
            result = {
                'filepath': filepath,
                'score': r['score'],
                'chunk_id': chunk_id,
                'heading': r.get('heading', ''),
                'processed_content': r.get('processed_content', ''),
                'original_length': r.get('original_length', 0)
            }
            
            if doc:
                result['content'] = doc.get('content', '')
                result['is_chunked'] = doc.get('is_chunked', False)
                result['summary'] = doc.get('summary', '')
            
            results.append(result)
        
        # Enhance with recency + location
        doc_metadata_map = {d['filepath']: d for d in self._document_manager.doc_metadata}
        enhanced_results = self._result_enhancer.enhance(results, doc_metadata_map)
        
        # Format based on chunk_mode
        if chunk_mode == "document":
            return self._format_as_documents(enhanced_results)
        elif chunk_mode == "hybrid":
            return self._format_as_hybrid(enhanced_results)
        
        return enhanced_results
    
    def _format_as_documents(self, results: List[Dict]) -> List[Dict]:
        """Deduplicate by document."""
        seen = set()
        docs = []
        for r in results:
            fp = r['filepath']
            if fp not in seen:
                seen.add(fp)
                docs.append({
                    'filepath': fp,
                    'content': r.get('content', ''),
                    'score': r['score'],
                    'summary': r.get('summary', ''),
                    'chunk_mode': 'document'
                })
        return docs
    
    def _format_as_hybrid(self, results: List[Dict]) -> List[Dict]:
        """Include both chunk and document info."""
        return results  # Already includes both
    
    def get_chunk(self, chunk_id: str) -> Optional[Dict]:
        """
        Get chunk by ID. Delegates to DatabaseService.
        
        Args:
            chunk_id: Chunk identifier
            
        Returns:
            Chunk dict or None
        """
        return self._database_service.get_chunk(chunk_id)
    
    def persist(self) -> bool:
        """
        Save all data to disk. Coordinates all services.
        
        Returns:
            True if successful
        """
        success = True
        
        # Save FAISS index and chunk mapping
        if not self._search_index.save():
            success = False
        
        # Close database
        self._database_service.close()
        
        return success
    
    def reset(self) -> bool:
        """
        Clear all data. Coordinates all services.
        
        Returns:
            True if successful
        """
        try:
            self._search_index.reset()
            self._document_manager.reset()
            self._database_service.reset()
            logger.info("Memory system reset")
            return True
        except Exception as e:
            logger.error(f"Failed to reset: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get memory system statistics.
        
        Returns:
            Stats dict
        """
        return {
            'documents': self._document_manager.get_stats(),
            'index_size': len(self._search_index),
            'embedding_cache_size': self._embedding_service.cache_size(),
            'data_dir': self._config.data_dir
        }
    
    def health_check(self) -> bool:
        """
        Check system health.
        
        Returns:
            True if healthy
        """
        try:
            # Check Ollama
            if not self._embedding_service.health_check():
                logger.warning("Ollama health check failed")
                return False
            
            # Check index
            if len(self._search_index) == 0 and self._document_manager.doc_count > 0:
                logger.warning("Index empty but documents exist")
                return False
            
            logger.info("Memory system healthy")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    # =========================================================================
    # Property Accessors (for backward compatibility)
    # =========================================================================
    
    @property
    def doc_metadata(self) -> List[Dict]:
        """Access document metadata (backward compat)."""
        return self._document_manager.doc_metadata
    
    @property
    def config(self) -> ConfigService:
        """Access configuration."""
        return self._config
    
    def get_document_count(self) -> int:
        """
        Get number of indexed documents.
        
        Returns:
            Document count
        """
        return self._document_manager.doc_count
    
    # =========================================================================
    # Cleanup
    # =========================================================================
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.persist()
        except Exception:
            pass  # Suppress cleanup errors
    
    def close(self) -> None:
        """Explicit cleanup."""
        self.persist()
