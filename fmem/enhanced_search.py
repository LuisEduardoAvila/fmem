#!/usr/bin/env python3
"""
Enhanced fmem search with location-based ranking
Combines semantic similarity, recency, and file location importance.
"""

import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

# Add workspace to path
workspace = os.path.dirname(os.path.abspath(__file__))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

from fmem import MemoryRetrieval

# Location-based importance weights
LOCATION_WEIGHTS = {
    # High importance - formal documentation and decisions
    '/docs/': 1.5,
    '/documentation/': 1.5,
    '/projects/': 1.3,
    '/decisions/': 1.4,
    '/formal/': 1.4,
    
    # Medium importance - active working files
    '/work/': 1.2,
    '/active/': 1.2,
    '/current/': 1.1,
    '/notes/': 1.0,
    '/memory/': 1.0,
    
    # Lower importance - casual/conversational content
    '/chats/': 0.8,
    '/conversations/': 0.8,
    '/daily/': 0.9,
    '/sessions/': 0.9,
    
    # Base importance
    '/': 1.0
}

def get_file_location_weight(filepath: str) -> float:
    """Calculate importance weight based on file location."""
    normalized_path = os.path.normpath(filepath)
    path_parts = normalized_path.split(os.sep)
    
    for pattern, weight in LOCATION_WEIGHTS.items():
        if pattern.startswith('/'):
            pattern_parts = pattern.strip('/').split('/')
            if len(path_parts) >= len(pattern_parts):
                if path_parts[-len(pattern_parts):] == pattern_parts:
                    return weight
        else:
            if any(pattern in part for part in path_parts):
                return weight
    
    return 1.0

def enhance_search_results_with_location(results: List[Dict], mr: MemoryRetrieval) -> List[Dict]:
    """
    Apply location-based ranking enhancement to search results.
    
    Args:
        results: Original search results from FAISS
        mr: MemoryRetrieval instance for configuration access
        
    Returns:
        Enhanced results with location-adjusted scores
    """
    if not results:
        return results
    
    enhanced_results = []
    
    for result in results:
        filepath = result['filepath']
        
        # Get location weight
        location_weight = get_file_location_weight(filepath)
        
        # Get existing scores
        semantic_score = result.get('semantic_score', result['score'])
        recency_score = result.get('recency_score', 1.0)
        
        # Apply enhanced scoring with configurable weights (use CONFIG defaults as fallback)
        from fmem import CONFIG
        location_weight_config = getattr(mr.config, 'location_weight', CONFIG.DEFAULT_LOCATION_WEIGHT)
        
        # Hybrid scoring: semantic * (1 - recency_weight - location_weight) + recency * recency_weight + location * location_weight
        remaining_weight = 1.0 - mr.config.recency_weight - location_weight_config
        enhanced_score = (
            semantic_score * remaining_weight +
            recency_score * mr.config.recency_weight +
            location_weight * location_weight_config
        )
        
        # Create enhanced result
        enhanced_result = result.copy()
        enhanced_result['score'] = enhanced_score
        enhanced_result['semantic_score'] = semantic_score
        enhanced_result['recency_score'] = recency_score
        enhanced_result['location_weight'] = location_weight
        enhanced_result['location_score'] = location_weight
        enhanced_result['enhanced'] = True
        
        enhanced_results.append(enhanced_result)
    
    # Sort by enhanced score
    enhanced_results.sort(key=lambda x: x['score'], reverse=True)
    
    return enhanced_results

def format_enhanced_result(result: Dict, index: int) -> str:
    """Format a single enhanced result for display."""
    filepath = result['filepath']
    filename = os.path.basename(filepath)
    
    output = f"[{index}] Score: {result['score']:.3f}"
    output += f"\n    File: {filepath}"
    
    # Show individual score components if available
    if 'semantic_score' in result:
        output += f"\n    Components: Semantic={result['semantic_score']:.3f}"
    if 'recency_score' in result:
        output += f", Recency={result['recency_score']:.3f}"
    if 'location_score' in result:
        output += f", Location={result['location_score']:.3f}"
    
    # Show preview
    content = result.get('content', '')
    if len(content) > 200:
        preview = content[:200] + "..."
    else:
        preview = content
    
    output += f"\n    Preview: {preview}"
    
    return output

def main():
    """Main search function."""
    import argparse
    import time
    
    parser = argparse.ArgumentParser(
        "Enhanced fmem search with location-based ranking",
        description="Search memory using semantic similarity + recency + location importance"
    )
    
    parser.add_argument('query', help='Search query')
    parser.add_argument('-k', '--top-k', type=int, default=5, help='Number of results (default: 5)')
    parser.add_argument('--quiet', action='store_true', help='Suppress non-result output')
    parser.add_argument('--show-location', action='store_true', help='Show location weights in output')
    
    args = parser.parse_args()
    
    # Validate query
    if not args.query or not args.query.strip():
        print("Error: Query cannot be empty")
        return 1
    
    # Initialize memory system
    try:
        mr = MemoryRetrieval()
    except Exception as e:
        print(f"[ERROR] Failed to initialize MemoryRetrieval: {e}")
        return 1
    
    # Perform search
    if not args.quiet:
        print(f"\nEnhanced Search: '{args.query}' (top-{args.top_k})")
        print("Ranking: Semantic + Recency + Location Importance")
        print("=" * 80)
    
    start_time = time.time()
    results = mr.search(args.query, top_k=args.top_k)
    search_time = time.time() - start_time
    
    # Apply location enhancement
    enhanced_results = enhance_search_results_with_location(results, mr)
    
    # Display results
    if not enhanced_results:
        if not args.quiet:
            print("No results found")
        return 0
    
    for i, result in enumerate(enhanced_results, 1):
        if not args.quiet:
            print(format_enhanced_result(result, i))
            print()
    
    # Summary
    if not args.quiet:
        print("=" * 80)
        print(f"Enhanced search completed in {search_time:.3f}s")
        print(f"Found {len(enhanced_results)} results")
        
        # Show score distribution
        if len(enhanced_results) > 1:
            scores = [r['score'] for r in enhanced_results]
            print(f"Score range: {min(scores):.3f} - {max(scores):.3f}")
        
        # Show location weights if requested
        if args.show_location:
            print("\nLocation weight distribution:")
            for result in enhanced_results:
                location_weight = result.get('location_score', 1.0)
                filename = os.path.basename(result['filepath'])
                print(f"  {filename}: {location_weight:.1f}x")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())