"""
fmem - FAISS-based Memory Search for OpenClaw

A privacy-focused, zero-cost memory search system with chunk-level indexing
for precise semantic retrieval using local FAISS embeddings via Ollama.

Version 3.2.0 - Refactored with Dependency Injection
"""

__version__ = "3.2.0"
__author__ = "Luis Eduardo Avila"
__email__ = "luis.eduardo.avila@gmail.com"

# Core imports (new refactored architecture)
from .config import ConfigService, ConfigData
from .embedding_service import EmbeddingService
from .search_index import SearchIndex
from .database_service import DatabaseService
from .result_enhancer import ResultEnhancer, EnhancerConfig
from .file_summarizer import FileSummarizer
from .document_manager import DocumentManager

# Backward compatibility - MemoryRetrieval is now a composition root
from .memory_retrieval import MemoryRetrieval

# Legacy aliases for backward compatibility
ConfigManager = ConfigService  # Legacy name

# Chunking (unified table-aware and heading-based)
from .chunking import chunk_markdown

# Utility functions
from .fmem import get_optimal_chunk_size, chunk_content_adaptively

# Integration helpers
from .fmem_integration import auto_recall, should_search, format_results
from . import memory_utils

__all__ = [
    # Core services (new architecture)
    "ConfigService",
    "ConfigData",
    "EmbeddingService",
    "SearchIndex",
    "DatabaseService",
    "ResultEnhancer",
    "EnhancerConfig",
    "FileSummarizer",
    "DocumentManager",
    
    # Main facade (composition root)
    "MemoryRetrieval",
    
    # Legacy aliases
    "ConfigManager",
    
    # Chunking
    "chunk_markdown",
    
    # Utility functions
    "get_optimal_chunk_size",
    "chunk_content_adaptively",
    
    # Integration helpers
    "auto_recall",
    "should_search",
    "format_results",
    "memory_utils"
]
