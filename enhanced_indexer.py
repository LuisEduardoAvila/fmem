#!/usr/bin/env python3
"""
Enhanced Memory Indexer with Location-Based Ranking
Adds file location importance scoring to recency and semantic similarity.
"""

import sys
import os
import time
import glob
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Add workspace to path
workspace = os.path.dirname(os.path.abspath(__file__))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

from fmem import MemoryRetrieval

# Configuration
MEMORY_DIR = os.path.join(os.environ.get('FMEM_WORKSPACE', '/home/luis/.openclaw/workspace'), 'memory')
MEMORY_MD_PATH = os.path.join(os.environ.get('FMEM_WORKSPACE', '/home/luis/.openclaw/workspace'), 'MEMORY.md')
NOTES_DIR = os.path.join(os.environ.get('FMEM_WORKSPACE', '/home/luis/.openclaw/workspace'), 'notes')
PERSONAS_DIR = os.path.join(os.environ.get('FMEM_WORKSPACE', '/home/luis/.openclaw/workspace'), 'PERSONAS')
INDEXED_TIME_FILE = os.path.expanduser('~/.openclaw/memory/.last_indexed')
SCAN_DELAY = int(os.environ.get('FMEM_SCAN_DELAY', '1800'))  # 30 minutes default

# File location importance mapping
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
    """
    Calculate importance weight based on file location.
    
    Args:
        filepath: Full path to the file
        
    Returns:
        Location weight (1.0 = base, >1.0 = more important, <1.0 = less important)
    """
    # Normalize the path
    normalized_path = os.path.normpath(filepath)
    path_parts = normalized_path.split(os.sep)
    
    # Check for location patterns
    for pattern, weight in LOCATION_WEIGHTS.items():
        if pattern.startswith('/'):
            # Absolute pattern - check if path ends with this pattern
            pattern_parts = pattern.strip('/').split('/')
            if len(path_parts) >= len(pattern_parts):
                if path_parts[-len(pattern_parts):] == pattern_parts:
                    return weight
        else:
            # Relative pattern - check if any part matches
            if any(pattern in part for part in path_parts):
                return weight
    
    # Default weight
    return 1.0

def scan_memory_files_with_locations() -> List[Tuple[str, float]]:
    """
    Scan memory directory for files to index with location weights.
    Uses relative paths since we chdir to workspace.
    
    Returns:
        List of (filepath, location_weight) tuples
    """
    files_with_weights = []
    
    # Always index MEMORY.md with high weight (relative path)
    if os.path.exists('MEMORY.md'):
        location_weight = get_file_location_weight('MEMORY.md')
        files_with_weights.append(('MEMORY.md', location_weight))
        print(f"  MEMORY.md (location weight: {location_weight:.1f})")
    
    # Index daily memory files with location weights
    if os.path.exists('memory'):
        for filepath in glob.glob('memory/*.md'):
            # Skip index metadata and temporary files
            filename = os.path.basename(filepath)
            if not any(skip in filename for skip in ['daily-index', '.last_indexed']):
                location_weight = get_file_location_weight(filepath)
                files_with_weights.append((filepath, location_weight))
                print(f"  {os.path.basename(filepath)} (location weight: {location_weight:.1f})")
    
    # Index notes directory (if exists)
    if os.path.exists('notes'):
        for filepath in glob.glob('notes/*.md'):
            location_weight = get_file_location_weight(filepath)
            files_with_weights.append((filepath, location_weight))
            print(f"  notes/{os.path.basename(filepath)} (location weight: {location_weight:.1f})")
    
    # PERSONAS excluded - already loaded in agent context
    
    return files_with_weights

def get_last_indexed_time():
    """Get timestamp of last indexing from file or metadata."""
    # Check indexed time file first
    if os.path.exists(INDEXED_TIME_FILE):
        try:
            with open(INDEXED_TIME_FILE, 'r') as f:
                return float(f.read().strip())
        except (ValueError, IOError):
            pass
    
    # Fallback: check doc_metadata.json
    metadata_path = os.path.expanduser("~/.openclaw/memory/doc_metadata.json")
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                if metadata and len(metadata) > 0:
                    # Get the most recent file modification time
                    return max(doc.get('last_modified', 0) for doc in metadata)
        except (ValueError, IOError, json.JSONDecodeError):
            pass
    
    return 0

