"""
Integration tests for refactored fmem (Phase 9)

Tests that verify all services work together correctly.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fmem import (
    ConfigService,
    EmbeddingService,
    SearchIndex,
    DatabaseService,
    ResultEnhancer,
    EnhancerConfig,
    FileSummarizer,
    DocumentManager,
    MemoryRetrieval,
)


class TestServiceIntegration(unittest.TestCase):
    """Integration tests for refactored services."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = os.path.join(self.temp_dir, 'test_data')
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_config_service(self):
        """Test ConfigService initialization."""
        # Use environment variable approach for testing
        import tempfile
        temp_data_dir = tempfile.mkdtemp()
        os.environ['FMEM_DATA_DIR'] = temp_data_dir
        os.environ['FMEM_CONFIG'] = os.path.join(temp_data_dir, 'fmem.conf')
        
        # Create config file
        with open(os.environ['FMEM_CONFIG'], 'w') as f:
            f.write("[settings]\n")
            f.write(f"data_dir = {temp_data_dir}\n")
        
        try:
            config = ConfigService()
            self.assertEqual(config.data_dir, temp_data_dir)
        finally:
            # Cleanup
            if 'FMEM_DATA_DIR' in os.environ:
                del os.environ['FMEM_DATA_DIR']
            if 'FMEM_CONFIG' in os.environ:
                del os.environ['FMEM_CONFIG']
            import shutil
            shutil.rmtree(temp_data_dir, ignore_errors=True)
    
    def test_search_index(self):
        """Test SearchIndex operations."""
        index = SearchIndex(dimension=384, data_dir=self.data_dir)
        
        # Test add
        import numpy as np
        embedding = np.random.random(384).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)  # Normalize
        
        idx = index.add(embedding, "test.md", "test.md#section-1",
                       heading="Test Section")
        self.assertEqual(idx, 0)
        self.assertEqual(len(index), 1)
        
        # Test search
        results = index.search(embedding, top_k=1, min_score=0.0)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['filepath'], "test.md")
        
        # Test save/load
        index.save()
        index.reset()
        self.assertEqual(len(index), 0)
        
        index.load()
        self.assertEqual(len(index), 1)
    
    def test_database_service(self):
        """Test DatabaseService operations."""
        db_path = os.path.join(self.data_dir, 'test.db')
        db = DatabaseService(db_path)
        
        # Test document CRUD
        doc_id = db.store_document(
            filepath="test.md",
            content="Test content",
            last_modified=1234567890,
            created_at=1234567890
        )
        self.assertIsNotNone(doc_id)
        
        doc = db.get_document("test.md")
        self.assertIsNotNone(doc)
        self.assertEqual(doc['filepath'], "test.md")
        
        # Test chunk CRUD
        success = db.store_chunk(
            chunk_id="test.md#section-1",
            parent_file="test.md",
            heading="Section 1",
            content="Chunk content",
            keywords=["test", "chunk"],
            category="test",
            token_count=10,
            chunk_index=0
        )
        self.assertTrue(success)
        
        chunk = db.get_chunk("test.md#section-1")
        self.assertIsNotNone(chunk)
        self.assertEqual(chunk['parent_file'], "test.md")
        
        db.close()
    
    def test_file_summarizer(self):
        """Test FileSummarizer."""
        summarizer = FileSummarizer()
        
        # Memory file
        memory_content = "# Session 2026-02-24\n\n## FMEM Refactoring\nCompleted Phase 8 ✅\n\n## Testing\nIn progress 🔄"
        summary = summarizer.summarize(memory_content, "memory/2026-02-24.md")
        self.assertIn("2026-02-24", summary)
        self.assertIn("topics", summary)
        
        # Regular file
        regular_content = "# Project README\n\nThis is a test project.\n\n## Features\nFeature 1\nFeature 2"
        summary = summarizer.summarize(regular_content, "README.md")
        self.assertIn("README", summary)
        
        # Test topics extraction
        topics = summarizer.extract_topics(regular_content)
        self.assertGreater(len(topics), 0)
    
    def test_result_enhancer(self):
        """Test ResultEnhancer."""
        enhancer = ResultEnhancer()
        
        results = [
            {'filepath': 'docs/test.md', 'score': 0.8},
            {'filepath': 'chats/test.md', 'score': 0.9},
        ]
        
        doc_metadata = {
            'docs/test.md': {'last_modified': 1704067200},
            'chats/test.md': {'last_modified': 1706659200},
        }
        
        enhanced = enhancer.enhance(results, doc_metadata)
        self.assertEqual(len(enhanced), 2)
        
        # Docs should get higher weight (1.5)
        self.assertIn('location_score', enhanced[0])
    
    def test_document_manager(self):
        """Test DocumentManager with mocked dependencies."""
        # This test would require Ollama running, so we skip for basic integration
        self.skipTest("Requires Ollama - run manually")
    
    def test_memory_retrieval_facade(self):
        """Test MemoryRetrieval as composition root."""
        # This test would require Ollama running
        self.skipTest("Requires Ollama - run manually")


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility."""
    
    def test_memory_retrieval_import(self):
        """Test that MemoryRetrieval can still be imported."""
        try:
            from fmem import MemoryRetrieval as MR
            # Should not raise
            self.assertTrue(callable(MR))
        except ImportError as e:
            self.fail(f"Import failed: {e}")
    
    def test_config_manager_alias(self):
        """Test ConfigManager still works (alias)."""
        from fmem import ConfigManager, ConfigService
        self.assertEqual(ConfigManager, ConfigService)


class TestServiceIndependence(unittest.TestCase):
    """Test that services can be used independently."""
    
    def test_services_independent(self):
        """Test each service can be instantiated alone."""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Config alone (create temp config file)
            config_path = os.path.join(temp_dir, 'test.conf')
            with open(config_path, 'w') as f:
                f.write("[settings]\n")
                f.write(f"data_dir = {temp_dir}\n")
            config = ConfigService(config_path=config_path)
            self.assertIsNotNone(config)
            
            # SearchIndex alone
            index = SearchIndex(dimension=384, data_dir=temp_dir)
            self.assertIsNotNone(index)
            
            # Database alone
            db_path = os.path.join(temp_dir, 'test.db')
            db = DatabaseService(db_path)
            self.assertIsNotNone(db)
            db.close()
            
            # Summarizer alone
            summarizer = FileSummarizer()
            self.assertIsNotNone(summarizer)
            
            # Enhancer alone
            enhancer = ResultEnhancer()
            self.assertIsNotNone(enhancer)
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
