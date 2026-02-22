"""
Markdown-aware chunking (md2chunks-style) for fmem.

Handles tables as atomic units, preserves header context.
Replaces LLM-based chunking with pure Python parsing.

Inspired by: verloop/md2chunks approach
"""

import re
from typing import List, Dict, Tuple


def extract_tables(content: str) -> List[Tuple[int, int, str]]:
    """
    Find all markdown tables in content.
    Returns: [(start_pos, end_pos, table_content), ...]
    """
    # Pattern: header row + separator + data rows
    table_pattern = r'(?m)^\|[^\n]+\|\n\|[-:| ]+\|\n(?:\|[^\n]+\|\n?)+'
    tables = []
    for match in re.finditer(table_pattern, content):
        tables.append((
            match.start(),
            match.end(),
            clean_table(match.group())
        ))
    return tables


def clean_table(table_text: str) -> str:
    """
    Convert markdown table to clean text.
    Input: "| Col1 | Col2 |\n|------|------|\n| A | B |"
    Output: "Col1 Col2 A B"
    """
    lines = table_text.strip().split('\n')
    cleaned = []
    for line in lines:
        # Skip separator lines (|------|)
        if re.match(r'^\|[-:| ]+\|$', line.strip()):
            continue
        # Extract cells
        cells = [c.strip() for c in line.split('|') if c.strip()]
        if cells:
            cleaned.append(' '.join(cells))
    return ' '.join(cleaned)


def extract_headers(content: str) -> List[Tuple[int, str]]:
    """
    Find all headers in content.
    Returns: [(position, header_text), ...]
    """
    header_pattern = r'^(#{1,6})\s+(.+)$'
    headers = []
    for match in re.finditer(header_pattern, content, re.MULTILINE):
        level = len(match.group(1))
        text = match.group(2).strip()
        headers.append((match.start(), f"{'#' * level} {text}"))
    return headers


def get_header_context(headers: List[Tuple[int, str]], position: int) -> str:
    """
    Get the hierarchical context (parent headers) for a position.
    """
    context = []
    for pos, header in headers:
        if pos < position:
            context.append(header)
        else:
            break
    # Keep last 2 levels of context
    return ' > '.join(context[-2:]) if context else ""


def split_text_chunk(text: str, context: str, max_chars: int, overlap: int) -> List[Dict]:
    """
    Split text content at paragraph/sentence boundaries.
    """
    chunks = []
    paragraphs = re.split(r'\n{2,}', text)
    current = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        # Check if adding this paragraph exceeds limit
        if current and len(current) + len(para) + 2 > max_chars:
            # Store current chunk
            if current:
                chunks.append({
                    'text': current.strip(),
                    'context': context,
                    'type': 'text',
                    'position': 0
                })
            # Start new chunk with overlap (last sentence of previous)
            overlap_text = _get_overlap(current, overlap)
            current = overlap_text + para if overlap_text else para
        else:
            current = current + '\n\n' + para if current else para
    
    # Store final chunk
    if current:
        chunks.append({
            'text': current.strip(),
            'context': context,
            'type': 'text',
            'position': 0
        })
    
    return chunks


def _get_overlap(text: str, overlap: int) -> str:
    """Get overlap text from end of previous chunk."""
    if len(text) <= overlap:
        return text
    
    # Try to get last sentence
    sentences = re.split(r'(?<=[.!?])\s+', text)
    result = ""
    for sent in reversed(sentences):
        if len(result) + len(sent) <= overlap:
            result = sent + " " + result if result else sent
        else:
            break
    return result.strip() if result else text[-overlap:]


def md2chunks_split(content: str, max_chars: int = 800, overlap: int = 100) -> List[Dict]:
    """
    Split markdown content using md2chunks-style processing.
    
    Tables are treated as atomic units (not split).
    Headers provide context for each chunk.
    
    Args:
        content: Raw markdown content
        max_chars: Maximum characters per chunk (default 800 for ~500 tokens)
        overlap: Character overlap between chunks
    
    Returns:
        List of chunk dicts with text, context, type, and position
    """
    chunks = []
    headers = extract_headers(content)
    tables = extract_tables(content)
    
    # Build protected regions (tables are atomic)
    protected_spans = [(start, end, table_text) for start, end, table_text in tables]
    
    # Process content, respecting atomic tables
    pos = 0
    for table_start, table_end, table_text in protected_spans:
        # Content before table
        if pos < table_start:
            before = content[pos:table_start]
            context = get_header_context(headers, pos)
            chunks.extend(split_text_chunk(before, context, max_chars, overlap))
        
        # Table as single atomic chunk
        context = get_header_context(headers, table_start)
        chunks.append({
            'text': table_text,
            'context': context,
            'type': 'table',
            'position': table_start
        })
        
        pos = table_end
    
    # Content after last table
    if pos < len(content):
        remaining = content[pos:]
        context = get_header_context(headers, pos)
        chunks.extend(split_text_chunk(remaining, context, max_chars, overlap))
    
    # If no tables, just process whole content
    if not protected_spans:
        context = ""
        chunks = split_text_chunk(content, context, max_chars, overlap)
    
    return chunks


def merge_tiny_chunks(chunks: List[Dict], min_chars: int = 200) -> List[Dict]:
    """
    Merge chunks smaller than min_chars with adjacent chunks.
    Prevents fragmented single sentences/words.
    """
    if not chunks:
        return chunks
    
    merged = []
    i = 0
    while i < len(chunks):
        chunk = chunks[i]
        
        # If chunk is large enough, keep it
        if len(chunk['text']) >= min_chars:
            merged.append(chunk)
            i += 1
        else:
            # Try to merge with neighbors
            merged_text = chunk['text']
            merged_context = chunk['context']
            j = i + 1
            
            # Merge with following chunks until large enough
            while j < len(chunks) and len(merged_text) < min_chars:
                merged_text += ' ' + chunks[j]['text']
                j += 1
            
            merged.append({
                'text': merged_text,
                'context': merged_context,
                'type': chunk['type'],
                'position': chunk['position']
            })
            i = j
    
    return merged


# Convenience export
__all__ = ['md2chunks_split', 'extract_tables', 'extract_headers', 'merge_tiny_chunks']