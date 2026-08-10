#!/bin/bash

# 1. check for updates
# 2. check for python
# 3. check for py-dependencies
# 4. run descriptor.sh
# 5. start api

# --- check for updates
#   lol ill setup updating when i push to github
# --- check for python
if command -v python3 &> /dev/null
then
    echo "Python is already installed."
    pip install -r requirements.txt
else
    echo "Installing Python..."
    apt install python3 python3-pip python3-venv -y
    pip install -r requirements.txt
fi

# --- check for py-dependencies
if command -v uv &> /dev/null
then
    echo "uv is already installed."
else
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# --- run descriptor.sh
./descriptor.sh

# --- start api
uv run uvicorn main:app --host 0.0.0.0 --port 8000