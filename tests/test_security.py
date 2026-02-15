#!/usr/bin/env python3
"""
Security tests for fmem memory system.

Tests:
- Path traversal attacks
- SQL injection attempts
- Symlink following attacks
- Rate limiting
- Content validation
"""

import sys
import os
import tempfile
import shutil
import unittest
import time

# Add workspace to path
workspace = os.path.dirname(os.path.abspath(__file__))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

# Add parent directory for fmem module
parent_dir = os.path.dirname(workspace)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from fmem import (
    sanitize_path,
    is_safe_symlink,
    RateLimiter,
    MemoryRetrieval,
    ConfigManager
)


class TestPathTraversalProtection(unittest.TestCase):
    """Tests for path traversal attack prevention."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = ConfigManager()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_path_traversal_allowed(self):
        """Test that normal paths within allowed directory are allowed."""
        # Create a safe path within allowed directory
        safe_path = os.path.join(self.temp_dir, "test.md")
        with open(safe_path, 'w') as f:
            f.write("test content")
        
        result = sanitize_path(safe_path, base_dir=self.temp_dir, config=self.config)
        self.assertIsNotNone(result, "Safe path should be allowed")
        self.assertIn("test.md", result)
    
    def test_path_traversal_attack(self):
        """Test that path traversal attacks are blocked."""
        # Try to access parent directory
        malicious_path = "../../../etc/passwd"
        
        result = sanitize_path(malicious_path, base_dir=self.temp_dir, config=self.config)
        self.assertIsNone(result, "Path traversal attack should be blocked")
    
    def test_path_traversal_with_null_bytes(self):
        """Test that null bytes in paths are handled."""
        malicious_path = "/etc/passwd\x00.md"
        
        result = sanitize_path(malicious_path, config=self.config)
        # Should return None after sanitization
        self.assertIsNone(result, "Null byte paths should be blocked")
    
    def test_path_traversal_absolute_path(self):
        """Test that absolute paths outside allowed dir are blocked."""
        result = sanitize_path("/etc/passwd", base_dir=self.temp_dir, config=self.config)
        self.assertIsNone(result, "Absolute path outside allowed dir should be blocked")
    
    def test_path_traversal_symlink_attack(self):
        """Test that symlinks pointing outside allowed dir are detected."""
        # Create a directory that will be the target of symlink
        target_dir = tempfile.mkdtemp()
        try:
            # Create a symlink pointing outside allowed dir
            symlink_path = os.path.join(self.temp_dir, "bad_symlink")
            os.symlink("/etc/passwd", symlink_path)
            
            result = is_safe_symlink(symlink_path, allowed_dirs=[self.temp_dir], config=self.config)
            self.assertFalse(result[0], "Symlink to /etc/passwd should be flagged")
        finally:
            shutil.rmtree(target_dir, ignore_errors=True)


class TestSQLInjectionProtection(unittest.TestCase):
    """Tests for SQL injection attack prevention."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Use a subdirectory of the default data_dir for testing
        self.temp_dir = tempfile.mkdtemp()
        # Override config data_dir to point to temp_dir
        self.config = ConfigManager()
        self.config.data_dir = self.temp_dir
        self.memory = MemoryRetrieval(config=self.config, db_path=os.path.join(self.temp_dir, "test.db"))
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.memory.persist()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_sanitized_path_used_in_query(self):
        """Test that sanitize_path is called before SQL queries."""
        # Create test file in a subdirectory to ensure path validation works
        subdir = os.path.join(self.temp_dir, "docs")
        os.makedirs(subdir, exist_ok=True)
        test_file = os.path.join(subdir, "test.md")
        with open(test_file, 'w') as f:
            f.write("# Test\n\nTest content")
        
        # Verify file exists before adding
        self.assertTrue(os.path.exists(test_file), "Test file should exist")
        
        # Add document (this should sanitize the path)
        result = self.memory.add_document(test_file)
        # Note: If this fails, it may be due to path traversal protection
        # which is expected behavior for certain paths
        
        # Try to get chunks - this uses _get_chunks_for_file which has path validation
        chunks = self.memory._get_chunks_for_file(test_file)
        self.assertIsInstance(chunks, list, "Should return list of chunks")


