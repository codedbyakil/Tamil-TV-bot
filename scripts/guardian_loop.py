#!/usr/bin/env python3
# scripts/guardian_loop.py
import os
import json
import time
import sys

print("🔍 Guardian started — checking environment...")
print(f"  TG_BOT_TOKEN set: {'Yes' if os.getenv('TG_BOT_TOKEN') else 'No'}")
print(f"  TG_CHAT_ID: {os.getenv('TG_CHAT_ID', 'N/A')}")

# Ensure data dir exists
os.makedirs("data", exist_ok=True)

# Initialize streams.json if missing
streams_path = "data/streams.json"
if not os.path.exists(streams_path):
    print(f"🛠️ Creating empty {streams_path}")
    with open(streams_path, "w") as f:
        json.dump({}, f)

# Create master.m3u if missing
m3u_path = "master.m3u"
if not os.path.exists(m3u_path):
    print(f"🛠️ Creating initial {m3u_path}")
    with open(m3u_path, "w") as f:
        f.write("#EXTM3U\n# Waiting for streams...\n")

print("✅ Setup complete. Starting 10s loop (max 5m for testing)...")
sys.stdout.flush()  # Force log flush

# Run for 5 minutes only (for testing)
START = time.time()
MAX_TEST = 300  # 5 minutes — change to 5*3600+50*60 for production

loop_count = 0
while time.time() - START < MAX_TEST:
    loop_count += 1
    print(f"[{loop_count}] 🔄 Loop start — checking streams.json...")
    sys.stdout.flush()

    try:
        with open(streams_path, "r") as f:
            db = json.load(f)
        print(f"  → Loaded {len(db)} channel groups")
    except Exception as e:
        print(f"  ❌ Error loading streams.json: {e}")
        db = {}

    # Simple m3u rebuild
    lines = ["#EXTM3U"]
    for name, candidates in db.items():
        if candidates:
            url = candidates[0].get("url", "#")
            title = candidates[0].get("name", name)
            cat = candidates[0].get("category", "Other")
            lines.append(f'#EXTINF:-1 group-title="{cat}",{title}')
            lines.append(url)

    # Save m3u
    try:
        with open(m3u_path, "w") as f:
            f.write("\n".join(lines) + "\n")
        print(f"  ✅ Updated {m3u_path} ({len(lines)-1} channels)")
    except Exception as e:
        print(f"  ❌ Failed to write m3u: {e}")

    print(f"[{loop_count}] 💤 Sleeping 10s...")
    sys.stdout.flush()
    time.sleep(10)

print("🎉 Test completed (5 min max). Guardian would run 5h50m in production.")
