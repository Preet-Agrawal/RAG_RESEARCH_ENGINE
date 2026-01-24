#!/bin/bash
# Setup script for RAG Research Engine Web Interface

echo "🚀 Setting up RAG Research Engine Web Interface..."
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    echo "   Visit: https://nodejs.org/"
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

echo "✓ Node.js $(node --version) detected"
echo "✓ Python $(python3 --version) detected"
echo ""

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install PyPDF2>=3.0.0 || {
    echo "❌ Failed to install PyPDF2"
    exit 1
}
echo "✓ PyPDF2 installed"
echo ""

# Navigate to web directory
cd web || {
    echo "❌ web directory not found"
    exit 1
}

# Install Node dependencies
echo "📦 Installing Node.js dependencies..."
npm install || {
    echo "❌ Failed to install Node.js dependencies"
    exit 1
}
echo "✓ Node.js dependencies installed"
echo ""

# Check for .env file
cd ..
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found!"
    echo ""
    echo "Creating .env from template..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your GROQ_API_KEY"
    echo "   Get your free API key at: https://console.groq.com"
    echo ""
else
    echo "✓ .env file exists"
fi

# Create uploads directory
mkdir -p data/uploads
echo "✓ Created data/uploads directory"
echo ""

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Make sure your GROQ_API_KEY is set in .env"
echo "  2. cd web"
echo "  3. npm run dev"
echo "  4. Open http://localhost:3000"
echo ""
echo "🎨 Enjoy your Claude-style RAG interface!"
