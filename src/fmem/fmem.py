#!/usr/bin/env python3
"""
FAISS-based Memory Search System - Production Hardened

Provides offline-first semantic search for agent memory using FAISS embeddings.
Zero external dependencies — works via FastEmbed (local embeddings, no HTTP).

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

__version__ = "3.1.0"

# Standard library imports
import json
import logging
import os
import sys
import re
import time
import hashlib
import datetime
from datetime import timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from contextlib import contextmanager
from collections import OrderedDict

# Configuration management with environment variable support
import configparser
from functools import lru_cache

# ============================================================================
# Chunk Metadata Schema
# ============================================================================

class ChunkMetadata:
    """Represents a chunk with metadata for enhanced retrieval."""
    
    def __init__(self, id: str, parent_file: str, heading: str, 
                 content: str, summary: str = None, keywords: List[str] = None,
                 category: str = None, tokens: int = 0, chunk_index: int = 0,
                 original_length: int = 0, processed_content: str = None):
        """
        Initialize chunk metadata.
        
        Args:
            id: Unique chunk identifier (e.g., "MEMORY.md#session-2026-02-13")
            parent_file: Path to original file
            heading: The ## heading text that defines this chunk
            content: Section content (original)
            summary: Chunk summary (generated in Phase 2)
            keywords: Extracted keywords from content
            category: Inferred category from heading
            tokens: Approximate token count
            chunk_index: Position index within parent file
            original_length: Length of original content before preprocessing
            processed_content: The preprocessed content that was actually embedded
        """
        self.id = id
        self.parent_file = parent_file
        self.heading = heading
        self.content = content
        self.summary = summary
        self.keywords = keywords or []
        self.category = category
        self.tokens = tokens
        self.chunk_index = chunk_index
        self.original_length = original_length
        self.processed_content = processed_content
    
    def to_dict(self) -> Dict:
        """Return dict representation."""
        return {
            'id': self.id,
            'parent_file': self.parent_file,
            'heading': self.heading,
            'content': self.content,
            'summary': self.summary,
            'keywords': self.keywords,
            'category': self.category,
            'tokens': self.tokens,
            'chunk_index': self.chunk_index,
            'original_length': self.original_length,
            'processed_content': self.processed_content
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ChunkMetadata':
        """Create ChunkMetadata from dict."""
        return cls(
            id=data.get('id', ''),
            parent_file=data.get('parent_file', ''),
            heading=data.get('heading', ''),
            content=data.get('content', ''),
            summary=data.get('summary'),
            keywords=data.get('keywords', []),
            category=data.get('category'),
            tokens=data.get('tokens', 0),
            chunk_index=data.get('chunk_index', 0),
            original_length=data.get('original_length', 0),
            processed_content=data.get('processed_content')
        )


# ============================================================================
# Embedding Model Token Limits for Chunk Sizing
# ============================================================================

def get_optimal_chunk_size() -> int:
    """
    Return optimal chunk size based on embedding model token limits.
    
    Uses FastEmbed with all-MiniLM-L6-v2 which has:
    - context length: 512 tokens (~200-800 chars depending on text)
    - embedding length: 384 dimensions
    
    Conservative limit: 800 characters to fit safely within 512 tokens.
    Hardware RAM doesn't matter - the embedding model is the bottleneck.
    
    The _get_embedding() call preprocesses content to ~500 chars anyway,
    so chunks larger than 800 are redundant for semantic search.
    
    Returns:
        Optimal chunk size in characters (800)
    """
    # Fixed at 800 chars - based on all-MiniLM-L6-v2's 512 token context limit
    # Not adaptive by design - the embedding model constrains us, not RAM
    return 800


def chunk_content_adaptively(content: str, max_chunk_size: int = None,
                              overlap_chars: int = 100) -> List[str]:
    """
    Split large content into chunks based on embedding model token limits.

    Default chunk size is 800 chars (fits in all-MiniLM-L6-v2's 512 token limit).
    Uses smart boundary detection to split at semantic breaks:
    1. Section boundaries (## headings)
    2. Paragraph boundaries (blank lines)
    3. Sentence boundaries (periods)
    4. Word boundaries (spaces)

    Includes overlap between chunks to preserve semantic continuity.

    Args:
        content: Content to chunk
        max_chunk_size: Maximum chunk size. If None, uses 800 chars (embedding limit)
        overlap_chars: Number of characters to overlap between chunks for continuity

    Returns:
        List of chunked content strings
    """
    if not content:
        return []
    
    # Get optimal chunk size if not specified
    if max_chunk_size is None:
        max_chunk_size = get_optimal_chunk_size()
    
    # If content fits in a single chunk, return as-is
    if len(content) <= max_chunk_size:
        return [content.strip()] if content.strip() else []
    
    chunks = []
    start_pos = 0
    content_len = len(content)
    
    while start_pos < content_len:
        # Calculate end position
        end_pos = min(start_pos + max_chunk_size, content_len)
        
        if end_pos >= content_len:
            # No need to find boundary at end of content
            chunk = content[start_pos:].strip()
            if chunk:
                chunks.append(chunk)
            break
        
        # Try to find a good splitting point (in priority order)
        split_pos = None
        search_end = end_pos
        
        # 1. Look for ## heading boundary (best)
        heading_match = re.search(r'(?=\n#{2}\s)', content[start_pos:search_end])
        if heading_match:
            # Found a heading start - split before it
            potential_split = start_pos + heading_match.start()
            if potential_split > start_pos + 100:  # Ensure chunk isn't too small
                split_pos = potential_split
        
        # 2. Look for paragraph boundary (blank line)
        if split_pos is None:
            para_match = re.search(r'\n\s*\n', content[start_pos:search_end])
            if para_match:
                split_pos = start_pos + para_match.end()
        
        # 3. Look for sentence boundary
        if split_pos is None:
            # Find last period followed by space or newline before end
            search_area = content[start_pos:search_end]
            sent_matches = list(re.finditer(r'[.!?]\s+', search_area))
            if sent_matches:
                split_pos = start_pos + sent_matches[-1].end()
        
        # 4. Look for word boundary
        if split_pos is None:
            word_match = re.search(r'\s+', content[end_pos - 100:end_pos])
            if word_match:
                split_pos = (end_pos - 100) + word_match.start()
        
        # If no good boundary found, just split at max_chunk_size
        if split_pos is None or split_pos <= start_pos:
            split_pos = end_pos
        
        # Extract chunk
        chunk = content[start_pos:split_pos].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start position forward for next chunk
        start_pos = split_pos
    
    return chunks


# ============================================================================
# Chunking Functions
# ============================================================================

def slugify(text: str) -> str:
    """
    Convert text to URL-friendly slug.
    
    Args:
        text: Input text
        
    Returns:
        Slug string (lowercase, hyphen-separated)
    """
    # Remove special characters and convert to lowercase
    text = re.sub(r'[^a-zA-Z0-9\s-]', '', text.lower())
    # Replace spaces with hyphens
    text = re.sub(r'[\s]+', '-', text.strip())
    # Remove consecutive hyphens
    text = re.sub(r'-+', '-', text)
    return text if text else 'section'


def extract_keywords(content: str, max_keywords: int = 5) -> List[str]:
    """
    Extract keywords from content (simple regex-based).
    
    Args:
        content: Text content
        max_keywords: Maximum number of keywords to extract
        
    Returns:
        List of keywords (4+ chars, most frequent)
    """
    # Extract words (4+ characters, alphanumeric only)
    words = re.findall(r'\b[a-zA-Z]{4,}\b', content.lower())
    
    # Count frequency
    freq = {}
    for word in words:
        freq[word] = freq.get(word, 0) + 1
    
    # Sort by frequency and return top keywords
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, count in sorted_words[:max_keywords]]


def infer_category(heading: str) -> str:
    """
    Infer category from heading text.
    
    Args:
        heading: The ## heading text
        
    Returns:
        Inferred category string
    """
    heading_lower = heading.lower()
    
    # Category keywords
    category_keywords = {
        'session_log': ['session', 'interaction', 'chat', 'conversation', 'todo', 'today'],
        'documentation': ['documentation', 'readme', 'guide', 'manual', 'docs'],
        'project': ['project', 'task', 'plan', 'feature', 'milestone'],
        'note': ['note', 'remind', 'todo', 'idea', 'brainstorm'],
        'technical': ['technical', 'implementation', 'code', 'api', 'system'],
        'personal': ['personal', 'reflection', 'journal', 'thought'],
        'meeting': ['meeting', 'discuss', 'decision', 'agree', 'plan'],
        'review': ['review', 'status', 'update', 'report'],
    }
    
    # Find best matching category
    best_category = 'general'
    best_score = 0
    
    for category, keywords in category_keywords.items():
        score = sum(1 for kw in keywords if kw in heading_lower)
        if score > best_score:
            best_score = score
            best_category = category
    
def _create_chunk(filename: str, heading: str, content: str, 
                  parent_file: str, chunk_index: int) -> ChunkMetadata:
    """
    Create a ChunkMetadata object with all fields populated.
    
    Args:
        filename: Base filename
        heading: Section heading text
        content: Section content
        parent_file: Full path to parent file
        chunk_index: Position index
        
    Returns:
        ChunkMetadata object
    """
    # Generate chunk ID
    slug = slugify(heading)
    chunk_id = f"{filename}#{slug}" if slug else f"{filename}#section-{chunk_index}"
    
    # Calculate approximate token count (4 chars ≈ 1 token)
    tokens = max(1, len(content) // 4)
    
    # Extract keywords
    keywords = extract_keywords(content)
    
    # Infer category
    category = infer_category(heading)
    
    return ChunkMetadata(
        id=chunk_id,
        parent_file=parent_file,
        heading=heading,
        content=content,
        keywords=keywords,
        category=category,
        tokens=tokens,
        chunk_index=chunk_index,
        original_length=len(content)
    )


import faiss
import numpy as np
import sqlite3

# Embedding model configuration (FastEmbed local, no external dependencies)
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# Import md2chunks splitter (new hybrid chunking for tables)
try:
    from .md2chunks_splitter import md2chunks_split, extract_tables
    MD2CHUNKS_AVAILABLE = True
except ImportError:
    MD2CHUNKS_AVAILABLE = False


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
    
    # Maximum embedding content size (1MB)
    MAX_EMBEDDING_SIZE = 1024 * 1024
    
    # Maximum batch size
    MAX_BATCH_SIZE = 100
    
    # Maximum files to index per batch (0 = no limit)
    DEFAULT_MAX_FILES_PER_BATCH = 0
    
    # Memory quality enhancement settings
    DEFAULT_ENABLE_RECENCY_RANKING = True
    DEFAULT_RECENCY_WEIGHT = 0.3
    DEFAULT_RECENCY_THRESHOLD_DAYS = 30
    DEFAULT_MIN_RECENCY_SCORE = 0.1
    DEFAULT_APPEND_ONLY_RECENCY_FACTOR = 0.33  # Reduce 30% → 10% for daily logs
    DEFAULT_ENABLE_LOCATION_RANKING = True
    DEFAULT_LOCATION_WEIGHT = 0.2
    
    def __init__(self):
        """Initialize configuration manager."""
        self.config = configparser.ConfigParser()
        self._load_config()
    
    # Maximum chunk size for adaptive chunking (in characters)
    # Overrides hardware-based auto-detection when set
    DEFAULT_MAX_CHUNK_SIZE = None
    
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
                self.data_dir = os.path.expanduser(self.config.get('settings', 'data_dir', fallback=self.data_dir))
                self.ollama_url = self.config.get('settings', 'ollama_url', fallback=self.ollama_url)
                
                # Directory indexing settings
                self.additional_dirs = self.config.get('settings', 'additional_dirs', fallback='')
                self.exclude_dirs = self.config.get('settings', 'exclude_dirs', fallback='')
                self.index_files = self.config.get('settings', 'index_files', fallback='')
                self.index_memory_md = self.config.getboolean('settings', 'index_memory_md', fallback=True)
                self.index_daily_files = self.config.getboolean('settings', 'index_daily_files', fallback=True)
                
                # File extensions to index
                extensions_str = self.config.get('settings', 'extensions', fallback='.md, .txt, .py, .json, .yaml, .yml, .csv')
                self.VALID_EXTENSIONS = {ext.strip() for ext in extensions_str.split(',') if ext.strip()}
                
                # Memory quality enhancement settings
                self.enable_recency_ranking = self.config.getboolean('settings', 'enable_recency_ranking', fallback=self.DEFAULT_ENABLE_RECENCY_RANKING)
                self.recency_weight = self.config.getfloat('settings', 'recency_weight', fallback=self.DEFAULT_RECENCY_WEIGHT)
                self.recency_threshold_days = self.config.getint('settings', 'recency_threshold_days', fallback=self.DEFAULT_RECENCY_THRESHOLD_DAYS)
                self.min_recency_score = self.config.getfloat('settings', 'min_recency_score', fallback=self.DEFAULT_MIN_RECENCY_SCORE)
                self.append_only_recency_factor = self.config.getfloat('settings', 'append_only_recency_factor', fallback=self.DEFAULT_APPEND_ONLY_RECENCY_FACTOR)
                # Location-based ranking settings
                self.enable_location_ranking = self.config.getboolean('settings', 'enable_location_ranking', fallback=self.DEFAULT_ENABLE_LOCATION_RANKING)
                self.location_weight = self.config.getfloat('settings', 'location_weight', fallback=self.DEFAULT_LOCATION_WEIGHT)
                
                # Chunking settings
                max_chunk_val = self.config.getint('settings', 'max_chunk_size', fallback=0)
                self.max_chunk_size = max_chunk_val if max_chunk_val > 0 else None
                
                # Batch limits
                self.max_files_per_batch = self.config.getint('settings', 'max_files_per_batch', fallback=self.DEFAULT_MAX_FILES_PER_BATCH)
                
                # Rate limiting settings (NEW - now configurable)
                self.rate_limit_requests = self.config.getint('settings', 'rate_limit_requests', fallback=600)
                self.rate_limit_window_seconds = self.config.getint('settings', 'rate_limit_window_seconds', fallback=60)
                
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
            self.additional_dirs = ''
            self.exclude_dirs = ''
            self.index_files = ''
            self.index_memory_md = True
            self.index_daily_files = True
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
# LRU Cache with TTL for Embeddings
# ============================================================================

class _LRUCache:
    """
    Thread-safe LRU cache with TTL expiration.
    Prevents unbounded memory growth while maintaining performance.
    """
    
    def __init__(self, maxsize: int = 10000, ttl: int = 3600):
        """
        Initialize LRU cache.
        
        Args:
            maxsize: Maximum number of entries (default 10000)
            ttl: Time-to-live in seconds (default 3600 = 1 hour)
        """
        self.maxsize = maxsize
        self.ttl = ttl
        self.cache = OrderedDict()
        self.timestamps = {}
        self._lock = None  # Simplified - no threading in this codebase
    
    def _is_expired(self, key: str) -> bool:
        """Check if a key has expired based on TTL."""
        if key not in self.timestamps:
            return True
        elapsed = time.time() - self.timestamps[key]
        return elapsed > self.ttl
    
    def get(self, key: str) -> Optional[np.ndarray]:
        """
        Get item from cache.
        
        Args:
            key: Cache key (text hash)
            
        Returns:
            Embedding array or None if not found/expired
        """
        if key not in self.cache:
            return None
        
        # Check if expired
        if self._is_expired(key):
            self._evict(key)
            return None
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return self.cache[key]
    
    def __contains__(self, key: str) -> bool:
        """Check if key is in cache (supports 'in' operator)."""
        if key not in self.cache:
            return False
        # Check if expired
        if self._is_expired(key):
            self._evict(key)
            return False
        return True
    
    def __getitem__(self, key: str) -> np.ndarray:
        """Get item using dict-style access (cache[key])."""
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value
    
    def __setitem__(self, key: str, value: np.ndarray) -> None:
        """Set item using dict-style access (cache[key] = value)."""
        self.put(key, value)
    
    def put(self, key: str, value: np.ndarray) -> None:
        """
        Add item to cache with LRU eviction and memory pressure checks.
        
        Args:
            key: Cache key (text hash)
            value: Embedding array
        """
        # Check memory pressure before adding
        if self._is_memory_pressure_high():
            # Evict more aggressively under memory pressure
            while len(self.cache) > int(self.maxsize * 0.7):
                oldest_key = next(iter(self.cache))
                self._evict(oldest_key)
        
        # Evict expired entries if cache is full
        while len(self.cache) >= self.maxsize:
            oldest_key = next(iter(self.cache))
            self._evict(oldest_key)
        
        # Add new entry
        self.cache[key] = value
        self.timestamps[key] = time.time()
    
    def _is_memory_pressure_high(self, threshold_percent: float = 0.85) -> bool:
        """
        Check if system memory pressure is high.
        
        Args:
            threshold_percent: Memory usage threshold (0.0-1.0)
            
        Returns:
            True if memory pressure is high
        """
        try:
            import psutil
            mem_info = psutil.virtual_memory()
            return mem_info.percent >= (threshold_percent * 100)
        except ImportError:
            # If psutil not available, check using /proc/meminfo
            try:
                # Use instance attribute to cache meminfo values (read once per cache instance)
                if not hasattr(self, '_meminfo_cache'):
                    # Read /proc/meminfo once and parse needed values
                    with open('/proc/meminfo', 'r') as f:
                        lines = f.readlines()
                    available_kb = None
                    total_kb = None
                    for line in lines:
                        if line.startswith('MemAvailable:'):
                            available_kb = int(line.split()[1])
                        elif line.startswith('MemTotal:'):
                            total_kb = int(line.split()[1])
                    # Cache the result on instance
                    self._meminfo_cache = (available_kb, total_kb)
                
                available_kb, total_kb = self._meminfo_cache
                if available_kb is not None and total_kb is not None:
                    used_percent = 100 - (available_kb / total_kb) * 100
                    return used_percent >= (threshold_percent * 100)
            except Exception:
                pass
            
            # Default to no pressure if we can't determine
            return False
    
    def _evict(self, key: str) -> None:
        """Evict a single key from cache."""
        if key in self.cache:
            del self.cache[key]
        if key in self.timestamps:
            del self.timestamps[key]
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.timestamps.clear()
    
    def __len__(self) -> int:
        """Return number of valid (non-expired) entries."""
        return sum(1 for k in self.cache if not self._is_expired(k))
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count of removed entries."""
        expired_keys = [k for k in self.cache if self._is_expired(k)]
        for key in expired_keys:
            self._evict(key)
        return len(expired_keys)


# ============================================================================
# Security Utilities
# ============================================================================

def sanitize_path(filepath: str, base_dir: Optional[str] = None, config = None) -> Optional[str]:
    """
    Sanitize and validate a file path to prevent path traversal attacks.
    
    Args:
        filepath: The file path to sanitize
        base_dir: Optional base directory to restrict paths to
        config: ConfigService or ConfigManager instance (uses global CONFIG if None)
        
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
            # Expand ~ before getting parent
            if Path(filepath).is_absolute():
                expanded_data_dir = os.path.expanduser(config.data_dir)
                base_dir = Path(expanded_data_dir).parent
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


def is_safe_symlink(filepath: str, allowed_dirs: List[str] = None, config = None) -> Tuple[bool, str]:
    """
    Check if a symlink is safe to follow.
    
    Args:
        filepath: Path to check
        allowed_dirs: List of allowed base directories
        config: ConfigService or ConfigManager instance
        
    Returns:
        Tuple of (is_safe: bool, reason: str)
    """
    if config is None:
        config = CONFIG
    
    if allowed_dirs is None:
        # Default allowed directories
        allowed_dirs = [config.data_dir]
    
    try:
        # Check if path is a symlink
        if os.path.islink(filepath):
            # Get the resolved path
            resolved_path = os.path.realpath(filepath)
            
            # Check if resolved path is within allowed directories
            for allowed_dir in allowed_dirs:
                allowed_dir_resolved = os.path.realpath(allowed_dir)
                try:
                    # Check if resolved path is within allowed directory
                    Path(resolved_path).relative_to(allowed_dir_resolved)
                    return True, "Safe symlink within allowed directory"
                except ValueError:
                    # Not within this allowed directory, check next
                    continue
            
            return False, f"Symlink resolves outside allowed directories"
        
        # Not a symlink, considered safe
        return True, "Not a symlink"
        
    except OSError as e:
        return False, f"Cannot resolve path: {e}"
    except Exception as e:
        return False, f"Error checking symlink: {e}"


# ============================================================================
# Rate Limiter for API Calls
# ============================================================================

class RateLimiter:
    """
    Thread-safe rate limiter using sliding window algorithm.
    
    Prevents Ollama API abuse by limiting requests within a time window.
    """
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests per window
            window_seconds: Time window in seconds (default 60s)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []  # List of request timestamps
        self._lock = None  # Simplified - no threading in this codebase
    
    def _cleanup_expired(self) -> None:
        """Remove expired request timestamps."""
        current_time = time.time()
        cutoff = current_time - self.window_seconds
        self.requests = [req_time for req_time in self.requests if req_time > cutoff]
    
    def is_allowed(self) -> bool:
        """
        Check if a new request is allowed.
        
        Returns:
            True if request is allowed, False if rate limited
        """
        self._cleanup_expired()
        
        if len(self.requests) >= self.max_requests:
            return False
        
        return True
    
    def record_request(self) -> bool:
        """
        Record a new request.
        
        Returns:
            True if request was recorded, False if rate limited
        """
        if not self.is_allowed():
            return False
        
        self.requests.append(time.time())
        return True
    
    def get_wait_time(self) -> float:
        """
        Get time to wait until next request is allowed.
        
        Returns:
            Seconds to wait (0 if allowed now)
        """
        self._cleanup_expired()
        
        if len(self.requests) < self.max_requests:
            return 0.0
        
        # Calculate wait time based on oldest request
        oldest_request = min(self.requests)
        wait_time = (oldest_request + self.window_seconds) - time.time()
        return max(0.0, wait_time)
    
    def reset(self) -> None:
        """Clear all request records."""
        self.requests.clear()


# ============================================================================
# Ollama Connection with Retry Logic
# ============================================================================

class FastEmbedClient:
    """FastEmbed client for local embeddings (no HTTP overhead)."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", 
                 max_retries: int = 3, timeout: int = 30):
        """
        Initialize FastEmbed client.
        
        Args:
            model_name: Hugging Face model name for embeddings
            max_retries: Maximum number of retry attempts  
            timeout: Request timeout in seconds (unused, for API compatibility)
        """
        self.model_name = model_name
        self.max_retries = max_retries
        self.timeout = timeout
        self._model = None
        self._model_loaded = False
        self.url = "local"  # For API compatibility
        
        # Check fastembed is available
        try:
            from fastembed import TextEmbedding
            self._TEXT_EMBEDDING = TextEmbedding
        except ImportError:
            raise ImportError("fastembed not installed. Run: pip install fastembed")
        
        logger.debug(f"FastEmbedClient initialized with model: {model_name}")
    
    def _load_model(self) -> bool:
        """Lazy load the embedding model."""
        if self._model_loaded:
            return True
        
        try:
            logger.info("Loading FastEmbed model (first call)...")
            self._model = self._TEXT_EMBEDDING(
                model_name=self.model_name,
                cache_dir=os.path.expanduser("~/.cache/fastembed")
            )
            self._model_loaded = True
            logger.info(f"✓ FastEmbed model loaded: {self.model_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to load FastEmbed model: {e}")
            return False
    
    def health_check(self) -> bool:
        """Check if FastEmbed is available (model can load)."""
        return self._load_model()
    
    def is_healthy(self, force_check: bool = False) -> bool:
        """
        Check if FastEmbed is healthy (cached for 60 seconds).
        
        Args:
            force_check: If True, bypass cache
            
        Returns:
            True if FastEmbed model can generate embeddings
        """
        import time
        
        # Use cached result if available
        if not force_check and hasattr(self, '_health_check_cache'):
            cached_result, cached_time = self._health_check_cache
            if time.time() - cached_time < 60:
                return cached_result
        
        # Perform actual check
        is_healthy = self._load_model()
        
        # Cache the result
        self._health_check_cache = (is_healthy, time.time())
        
        return is_healthy
    
    def generate_embeddings(self, texts: List[str]) -> Optional[np.ndarray]:
        """
        Generate embeddings using FastEmbed (local, no HTTP).
        
        Args:
            texts: List of strings to embed
            
        Returns:
            Embeddings array (N x 384) or None if failed
        """
        if not texts:
            logger.warning("Empty text list provided for embedding")
            return None
        
        if not self._load_model():
            return None
        
        for attempt in range(self.max_retries):
            try:
                # FastEmbed returns a generator, convert to list
                embeddings_gen = self._model.embed(texts)
                embeddings_list = list(embeddings_gen)
                
                if not embeddings_list:
                    logger.error("Empty embeddings list received")
                    return None
                
                # Convert to numpy array
                return np.array(embeddings_list).astype('float32')
                
            except Exception as e:
                logger.warning(f"Embedding generation attempt {attempt + 1}/{self.max_retries} failed: {e}")
                if attempt < self.max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)
        
        logger.error("All embedding generation attempts failed")
        return None


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
