#!/usr/bin/env python3
"""Memory file helper utilities."""

import os
from datetime import datetime
from pathlib import Path


def get_memory_file_path(date: datetime = None) -> Path:
    """Get the path to today's memory file.
    
    Args:
        date: Date for the memory file (defaults to today)
        
    Returns:
        Path to the memory file in workspace/memory/
    """
    if date is None:
        date = datetime.now()
    
    # Always use workspace/memory/ directory, not config data_dir
    memory_dir = Path("/home/luis/.openclaw/workspace/memory")
    memory_dir.mkdir(exist_ok=True)
    
    return memory_dir / f"{date.strftime('%Y-%m-%d')}.md"


def save_memory_entry(content: str, date: datetime = None, append: bool = True):
    """Save a memory entry to the daily file.
    
    Args:
        content: Memory content to save
        date: Date for the memory file (defaults to today)
        append: Whether to append to existing file or overwrite
    """
    memory_file = get_memory_file_path(date)
    
    # Create directory if needed
    memory_file.parent.mkdir(exist_ok=True)
    
    # Ensure content ends with proper markdown formatting
    if not content.strip().startswith("# "):
        content = f"\n\n{content}"
    if not content.endswith("\n"):
        content = f"{content}\n"
    
    if append and memory_file.exists():
        # Read existing content
        with open(memory_file, 'r', encoding='utf-8') as f:
            existing_content = f.read()
        
        # Append new content (ensure proper spacing)
        with open(memory_file, 'a', encoding='utf-8') as f:
            # Add separator between entries if needed
            if existing_content and not existing_content.endswith("\n\n"):
                f.write("\n\n")
            f.write(content)
    else:
        # Create new file or overwrite
        with open(memory_file, 'w', encoding='utf-8') as f:
            f.write(content)


def get_memory_file_content(date: datetime = None) -> str:
    """Get content of today's memory file.
    
    Args:
        date: Date for the memory file (defaults to today)
        
    Returns:
        Content of the memory file or empty string if doesn't exist
    """
    memory_file = get_memory_file_path(date)
    
    if not memory_file.exists():
        return ""
    
    with open(memory_file, 'r', encoding='utf-8') as f:
        return f.read()


if __name__ == "__main__":
    # Test the helper functions
    test_content = f"## Test Entry\n- Test content at {datetime.now()}"
    save_memory_entry(test_content, append=True)
    print(f"Memory entry saved to: {get_memory_file_path()}")
    print(f"File exists: {get_memory_file_path().exists()}")
    print(f"Content preview: {get_memory_file_content()[:100]}...")