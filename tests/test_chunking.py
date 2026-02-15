#!/usr/bin/env python3
"""
Unit tests for chunk-level indexing functionality.

Tests:
- chunk_markdown() splits correctly
- Empty/short sections handled
- Non-markdown files fallback to whole document
- Chunk IDs are unique
- Search returns chunks properly
"""

import sys
import os
import tempfile
import shutil
import unittest

# Add workspace to path
workspace = os.path.dirname(os.path.abspath(__file__))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

# Add parent directory for fmem module
parent_dir = os.path.dirname(workspace)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from fmem import (
    chunk_markdown, 
    ChunkMetadata, 
    slugify,
    extract_keywords,
    infer_category
)


class TestChunkMetadata(unittest.TestCase):
    """Tests for ChunkMetadata class."""
    
    def test_chunk_metadata_creation(self):
        """Test basic ChunkMetadata creation."""
        chunk = ChunkMetadata(
            id="test.md#section-1",
            parent_file="test.md",
            heading="Section 1",
            content="Test content",
            keywords=["test", "content"],
            category="test",
            tokens=5,
            chunk_index=0
        )
        
        self.assertEqual(chunk.id, "test.md#section-1")
        self.assertEqual(chunk.parent_file, "test.md")
        self.assertEqual(chunk.heading, "Section 1")
        self.assertEqual(chunk.content, "Test content")
        self.assertEqual(chunk.keywords, ["test", "content"])
        self.assertEqual(chunk.category, "test")
        self.assertEqual(chunk.tokens, 5)
        self.assertEqual(chunk.chunk_index, 0)
    
    def test_chunk_metadata_to_dict(self):
        """Test ChunkMetadata to_dict method."""
        chunk = ChunkMetadata(
            id="test.md#section-1",
            parent_file="test.md",
            heading="Section 1",
            content="Test content"
        )
        
        chunk_dict = chunk.to_dict()
        
        self.assertIn('id', chunk_dict)
        self.assertIn('parent_file', chunk_dict)
        self.assertIn('heading', chunk_dict)
        self.assertIn('content', chunk_dict)
        self.assertIn('keywords', chunk_dict)
        self.assertIn('category', chunk_dict)
        self.assertIn('tokens', chunk_dict)
        self.assertIn('chunk_index', chunk_dict)
    
    def test_chunk_metadata_from_dict(self):
        """Test ChunkMetadata from_dict method."""
        data = {
            'id': "test.md#section-1",
            'parent_file': "test.md",
            'heading': "Section 1",
            'content': "Test content",
            'keywords': ["test"],
            'category': "test",
            'tokens': 5,
            'chunk_index': 0
        }
        
        chunk = ChunkMetadata.from_dict(data)
        
        self.assertEqual(chunk.id, "test.md#section-1")
        self.assertEqual(chunk.parent_file, "test.md")
        self.assertEqual(chunk.heading, "Section 1")
        self.assertEqual(chunk.content, "Test content")
        self.assertEqual(chunk.keywords, ["test"])
        self.assertEqual(chunk.category, "test")
        self.assertEqual(chunk.tokens, 5)
        self.assertEqual(chunk.chunk_index, 0)


class TestSlugify(unittest.TestCase):
    """Tests for slugify function."""
    
    def test_basic_slugify(self):
        """Test basic slugify functionality."""
        self.assertEqual(slugify("Hello World"), "hello-world")
        self.assertEqual(slugify("Hello World!"), "hello-world")
        self.assertEqual(slugify("  Hello   World  "), "hello-world")
    
    def test_special_characters(self):
        """Test slugify with special characters."""
        self.assertEqual(slugify("C++ Programming"), "c-programming")
        # Dots are removed (expected behavior - dots become hyphens then removed)
        self.assertEqual(slugify("Python 3.11"), "python-311")
        self.assertEqual(slugify("Test@#$%Content"), "testcontent")
    
    def test_empty_string(self):
        """Test slugify with empty string."""
        self.assertEqual(slugify(""), "section")
        self.assertEqual(slugify("   "), "section")


