"""
SearchIndex - FAISS Index Operations for fmem

Manages FAISS vector index operations with metadata mapping.
Extracted from MemoryRetrieval to follow Single Responsibility Principle.
"""

import fcntl
import json
import logging
import os
import tempfile
from contextlib import contextmanager
from typing import List, Dict, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)


@contextmanager
def _file_lock(lock_path: str, timeout: int = 30):
    """
    Context manager for exclusive file locking using fcntl.
    
    Args:
        lock_path: Path to lock file
        timeout: Maximum seconds to wait for lock (default 30)
        
    Raises:
        TimeoutError: If lock cannot be acquired within timeout
    """
    lock_file = None
    try:
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
        
        lock_file = open(lock_path, 'w')
        
        # Try to acquire exclusive lock with timeout
        import time
        start_time = time.time()
        while True:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except (IOError, OSError):
                if time.time() - start_time >= timeout:
                    raise TimeoutError(f"Could not acquire lock on {lock_path} within {timeout}s")
                time.sleep(0.1)
        
        yield lock_file
    finally:
        if lock_file is not None:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                lock_file.close()
            except (IOError, OSError):
                pass


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
    
    def remove_chunks_by_filepath(self, filepath: str) -> int:
        """
        Remove all chunks associated with a filepath from the FAISS index.
        
        Since FAISS doesn't support efficient individual deletion,
        this rebuilds the index without the removed chunks.
        
        Args:
            filepath: Path to the file whose chunks should be removed
            
        Returns:
            Number of chunks removed
        """
        import faiss
        
        # Find indices to remove
        indices_to_remove = []
        for i, mapping in enumerate(self._chunk_index_map):
            if mapping.get('filepath') == filepath:
                indices_to_remove.append(i)
        
        if not indices_to_remove:
            return 0
        
        # Get all embeddings and rebuild index without removed ones
        removed_count = len(indices_to_remove)
        logger.info(f"Removing {removed_count} chunks for {filepath}")
        
        # Create set for O(1) lookup
        remove_set = set(indices_to_remove)
        
        # Rebuild chunk index map without removed entries
        new_mapping = []
        for i, mapping in enumerate(self._chunk_index_map):
            if i not in remove_set:
                new_mapping.append(mapping)
        
        # Rebuild FAISS index
        if self.index.ntotal > 0:
            # Get all embeddings from current index
            all_embeddings = self.index.reconstruct_n(0, self.index.ntotal)
            
            # Filter out removed embeddings
            keep_indices = [i for i in range(len(all_embeddings)) if i not in remove_set]
            if keep_indices:
                new_embeddings = all_embeddings[keep_indices]
            else:
                new_embeddings = np.empty((0, self.dimension), dtype=np.float32)
            
            # Reset and rebuild index
            self.index.reset()
            if len(new_embeddings) > 0:
                self.index.add(new_embeddings)
        
        # Update mapping
        self._chunk_index_map = new_mapping
        
        logger.info(f"Removed {removed_count} chunks, index now has {len(self._chunk_index_map)} entries")
        return removed_count
    
    def _create_backup(self, filepath: str) -> bool:
        """
        Create a backup copy of a file with .bak extension.
        
        Args:
            filepath: Path to file to backup
            
        Returns:
            True if backup created or original doesn't exist
        """
        if not os.path.exists(filepath):
            return True
        
        backup_path = filepath + '.bak'
        
        # Remove old backup if exists
        if os.path.exists(backup_path):
            try:
                os.unlink(backup_path)
            except OSError:
                pass
        
        try:
            import shutil
            shutil.copy2(filepath, backup_path)
            logger.debug(f"Created backup at {backup_path}")
            return True
        except Exception as e:
            logger.warning(f"Failed to create backup of {filepath}: {e}")
            return False
    
    def _validate_faiss_index(self) -> bool:
        """
        Validate FAISS index by attempting a simple search operation.
        
        Returns:
            True if index is valid and operational
        """
        import faiss
        
        if self.index is None:
            return False
        
        try:
            # If index is empty, it's valid (just empty)
            if self.index.ntotal == 0:
                return True
            
            # Try to reconstruct a vector (validates index integrity)
            vector = self.index.reconstruct_n(0, 1)
            if vector is not None and len(vector) > 0:
                return True
            
            # Try a dummy search
            dummy_query = np.zeros((1, self.dimension), dtype=np.float32)
            self.index.search(dummy_query, 1)
            return True
        except Exception as e:
            logger.error(f"FAISS index validation failed: {e}")
            return False
    
    def save(self, index_path: str = None, mapping_path: str = None) -> bool:
        """
        Save FAISS index and chunk mapping to disk atomically.
        
        Uses write-to-temp-then-rename pattern for atomicity.
        Uses file locking to prevent concurrent write corruption.
        Creates backup (.bak) before overwriting.
        
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
        
        # Lock file for exclusive access
        lock_path = os.path.join(self.data_dir, '.fmem_index.lock')
        
        try:
            with _file_lock(lock_path, timeout=30):
                # Create backups before overwriting
                self._create_backup(index_path)
                self._create_backup(mapping_path)
                
                # Save FAISS index atomically
                if self.index is not None:
                    try:
                        # Write to temp file first
                        fd, temp_path = tempfile.mkstemp(
                            dir=os.path.dirname(index_path) or '.',
                            prefix='.faiss_index.tmp.'
                        )
                        try:
                            os.close(fd)
                            faiss.write_index(self.index, temp_path)
                            # fsync to ensure data is on disk
                            with open(temp_path, 'rb') as f:
                                os.fsync(f.fileno())
                            # Atomic rename
                            os.replace(temp_path, index_path)
                            logger.info(f"FAISS index saved to {index_path}")
                        except Exception:
                            # Clean up temp file on failure
                            try:
                                os.unlink(temp_path)
                            except OSError:
                                pass
                            raise
                    except Exception as e:
                        logger.error(f"Failed to save FAISS index: {e}")
                        success = False
                
                # Save chunk index map atomically
                if self._chunk_index_map:
                    try:
                        # Write to temp file first
                        fd, temp_path = tempfile.mkstemp(
                            dir=os.path.dirname(mapping_path) or '.',
                            prefix='.chunk_index_map.tmp.',
                            suffix='.json'
                        )
                        try:
                            os.close(fd)
                            with open(temp_path, 'w') as f:
                                json.dump(self._chunk_index_map, f, indent=2)
                                f.flush()
                                os.fsync(f.fileno())
                            # Atomic rename
                            os.replace(temp_path, mapping_path)
                            logger.info(f"Chunk index map saved to {mapping_path}")
                        except Exception:
                            # Clean up temp file on failure
                            try:
                                os.unlink(temp_path)
                            except OSError:
                                pass
                            raise
                    except Exception as e:
                        logger.error(f"Failed to save chunk index map: {e}")
                        success = False
        except TimeoutError as e:
            logger.error(f"Could not acquire lock for save: {e}")
            success = False
        
        return success
    
    def load(self, index_path: str = None, mapping_path: str = None) -> bool:
        """
        Load FAISS index and chunk mapping from disk.
        
        Uses shared file locking for safe concurrent access.
        Validates FAISS index after loading; restores from backup if corrupted.
        
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
        
        # Also check for backups
        index_backup_path = index_path + '.bak'
        mapping_backup_path = mapping_path + '.bak'
        
        success = False
        
        # Lock file for shared access (readers can access concurrently)
        lock_path = os.path.join(self.data_dir, '.fmem_index.lock')
        
        # Use non-blocking shared lock for reads
        lock_file = None
        try:
            try:
                os.makedirs(os.path.dirname(lock_path) or '.', exist_ok=True)
                lock_file = open(lock_path, 'w')
                # Shared lock for reads - multiple readers allowed
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
            except (IOError, OSError):
                # Non-critical: continue without lock if unable to acquire
                logger.debug("Could not acquire shared lock for load, proceeding without")
                lock_file = None
            
            # Load FAISS index
            index_loaded = False
            if os.path.exists(index_path):
                try:
                    self.index = faiss.read_index(index_path)
                    logger.info(f"Loaded FAISS index from {index_path}")
                    
                    # Validate the loaded index
                    if self._validate_faiss_index():
                        success = True
                        index_loaded = True
                    else:
                        logger.error(f"FAISS index validation failed - index may be corrupted")
                        # Try to restore from backup
                        if os.path.exists(index_backup_path):
                            logger.info(f"Attempting to restore FAISS index from backup...")
                            try:
                                self.index = faiss.read_index(index_backup_path)
                                if self._validate_faiss_index():
                                    logger.info(f"Successfully restored FAISS index from backup")
                                    success = True
                                    index_loaded = True
                                else:
                                    logger.error(f"Backup FAISS index also invalid")
                                    self.index = faiss.IndexFlatIP(self.dimension)
                            except Exception as backup_e:
                                logger.error(f"Failed to restore from backup: {backup_e}")
                                self.index = faiss.IndexFlatIP(self.dimension)
                        else:
                            logger.warning(f"No backup available at {index_backup_path}")
                            self.index = faiss.IndexFlatIP(self.dimension)
                except Exception as e:
                    logger.error(f"Failed to load FAISS index: {e}")
                    # Try backup
                    if os.path.exists(index_backup_path):
                        logger.info(f"Attempting to restore FAISS index from backup...")
                        try:
                            self.index = faiss.read_index(index_backup_path)
                            if self._validate_faiss_index():
                                logger.info(f"Successfully restored FAISS index from backup")
                                success = True
                                index_loaded = True
                            else:
                                self.index = faiss.IndexFlatIP(self.dimension)
                        except Exception as backup_e:
                            logger.error(f"Backup also corrupted: {backup_e}")
                            self.index = faiss.IndexFlatIP(self.dimension)
                    else:
                        self.index = faiss.IndexFlatIP(self.dimension)
            else:
                logger.warning(f"FAISS index not found at {index_path}, using empty index")
                self.index = faiss.IndexFlatIP(self.dimension)
            
            # Load chunk index map
            mapping_loaded = False
            if os.path.exists(mapping_path):
                try:
                    with open(mapping_path, 'r') as f:
                        self._chunk_index_map = json.load(f)
                    logger.info(f"Loaded {len(self._chunk_index_map)} chunk mappings from {mapping_path}")
                    mapping_loaded = True
                except Exception as e:
                    logger.error(f"Failed to load chunk index map: {e}")
                    # Try backup
                    if os.path.exists(mapping_backup_path):
                        logger.info(f"Attempting to restore chunk index map from backup...")
                        try:
                            with open(mapping_backup_path, 'r') as f:
                                self._chunk_index_map = json.load(f)
                            logger.info(f"Restored {len(self._chunk_index_map)} chunk mappings from backup")
                            mapping_loaded = True
                        except Exception as backup_e:
                            logger.error(f"Backup also failed: {backup_e}")
                            self._chunk_index_map = []
                    else:
                        self._chunk_index_map = []
            else:
                logger.warning(f"Chunk index map not found at {mapping_path}")
                # Try backup
                if os.path.exists(mapping_backup_path):
                    logger.info(f"Attempting to restore chunk index map from backup...")
                    try:
                        with open(mapping_backup_path, 'r') as f:
                            self._chunk_index_map = json.load(f)
                        logger.info(f"Restored {len(self._chunk_index_map)} chunk mappings from backup")
                        mapping_loaded = True
                    except Exception:
                        self._chunk_index_map = []
                else:
                    self._chunk_index_map = []
            
            # Overall success if at least index loaded (mapping is optional)
            success = index_loaded
        finally:
            if lock_file is not None:
                try:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                    lock_file.close()
                except (IOError, OSError):
                    pass
        
        return success
    
    def __len__(self) -> int:
        """Return number of embeddings in index."""
        return self.index.ntotal if self.index is not None else 0
    
    def __del__(self):
        """Cleanup on deletion."""
        pass  # No resources to clean up (caller should explicitly save if needed)
