# scripts/guardian_loop.py
import os
import json
import time
import subprocess
import requests
from datetime import datetime

TG_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT = os.getenv("TG_CHAT_ID")

def send_telegram(text):
    if not TG_TOKEN or not TG_CHAT:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={
                "chat_id": TG_CHAT,
                "text": text[:4000],
                "disable_web_page_preview": True
            },
            timeout=10
        )
    except Exception as e:
        print(f"⚠️ Telegram send failed: {e}")

def is_stream_alive(url):
    try:
        r = requests.head(
            url,
            timeout=5,
            headers={"User-Agent": "VLC/3.0.16"},
            allow_redirects=True
        )
        return r.status_code in (200, 206, 301, 302, 403)
    except:
        return False

def build_m3u():
    streams_file = "data/streams.json"
    if not os.path.exists(streams_file):
        return ["#EXTM3U", "# No streams. Add Xtream via Telegram."]

    try:
        with open(streams_file, "r", encoding="utf-8") as f:
            db = json.load(f)
    except Exception as e:
        print(f"❌ JSON load error: {e}")
        return ["#EXTM3U", "# Error loading streams.json"]

    lines = ["#EXTM3U"]
    for key, candidates in db.items():
        if not candidates:
            continue
        # Sort by newest first
        candidates.sort(key=lambda x: x.get("added_at", ""), reverse=True)
        selected = None
        for cand in candidates:
            if is_stream_alive(cand.get("url", "")):
                selected = cand
                break
        name = selected["name"] if selected else candidates[0]["name"] + " ❌"
        category = selected["category"] if selected else candidates[0]["category"]
        url = selected["url"] if selected else candidates[0]["url"]
        lines.append(f'#EXTINF:-1 group-title="{category}",{name}')
        lines.append(url)
    return lines

# Main loop
start_time = time.time()
send_telegram("🛡️ Guardian started. Checking every 10s.")
print("🛡️ Guardian started.")

try:
    while time.time() - start_time < 5 * 3600 + 50 * 60:  # 5h50m
        new_m3u = build_m3u()

        # Read current m3u
        current_m3u = []
        if os.path.exists("master.m3u"):
            with open("master.m3u", "r", encoding="utf-8") as f:
                current_m3u = [line.rstrip() for line in f]

        # Save if changed
        if new_m3u != current_m3u:
            with open("master.m3u", "w", encoding="utf-8") as f:
                f.write("\n".join(new_m3u) + "\n")

            # Try to commit
            try:
                subprocess.run(["git", "config", "user.name", "Guardian"], check=True)
                subprocess.run(["git", "config", "user.email", "actions@github.com"], check=True)
                subprocess.run(["git", "add", "master.m3u"], check=True)
                diff = subprocess.run(["git", "diff", "--quiet", "master.m3u"], capture_output=True)
                if diff.returncode != 0:
                    subprocess.run(["git", "commit", "-m", "🛡️ Auto M3U update"], check=True)
                    subprocess.run(["git", "push"], check=True)
                    send_telegram(f"✅ Updated master.m3u ({len(new_m3u)-1} channels)")
                    print("✅ Pushed update")
            except subprocess.CalledProcessError as e:
                print(f"⚠️ Git error: {e}")

        time.sleep(10)

except KeyboardInterrupt:
    pass

send_telegram("🛑 Guardian job ended (max runtime).")
print("⏰ Guardian ended.")
