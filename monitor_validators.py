#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request

# Force line-buffered stdout for immediate logging in systemd/cron
sys.stdout.reconfigure(line_buffering=True)

DEFAULT_URL = "https://api.camino.network"
DEFAULT_STATE_NAME = ".val_monitor_state.json"

def load_json(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_json(filepath, data):
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

def get_offline_validators(url):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "platform.getCurrentValidators",
        "params": {}
    }
    req_url = url.rstrip('/') + "/ext/bc/P"
    req = urllib.request.Request(
        req_url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    with urllib.request.urlopen(req, timeout=10) as r:
        res = json.loads(r.read().decode('utf-8'))
        if 'error' in res:
            raise Exception(res['error']['message'])
        
        validators = res.get('result', {}).get('validators', [])
        offline = []
        for val in validators:
            connected = val.get('connected', True)
            if not connected:
                offline.append(val)
        return offline

def send_notification(summary, body, urgency="normal", icon="dialog-information"):
    env = os.environ.copy()
    uid = os.getuid()
    dbus_path = f"/run/user/{uid}/bus"
    if "DBUS_SESSION_BUS_ADDRESS" not in env and os.path.exists(dbus_path):
        env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={dbus_path}"
    if "DISPLAY" not in env:
        env["DISPLAY"] = ":0"
        
    cmd = ["/usr/bin/notify-send", "-u", urgency, "-a", "Camino Monitor", summary, body]
    if icon:
        cmd += ["-i", icon]
    
    try:
        subprocess.run(cmd, env=env, check=True)
    except Exception as e:
        sys.stderr.write(f"Error sending notification: {e}\n")

def check_status(url, state_file, force=False):
    try:
        offline_nodes = get_offline_validators(url)
    except Exception as e:
        send_notification("Camino Monitor API Error", f"Failed to fetch validators from {url}:\n{e}", urgency="normal", icon="dialog-error")
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] API Error: {e}")
        return

    current_offline = [f"• {node['nodeID']} (Uptime: {node['uptime']}%)" for node in offline_nodes]
    current_offline_set = set(current_offline)
    
    # Write CURRENT_OFFLINE.txt in the same directory as the state_file
    offline_file_path = os.path.join(os.path.dirname(os.path.abspath(state_file)), "CURRENT_OFFLINE.txt")
    try:
        with open(offline_file_path, 'w') as f:
            f.write(f"Last Check: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            if offline_nodes:
                f.write(f"Total Offline: {len(offline_nodes)}\n")
                f.write("=" * 50 + "\n\n")
                for node in offline_nodes:
                    node_id = node.get('nodeID', 'Unknown')
                    uptime = node.get('uptime', '0')
                    reward_owner = node.get('rewardOwner', {})
                    reward_addresses = reward_owner.get('addresses', [])
                    reward_str = ", ".join(reward_addresses) if reward_addresses else "None"
                    
                    f.write(f"NodeID: {node_id}\n")
                    f.write(f"Uptime: {uptime}%\n")
                    f.write(f"Reward Owner Addresses: {reward_str}\n")
                    f.write("-" * 50 + "\n")
            else:
                f.write("Status: All validators are online.\n")
    except Exception as e:
        sys.stderr.write(f"Warning: Failed to write {offline_file_path}: {e}\n")

    prev_state = load_json(state_file)
    prev_offline_set = set(prev_state.get('offline', []))
    
    if current_offline_set != prev_offline_set or force:
        if current_offline:
            num_offline = len(offline_nodes)
            emoji = "🚨" if num_offline > 1 else "⚠️"
            summary = f"{emoji} Camino Validator Offline Alert"
            body = f"{num_offline} validator(s) are offline:\n" + "\n".join(sorted(current_offline))
            icon = "dialog-error" if num_offline > 1 else "dialog-warning"
            send_notification(summary, body, urgency="normal", icon=icon)
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Alert: {num_offline} offline node(s). Notification sent.")
        else:
            if prev_offline_set:
                summary = "✅ Camino Validators Recovered"
                body = "All validators are now online and connected."
                send_notification(summary, body, urgency="normal", icon="dialog-information")
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Recovery: All nodes online. Notification sent.")
            else:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Status: All nodes online.")
                
        save_json(state_file, {'offline': list(current_offline_set)})
    else:
        if current_offline:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Status: {len(current_offline)} node(s) still offline (no change).")
        else:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Status: All nodes online.")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    parser = argparse.ArgumentParser(description="Monitor Camino Network validators and send desktop alerts when offline.")
    parser.add_argument('--url', default=DEFAULT_URL, help=f"Camino API endpoint URL (default: {DEFAULT_URL})")
    parser.add_argument('--force', '-f', action='store_true', help="Force status check to send notification even if offline set did not change")
    parser.add_argument('--test-notify', choices=['online', 'single', 'multiple'], const='single', nargs='?',
                        help="Send a test desktop notification for different events and exit. Choices: online, single, multiple (default: single)")
    parser.add_argument('--daemon', '-d', action='store_true', help="Run continuously in a loop")
    parser.add_argument('--interval', '-i', type=int, default=60, help="Check interval in seconds in daemon mode (default: 60)")
    parser.add_argument('--state-file', help="Path to state file for tracking offline nodes")
    
    args = parser.parse_args()
    state_file = args.state_file or os.path.join(script_dir, DEFAULT_STATE_NAME)
    
    if args.test_notify:
        if args.test_notify == 'online':
            send_notification("✅ Camino Validators Recovered", "All validators are now online and connected.", urgency="normal", icon="dialog-information")
            print("Sent test 'online' (recovery) notification.")
        elif args.test_notify == 'single':
            body = "1 validator(s) are offline:\n• NodeID-BYN6srNss7JVSS6w8u8mMfVSRjHbjKbo5 (Uptime: 94.25%)"
            send_notification("⚠️ Camino Validator Offline Alert", body, urgency="normal", icon="dialog-warning")
            print("Sent test 'single' offline notification.")
        elif args.test_notify == 'multiple':
            body = (
                "3 validator(s) are offline:\n"
                "• NodeID-3qwPm8pTpFr41er2zwLTwmzUsWhwqNyQ4 (Uptime: 88.50%)\n"
                "• NodeID-9tmq7eMkdYzhKc1i88TJqwxbJpcudsYCP (Uptime: 75.12%)\n"
                "• NodeID-BYN6srNss7JVSS6w8u8mMfVSRjHbjKbo5 (Uptime: 94.25%)"
            )
            send_notification("🚨 Camino Validator Offline Alert", body, urgency="normal", icon="dialog-error")
            print("Sent test 'multiple' offline notification.")
        sys.exit(0)
        
    if args.daemon:
        print(f"Starting Camino Validator Monitor daemon (interval: {args.interval}s, URL: {args.url})...")
        try:
            check_status(args.url, state_file, args.force)
        except KeyboardInterrupt:
            print("\nExiting.")
            sys.exit(0)
        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")
            
        while True:
            try:
                time.sleep(args.interval)
                check_status(args.url, state_file)
            except KeyboardInterrupt:
                print("\nExiting.")
                sys.exit(0)
            except Exception as e:
                sys.stderr.write(f"Error during check: {e}\n")
    else:
        check_status(args.url, state_file, args.force)

if __name__ == '__main__':
    main()
