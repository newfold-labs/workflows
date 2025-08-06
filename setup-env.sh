#!/bin/bash
set -e

if [ ! -d "venv" ]; then
  python3 -m venv venv
  echo "✅ Created virtual environment"
fi

source venv/bin/activate
echo "✅ Activated virtual environment"

pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Installed dependencies"
