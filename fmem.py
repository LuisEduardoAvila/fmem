#!/usr/bin/env python3
"""
FAISS-based Memory Search System

Provides offline-first semantic search for agent memory using FAISS embeddings.
Zero external dependencies — works via litellm → Ollama (no OpenAI API).

Usage:
    from fmem.memory_search import MemoryRetrieval

    memory = MemoryRetrieval()
    results = memory.search("query", top_k=5)
    for r in results:
        print(f"[{r['score']:.3f}] {r['filepath']}")
"""

import faiss
import numpy as np
import sqlite3
import json
import os
import datetime
from typing import List, Dict, Optional
import sys

# Add skill directory to path
skill_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fmem')
if skill_dir not in sys.path:
    sys.path.insert(0, skill_dir)

# Import litellm and use nomic-embed-text model (served by local Ollama)
try:
    import litellm
    EMBEDDING_MODEL = "nomic-embed-text"
    EMBEDDING_DIM = 768
except ImportError:
    print("Error: litellm not installed")
    print("Run: pip3 install --break-system-packages litellm")
    sys.exit(1)


class MemoryRetrieval:
    """
    FAISS-based semantic memory search system.

    Features:
    - Zero external dependencies (no OpenAI/Pinecone)
    - In-memory or persistent storage
    - Low memory footprint (~8KB index)
    - Scalable to thousands of documents

    Usage:
        memory = MemoryRetrieval(db_path="/home/luis/.openclaw/memory/documents.db")
        memory.add_documents("/path/to/file.md", content)

        results = memory.search("your query", top_k=5)
        for doc in results:
            print(f"[{doc['score']:.3f}] {doc['filepath']}")
    """

    def __init__(self, db_path: str = None):
        """
        Initialize memory search system.

        Args:
            db_path: Optional SQLite path for persistent metadata.
                    If None, uses in-memory index (ephemeral).
        """
        self.dimension = EMBEDDING_DIM
        self.index = None
        self.doc_metadata = []  # List of {filepath, content, last_modified}
        self.db_path = db_path
        self.conn = None

        # Paths
        self.data_dir = os.path.expanduser("~/.openclaw/memory")
        self.index_path = os.path.join(self.data_dir, "faiss_index.fai")
        self.metadata_path = os.path.join(self.data_dir, "doc_metadata.json")

        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)

        # Try to load existing index
        self._load_index()

    def _load_index(self):
        """Load FAISS index and document metadata from disk"""
        try:
            if os.path.exists(self.index_path):
                self.index = faiss.read_index(self.index_path)
                print(f"✓ Loaded FAISS index from {self.index_path}")

            # Load metadata
            if os.path.exists(self.metadata_path):
                with open(self.metadata_path, 'r') as f:
                    self.doc_metadata = json.load(f)
                print(f"✓ Loaded {len(self.doc_metadata)} documents from metadata")
        except Exception as e:
            print(f"Warning: Failed to load cached index: {e}")
            # Initialize new index
            self.index = faiss.IndexFlatIP(self.dimension)

        # Initialize SQLite if db_path provided
        if self.db_path:
            self.conn = sqlite3.connect(self.db_path)
            self._create_db_tables()

    def _create_db_tables(self):
        """Create document metadata table if not exists"""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filepath TEXT UNIQUE,
                content TEXT,
                last_modified INTEGER,
                created_at INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                doc_id INTEGER,
                embedding BLOB,
                PRIMARY KEY (doc_id)
            )
        """)
        self.conn.commit()

    def add_document(self, filepath: str, content: Optional[str] = None):
        """
        Add a document to memory system.

        Args:
            filepath: Path to file (for metadata)
            content: Full document content. If None, reads from file.
        """
        # Load content if not provided
        if content is None:
            if not os.path.exists(filepath):
                print(f"Warning: File not found: {filepath}")
                return

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                print(f"Error: Failed to read {filepath}: {e}")
                return

        # Store metadata
        metadata = {
            'filepath': filepath,
            'content': content,
            'last_modified': int(datetime.datetime.now().timestamp()),
            'created_at': int(datetime.datetime.now().timestamp())
        }
        self.doc_metadata.append(metadata)

        # Generate embedding for content (for caching in SQLite)
        if self.conn:
            self._store_embedding(metadata, content)

    def _store_embedding(self, metadata: Dict, content: str):
        """Store embedding in SQLite for faster retrieval"""
        try:
            cursor = self.conn.cursor()

            # Check if already exists
            cursor.execute("SELECT id FROM documents WHERE filepath = ?", (metadata['filepath'],))
            doc_id = cursor.fetchone()

            if doc_id:
                doc_id = doc_id[0]
                # Update content and timestamp
                cursor.execute("""
                    UPDATE documents SET content = ?, last_modified = ?
                    WHERE filepath = ?
                """, (content, metadata['last_modified'], metadata['filepath']))
            else:
                # Insert new document
                cursor.execute("""
                    INSERT INTO documents (filepath, content, last_modified, created_at)
                    VALUES (?, ?, ?, ?)
                """, (metadata['filepath'], content, metadata['last_modified'], metadata['created_at']))
                doc_id = cursor.lastrowid

            self.conn.commit()
            print(f"✓ Stored {metadata['filepath']} in database")
        except Exception as e:
            print(f"Warning: Failed to store in database: {e}")

    def add_documents_batch(self, files: List[str]):
        """Add multiple documents in batch"""
        for filepath in files:
            self.add_document(filepath)

    def _generate_embeddings(self, texts: List[str]):
        """
        Generate embeddings using litellm with nomic-embed-text model via Ollama.

        Args:
            texts: List of strings to embed

        Returns:
            Embeddings array (N x 768)
        """
        try:
            # Use the ollama provider directly
            response = litellm.embedding(
                model="ollama/nomic-embed-text",
                input=texts,
                api_base="http://localhost:11434"
            )

            # Extract the embeddings from the response
            if hasattr(response, 'data'):
                # It's an EmbeddingResponse object, extract data
                embeddings_list = [item['embedding'] for item in response.data]
            elif isinstance(response, list):
                # It's already a list
                embeddings_list = response
            else:
                raise ValueError(f"Unexpected response type: {type(response)}")

            # Convert to numpy array
            return np.array(embeddings_list).astype('float32')
        except Exception as e:
            print(f"Error: Failed to generate embeddings: {e}")
            print(f"Note: Ensure Ollama is running with nomic-embed-text model installed")
            print(f"This model typically requires: ollama pull nomic-embed-text")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Search memory for relevant documents.

        Args:
            query: Search query string
            top_k: Number of relevant documents to return

        Returns:
            List of {filepath, content, score} dicts
        """
        if not self.index:
            if len(self.doc_metadata) == 0:
                return []
            # Initialize index with metadata dimensions
            self.index = faiss.IndexFlatIP(self.dimension)

        if len(self.doc_metadata) == 0:
            return []

        # Generate embedding for query
        query_embedding = self._generate_embeddings([query])[0]

        # Search FAISS index
        D, I = self.index.search(np.array([query_embedding]), top_k)

        # Build results
        results = []
        for idx in range(len(I[0])):
            doc_idx = I[0][idx]
            if doc_idx >= len(self.doc_metadata):
                continue

            results.append({
                'filepath': self.doc_metadata[doc_idx]['filepath'],
                'content': self.doc_metadata[doc_idx].get('content', ''),
                'score': float(D[0][idx])
            })

        return results

    def persist(self):
        """Save index and metadata to disk for persistence"""
        if self.index:
            try:
                faiss.write_index(self.index, self.index_path)
                print(f"✓ FAISS index persisted to {self.index_path}")
            except Exception as e:
                print(f"Warning: Failed to persist index: {e}")

        # Persist metadata
        if self.doc_metadata:
            try:
                with open(self.metadata_path, 'w') as f:
                    json.dump(self.doc_metadata, f)
                print(f"✓ Metadata persisted to {self.metadata_path}")
            except Exception as e:
                print(f"Warning: Failed to persist metadata: {e}")

        if self.conn:
            self.conn.close()

    def __del__(self):
        """Cleanup on deletion"""
        self.persist()

    def reset(self):
        """Clear all data"""
        if self.index:
            self.index.reset()
        self.doc_metadata = []
        if os.path.exists(self.index_path):
            os.remove(self.index_path)
        if os.path.exists(self.metadata_path):
            os.remove(self.metadata_path)
        print("✓ Memory cleared")


