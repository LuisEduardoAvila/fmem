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

# Import from same package (src/)
from .memory_retrieval import MemoryRetrieval

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
    Format search results for meaningful context injection into OpenClaw.
    
    Creates natural, conversational context that helps the LLM understand:
    - What was found (relevance-ranked)
    - Where it came from (source context)
    - How it relates to the query
    
    Args:
        results: List of search results from fmem.search()
        max_preview: Maximum preview length per result
        chunk_mode: Format style ("chunk", "document", or "hybrid")
        
    Returns:
        Formatted string ready for LLM context injection
    """
    try:
        if not results:
            return ""
        
        # Sort by score (highest first)
        sorted_results = sorted(results, key=lambda x: x.get('score', 0), reverse=True)
        
        # Adaptive preview based on number of results
        result_count = len(sorted_results)
        if result_count == 1:
            preview_len = 400  # Give single result more space
        elif result_count <= 3:
            preview_len = 250  # Balance for few results
        else:
            preview_len = 150  # Shorter for many results
        
        actual_preview = min(max_preview, preview_len)
        
        # Build output
        output = []
        output.append("<retrieved_memory>")
        output.append("")
        
        # Summary header
        if result_count == 1:
            output.append("I found 1 relevant memory for this conversation:")
        else:
            output.append(f"I found {result_count} relevant memories for this conversation:")
        output.append("")
        
        # Group by source file for organization
        from collections import defaultdict
        by_source = defaultdict(list)
        
        for r in sorted_results[:4]:  # Top 4 results
            filepath = r.get('filepath', 'unknown')
            by_source[filepath].append(r)
        
        # Format each result with relevance ranking
        for idx, (filepath, file_results) in enumerate(by_source.items(), 1):
            filename = os.path.basename(filepath)
            dirname = os.path.basename(os.path.dirname(filepath))
            
            # Determine relevance label
            if idx == 1:
                relevance = "Most relevant"
            elif idx == 2:
                relevance = "Also relevant"
            else:
                relevance = "Related"
            
            # Document type context
            doc_type = _get_doc_type(filename, dirname)
            source_context = f"{doc_type} from {dirname}/{filename}"
            
            output.append(f"[{idx}] {relevance}: {source_context}")
            # Include full path for potential file reading (security: local paths only)
            output.append(f"   Source: {filepath}")
            
            # OPTION C: Combine pre-computed summary + dynamic stats
            # Get pre-computed summary from doc_metadata (if available)
            precomputed_summary = ""
            dynamic_stats = ""
            
            # Try to get pre-computed summary from the first result's metadata
            # (In a real implementation, we'd pass mr instance to format_results)
            # For now, we'll use the _extract_file_summary which combines both
            
            # Get dynamic stats from relevant chunks
            stats_found = []
            for r in file_results:
                content = r.get('content', '')
                import re
                stat_matches = re.findall(r'(\d+\s+(?:movies?|series?|episodes?|shows?|tracked|watched))', content.lower())
                if stat_matches:
                    stats_found.extend(stat_matches)
            
            if stats_found:
                dynamic_stats = f"Relevant stats: {', '.join(set(stats_found[:3]))}"
            
            # Get file summary (pre-computed from doc_metadata via heuristic)
            # In actual implementation, this would come from mr.doc_metadata[filepath]['summary']
            file_summary_summary = _extract_file_summary(file_results)
            
            # Combine: Pre-computed overview + dynamic stats from search
            if file_summary_summary and dynamic_stats:
                combined_summary = f"{file_summary_summary} | {dynamic_stats}"
            elif file_summary_summary:
                combined_summary = file_summary_summary
            elif dynamic_stats:
                combined_summary = dynamic_stats
            else:
                combined_summary = ""
            
            if combined_summary:
                output.append(f"   About this file: {combined_summary}")
            
            output.append("")
            
            # Include each chunk from this file
            for r in file_results:
                content = r.get('content', '')
                preview = content[:actual_preview].strip()
                if len(content) > actual_preview:
                    preview += "..."
                
                # Get heading if available
                chunk_info = r.get('chunk_info', {})
                heading = chunk_info.get('heading', '')
                
                if heading and heading != 'Text':
                    output.append(f"   Under '{heading}':")
                
                # Clean content for readability
                clean_content = _clean_for_llm(preview)
                output.append(f"   {clean_content}")
                output.append("")
                
                # Show score if meaningful
                score = r.get('score', 0)
                if score > 0.5:
                    output.append(f"   [relevance: {score:.0%}]")
                    output.append("")
        
        # Footer
        if result_count > 4:
            output.append(f"...and {result_count - 4} more related memories")
            output.append("")
        
        output.append("</retrieved_memory>")
        
        return "\n".join(output)
        
    except Exception as e:
        logger.warning(f"Format results failed: {e}")
        return ""


def _get_doc_type(filename: str, dirname: str) -> str:
    """Determine document type for context."""
    lowername = filename.lower()
    lowerdir = dirname.lower()
    
    if 'memory' in lowerdir or 'memory' in lowername:
        return "Memory"
    elif 'docs' in lowerdir or 'documentation' in lowerdir:
        return "Documentation"
    elif 'decisions' in lowerdir or 'decisions' in lowername:
        return "Decision"
    elif 'projects' in lowerdir:
        return "Project notes"
    elif 'notes' in lowerdir:
        return "Notes"
    elif 'chats' in lowerdir or 'conversations' in lowerdir:
        return "Chat history"
    elif 'binge' in lowerdir or 'watch' in lowername:
        return "Movie/series tracking"
    elif lowername.endswith('.md'):
        return "Document"
    else:
        return "File"


def _clean_for_llm(text: str) -> str:
    """
    Clean up text for better LLM readability.
    Removes markdown formatting artifacts while preserving meaning.
    """
    import re
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Skip heading-only content (likely a table of contents marker)
    if text.startswith('###') and len(text) < 50:
        return "(Section heading)"
    
    # Remove markdown heading markers
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    
    # Remove markdown table separators
    text = re.sub(r'\|[-:\| ]+\|', '', text)
    
    # Remove excessive newlines but preserve paragraph breaks
    lines = [line.strip() for line in text.split('\n')]
    lines = [line for line in lines if line]
    text = ' '.join(lines)
    
    # Clean up multiple spaces
    text = ' '.join(text.split())
    
    # Remove leftover table cell separators
    text = text.replace(' | ', ' ')
    text = text.replace('|', ' ')
    
    return text


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


def _extract_file_summary(file_results: list) -> str:
    """
    Extract a brief summary of the file based on its chunks.
    
    This gives the LLM context about what the file contains overall,
    helping it decide whether to read the full file.
    
    Args:
        file_results: List of chunk results from this file
        
    Returns:
        Brief summary string (or empty if can't extract)
    """
    if not file_results:
        return ""
    
    # Collect headings and key stats from chunks
    headings = []
    stats = []
    
    for r in file_results:
        chunk_info = r.get('chunk_info', {})
        heading = chunk_info.get('heading', '')
        content = r.get('content', '')
        
        # Collect meaningful headings (not generic "Text")
        if heading and heading not in ['Text', 'Section']:
            headings.append(heading)
        
        # Extract stats/numbers mentioned
        stat_matches = re.findall(r'(\d+\s+(?:movies|series|episodes|shows|tracked|watched))', content.lower())
        stats.extend(stat_matches)
    
    # Build summary
    summary_parts = []
    
    # If we have headings, show first meaningful one as file topic
    if headings:
        summary_parts.append(f"Topics: {', '.join(headings[:2])}")
    
    # If we have stats, include them
    if stats:
        summary_parts.append(f"Contains: {', '.join(set(stats[:3]))}")
    
    return ' • '.join(summary_parts) if summary_parts else ""
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