#!/bin/bash

# Voice Questionnaire Setup Script
echo "🎤 Setting up Voice Questionnaire System..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is required but not installed."
    exit 1
fi

# Install requirements
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

# Check if config.env exists
if [ ! -f "config.env" ]; then
    echo "⚠️  config.env not found. Creating from template..."
    cp .env.example config.env
    echo "📝 Please edit config.env and add your OpenAI API key:"
    echo "   OPENAI_API_KEY=your_actual_api_key_here"
    echo ""
    echo "🔗 Get your API key from: https://platform.openai.com/api-keys"
    echo ""
    read -p "Press Enter after updating config.env..."
fi

# Check if API key is set
if grep -q "your_openai_api_key_here" config.env; then
    echo "⚠️  Please update your OpenAI API key in config.env"
    echo "   Current value: your_openai_api_key_here"
    echo "   Replace with your actual API key"
    exit 1
fi

echo "✅ Setup complete!"
echo "🚀 To start the server, run: python3 start.py"
echo "🌐 Then open: http://localhost:5001"
