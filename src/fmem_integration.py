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
import time
import logging
from typing import Set, Dict

# Set up logging first
logger = logging.getLogger(__name__)

# Get workspace from environment variable with proper fallback
workspace = os.environ.get('FMEM_WORKSPACE')
if not workspace:
    # Use default fallback path
    workspace = os.path.expanduser('~/.fmem/workspace')
    logger.warning(f"FMEM_WORKSPACE not set, using fallback: {workspace}")

# Add workspace to path if not already present
if workspace not in sys.path:
    sys.path.insert(0, workspace)

from fmem import MemoryRetrieval

# Singleton memory instance
_memory = None

# Session-level deduplication
_session_recalled: Dict[str, float] = {}  # filepath -> timestamp
_dedupe_ttl_seconds = 300  # 5 minutes before allowing re-recall

# Relevance threshold - filter out low-quality results
MIN_RELEVANCE_SCORE = 0.25

def get_memory():
    """Get or create memory instance with error handling."""
    global _memory
    if _memory is None:
        try:
            _memory = MemoryRetrieval()
        except Exception as e:
            logger.error(f"Failed to initialize memory: {e}")
            _memory = None
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

def auto_recall(message: str, top_k: int = 3, chunk_mode: str = "chunk") -> list:
    """
    Perform automatic memory recall based on message with graceful degradation.
    
    Args:
        message: User message to analyze
        top_k: Number of results to return
        chunk_mode: How to return results ("chunk", "document", or "hybrid")
        
    Returns:
        List of search results with enhanced scoring, or empty list on error
    """
    try:
        memory = get_memory()
        
        # Check if we have documents
        if memory is None or memory.get_document_count() == 0:
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
            results = memory.search(query, top_k=top_k + 2, chunk_mode=chunk_mode)
            memory.config.recency_weight = original_recency
        elif bias == 'location':
            # Temporarily boost location weight
            original_location = memory.config.location_weight
            memory.config.location_weight = min(0.4, original_location + 0.1)
            results = memory.search(query, top_k=top_k + 2, chunk_mode=chunk_mode)
            memory.config.location_weight = original_location
        else:
            results = memory.search(query, top_k=top_k + 2, chunk_mode=chunk_mode)
        
        # Filter by relevance threshold
        results = [r for r in results if r.get('score', 0) >= MIN_RELEVANCE_SCORE]
        
        # Deduplicate: remove recently recalled files
        now = time.time()
        filtered = []
        for r in results:
            filepath = r.get('filepath', '')
            last_recalled = _session_recalled.get(filepath, 0)
            
            # Include if not recently recalled (TTL expired or never recalled)
            if now - last_recalled > _dedupe_ttl_seconds:
                filtered.append(r)
                _session_recalled[filepath] = now
        
        return filtered[:top_k]
        
    except Exception as e:
        # Graceful degradation: log error and return empty list instead of crashing
        logger.warning(f"Memory recall failed (degraded): {e}")
        return []

