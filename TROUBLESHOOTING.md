# fmem Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the fmem skill.

---

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Ollama Connection Issues](#ollama-connection-issues)
3. [Index Problems](#index-problems)
4. [Search Issues](#search-issues)
5. [Performance Problems](#performance-problems)
6. [Security Errors](#security-errors)

---

## Installation Issues

### "ModuleNotFoundError: No module named 'faiss'"

**Problem:** FAISS is not installed.

**Solution:**
```bash
pip install faiss-cpu
# Or for GPU support:
pip install faiss-gpu
```

**Verification:**
```bash
python3 -c "import faiss; print('FAISS OK')"
```

---

### "ModuleNotFoundError: No module named 'litellm'"

**Problem:** LiteLLM is not installed.

**Solution:**
```bash
pip install litellm
```

**Verification:**
```bash
python3 -c "import litellm; print('LiteLLM OK')"
```

---

### "Permission denied" when creating data directory

**Problem:** The system can't write to the default data directory.

**Solution:**
```bash
# Create directory with proper permissions
mkdir -p ~/.openclaw/memory/
chmod 755 ~/.openclaw/memory/

# Or use custom directory
export FMEM_DATA_DIR=/custom/path/
python3 fmem.py add /path/to/file.md
```

---

## Ollama Connection Issues

### "No models found in Ollama"

**Problem:** The Ollama service is not running or the model is not installed.

**Solution:**
```bash
# Check if Ollama is running
curl http://localhost:11434/v1/models

# If not running, start Ollama
ollama serve &

# Pull required model
ollama pull nomic-embed-text

# Verify model is available
curl http://localhost:11434/v1/models
```

---

### "Failed to generate embeddings"

**Problem:** Ollama connection failed or model not found.

**Solution:**
```bash
# Check Ollama URL
export FMEM_OLLAMA_URL="http://localhost:11434"

# Test connection
curl -X GET http://localhost:11434/v1/models

# Check if model is available
curl -X GET http://localhost:11434/v1/models | grep nomic-embed-text
```

---

### Ollama timeout errors

**Problem:** Embedding generation takes too long or times out.

**Solution:**
```bash
# Increase timeout
export FMEM_OLLAMA_TIMEOUT=60

# Check Ollama is not overloaded
ollama ps

# Reduce batch size
python3 fmem.py add --batch batch.txt --quiet
```

---

## Index Problems

### FAISS Index Not Persisting

**Problem:** The index file cannot be saved.

**Solution:**
```bash
# Check directory exists and is writable
ls -la ~/.openclaw/memory/

# Check disk space
df -h ~/.openclaw/memory/

# Try with custom directory
export FMEM_DATA_DIR=/custom/path/
python3 fmem.py add /path/to/file.md
```

---

### Index Corruption

**Problem:** The FAISS index file is corrupted.

**Solution:**
```bash
# Delete corrupted index
rm ~/.openclaw/memory/faiss_index.fai

# Re-add documents
python3 fmem.py reset
python3 fmem.py add /path/to/documents/*
```

---

### Empty Results After Adding Documents

**Problem:** Documents were added but search returns empty.

**Solution:**
```bash
# Check document count
python3 fmem.py status

# Check if documents were actually indexed
ls -la ~/.openclaw/memory/

# Reset and re-add
python3 fmem.py reset
python3 fmem.py add /path/to/documents/*
```

---

## Search Issues

### No Results for Valid Queries

**Problem:** Search returns no results even for known content.

**Solution:**
```bash
# Check Ollama is responding
curl http://localhost:11434/v1/models

# Check document count
python3 fmem.py status

# Try different query terms
python3 fmem.py search "simpler terms"
```

---

### Results Not Relevant

**Problem:** Search results are not relevant to the query.

**Solution:**
```bash
# Try different search terms
# Use specific keywords from your documents

# Increase result count
python3 fmem.py search "query" -k 10

# Check document content quality
# Better documents = better search results
```

---

### Search Takes Too Long

**Problem:** First search after adding documents is slow.

**Solution:**
```bash
# This is normal for first search
# Embeddings are generated on-the-fly

# For faster subsequent searches:
python3 fmem.py add /path/to/documents/*
python3 fmem.py persist
```

---

## Performance Problems

### Slow Indexing

**Problem:** Adding documents takes too long.

**Solution:**
```bash
# Batch add instead of individual
python3 fmem.py add --batch file_list.txt

# Use GPU if available
pip install faiss-gpu

# Reduce batch size for memory efficiency
# (fmem handles batching automatically)
```

---

### High Memory Usage

**Problem:** fmem uses too much memory.

**Solution:**
```bash
# Limit result count
python3 fmem.py search "query" -k 3

# Reduce document count
python3 fmem.py reset
python3 fmem.py add --batch smaller_batch.txt

# Use smaller index
# (fmem uses minimal memory by default)
```

---

## Security Errors

### "Path traversal attempt detected"

**Problem:** You're trying to access a file outside allowed directories.

**Solution:**
```bash
# Use absolute paths within allowed directory
python3 fmem.py add /home/user/documents/file.md

# Or relative to current directory
python3 fmem.py add ./file.md

# The system prevents: ../etc/passwd type paths
```

---

### "Invalid file extension"

**Problem:** You're trying to add a file with a non-whitelisted extension.

**Solution:**
```bash
# Only these extensions are allowed:
# .md, .txt, .py, .json, .yaml, .yml, .csv

# Rename file
mv file.exe file.txt

# Or convert to allowed format
pandoc file.docx -o file.md
```

---

### "File too large"

**Problem:** You're trying to add a file larger than 50MB.

**Solution:**
```bash
# Split large files
split -l 1000 large_file.md part_

# Or use only specific parts
python3 fmem.py add large_file_part_1.md
```

---

## Debug Mode

For detailed debugging, enable debug mode:

```bash
# Set debug environment variable
export FMEM_DEBUG=true

# Or run with debug flag
python3 fmem.py search "query" --debug
```

This will show:
- Full stack traces
- Configuration values
- Database operations
- Ollama connection details

---

## Getting Help

If you're still having issues:

1. **Check the logs:**
   ```bash
   grep -E "(Error|Warning)" ~/.openclaw/memory/*.log
   ```

2. **Run health check:**
   ```bash
   python3 fmem.py health
   ```

3. **Check status:**
   ```bash
   python3 fmem.py status
   ```

4. **Consult documentation:**
   - [README.md](README.md) - Overview and usage
   - [SECURITY.md](SECURITY.md) - Security details
   - [SKILL.md](SKILL.md) - Integration guide

---

**Version:** 2.0.0  
**Last Updated:** 2026-02-14
