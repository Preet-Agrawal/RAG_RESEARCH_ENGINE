#!/bin/bash

echo "=========================================="
echo "Ollama Setup for RAG Research Engine"
echo "FREE - No API Keys Required!"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install minimal dependencies (no OpenAI/Anthropic)
echo ""
echo "Installing dependencies (Ollama-only, no API libraries)..."
pip install -r requirements-ollama.txt

# Create necessary directories
echo ""
echo "Creating directory structure..."
mkdir -p results data config notebooks

# Copy environment file
echo ""
echo "Setting up environment configuration..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✓ Created .env file (no API keys needed for Ollama!)"
else
    echo "✓ .env file already exists"
fi

# Make scripts executable
echo ""
echo "Making scripts executable..."
chmod +x run_experiments.py
chmod +x test_ollama.py
chmod +x setup_ollama.sh

echo ""
echo "=========================================="
echo "Checking Ollama Installation"
echo "=========================================="
echo ""

# Check if Ollama is installed
if command -v ollama &> /dev/null; then
    echo "✓ Ollama is installed!"
    ollama --version

    echo ""
    echo "Installed models:"
    ollama list

    # Check if llama3:8b is installed
    if ollama list | grep -q "llama3:8b"; then
        echo ""
        echo "✓ llama3:8b is already installed!"
    else
        echo ""
        echo "⚠️  Recommended model 'llama3:8b' not found."
        echo ""
        read -p "Would you like to pull llama3:8b now? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Pulling llama3:8b (this may take a few minutes)..."
            ollama pull llama3:8b
        fi
    fi
else
    echo "⚠️  Ollama is not installed!"
    echo ""
    echo "Install Ollama by running:"
    echo "  curl -fsSL https://ollama.com/install.sh | sh"
    echo ""
    echo "Or download from: https://ollama.com/download"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Make sure Ollama is running (it should auto-start)"
echo "2. Activate the virtual environment: source venv/bin/activate"
echo "3. Test Ollama: python test_ollama.py"
echo "4. Run experiment: python run_experiments.py dead_zone --quick --provider ollama --model llama3:8b"
echo ""
echo "For full documentation, see README_OLLAMA.md"
echo ""
