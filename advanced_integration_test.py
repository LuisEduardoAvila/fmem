#!/usr/bin/env python3
"""
Advanced integration and edge case testing for chunk-level indexing.

Tests more complex scenarios and potential edge cases that could reveal defects.
"""

import sys
import os
import shutil
import tempfile
import time

# Add workspace to path
workspace = os.path.dirname(os.path.abspath(__file__))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

from fmem import chunk_markdown, MemoryRetrieval, CONFIG
from fmem_integration import auto_recall, get_context_for_message, should_search

def test_database_integrity():
    """Test database integrity under various operations."""
    print("\n=== Advanced Test 1: Database Integrity ===")
    
    # Create temp database
    temp_db = os.path.join(tempfile.gettempdir(), f"test_integrity_{int(time.time())}.db")
    
    memory = MemoryRetrieval(db_path=temp_db)
    
    # Add multiple documents
    test_docs = [
        ("doc1.md", "# Document 1\n\n## Section A\n\nContent A\n\n## Section B\n\nContent B"),
        ("doc2.md", "# Document 2\n\n## Section X\n\nContent X"),
        ("doc3.py", "# Python file\nprint('hello')"),
    ]
    
    for filepath, content in test_docs:
        memory.add_document(filepath, content=content)
    
    # Verify counts
    cursor = memory.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM chunks")
    chunk_count = cursor.fetchone()[0]
    print(f"Added {len(test_docs)} documents, {chunk_count} chunks")
    
    # Test chunk retrieval
    cursor.execute("SELECT chunk_id, heading FROM chunks LIMIT 5")
    chunks = cursor.fetchall()
    print(f"Retrieved {len(chunks)} chunks from database")
    
    # Verify each chunk has required fields
    for chunk in chunks:
        cursor.execute("SELECT * FROM chunks WHERE chunk_id = ?", (chunk[0],))
        full_chunk = cursor.fetchone()
        required_fields = ['chunk_id', 'parent_file', 'heading', 'content', 
                          'keywords', 'category', 'token_count', 'chunk_index']
        for field in required_fields:
            assert field in full_chunk.keys(), f"Missing field: {field}"
    
    # Cleanup
    if os.path.exists(temp_db):
        os.remove(temp_db)
    
    print("✓ Database integrity test passed")
    return True

def test_search_with_no_results():
    """Test search behavior when no results match."""
    print("\n=== Advanced Test 2: Search with No Results ===")
    
    memory = MemoryRetrieval()
    
    # Search for term unlikely to match
    results = memory.search("zzzxyz123nonexistent", top_k=5, chunk_mode="chunk")
    
    print(f"Search for 'zzzxyz123nonexistent' returned {len(results)} results")
    
    # Should return empty list, not crash
    assert isinstance(results, list), "Should return list even when no results"
    
    print("✓ No-results search test passed")
    return True

def test_large_file_handling():
    """Test handling of large files."""
    print("\n=== Advanced Test 3: Large File Handling ===")
    
    # Create a large markdown file
    large_content = "# Large Document\n\n"
    for i in range(100):
        large_content += f"## Section {i}\n\n"
        large_content += f"Content for section {i} with some additional text to make it longer.\n"
        large_content += f"More content here to ensure we have enough tokens.\n\n"
    
    # Chunk it
    chunks = chunk_markdown(large_content, "large.md")
    
    print(f"Large file ({len(large_content)} chars) split into {len(chunks)} chunks")
    
    # Verify chunks are reasonable size
    for i, chunk in enumerate(chunks):
        assert len(chunk.content) > 0, f"Chunk {i} should have content"
        assert chunk.tokens > 0, f"Chunk {i} should have positive tokens"
    
    print(f"✓ Large file handling test passed ({len(chunks)} chunks)")
    return True

def test_special_markdown_content():
    """Test special markdown content handling."""
    print("\n=== Advanced Test 4: Special Markdown Content ===")
    
    test_cases = [
        ("Empty headings", "# Title\n\n## \n\nContent"),
        ("Multiple consecutive headings", "# Title\n\n## A\n\nB\n\n## C\n\nD"),
        ("Code blocks", "# Title\n\n## Code\n\n```\ndef hello(): pass\n```"),
        ("Tables", "# Title\n\n## Table\n\n| A | B |\n|---|---|\n| 1 | 2 |"),
        ("Links and images", "# Title\n\n## Links\n\n[Link](http://example.com)"),
        ("Math expressions", "# Title\n\n## Math\n\n$$E=mc^2$$"),
    ]
    
    for name, content in test_cases:
        try:
            chunks = chunk_markdown(content, f"special_{name.replace(' ', '_')}.md")
            print(f"  ✓ {name}: {len(chunks)} chunk(s)")
        except Exception as e:
            print(f"  ✗ {name}: {e}")
            return False
    
    print("✓ Special markdown content test passed")
    return True

