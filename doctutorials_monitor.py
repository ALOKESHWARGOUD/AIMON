"""
DocTutorials Leak Monitoring Tool
Single-file implementation using AIMON framework
"""

import asyncio
import json
from datetime import datetime, timezone

# Import AIMON framework
from aimon import AIMON


# ==============================
# Configuration
# ==============================

SCAN_INTERVAL = 600

KEYWORDS = [
    "DocTutorials download",
    "DocTutorials lectures free",
    "DocTutorials telegram",
    "DocTutorials torrent",
    "DocTutorials google drive",
]

LEAK_KEYWORDS = [
    "download",
    "torrent",
    "telegram",
    "drive.google.com",
    "mega.nz",
    "free lectures",
]

RISK_THRESHOLD = 0.7

ALERT_FILE = "alerts_log.json"


# ==============================
# Leak Detection
# ==============================

def detect_leak(page_content: str):

    if not page_content:
        return {"risk_score": 0, "is_leak": False}

    content = page_content.lower()

    score = 0

    if "doctutorials" in content:
        score += 0.4

    for keyword in LEAK_KEYWORDS:
        if keyword in content:
            score += 0.15

    score = min(score, 1.0)

    return {
        "risk_score": score,
        "is_leak": score > RISK_THRESHOLD
    }


# ==============================
# Alert System
# ==============================

def send_alert(alert):

    print("\n🚨 LEAK ALERT DETECTED 🚨")
    print("Platform:", alert["platform"])
    print("URL:", alert["url"])
    print("Risk Score:", alert["risk_score"])
    print("")

    save_alert(alert)


def save_alert(alert):

    alert["timestamp"] = datetime.now(timezone.utc).isoformat()

    try:
        with open(ALERT_FILE, "a") as f:
            f.write(json.dumps(alert) + "\n")
    except Exception as e:
        print("Failed saving alert:", e)


# ==============================
# Scan Logic
# ==============================

async def scan_query(framework, query):

    print("\nSearching:", query)

    sources = await framework.search_sources(query)

    if not sources:
        print("No sources found")
        return

    for source in sources:

        try:

            url = source.get("url")

            if not url:
                continue

            page = await framework.crawler.crawl(source)

            content = page.get("content", "")

            result = detect_leak(content)

            if result["is_leak"]:

                alert = {
                    "platform": "DocTutorials",
                    "url": url,
                    "risk_score": result["risk_score"],
                    "type": "video_leak",
                }

                send_alert(alert)

        except Exception as e:
            print("Scan error:", e)


# ==============================
# Monitoring Engine
# ==============================

async def monitor():

    print("\nStarting DocTutorials Leak Monitor\n")

    async with AIMON() as framework:

        while True:

            print("\n==============================")
            print("Starting new scan cycle")
            print("==============================\n")

            for query in KEYWORDS:
                await scan_query(framework, query)

            print("\nScan complete")
            print("Sleeping for", SCAN_INTERVAL, "seconds\n")

            await asyncio.sleep(SCAN_INTERVAL)


# ==============================
# Entry Point
# ==============================

if __name__ == "__main__":

    try:
        asyncio.run(monitor())

    except KeyboardInterrupt:
        print("\nMonitoring stopped")
