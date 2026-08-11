# RPi-Portal
Python-based emulator for toys-to-life games on most platforms, using a RPi4. Based on implementation from RPCS3.
Remember that in it's current state it's practically unusable.

# To-Do List
- [-] Rewrite RPCS3's Infinity base code in Python
- [-] Set up FastAPI to interface with emulated base
- [ ] Create a proper WebUI instead of copy pasting bin paths into Swagger docs
- [ ] Fix startup.sh script so you can actually properly set it up
- [ ] Clean up files and add comments within the project
- [ ] Add support for colors on the slots (most emulators didn't implement it because it's absolutely useless)
- [ ] Add support for Lego Dimensions
- [ ] Add support for Skylanders

# Instructions
## Requirements
- Raspberry Pi with dwc2 chipset (ie. NOT RPi3B(+))
- USB-C - USB-A cable
- The game you want to play
- Local internet
- A game console
- A television (optional)
## Installation
1. Set up any reasonable version of Debian on your Pi, preferably with OpenSSH set up. Wi-Fi is obviously mandatory to control it via a web interface. You can use Raspberry Pi Imager to make things easier.

2. Clone the repo with: 
```
git clone https://github.com/ah-yis/RPi-Portal.git
```

3. Enter the repo and make `startup.sh` executable, run: 
```
cd RPi-Portal && sudo chmod +x startup.sh
```

4. Finally, run: 
```
sudo ./startup.sh
```

5. The script will ask you to configure it. So, configure it. You should probably stick to the default configuration, but it doesn't hurt to have options.

## Usage
You can now wait for your Pi to startup, and visit `http://<hostname>` to see the website and enjoy your obsolete cash-grab children's game!