class TestExtractKeywords(unittest.TestCase):
    """Tests for extract_keywords function."""
    
    def test_basic_keywords(self):
        """Test basic keyword extraction."""
        content = "This is a test content with some important keywords here"
        keywords = extract_keywords(content, max_keywords=3)
        
        self.assertLessEqual(len(keywords), 3)
        # Should exclude short words like "this", "is", "a"
        self.assertTrue(all(len(kw) >= 4 for kw in keywords))
    
    def test_empty_content(self):
        """Test keyword extraction with empty content."""
        keywords = extract_keywords("", max_keywords=5)
        self.assertEqual(keywords, [])
    
    def test_single_word(self):
        """Test keyword extraction with single word."""
        keywords = extract_keywords("test", max_keywords=5)
        self.assertEqual(keywords, ["test"])
    
    def test_keyword_count(self):
        """Test keyword count is limited correctly."""
        content = "apple banana cherry date elderberry fig grape honeydew"
        keywords = extract_keywords(content, max_keywords=3)
        self.assertLessEqual(len(keywords), 3)


class TestInferCategory(unittest.TestCase):
    """Tests for infer_category function."""
    
    def test_session_category(self):
        """Test session category inference."""
        self.assertEqual(infer_category("Session 2026-02-13"), "session_log")
        self.assertEqual(infer_category("Chat Log"), "session_log")
    
    def test_documentation_category(self):
        """Test documentation category inference."""
        self.assertEqual(infer_category("Documentation"), "documentation")
        self.assertEqual(infer_category("User Guide"), "documentation")
    
    def test_general_category(self):
        """Test general category for unknown headings."""
        self.assertEqual(infer_category("Random Topic"), "general")
        self.assertEqual(infer_category("Some Random Heading"), "general")
    
    def test_project_category(self):
        """Test project category inference."""
        self.assertEqual(infer_category("Project Planning"), "project")
        self.assertEqual(infer_category("Feature Request"), "project")


class TestChunkMarkdown(unittest.TestCase):
    """Tests for chunk_markdown function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_md_content = """# Main Title

Some introduction content here.

## Section 1

This is the first section with some content.

## Section 2

This is the second section with different content.

### Subsection 2.1

A subsection under section 2.

## Section 3

Final section with more content.
"""
        self.test_file = "test.md"
    
    def test_splits_by_headings(self):
        """Test that markdown is split by ## headings."""
        chunks = chunk_markdown(self.test_md_content, self.test_file)
        
        # Should have at least one chunk (top-level)
        self.assertGreater(len(chunks), 0)
        
        # Check that chunks have proper IDs
        for chunk in chunks:
            self.assertIn(self.test_file, chunk.id)
            self.assertTrue(len(chunk.id) > len(self.test_file))
    
    def test_chunk_has_metadata(self):
        """Test that chunks have proper metadata."""
        chunks = chunk_markdown(self.test_md_content, self.test_file)
        
        self.assertGreater(len(chunks), 0)
        chunk = chunks[0]
        
        self.assertIsNotNone(chunk.heading)
        self.assertIsNotNone(chunk.content)
        self.assertIsNotNone(chunk.id)
        self.assertIsNotNone(chunk.category)
    
    def test_chunk_ids_are_unique(self):
        """Test that chunk IDs are unique."""
        chunks = chunk_markdown(self.test_md_content, self.test_file)
        chunk_ids = [c.id for c in chunks]
        
        self.assertEqual(len(chunk_ids), len(set(chunk_ids)),
                        "Chunk IDs should be unique")
    
    def test_content_is_preserved(self):
        """Test that content is preserved in chunks."""
        chunks = chunk_markdown(self.test_md_content, self.test_file)
        
        # Should have chunks for each heading
        chunk_headings = [c.heading for c in chunks]
        self.assertIn("Section 1", chunk_headings)
        self.assertIn("Section 2", chunk_headings)
        
        # Verify content exists in chunks
        combined_content = " ".join(c.content for c in chunks)
        self.assertIn("first section", combined_content)
        self.assertIn("second section", combined_content)
    
    def test_empty_content(self):
        """Test chunking with empty content."""
        chunks = chunk_markdown("", "test.md")
        self.assertEqual(chunks, [])
    
    def test_no_headings(self):
        """Test chunking with content that has no headings."""
        content = "Just some plain text without any headings."
        chunks = chunk_markdown(content, "test.md")
        
        # Should create one chunk for the entire content with default heading
        self.assertEqual(len(chunks), 1)
        # Default heading for no-heading content
        self.assertIn(chunks[0].heading, ["Top-Level Content", "Document"])
    
    def test_short_sections_merged(self):
        """Test that short sections are merged."""
        # Content with many short sections
        content = """# Title

## Short 1

A

## Short 2

B

## Short 3

C

## Longer

This is a longer section with more content.
"""
        chunks = chunk_markdown(content, "test.md", min_chunk_size=50)
        
        # After merging, should have fewer chunks
        self.assertLessEqual(len(chunks), 2)
    
    def test_non_markdown_fallback(self):
        """Test that non-markdown files fall back to whole document."""
        # Create a text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Some plain text content")
            temp_file = f.name
        
        try:
            chunks = chunk_markdown("Some plain text content", temp_file)
            # Should create one chunk for the entire content
            self.assertEqual(len(chunks), 1)
        finally:
            os.unlink(temp_file)


