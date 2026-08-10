"""
Crypto/NFT Alert Bot
Fetches recent crypto/NFT news, campaigns, and trending content from free sources,
filters for recency + relevance, and pushes formatted alerts to Telegram.

Runs on a schedule via GitHub Actions (see .github/workflows/alert.yml)
"""

import os
import json
import time
import hashlib
import requests
import feedparser
from datetime import datetime, timezone, timedelta

# ---------- CONFIG ----------
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
CRYPTOPANIC_KEY = os.environ.get("CRYPTOPANIC_KEY", "")  # optional, empty ok

RECENCY_HOURS = 72
ENDING_SOON_HOURS = 24
SEEN_FILE = "seen_ids.json"  # persisted between runs via git commit (see workflow)

KEYWORDS_HOT = [
    "airdrop", "mint", "presale", "giveaway", "hack", "exploit", "rug",
    "listing", "launch", "campaign", "whitelist", "claim", "reward",
    "meme", "pump", "moon", "breaking", "alert", "vulnerability", "drain",
]

RSS_FEEDS = {
    "CoinTelegraph": "https://cointelegraph.com/rss",
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Decrypt": "https://decrypt.co/feed",
    "Medium-Crypto": "https://medium.com/feed/tag/cryptocurrency",
    "Medium-NFT": "https://medium.com/feed/tag/nft",
    "Reddit-CryptoCurrency": "https://www.reddit.com/r/CryptoCurrency/new/.rss",
    "Reddit-NFT": "https://www.reddit.com/r/NFT/new/.rss",
    "Reddit-CryptoMoonShots": "https://www.reddit.com/r/CryptoMoonShots/new/.rss",
}


# ---------- HELPERS ----------
def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    # keep only last 2000 to avoid unbounded growth
    trimmed = list(seen)[-2000:]
    with open(SEEN_FILE, "w") as f:
        json.dump(trimmed, f)


def item_id(title, link):
    return hashlib.sha256((title + link).encode()).hexdigest()[:16]


def score_item(title, summary=""):
    text = (title + " " + summary).lower()
    score = sum(1 for kw in KEYWORDS_HOT if kw in text)
    return score


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    r = requests.post(url, data=payload, timeout=15)
    if not r.ok:
        print("Telegram send failed:", r.text)


# ---------- FETCHERS ----------
def fetch_rss(name, url, cutoff):
    items = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "")
            summary = entry.get("summary", "")[:300]
            published = entry.get("published_parsed") or entry.get("updated_parsed")
            if not published:
                continue
            pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
            if pub_dt < cutoff:
                continue
            items.append({
                "source": name,
                "title": title,
                "link": link,
                "summary": summary,
                "published": pub_dt,
            })
    except Exception as e:
        print(f"RSS fetch failed for {name}: {e}")
    return items


def fetch_cryptopanic(cutoff):
    items = []
    if not CRYPTOPANIC_KEY:
        return items
    try:
        url = f"https://cryptopanic.com/api/v1/posts/?auth_token={CRYPTOPANIC_KEY}&kind=news&public=true"
        r = requests.get(url, timeout=15)
        data = r.json()
        for post in data.get("results", []):
            pub_dt = datetime.fromisoformat(post["published_at"].replace("Z", "+00:00"))
            if pub_dt < cutoff:
                continue
            items.append({
                "source": "CryptoPanic",
                "title": post.get("title", ""),
                "link": post.get("url", ""),
                "summary": "",
                "published": pub_dt,
            })
    except Exception as e:
        print(f"CryptoPanic fetch failed: {e}")
    return items


def fetch_coingecko_trending():
    items = []
    try:
        r = requests.get("https://api.coingecko.com/api/v3/search/trending", timeout=15)
        data = r.json()
        now = datetime.now(timezone.utc)
        for coin in data.get("coins", [])[:7]:
            c = coin["item"]
            items.append({
                "source": "CoinGecko Trending",
                "title": f"🔥 Trending: {c['name']} ({c['symbol'].upper()}) - rank #{c.get('market_cap_rank', 'N/A')}",
                "link": f"https://www.coingecko.com/en/coins/{c['id']}",
                "summary": "",
                "published": now,  # trending is always \"now\"
            })
    except Exception as e:
        print(f"CoinGecko fetch failed: {e}")
    return items


# ---------- MAIN ----------
def main():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=RECENCY_HOURS)
    soon_cutoff = now + timedelta(hours=ENDING_SOON_HOURS)

    seen = load_seen()
    all_items = []

    for name, url in RSS_FEEDS.items():
        all_items.extend(fetch_rss(name, url, cutoff))

    all_items.extend(fetch_cryptopanic(cutoff))
    all_items.extend(fetch_coingecko_trending())

    # filter unseen + score
    new_items = []
    for it in all_items:
        iid = item_id(it["title"], it["link"])
        if iid in seen:
            continue
        it["score"] = score_item(it["title"], it["summary"])
        it["id"] = iid
        new_items.append(it)

    # sort: highest score first, then most recent
    new_items.sort(key=lambda x: (x["score"], x["published"]), reverse=True)

    # only push items with at least some signal, cap to avoid spam
    to_send = [it for it in new_items if it["score"] > 0][:12]

    if not to_send:
        print("No new relevant items this run.")
        return

    for it in to_send:
        age_hrs = round((now - it["published"]).total_seconds() / 3600, 1)
        emoji = "🚨" if it["score"] >= 3 else "📢"
        msg = (
            f"{emoji} <b>{it['title']}</b>\n"
            f"Source: {it['source']} | {age_hrs}h ago\n"
            f"{it['link']}"
        )
        send_telegram(msg)
        seen.add(it["id"])
        time.sleep(1)  # avoid Telegram rate limits

    save_seen(seen)
    print(f"Sent {len(to_send)} alerts.")


if __name__ == "__main__":
    main()
