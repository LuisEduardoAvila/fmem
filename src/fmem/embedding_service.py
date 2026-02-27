#!/usr/bin/env python3
"""
Embedding Service for fmem v3.1.0

Handles embedding generation with caching and rate limiting.
Extracted from MemoryRetrieval as part of Phase 2 SRP decomposition.
"""

import hashlib
import logging
import time
import re
from collections import OrderedDict
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)


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
# RateLimiter (copied from fmem.py)
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
# EmbeddingService
# ============================================================================

class EmbeddingService:
    """
    Handles embedding generation with caching and rate limiting.
    
    Extracted from MemoryRetrieval to follow Single Responsibility Principle.
    """
    
    def __init__(
        self,
        embedding_client,  # FastEmbedClient or similar
        config,  # ConfigService or ConfigData
        rate_limiter: Optional[RateLimiter] = None
    ):
        """
        Initialize EmbeddingService.
        
        Args:
            embedding_client: Client for generating embeddings (e.g., FastEmbedClient)
            config: Configuration object (ConfigService or ConfigData)
            rate_limiter: Optional RateLimiter instance. If None, creates one from config.
        """
        self._client = embedding_client
        self._config = config
        
        # Get rate limit settings from config
        max_requests = getattr(config, 'rate_limit_requests', 10)
        window_seconds = getattr(config, 'rate_limit_window_seconds', 60)
        
        # Use provided rate limiter or create new one from config
        self._rate_limiter = rate_limiter or RateLimiter(
            max_requests=max_requests,
            window_seconds=window_seconds
        )
        
        # Initialize embedding cache with TTL (1 hour) and LRU eviction (max 10000 entries)
        self._embedding_cache = _LRUCache(maxsize=10000, ttl=3600)
    
    def _preprocess_for_embedding(self, content: str, heading: str = "") -> str:
        """
        Preprocess content for embedding: extract headings + summary.
        
        This ensures content fits within Ollama's context window while
        preserving semantic structure for searchability.
        
        Args:
            content: The content to preprocess
            heading: Optional heading string
            
        Returns:
            Preprocessed string suitable for embedding
        """
        # Extract all ## and ### headings from content
        headings = re.findall(r'^(#{2,3})\s+(.+)$', content, re.MULTILINE)
        heading_lines = [f"{'#'*min(3,len(h[0]))} {h[1]}" for h in headings[:8]]
        
        # Create brief summary from first 200 chars of actual text (not markdown)
        # Remove markdown syntax for summary
        text_only = re.sub(r'[#*`\[\]|]', '', content[:300]).replace('\n', ' ').strip()
        summary = text_only[:180] + "..." if len(text_only) > 180 else text_only
        
        # Combine: headings give structure, summary gives content
        if heading_lines:
            structured = '\n'.join(heading_lines) + '\n\n' + summary
        else:
            structured = heading + '\n\n' + summary if heading else summary
        
        # Ensure under 500 chars (safe for all-minilm:22m)
        result = structured[:500]
        
        return result
    
    def get_embedding(self, text: str, heading: str = "") -> Optional[np.ndarray]:
        """
        Get embedding from cache or generate new one with rate limiting.
        
        Args:
            text: The text to embed
            heading: Optional heading for context
            
        Returns:
            Embedding array or None if failed/rate limited
        """
        # Preprocess text before embedding (headings + summary)
        processed_text = self._preprocess_for_embedding(text, heading=heading)
        
        # Generate cache key using MD5 hash of processed text
        text_hash = hashlib.md5(processed_text.encode()).hexdigest()
        
        # Check cache first
        if text_hash in self._embedding_cache:
            return self._embedding_cache[text_hash]
        
        # Check rate limit before making API call
        if not self._rate_limiter.is_allowed():
            logger.warning("Rate limit exceeded for embedding generation")
            return None
        
        # Generate embedding using the client
        embedding = self._client.generate_embeddings([processed_text])
        
        if embedding is not None:
            # Record the successful request
            self._rate_limiter.record_request()
            # Cache the embedding
            self._embedding_cache[text_hash] = embedding[0]
        
        return embedding[0] if embedding is not None else None
    
    def get_embeddings_batch(self, texts: List[str]) -> Optional[np.ndarray]:
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
        batch_size = getattr(self._config, 'MAX_BATCH_SIZE', 100)
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = self._client.generate_embeddings(batch)
            
            if embeddings is not None:
                all_embeddings.append(embeddings)
            else:
                logger.warning(f"Failed to generate embeddings for batch {i//batch_size + 1}")
        
        if all_embeddings:
            return np.vstack(all_embeddings)
        return None
    
    @property
    def cache(self) -> _LRUCache:
        """Return the embedding cache for inspection."""
        return self._embedding_cache
    
    def cache_size(self) -> int:
        """Return the number of items in the cache."""
        return len(self._embedding_cache)
    
    def health_check(self) -> bool:
        """Check if embedding service is healthy."""
        try:
            # Check if client is available
            if self._client is None:
                return False
            # Try to generate a test embedding
            test_embedding = self._client.generate_embeddings(["test"])
            return test_embedding is not None
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
    
    @property
    def rate_limiter(self) -> RateLimiter:
        """Return the rate limiter for inspection."""
        return self._rate_limiter
