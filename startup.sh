#!/bin/bash
set -euo pipefail

# --- check for updates
#       TODO: check for updates on launch once this is pushed to GitHub (default yes)

# --- check for python ---
if command -v python3 &> /dev/null; then
    echo "Python is already installed."
else
    echo "Installing Python..."
    sudo apt update
    sudo apt install -y python3 python3-venv
fi

# --- check for uv ---
if command -v uv &> /dev/null; then
    echo "uv is already installed."
else
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    export PATH="$HOME/.local/bin:$PATH"
fi

# --- install project dependencies via uv (replaces manual venv + pip) ---
echo "Syncing project dependencies..."
uv sync

# --- set up the USB gadget descriptor ---
chmod +x descriptor.sh
sudo ./descriptor.sh

# --- offer to set up a systemd service ---
if systemctl is-active --quiet rpi-portal.service 2>/dev/null; then
    echo "rpi-portal.service already running, skipping setup."
else
    read -p "Would you like to set up a systemd service to autostart on boot? (Y/n): " response
    response=${response,,}
    response=${response:-y} 

    if [ "$response" = "y" ]; then
        portalDir=$(pwd)
        serviceFile="/etc/systemd/system/rpi-portal.service"

        sudo bash -c "cat > '$serviceFile'" <<EOF
[Unit]
Description=RPi-Portal
After=network.target

[Service]
WorkingDirectory=$portalDir
ExecStart=$(command -v uv) run uvicorn main:app --host 0.0.0.0 --port 80
Restart=on-failure
User=root

[Install]
WantedBy=multi-user.target
EOF

        sudo systemctl daemon-reload
        sudo systemctl enable --now rpi-portal.service

        echo "Service created. RPi-Portal will autostart on boot."
    else
        echo "NOT creating a systemd service..."
    fi
fi

# --- start api!!!!!
uv run uvicorn main:app --host 0.0.0.0 --port 80