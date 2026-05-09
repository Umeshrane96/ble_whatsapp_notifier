#!/usr/bin/env python3
"""
BLE Proximity Telegram Notifier
================================
Continuously scans for a target BLE device and sends a Telegram message
when the device comes within range or goes out of range.

Run: python3 ble_whatsapp_notifier.py
"""

import asyncio
import json
import os
import time
import requests
from bleak import BleakScanner

# ============== CONFIGURATION ==============

# Target BLE device MAC address (the nearest device we found)
TARGET_DEVICE = "F3:10:D1:67:36:08"

# RSSI threshold — device is "nearby" if signal is stronger (less negative) than this
# -60 = very close (~1-2m), -70 = nearby (~3-5m), -80 = in range (~5-10m)
RSSI_THRESHOLD = -70

# Scan interval in seconds (pause between scans)
SCAN_INTERVAL = 3

# Scan duration per cycle in seconds (longer = more reliable detection)
SCAN_DURATION = 10

# Cooldown: minimum seconds between messages (avoid spam)
MESSAGE_COOLDOWN = 30  # 30 seconds (for testing, increase to 300 for production)

# ============ TELEGRAM SETTINGS ============

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# ===========================================================


def send_telegram_message(message):
    """Send a Telegram message via Bot API."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            print(f"  [OK] Telegram message sent!")
            return True
        else:
            print(f"  [FAIL] Telegram API returned status {response.status_code}")
            print(f"         Response: {response.text[:200]}")
            return False
    except requests.RequestException as e:
        print(f"  [ERROR] Failed to send Telegram message: {e}")
        return False


async def scan_for_device():
    """Scan for BLE devices and return target device info if found."""
    devices = await BleakScanner.discover(timeout=SCAN_DURATION, return_adv=True)
    for addr, (device, adv) in devices.items():
        if addr.upper() == TARGET_DEVICE.upper():
            name = adv.local_name or device.name or "Unknown"
            return {"address": addr, "name": name, "rssi": adv.rssi}
    return None


async def main():
    print("=" * 60)
    print("  BLE Proximity Telegram Notifier")
    print("=" * 60)
    print(f"  Target device : {TARGET_DEVICE}")
    print(f"  RSSI threshold: {RSSI_THRESHOLD} dBm")
    print(f"  Scan interval : {SCAN_INTERVAL}s")
    print(f"  Cooldown      : {MESSAGE_COOLDOWN}s")
    print(f"  Telegram chat : {TELEGRAM_CHAT_ID}")
    print("=" * 60)

    last_message_time = 0
    miss_count = 0
    MISS_THRESHOLD = 6  # Must miss 6 consecutive scans (~72s) before "out of range"
    STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ble_state.json")

    # Load saved state
    def load_state():
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                return json.load(f).get("in_range", True)
        return True  # Assume in range on first run

    def save_state(in_range):
        with open(STATE_FILE, "w") as f:
            json.dump({"in_range": in_range, "updated": time.strftime('%Y-%m-%d %H:%M:%S')}, f)

    was_detected = load_state()
    print(f"  Saved state   : {'IN range' if was_detected else 'OUT of range'}")

    print("\nStarting continuous BLE scan... (Ctrl+C to stop)\n")

    while True:
        try:
            result = await scan_for_device()
            now = time.time()
            timestamp = time.strftime("%H:%M:%S")

            if result:
                rssi = result["rssi"]
                miss_count = 0
                print(f"[{timestamp}] Device detected: {result['address']} "
                      f"(RSSI: {rssi} dBm, Name: {result['name']})")

                if not was_detected:
                    message = (
                        f"🏠 Home Minister arrived at home! "
                        f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    print(f"  Sending Telegram notification...")
                    send_telegram_message(message)
                    was_detected = True
                    save_state(True)

            else:
                miss_count += 1
                print(f"[{timestamp}] Device not detected (miss {miss_count}/{MISS_THRESHOLD})")
                if was_detected and miss_count >= MISS_THRESHOLD:
                    message = (
                        f"🚶 Home Minister left home! "
                        f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    print(f"  Sending 'out of range' Telegram notification...")
                    send_telegram_message(message)
                    was_detected = False
                    save_state(False)

        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Scan error: {e}")

        await asyncio.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nStopped by user.")