def test_memory_retrieval_consistency():
    """Test that MemoryRetrieval behaves consistently across multiple instances."""
    print("\n=== Advanced Test 5: Memory Retrieval Consistency ===")
    
    # Create two instances
    mem1 = MemoryRetrieval()
    mem2 = MemoryRetrieval()
    
    # Both should see same document count
    count1 = mem1.get_document_count()
    count2 = mem2.get_document_count()
    
    print(f"Instance 1: {count1} documents")
    print(f"Instance 2: {count2} documents")
    
    assert count1 == count2, "Multiple instances should see same document count"
    
    # Test search consistency
    results1 = mem1.search("user", top_k=3)
    results2 = mem2.search("user", top_k=3)
    
    assert len(results1) == len(results2), "Search results should be consistent"
    
    print("✓ Memory retrieval consistency test passed")
    return True

def test_chunk_overlap_and_context():
    """Test chunk overlap and context handling."""
    print("\n=== Advanced Test 6: Chunk Context Handling ===")
    
    content = """# Main Document

## First Section
This is the first section with important context.

### Subsection 1.1
This is a subsection with related content.

### Subsection 1.2
Another related subsection.

## Second Section
This section is different from the first.

### Subsection 2.1
Details about the second section.
"""
    
    chunks = chunk_markdown(content, "context.md")
    
    print(f"Created {len(chunks)} chunks")
    
    # Verify hierarchy is preserved
    headings = [c.heading for c in chunks]
    print(f"Headings: {headings}")
    
    # Verify headings are preserved (headings are in heading field, not content)
    assert "First Section" in headings, "Main section headings should be in chunks"
    assert "Subsection 1.1" in headings, "Subsection headings should be in chunks"
    assert "Second Section" in headings, "Main section headings should be in chunks"
    
    # Verify content is preserved (not headings - those are in the headings list)
    combined = " ".join(c.content for c in chunks)
    assert "important context" in combined.lower(), "Section content should be in chunks"
    
    print("✓ Chunk context handling test passed")
    return True

def test_integration_with_chat():
    """Test integration with chat memory recall."""
    print("\n=== Advanced Test 7: Chat Integration ===")
    
    # Test search triggers
    test_messages = [
        ("Find my preferences", True),
        ("What did we discuss yesterday?", True),
        ("Look up the documentation", True),
        ("Hello there", False),
        ("How are you?", False),
    ]
    
    for message, should_trigger in test_messages:
        triggered = should_search(message)
        status = "✓" if triggered == should_trigger else "✗"
        print(f"  {status} '{message}' -> triggered={triggered} (expected={should_trigger})")
        
        if triggered != should_trigger:
            print(f"    FAILED: Expected {should_trigger}, got {triggered}")
            return False
    
    print("✓ Chat integration test passed")
    return True

def test_persistence_across_sessions():
    """Test that indexed data persists across MemoryRetrieval instances."""
    print("\n=== Advanced Test 8: Persistence Across Sessions ===")
    
    # Get current state
    mem1 = MemoryRetrieval()
    count_before = mem1.get_document_count()
    
    # Create new instance
    mem2 = MemoryRetrieval()
    count_after = mem2.get_document_count()
    
    print(f"Instance 1: {count_before} documents")
    print(f"Instance 2: {count_after} documents")
    
    assert count_before == count_after, "Documents should persist across instances"
    
    print("✓ Persistence test passed")
    return True

def test_error_handling():
    """Test error handling for invalid inputs."""
    print("\n=== Advanced Test 9: Error Handling ===")
    
    memory = MemoryRetrieval()
    
    # Test with empty query
    try:
        results = memory.search("", top_k=5)
        print(f"  ✓ Empty query handled: {len(results)} results")
    except Exception as e:
        print(f"  ✗ Empty query failed: {e}")
        return False
    
    # Test with None query
    try:
        # This should handle gracefully
        results = memory.search(None, top_k=5) if hasattr(memory, 'search') else []
        print(f"  ✓ None query handled")
    except Exception as e:
        print(f"  ✗ None query failed: {e}")
        return False
    
    # Test with negative top_k
    try:
        results = memory.search("test", top_k=-1)
        print(f"  ✓ Negative top_k handled: {len(results)} results")
    except Exception as e:
        print(f"  Note: Negative top_k raises exception: {e}")
    
    print("✓ Error handling test passed")
    return True

