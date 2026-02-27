"""
Chunking module for fmem - Unified chunking strategies.

Provides table-aware and heading-based chunking strategies,
converting all outputs to standard ChunkMetadata format.

This module bridges the gap between:
- md2chunks_splitter.py: Table-aware splitting (atomic tables)
- fmem.py chunk_markdown: Heading-based splitting (original)
"""

import os
import re
from typing import List, Optional, Tuple

from .md2chunks_splitter import md2chunks_split, extract_tables
from .fmem import ChunkMetadata, _create_chunk, get_optimal_chunk_size


def chunk_markdown(
    content: str,
    filepath: str,
    min_chunk_size: int = 50,
    adaptive: bool = True,
    max_chunk_size: Optional[int] = None
) -> List[ChunkMetadata]:
    """
    Split markdown content using unified chunking strategy.
    
    **Strategy:**
    - If content has tables → use md2chunks_split (table-aware)
    - If no tables → use heading-based chunking (original logic)
    
    Tables are treated as atomic units and never split mid-row.
    
    Args:
        content: Full markdown content
        filepath: Original file path (used for chunk IDs)
        min_chunk_size: Minimum chunk size (merge smaller sections)
        adaptive: Whether to split large sections (default: True)
        max_chunk_size: Max chunk size (None = use 800 chars default)
        
    Returns:
        List of ChunkMetadata with consistent format
    """
    if not content or not filepath:
        return []
    
    filename = os.path.basename(filepath)
    effective_size = max_chunk_size or get_optimal_chunk_size()
    
    # Detect tables
    tables = extract_tables(content)
    
    if tables:
        # Use table-aware chunking
        chunks = _chunk_with_tables(content, filepath, filename, effective_size, min_chunk_size)
    else:
        # Use heading-based chunking (original logic)
        chunks = _chunk_with_headings(content, filepath, filename, effective_size, min_chunk_size, adaptive)
    
    return chunks


def _chunk_with_tables(
    content: str,
    filepath: str,
    filename: str,
    max_size: int,
    min_size: int
) -> List[ChunkMetadata]:
    """Chunk content using md2chunks_split (table-aware)."""
    chunk_dicts = md2chunks_split(content, max_chars=max_size, overlap=100)
    
    chunks = []
    for i, chunk_dict in enumerate(chunk_dicts):
        chunk_content = chunk_dict['text']
        heading = chunk_dict.get('context', '')
        
        # Skip tiny chunks (merge would have happened in md2chunks)
        if len(chunk_content) < min_size and i < len(chunk_dicts) - 1:
            continue
        
        chunks.append(_create_chunk(
            filename=filename,
            heading=heading or f"Section {i+1}",
            content=chunk_content,
            parent_file=filepath,
            chunk_index=i
        ))
    
    return chunks


def _chunk_with_headings(
    content: str,
    filepath: str,
    filename: str,
    max_size: int,
    min_size: int,
    adaptive: bool
) -> List[ChunkMetadata]:
    """Chunk content by ## headings (original logic)."""
    from .fmem import chunk_content_adaptively
    
    chunks = []
    heading_pattern = re.compile(r'^(#{2,})\s+(.+)$', re.MULTILINE)
    
    parts = []
    last_end = 0
    current_heading = "Top-Level Content"
    
    for match in heading_pattern.finditer(content):
        if match.start() > last_end:
            section_content = content[last_end:match.start()].strip()
            if section_content:
                parts.append((current_heading, section_content))
        
        current_heading = match.group(2).strip()
        last_end = match.end()
    
    # Add remaining content
    if last_end < len(content):
        section_content = content[last_end:].strip()
        if section_content:
            parts.append((current_heading, section_content))
    
    # Merge small chunks
    merged = _merge_small_parts(parts, min_size)
    
    # Create chunks with adaptive splitting for large sections
    chunk_index = 0
    for heading, section_content in merged:
        if adaptive and len(section_content) > max_size:
            split_sections = chunk_content_adaptively(section_content, max_chunk_size=max_size)
            for j, split_content in enumerate(split_sections):
                sub_heading = f"{heading} (part {j+1})" if len(split_sections) > 1 else heading
                chunks.append(_create_chunk(
                    filename=filename,
                    heading=sub_heading,
                    content=split_content,
                    parent_file=filepath,
                    chunk_index=chunk_index
                ))
                chunk_index += 1
        else:
            chunks.append(_create_chunk(
                filename=filename,
                heading=heading,
                content=section_content,
                parent_file=filepath,
                chunk_index=chunk_index
            ))
            chunk_index += 1
    
    return chunks


def _merge_small_parts(
    parts: List[tuple],
    min_size: int
) -> List[tuple]:
    """Merge parts smaller than min_size with adjacent parts."""
    if not parts:
        return parts
    
    merged = []
    buffer_heading = ""
    buffer_content = ""
    
    for heading, content in parts:
        if buffer_content and len(buffer_content) + len(content) < min_size:
            buffer_content += "\n\n" + content
        else:
            if buffer_content:
                merged.append((buffer_heading, buffer_content))
            buffer_heading = heading
            buffer_content = content
    
    if buffer_content:
        merged.append((buffer_heading, buffer_content))
    
    return merged


# Re-export for backward compatibility
__all__ = ['chunk_markdown', 'extract_tables']
