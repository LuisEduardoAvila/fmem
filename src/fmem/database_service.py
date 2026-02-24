"""
DatabaseService - SQLite Storage for Documents and Chunks

Manages SQLite database operations for document and chunk metadata.
Extracted from MemoryRetrieval to follow Single Responsibility Principle.
"""

import logging
import os
import sqlite3
import hashlib
from typing import List, Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabaseService:
    """
    Manages SQLite database operations for fmem.
    
    Responsibilities:
    - SQLite connection management
    - Document CRUD operations
    - Chunk CRUD operations
    - Database schema management
    - Query operations for documents and chunks
    """
    
    def __init__(self, db_path: str):
        """
        Initialize DatabaseService.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize connection and tables
        self._connect()
        self._create_tables()
        
        logger.info(f"DatabaseService initialized with {db_path}")
    
    def _connect(self) -> bool:
        """
        Establish database connection.
        
        Returns:
            True if connection established
        """
        try:
            self.conn = sqlite3.connect(self.db_path, timeout=30.0)
            self.conn.row_factory = sqlite3.Row
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            self.conn = None
            return False
    
    def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        if not self.conn:
            return
        
        cursor = self.conn.cursor()
        
        # Documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filepath TEXT UNIQUE,
                content TEXT,
                last_modified INTEGER,
                created_at INTEGER,
                file_hash TEXT
            )
        """)
        
        # Embeddings table (links to documents)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                doc_id INTEGER,
                embedding BLOB,
                PRIMARY KEY (doc_id),
                FOREIGN KEY (doc_id) REFERENCES documents(id)
            )
        """)
        
        # Chunks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                parent_file TEXT,
                heading TEXT,
                content TEXT,
                keywords TEXT,
                category TEXT,
                token_count INTEGER,
                chunk_index INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Index for parent_file lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_parent_file ON chunks(parent_file)
        """)
        
        self.conn.commit()
        logger.debug("Database tables created/verified")
    
    def store_document(self, filepath: str, content: str, 
                       last_modified: int, created_at: int) -> Optional[int]:
        """
        Store or update document in database.
        
        Args:
            filepath: Path to file
            content: File content
            last_modified: Modification timestamp
            created_at: Creation timestamp
            
        Returns:
            Document ID or None if failed
        """
        if not self.conn:
            return None
        
        try:
            cursor = self.conn.cursor()
            
            # Check if document exists
            cursor.execute("SELECT id FROM documents WHERE filepath = ?", (filepath,))
            row = cursor.fetchone()
            
            file_hash = hashlib.md5(content.encode()).hexdigest()
            
            if row:
                # Update existing document
                doc_id = row[0]
                cursor.execute("""
                    UPDATE documents 
                    SET content = ?, last_modified = ?, file_hash = ?
                    WHERE id = ?
                """, (content, last_modified, file_hash, doc_id))
            else:
                # Insert new document
                cursor.execute("""
                    INSERT INTO documents (filepath, content, last_modified, created_at, file_hash)
                    VALUES (?, ?, ?, ?, ?)
                """, (filepath, content, last_modified, created_at, file_hash))
                doc_id = cursor.lastrowid
            
            self.conn.commit()
            logger.debug(f"Stored document {filepath} (id={doc_id})")
            return doc_id
            
        except Exception as e:
            logger.error(f"Failed to store document {filepath}: {e}")
            return None
    
    def get_document(self, filepath: str) -> Optional[Dict]:
        """
        Retrieve document by filepath.
        
        Args:
            filepath: Path to file
            
        Returns:
            Document dict or None if not found
        """
        if not self.conn:
            return None
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, filepath, content, last_modified, created_at, file_hash
                FROM documents
                WHERE filepath = ?
            """, (filepath,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'filepath': row[1],
                    'content': row[2],
                    'last_modified': row[3],
                    'created_at': row[4],
                    'file_hash': row[5]
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to get document {filepath}: {e}")
            return None
    
    def get_all_documents(self) -> List[Dict]:
        """
        Retrieve all documents.
        
        Returns:
            List of document dicts
        """
        if not self.conn:
            return []
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, filepath, content, last_modified, created_at, file_hash
                FROM documents
            """)
            
            docs = []
            for row in cursor.fetchall():
                docs.append({
                    'id': row[0],
                    'filepath': row[1],
                    'content': row[2],
                    'last_modified': row[3],
                    'created_at': row[4],
                    'file_hash': row[5]
                })
            return docs
            
        except Exception as e:
            logger.error(f"Failed to get all documents: {e}")
            return []
    
    def delete_document(self, filepath: str) -> bool:
        """
        Delete document and its chunks.
        
        Args:
            filepath: Path to file
            
        Returns:
            True if successful
        """
        if not self.conn:
            return False
        
        try:
            cursor = self.conn.cursor()
            
            # Get document ID
            cursor.execute("SELECT id FROM documents WHERE filepath = ?", (filepath,))
            row = cursor.fetchone()
            
            if row:
                doc_id = row[0]
                # Delete from embeddings
                cursor.execute("DELETE FROM embeddings WHERE doc_id = ?", (doc_id,))
                # Delete document
                cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            
            # Delete chunks
            cursor.execute("DELETE FROM chunks WHERE parent_file = ?", (filepath,))
            
            self.conn.commit()
            logger.debug(f"Deleted document and chunks for {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document {filepath}: {e}")
            return False
    
    def store_chunk(self, chunk_id: str, parent_file: str, heading: str,
                    content: str, keywords: List[str] = None, 
                    category: str = None, token_count: int = 0,
                    chunk_index: int = 0) -> bool:
        """
        Store or update chunk in database.
        
        Args:
            chunk_id: Unique chunk identifier
            parent_file: Path to parent file
            heading: Section heading
            content: Chunk content
            keywords: List of keywords
            category: Content category
            token_count: Token count
            chunk_index: Position index within parent file
            
        Returns:
            True if successful
        """
        if not self.conn:
            return False
        
        try:
            cursor = self.conn.cursor()
            
            keywords_str = ','.join(keywords) if keywords else ''
            
            cursor.execute("""
                INSERT OR REPLACE INTO chunks
                (chunk_id, parent_file, heading, content, keywords, category, token_count, chunk_index)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                chunk_id, parent_file, heading, content, keywords_str,
                category, token_count, chunk_index
            ))
            
            self.conn.commit()
            logger.debug(f"Stored chunk {chunk_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store chunk {chunk_id}: {e}")
            return False
    
    def get_chunk(self, chunk_id: str) -> Optional[Dict]:
        """
        Retrieve chunk by ID.
        
        Args:
            chunk_id: Unique chunk identifier
            
        Returns:
            Chunk dict or None if not found
        """
        if not self.conn:
            return None
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT chunk_id, parent_file, heading, content, keywords,
                       category, token_count, chunk_index
                FROM chunks WHERE chunk_id = ?
            """, (chunk_id,))
            
            row = cursor.fetchone()
            if row:
                keywords = row[4].split(',') if row[4] else []
                return {
                    'chunk_id': row[0],
                    'parent_file': row[1],
                    'heading': row[2],
                    'content': row[3],
                    'keywords': keywords,
                    'category': row[5],
                    'token_count': row[6],
                    'chunk_index': row[7]
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to get chunk {chunk_id}: {e}")
            return None
    
    def get_chunks_by_parent(self, parent_file: str) -> List[Dict]:
        """
        Get all chunks for a parent file.
        
        Args:
            parent_file: Path to parent file
            
        Returns:
            List of chunk dicts
        """
        if not self.conn:
            return []
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT chunk_id, parent_file, heading, content, keywords,
                       category, token_count, chunk_index
                FROM chunks WHERE parent_file = ?
                ORDER BY chunk_index
            """, (parent_file,))
            
            chunks = []
            for row in cursor.fetchall():
                keywords = row[4].split(',') if row[4] else []
                chunks.append({
                    'chunk_id': row[0],
                    'parent_file': row[1],
                    'heading': row[2],
                    'content': row[3],
                    'keywords': keywords,
                    'category': row[5],
                    'token_count': row[6],
                    'chunk_index': row[7]
                })
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to get chunks for {parent_file}: {e}")
            return []
    
    def get_all_chunks(self) -> List[Dict]:
        """
        Get all chunks.
        
        Returns:
            List of chunk dicts
        """
        if not self.conn:
            return []
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT chunk_id, parent_file, heading, content, keywords,
                       category, token_count, chunk_index
                FROM chunks
                ORDER BY parent_file, chunk_index
            """)
            
            chunks = []
            for row in cursor.fetchall():
                keywords = row[4].split(',') if row[4] else []
                chunks.append({
                    'chunk_id': row[0],
                    'parent_file': row[1],
                    'heading': row[2],
                    'content': row[3],
                    'keywords': keywords,
                    'category': row[5],
                    'token_count': row[6],
                    'chunk_index': row[7]
                })
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to get all chunks: {e}")
            return []
    
    def store_embedding(self, doc_id: int, embedding: bytes) -> bool:
        """
        Store embedding for a document.
        
        Args:
            doc_id: Document ID
            embedding: Binary embedding data
            
        Returns:
            True if successful
        """
        if not self.conn:
            return False
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO embeddings (doc_id, embedding)
                VALUES (?, ?)
            """, (doc_id, embedding))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to store embedding for doc {doc_id}: {e}")
            return False
    
    def get_embedding(self, doc_id: int) -> Optional[bytes]:
        """
        Get embedding for a document.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Binary embedding or None
        """
        if not self.conn:
            return None
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT embedding FROM embeddings WHERE doc_id = ?", (doc_id,))
            row = cursor.fetchone()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"Failed to get embedding for doc {doc_id}: {e}")
            return None
    
    def reset(self) -> bool:
        """
        Clear all data from database.
        
        Returns:
            True if successful
        """
        if not self.conn:
            return False
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM embeddings")
            cursor.execute("DELETE FROM chunks")
            cursor.execute("DELETE FROM documents")
            self.conn.commit()
            logger.info("Database reset - all tables cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to reset database: {e}")
            return False
    
    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            try:
                self.conn.close()
                self.conn = None
                logger.debug("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing database: {e}")
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close()
