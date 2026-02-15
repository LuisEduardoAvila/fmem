#!/usr/bin/env python3
"""
Test location-based ranking functionality
"""

import sys
import os
from datetime import datetime, timedelta

# Add workspace to path
workspace = os.path.dirname(os.path.abspath(__file__))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

from fmem import MemoryRetrieval

def test_location_ranking():
    """Test the location-based ranking functionality."""
    print("Testing fmem location-based ranking...")
    
    try:
        mr = MemoryRetrieval()
        print(f"✓ MemoryRetrieval initialized with {len(mr.doc_metadata)} documents")
        
        # Test configuration
        print(f"✓ Location ranking enabled: {mr.config.enable_location_ranking}")
        print(f"✓ Location weight: {mr.config.location_weight}")
        print(f"✓ Recency ranking enabled: {mr.config.enable_recency_ranking}")
        print(f"✓ Recency weight: {mr.config.recency_weight}")
        
        # Test location weight calculation
        print("\nTesting location weight calculation:")
        
        test_files = [
            "/home/luis/.openclaw/workspace/MEMORY.md",
            "/home/luis/.openclaw/workspace/docs/formal-doc.md",
            "/home/luis/.openclaw/workspace/projects/project-decision.md",
            "/home/luis/.openclaw/workspace/chats/casual-chat.md",
            "/home/luis/.openclaw/workspace/memory/session-log.md"
        ]
        
        for filepath in test_files:
            location_weight = mr._calculate_location_weight(filepath)
            filename = os.path.basename(filepath)
            print(f"  {filename}: {location_weight:.1f}x")
        
        # Test search with enhancement
        print("\nTesting search with multi-factor enhancement:")
        results = mr.search("test", top_k=3)
        
        for i, result in enumerate(results, 1):
            print(f"[{i}] {result['filepath']}")
            if 'semantic_score' in result and 'recency_score' in result and 'location_score' in result:
                print(f"    Semantic: {result['semantic_score']:.3f}")
                print(f"    Recency: {result['recency_score']:.3f}")
                print(f"    Location: {result['location_score']:.3f}")
                print(f"    Enhanced: {result['score']:.3f}")
            else:
                print(f"    Score: {result['score']:.3f}")
        
        print("\n✓ Location ranking test completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_location_ranking()
    sys.exit(0 if success else 1)