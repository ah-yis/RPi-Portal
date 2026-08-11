#!/bin/bash

# --- check for updates
#       lol ill setup updating when i push to github
#       ask the user to check for updates every launc, if they want (default yes)

# --- check for python
# actually python might not be necessary, since i get break system package errors
# instead, use pyenv

# --- check for python
if command -v python3 &> /dev/null
then
    echo "Python is already installed."
else
    echo "Installing Python..."
    apt install python3 python3-venv -y
    pip install -r requirements.txt
fi

# --- check for py-dependencies
if command -v uv &> /dev/null
then
    echo "uv is already installed."
    echo "Installing Python dependencies..."
    bash ./pyenv/bin/pip install -r requirements.txt
else
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    echo "Installing Python dependencies..."
    bash ./pyenv/bin/pip install -r requirements.txt
fi



# --- check if script is run via systemd services
#       ... if not, ask the user if they want to make a systemd service to run on startup
#       ... then make the systemd service...

# --- run descriptor.sh
chmod a+x descriptor.sh
sh ./descriptor.sh

# --- start api
uv run uvicorn main:app --host 0.0.0.0 --port 8000