def test_chunk_metadata_fields():
    """Test that all chunk metadata fields are populated correctly."""
    print("\n=== Advanced Test 10: Chunk Metadata Fields ===")
    
    content = "# Test\n\n## Section\n\nContent here"
    chunks = chunk_markdown(content, "metadata_test.md")
    
    required_fields = ['chunk_id', 'parent_file', 'heading', 'content', 
                      'keywords', 'category', 'tokens', 'chunk_index']
    
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i+1}:")
        print(f"  ID: {chunk.id}")
        print(f"  Heading: {chunk.heading}")
        print(f"  Category: {chunk.category}")
        print(f"  Keywords: {chunk.keywords}")
        print(f"  Tokens: {chunk.tokens}")
        print(f"  Index: {chunk.chunk_index}")
        
        # Verify all required fields
        for field in required_fields:
            if field == 'chunk_id':
                assert hasattr(chunk, 'id'), f"Missing field: id"
            else:
                assert hasattr(chunk, field), f"Missing field: {field}"
        
        # Verify values are reasonable
        assert len(chunk.id) > len(chunk.parent_file), "ID should include parent file"
        assert chunk.tokens > 0, "Tokens should be positive"
        assert chunk.chunk_index >= 0, "Chunk index should be non-negative"
    
    print("\n✓ Chunk metadata fields test passed")
    return True

def run_all_tests():
    """Run all advanced integration tests."""
    print("=" * 60)
    print("Advanced Integration & Edge Case Testing")
    print("=" * 60)
    
    tests = [
        ("Database Integrity", test_database_integrity),
        ("Search with No Results", test_search_with_no_results),
        ("Large File Handling", test_large_file_handling),
        ("Special Markdown Content", test_special_markdown_content),
        ("Memory Retrieval Consistency", test_memory_retrieval_consistency),
        ("Chunk Context Handling", test_chunk_overlap_and_context),
        ("Chat Integration", test_integration_with_chat),
        ("Persistence Across Sessions", test_persistence_across_sessions),
        ("Error Handling", test_error_handling),
        ("Chunk Metadata Fields", test_chunk_metadata_fields),
    ]
    
    results = {
        'passed': 0,
        'failed': 0,
        'errors': []
    }
    
    for name, test_func in tests:
        try:
            if test_func():
                results['passed'] += 1
            else:
                results['failed'] += 1
                results['errors'].append(f"{name}: Test returned False")
                print(f"✗ {name} FAILED")
        except Exception as e:
            results['failed'] += 1
            results['errors'].append(f"{name}: {str(e)}")
            print(f"✗ {name} FAILED with exception: {e}")
    
    return results

def write_detailed_report(results):
    """Write detailed defect report."""
    report = []
    
    report.append("# Advanced Integration & Edge Case Test Report")
    report.append("")
    report.append("## Summary")
    report.append("")
    report.append(f"- **Tests Run**: {results['passed'] + results['failed']}")
    report.append(f"- **Passed**: {results['passed']}")
    report.append(f"- **Failed**: {results['failed']}")
    report.append(f"- **Pass Rate**: {(results['passed'])/(results['passed']+results['failed'])*100:.0f}%")
    report.append("")
    
    if results['errors']:
        report.append("## Defects Found")
        report.append("")
        for i, error in enumerate(results['errors'], 1):
            report.append(f"### Defect #{i}")
            report.append("")
            report.append(f"**Name**: {error.split(':')[0]}")
            report.append(f"**Error**: {':'.join(error.split(':')[1:]).strip()}")
            report.append("")
            report.append("**Reproduction Steps**:")
            report.append("1. Run advanced integration tests")
            report.append("2. Observe failure in affected test")
            report.append("")
    
    report.append("## Test Details")
    report.append("")
    
    test_details = [
        ("Database Integrity", "Verifies SQLite storage under various operations"),
        ("Search with No Results", "Tests search behavior when no matches found"),
        ("Large File Handling", "Tests chunking of 100+ section documents"),
        ("Special Markdown Content", "Tests edge cases in markdown parsing"),
        ("Memory Retrieval Consistency", "Verifies multiple instances see same data"),
        ("Chunk Context Handling", "Tests hierarchical heading preservation"),
        ("Chat Integration", "Tests search trigger detection"),
        ("Persistence Across Sessions", "Verifies data persists between instances"),
        ("Error Handling", "Tests invalid input handling"),
        ("Chunk Metadata Fields", "Verifies all required fields are populated"),
    ]
    
    for name, desc in test_details:
        report.append(f"### {name}")
        report.append("")
        report.append(f"{desc}")
        report.append("")
    
    report.append("---")
    report.append("*Report generated by advanced_integration_test.py*")
    
    report_path = os.path.join(workspace, "ADVANCED_TEST_REPORT.md")
    with open(report_path, 'w') as f:
        f.write("\n".join(report))
    
    print(f"\n✓ Detailed report written to {report_path}")
    return report_path

if __name__ == '__main__':
    results = run_all_tests()
    
    print("\n" + "=" * 60)
    print("Advanced Test Results")
    print("=" * 60)
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    
    if results['errors']:
        print("\nErrors:")
        for error in results['errors']:
            print(f"  - {error}")
    
    print("\n" + "=" * 60)
    if results['failed'] == 0:
        print("✓ All advanced integration tests passed!")
    else:
        print("✗ Some advanced integration tests failed")
    print("=" * 60)
    
    # Write report
    write_detailed_report(results)
    
    sys.exit(0 if results['failed'] == 0 else 1)