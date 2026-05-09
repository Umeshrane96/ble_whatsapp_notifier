<div align="center">

# 📡 BLE Proximity Telegram Notifier

**Know when someone arrives or leaves — powered by Bluetooth Low Energy**

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-Ready-C51A4A?style=for-the-badge&logo=raspberrypi&logoColor=white)](https://www.raspberrypi.org/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot%20API-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

<br>

A lightweight Python daemon that continuously scans for a target BLE device and sends instant **Telegram notifications** when the device enters or leaves range. Perfect for home presence detection on a **Raspberry Pi**.

<br>

🏠 *"Home Minister arrived at home!"* &nbsp;|&nbsp; 🚶 *"Home Minister left home!"*

---

</div>

## ✨ Features

| Feature | Description |
|:---:|---|
| 📶 **BLE Scanning** | Continuously scans for a target BLE device by MAC address using [`bleak`](https://github.com/hbldh/bleak) |
| 📲 **Telegram Alerts** | Instant push notifications via Telegram Bot API on arrival & departure |
| 🛡️ **Smart Debouncing** | Requires 6 consecutive missed scans (~78s) before triggering "out of range" — no false alerts |
| 💾 **State Persistence** | Saves state to `ble_state.json` — survives restarts without duplicate alerts |
| ⚙️ **Systemd Ready** | Run as a background service that starts on boot |
| 🔐 **Secure Config** | Credentials loaded from environment variables — never hardcoded |

## 🏗️ How It Works

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
2. If the target device is found → mark as **"in range"**
3. If the target device is missing for **6 consecutive scans** → mark as **"out of range"**
4. On each **state change**, a Telegram message is sent instantly

## 📋 Requirements

- **Python** 3.8+
- **Linux** with Bluetooth adapter (built-in or USB BLE dongle)
- **BlueZ** (Linux Bluetooth stack)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/Umeshrane96/ble_whatsapp_notifier.git
cd ble_whatsapp_notifier
```

### 2. Set Up Python Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
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

### 4. Set Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
TELEGRAM_BOT_TOKEN=your-bot-token-here
TELEGRAM_CHAT_ID=your-chat-id-here
```

Then load them before running:

```bash
export $(cat .env | xargs)
```

### 5. Find Your Target BLE Device

Discover nearby BLE devices:

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

Update `TARGET_DEVICE` in the script with your device's MAC address.

### 6. Run

```bash
sudo -E python3 ble_whatsapp_notifier.py
```

> **Note:** `sudo` is required for BLE scanning on most Linux systems. The `-E` flag preserves your environment variables.

## 🔧 Configuration

| Parameter | Default | Description |
|:---|:---:|:---|
| `TARGET_DEVICE` | — | MAC address of the BLE device to track |
| `RSSI_THRESHOLD` | `-70` | Signal strength threshold in dBm |
| `SCAN_INTERVAL` | `3` | Seconds between scan cycles |
| `SCAN_DURATION` | `10` | Duration of each BLE scan in seconds |
| `MESSAGE_COOLDOWN` | `30` | Minimum seconds between messages |
| `MISS_THRESHOLD` | `6` | Consecutive misses before "out of range" |

### 📏 RSSI Reference

| RSSI (dBm) | Distance | Signal |
|:---:|:---|:---:|
| -30 to -50 | Very close (< 1m) | 🟢🟢🟢🟢 |
| -50 to -60 | Close (1–3m) | 🟢🟢🟢 |
| -60 to -70 | Nearby (3–5m) | 🟢🟢 |
| -70 to -80 | In range (5–10m) | 🟢 |
| < -80 | Far / unreliable | 🔴 |

## 🖥️ Run as Systemd Service (Raspberry Pi)

<details>
<summary><b>Click to expand setup instructions</b></summary>

<br>

1. **Create the service file:**

```bash
sudo tee /etc/systemd/system/ble-notifier.service > /dev/null << 'EOF'
[Unit]
Description=BLE Proximity Telegram Notifier
After=bluetooth.target network-online.target
Wants=network-online.target bluetooth.target

[Service]
Type=simple
User=root
EnvironmentFile=/home/umesh/ble_whatsapp_notifier/.env
ExecStartPre=/bin/sleep 5
ExecStart=/home/umesh/ble_whatsapp_notifier/venv/bin/python3 /home/umesh/ble_whatsapp_notifier/ble_whatsapp_notifier.py
WorkingDirectory=/home/umesh/ble_whatsapp_notifier
Restart=on-failure
RestartSec=15

[Install]
WantedBy=multi-user.target
EOF
```

2. **Enable and start:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable ble-notifier.service
sudo systemctl start ble-notifier.service
```

3. **Check status:**

```bash
sudo systemctl status ble-notifier.service
sudo journalctl -u ble-notifier.service -f
```

</details>

## 📁 Project Structure

```
ble_whatsapp_notifier/
├── ble_whatsapp_notifier.py   # Main script
├── .env.example               # Environment variable template
├── .gitignore                 # Git ignore rules
├── requirements.txt           # Python dependencies
├── LICENSE                    # MIT License
└── README.md                  # Documentation
```

## 🔍 Troubleshooting

<details>
<summary><b>"No Bluetooth adapters found"</b></summary>

- Ensure Bluetooth is enabled: `sudo hciconfig hci0 up`
- Check adapter exists: `hciconfig -a`
- Install BlueZ: `sudo apt install bluez`
</details>

<details>
<summary><b>"Permission denied" errors</b></summary>

- Run with `sudo`: `sudo -E python3 ble_whatsapp_notifier.py`
- Or add your user to the `bluetooth` group: `sudo usermod -aG bluetooth $USER`
</details>

<details>
<summary><b>Telegram messages not arriving</b></summary>

- Verify your bot token: `curl https://api.telegram.org/bot<TOKEN>/getMe`
- Ensure you've sent at least one message to the bot first
- Check that `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` environment variables are set
</details>

<details>
<summary><b>Device detected intermittently</b></summary>

- Increase `SCAN_DURATION` for more reliable detection
- The debouncing mechanism (6 missed scans) already handles occasional BLE flicker
- Move the Bluetooth adapter closer to the monitored area
</details>

## 🤝 Contributing

Contributions are welcome! Feel free to open an issue or submit a pull request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Made with ❤️ for home automation enthusiasts**

⭐ Star this repo if you find it useful!

</div>
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
