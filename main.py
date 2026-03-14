import os
import json
import time
import requests
from datetime import datetime

# ── Config (from environment variables) ───────────────────────────────
WHATSAPP_TOKEN   = os.environ.get("WHATSAPP_TOKEN")       # Your WhatsApp API token
WHATSAPP_PHONE   = os.environ.get("WHATSAPP_PHONE")       # Your phone number (with country code, e.g. 8801XXXXXXXXX)
PHONE_ID         = os.environ.get("WHATSAPP_PHONE_ID")    # WhatsApp Business Phone ID
CHECK_INTERVAL   = int(os.environ.get("CHECK_INTERVAL", "300"))  # seconds (default 5 min)

IUBAT_API = (
    "https://iubat.edu/wp-json/wp/v2/posts"
    "?per_page=10&_fields=id,title,link,date&orderby=date&order=desc"
)

SEEN_FILE = "seen_ids.json"

# ── Load/Save seen notice IDs ──────────────────────────────────────────
def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(ids):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(ids), f)

# ── Fetch latest notices from IUBAT ───────────────────────────────────
def fetch_notices():
    try:
        res = requests.get(IUBAT_API, timeout=15)
        res.raise_for_status()
        data = res.json()
        return [
            {
                "id":    str(item["id"]),
                "title": item["title"]["rendered"],
                "link":  item["link"],
                "date":  item["date"][:10],  # YYYY-MM-DD
            }
            for item in data
        ]
    except Exception as e:
        print(f"[{now()}] ERROR fetching notices: {e}")
        return []

# ── Send WhatsApp message ──────────────────────────────────────────────
def send_whatsapp(message):
    url = f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": WHATSAPP_PHONE,
        "type": "text",
        "text": {"body": message},
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        if res.status_code == 200:
            print(f"[{now()}] ✅ WhatsApp sent!")
        else:
            print(f"[{now()}] ❌ WhatsApp error: {res.text}")
    except Exception as e:
        print(f"[{now()}] ❌ WhatsApp exception: {e}")

# ── Format notification message ────────────────────────────────────────
def format_message(new_notices):
    count = len(new_notices)
    lines = [f"🎓 *IUBAT Notice Alert* — {count} new notice{'s' if count > 1 else ''}!\n"]
    for n in new_notices:
        lines.append(f"📋 *{n['title']}*")
        lines.append(f"📅 {n['date']}")
        lines.append(f"🔗 {n['link']}\n")
    lines.append("—\nIUBAT Notice Tracker")
    return "\n".join(lines)

# ── Helpers ────────────────────────────────────────────────────────────
def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def strip_html(s):
    import re
    return re.sub(r"<[^>]+>", "", s).strip()

# ── Main loop ──────────────────────────────────────────────────────────
def main():
    print(f"[{now()}] 🚀 IUBAT Notice Tracker started")
    print(f"[{now()}] Checking every {CHECK_INTERVAL}s")

    seen = load_seen()
    first_run = len(seen) == 0

    while True:
        print(f"[{now()}] 🔍 Checking IUBAT notices...")
        notices = fetch_notices()

        if notices:
            new_notices = [n for n in notices if n["id"] not in seen]

            if first_run:
                # Just establish baseline, don't alert
                print(f"[{now()}] 📌 First run — saving {len(notices)} notices as baseline")
                for n in notices:
                    seen.add(n["id"])
                save_seen(seen)
                first_run = False

            elif new_notices:
                print(f"[{now()}] 🔔 {len(new_notices)} NEW notice(s) found!")
                for n in new_notices:
                    n["title"] = strip_html(n["title"])
                    print(f"  → {n['title']}")
                    seen.add(n["id"])

                save_seen(seen)
                msg = format_message(new_notices)
                send_whatsapp(msg)

            else:
                print(f"[{now()}] ✓ No new notices")
        else:
            print(f"[{now()}] ⚠ Could not fetch notices")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
