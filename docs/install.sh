#!/bin/bash
# fmem Skill Installation Script
# ==============================
# This script installs the fmem skill and its dependencies.

set -e

echo "=== fmem Skill Installation ==="
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 not found. Please install pip."
    exit 1
fi

# Create data directory
echo ""
echo "Creating data directory..."
mkdir -p ~/.openclaw/memory/
chmod 755 ~/.openclaw/memory/

# Install dependencies
echo ""
echo "Installing dependencies..."

# Check if already installed
if python3 -c "import faiss; import litellm" 2>/dev/null; then
    echo "✓ FAISS and LiteLLM are already installed"
else
    echo "Installing faiss-cpu..."
    pip3 install --break-system-packages faiss-cpu
    
    echo "Installing litellm..."
    pip3 install --break-system-packages litellm
fi

# Verify installation
echo ""
echo "Verifying installation..."
python3 -c "
import faiss
import litellm
print('✓ FAISS version:', faiss.__version__)
print('✓ LiteLLM imported successfully')
"

# Test basic functionality
echo ""
echo "Testing basic functionality..."
python3 -c "
from fmem import MemoryRetrieval, CONFIG
print('✓ fmem imported successfully')
print('✓ Config loaded:', CONFIG.data_dir)
"

echo ""
echo "=== Installation Complete ==="
echo ""
echo "You can now use fmem:"
echo "  python3 fmem.py search \"your query\""
echo "  python3 fmem.py add /path/to/file.md"
echo "  python3 fmem.py status"
echo ""
echo "For more help, see README.md or TROUBLESHOOTING.md"
echo ""
