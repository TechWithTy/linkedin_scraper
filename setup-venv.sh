#!/bin/bash
# Setup script for LinkedIn scraper virtual environment using uv

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "[*] Setting up LinkedIn scraper virtual environment..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "[X] Error: uv is not installed"
    echo "[!] Please install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Create virtual environment
echo "[*] Creating virtual environment..."
uv venv .venv

# Detect platform and use correct activation path
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || -f ".venv/Scripts/activate" ]]; then
    # Windows (Git Bash or WSL)
    ACTIVATE_SCRIPT=".venv/Scripts/activate"
    PYTHON_EXE=".venv/Scripts/python.exe"
else
    # Linux/Mac
    ACTIVATE_SCRIPT=".venv/bin/activate"
    PYTHON_EXE=".venv/bin/python"
fi

# Activate virtual environment
echo "[*] Activating virtual environment..."
source "$ACTIVATE_SCRIPT"

# Install dependencies
echo "[*] Installing dependencies..."
uv pip install -e .

# Install Playwright browsers
echo "[*] Installing Playwright browsers..."
"$PYTHON_EXE" -m playwright install chromium

echo "[OK] LinkedIn scraper setup complete!"
echo "[*] To activate the virtual environment, run:"
echo "    source .venv/bin/activate"

