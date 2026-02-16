# Installation

## Requirements

- Python 3.10+
- FAISS (CPU version)
- Ollama (for local embeddings)

## Quick Install

```bash
pip install faiss-cpu numpy
```

## Setup

1. **Install Ollama** (for embeddings):
   ```bash
   # On Raspberry Pi
   curl -fsSL https://ollama.com/install.sh | sh
   ```

2. **Configure fmem**:
   ```bash
   export FMEM_DATA_DIR="~/.fmem"
   export OLLAMA_HOST="http://localhost:11434"
   ```

3. **Index your files**:
   ```python
   from fmem import MemoryRetrieval
   
   memory = MemoryRetrieval()
   memory.index_directory("/path/to/notes")
   ```

## Docker Option

See `config/` for Docker compose setup.
