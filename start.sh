#!/bin/bash

# 🌍 Africa Network Infrastructure Optimizer - Startup Script

echo "🚀 Starting Africa Network Infrastructure Optimizer..."
echo "=================================================="

# Check if we're in the right directory
if [ ! -d "routing_optimizer" ]; then
    echo "❌ Error: routing_optimizer directory not found"
    echo "Please run this script from the project root directory"
    exit 1
fi

# Navigate to the application directory
cd routing_optimizer

# Check if requirements are installed
echo "📦 Checking dependencies..."
if ! python -c "import flask" 2>/dev/null; then
    echo "📥 Installing dependencies..."
    pip install -r requirements.txt
else
    echo "✅ Dependencies already installed"
fi

# Start the application
echo "🌍 Starting the application..."
echo "=================================================="
echo "🔗 The application will be available on port 5000"
echo "🔗 Access it through the forwarded port in Codespaces"
echo "=================================================="

# Run the Flask application
python run_app.py
