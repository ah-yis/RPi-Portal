#!/bin/bash

# --- check for updates
#       lol ill setup updating when i push to github
#       ask the user to check for updates every launc, if they want (default yes)

# --- check for python
# actually python might not be necessary, since i get break system package errors
# instead, use pyenv

bash ./pyenv/bin/pip install -r requirements.txt
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# --- check if script is run via systemd services
#       ... if not, ask the user if they want to make a systemd service to run on startup
#       ... then make the systemd service...

# --- run descriptor.sh
chmod a+x descriptor.sh
sh ./descriptor.sh

# --- start api
uv run uvicorn main:app --host 0.0.0.0 --port 8000