#!/usr/bin/env python3
"""
FAISS-based Memory Search System - Production Hardened

Provides offline-first semantic search for agent memory using FAISS embeddings.
Zero external dependencies — works via litellm → Ollama (no OpenAI API).

Security Features:
- Path traversal protection
- Input validation
- Safe file extension whitelisting
- Graceful error handling
- Comprehensive logging

Usage:
    from fmem.memory_search import MemoryRetrieval

    memory = MemoryRetrieval()
    results = memory.search("query", top_k=5)
    for r in results:
        print(f"[{r['score']:.3f}] {r['filepath']}")
"""

__version__ = "2.0.0"

import faiss
import numpy as np
import sqlite3
import json
import os
import sys
import logging
import datetime
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from contextlib import contextmanager

# Configuration management with environment variable support
import configparser
from functools import lru_cache

# Try to import litellm and use nomic-embed-text model (served by local Ollama)
try:
    import litellm
    EMBEDDING_MODEL = "nomic-embed-text"
    EMBEDDING_DIM = 768
except ImportError:
    raise ImportError(
        "litellm not installed. Run: pip install --break-system-packages litellm"
    )


# ============================================================================
# Configuration Management
# ============================================================================

class ConfigManager:
    """Handles configuration from environment variables and config files."""
    
    DEFAULT_DATA_DIR = os.path.expanduser("~/.openclaw/memory")
    DEFAULT_OLLAMA_URL = "http://localhost:11434"
    DEFAULT_INDEX_NAME = "faiss_index.fai"
    DEFAULT_METADATA_NAME = "doc_metadata.json"
    DEFAULT_SQLITE_NAME = "documents.db"
    
    # Valid file extensions for indexing
    VALID_EXTENSIONS = {'.md', '.txt', '.py', '.json', '.yaml', '.yml', '.csv'}
    
    # Maximum file size (50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024
    
    # Maximum path length (4096 characters on most systems)
    MAX_PATH_LENGTH = 1024
    
    # Maximum query length
    MAX_QUERY_LENGTH = 1000
    
    # Maximum batch size
    MAX_BATCH_SIZE = 100
    
    # Memory quality enhancement settings
    DEFAULT_ENABLE_RECENCY_RANKING = True
    DEFAULT_RECENCY_WEIGHT = 0.3
    DEFAULT_RECENCY_THRESHOLD_DAYS = 30
    DEFAULT_MIN_RECENCY_SCORE = 0.1
    DEFAULT_ENABLE_LOCATION_RANKING = True
    DEFAULT_LOCATION_WEIGHT = 0.2
    
    def __init__(self):
        """Initialize configuration manager."""
        self.config = configparser.ConfigParser()
        self._load_config()
    
    def _load_config(self):
        """Load configuration from environment and config file."""
        # Environment variables take precedence
        self.data_dir = os.environ.get('FMEM_DATA_DIR', self.DEFAULT_DATA_DIR)
        self.ollama_url = os.environ.get('FMEM_OLLAMA_URL', self.DEFAULT_OLLAMA_URL)
        self.index_name = os.environ.get('FMEM_INDEX_NAME', self.DEFAULT_INDEX_NAME)
        self.metadata_name = os.environ.get('FMEM_METADATA_NAME', self.DEFAULT_METADATA_NAME)
        self.sqlite_name = os.environ.get('FMEM_SQLITE_NAME', self.DEFAULT_SQLITE_NAME)
        
        # Path to config file
        config_path = os.environ.get('FMEM_CONFIG', os.path.join(self.data_dir, 'fmem.conf'))
        
        if os.path.exists(config_path):
            self.config.read(config_path)
            if 'settings' in self.config:
                self.data_dir = self.config.get('settings', 'data_dir', fallback=self.data_dir)
                self.ollama_url = self.config.get('settings', 'ollama_url', fallback=self.ollama_url)
                # Memory quality enhancement settings
                self.enable_recency_ranking = self.config.getboolean('settings', 'enable_recency_ranking', fallback=self.DEFAULT_ENABLE_RECENCY_RANKING)
                self.recency_weight = self.config.getfloat('settings', 'recency_weight', fallback=self.DEFAULT_RECENCY_WEIGHT)
                self.recency_threshold_days = self.config.getint('settings', 'recency_threshold_days', fallback=self.DEFAULT_RECENCY_THRESHOLD_DAYS)
                self.min_recency_score = self.config.getfloat('settings', 'min_recency_score', fallback=self.DEFAULT_MIN_RECENCY_SCORE)
                # Location-based ranking settings
                self.enable_location_ranking = self.config.getboolean('settings', 'enable_location_ranking', fallback=self.DEFAULT_ENABLE_LOCATION_RANKING)
                self.location_weight = self.config.getfloat('settings', 'location_weight', fallback=self.DEFAULT_LOCATION_WEIGHT)
                # Location-based importance weights for directories
                self.location_weights = {
                    # High importance - formal documentation and decisions
                    'docs': self.config.getfloat('settings', 'docs_weight', fallback=1.5),
                    'documentation': self.config.getfloat('settings', 'documentation_weight', fallback=1.5),
                    'projects': self.config.getfloat('settings', 'projects_weight', fallback=1.3),
                    'decisions': self.config.getfloat('settings', 'decisions_weight', fallback=1.4),
                    'formal': self.config.getfloat('settings', 'formal_weight', fallback=1.4),
                    # Medium importance - active working files
                    'work': self.config.getfloat('settings', 'work_weight', fallback=1.2),
                    'active': self.config.getfloat('settings', 'active_weight', fallback=1.2),
                    'current': self.config.getfloat('settings', 'current_weight', fallback=1.1),
                    'notes': self.config.getfloat('settings', 'notes_weight', fallback=1.0),
                    'memory': self.config.getfloat('settings', 'memory_weight', fallback=1.0),
                    # Lower importance - casual/conversational content
                    'chats': self.config.getfloat('settings', 'chats_weight', fallback=0.8),
                    'conversations': self.config.getfloat('settings', 'conversations_weight', fallback=0.8),
                    'daily': self.config.getfloat('settings', 'daily_weight', fallback=0.9),
                    'sessions': self.config.getfloat('settings', 'sessions_weight', fallback=0.9),
                    # Base importance
                    'base': self.config.getfloat('settings', 'base_weight', fallback=1.0),
                }
        else:
            # Use defaults if config file doesn't exist
            self.enable_recency_ranking = self.DEFAULT_ENABLE_RECENCY_RANKING
            self.recency_weight = self.DEFAULT_RECENCY_WEIGHT
            self.recency_threshold_days = self.DEFAULT_RECENCY_THRESHOLD_DAYS
            self.min_recency_score = self.DEFAULT_MIN_RECENCY_SCORE
            self.enable_location_ranking = self.DEFAULT_ENABLE_LOCATION_RANKING
            self.location_weight = self.DEFAULT_LOCATION_WEIGHT
            # Location-based importance weights for directories (defaults)
            self.location_weights = {
                # High importance - formal documentation and decisions
                'docs': 1.5,
                'documentation': 1.5,
                'projects': 1.3,
                'decisions': 1.4,
                'formal': 1.4,
                # Medium importance - active working files
                'work': 1.2,
                'active': 1.2,
                'current': 1.1,
                'notes': 1.0,
                'memory': 1.0,
                # Lower importance - casual/conversational content
                'chats': 0.8,
                'conversations': 0.8,
                'daily': 0.9,
                'sessions': 0.9,
                # Base importance
                'base': 1.0,
            }
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
    
    @property
    def index_path(self) -> str:
        """Get full path to FAISS index file."""
        return os.path.join(self.data_dir, self.index_name)
    
    @property
    def metadata_path(self) -> str:
        """Get full path to metadata file."""
        return os.path.join(self.data_dir, self.metadata_name)
    
    @property
    def sqlite_path(self) -> str:
        """Get full path to SQLite database."""
        return os.path.join(self.data_dir, self.sqlite_name)
    
    def is_valid_extension(self, filepath: str) -> bool:
        """Check if file extension is in whitelist."""
        ext = Path(filepath).suffix.lower()
        return ext in self.VALID_EXTENSIONS
    
    def is_safe_path(self, filepath: str, base_dir: Optional[str] = None) -> bool:
        """Validate path to prevent path traversal attacks."""
        if not filepath:
            return False
        
        # Check path length
        if len(filepath) > self.MAX_PATH_LENGTH:
            return False
        
        # Normalize path
        try:
            resolved = Path(filepath).resolve()
        except (OSError, ValueError):
            return False
        
        # For absolute paths, require explicit base_dir
        # For relative paths, resolve relative to current dir is OK
        if Path(filepath).is_absolute():
            if base_dir is None:
                # Absolute paths need a base to validate against
                return False
            base_dir = Path(base_dir).resolve()
        else:
            # Relative paths are OK - resolve to current dir
            base_dir = Path.cwd()
        
        # Check if resolved path is within base directory
        try:
            resolved.relative_to(base_dir)
            return True
        except ValueError:
            return False
    
    def validate_query(self, query: str) -> Tuple[bool, str]:
        """Validate search query."""
        if not query or not isinstance(query, str):
            return False, "Query must be a non-empty string"
        
        if len(query) > self.MAX_QUERY_LENGTH:
            return False, f"Query too long (max {self.MAX_QUERY_LENGTH} chars)"
        
        if len(query.strip()) == 0:
            return False, "Query cannot be whitespace only"
        
        return True, ""
    
    def validate_file_size(self, filepath: str) -> Tuple[bool, str]:
        """Validate file size."""
        try:
            size = os.path.getsize(filepath)
            if size > self.MAX_FILE_SIZE:
                return False, f"File too large (max {self.MAX_FILE_SIZE} bytes)"
            if size == 0:
                return False, "File is empty"
            return True, ""
        except OSError as e:
            return False, f"Cannot access file: {e}"


