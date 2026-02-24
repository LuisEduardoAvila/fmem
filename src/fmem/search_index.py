"""
SearchIndex - FAISS Index Operations for fmem

Manages FAISS vector index operations with metadata mapping.
Extracted from MemoryRetrieval to follow Single Responsibility Principle.
"""

import json
import logging
import os
from typing import List, Dict, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class SearchIndex:
    """
    Manages FAISS index operations and chunk-to-index mapping.
    
    Responsibilities:
    - FAISS index creation, add, search operations
    - Maintains _chunk_index_map for FAISS index → (filepath, chunk_id) mapping
    - Persistence: save/load FAISS index and JSON mapping
    """
    
    def __init__(self, dimension: int = 384, data_dir: str = None):
        """
        Initialize SearchIndex with FAISS IndexFlatIP.
        
        Args:
            dimension: Embedding dimension (default 384 for all-minilm:22m)
            data_dir: Directory for saving/loading index files
        """
        import faiss
        
        self.dimension = dimension
        self.data_dir = data_dir or os.path.expanduser("~/.openclaw/memory/index")
        
        # FAISS IndexFlatIP (Inner Product = Cosine similarity with normalized vectors)
        # Use with unit vectors for cosine similarity
        self.index = faiss.IndexFlatIP(dimension)
        
        # Chunk-to-document mapping: maps FAISS index -> (filepath, chunk_id)
        # This is critical because FAISS contains chunk embeddings, not document embeddings
        self._chunk_index_map = []
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        logger.info(f"SearchIndex initialized with dimension={dimension}")
    
    def add(self, embedding: np.ndarray, filepath: str, chunk_id: str, 
            heading: str = "", processed_content: str = "", original_length: int = 0) -> int:
        """
        Add embedding to FAISS index with metadata mapping.
        
        Args:
            embedding: Numpy array of shape (dimension,) or (1, dimension)
            filepath: Path to source file
            chunk_id: Unique chunk identifier
            heading: Section heading for this chunk
            processed_content: Preprocessed content that was embedded
            original_length: Original content length before preprocessing
            
        Returns:
            FAISS index position of added embedding
        """
        # Ensure embedding is 2D array for FAISS
        if embedding.ndim == 1:
            embedding = embedding.reshape(1, -1)
        
        # Add to FAISS index
        idx = self.index.ntotal  # Current index before adding
        self.index.add(embedding)
        
        # Add to mapping
        self._chunk_index_map.append({
            'filepath': filepath,
            'chunk_id': chunk_id,
            'heading': heading,
            'processed_content': processed_content,
            'original_length': original_length
        })
        
        logger.debug(f"Added embedding at index {idx}: {filepath}#{chunk_id}")
        return idx
    
    def search(self, query_embedding: np.ndarray, top_k: int = 5, 
               min_score: float = 0.3) -> List[Dict]:
        """
        Search FAISS index for similar embeddings.
        
        Args:
            query_embedding: Query vector of shape (dimension,) or (1, dimension)
            top_k: Maximum number of results to return
            min_score: Minimum similarity score threshold (0.0-1.0)
            
        Returns:
            List of dicts with keys: score, filepath, chunk_id, heading, 
            processed_content, original_length, faiss_idx
        """
        if self.index.ntotal == 0:
            return []
        
        # Ensure 2D array
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        # Search FAISS index
        distances, indices = self.index.search(query_embedding, top_k)
        
        results = []
        processed_chunks = set()  # Track processed chunk IDs for deduplication
        
        for i in range(len(indices[0])):
            score = float(distances[0][i])
            faiss_idx = int(indices[0][i])
            
            # Skip results below similarity threshold
            if score < min_score:
                continue
            
            # Get chunk mapping if available
            if 0 <= faiss_idx < len(self._chunk_index_map):
                mapping = self._chunk_index_map[faiss_idx]
                
                # Deduplicate
                chunk_key = (mapping['filepath'], mapping['chunk_id'])
                if chunk_key in processed_chunks:
                    continue
                processed_chunks.add(chunk_key)
                
                results.append({
                    'score': score,
                    'filepath': mapping['filepath'],
                    'chunk_id': mapping['chunk_id'],
                    'heading': mapping.get('heading', ''),
                    'processed_content': mapping.get('processed_content', ''),
                    'original_length': mapping.get('original_length', 0),
                    'faiss_idx': faiss_idx
                })
            else:
                logger.warning(f"FAISS index {faiss_idx} out of range for chunk_index_map (size: {len(self._chunk_index_map)})")
        
        return results
    
    def get_chunk_mapping(self, faiss_idx: int) -> Optional[Dict]:
        """
        Get chunk mapping for a specific FAISS index.
        
        Args:
            faiss_idx: Index in FAISS array
            
        Returns:
            Mapping dict or None if out of range
        """
        if 0 <= faiss_idx < len(self._chunk_index_map):
            return self._chunk_index_map[faiss_idx]
        return None
    
    def reset(self) -> None:
        """Clear FAISS index and chunk mapping."""
        if self.index is not None:
            self.index.reset()
        self._chunk_index_map = []
        logger.info("SearchIndex reset")
    
    def save(self, index_path: str = None, mapping_path: str = None) -> bool:
        """
        Save FAISS index and chunk mapping to disk.
        
        Args:
            index_path: Path for FAISS index file (default: data_dir/faiss_index.fai)
            mapping_path: Path for chunk mapping JSON (default: data_dir/chunk_index_map.json)
            
        Returns:
            True if both saved successfully
        """
        import faiss
        
        success = True
        
        if index_path is None:
            index_path = os.path.join(self.data_dir, 'faiss_index.fai')
        if mapping_path is None:
            mapping_path = os.path.join(self.data_dir, 'chunk_index_map.json')
        
        # Save FAISS index
        if self.index is not None:
            try:
                faiss.write_index(self.index, index_path)
                logger.info(f"FAISS index saved to {index_path}")
            except Exception as e:
                logger.error(f"Failed to save FAISS index: {e}")
                success = False
        
        # Save chunk index map
        if self._chunk_index_map:
            try:
                with open(mapping_path, 'w') as f:
                    json.dump(self._chunk_index_map, f, indent=2)
                logger.info(f"Chunk index map saved to {mapping_path}")
            except Exception as e:
                logger.error(f"Failed to save chunk index map: {e}")
                success = False
        
        return success
    
    def load(self, index_path: str = None, mapping_path: str = None) -> bool:
        """
        Load FAISS index and chunk mapping from disk.
        
        Args:
            index_path: Path for FAISS index file (default: data_dir/faiss_index.fai)
            mapping_path: Path for chunk mapping JSON (default: data_dir/chunk_index_map.json)
            
        Returns:
            True if index loaded successfully (mapping optional)
        """
        import faiss
        
        if index_path is None:
            index_path = os.path.join(self.data_dir, 'faiss_index.fai')
        if mapping_path is None:
            mapping_path = os.path.join(self.data_dir, 'chunk_index_map.json')
        
        success = False
        
        # Load FAISS index
        if os.path.exists(index_path):
            try:
                self.index = faiss.read_index(index_path)
                logger.info(f"Loaded FAISS index from {index_path}")
                success = True
            except Exception as e:
                logger.error(f"Failed to load FAISS index: {e}")
                # Initialize new index
                self.index = faiss.IndexFlatIP(self.dimension)
        else:
            logger.warning(f"FAISS index not found at {index_path}, using empty index")
            self.index = faiss.IndexFlatIP(self.dimension)
        
        # Load chunk index map
        if os.path.exists(mapping_path):
            try:
                with open(mapping_path, 'r') as f:
                    self._chunk_index_map = json.load(f)
                logger.info(f"Loaded {len(self._chunk_index_map)} chunk mappings from {mapping_path}")
            except Exception as e:
                logger.error(f"Failed to load chunk index map: {e}")
                self._chunk_index_map = []
        else:
            logger.warning(f"Chunk index map not found at {mapping_path}")
            self._chunk_index_map = []
        
        return success
    
    def __len__(self) -> int:
        """Return number of embeddings in index."""
        return self.index.ntotal if self.index is not None else 0
    
    def __del__(self):
        """Cleanup on deletion."""
        pass  # No resources to clean up (caller should explicitly save if needed)
