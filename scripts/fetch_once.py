# scripts/fetch_once.py
import os
import json
import requests
from datetime import datetime

host = os.getenv("XTREAM_HOST")
user = os.getenv("XTREAM_USER")
passwd = os.getenv("XTREAM_PASS")

if not all([host, user, passwd]):
    print("❌ Error: Missing XTREAM_HOST, XTREAM_USER, or XTREAM_PASS")
    exit(1)

print(f"📡 Fetching streams from {host}...")

base_url = f"{host}/player_api.php"
params = {"username": user, "password": passwd}

try:
    # Fetch categories
    cat_resp = requests.get(
        f"{base_url}?action=get_live_categories",
        params=params,
        timeout=10
    )
    cat_resp.raise_for_status()
    categories = cat_resp.json()
    cat_map = {str(c["category_id"]): c["category_name"] for c in categories}

    # Fetch streams
    stream_resp = requests.get(
        f"{base_url}?action=get_live_streams",
        params=params,
        timeout=10
    )
    stream_resp.raise_for_status()
    streams = stream_resp.json()

    print(f"✅ Loaded {len(streams)} streams, {len(categories)} categories")
except Exception as e:
    print(f"❌ API error: {e}")
    exit(1)

# Test streams and keep only working ones
healthy = []
for s in streams:
    url = s.get("stream_url")
    name = s.get("name", "Unknown")
    cat_id = str(s.get("category_id", ""))
    category = cat_map.get(cat_id, "Other")

    if not url or not name:
        continue

    try:
        # Lightweight check
        r = requests.head(
            url,
            timeout=5,
            headers={"User-Agent": "VLC/3.0.16"},
            allow_redirects=True
        )
        if r.status_code in (200, 206, 301, 302):
            healthy.append({
                "url": url,
                "name": name,
                "category": category,
                "added_at": datetime.utcnow().isoformat()
            })
        elif r.status_code == 403:
            # Some Xtreams allow GET but block HEAD
            r2 = requests.get(
                url,
                timeout=5,
                headers={"User-Agent": "VLC/3.0.16", "Range": "bytes=0-1024"},
                stream=True
            )
            if r2.status_code in (200, 206):
                healthy.append({
                    "url": url,
                    "name": name,
                    "category": category,
                    "added_at": datetime.utcnow().isoformat()
                })
    except Exception as e:
        print(f"  ❌ {name}: {e}")

print(f"✅ {len(healthy)} working streams found")

# Load existing database
os.makedirs("data", exist_ok=True)
streams_file = "data/streams.json"
db = {}
if os.path.exists(streams_file):
    with open(streams_file, "r", encoding="utf-8") as f:
        try:
            db = json.load(f)
        except:
            pass

# Normalize name for grouping
def normalize(name):
    return name.strip().lower().replace(" ", "_").replace("-", "_").replace(".", "_")

# Add to DB
for item in healthy:
    key = normalize(item["name"])
    if key not in db:
        db[key] = []
    # Avoid duplicates
    if not any(existing["url"] == item["url"] for existing in db[key]):
        db[key].append(item)

# Save back
with open(streams_file, "w", encoding="utf-8") as f:
    json.dump(db, f, indent=2, ensure_ascii=False)

print("💾 Saved to data/streams.json")