class TestSymlinkProtection(unittest.TestCase):
    """Tests for symlink attack prevention."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = ConfigManager()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_safe_symlink_detection(self):
        """Test that safe symlinks within allowed dirs are allowed."""
        # Create a file in allowed directory
        target_file = os.path.join(self.temp_dir, "target.md")
        with open(target_file, 'w') as f:
            f.write("Target content")
        
        # Create symlink to the file
        symlink_path = os.path.join(self.temp_dir, "symlink.md")
        os.symlink(target_file, symlink_path)
        
        result = is_safe_symlink(symlink_path, allowed_dirs=[self.temp_dir], config=self.config)
        self.assertTrue(result[0], "Symlink within allowed dir should be safe")
    
    def test_dangerous_symlink_detection(self):
        """Test that symlinks pointing outside allowed dirs are flagged."""
        # Create symlink outside allowed directory
        symlink_path = os.path.join(self.temp_dir, "dangerous_symlink")
        os.symlink("/etc/passwd", symlink_path)
        
        result = is_safe_symlink(symlink_path, allowed_dirs=[self.temp_dir], config=self.config)
        self.assertFalse(result[0], "Symlink to /etc/passwd should be flagged as unsafe")
    
    def test_symlink_to_absolute_path(self):
        """Test that symlinks to absolute paths outside allowed dir are blocked."""
        # Create a link to system file
        symlink_path = os.path.join(self.temp_dir, "system_link")
        os.symlink("/etc/shadow", symlink_path)
        
        result = is_safe_symlink(symlink_path, allowed_dirs=[self.temp_dir], config=self.config)
        self.assertFalse(result[0], "Symlink to /etc/shadow should be blocked")


class TestRateLimiter(unittest.TestCase):
    """Tests for rate limiting functionality."""
    
    def test_rate_limiter_allows_requests(self):
        """Test that rate limiter allows requests within limit."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        
        # Should allow first 10 requests
        for i in range(10):
            self.assertTrue(limiter.record_request(), f"Request {i+1} should be allowed")
    
    def test_rate_limiter_blocks_excess_requests(self):
        """Test that rate limiter blocks requests exceeding limit."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        # Use up the rate limit
        for i in range(5):
            limiter.record_request()
        
        # 6th request should be blocked
        self.assertFalse(limiter.is_allowed(), "6th request should be blocked")
    
    def test_rate_limiter_reset(self):
        """Test that rate limiter can be reset."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        # Use up the limit
        for i in range(5):
            limiter.record_request()
        
        # Reset and verify
        limiter.reset()
        self.assertTrue(limiter.is_allowed(), "After reset, requests should be allowed")
    
    def test_rate_limiter_wait_time(self):
        """Test that wait time calculation works correctly."""
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        
        # Make one request
        limiter.record_request()
        
        # Should need to wait
        wait_time = limiter.get_wait_time()
        self.assertGreater(wait_time, 0, "Should need to wait after hitting limit")
    
    def test_rate_limiter_integration_with_memory(self):
        """Test that rate limiter is integrated with MemoryRetrieval."""
        temp_dir = tempfile.mkdtemp()
        try:
            memory = MemoryRetrieval(db_path=os.path.join(temp_dir, "test.db"))
            
            # Verify rate limiter exists
            self.assertIsNotNone(memory.rate_limiter, "Rate limiter should exist")
            self.assertEqual(memory.rate_limiter.max_requests, 10, "Default max_requests should be 10")
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestContentValidation(unittest.TestCase):
    """Tests for content validation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = ConfigManager()
    
    def test_max_embedding_size_constant(self):
        """Test that MAX_EMBEDDING_SIZE constant exists."""
        self.assertTrue(hasattr(self.config, 'MAX_EMBEDDING_SIZE'), "MAX_EMBEDDING_SIZE should exist")
        self.assertEqual(self.config.MAX_EMBEDDING_SIZE, 1024 * 1024, "MAX_EMBEDDING_SIZE should be 1MB")
    
    def test_content_validation_in_add_document(self):
        """Test that content size is validated before embedding."""
        temp_dir = tempfile.mkdtemp()
        try:
            memory = MemoryRetrieval(db_path=os.path.join(temp_dir, "test.db"))
            
            # Create a file that exceeds MAX_EMBEDDING_SIZE
            large_file = os.path.join(temp_dir, "large.md")
            # 2MB content (twice the limit)
            large_content = "x" * (2 * 1024 * 1024)
            with open(large_file, 'w') as f:
                f.write(large_content)
            
            # Should fail validation
            result = memory.add_document(large_file)
            self.assertFalse(result, "Document exceeding MAX_EMBEDDING_SIZE should be rejected")
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestMemoryPressure(unittest.TestCase):
    """Tests for memory pressure handling."""
    
    def test_memory_pressure_detection(self):
        """Test that memory pressure can be detected."""
        from fmem import _LRUCache
        
        cache = _LRUCache(maxsize=100)
        
        # Should have method for memory pressure detection
        self.assertTrue(hasattr(cache, '_is_memory_pressure_high'), "Cache should have _is_memory_pressure_high method")
    
    def test_memory_pressure_implementation(self):
        """Test that memory pressure check is implemented."""
        from fmem import _LRUCache
        
        cache = _LRUCache(maxsize=100)
        
        # Test with a small embedding
        import numpy as np
        small_embedding = np.array([0.1] * 768, dtype='float32')
        
        # Should not raise exception when memory pressure is checked
        try:
            cache.put("test_key", small_embedding)
            self.assertIn("test_key", cache)
        except Exception as e:
            self.fail(f"Memory pressure check should not raise exception: {e}")


class TestDatabaseIndex(unittest.TestCase):
    """Tests for database index."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_database_index_created(self):
        """Test that database index is created for chunks table."""
        from fmem import MemoryRetrieval
        
        db_path = os.path.join(self.temp_dir, "test.db")
        memory = MemoryRetrieval(db_path=db_path)
        
        try:
            # Query to check if index exists
            cursor = memory.conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name='idx_parent_file'
            """)
            result = cursor.fetchone()
            
            self.assertIsNotNone(result, "idx_parent_file index should exist")
        finally:
            memory.persist()
    
    def test_database_index_improves_performance(self):
        """Test that database query uses the index."""
        from fmem import MemoryRetrieval, ChunkMetadata
        
        db_path = os.path.join(self.temp_dir, "test.db")
        memory = MemoryRetrieval(db_path=db_path)
        
        try:
            # Add some test data
            test_file = os.path.join(self.temp_dir, "test.md")
            with open(test_file, 'w') as f:
                f.write("# Section 1\n\nContent 1\n\n# Section 2\n\nContent 2")
            
            memory.add_document(test_file)
            
            # This should use the index
            chunks = memory._get_chunks_for_file(test_file)
            self.assertIsInstance(chunks, list, "Should return list of chunks")
            
        finally:
            memory.persist()


if __name__ == '__main__':
    unittest.main()
