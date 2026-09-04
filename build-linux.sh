#!/bin/bash
set -e

echo "=== Building Turing System Monitor for Linux ==="

# Install dependencies
echo "Installing dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller

# Build with PyInstaller
echo "Building executables..."
pyinstaller turing-system-monitor.spec --clean

echo ""
echo "=== Build Complete ==="
echo "Executables location: dist/turing-system-monitor/"
echo ""
echo "To run:"
echo "  cd dist/turing-system-monitor"
echo "  ./main"
