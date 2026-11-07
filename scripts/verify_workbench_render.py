import os
import sys
import time
import subprocess
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

def main():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1400,2400")

    service = Service()
    service.creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    driver = webdriver.Chrome(service=service, options=chrome_options)
    try:
        html_path = Path("C:/Users/joaod/Documents/GitHub/Varedura/workbench.html").resolve().as_uri()
        print(f"[*] Loading workbench at {html_path}...")
        driver.get(html_path)
        time.sleep(2.0)

        preview_dest = Path("screenshots/workbench_preview.png")
        brain_preview = Path("C:/Users/joaod/.gemini/antigravity/brain/2146c8aa-f525-4fdc-9021-9f271a4786a4/workbench_preview.png")
        driver.save_screenshot(str(preview_dest))
        driver.save_screenshot(str(brain_preview))
        print(f"[+] Saved workbench preview screenshot: {preview_dest} ({preview_dest.stat().st_size} bytes)")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