# Global configuration instance
CONFIG = ConfigManager()


# ============================================================================
# Logging Setup
# ============================================================================

def setup_logging(name: str = "fmem", level: int = None) -> logging.Logger:
    """Set up logging with specified level."""
    if level is None:
        level = logging.INFO
        if os.environ.get('FMEM_DEBUG', '').lower() in ('1', 'true', 'yes'):
            level = logging.DEBUG
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


logger = setup_logging()


# ============================================================================
# Security Utilities
# ============================================================================

def sanitize_path(filepath: str, base_dir: Optional[str] = None, config: ConfigManager = None) -> Optional[str]:
    """
    Sanitize and validate a file path to prevent path traversal attacks.
    
    Args:
        filepath: The file path to sanitize
        base_dir: Optional base directory to restrict paths to
        config: ConfigManager instance (uses global CONFIG if None)
        
    Returns:
        Sanitized absolute path or None if invalid
    """
    if config is None:
        config = CONFIG
    
    if not filepath or not isinstance(filepath, str):
        logger.warning("Invalid filepath: not a string")
        return None
    
    # Remove null bytes and control characters
    filepath = filepath.replace('\x00', '').strip()
    
    # Check path length
    if len(filepath) > config.MAX_PATH_LENGTH:
        logger.warning(f"Path too long: {len(filepath)} chars")
        return None
    
    try:
        # Normalize the path
        normalized = Path(filepath).resolve()
        
        # Get base directory
        if base_dir is None:
            # For absolute paths, use the parent of data_dir as base
            if Path(filepath).is_absolute():
                base_dir = Path(config.data_dir).parent
            else:
                # For relative paths, use current working directory
                base_dir = Path.cwd()
        else:
            base_dir = Path(base_dir).resolve()
        
        # Check if path is within allowed directory
        try:
            normalized.relative_to(base_dir)
        except ValueError:
            logger.warning(f"Path traversal attempt detected: {filepath}")
            return None
        
        # Check if file extension is valid
        if not config.is_valid_extension(str(normalized)):
            logger.warning(f"Invalid file extension: {filepath}")
            return None
        
        return str(normalized)
        
    except (OSError, ValueError) as e:
        logger.warning(f"Invalid path '{filepath}': {e}")
        return None


