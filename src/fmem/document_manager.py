"""
DocumentManager - Document Lifecycle Management

Manages document indexing, chunking, and metadata operations.
Extracted from MemoryRetrieval to follow Single Responsibility Principle.
"""

import datetime
import logging
import os
import re
from typing import List, Dict, Optional, Any
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class DocumentManager:
    """
    Manages document lifecycle: add, index, chunk, update metadata.
    
    Responsibilities:
    - Document validation (path, extension, size, symlinks)
    - Content loading and cleaning
    - Chunking for markdown files
    - Metadata extraction and caching
    - Coordinate with EmbeddingService, SearchIndex, DatabaseService
    
    Dependencies (all via constructor):
    - embedding_service: For generating embeddings
    - search_index: For FAISS index operations
    - database_service: For SQLite storage
    - file_summarizer: For summary extraction
    - config: For validation rules
    """
    
    def __init__(
        self,
        embedding_service: 'EmbeddingService',
        search_index: 'SearchIndex',
        database_service: 'DatabaseService',
        file_summarizer: 'FileSummarizer',
        config: 'ConfigService'
    ):
        """
        Initialize DocumentManager with dependencies.
        
        Args:
            embedding_service: Service for generating embeddings
            search_index: FAISS index manager
            database_service: SQLite database manager
            file_summarizer: Summary extraction service
            config: Configuration service
        """
        self._embedding_service = embedding_service
        self._search_index = search_index
        self._db = database_service
        self._summarizer = file_summarizer
        self._config = config
        
        # Document metadata cache
        self._doc_metadata: List[Dict] = []
        self._doc_metadata_cache: Dict[str, Dict] = {}
        
        logger.info("DocumentManager initialized")
    
    @property
    def doc_metadata(self) -> List[Dict]:
        """Get document metadata list."""
        return self._doc_metadata
    
    @property
    def doc_count(self) -> int:
        """Get number of documents."""
        return len(self._doc_metadata)
    
    def _validate_path(self, filepath: str) -> Optional[str]:
        """
        Validate and sanitize file path.
        
        Args:
            filepath: Input file path
            
        Returns:
            Sanitized path or None if invalid
        """
        # Import here to avoid circular dependency
        from .path_utils import sanitize_path, is_safe_symlink
        
        safe_path = sanitize_path(filepath, config=self._config)
        if safe_path is None:
            logger.error(f"Invalid filepath: {filepath}")
            return None
        
        # Check symlink safety
        is_safe, reason = is_safe_symlink(safe_path, config=self._config)
        if not is_safe:
            logger.error(f"Unsafe symlink detected: {reason}")
            return None
        
        return safe_path
    
    def _load_content(self, filepath: str) -> Optional[str]:
        """
        Load and clean file content.
        
        Args:
            filepath: Path to file
            
        Returns:
            File content or None if failed
        """
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return None
        
        # Check file size
        from .config import ConfigService
        if hasattr(self._config, 'validate_file_size'):
            valid, msg = self._config.validate_file_size(filepath)
            if not valid:
                logger.error(msg)
                return None
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(filepath, 'r', encoding='latin-1', errors='ignore') as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"Failed to read {filepath}: {e}")
                return None
        except Exception as e:
            logger.error(f"Failed to read {filepath}: {e}")
            return None
        
        # Clean content
        content = re.sub(r'[^\x20-\x7E\t\n\r]', '', content)
        
        return content
    
    def _check_duplicate(self, filepath: str, file_mtime: int) -> tuple:
        """
        Check if file already indexed with same mtime.
        
        Args:
            filepath: File path
            file_mtime: Current modification time
            
        Returns:
            (is_duplicate: bool, existing_idx: Optional[int], created_at: int)
        """
        created_at = int(datetime.datetime.now().timestamp())
        
        for i, doc in enumerate(self._doc_metadata):
            if doc['filepath'] == filepath:
                stored_mtime = doc.get('last_modified', 0)
                if stored_mtime == file_mtime:
                    return True, i, doc.get('created_at', created_at)
                else:
                    logger.info(f"File modified, re-indexing: {filepath}")
                    return False, i, doc.get('created_at', created_at)
        
        return False, None, created_at
    
    def add_document(
        self,
        filepath: str,
        content: Optional[str] = None,
        chunk_by_sections: bool = True
    ) -> bool:
        """
        Add a document to memory system with validation.
        
        Args:
            filepath: Path to file
            content: Full document content. If None, reads from file.
            chunk_by_sections: If True, split markdown by ## headings.
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate path
            filepath = self._validate_path(filepath)
            if filepath is None:
                return False
            
            # Check file extension
            if hasattr(self._config, 'is_valid_extension'):
                if not self._config.is_valid_extension(filepath):
                    logger.error(f"Invalid file extension: {filepath}")
                    return False
            elif not filepath.endswith('.md'):
                # Default to markdown only
                pass
            
            # Get file modification time
            file_mtime = None
            if os.path.exists(filepath):
                file_mtime = int(os.path.getmtime(filepath))
                
                # Check for duplicates
                is_dup, existing_idx, created_at = self._check_duplicate(filepath, file_mtime)
                if is_dup:
                    logger.info(f"Skipped (unchanged): {filepath}")
                    return True
            else:
                created_at = int(datetime.datetime.now().timestamp())
            
            # Load content if not provided
            if content is None:
                content = self._load_content(filepath)
                if content is None:
                    return False
            
            # Validate content
            if not content or len(content.strip()) == 0:
                logger.error("Empty content")
                return False
            
            if hasattr(self._config, 'MAX_FILE_SIZE'):
                if len(content) > self._config.MAX_FILE_SIZE:
                    logger.error("Content too large")
                    return False
            
            if hasattr(self._config, 'MAX_EMBEDDING_SIZE'):
                if len(content) > self._config.MAX_EMBEDDING_SIZE:
                    logger.error(f"Content exceeds embedding size limit")
                    return False
            
            # Generate embedding for full document
            main_embedding = self._embedding_service.get_embedding(content)
            
            # Determine if chunking
            should_chunk = chunk_by_sections and filepath.endswith('.md')
            
            if should_chunk:
                return self._add_chunked_document(
                    filepath, content, file_mtime, created_at, main_embedding
                )
            else:
                return self._add_single_document(
                    filepath, content, file_mtime, created_at, main_embedding
                )
                
        except Exception as e:
            logger.error(f"Error adding document {filepath}: {e}")
            return False
    
    def _add_chunked_document(
        self,
        filepath: str,
        content: str,
        file_mtime: Optional[int],
        created_at: int,
        main_embedding: Optional[np.ndarray]
    ) -> bool:
        """Add document by chunking sections."""
        # Import chunk_markdown
        from .chunking import chunk_markdown
        
        # Chunk the content
        max_size = getattr(self._config, 'max_chunk_size', 800)
        chunks = chunk_markdown(content, filepath, max_chunk_size=max_size)
        logger.info(f"✓ Split {filepath} into {len(chunks)} chunks")
        
        # Remove existing chunks for this file
        self._remove_existing_chunks(filepath)
        
        # Index each chunk
        chunk_count = 0
        for i, chunk in enumerate(chunks):
            # Preprocess and get embedding
            processed = self._embedding_service._preprocess_for_embedding(
                chunk.content, heading=chunk.heading
            )
            chunk.processed_content = processed
            
            chunk_embedding = self._embedding_service.get_embedding(
                chunk.content, heading=chunk.heading
            )
            
            if chunk_embedding is not None:
                # Add to search index
                self._search_index.add(
                    chunk_embedding, filepath, chunk.id,
                    heading=chunk.heading,
                    processed_content=processed,
                    original_length=chunk.original_length
                )
                chunk_count += 1
            
            # Store in database
            self._db.store_chunk(
                chunk_id=chunk.id,
                parent_file=chunk.parent_file,
                heading=chunk.heading,
                content=chunk.content,
                keywords=chunk.keywords,
                category=chunk.category,
                token_count=chunk.tokens,
                chunk_index=chunk.chunk_index
            )
        
        # Create metadata
        summary = self._summarizer.summarize(content, filepath)
        metadata = {
            'filepath': filepath,
            'content': content,
            'last_modified': file_mtime if file_mtime else int(datetime.datetime.now().timestamp()),
            'created_at': created_at,
            'is_chunked': True,
            'chunk_count': chunk_count,
            'summary': summary
        }
        
        # Update metadata list
        existing_idx = None
        for i, doc in enumerate(self._doc_metadata):
            if doc['filepath'] == filepath:
                existing_idx = i
                break
        
        if existing_idx is not None:
            self._doc_metadata[existing_idx] = metadata
        else:
            self._doc_metadata.append(metadata)
        
        self._doc_metadata_cache[filepath] = metadata
        
        # Store in database
        self._db.store_document(
            filepath=filepath,
            content=content,
            last_modified=metadata['last_modified'],
            created_at=created_at
        )
        
        logger.info(f"✓ Indexed {chunk_count}/{len(chunks)} chunks")
        return True
    
    def _add_single_document(
        self,
        filepath: str,
        content: str,
        file_mtime: Optional[int],
        created_at: int,
        main_embedding: Optional[np.ndarray]
    ) -> bool:
        """Add document as single unit."""
        summary = self._summarizer.summarize(content, filepath)
        
        metadata = {
            'filepath': filepath,
            'content': content,
            'last_modified': file_mtime if file_mtime else int(datetime.datetime.now().timestamp()),
            'created_at': created_at,
            'is_chunked': False,
            'chunk_count': 1 if main_embedding is not None else 0,
            'summary': summary
        }
        
        # Update metadata
        existing_idx = None
        for i, doc in enumerate(self._doc_metadata):
            if doc['filepath'] == filepath:
                existing_idx = i
                break
        
        if existing_idx is not None:
            self._doc_metadata[existing_idx] = metadata
            logger.info(f"✓ Updated document: {filepath}")
        else:
            self._doc_metadata.append(metadata)
            logger.info(f"✓ Added document: {filepath}")
        
        self._doc_metadata_cache[filepath] = metadata
        
        # Add to search index
        if main_embedding is not None:
            self._search_index.add(
                main_embedding, filepath, filepath,
                heading="", processed_content=content[:1000], original_length=len(content)
            )
        
        # Store in database
        self._db.store_document(
            filepath=filepath,
            content=content,
            last_modified=metadata['last_modified'],
            created_at=created_at
        )
        
        return True
    
    def _remove_existing_chunks(self, filepath: str) -> None:
        """Remove existing chunks from mapping TODO: implement in SearchIndex."""
        # This is a placeholder - SearchIndex needs chunk removal support
        # For now, rely on SearchIndex.add to append new chunks
        # Re-indexing will rebuild the FAISS index on save
        logger.debug(f"Removing existing chunks for {filepath}")
    
    def add_documents_batch(
        self,
        files: List[str],
        use_progress: bool = False
    ) -> Dict[str, bool]:
        """
        Add multiple documents in batch.
        
        Args:
            files: List of file paths
            use_progress: Show progress logging
            
        Returns:
            Dict mapping filepath to success status
        """
        results = {}
        total = len(files)
        
        for i, filepath in enumerate(files):
            if use_progress:
                logger.info(f"Processing {i + 1}/{total}: {filepath}")
            
            success = self.add_document(filepath)
            results[filepath] = success
            
            if not success:
                logger.warning(f"Failed to add: {filepath}")
        
        return results
    
    def get_document(self, filepath: str) -> Optional[Dict]:
        """
        Get document by filepath.
        
        Args:
            filepath: File path
            
        Returns:
            Document metadata or None
        """
        return self._doc_metadata_cache.get(filepath)
    
    def has_document(self, filepath: str) -> bool:
        """
        Check if document exists.
        
        Args:
            filepath: File path
            
        Returns:
            True if exists
        """
        return filepath in self._doc_metadata_cache
    
    def get_modification_time(self, filepath: str) -> Optional[int]:
        """
        Get stored modification time for document.
        
        Args:
            filepath: File path
            
        Returns:
            Modification timestamp or None
        """
        doc = self._doc_metadata_cache.get(filepath)
        if doc:
            return doc.get('last_modified')
        return None
    
    def reset(self) -> None:
        """Clear all document metadata."""
        self._doc_metadata = []
        self._doc_metadata_cache = {}
        logger.info("DocumentManager reset")
    
    def load_from_database(self) -> int:
        """
        Load documents from database.
        
        Returns:
            Number of documents loaded
        """
        docs = self._db.get_all_documents()
        
        existing = {d['filepath'] for d in self._doc_metadata}
        loaded = 0
        
        for doc in docs:
            if doc['filepath'] not in existing:
                self._doc_metadata.append({
                    'filepath': doc['filepath'],
                    'content': doc.get('content', ''),
                    'last_modified': doc.get('last_modified', 0),
                    'created_at': doc.get('created_at', 0),
                    'is_chunked': False,  # Assume not chunked
                    'summary': ''
                })
                loaded += 1
        
        self._rebuild_cache()
        logger.info(f"Loaded {loaded} documents from database")
        return loaded
    
    def _rebuild_cache(self) -> None:
        """Rebuild O(1) metadata cache."""
        self._doc_metadata_cache = {d['filepath']: d for d in self._doc_metadata}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get document statistics."""
        chunked = sum(1 for d in self._doc_metadata if d.get('is_chunked', False))
        return {
            'total_documents': len(self._doc_metadata),
            'chunked_documents': chunked,
            'single_documents': len(self._doc_metadata) - chunked
        }
