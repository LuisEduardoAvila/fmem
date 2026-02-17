"""
fmem - FAISS-based Memory Search for OpenClaw

A privacy-focused, zero-cost memory search system with chunk-level indexing
for precise semantic retrieval using local FAISS embeddings via Ollama.
"""

__version__ = "3.1.0"
__author__ = "Luis Eduardo Avila"
__email__ = "luis.eduardo.avila@gmail.com"

# Core imports
from .fmem import MemoryRetrieval, ConfigManager, get_optimal_chunk_size, chunk_content_adaptively
from .fmem_integration import auto_recall, should_search, format_results
from . import memory_utils

__all__ = [
    "MemoryRetrieval",
    "ConfigManager", 
    "get_optimal_chunk_size",
    "chunk_content_adaptively",
    "auto_recall",
    "should_search",
    "format_results",
    "memory_utils"
]