"""fmem - FAISS-based Memory Search for OpenClaw"""

from .fmem import MemoryRetrieval, __version__, CONFIG, ChunkMetadata
from .fmem_integration import auto_recall, format_results, should_search

__all__ = [
    'MemoryRetrieval',
    '__version__',
    'CONFIG',
    'ChunkMetadata',
    'auto_recall',
    'format_results',
    'should_search',
]