def cli():
    """Command-line interface for fmem skill"""
    import argparse

    parser = argparse.ArgumentParser("fmem — FAISS Memory Search")
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Search command
    parser_search = subparsers.add_parser('search', help='Search memory')
    parser_search.add_argument('query', help='Search query')
    parser_search.add_argument('-k', '--top-k', type=int, default=5, help='Number of results')

    # Add command
    parser_add = subparsers.add_parser('add', help='Add document to memory')
    parser_add.add_argument('filepath', help='Path to file to add')

    # Reset command
    subparsers.add_parser('reset', help='Clear memory')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    memory = MemoryRetrieval()

    if args.command == 'search':
        print(f"\nSearching: '{args.query}' (top-{args.top_k})\n")
        results = memory.search(args.query, top_k=args.top_k)
        for r in results:
            print(f"[{r['score']:.3f}] {r['filepath']}")
            # Preview content (first 200 chars)
            content_preview = r['content'][:200] + "..." if len(r['content']) > 200 else r['content']
            print(f"    Content: {content_preview}")

    elif args.command == 'add':
        print(f"\nAdding: {args.filepath}\n")
        memory.add_document(args.filepath)

    elif args.command == 'reset':
        print("\nResetting memory...")
        memory.reset()
        print("✓ Done\n")

    memory.persist()


if __name__ == '__main__':
    cli()