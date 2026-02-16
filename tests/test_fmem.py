#!/usr/bin/env python3
"""
fmem Unit Tests

Basic tests for fmem core functionality.
"""

import sys
import os
import tempfile
import unittest

# Add src to path to import fmem
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fmem import MemoryRetrieval, ConfigManager

class TestFmemCore(unittest.TestCase):
    """Test core fmem functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for test data
        self.test_dir = tempfile.mkdtemp()
        self.config = ConfigManager()
        self.config.data_dir = self.test_dir
        
    def tearDown(self):
        """Clean up test environment."""
        # Remove temporary directory
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_config_manager(self):
        """Test configuration manager."""
        self.assertIsInstance(self.config, ConfigManager)
        self.assertTrue(self.config.data_dir)
        
    def test_memory_initialization(self):
        """Test memory system initialization."""
        memory = MemoryRetrieval(config=self.config)
        self.assertIsNotNone(memory)
        
    def test_file_validation(self):
        """Test file path validation."""
        # Valid file
        self.assertTrue(self.config.is_valid_extension("/path/to/file.md"))
        self.assertTrue(self.config.is_valid_extension("/path/to/file.txt"))
        
        # Invalid extension
        self.assertFalse(self.config.is_valid_extension("/path/to/file.exe"))
        self.assertFalse(self.config.is_valid_extension("/path/to/file.jpg"))
        
    def test_query_validation(self):
        """Test query validation."""
        # Valid queries
        valid, msg = self.config.validate_query("test query")
        self.assertTrue(valid)
        
        # Invalid queries
        valid, msg = self.config.validate_query("")
        self.assertFalse(valid)
        
        valid, msg = self.config.validate_query("   ")
        self.assertFalse(valid)

class TestFmemIntegration(unittest.TestCase):
    """Test fmem integration functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Add src to path
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        
    def test_should_search(self):
        """Test search trigger logic."""
        from fmem_integration import should_search
        
        # Messages that should trigger search
        self.assertTrue(should_search("What were my preferences?"))
        self.assertTrue(should_search("Look up my settings"))
        self.assertTrue(should_search("Find information about projects"))
        
        # Messages that should not trigger search
        self.assertFalse(should_search("Hello, how are you?"))
        self.assertFalse(should_search("Good morning"))
        
    def test_extract_search_query(self):
        """Test search query extraction."""
        from fmem_integration import extract_search_query
        
        # Test query extraction
        query = extract_search_query("What were my preferences for the agent setup?")
        self.assertIn("preferences", query)
        self.assertIn("agent", query)

def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestFmemCore))
    suite.addTests(loader.loadTestsFromTestCase(TestFmemIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)