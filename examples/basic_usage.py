#!/usr/bin/env python3
"""
fmem Basic Usage Example

This example demonstrates the core functionality of the fmem memory search system.
"""

import sys
import os

# Add src to path to import fmem
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fmem import MemoryRetrieval

def main():
    """Demonstrate basic fmem functionality."""
    print("=== fmem Basic Usage Example ===")
    
    # Initialize memory retrieval system
    print("Initializing memory retrieval system...")
    memory = MemoryRetrieval()
    
    # Check if we have any documents
    doc_count = memory.get_document_count() if hasattr(memory, 'get_document_count') else 0
    print(f"Current documents in memory: {doc_count}")
    
    # Example search
    if doc_count > 0:
        print("\nPerforming example search...")
        results = memory.search("memory preferences", top_k=3)
        
        print(f"\nFound {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"{i}. [{result.get('score', 0):.3f}] {result.get('filepath', 'Unknown')}")
            if 'content' in result:
                content_preview = result['content'][:100] + "..." if len(result['content']) > 100 else result['content']
                print(f"   Preview: {content_preview}")
    else:
        print("\nNo documents found. Add some files to test searching.")
    
    print("\n=== Example Complete ===")

if __name__ == "__main__":
    main()