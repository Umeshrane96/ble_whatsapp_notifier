# BLE Proximity Telegram Notifier

A Python-based BLE (Bluetooth Low Energy) proximity detection system that sends Telegram notifications when a target device enters or leaves range. Designed to run headlessly on a Raspberry Pi.

## Features

- **BLE Device Scanning** — Continuously scans for a target BLE device by MAC address using the `bleak` library
- **Telegram Alerts** — Sends real-time notifications via Telegram Bot API:
  - 🏠 *"Home Minister arrived at home!"* — when device comes in range
  - 🚶 *"Home Minister left home!"* — when device goes out of range
- **Debouncing** — Requires 6 consecutive missed scans (~78s) before declaring a device "out of range", preventing false alerts from BLE signal flicker
- **State Persistence** — Saves current state to `ble_state.json` so it survives restarts without sending duplicate alerts
- **Systemd Service** — Can run as a startup service on Raspberry Pi

## How It Works

```
┌─────────────┐     BLE Scan      ┌──────────────┐
│  Target BLE │ ◄──────────────── │  RPi / Linux │
│   Device    │   (every 10s)     │   Machine    │
└─────────────┘                   └──────┬───────┘
                                         │
                                    State Change?
                                         │
                                   ┌─────▼──────┐
                                   │  Telegram   │
                                   │   Bot API   │
                                   └─────┬──────┘
                                         │
                                   ┌─────▼──────┐
                                   │  Your Phone │
                                   │  (Telegram) │
                                   └────────────┘
```

1. The script scans for BLE advertisements every **10 seconds**
2. If the target device is found → mark as "in range"
3. If the target device is missing for **6 consecutive scans** → mark as "out of range"
4. On each **state change**, a Telegram message is sent

## Requirements

- Python 3.8+
- Linux with Bluetooth adapter (built-in or USB BLE dongle)
- BlueZ (Linux Bluetooth stack)

### Python Dependencies

```
bleak>=0.21.0
requests>=2.28.0
```

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/ble_whatsapp_notifier.git
cd ble_whatsapp_notifier
```

### 2. Set Up Python Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install bleak requests
```

### 3. Configure Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts to create a bot
3. Copy the **Bot Token** you receive
4. Send a message to your new bot, then visit:
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
5. Find your **Chat ID** from the response JSON

### 4. Configure the Script

Edit `ble_whatsapp_notifier.py` and update these values:

```python
# Target BLE device MAC address
TARGET_DEVICE = "XX:XX:XX:XX:XX:XX"

# Telegram settings
TELEGRAM_BOT_TOKEN = "your-bot-token-here"
TELEGRAM_CHAT_ID = "your-chat-id-here"
```

### 5. Find Your Target BLE Device

You can use the built-in BLE scanner to discover nearby devices:

```bash
sudo python3 -c "
import asyncio
from bleak import BleakScanner

async def scan():
    devices = await BleakScanner.discover(timeout=10, return_adv=True)
    for addr, (dev, adv) in sorted(devices.items(), key=lambda x: x[1][1].rssi, reverse=True):
        print(f'{addr}  RSSI: {adv.rssi:>4} dBm  Name: {adv.local_name or dev.name or \"Unknown\"}')

asyncio.run(scan())
"
```

Pick the MAC address of your target device and set it as `TARGET_DEVICE`.

## Usage

### Run Manually

```bash
sudo python3 ble_whatsapp_notifier.py
```

> **Note:** `sudo` is required for BLE scanning on most Linux systems.

### Run as Systemd Service (Raspberry Pi)

1. Create the service file:

```bash
sudo tee /etc/systemd/system/ble-notifier.service > /dev/null << 'EOF'
[Unit]
Description=BLE Proximity Telegram Notifier
After=bluetooth.target network-online.target
Wants=network-online.target bluetooth.target

[Service]
Type=simple
User=root
ExecStartPre=/bin/sleep 5
ExecStart=/home/umesh/ble_venv/bin/python3 /home/umesh/ble_notifier.py
WorkingDirectory=/home/umesh
Restart=on-failure
RestartSec=15

[Install]
WantedBy=multi-user.target
EOF
```

2. Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ble-notifier.service
sudo systemctl start ble-notifier.service
```

3. Check status:

```bash
sudo systemctl status ble-notifier.service
sudo journalctl -u ble-notifier.service -f
```

## Configuration

| Parameter | Default | Description |
|---|---|---|
| `TARGET_DEVICE` | — | MAC address of the BLE device to track |
| `RSSI_THRESHOLD` | `-70` | Signal strength threshold in dBm |
| `SCAN_INTERVAL` | `3` | Seconds between scan cycles |
| `SCAN_DURATION` | `10` | Duration of each BLE scan in seconds |
| `MESSAGE_COOLDOWN` | `30` | Minimum seconds between messages |
| `MISS_THRESHOLD` | `6` | Consecutive misses before "out of range" |

### RSSI Reference

| RSSI (dBm) | Approximate Distance |
|---|---|
| -30 to -50 | Very close (< 1m) |
| -50 to -60 | Close (1–3m) |
| -60 to -70 | Nearby (3–5m) |
| -70 to -80 | In range (5–10m) |
| < -80 | Far / unreliable |

## File Structure

```
ble_whatsapp_notifier/
├── ble_whatsapp_notifier.py   # Main script
├── ble_state.json             # Runtime state (auto-generated)
├── README.md                  # This file
└── requirements.txt           # Python dependencies
```

## Troubleshooting

### "No Bluetooth adapters found"
- Ensure Bluetooth is enabled: `sudo hciconfig hci0 up`
- Check adapter exists: `hciconfig -a`
- On Raspberry Pi, check for undervoltage: `vcgencmd get_throttled`

### Telegram messages not sending
- Verify bot token and chat ID are correct
- Ensure you've sent at least one message to the bot first
- Test with: `curl "https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<CHAT_ID>&text=test"`

### False alerts / flickering
- Increase `MISS_THRESHOLD` (e.g., 10 for ~130s debounce)
- Increase `SCAN_DURATION` (e.g., 15 for longer scan window)

### BLE device not detected
- Ensure the device is advertising (BLE must be active, not just classic Bluetooth)
- Verify the MAC address — BLE devices with random/private addresses may change their MAC

## License

MIT License

## Author

Umesh
