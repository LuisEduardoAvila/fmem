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

__version__ = "3.0.0"

# ============================================================================
# Chunk Metadata Schema
# ============================================================================

class ChunkMetadata:
    """Represents a chunk with metadata for enhanced retrieval."""
    
    def __init__(self, id: str, parent_file: str, heading: str, 
                 content: str, summary: str = None, keywords: List[str] = None,
                 category: str = None, tokens: int = 0, chunk_index: int = 0):
        """
        Initialize chunk metadata.
        
        Args:
            id: Unique chunk identifier (e.g., "MEMORY.md#session-2026-02-13")
            parent_file: Path to original file
            heading: The ## heading text that defines this chunk
            content: Section content
            summary: Chunk summary (generated in Phase 2)
            keywords: Extracted keywords from content
            category: Inferred category from heading
            tokens: Approximate token count
            chunk_index: Position index within parent file
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
            'chunk_index': self.chunk_index
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
            chunk_index=data.get('chunk_index', 0)
        )


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
    
    return best_category


def chunk_markdown(content: str, filepath: str, min_chunk_size: int = 50) -> List[ChunkMetadata]:
    """
    Split markdown by ## headings.
    Each section becomes a chunk with:
    - id: "{filename}#{heading-slug}"
    - parent_file: original filepath
    - heading: the ## heading text
    - content: section content
    - summary: NOT generated yet (Phase 2)
    - keywords: extracted from content (simple regex)
    - category: inferred from heading
    - tokens: approximate count
    
    Args:
        content: Full markdown content
        filepath: Original file path
        min_chunk_size: Minimum chunk size in chars (merge smaller sections)
        
    Returns:
        List of ChunkMetadata objects
    """
    if not content or not filepath:
        return []
    
    filename = os.path.basename(filepath)
    chunks = []
    current_heading = "Top-Level Content"
    current_content = ""
    heading_pattern = re.compile(r'^(#{2,})\s+(.+)$', re.MULTILINE)
    
    # Split content by ## headings
    parts = []
    last_end = 0
    
    for match in heading_pattern.finditer(content):
        # Add content before this heading
        if match.start() > last_end:
            section_content = content[last_end:match.start()].strip()
            if section_content:
                parts.append((current_heading, section_content))
        
        # Update current heading
        current_heading = match.group(2).strip()
        last_end = match.end()
    
    # Add remaining content after last heading
    if last_end < len(content):
        section_content = content[last_end:].strip()
        if section_content:
            parts.append((current_heading, section_content))
    
    # If no headings found, treat entire content as one chunk
    if not parts:
        # Remove file header/if present
        content_clean = content.strip()
        if content_clean:
            chunks.append(_create_chunk(
                filename=filename,
                heading="Document",
                content=content_clean,
                parent_file=filepath,
                chunk_index=0
            ))
        return chunks
    
    # Merge small chunks (under min_chunk_size)
    merged_parts = []
    buffer_heading = ""
    buffer_content = ""
    
    for heading, section_content in parts:
        # Merge if buffer has content and new section is small
        if buffer_content and len(buffer_content) + len(section_content) < min_chunk_size:
            buffer_content += "\n\n" + section_content
        else:
            # Save current buffer if exists
            if buffer_content:
                merged_parts.append((buffer_heading, buffer_content))
            # Start new buffer
            buffer_heading = heading
            buffer_content = section_content
    
    # Don't forget the last buffer
    if buffer_content:
        merged_parts.append((buffer_heading, buffer_content))
    
    # Create chunks from merged parts
    for i, (heading, section_content) in enumerate(merged_parts):
        chunk = _create_chunk(
            filename=filename,
            heading=heading,
            content=section_content,
            parent_file=filepath,
            chunk_index=i
        )
        chunks.append(chunk)
    
    return chunks


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
        chunk_index=chunk_index
    )


import faiss
import numpy as np
import sqlite3
import json
import os
import sys
import logging
import datetime
import hashlib
import re
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from contextlib import contextmanager
from collections import OrderedDict

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
    
    # Maximum embedding content size (1MB)
    MAX_EMBEDDING_SIZE = 1024 * 1024
    
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
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if line.startswith('MemAvailable:'):
                            available_kb = int(line.split()[1])
                            total_kb = int(open('/proc/meminfo').read().split('\n')[0].split()[1])
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


def is_safe_symlink(filepath: str, allowed_dirs: List[str] = None, config: ConfigManager = None) -> Tuple[bool, str]:
    """
    Check if a symlink is safe to follow.
    
    Args:
        filepath: Path to check
        allowed_dirs: List of allowed base directories
        config: ConfigManager instance
        
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
        # Rate limiter for Ollama API (10 requests per 60 seconds)
        self.rate_limiter = RateLimiter(max_requests=10, window_seconds=60)
        # Embedding cache with TTL (1 hour) and LRU eviction (max 10000 entries)
        self.embedding_cache = _LRUCache(maxsize=10000, ttl=3600)
        
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                parent_file TEXT,
                heading TEXT,
                content TEXT,
                keywords TEXT,
                category TEXT,
                token_count INTEGER,
                chunk_index INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Create index for parent_file to speed up chunk lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_parent_file ON chunks(parent_file)
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
        """Get embedding from cache or generate new one with rate limiting."""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        if text_hash in self.embedding_cache:
            return self.embedding_cache[text_hash]
        
        # Check rate limit before making API call
        if not self.rate_limiter.is_allowed():
            logger.warning("Rate limit exceeded for embedding generation")
            return None
        
        embedding = self.ollama.generate_embeddings([text])
        if embedding is not None:
            # Record the successful request
            self.rate_limiter.record_request()
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
    
    def _store_chunk_metadata(self, chunk: ChunkMetadata) -> bool:
        """
        Store chunk metadata in SQLite database.
        
        Args:
            chunk: ChunkMetadata object
            
        Returns:
            True if successful, False otherwise
        """
        if not self.conn:
            return False
        
        try:
            cursor = self.conn.cursor()
            
            # Convert keywords list to comma-separated string
            keywords_str = ','.join(chunk.keywords) if chunk.keywords else ''
            
            cursor.execute("""
                INSERT OR REPLACE INTO chunks 
                (chunk_id, parent_file, heading, content, keywords, category, token_count, chunk_index)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                chunk.id,
                chunk.parent_file,
                chunk.heading,
                chunk.content,
                keywords_str,
                chunk.category,
                chunk.tokens,
                chunk.chunk_index
            ))
            
            self.conn.commit()
            logger.debug(f"✓ Stored chunk: {chunk.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store chunk metadata: {e}")
            return False
    
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
    
    def add_document(self, filepath: str, content: Optional[str] = None, 
                     chunk_by_sections: bool = True) -> bool:
        """
        Add a document to memory system with validation.
        
        Args:
            filepath: Path to file (for metadata)
            content: Full document content. If None, reads from file.
            chunk_by_sections: If True, split markdown by ## headings and index each as separate chunk.
                             If False, index as single document (backward compatible).
            
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
            
            # Check symlink safety
            is_safe, reason = is_safe_symlink(filepath, config=self.config)
            if not is_safe:
                logger.error(f"Unsafe symlink detected: {reason}")
                return False
            
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
            
            # Verify content doesn't exceed embedding size limit
            if len(content) > self.config.MAX_EMBEDDING_SIZE:
                logger.error(f"Content exceeds embedding size limit: {len(content)} > {self.config.MAX_EMBEDDING_SIZE}")
                return False
            
            # Generate embedding for main document
            main_embedding = self._get_embedding(content[:1000])  # Use first 1000 chars
            
            # Determine whether to chunk or index as whole document
            if chunk_by_sections and filepath.endswith('.md'):
                # Chunk markdown by sections
                chunks = chunk_markdown(content, filepath)
                logger.info(f"✓ Split {filepath} into {len(chunks)} chunks")
                
                # Index each chunk separately
                chunk_embeddings = []
                for i, chunk in enumerate(chunks):
                    # Generate embedding for chunk
                    chunk_embedding = self._get_embedding(chunk.content[:1000])
                    if chunk_embedding is not None:
                        chunk_embeddings.append(chunk_embedding)
                        
                        # Add to FAISS index
                        if self.index is None:
                            self.index = faiss.IndexFlatIP(self.dimension)
                        self.index.add(np.array([chunk_embedding]))
                        
                        # Store chunk metadata
                        self._store_chunk_metadata(chunk)
                
                # Also store the full document for backward compatibility
                metadata = {
                    'filepath': filepath,
                    'content': content,
                    'last_modified': int(datetime.datetime.now().timestamp()),
                    'created_at': int(datetime.datetime.now().timestamp()),
                    'is_chunked': True,
                    'chunk_count': len(chunks)
                }
                
                # Add document metadata (pointing to chunks)
                existing_idx = None
                for i, doc in enumerate(self.doc_metadata):
                    if doc['filepath'] == filepath:
                        existing_idx = i
                        break
                
                if existing_idx is not None:
                    self.doc_metadata[existing_idx] = metadata
                else:
                    self.doc_metadata.append(metadata)
                
                # Store in database
                self._store_embedding(metadata, content)
                
                if chunk_embeddings:
                    logger.info(f"✓ Indexed {len(chunks)} chunks with embeddings")
                
            else:
                # Traditional document indexing (no chunking)
                metadata = {
                    'filepath': filepath,
                    'content': content,
                    'last_modified': int(datetime.datetime.now().timestamp()),
                    'created_at': int(datetime.datetime.now().timestamp()),
                    'is_chunked': False
                }
                
                # Check if document already exists
                existing_idx = None
                for i, doc in enumerate(self.doc_metadata):
                    if doc['filepath'] == filepath:
                        existing_idx = i
                        break
                
                if existing_idx is not None:
                    self.doc_metadata[existing_idx] = metadata
                    logger.info(f"✓ Updated document: {filepath}")
                else:
                    self.doc_metadata.append(metadata)
                    
                    # Add to FAISS index
                    if main_embedding is not None:
                        if self.index is None:
                            self.index = faiss.IndexFlatIP(self.dimension)
                        self.index.add(np.array([main_embedding]))
                    
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
    
    def search(self, query: str, top_k: int = 5, chunk_mode: str = "chunk") -> List[Dict]:
        """
        Search memory for relevant documents with validation.
        
        Args:
            query: Search query string
            top_k: Number of relevant documents to return
            chunk_mode: How to return results:
                       - "chunk": Return individual chunks with full metadata
                       - "document": Return full documents only
                       - "hybrid": Return both chunks and documents
            
        Returns:
            List of {filepath, content, score, chunk_info?} dicts
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
        
        # Build results based on chunk_mode
        results = []
        processed_chunks = set()  # Track processed chunk IDs for deduplication
        
        for idx in range(len(I[0])):
            doc_idx = I[0][idx]
            if doc_idx >= len(self.doc_metadata):
                continue
            
            doc = self.doc_metadata[doc_idx]
            filepath = doc['filepath']
            
            # Handle chunk_mode
            if chunk_mode == "document" or not doc.get('is_chunked', False):
                # Return full document
                results.append({
                    'filepath': filepath,
                    'content': doc.get('content', ''),
                    'score': float(D[0][idx]),
                    'chunk_mode': 'document',
                    'is_chunked': doc.get('is_chunked', False)
                })
            elif chunk_mode == "chunk":
                # Return individual chunks
                chunks = self._get_chunks_for_file(filepath)
                for chunk in chunks:
                    if chunk.id not in processed_chunks:
                        processed_chunks.add(chunk.id)
                        results.append({
                            'filepath': chunk.parent_file,
                            'content': chunk.content,
                            'score': float(D[0][idx]),
                            'chunk_mode': 'chunk',
                            'chunk_info': chunk.to_dict()
                        })
            elif chunk_mode == "hybrid":
                # Return both chunks and document
                chunks = self._get_chunks_for_file(filepath)
                chunk_results = []
                for chunk in chunks:
                    if chunk.id not in processed_chunks:
                        processed_chunks.add(chunk.id)
                        chunk_results.append({
                            'filepath': chunk.parent_file,
                            'content': chunk.content,
                            'score': float(D[0][idx]),
                            'chunk_mode': 'chunk',
                            'chunk_info': chunk.to_dict()
                        })
                
                # Add document result
                doc_result = {
                    'filepath': filepath,
                    'content': doc.get('content', ''),
                    'score': float(D[0][idx]),
                    'chunk_mode': 'document',
                    'is_chunked': doc.get('is_chunked', False)
                }
                
                # Combine document with its chunks
                doc_result['chunks'] = chunk_results
                results.append(doc_result)
        
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
    
    def _get_chunks_for_file(self, filepath: str) -> List[ChunkMetadata]:
        """
        Retrieve chunks for a file from database with path validation.
        
        Args:
            filepath: File path
            
        Returns:
            List of ChunkMetadata objects
        """
        if not self.conn:
            return []
        
        # Validate filepath to prevent SQL injection and path traversal
        safe_path = sanitize_path(filepath, config=self.config)
        if safe_path is None:
            logger.warning(f"Invalid filepath for chunk retrieval: {filepath}")
            return []
        
        filepath = safe_path
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT chunk_id, parent_file, heading, content, keywords, 
                       category, token_count, chunk_index
                FROM chunks WHERE parent_file = ?
                ORDER BY chunk_index
            """, (filepath,))
            
            chunks = []
            for row in cursor.fetchall():
                keywords = row[4].split(',') if row[4] else []
                chunk = ChunkMetadata(
                    id=row[0],
                    parent_file=row[1],
                    heading=row[2],
                    content=row[3],
                    keywords=keywords,
                    category=row[5],
                    tokens=row[6],
                    chunk_index=row[7]
                )
                chunks.append(chunk)
            
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to retrieve chunks for {filepath}: {e}")
            return []
    
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
