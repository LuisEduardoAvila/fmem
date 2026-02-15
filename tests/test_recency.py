#!/usr/bin/env python3
"""
Test recency enhancement functionality
"""

import sys
import os
from datetime import datetime, timedelta

# Add workspace to path
workspace = os.path.dirname(os.path.abspath(__file__))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

from fmem import MemoryRetrieval

def test_recency_enhancement():
    """Test the recency enhancement functionality."""
    print("Testing fmem recency enhancement...")
    
    try:
        mr = MemoryRetrieval()
        print(f"✓ MemoryRetrieval initialized with {len(mr.doc_metadata)} documents")
        
        # Test configuration
        print(f"✓ Recency ranking enabled: {mr.config.enable_recency_ranking}")
        print(f"✓ Recency weight: {mr.config.recency_weight}")
        print(f"✓ Recency threshold: {mr.config.recency_threshold_days} days")
        print(f"✓ Minimum recency score: {mr.config.min_recency_score}")
        
        # Test recency calculation
        print("\nTesting recency score calculation:")
        
        # Create test timestamps
        now = datetime.now().timestamp()
        recent_time = now - (24 * 60 * 60)  # 1 day ago
        old_time = now - (15 * 24 * 60 * 60)  # 15 days ago
        very_old_time = now - (60 * 24 * 60 * 60)  # 60 days ago
        
        recent_score = mr._calculate_recency_score(recent_time)
        old_score = mr._calculate_recency_score(old_time)
        very_old_score = mr._calculate_recency_score(very_old_time)
        
        print(f"Recent document (1 day old): {recent_score:.3f}")
        print(f"Old document (15 days old): {old_score:.3f}")
        print(f"Very old document (60 days old): {very_old_score:.3f}")
        
        # Test search with enhancement
        print("\nTesting search with recency enhancement:")
        results = mr.search("test", top_k=3)
        
        for i, result in enumerate(results, 1):
            print(f"[{i}] {result['filepath']}")
            if 'semantic_score' in result and 'recency_score' in result:
                print(f"    Semantic: {result['semantic_score']:.3f}")
                print(f"    Recency: {result['recency_score']:.3f}")
                print(f"    Enhanced: {result['score']:.3f}")
            else:
                print(f"    Score: {result['score']:.3f}")
        
        print("\n✓ Recency enhancement test completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_recency_enhancement()
    sys.exit(0 if success else 1)