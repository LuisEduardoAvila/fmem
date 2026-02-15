"""
fmem - Local FAISS-Based Memory Search for OpenClaw

A privacy-focused, zero-cost memory search system with chunk-level indexing
for precise semantic retrieval.

Example:
    >>> from fmem import MemoryRetrieval
    >>> memory = MemoryRetrieval()
    >>> results = memory.search("project ideas", top_k=3, chunk_mode='chunk')
"""

__version__ = "3.0.0"
__author__ = "Luis Eduardo Avila"

# Expose the main classes directly (not wrapped)
from .fmem import MemoryRetrieval
from .fmem import chunk_markdown
from .fmem import ChunkMetadata
from .fmem import slugify
from .fmem import extract_keywords
from .fmem import infer_category
from .fmem import sanitize_path
from .fmem import is_safe_symlink
from .fmem import RateLimiter
from .fmem import ConfigManager
from .fmem import _LRUCache

def auto_recall(*args, **kwargs):
    from .fmem_integration import auto_recall as _ar
    return _ar(*args, **kwargs)

def format_results(*args, **kwargs):
    from .fmem_integration import format_results as _fr
    return _fr(*args, **kwargs)

__all__ = [
    'MemoryRetrieval',
    'chunk_markdown',
    'ChunkMetadata',
    'slugify',
    'extract_keywords',
    'infer_category',
    'auto_recall',
    'format_results',
    'sanitize_path',
    'is_safe_symlink',
    'RateLimiter',
    'ConfigManager',
    '_LRUCache',
]
