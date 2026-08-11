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
fi

# --- check for uv
if command -v uv &> /dev/null
then
    echo "uv is already installed."
else
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> $HOME/.bashrc
fi

# --- check for pyenv
if [ -d "pyenv" ];
then
    echo "pyenv already exists";
else
    echo "Creating pyenv and installing dependencies...";
    bash python3 -m venv pyenv
    bash ./pyenv/bin/pip install -r requirements.txt
fi

# --- check if script is run via systemd services
#       ... if not, ask the user if they want to make a systemd service to run on startup
#       ... then make the systemd service...

read -p "Would you like to setup a systemd service, to autostart this after boot? (Y/n): " response

response=${response,,}

if $response == "y";
then
portalDir = $(pwd)
fileDir = "/etc/systemd/system/rpi-portal.service"

cat <<tis > $fileDir
[Unit]
Description=RPi-Portal
After=network.target

[Service]
ExecStart=/bin/bash $fileDir 
Restart=on-failure

[Install]
WantedBy=multi-user.target
tis

systemctl daemon-reload
systemctl enable --now rpi-portal.service

echo "Done!"

else
echo "NOT creating a systemd service..."
fi

# --- run descriptor.sh
chmod a+x descriptor.sh
sh ./descriptor.sh

# --- start api
uv run uvicorn main:app --host 0.0.0.0 --port 80