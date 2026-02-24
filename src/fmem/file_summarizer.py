"""
FileSummarizer - Extract File Summaries for Context Injection

Extracts brief summaries from files to provide context for LLM.
Extracted from MemoryRetrieval to follow Single Responsibility Principle.
"""

import logging
import os
import re
from typing import List, Optional

logger = logging.getLogger(__name__)


class FileSummarizer:
    """
    Extracts summaries from file content for context injection.
    
    Responsibilities:
    - Detect memory/log-style files vs regular files
    - Extract memory summaries: date, topics, status counts
    - Extract regular summaries: heading + first paragraph
    - Provide brief overviews (50-150 chars) for doc_metadata
    """
    
    def __init__(self):
        """Initialize FileSummarizer."""
        pass
    
    def summarize(self, content: str, filepath: str) -> str:
        """
        Extract a brief summary of the file from its content.
        
        This summary is stored in doc_metadata and used for context injection
        to give the LLM an overview of what the file contains.
        
        Special handling for:
        - Memory files (memory/YYYY-MM-DD.md, MEMORY.md): Extract topics + status
        - Regular files: First heading + first paragraph
        
        Args:
            content: Full file content
            filepath: Path to the file
            
        Returns:
            Brief summary string (50-150 chars)
        """
        # Detect memory files
        is_memory_file = self._is_memory_file(filepath)
        
        if is_memory_file:
            return self._extract_memory_summary(content, filepath)
        else:
            return self._extract_regular_summary(content, filepath)
    
    def _is_memory_file(self, filepath: str) -> bool:
        """
        Detect if file is a memory/log-style file.
        
        Args:
            filepath: Path to the file
            
        Returns:
            True if memory file, False otherwise
        """
        normalized_path = os.path.normpath(filepath).lower()
        
        if 'memory.md' in normalized_path or normalized_path.endswith('memory.md'):
            return True
        elif 'memory/' in normalized_path or '/memory/' in normalized_path:
            filename = os.path.basename(filepath)
            if re.search(r'\d{4}-\d{2}-\d{2}', filename):
                return True
        
        return False
    
    def _extract_memory_summary(self, content: str, filepath: str) -> str:
        """
        Extract summary from memory/log-style files.
        
        Extracts:
        - Date from filename or first heading
        - All ## topics/sections
        - Status keywords (COMPLETED, FIXED, DONE, ✅)
        - Count of topics and completed items
        
        Args:
            content: File content
            filepath: File path
            
        Returns:
            Summary like: "2026-02-22: 7 topics, 3 COMPLETED (FMEM, Bug fixes, Testing)"
        """
        filename = os.path.basename(filepath)
        
        # Extract date
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
        if date_match:
            date = date_match.group(1)
        else:
            heading_match = re.search(r'^#\s+(Session\s+)?(\d{4}-\d{2}-\d{2})', content, re.MULTILINE)
            if heading_match:
                date = heading_match.group(2)
            else:
                date = "Session"
        
        # Extract all ## headings (topics)
        topics = []
        for match in re.finditer(r'^##\s+(.+)$', content, re.MULTILINE):
            topic = match.group(1).strip()
            # Clean up: remove emojis, truncate
            topic = re.sub(r'^[\s\-\*\✓\✅\⚠️\❌]+', '', topic)
            topic = topic.split(':')[0][:30]
            if topic and topic not in ['Next Steps', 'Technical Notes']:
                topics.append(topic)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_topics = []
        for t in topics:
            if t.lower() not in seen:
                seen.add(t.lower())
                unique_topics.append(t)
        
        # Count status keywords
        completed_count = len(re.findall(r'(COMPLETED|✅|✓|DONE|FIXED)', content))
        in_progress_count = len(re.findall(r'(IN PROGRESS|🔄|→)', content))
        
        # Build summary
        summary_parts = [f"{date}: {len(unique_topics)} topics"]
        
        status_parts = []
        if completed_count > 0:
            status_parts.append(f"{completed_count} COMPLETED")
        if in_progress_count > 0:
            status_parts.append(f"{in_progress_count} IN PROGRESS")
        
        if status_parts:
            summary_parts.append(f"{', '.join(status_parts)}")
        
        # Add top 2-3 topics as examples
        if len(unique_topics) > 0:
            topic_examples = unique_topics[:3]
            summary_parts.append(f"({', '.join(topic_examples)})")
        
        summary = ' • '.join(summary_parts)
        
        if len(summary) > 150:
            summary = summary[:147] + '...'
        
        return summary if summary else f"Session {date}"
    
    def _extract_regular_summary(self, content: str, filepath: str) -> str:
        """
        Extract summary from regular documents.
        
        Uses first # heading + first meaningful paragraph.
        
        Args:
            content: File content
            filepath: File path
            
        Returns:
            Summary like: "BingeWatching Tracker • Personal entertainment tracking system"
        """
        lines = content.split('\n')
        summary_parts = []
        
        # Get title from first # heading
        for line in lines[:10]:
            if line.startswith('# ') and not line.startswith('##'):
                title = line[2:].strip()
                title = re.sub(r'^[^\w]*', '', title)
                if len(title) > 10:
                    summary_parts.append(title)
                    break
        
        # Get first meaningful paragraph
        for line in lines[:20]:
            line = line.strip()
            if (line and 
                not line.startswith('#') and 
                not line.startswith('```') and 
                not line.startswith('|') and
                not line.startswith('- ') and
                not line.startswith('* ') and
                len(line) > 30):
                if len(line) > 80:
                    line = line[:77] + '...'
                summary_parts.append(line)
                break
        
        # Extract key stats
        stats = []
        stat_patterns = [
            r'(\d+)\s+(?:movies?|films?)',
            r'(\d+)\s+(?:series?|shows?)',
            r'(\d+)\s+(?:episodes?)',
        ]
        for pattern in stat_patterns:
            match = re.search(pattern, content.lower()[:5000])
            if match:
                stats.append(match.group(0))
                break
        
        # Build summary
        if summary_parts:
            base_summary = ' • '.join(summary_parts[:2])
        else:
            base_summary = os.path.splitext(os.path.basename(filepath))[0].replace('-', ' ').title()
        
        if stats:
            base_summary += f" ({stats[0]})"
        
        if len(base_summary) > 120:
            base_summary = base_summary[:117] + '...'
        
        return base_summary
    
    def extract_topics(self, content: str, max_topics: int = 10) -> List[str]:
        """
        Extract ## heading topics from content.
        
        Args:
            content: File content
            max_topics: Maximum number of topics to return
            
        Returns:
            List of topic strings
        """
        topics = []
        for match in re.finditer(r'^##\s+(.+)$', content, re.MULTILINE):
            topic = match.group(1).strip()
            topic = re.sub(r'^[\s\-\*\✓\✅\⚠️\❌]+', '', topic)
            topic = topic.split(':')[0]
            if topic and topic not in topics:
                topics.append(topic)
                if len(topics) >= max_topics:
                    break
        return topics
    
    def count_status_items(self, content: str) -> dict:
        """
        Count status items in content.
        
        Args:
            content: File content
            
        Returns:
            Dict with 'completed', 'in_progress' counts
        """
        return {
            'completed': len(re.findall(r'(COMPLETED|✅|✓|DONE|FIXED)', content)),
            'in_progress': len(re.findall(r'(IN PROGRESS|🔄|→)', content))
        }