def format_results(results: list, max_preview: int = 200, chunk_mode: str = "chunk") -> str:
    """
    Format search results for context injection with clear memory tags.
    Uses adaptive preview length based on result count.
    
    Args:
        results: List of search results
        max_preview: Maximum preview length (adjusted adaptively)
        chunk_mode: How to format results:
                   - "chunk": Format individual chunks
                   - "document": Format full documents
                   - "hybrid": Combine chunks with parent documents
        
    Returns:
        Formatted string for context
    """
    try:
        if not results:
            return ""
        
        # Adaptive preview: more space for single result, less for many
        result_count = len(results)
        if result_count == 1:
            adaptive_preview = 400  # Deep dive into single result
        elif result_count == 2:
            adaptive_preview = 250  # Balanced
        else:
            adaptive_preview = 150  # Quick overview
        
        # Use smaller of provided max or adaptive
        actual_preview = min(max_preview, adaptive_preview)
        
        # Group results by parent file
        parent_docs = {}  # filepath -> {document, chunks: []}
        chunk_results = []
        
        for r in results:
            filepath = r['filepath']
            chunk_info = r.get('chunk_info')
            
            if chunk_info:
                # This is a chunk result
                if filepath not in parent_docs:
                    parent_docs[filepath] = {'document': None, 'chunks': []}
                parent_docs[filepath]['chunks'].append(r)
            else:
                # This is a document result
                if filepath not in parent_docs:
                    parent_docs[filepath] = {'document': r, 'chunks': []}
                else:
                    parent_docs[filepath]['document'] = r
        
        output = ["\n<retrieved_memory>"]
        output.append("📝 The following is retrieved from your long-term memory (previous interactions, notes, and preferences).")
        output.append("This context helps inform the current conversation but may not reflect recent updates.\n")
        
        item_index = 1
        
        for filepath, data in parent_docs.items():
            filename = os.path.basename(filepath)
            dirname = os.path.basename(os.path.dirname(filepath)) if '/' in filepath else ''
            
            # Format scores if available
            scores = ""
            if 'semantic_score' in data['document'] if data['document'] else r:
                score_source = data['document'] if data['document'] else r
                scores = f" | relevance={score_source['semantic_score']:.2f}"
                if 'recency_score' in score_source:
                    scores += f", recency={score_source['recency_score']:.2f}"
            
            location_label = f"[{dirname}/]" if dirname else ""
            
            if chunk_mode == "chunk":
                # Format individual chunks
                chunks = data.get('chunks', [])
                for chunk in chunks:
                    content = chunk.get('content', '')
                    preview = content[:actual_preview] + "..." if len(content) > actual_preview else content
                    
                    # Get chunk metadata
                    chunk_info = chunk.get('chunk_info', {})
                    heading = chunk_info.get('heading', 'Section')
                    keywords = chunk_info.get('keywords', [])
                    category = chunk_info.get('category', 'general')
                    
                    # Build keywords string
                    keywords_str = ', '.join(keywords) if keywords else ''
                    
                    output.append(f"<memory_chunk index=\"{item_index}\" source=\"{location_label}{filename}#{slugify(heading)}\" category=\"{category}\">")
                    output.append(f"<heading>{heading}</heading>")
                    output.append(f"<content>{preview.strip()}</content>")
                    if keywords_str:
                        output.append(f"<keywords>{keywords_str}</keywords>")
                    output.append(f"</memory_chunk>")
                    item_index += 1
                    
                    # Limit to top 3 chunks total for context
                    if item_index > 4:
                        break
            elif chunk_mode == "document" or chunk_mode == "hybrid":
                # Format full document
                doc = data.get('document')
                if doc:
                    content = doc.get('content', '')
                    preview = content[:actual_preview] + "..." if len(content) > actual_preview else content
                    
                    output.append(f"<memory_item index=\"{item_index}\" source=\"{location_label}{filename}\"{scores}>")
                    output.append(preview.strip())
                    output.append(f"</memory_item>")
                    item_index += 1
            else:
                # Default: format as chunks
                chunks = data.get('chunks', [])
                for chunk in chunks:
                    content = chunk.get('content', '')
                    preview = content[:actual_preview] + "..." if len(content) > actual_preview else content
                    
                    chunk_info = chunk.get('chunk_info', {})
                    heading = chunk_info.get('heading', 'Section')
                    keywords = chunk_info.get('keywords', [])
                    category = chunk_info.get('category', 'general')
                    
                    keywords_str = ', '.join(keywords) if keywords else ''
                    
                    output.append(f"<memory_chunk index=\"{item_index}\" source=\"{location_label}{filename}#{slugify(heading)}\" category=\"{category}\">")
                    output.append(f"<heading>{heading}</heading>")
                    output.append(f"<content>{preview.strip()}</content>")
                    if keywords_str:
                        output.append(f"<keywords>{keywords_str}</keywords>")
                    output.append(f"</memory_chunk>")
                    item_index += 1
                    
                    if item_index > 4:
                        break
            
            # Limit total items
            if item_index > 4:
                break
        
        output.append("</retrieved_memory>")
        
        return "\n".join(output)
        
    except Exception as e:
        # Graceful degradation: log error and return empty string instead of crashing
        logger.warning(f"Format results failed (degraded): {e}")
        return ""


def slugify(text: str) -> str:
    """
    Convert text to URL-friendly slug.
    
    Args:
        text: Input text
        
    Returns:
        Slug string (lowercase, hyphen-separated)
    """
    import re
    text = re.sub(r'[^a-zA-Z0-9\s-]', '', text.lower())
    text = re.sub(r'[\s]+', '-', text.strip())
    text = re.sub(r'-+', '-', text)
    return text if text else 'section'

def get_context_for_message(message: str, top_k: int = 3, chunk_mode: str = "chunk") -> str:
    """
    Main entry point: Get formatted context for a message.
    
    Args:
        message: User message to process
        top_k: Number of results
        chunk_mode: How to return results ("chunk", "document", or "hybrid")
        
    Returns:
        Formatted context string (empty if no relevant memories)
    """
    if not should_search(message):
        return ""
    
    try:
        results = auto_recall(message, top_k, chunk_mode)
        return format_results(results, chunk_mode=chunk_mode)
    except Exception as e:
        # Graceful degradation: return empty string instead of crashing
        logger.warning(f"Context extraction failed (degraded): {e}")
        return ""


def clear_dedupe_cache():
    """Clear the session deduplication cache."""
    global _session_recalled
    _session_recalled = {}


def get_dedupe_stats() -> dict:
    """Get deduplication statistics."""
    now = time.time()
    active = sum(1 for ts in _session_recalled.values() if now - ts < _dedupe_ttl_seconds)
    return {
        "total_recalled": len(_session_recalled),
        "active_in_ttl": active,
        "ttl_seconds": _dedupe_ttl_seconds
    }


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