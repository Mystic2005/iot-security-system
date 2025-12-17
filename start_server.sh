#!/bin/bash

echo "🏠 Starting intrusion detection system..."
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "⚙️  Activating virtual environment..."
source venv/bin/activate

echo "📥 Checking dependencies..."
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

echo "
Flask API: http://127.0.0.1:5000
Security System API: http://127.0.0.1:5001
"

python api.py & python security_system.py
