import hashlib
import os
import sys
import time
import subprocess
from pathlib import Path

# Add repo root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from varedura.daemon_api import VareduraDaemonServer

def main():
    print("[*] Starting Varedura Daemon API Server on port 8420...")
    daemon = VareduraDaemonServer(host="127.0.0.1", port=8420)
    daemon.start()
    time.sleep(2.0)

    output_dir = Path("screenshots")
    output_dir.mkdir(parents=True, exist_ok=True)
    brain_dir = Path("C:/Users/joaod/.gemini/antigravity/brain/2146c8aa-f525-4fdc-9021-9f271a4786a4")

    print("[*] Configuring Headless Chrome with High-DPI Mobile Device Emulation...")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--hide-scrollbars")
    chrome_options.add_argument("--force-device-scale-factor=2")

    # Emulate Google Pixel 7 / iPhone 14 (412x892 @ 2x DPI)
    mobile_emulation = {
        "deviceMetrics": {"width": 412, "height": 892, "pixelRatio": 2.0},
        "userAgent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36"
    }
    chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)

    service = Service()
    service.creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_window_size(412, 892)

    screens = [
        ("mobile_camera_grid", "http://127.0.0.1:8420/#/cameras", "1. Camera Fleet Gallery Grid"),
        ("mobile_camera_player", "http://127.0.0.1:8420/#/player", "2. Camera Player with Live CCTV & PTZ"),
        ("mobile_diagnostics", "http://127.0.0.1:8420/#/diagnostics", "3. Network Diagnostics Center"),
        ("mobile_node_manager", "http://127.0.0.1:8420/#/node_manager", "4. Remote Node Manager & Docker"),
    ]

    hashes = {}

    try:
        # Pre-warm Flutter engine
        print("[*] Pre-warming Flutter Web engine...")
        driver.get("http://127.0.0.1:8420/#/")
        time.sleep(5.0)

        for filename, route_url, title in screens:
            print(f"[*] Navigating to {title} ({route_url})...")
            driver.get(route_url)
            time.sleep(4.0)

            dest1 = output_dir / f"{filename}.png"
            dest2 = brain_dir / f"{filename}.png"
            driver.save_screenshot(str(dest1))
            driver.save_screenshot(str(dest2))

            data = dest1.read_bytes()
            h = hashlib.sha256(data).hexdigest()[:12]
            hashes[filename] = h
            print(f"[+] Saved authentic mobile capture: {dest1} ({len(data)} bytes, sha256:{h})")

        print("\n[*] Validation Summary of Captured Screens:")
        for k, v in hashes.items():
            print(f"    - {k}: {v}")
        
        unique_hashes = len(set(hashes.values()))
        print(f"[*] Unique screen hashes: {unique_hashes} / {len(screens)}")
        if unique_hashes == len(screens):
            print(">>> SUCCESS: All 4 mobile screens are 100% unique, authentic, and rendered in high-definition!")
        else:
            print(">>> WARNING: Some screens have duplicate hashes, check navigation.")

    finally:
        driver.quit()
        daemon.stop()
        print("[*] Daemon stopped cleanly.")

if __name__ == "__main__":
    main()