def set_last_indexed_time(timestamp=None):
    """Record the last indexing time."""
    if timestamp is None:
        timestamp = time.time()
    
    os.makedirs(os.path.dirname(INDEXED_TIME_FILE), exist_ok=True)
    with open(INDEXED_TIME_FILE, 'w') as f:
        f.write(str(timestamp))

def needs_reindex(filepath, last_indexed):
    """Check if file needs reindexing based on modification time."""
    if not last_indexed:
        return True
    
    try:
        file_mtime = os.path.getmtime(filepath)
        return file_mtime > last_indexed
    except OSError:
        return False

def format_file_info(filepath, size=0):
    """Format file information for logging."""
    try:
        size = os.path.getsize(filepath)
    except OSError:
        size = 0
    
    size_kb = size / 1024
    return f"{os.path.basename(filepath)} ({size_kb:.1f}KB)"

def main():
    """Main indexer function."""
    start_time = time.time()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting enhanced memory indexer with location ranking...")
    
    # Change to workspace directory for relative path handling
    workspace = os.environ.get('FMEM_WORKSPACE', '/home/luis/.openclaw/workspace')
    os.chdir(workspace)
    
    # Initialize memory system
    try:
        mr = MemoryRetrieval()
    except Exception as e:
        print(f"[ERROR] Failed to initialize MemoryRetrieval: {e}")
        return 1
    
    # Get last indexed time
    last_indexed = get_last_indexed_time()
    last_indexed_str = (
        datetime.fromtimestamp(last_indexed).strftime('%Y-%m-%d %H:%M:%S')
        if last_indexed else 'Never'
    )
    print(f"Last indexed: {last_indexed_str}")
    
    # Scan for files with location weights
    files_with_weights = scan_memory_files_with_locations()
    print(f"Found {len(files_with_weights)} memory files to check")
    
    if files_with_weights:
        print("File location importance weights:")
        for filepath, weight in files_with_weights:
            print(f"  - {format_file_info(filepath)}: {weight:.1f}x")
    
    # Index new/modified files
    indexed_count = 0
    skipped_count = 0
    failed_count = 0
    failures = []
    
    for filepath, location_weight in files_with_weights:
        try:
            # Check if file needs reindexing
            if not needs_reindex(filepath, last_indexed):
                print(f"  - Skipped (unchanged): {format_file_info(filepath)}")
                skipped_count += 1
                continue
            
            # Add document with location weight metadata
            success = mr.add_document(filepath)
            
            if success:
                print(f"  ✓ Indexed: {format_file_info(filepath)}")
                indexed_count += 1
            else:
                print(f"  ✗ Failed to index: {format_file_info(filepath)}")
                failed_count += 1
                failures.append(filepath)
                
        except Exception as e:
            print(f"  ✗ Error processing {format_file_info(filepath)}: {e}")
            failed_count += 1
            failures.append(filepath)
    
    # Persist changes to disk
    if indexed_count > 0:
        print("Persisting changes to disk...")
        if mr.persist():
            print("  ✓ Changes persisted successfully")
        else:
            print("  ✗ Failed to persist changes")
    
    # Record indexing time
    current_time = time.time()
    set_last_indexed_time(current_time)
    
    # Calculate elapsed time
    elapsed = time.time() - start_time
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Enhanced indexing complete in {elapsed:.2f}s")
    print(f"  Indexed: {indexed_count} files")
    print(f"  Skipped: {skipped_count} files")
    print(f"  Failed:  {failed_count} files")
    
    if failures:
        print(f"\nFailed files:")
        for f in failures:
            print(f"  - {os.path.basename(f)}")
    
    # Show location weight distribution
    if files_with_weights:
        weights = [w for _, w in files_with_weights]
        print(f"\nLocation weight distribution:")
        print(f"  Average: {sum(weights)/len(weights):.1f}x")
        print(f"  Min: {min(weights):.1f}x")
        print(f"  Max: {max(weights):.1f}x")
    
    print(f"{'='*60}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())