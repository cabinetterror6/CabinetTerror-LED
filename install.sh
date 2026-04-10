#!/bin/bash
echo "=================================================="
echo "  STARTING CABINETTERROR-LED MASTER INSTALLER"
echo "=================================================="

# 1. Update System & Install Dependencies
echo ">>> Installing System Dependencies..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-dev python3-pillow python3-flask python3-requests python3-paho-mqtt mosquitto git make g++ network-manager

# 2. Download from GitHub
echo ">>> Pulling Golden Files from GitHub..."
cd /home/shanpi
git clone https://github.com/cabinetterror6/CabinetTerror-LED.git /tmp/led_build
mv /tmp/led_build/app.py /home/shanpi/
mv /tmp/led_build/twitch_scroller.py /home/shanpi/
mkdir -p /home/shanpi/templates
mv /tmp/led_build/templates/* /home/shanpi/templates/
rm -rf /tmp/led_build

# 3. Build the LED Matrix Brain
echo ">>> Compiling RGB Matrix Drivers..."
mkdir -p /home/shanpi/LEDMatrix
cd /home/shanpi/LEDMatrix
# Only clone if it doesn't already exist to save time on rebuilds
if [ ! -d "rpi-rgb-led-matrix-master" ]; then
    git clone https://github.com/hzeller/rpi-rgb-led-matrix.git rpi-rgb-led-matrix-master
fi
cd rpi-rgb-led-matrix-master
make build-python PYTHON=$(which python3)
sudo make install-python PYTHON=$(which python3)

# 4. God-Mode Wi-Fi Permissions
echo ">>> Granting Network Permissions..."
echo "shanpi ALL=(ALL) NOPASSWD: /usr/bin/nmcli" | sudo tee /etc/sudoers.d/010_shanpi_wifi

# 5. Create Background Services
echo ">>> Wiring up System Services..."

# Dashboard Service
sudo bash -c 'cat > /etc/systemd/system/led_dashboard.service <<EOF
[Unit]
Description=CabinetTerror Web Dashboard
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/shanpi/app.py
WorkingDirectory=/home/shanpi
StandardOutput=inherit
StandardError=inherit
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF'

# Matrix Scroller Service
sudo bash -c 'cat > /etc/systemd/system/twitch_led.service <<EOF
[Unit]
Description=CabinetTerror Matrix Scroller
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/shanpi/twitch_scroller.py
WorkingDirectory=/home/shanpi
StandardOutput=inherit
StandardError=inherit
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF'

# 6. Enable and Start the Ecosystem
echo ">>> Booting Systems..."
sudo systemctl daemon-reload
sudo systemctl enable led_dashboard.service
sudo systemctl enable twitch_led.service
sudo systemctl restart led_dashboard.service
sudo systemctl restart twitch_led.service

echo "=================================================="
echo "  INSTALLATION COMPLETE!"
echo "  Connect to the Wi-Fi and go to http://shanpi.local"
echo "=================================================="
