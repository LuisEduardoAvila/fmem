#!/usr/bin/env python3
"""
OpenClaw Chat Integration for fmem
Provides automatic memory recall triggered by conversational cues.

Usage in agent:
    from fmem_integration import auto_recall, should_search
    
    if should_search(user_message):
        results = auto_recall(user_message)
        context += format_results(results)
"""

import re
import os
import sys

# Add DarthSpud to path
workspace = os.environ.get('FMEM_WORKSPACE', '/home/luis/.openclaw/workspace')
darthspud_dir = os.path.join(workspace, 'DarthSpud')
if darthspud_dir not in sys.path:
    sys.path.insert(0, darthspud_dir)

from fmem import MemoryRetrieval

# Singleton memory instance
_memory = None

def get_memory():
    """Get or create memory instance."""
    global _memory
    if _memory is None:
        _memory = MemoryRetrieval()
    return _memory

# Search trigger patterns
SEARCH_TRIGGERS = {
    'explicit': [
        r'\b(look up|find|search|recall|remember)\b',
        r'\b(what (did|was|were)|when did)\b',
        r'\b(show me|tell me about)\b',
    ],
    'recency': [
        r'\b(last|recent|previous|earlier)\s+(week|month|day|session|conversation)\b',
        r'\b(yesterday|before|recently)\b',
    ],
    'location': [
        r'\b(in|under|from)\s+([\w-]+/[\w-]+)',  # Path-like reference
        r'\b(docs|projects|notes|memory|personas)\b',
    ],
    'context': [
        r'\b(my|our)\s+(preferences|settings|goals|projects)\b',
        r'\b(Luis|workspace|setup)\b',
    ],
}

def should_search(message: str) -> bool:
    """
    Determine if a message should trigger memory search.
    
    Args:
        message: User message text
        
    Returns:
        True if search should be triggered
    """
    message_lower = message.lower()
    
    for category, patterns in SEARCH_TRIGGERS.items():
        for pattern in patterns:
            if re.search(pattern, message_lower):
                return True
    
    return False

def extract_search_query(message: str) -> str:
    """
    Extract relevant search terms from message.
    
    Args:
        message: User message text
        
    Returns:
        Extracted search query
    """
    # Remove common filler words
    filler = r'\b(please|can you|could you|would you|i want to|i need|i\'d like)\b'
    cleaned = re.sub(filler, '', message.lower(), flags=re.IGNORECASE)
    
    # Extract key content words
    words = re.findall(r'\b[a-z]{3,}\b', cleaned)
    
    # Take meaningful words
    query = ' '.join(words[:10])  # Limit to 10 words
    
    return query if query else message

def get_search_bias(message: str) -> str:
    """
    Determine search bias based on message content.
    
    Args:
        message: User message text
        
    Returns:
        'recency', 'location', or 'semantic'
    """
    message_lower = message.lower()
    
    # Check for recency triggers
    for pattern in SEARCH_TRIGGERS['recency']:
        if re.search(pattern, message_lower):
            return 'recency'
    
    # Check for location triggers
    for pattern in SEARCH_TRIGGERS['location']:
        if re.search(pattern, message_lower):
            return 'location'
    
    return 'semantic'

def auto_recall(message: str, top_k: int = 3) -> list:
    """
    Perform automatic memory recall based on message.
    
    Args:
        message: User message to analyze
        top_k: Number of results to return
        
    Returns:
        List of search results with enhanced scoring
    """
    memory = get_memory()
    
    # Check if we have documents
    if memory.get_document_count() == 0:
        return []
    
    # Extract query
    query = extract_search_query(message)
    
    # Get search bias
    bias = get_search_bias(message)
    
    # Adjust weights based on bias
    if bias == 'recency':
        # Temporarily boost recency weight
        original_recency = memory.config.recency_weight
        memory.config.recency_weight = min(0.5, original_recency + 0.2)
        results = memory.search(query, top_k=top_k)
        memory.config.recency_weight = original_recency
    elif bias == 'location':
        # Temporarily boost location weight
        original_location = memory.config.location_weight
        memory.config.location_weight = min(0.4, original_location + 0.1)
        results = memory.search(query, top_k=top_k)
        memory.config.location_weight = original_location
    else:
        results = memory.search(query, top_k=top_k)
    
    return results

def format_results(results: list, max_preview: int = 200) -> str:
    """
    Format search results for context injection with clear memory tags.
    
    Args:
        results: List of search results
        max_preview: Maximum preview length
        
    Returns:
        Formatted string for context
    """
    if not results:
        return ""
    
    output = ["\n<retrieved_memory>"]
    output.append("📝 The following is retrieved from your long-term memory (previous interactions, notes, and preferences).")
    output.append("This context helps inform the current conversation but may not reflect recent updates.\n")
    
    for i, r in enumerate(results[:3], 1):
        filepath = r['filepath']
        filename = os.path.basename(filepath)
        dirname = os.path.basename(os.path.dirname(filepath)) if '/' in filepath else ''
        
        # Get preview
        content = r.get('content', '')
        preview = content[:max_preview] + "..." if len(content) > max_preview else content
        
        # Format scores if available
        scores = ""
        if 'semantic_score' in r:
            scores = f" | relevance={r['semantic_score']:.2f}"
            if 'recency_score' in r:
                scores += f", recency={r['recency_score']:.2f}"
        
        location_label = f"[{dirname}/]" if dirname else ""
        output.append(f"<memory_item index=\"{i}\" source=\"{location_label}{filename}\"{scores}>")
        output.append(preview.strip())
        output.append(f"</memory_item>")
    
    output.append("</retrieved_memory>")
    
    return "\n".join(output)

def get_context_for_message(message: str, top_k: int = 3) -> str:
    """
    Main entry point: Get formatted context for a message.
    
    Args:
        message: User message to process
        top_k: Number of results
        
    Returns:
        Formatted context string (empty if no relevant memories)
    """
    if not should_search(message):
        return ""
    
    results = auto_recall(message, top_k)
    return format_results(results)


# CLI for testing
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser("fmem chat integration")
    parser.add_argument('message', help='Test message to analyze')
    parser.add_argument('--check', action='store_true', help='Only check if search triggered')
    parser.add_argument('--search', action='store_true', help='Perform search')
    
    args = parser.parse_args()
    
    if args.check:
        triggered = should_search(args.message)
        bias = get_search_bias(args.message) if triggered else 'none'
        print(f"Search triggered: {triggered}")
        print(f"Bias: {bias}")
    elif args.search:
        results = auto_recall(args.message)
        print(format_results(results))
    else:
        context = get_context_for_message(args.message)
        print(context if context else "No relevant memories found")