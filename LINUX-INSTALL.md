# Linux Installation Instructions

## Method 1: Build from Source (Recommended)

### Ubuntu/Debian:
```bash
# Clone repository
git clone https://github.com/mathoudebine/turing-smart-screen-python.git
cd turing-smart-screen-python

# Install system dependencies
sudo apt update
sudo apt install python3 python3-pip python3-venv

# Build
chmod +x build-linux.sh
./build-linux.sh

# Run
cd dist/turing-system-monitor
./main
```

## Method 2: Run from Source (No Build)

```bash
# Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run
python3 main.py
```

## Auto-start with systemd

Create service file:
```bash
sudo nano /etc/systemd/system/turing-screen.service
```

Content:
```ini
[Unit]
Description=Turing Smart Screen Monitor
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/path/to/turing-smart-screen-python
ExecStart=/path/to/turing-smart-screen-python/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable turing-screen.service
sudo systemctl start turing-screen.service

# Check status
sudo systemctl status turing-screen.service
```

## USB Permissions

Add your user to dialout group for USB access:
```bash
sudo usermod -a -G dialout $USER
# Log out and back in for changes to take effect
```

## Your Custom Updates Included

✅ MissionCenter theme (`res/themes/MissionCenter/`)
✅ psutil fallback for CPU frequency
✅ Fill and antialias support for line graphs
