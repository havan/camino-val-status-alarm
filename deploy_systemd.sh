#!/bin/bash

# Ensure the script is run with sudo or has root privileges
if [ "$EUID" -ne 0 ]; then
  echo "Error: Please run this deploy script with sudo."
  exit 1
fi

# Detect absolute path of the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
CURRENT_USER=$(logname || echo $SUDO_USER || echo $USER)

TEMPLATE_FILE="$SCRIPT_DIR/camino-monitor.service.template"
SERVICE_FILE="/etc/systemd/system/camino-monitor.service"

if [ ! -f "$TEMPLATE_FILE" ]; then
  echo "Error: Template file $TEMPLATE_FILE not found."
  exit 1
fi

echo "Installing Camino Validator Monitor systemd service..."
echo "Working Directory: $SCRIPT_DIR"
echo "User: $CURRENT_USER"

# Replace placeholders and write to /etc/systemd/system
sed -e "s|__USER__|${CURRENT_USER}|g" \
    -e "s|__WORKDIR__|${SCRIPT_DIR}|g" \
    "$TEMPLATE_FILE" > "$SERVICE_FILE"

# Make sure monitor_validators.py is executable
chmod +x "$SCRIPT_DIR/monitor_validators.py"

# Reload systemd, enable, and start service
echo "Reloading systemd daemon..."
systemctl daemon-reload

echo "Enabling camino-monitor.service..."
systemctl enable camino-monitor.service

echo "Starting camino-monitor.service..."
systemctl start camino-monitor.service

echo "Checking status..."
systemctl status camino-monitor.service --no-pager -l

echo ""
echo "Done! Service is now deployed and running."
echo "You can check logs using: journalctl -u camino-monitor.service -f"