# ============================================================================
# Ollama Connection with Retry Logic
# ============================================================================

class OllamaClient:
    """Ollama client with connection pooling and retry logic."""
    
    def __init__(self, url: str = None, max_retries: int = 3, timeout: int = 30):
        """
        Initialize Ollama client.
        
        Args:
            url: Ollama base URL
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
        """
        self.url = url or CONFIG.ollama_url
        self.max_retries = max_retries
        self.timeout = timeout
        self._connection_pool = None
        
        logger.debug(f"OllamaClient initialized with URL: {self.url}")
    
    @contextmanager
    def _get_connection(self):
        """Get connection from pool with automatic retry."""
        for attempt in range(self.max_retries):
            try:
                yield
                return
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
    
    def health_check(self) -> bool:
        """Check if Ollama service is available."""
        try:
            response = litellm.embedding(
                model="ollama/nomic-embed-text",
                input=["health check"],
                api_base=self.url,
                timeout=self.timeout
            )
            return response is not None
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False
    
    def generate_embeddings(self, texts: List[str]) -> Optional[np.ndarray]:
        """
        Generate embeddings with retry logic.
        
        Args:
            texts: List of strings to embed
            
        Returns:
            Embeddings array (N x 768) or None if failed
        """
        if not texts:
            logger.warning("Empty text list provided for embedding")
            return None
        
        for attempt in range(self.max_retries):
            try:
                with self._get_connection():
                    response = litellm.embedding(
                        model="ollama/nomic-embed-text",
                        input=texts,
                        api_base=self.url,
                        timeout=self.timeout
                    )
                    
                    # Extract embeddings from response
                    if hasattr(response, 'data'):
                        embeddings_list = [item['embedding'] for item in response.data]
                    elif isinstance(response, list):
                        embeddings_list = response
                    else:
                        raise ValueError(f"Unexpected response type: {type(response)}")
                    
                    if not embeddings_list:
                        logger.error("Empty embeddings list received")
                        return None
                    
                    # Convert to numpy array
                    return np.array(embeddings_list).astype('float32')
                    
            except Exception as e:
                logger.warning(f"Embedding generation attempt {attempt + 1}/{self.max_retries} failed: {e}")
                if attempt < self.max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        logger.error("All embedding generation attempts failed")
        return None
    
    def get_model_list(self) -> List[str]:
        """Get list of available models from Ollama."""
        try:
            response = litellm.models(api_base=self.url, timeout=self.timeout)
            if isinstance(response, list):
                return [m['id'] for m in response]
            elif hasattr(response, 'data'):
                return [m['id'] for m in response.data]
            return []
        except Exception as e:
            logger.error(f"Failed to get model list: {e}")
            return []