class TestChunkIntegration(unittest.TestCase):
    """Integration tests for chunk functionality."""
    
    def test_chunk_indexing_lifecycle(self):
        """Test the complete chunk indexing lifecycle."""
        content = """# Test Document

## First Section

This is the first section with important information.

## Second Section

This is the second section with different content.

### Subsection

Some subsection content here.
"""
        filepath = "test.md"
        
        # Chunk the content
        chunks = chunk_markdown(content, filepath)
        
        # Verify chunks were created
        self.assertGreater(len(chunks), 0)
        
        # Verify each chunk has required fields
        for chunk in chunks:
            self.assertIsInstance(chunk, ChunkMetadata)
            self.assertIn(filepath, chunk.parent_file)
            self.assertIsNotNone(chunk.id)
            self.assertIsNotNone(chunk.content)
            self.assertIsNotNone(chunk.category)
            self.assertIsNotNone(chunk.keywords)
            self.assertGreater(chunk.tokens, 0)
    
    def test_chunk_with_special_characters(self):
        """Test chunking with special characters in content."""
        # Use min_chunk_size=10 to prevent merging of short sections
        content = """# Test

## Section with quotes

Content with special chars: <>&"'

## Another Section

More content.
"""
        chunks = chunk_markdown(content, "test.md", min_chunk_size=10)
        
        # Should have 3 chunks (Top-Level + 2 sections)
        self.assertGreaterEqual(len(chunks), 2)
        # Verify chunks have proper headings
        chunk_headings = [c.heading for c in chunks]
        self.assertIn("Section with quotes", chunk_headings)
        self.assertIn("Another Section", chunk_headings)


def run_tests():
    """Run all tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestChunkMetadata))
    suite.addTests(loader.loadTestsFromTestCase(TestSlugify))
    suite.addTests(loader.loadTestsFromTestCase(TestExtractKeywords))
    suite.addTests(loader.loadTestsFromTestCase(TestInferCategory))
    suite.addTests(loader.loadTestsFromTestCase(TestChunkMarkdown))
    suite.addTests(loader.loadTestsFromTestCase(TestChunkIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == '__main__':
    print("=" * 60)
    print("Testing Chunk-Level Indexing")
    print("=" * 60)
    
    result = run_tests()
    
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")
        print(f"  Failures: {len(result.failures)}")
        print(f"  Errors: {len(result.errors)}")
    print("=" * 60)
    
    sys.exit(0 if result.wasSuccessful() else 1)
