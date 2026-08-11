# Camino Validator Status Monitor

A Python utility to monitor validator status on the Camino Network and send desktop alerts when validators go offline.

## Quick Install (Ubuntu)

1. Install dependencies:
   ```bash
   sudo apt update && sudo apt install -y python3 libnotify-bin git
   ```

2. Clone the repository and run the deploy script:
   ```bash
   git clone https://github.com/havan/camino-val-status-alarm.git
   cd camino-val-status-alarm
   sudo ./deploy_systemd.sh
   ```

That's it! The background service is now active and monitoring Camino Mainnet every 30 seconds.

---

## Files

*   **[monitor_validators.py](monitor_validators.py)**: The main python monitor script.
*   **`CURRENT_OFFLINE.txt`**: A status file generated automatically on every check, documenting the exact list of offline nodes, their Node ID, current uptime, and reward owner addresses (or "All validators are online").
*   **[deploy_systemd.sh](deploy_systemd.sh)**: Script to deploy and start the systemd service automatically.
*   **[camino-monitor.service.template](camino-monitor.service.template)**: Systemd service unit template file.
*   **[camino-monitor.cron](camino-monitor.cron)**: Configuration template and instructions for scheduling via cron.

## Usage

### 1. Manual Check
To run a single check immediately:
```bash
python3 monitor_validators.py
```
This is perfect for scheduling with `cron`.

### 2. Daemon Mode (Manual Start)
To run continuously in the background (e.g., checking every 30 seconds and alerting continuously if validators are offline):
```bash
python3 monitor_validators.py --daemon --interval 30 --force
```

### 3. Custom Endpoint
To monitor a different Camino endpoint (e.g., Columbus Testnet):
```bash
python3 monitor_validators.py --url https://columbus.camino.network
```

### 4. Test Notifications
To verify desktop notifications for different network conditions:
```bash
# Test single validator offline alert (default)
python3 monitor_validators.py --test-notify

# Test multiple validators offline alert
python3 monitor_validators.py --test-notify multiple

# Test recovery notification (all validators online)
python3 monitor_validators.py --test-notify online
```

---

## Deploying as a Systemd Service

To deploy the daemon as a system-level systemd service:

```bash
sudo ./deploy_systemd.sh
```

This script will automatically:
1. Detect your current system user and absolute directory path.
2. Render the systemd service template (`camino-monitor.service.template`).
3. Move the service file to `/etc/systemd/system/camino-monitor.service`.
4. Ensure the monitor script is executable.
5. Reload systemd, enable the service to start on boot, and start the service immediately.

To view the service status and logs:
```bash
# Check status
systemctl status camino-monitor.service

# View live logs
journalctl -u camino-monitor.service -f
```

---

## Scheduling with Cron

You can set up a cron job to check the status every minute. Because desktop notifications require `DBUS_SESSION_BUS_ADDRESS` and `DISPLAY` environment variables, the script automatically detects and exports them using your user ID.

To edit your cron table:
```bash
crontab -e
```

Add the following entry to check every minute and alert continuously on offline state (replace the path with your actual absolute path):
```cron
* * * * * /path/to/camino-val-status-alarm/monitor_validators.py --force
```
For more information, see the [camino-monitor.cron](camino-monitor.cron) file.
