"""
ResultEnhancer - Search Result Ranking with Recency and Location Weights

Applies recency and location-based scoring to search results.
Extracted from MemoryRetrieval to follow Single Responsibility Principle.
"""

import logging
import os
import re
import time
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EnhancerConfig:
    """Configuration for result enhancement."""
    enable_recency_ranking: bool = True
    enable_location_ranking: bool = True
    recency_weight: float = 0.2
    location_weight: float = 0.1
    recency_threshold_days: int = 30
    min_recency_score: float = 0.2
    append_only_recency_factor: float = 0.5
    
    # Location weights mapping
    location_weights: Dict[str, float] = None
    
    def __post_init__(self):
        if self.location_weights is None:
            self.location_weights = {
                # High importance - formal documentation and decisions
                'docs': 1.5,
                'documentation': 1.5,
                'projects': 1.3,
                'decisions': 1.4,
                'formal': 1.4,
                # Medium importance - active working files
                'work': 1.2,
                'active': 1.2,
                'current': 1.1,
                'notes': 1.0,
                'memory': 1.0,
                # Lower importance - casual/conversational content
                'chats': 0.8,
                'conversations': 0.8,
                'daily': 0.9,
                'sessions': 0.9,
                # Base importance
                'base': 1.0,
            }


class ResultEnhancer:
    """
    Enhances search results with recency and location-based ranking.
    
    Responsibilities:
    - Calculate recency scores based on file modification time
    - Calculate location weights based on file path
    - Apply hybrid scoring: semantic + recency + location
    - Handle append-only file special cases
    """
    
    def __init__(self, config: EnhancerConfig = None):
        """
        Initialize ResultEnhancer.
        
        Args:
            config: EnhancerConfig instance or None for defaults
        """
        self.config = config or EnhancerConfig()
        logger.info("ResultEnhancer initialized")
    
    def _is_append_only_file(self, filepath: str) -> bool:
        """
        Detect if file is append-only daily log.
        
        These files are updated frequently (high mtime) but contain accumulated
        content, not freshly-written content. Recency weight is reduced to 
        prevent old entries from appearing more recent than they are.
        
        Args:
            filepath: Path to the file
            
        Returns:
            True if file is a daily log (append-only), False otherwise
        """
        # Pattern: memory/YYYY-MM-DD.md or MEMORY.md
        if filepath == 'MEMORY.md':
            return True
        
        # Normalize path for checking
        filepath_lower = os.path.normpath(filepath).lower()
        path_parts = filepath_lower.split(os.sep)
        
        # Check if any path part is "memory" (our daily log directory)
        if 'memory' in path_parts:
            # Get the filename (last part of path)
            filename = os.path.basename(filepath)
            
            # Check if filename matches date pattern YYYY-MM-DD.md
            if re.search(r'\d{4}-\d{2}-\d{2}', filename):
                return True
        
        return False
    
    def _calculate_recency_score(self, last_modified: float, filepath: str = None) -> float:
        """
        Calculate recency score for a document based on its modification time.
        
        Args:
            last_modified: Unix timestamp of last modification
            filepath: Optional path to file for special handling
            
        Returns:
            Recency score between 0.0 and 1.0
        """
        if not self.config.enable_recency_ranking:
            return 1.0  # No recency adjustment
        
        current_time = time.time()
        age_days = (current_time - last_modified) / (24 * 60 * 60)
        
        # If within threshold, calculate score based on age
        if age_days <= self.config.recency_threshold_days:
            # Linear decay: newer documents get higher scores
            recency_score = 1.0 - (age_days / self.config.recency_threshold_days)
            return max(recency_score, self.config.min_recency_score)
        else:
            # Beyond threshold, apply minimum recency score
            return self.config.min_recency_score
    
    def _calculate_location_weight(self, filepath: str) -> float:
        """
        Calculate location-based importance weight for a file.
        
        Args:
            filepath: Full path to the file
            
        Returns:
            Location weight (1.0 = base, >1.0 = more important, <1.0 = less important)
        """
        if not self.config.enable_location_ranking:
            return 1.0
        
        # Normalize the path to lowercase for case-insensitive matching
        normalized_path = os.path.normpath(filepath).lower()
        path_parts = normalized_path.split(os.sep)
        
        # Check each directory in path for known patterns
        for part in path_parts:
            if part in self.config.location_weights:
                return self.config.location_weights[part]
        
        return self.config.location_weights.get('base', 1.0)
    
    def enhance(self, results: List[Dict], doc_metadata: Dict[str, Dict]) -> List[Dict]:
        """
        Apply recency and location enhancement to search results.
        
        Args:
            results: Original search results with 'score' and 'filepath' keys
            doc_metadata: Dict mapping filepath -> metadata dict with 'last_modified'
            
        Returns:
            Enhanced results with adjusted scores
        """
        if not results:
            return results
        
        # Calculate normalized weights
        total_weight = self.config.recency_weight + self.config.location_weight
        if total_weight > 1.0:
            logger.warning(f"Recency + location weights ({total_weight}) exceed 1.0. Normalizing.")
            scale = 1.0 / total_weight
            recency_w = self.config.recency_weight * scale
            location_w = self.config.location_weight * scale
        else:
            recency_w = self.config.recency_weight
            location_w = self.config.location_weight
        
        semantic_w = 1.0 - recency_w - location_w
        
        enhanced_results = []
        
        for result in results:
            filepath = result.get('filepath', '')
            semantic_score = result.get('score', 0.0)
            
            # Get document metadata
            metadata = doc_metadata.get(filepath, {})
            last_modified = metadata.get('last_modified', 0)
            
            # Calculate component scores
            recency_score = self._calculate_recency_score(last_modified, filepath)
            location_score = self._calculate_location_weight(filepath)
            
            # Adjust recency weight for append-only files
            adjusted_recency_w = recency_w
            if self._is_append_only_file(filepath):
                adjusted_recency_w *= self.config.append_only_recency_factor
                # Re-normalize semantic weight
                adjusted_semantic_w = 1.0 - adjusted_recency_w - location_w
            else:
                adjusted_semantic_w = semantic_w
            
            # Apply hybrid scoring
            enhanced_score = (
                semantic_score * adjusted_semantic_w +
                recency_score * adjusted_recency_w +
                location_score * location_w
            )
            
            # Create enhanced result
            enhanced_result = result.copy()
            enhanced_result['score'] = enhanced_score
            enhanced_result['semantic_score'] = semantic_score
            enhanced_result['recency_score'] = recency_score
            enhanced_result['location_score'] = location_score
            enhanced_result['recency_weight'] = adjusted_recency_w
            enhanced_result['location_weight'] = location_w
            enhanced_result['semantic_weight'] = adjusted_semantic_w
            enhanced_result['enhanced'] = True
            
            enhanced_results.append(enhanced_result)
        
        # Sort by enhanced score
        enhanced_results.sort(key=lambda x: x['score'], reverse=True)
        
        return enhanced_results
    
    def enhance_with_recency(self, results: List[Dict], doc_metadata: Dict[str, Dict]) -> List[Dict]:
        """
        Apply only recency enhancement.
        
        Args:
            results: Original search results
            doc_metadata: Document metadata dict
            
        Returns:
            Recency-enhanced results
        """
        if not self.config.enable_recency_ranking or not results:
            return results
        
        enhanced_results = []
        
        for result in results:
            filepath = result.get('filepath', '')
            semantic_score = result.get('score', 0.0)
            
            metadata = doc_metadata.get(filepath, {})
            last_modified = metadata.get('last_modified', 0)
            
            recency_score = self._calculate_recency_score(last_modified, filepath)
            
            # Get recency weight (may be reduced for append-only)
            recency_weight = self.config.recency_weight
            if self._is_append_only_file(filepath):
                recency_weight *= self.config.append_only_recency_factor
            
            # Apply hybrid scoring
            enhanced_score = (
                semantic_score * (1 - recency_weight) +
                recency_score * recency_weight
            )
            
            enhanced_result = result.copy()
            enhanced_result['score'] = enhanced_score
            enhanced_result['semantic_score'] = semantic_score
            enhanced_result['recency_score'] = recency_score
            enhanced_result['recency_weight_applied'] = recency_weight
            enhanced_result['enhanced'] = True
            
            enhanced_results.append(enhanced_result)
        
        enhanced_results.sort(key=lambda x: x['score'], reverse=True)
        return enhanced_results
    
    def enhance_with_location(self, results: List[Dict]) -> List[Dict]:
        """
        Apply only location enhancement.
        
        Args:
            results: Original search results
            
        Returns:
            Location-enhanced results
        """
        if not self.config.enable_location_ranking or not results:
            return results
        
        enhanced_results = []
        
        for result in results:
            filepath = result.get('filepath', '')
            semantic_score = result.get('score', 0.0)
            
            location_score = self._calculate_location_weight(filepath)
            location_weight = self.config.location_weight
            
            # Apply hybrid scoring
            enhanced_score = (
                semantic_score * (1 - location_weight) +
                location_score * location_weight
            )
            
            enhanced_result = result.copy()
            enhanced_result['score'] = enhanced_score
            enhanced_result['semantic_score'] = semantic_score
            enhanced_result['location_score'] = location_score
            enhanced_result['location_weight_applied'] = location_weight
            enhanced_result['enhanced'] = True
            
            enhanced_results.append(enhanced_result)
        
        enhanced_results.sort(key=lambda x: x['score'], reverse=True)
        return enhanced_results
