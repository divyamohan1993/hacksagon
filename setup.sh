#!/bin/bash
# Eco-Lens Quick Setup Script

echo "🌿 ECO-LENS Setup"
echo "=================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.11+"
    exit 1
fi

# Check Node
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 18+"
    exit 1
fi

# Setup backend
echo "📦 Setting up backend..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..

# Setup frontend
echo "📦 Setting up frontend..."
cd frontend
npm install
cd ..

# Check for .env
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Copying .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env with your API keys"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the application:"
echo "  Terminal 1: cd backend && source venv/bin/activate && python -m uvicorn main:app --reload --port 8000"
echo "  Terminal 2: cd frontend && npm run dev"
echo ""
echo "Dashboard: http://localhost:3000"
echo "API Docs:  http://localhost:8000/docs"
