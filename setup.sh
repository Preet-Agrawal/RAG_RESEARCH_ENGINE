#!/bin/bash

echo "=========================================="
echo "Lost in the Middle: RAG Research Engine"
echo "Setup Script"
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

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo ""
echo "Creating directory structure..."
mkdir -p results data config notebooks

# Copy environment file
echo ""
echo "Setting up environment configuration..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✓ Created .env file"
    echo "⚠️  Please edit .env and add your API keys!"
else
    echo "✓ .env file already exists"
fi

# Make run script executable
echo ""
echo "Making scripts executable..."
chmod +x run_experiments.py
chmod +x setup.sh

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env and add your OpenAI or Anthropic API key"
echo "2. Activate the virtual environment: source venv/bin/activate"
echo "3. Run a quick test: python run_experiments.py dead_zone --quick"
echo ""
echo "For full documentation, see README.md"
echo ""
