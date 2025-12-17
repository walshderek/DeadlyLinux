import sys
import os
import time
import json
import requests
from urllib.parse import quote_plus
from pathlib import Path
from typing import List

# --- BOOTSTRAP PATHS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
import utils

# Ensure Playwright is available
try:
    from playwright.sync_api import sync_playwright, TimeoutError
except ImportError:
    utils.install_package("playwright")
    import subprocess
    subprocess.run([sys.executable, "-m", "playwright", "install"], check=True)
    from playwright.sync_api import sync_playwright, TimeoutError

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# --- ANTI-HANG CONFIG (Section XXV) ---
MAX_STALEMATE_COUNT = 3      # Stop after 3 failed scrolls (was 15)
SCROLL_DELAY = 1.5           # Seconds between scrolls (was 2)
PAGE_LOAD_TIMEOUT = 15000    # 15 seconds for page load (was 120s)
DOWNLOAD_TIMEOUT = 5         # 5 seconds for image download

def download_image(url, save_path):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=DOWNLOAD_TIMEOUT)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
    except: pass
    return False

def scrape_bing_playwright(query, limit, save_dir, prefix, start_idx=1):
    print(f"--> Launching Playwright for Bing: '{query}'")
    search_url = f"https://www.bing.com/images/search?q={quote_plus(query)}&form=HDRSC3&first=1"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
        except TimeoutError:
            print(f"❌ Bing page load timed out after {PAGE_LOAD_TIMEOUT/1000}s.")
            browser.close()
            return 0
        time.sleep(SCROLL_DELAY)
        
        urls = []
        seen = set()
        stagnation_counter = 0
        
        print(f"--> Scrolling to find {limit} images...")
        
        while len(urls) < limit:
            prev_len = len(urls)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(SCROLL_DELAY)
            
            thumbnails = page.query_selector_all("a.iusc")
            for thumb in thumbnails:
                if len(urls) >= limit: break
                m = thumb.get_attribute("m")
                if m:
                    try:
                        data = json.loads(m)
                        img_url = data.get("murl")
                        if img_url and img_url.startswith("http") and img_url not in seen:
                            seen.add(img_url)
                            urls.append(img_url)
                    except: pass
            
            # STALEMATE CHECK - count ALWAYS increments if no new images
            if len(urls) == prev_len:
                stagnation_counter += 1
                print(f"    Found {len(urls)} unique URLs... (stale x{stagnation_counter})", end='\r')
                
                # Try clicking 'See more' buttons (but don't reset counter!)
                try:
                    if page.is_visible("input[value*='See more']"):
                        page.click("input[value*='See more']", timeout=1000)
                        time.sleep(SCROLL_DELAY)
                    elif page.is_visible(".btn_seemore"):
                        page.click(".btn_seemore", timeout=1000)
                        time.sleep(SCROLL_DELAY)
                except: pass
                
                # HARD BREAK after MAX_STALEMATE_COUNT failures
                if stagnation_counter >= MAX_STALEMATE_COUNT:
                    print(f"\n⚠️ Stalemate reached (No new images after {MAX_STALEMATE_COUNT} scrolls). Moving on.")
                    break
            else:
                stagnation_counter = 0
                print(f"    Found {len(urls)} unique URLs...", end='\r')

        browser.close()
        
    print(f"\n--> Downloading {len(urls)} images...")
    
    saved = 0
    idx = start_idx
    for url in urls:
        if saved >= limit: break
        ext = os.path.splitext(url)[1].lower()
        if ext not in ALLOWED_EXTENSIONS: ext = ".jpg"
        ext = ext.split('?')[0]
        filename = f"{prefix}_{idx:04d}{ext}"
        if download_image(url, save_dir / filename):
            saved += 1
            idx += 1
            print(f"    Downloaded: {filename} [{saved}/{limit}]", end='\r')
    print(f"\n✅ Downloaded images.")
    return saved


def run(slug):
    # 1. Load Config (Orchestrator saved this)
    config = utils.load_config(slug)
    if not config:
        print(f"❌ Error: Config not found for {slug}")
        return

    # 2. Extract settings
    limit = config.get('limit', 100)
    name = config.get('name', slug.replace("_", " ").title())
    
    # HYBRID APPROACH: Use person-specific disambiguation terms
    # Better for famous people - avoids cartoon/fictional characters
    queries = [
        f'"{name}" actor OR politician OR celebrity',  # Primary - disambiguate from fiction
        f'"{name}" portrait photo',                    # Backup 1 - face focused
        f'"{name}" headshot',                          # Backup 2 - professional shots
        f'"{name}" interview',                         # Backup 3 - real person context
        f'"{name}" award ceremony',                    # Backup 4 - public appearances
    ]

    # 3. Setup Paths
    path = utils.get_project_path(slug)
    scrape_dir = path / utils.DIRS['scrape']
    scrape_dir.mkdir(parents=True, exist_ok=True)

    # 4. Check existing
    existing = [f for f in os.listdir(scrape_dir) if f.lower().endswith(tuple(ALLOWED_EXTENSIONS))]
    if len(existing) >= limit:
        print(f"✅ Found {len(existing)} images, skipping scrape.")
        return

    # 5. Run scrape using multiple queries until we hit the limit
    downloaded = len(existing)
    for query in queries:
        remaining = limit - downloaded
        if remaining <= 0:
            break
        saved = scrape_bing_playwright(query, remaining, scrape_dir, slug, start_idx=downloaded + 1)
        downloaded += saved
    
    print(f"📸 Total scraped: {downloaded} images")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])