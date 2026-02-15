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

# Lazy imports to avoid circular dependencies
def MemoryRetrieval(*args, **kwargs):
    from .fmem import MemoryRetrieval as _MR
    return _MR(*args, **kwargs)

def chunk_markdown(*args, **kwargs):
    from .fmem import chunk_markdown as _cm
    return _cm(*args, **kwargs)

def ChunkMetadata(*args, **kwargs):
    from .fmem import ChunkMetadata as _CM
    return _CM(*args, **kwargs)

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
    'auto_recall',
    'format_results',
]
