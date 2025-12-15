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
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org Flask==3.0.0 > /dev/null 2>&1

echo "
🚀 Starting Flask server...
✅ Server ready!

🌐 Web interface: http://127.0.0.1:5000
📡 REST API     : http://127.0.0.1:5000/api/

📝 To stop the server: Ctrl+C
"

python api.py