# ============================================================================
# Memory Retrieval System
# ============================================================================

class MemoryRetrieval:
    """
    FAISS-based semantic memory search system.
    
    Features:
    - Zero external dependencies (no OpenAI/Pinecone)
    - In-memory or persistent storage
    - Low memory footprint (~8KB index)
    - Scalable to thousands of documents
    - Path traversal protection
    - Input validation
    - Comprehensive error handling
    """
    
    def __init__(self, db_path: str = None, config: ConfigManager = None, ollama_client: OllamaClient = None):
        """
        Initialize memory search system.
        
        Args:
            db_path: Optional SQLite path for persistent metadata.
                    If None, uses default from config.
            config: ConfigManager instance
            ollama_client: OllamaClient instance
        """
        self.config = config or CONFIG
        self.ollama = ollama_client or OllamaClient()
        self.dimension = EMBEDDING_DIM
        self.index = None
        self.doc_metadata = []  # List of {filepath, content, last_modified}
        self.db_path = db_path or self.config.sqlite_path
        self.conn = None
        self.embedding_cache = {}  # Cache embeddings for performance
        
        logger.info("Initializing MemoryRetrieval...")
        
        # Ensure data directory exists
        os.makedirs(self.config.data_dir, exist_ok=True)
        
        # Try to load existing index
        self._load_index()
        
        # Initialize SQLite connection
        self._init_database()
        
        logger.info(f"MemoryRetrieval initialized with {len(self.doc_metadata)} documents loaded")
    
    def _init_database(self):
        """Initialize SQLite database connection."""
        try:
            self.conn = sqlite3.connect(self.db_path, timeout=30.0)
            self.conn.row_factory = sqlite3.Row
            self._create_db_tables()
            logger.debug(f"Database initialized: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            self.conn = None
    
    def _create_db_tables(self):
        """Create document metadata table if not exists."""
        if not self.conn:
            return
        
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filepath TEXT UNIQUE,
                content TEXT,
                last_modified INTEGER,
                created_at INTEGER,
                file_hash TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                doc_id INTEGER,
                embedding BLOB,
                PRIMARY KEY (doc_id),
                FOREIGN KEY (doc_id) REFERENCES documents(id)
            )
        """)
        self.conn.commit()
    
    def _load_index(self):
        """Load FAISS index and document metadata from disk."""
        try:
            if os.path.exists(self.config.index_path):
                self.index = faiss.read_index(self.config.index_path)
                logger.info(f"✓ Loaded FAISS index from {self.config.index_path}")
            
            # Load metadata
            if os.path.exists(self.config.metadata_path):
                with open(self.config.metadata_path, 'r') as f:
                    self.doc_metadata = json.load(f)
                logger.info(f"✓ Loaded {len(self.doc_metadata)} documents from metadata")
                
                # Also load from database
                self._load_from_database()
        except Exception as e:
            logger.warning(f"Failed to load cached index: {e}")
            # Initialize new index
            self.index = faiss.IndexFlatIP(self.dimension)
    
    def _load_from_database(self):
        """Load document metadata from SQLite database."""
        if not self.conn:
            return
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT filepath, content, last_modified, created_at FROM documents")
            
            db_docs = []
            for row in cursor.fetchall():
                db_docs.append({
                    'filepath': row['filepath'],
                    'content': row['content'],
                    'last_modified': row['last_modified'],
                    'created_at': row['created_at']
                })
            
            # Merge with existing metadata
            existing_paths = {d['filepath'] for d in self.doc_metadata}
            for doc in db_docs:
                if doc['filepath'] not in existing_paths:
                    self.doc_metadata.append(doc)
            
            logger.debug(f"Loaded {len(db_docs)} documents from database")
        except Exception as e:
            logger.error(f"Failed to load from database: {e}")
    
    def _calculate_recency_score(self, last_modified: float) -> float:
        """
        Calculate recency score for a document based on its modification time.
        
        Args:
            last_modified: Unix timestamp of last modification
            
        Returns:
            Recency score between 0.0 and 1.0
        """
        if not self.config.enable_recency_ranking:
            return 1.0  # No recency adjustment
        
        import time
        current_time = time.time()
        age_days = (current_time - last_modified) / (24 * 60 * 60)
        
        # If within threshold, calculate score based on age
        if age_days <= self.config.recency_threshold_days:
            # Exponential decay: newer documents get higher scores
            recency_score = 1.0 - (age_days / self.config.recency_threshold_days)
            return max(recency_score, self.config.min_recency_score)
        else:
            # Beyond threshold, apply minimum recency score
            return self.config.min_recency_score
    
    def _enhance_search_results_with_recency(self, results: List[Dict]) -> List[Dict]:
        """
        Apply recency-based ranking enhancement to search results.
        
        Args:
            results: Original search results from FAISS
            
        Returns:
            Enhanced results with recency-adjusted scores
        """
        if not self.config.enable_recency_ranking or not results:
            return results
        
        enhanced_results = []
        
        for result in results:
            # Get the document metadata
            filepath = result['filepath']
            doc_metadata = None
            
            for doc in self.doc_metadata:
                if doc['filepath'] == filepath:
                    doc_metadata = doc
                    break
            
            if doc_metadata:
                # Calculate recency score
                recency_score = self._calculate_recency_score(doc_metadata['last_modified'])
                
                # Apply hybrid scoring: semantic_score * (1 - recency_weight) + recency_score * recency_weight
                semantic_score = result['score']
                enhanced_score = (semantic_score * (1 - self.config.recency_weight) + 
                                recency_score * self.config.recency_weight)
                
                # Create enhanced result
                enhanced_result = result.copy()
                enhanced_result['score'] = enhanced_score
                enhanced_result['semantic_score'] = semantic_score
                enhanced_result['recency_score'] = recency_score
                enhanced_result['enhanced'] = True
                
                enhanced_results.append(enhanced_result)
            else:
                # No metadata found, use original result
                enhanced_results.append(result)
        
        # Sort by enhanced score
        enhanced_results.sort(key=lambda x: x['score'], reverse=True)
        
        return enhanced_results
    
    def _calculate_location_weight(self, filepath: str) -> float:
        """
        Calculate location-based importance weight for a file.
        
        Args:
            filepath: Full path to the file
            
        Returns:
            Location weight (1.0 = base, >1.0 = more important, <1.0 = less important)
        """
        if not self.config.enable_location_ranking:
            return 1.0  # No location adjustment
        
        import os
        
        # Normalize the path to lowercase for case-insensitive matching
        normalized_path = os.path.normpath(filepath).lower()
        path_parts = normalized_path.split(os.sep)
        
        # Check each directory in path for known patterns (case-insensitive)
        for part in path_parts:
            if part in self.config.location_weights:
                return self.config.location_weights[part]
        
        # Default weight (base)
        return self.config.location_weights.get('base', 1.0)
    
    def _enhance_search_results_with_location(self, results: List[Dict]) -> List[Dict]:
        """
        Apply location-based ranking enhancement to search results.
        
        Args:
            results: Original search results from FAISS
            
        Returns:
            Enhanced results with location-adjusted scores
        """
        if not self.config.enable_location_ranking or not results:
            return results
        
        # Validate weight sums don't exceed 1.0
        total_weight = self.config.recency_weight + self.config.location_weight
        if total_weight > 1.0:
            logger.warning(f"Recency + location weights ({total_weight}) exceed 1.0. Normalizing.")
            scale = 1.0 / total_weight
            recency_w = self.config.recency_weight * scale
            location_w = self.config.location_weight * scale
        else:
            recency_w = self.config.recency_weight
            location_w = self.config.location_weight
        
        remaining_weight = 1.0 - recency_w - location_w
        
        # Get min/max for location weight normalization
        loc_weights = self.config.location_weights.values()
        loc_min = min(loc_weights)
        loc_max = max(loc_weights)
        loc_range = loc_max - loc_min if loc_max > loc_min else 1.0
        
        enhanced_results = []
        
        for result in results:
            filepath = result['filepath']
            
            # Get location weight and normalize to 0.0-1.0 range
            location_weight = self._calculate_location_weight(filepath)
            normalized_location = (location_weight - loc_min) / loc_range
            
            # Get existing scores
            semantic_score = result.get('semantic_score', result['score'])
            recency_score = result.get('recency_score', 1.0)
            
            # Apply enhanced scoring with normalized location
            enhanced_score = (
                semantic_score * remaining_weight +
                recency_score * recency_w +
                normalized_location * location_w
            )
            
            # Create enhanced result
            enhanced_result = result.copy()
            enhanced_result['score'] = enhanced_score
            enhanced_result['semantic_score'] = semantic_score
            enhanced_result['recency_score'] = recency_score
            enhanced_result['location_weight'] = location_weight
            enhanced_result['location_normalized'] = normalized_location
            enhanced_result['location_score'] = normalized_location
            enhanced_result['enhanced'] = True
            
            enhanced_results.append(enhanced_result)
        
        # Sort by enhanced score
        enhanced_results.sort(key=lambda x: x['score'], reverse=True)
        
        return enhanced_results
    
    def _get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get embedding from cache or generate new one."""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        if text_hash in self.embedding_cache:
            return self.embedding_cache[text_hash]
        
        embedding = self.ollama.generate_embeddings([text])
        if embedding is not None:
            self.embedding_cache[text_hash] = embedding[0]
        
        return embedding[0] if embedding is not None else None
    
    def _store_embedding(self, metadata: Dict, content: str) -> Optional[int]:
        """Store embedding in SQLite for faster retrieval."""
        if not self.conn:
            return None
        
        try:
            cursor = self.conn.cursor()
            
            # Check if already exists
            cursor.execute("SELECT id FROM documents WHERE filepath = ?", (metadata['filepath'],))
            doc_id = cursor.fetchone()
            
            if doc_id:
                doc_id = doc_id[0]
                # Update content and timestamp
                cursor.execute("""
                    UPDATE documents SET content = ?, last_modified = ?, file_hash = ?
                    WHERE filepath = ?
                """, (
                    content,
                    metadata['last_modified'],
                    hashlib.md5(content.encode()).hexdigest(),
                    metadata['filepath']
                ))
            else:
                # Insert new document
                cursor.execute("""
                    INSERT INTO documents (filepath, content, last_modified, created_at, file_hash)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    metadata['filepath'],
                    content,
                    metadata['last_modified'],
                    metadata['created_at'],
                    hashlib.md5(content.encode()).hexdigest()
                ))
                doc_id = cursor.lastrowid
            
            self.conn.commit()
            logger.debug(f"✓ Stored {metadata['filepath']} in database (id={doc_id})")
            return doc_id
            
        except Exception as e:
            logger.error(f"Failed to store in database: {e}")
            return None
    
    def _generate_embeddings_batch(self, texts: List[str]) -> Optional[np.ndarray]:
        """
        Generate embeddings for multiple texts with batching.
        
        Args:
            texts: List of strings to embed
            
        Returns:
            Embeddings array (N x 768) or None if failed
        """
        if not texts:
            return None
        
        # Split into batches if needed
        all_embeddings = []
        batch_size = min(len(texts), self.config.MAX_BATCH_SIZE)
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = self.ollama.generate_embeddings(batch)
            
            if embeddings is not None:
                all_embeddings.append(embeddings)
            else:
                logger.warning(f"Failed to generate embeddings for batch {i//batch_size + 1}")
        
        if all_embeddings:
            return np.vstack(all_embeddings)
        return None
    
    def add_document(self, filepath: str, content: Optional[str] = None) -> bool:
        """
        Add a document to memory system with validation.
        
        Args:
            filepath: Path to file (for metadata)
            content: Full document content. If None, reads from file.
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Sanitize path with instance config
            safe_path = sanitize_path(filepath, config=self.config)
            if safe_path is None:
                logger.error(f"Invalid filepath: {filepath}")
                return False
            
            filepath = safe_path
            
            # Check file extension
            if not self.config.is_valid_extension(filepath):
                logger.error(f"Invalid file extension: {filepath}")
                return False
            
            # Load content if not provided
            if content is None:
                # Check if file exists
                if not os.path.exists(filepath):
                    logger.error(f"File not found: {filepath}")
                    return False
                
                # Check file size
                valid, msg = self.config.validate_file_size(filepath)
                if not valid:
                    logger.error(msg)
                    return False
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    # Try with different encoding
                    try:
                        with open(filepath, 'r', encoding='latin-1') as f:
                            content = f.read()
                    except Exception as e:
                        logger.error(f"Failed to read {filepath}: {e}")
                        return False
                except Exception as e:
                    logger.error(f"Failed to read {filepath}: {e}")
                    return False
            
            # Validate content length
            if not content or len(content.strip()) == 0:
                logger.error("Empty content")
                return False
            
            if len(content) > self.config.MAX_FILE_SIZE:
                logger.error("Content too large")
                return False
            
            # Generate embedding
            embedding = self._get_embedding(content[:1000])  # Use first 1000 chars for quick embedding
            
            # Store metadata
            metadata = {
                'filepath': filepath,
                'content': content,
                'last_modified': int(datetime.datetime.now().timestamp()),
                'created_at': int(datetime.datetime.now().timestamp())
            }
            
            # Check if document already exists
            existing_idx = None
            for i, doc in enumerate(self.doc_metadata):
                if doc['filepath'] == filepath:
                    existing_idx = i
                    break
            
            if existing_idx is not None:
                # Update existing document
                self.doc_metadata[existing_idx] = metadata
                logger.info(f"✓ Updated document: {filepath}")
            else:
                # Add new document
                self.doc_metadata.append(metadata)
                
                # Add to FAISS index
                if embedding is not None:
                    if self.index is None:
                        self.index = faiss.IndexFlatIP(self.dimension)
                    self.index.add(np.array([embedding]))
                
                logger.info(f"✓ Added document: {filepath}")
            
            # Store in database
            self._store_embedding(metadata, content)
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding document {filepath}: {e}")
            return False
    
    def add_documents_batch(self, files: List[str], use_progress: bool = False) -> Dict[str, bool]:
        """
        Add multiple documents in batch with progress indication.
        
        Args:
            files: List of file paths to add
            use_progress: Whether to show progress
            
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
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Search memory for relevant documents with validation.
        
        Args:
            query: Search query string
            top_k: Number of relevant documents to return
            
        Returns:
            List of {filepath, content, score} dicts
        """
        # Validate query
        valid, msg = self.config.validate_query(query)
        if not valid:
            logger.warning(f"Invalid query: {msg}")
            return []
        
        # Limit top_k
        top_k = min(top_k, self.config.MAX_BATCH_SIZE, len(self.doc_metadata))
        
        # Initialize index if needed
        if self.index is None:
            if len(self.doc_metadata) == 0:
                return []
            self.index = faiss.IndexFlatIP(self.dimension)
        
        # Check if we have documents
        if len(self.doc_metadata) == 0:
            return []
        
        # Generate embedding for query
        query_embedding = self._get_embedding(query)
        if query_embedding is None:
            logger.error("Failed to generate query embedding")
            return []
        
        # Search FAISS index
        D, I = self.index.search(np.array([query_embedding]), top_k)
        
        # Build results
        results = []
        for idx in range(len(I[0])):
            doc_idx = I[0][idx]
            if doc_idx >= len(self.doc_metadata):
                continue
            
            results.append({
                'filepath': self.doc_metadata[doc_idx]['filepath'],
                'content': self.doc_metadata[doc_idx].get('content', ''),
                'score': float(D[0][idx])
            })
        
        # Apply recency-based ranking enhancement if enabled
        if self.config.enable_recency_ranking:
            results = self._enhance_search_results_with_recency(results)
            logger.debug(f"Applied recency enhancement: {len(results)} results enhanced")
        
        # Apply location-based ranking enhancement if enabled
        if self.config.enable_location_ranking:
            results = self._enhance_search_results_with_location(results)
            logger.debug(f"Applied location enhancement: {len(results)} results enhanced")
        
        logger.debug(f"Search returned {len(results)} results for query: '{query[:50]}...'")
        return results
    
    def persist(self) -> bool:
        """Save index and metadata to disk for persistence."""
        success = True
        
        # Save FAISS index
        if self.index:
            try:
                faiss.write_index(self.index, self.config.index_path)
                logger.info(f"✓ FAISS index persisted to {self.config.index_path}")
            except Exception as e:
                logger.error(f"Failed to persist index: {e}")
                success = False
        
        # Persist metadata
        if self.doc_metadata:
            try:
                with open(self.config.metadata_path, 'w') as f:
                    json.dump(self.doc_metadata, f, indent=2)
                logger.info(f"✓ Metadata persisted to {self.config.metadata_path}")
            except Exception as e:
                logger.error(f"Failed to persist metadata: {e}")
                success = False
        
        # Close database connection
        if self.conn:
            try:
                self.conn.close()
                self.conn = None
                logger.debug("Database connection closed")
            except Exception as e:
                logger.error(f"Failed to close database: {e}")
                success = False
        
        return success
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.persist()
        except Exception:
            pass  # Suppress cleanup errors
    
    def reset(self) -> bool:
        """Clear all data and reset to initial state."""
        try:
            if self.index:
                self.index.reset()
            
            self.doc_metadata = []
            self.embedding_cache = {}
            
            # Remove persisted files
            for path in [self.config.index_path, self.config.metadata_path]:
                if os.path.exists(path):
                    os.remove(path)
                    logger.info(f"Removed: {path}")
            
            # Clear database
            if self.conn:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM documents")
                cursor.execute("DELETE FROM embeddings")
                self.conn.commit()
            
            logger.info("✓ Memory cleared")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset memory: {e}")
            return False
    
    def get_status(self) -> Dict:
        """Get current memory system status."""
        return {
            'version': __version__,
            'documents_count': len(self.doc_metadata),
            'index_ready': self.index is not None,
            'database_ready': self.conn is not None,
            'data_dir': self.config.data_dir,
            'ollama_url': self.config.ollama_url,
            'embedding_cache_size': len(self.embedding_cache)
        }
    
    def health_check(self) -> bool:
        """Check if memory system is healthy."""
        try:
            # Check Ollama connectivity
            if not self.ollama.health_check():
                logger.warning("Ollama health check failed")
                return False
            
            # Check index
            if self.index is None and len(self.doc_metadata) > 0:
                logger.warning("Index not loaded")
                return False
            
            # Check database
            if self.conn is None:
                logger.warning("Database not connected")
                return False
            
            logger.info("✓ Memory system healthy")
            return True
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def get_document_count(self) -> int:
        """Get total number of indexed documents."""
        return len(self.doc_metadata)
    
    def get_document_paths(self) -> List[str]:
        """Get list of all indexed document paths."""
        return [doc['filepath'] for doc in self.doc_metadata]


# ============================================================================
# CLI Interface
# ============================================================================

def cli():
    """Command-line interface for fmem skill."""
    import argparse
    import time
    
    parser = argparse.ArgumentParser(
        "fmem — FAISS Memory Search (v" + __version__ + ")",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  fmem search "your query here"           # Search memory
  fmem search "query" -k 10               # Return top 10 results
  fmem add /path/to/document.md           # Add document
  fmem add --batch batch_files.txt        # Add multiple files
  fmem reset                              # Clear memory
  fmem status                             # Show system status
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Search command
    parser_search = subparsers.add_parser('search', help='Search memory')
    parser_search.add_argument('query', help='Search query')
    parser_search.add_argument('-k', '--top-k', type=int, default=5, help='Number of results (default: 5)')
    parser_search.add_argument('--quiet', action='store_true', help='Suppress non-result output')
    
    # Add command
    parser_add = subparsers.add_parser('add', help='Add document to memory')
    parser_add.add_argument('filepath', nargs='?', help='Path to file to add')
    parser_add.add_argument('--batch', '-b', help='File containing paths to add (one per line)')
    parser_add.add_argument('--quiet', action='store_true', help='Suppress non-result output')
    parser_add.add_argument('--recursive', '-r', action='store_true', help='Recursively add files from directory')
    parser_add.add_argument('--skip-existing', action='store_true', help='Skip already indexed files')
    
    # Reset command
    subparsers.add_parser('reset', help='Clear memory')
    
    # Status command
    subparsers.add_parser('status', help='Show system status')
    
    # Health check command
    subparsers.add_parser('health', help='Check system health')
    
    # Version command
    subparsers.add_parser('version', help='Show version info')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        memory = MemoryRetrieval()
        
        if args.command == 'search':
            if not args.quiet:
                print(f"\nSearching: '{args.query}' (top-{args.top_k})\n")
            
            start_time = time.time()
            results = memory.search(args.query, top_k=args.top_k)
            elapsed = time.time() - start_time
            
            if not args.quiet:
                print(f"Found {len(results)} results in {elapsed:.3f}s\n")
            
            for i, r in enumerate(results, 1):
                print(f"[{i}] Score: {r['score']:.3f}")
                print(f"    File: {r['filepath']}")
                
                # Preview content (first 200 chars)
                content = r['content']
                preview = content[:200] + "..." if len(content) > 200 else content
                print(f"    Preview: {preview}")
                print()
            
            if not args.quiet:
                print(f"Search completed in {elapsed:.3f}s")
        
        elif args.command == 'add':
            files_to_add = []
            
            if args.batch:
                # Read batch file
                try:
                    with open(args.batch, 'r') as f:
                        files_to_add = [line.strip() for line in f if line.strip()]
                except Exception as e:
                    print(f"Error reading batch file: {e}")
                    return
            
            elif args.filepath:
                # Single file or directory
                if os.path.isdir(args.filepath) and args.recursive:
                    import glob
                    for ext in CONFIG.VALID_EXTENSIONS:
                        files_to_add.extend(glob.glob(f"{args.filepath}/**/*{ext}", recursive=True))
                else:
                    files_to_add = [args.filepath]
            
            if not files_to_add:
                print("No files specified. Use filepath or --batch.")
                return
            
            # Filter existing files if --skip-existing
            if args.skip_existing:
                existing_paths = set(memory.get_document_paths())
                files_to_add = [f for f in files_to_add if f not in existing_paths]
            
            if not args.quiet:
                print(f"\nAdding {len(files_to_add)} documents...\n")
            
            start_time = time.time()
            results = memory.add_documents_batch(files_to_add, use_progress=not args.quiet)
            elapsed = time.time() - start_time
            
            if not args.quiet:
                print(f"\n{'='*50}")
                print(f"Completed in {elapsed:.3f}s")
                print(f"Success: {sum(results.values())}/{len(results)}")
                
                failures = [f for f, s in results.items() if not s]
                if failures:
                    print(f"\nFailed to add {len(failures)} files:")
                    for f in failures:
                        print(f"  - {f}")
            
            memory.persist()
        
        elif args.command == 'reset':
            quiet = getattr(args, 'quiet', False)
            if not quiet:
                print("\nResetting memory...")
            memory.reset()
            if not quiet:
                print("✓ Done\n")
        
        elif args.command == 'status':
            status = memory.get_status()
            print("\nMemory System Status")
            print("="*50)
            print(f"Version: {status['version']}")
            print(f"Documents: {status['documents_count']}")
            print(f"Index: {'Ready' if status['index_ready'] else 'Not ready'}")
            print(f"Database: {'Connected' if status['database_ready'] else 'Not connected'}")
            print(f"Data Directory: {status['data_dir']}")
            print(f"Ollama URL: {status['ollama_url']}")
            print(f"Embedding Cache: {status['embedding_cache_size']} entries")
            print()
        
        elif args.command == 'health':
            if memory.health_check():
                print("✓ Memory system is healthy")
            else:
                print("✗ Memory system has issues")
                sys.exit(1)
        
        elif args.command == 'version':
            print(f"fmem version {__version__}")
        
        else:
            parser.print_help()
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    cli()
