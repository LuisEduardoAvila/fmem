#!/usr/bin/env python3
"""
Quick test for fmem skill
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fmem import MemoryRetrieval

def test_basic():
    """Test basic initialization"""
    print("Test 1: Basic initialization")
    try:
        memory = MemoryRetrieval()
        print("✓ MemoryRetrieval initialized")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

def test_add_and_search():
    """Test adding content and searching"""
    print("\nTest 2: Add and search")
    try:
        memory = MemoryRetrieval()

        # Add test document
        test_content = """# Test Memory Document

This is a test document for fmem skill.

Luis's favorite technology is Oracle EPM.
Favorite movie is 911.
"""

        memory.add_document("/tmp/test_memory.md", test_content)

        print(f"✓ Added {len(memory.doc_metadata)} documents")

        # Search
        results = memory.search("Oracle EPM", top_k=2)

        print(f"✓ Found {len(results)} results")
        for r in results:
            print(f"    [Score: {r['score']:.3f}] {r['filepath']}")

        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    os.makedirs("/tmp", exist_ok=True)

    # Run tests
    passed = []
    passed.append(test_basic())
    passed.append(test_add_and_search())

    print(f"\n{'='*50}")
    print(f"Tests passed: {sum(passed)}/{len(passed)}")

    if all(passed):
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")
        sys.exit(1)