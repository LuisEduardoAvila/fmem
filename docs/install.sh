#!/bin/bash
# fmem Installation Script
# =======================
# This script installs fmem and its dependencies.
# Usage: ./install.sh

set -e

echo "=== fmem Installation ==="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# ============================================================================
# Python Version Check
# ============================================================================
echo "Checking Python version..."

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
print_success "Found Python $PYTHON_VERSION"

# Check Python version >= 3.8
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
    print_error "Python 3.8+ required. Current version: $PYTHON_VERSION"
    exit 1
fi

print_success "Python version check passed (>= 3.8)"

# ============================================================================
# Pip Availability Check
# ============================================================================
echo ""
echo "Checking pip availability..."

if ! command -v pip3 &> /dev/null; then
    print_error "pip3 not found. Please install pip."
    echo ""
    echo "On Debian/Ubuntu: sudo apt-get install python3-pip"
    echo "On macOS: brew install python3"
    exit 1
fi

print_success "pip3 found"

# ============================================================================
# Ollama Check
# ============================================================================
echo ""
echo "Checking Ollama installation..."

if ! command -v ollama &> /dev/null; then
    print_error "Ollama not found."
    echo ""
    echo "Please install Ollama from: https://ollama.com/"
    echo ""
    echo "Quick install:"
    echo "  curl -fsSL https://ollama.com/install.sh | sh"
    exit 1
fi

print_success "Ollama found"

# Check if Ollama service is running
echo ""
echo "Checking Ollama service..."

if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
    print_warning "Ollama service not running"
    echo ""
    echo "Please start Ollama:"
    echo "  ollama serve"
    echo ""
    read -p "Start Ollama now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ollama serve &
        OLLAMA_PID=$!
        sleep 3
        
        if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
            print_error "Failed to start Ollama service"
            exit 1
        fi
        print_success "Ollama service started"
    else
        print_error "Ollama must be running to use fmem"
        exit 1
    fi
else
    print_success "Ollama service is running"
fi

# Check for nomic-embed-text model
echo ""
echo "Checking embedding model..."

if ! curl -s http://localhost:11434/api/tags | grep -q "nomic-embed-text"; then
    print_warning "nomic-embed-text model not found"
    echo ""
    echo "Pulling required model (this may take a few minutes)..."
    ollama pull nomic-embed-text
    
    if [ $? -ne 0 ]; then
        print_error "Failed to pull nomic-embed-text model"
        exit 1
    fi
fi

print_success "nomic-embed-text model available"

# ============================================================================
# Data Directory Setup
# ============================================================================
echo ""
echo "Setting up data directory..."

DATA_DIR="${HOME}/.openclaw/memory"
mkdir -p "$DATA_DIR"
chmod 755 "$DATA_DIR"

print_success "Data directory created: $DATA_DIR"

# ============================================================================
# Python Package Installation
# ============================================================================
echo ""
echo "Installing Python dependencies..."

# Check if fmem is already installed
if python3 -c "import fmem" 2>/dev/null; then
    print_warning "fmem appears to be already installed"
    read -p "Reinstall/upgrade? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping installation"
    fi
fi

# Install from current directory
echo "Installing fmem package..."

# Try different installation methods
if [ -f "pyproject.toml" ]; then
    # Modern: pip install -e .
    if pip3 install --user -e . 2>/dev/null || pip3 install -e . 2>/dev/null; then
        print_success "Installed from pyproject.toml"
    else
        print_error "Failed to install from pyproject.toml"
        echo "Trying alternative method..."
        
        # Fallback: direct dependencies
        pip3 install faiss-cpu litellm || {
            print_error "Failed to install dependencies"
            exit 1
        }
    fi
else
    # Legacy: install dependencies directly
    echo "Installing dependencies..."
    pip3 install faiss-cpu litellm || {
        print_error "Failed to install dependencies"
        exit 1
    }
fi

# ============================================================================
# Configuration File Setup
# ============================================================================
echo ""
echo "Setting up configuration..."

CONFIG_FILE="$DATA_DIR/fmem.conf"

if [ -f "docs/fmem.conf" ]; then
    cp docs/fmem.conf "$CONFIG_FILE"
    print_success "Configuration file created: $CONFIG_FILE"
else
    # Create minimal config
    cat > "$CONFIG_FILE" << 'EOF'
# fmem Configuration
# Place at: ~/.openclaw/memory/fmem.conf

[settings]
data_dir = ~/.openclaw/memory/
ollama_url = http://localhost:11434
index_name = faiss_index.fai
metadata_name = doc_metadata.json
sqlite_name = documents.db
extensions = .md, .txt, .py, .json, .yaml, .yml, .csv
EOF
    print_success "Default configuration file created"
fi

# ============================================================================
# Verification
# ============================================================================
echo ""
echo "Verifying installation..."

# Test imports
if python3 -c "
import sys
try:
    import faiss
    import litellm
    print('✓ FAISS imported')
    print('✓ LiteLLM imported')
    sys.exit(0)
except ImportError as e:
    print(f'✗ Import error: {e}')
    sys.exit(1)
"; then
    print_success "Core dependencies verified"
else
    print_error "Dependency verification failed"
    exit 1
fi

# Test fmem import
if python3 -c "
import sys
try:
    from fmem import MemoryRetrieval
    print('✓ fmem imported')
    sys.exit(0)
except ImportError as e:
    print(f'✗ fmem import error: {e}')
    sys.exit(1)
"; then
    print_success "fmem package verified"
else
    print_warning "fmem import failed (may be expected if not in package mode)"
fi

# Test Ollama connection
if python3 -c "
import sys
try:
    import litellm
    response = litellm.embedding(
        model='ollama/nomic-embed-text',
        input=['test'],
        api_base='http://localhost:11434'
    )
    print('✓ Ollama embedding working')
    sys.exit(0)
except Exception as e:
    print(f'✗ Ollama test failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
    print_success "Ollama embedding verified"
else
    print_warning "Could not verify Ollama embeddings (may need model pull)"
fi

# ============================================================================
# Summary
# ============================================================================
echo ""
echo "=================================="
echo "Installation Complete!"
echo "=================================="
echo ""
echo "You can now use fmem:"
echo ""
echo "  # From command line:"
echo "  python3 -m fmem.cli search \"your query\""
echo "  python3 -m fmem.cli add /path/to/file.md"
echo "  python3 -m fmem.cli status"
echo ""
echo "  # In Python:"
echo "  from fmem import MemoryRetrieval"
echo "  memory = MemoryRetrieval()"
echo "  results = memory.search(\"query\")"
echo ""
echo "Configuration file: ~/.openclaw/memory/fmem.conf"
echo "Data directory:      ~/.openclaw/memory/"
echo ""
echo "For help, see README.md or open an issue:"
echo "  https://github.com/LuisEduardoAvila/DarthSpudFmem/issues"
echo ""
print_success "Happy searching! 🔍"
echo ""
