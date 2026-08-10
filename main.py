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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

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

TWEET_HOOKS = [
    "🚨 {title}\n\nWhat's your take? 👇",
    "Just in: {title}\n\nBullish or bearish? 🤔",
    "This is huge 👀\n\n{title}\n\nThoughts?",
    "{title}\n\nEveryone's talking about this right now.",
    "Hot off the press 🔥\n\n{title}",
    "PSA for the timeline 📢\n\n{title}",
]

HASHTAG_MAP = {
    "airdrop": ["#Airdrop", "#CryptoAirdrop"],
    "nft": ["#NFT", "#NFTCommunity"],
    "hack": ["#CryptoSecurity", "#Web3Safety"],
    "exploit": ["#CryptoSecurity", "#Web3Safety"],
    "mint": ["#NFTMint"],
    "meme": ["#CryptoMemes", "#MemeCoin"],
    "trending": ["#Crypto", "#Altcoins"],
}
DEFAULT_HASHTAGS = ["#Crypto", "#Web3"]


def build_hashtags(title, summary=""):
    text = (title + " " + summary).lower()
    tags = []
    for kw, tag_list in HASHTAG_MAP.items():
        if kw in text:
            for t in tag_list:
                if t not in tags:
                    tags.append(t)
    if not tags:
        tags = DEFAULT_HASHTAGS
    return " ".join(tags[:3])


GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

TWEET_SYSTEM_PROMPT = (
    "You are a sharp, well-connected crypto Twitter poster with a real point of view. "
    "You write short, punchy takes that sound like a human who's actually paying attention "
    "to the market, not a headline bot. Given a news item, write ONE tweet reacting to it: "
    "connect it to a broader trend, add a hot take or a 'here's what this actually means' angle, "
    "and end with something that invites replies (a question, a bold claim, or a prediction). "
    "No hashtags spam (max 2, only if they fit naturally). No emojis unless they add punch (max 2). "
    "Sound confident and specific, not generic. Hard limit: 280 characters. "
    "Output ONLY the tweet text, nothing else."
)


def generate_tweet_llm(item):
    if not GROQ_API_KEY:
        return None
    try:
        prompt = f"News: {item['title']}\n{item.get('summary', '')[:400]}"
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": TWEET_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.9,
                "max_tokens": 150,
            },
            timeout=20,
        )
        data = r.json()
        text = data["choices"][0]["message"]["content"].strip()
        text = text.strip('"')
        if len(text) > 280:
            text = text[:277] + "..."
        return text
    except Exception as e:
        print(f"Groq tweet generation failed: {e}")
        return None


def generate_tweet_draft(item):
    llm_draft = generate_tweet_llm(item)
    if llm_draft:
        return llm_draft
    # fallback template if Groq is unavailable or key missing
    hook = TWEET_HOOKS[item["score"] % len(TWEET_HOOKS)]
    title = item["title"]
    if len(title) > 180:
        title = title[:177] + "..."
    hashtags = build_hashtags(item["title"], item.get("summary", ""))
    return hook.format(title=title) + f"\n\n{hashtags}"

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
    trimmed = list(seen)[-2000:]
    with open(SEEN_FILE, "w") as f:
        json.dump(trimmed, f)


def item_id(title, link):
    return hashlib.sha256((title + link).encode()).hexdigest()[:16]


def score_item(title, summary=""):
    text = (title + " " + summary).lower()
    return sum(1 for kw in KEYWORDS_HOT if kw in text)


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
        resp = requests.get(url, headers=HEADERS, timeout=15)
        feed = feedparser.parse(resp.content)
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
        r = requests.get(url, headers=HEADERS, timeout=15)
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
        r = requests.get("https://api.coingecko.com/api/v3/search/trending", headers=HEADERS, timeout=15)
        data = r.json()
        now = datetime.now(timezone.utc)
        for coin in data.get("coins", [])[:7]:
            c = coin["item"]
            items.append({
                "source": "CoinGecko Trending",
                "title": f"🔥 Trending: {c['name']} ({c['symbol'].upper()}) - rank #{c.get('market_cap_rank', 'N/A')}",
                "link": f"https://www.coingecko.com/en/coins/{c['id']}",
                "summary": "",
                "published": now,
            })
    except Exception as e:
        print(f"CoinGecko fetch failed: {e}")
    return items


# ---------- MAIN ----------
def main():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=RECENCY_HOURS)

    seen = load_seen()
    all_items = []

    for name, url in RSS_FEEDS.items():
        fetched = fetch_rss(name, url, cutoff)
        print(f"{name}: fetched {len(fetched)} items")
        all_items.extend(fetched)

    cp_items = fetch_cryptopanic(cutoff)
    print(f"CryptoPanic: fetched {len(cp_items)} items")
    all_items.extend(cp_items)

    cg_items = fetch_coingecko_trending()
    print(f"CoinGecko: fetched {len(cg_items)} items")
    all_items.extend(cg_items)

    print(f"Total items fetched: {len(all_items)}")

    new_items = []
    for it in all_items:
        iid = item_id(it["title"], it["link"])
        if iid in seen:
            continue
        it["score"] = score_item(it["title"], it["summary"])
        it["id"] = iid
        new_items.append(it)

    print(f"New (unseen) items: {len(new_items)}")

    new_items.sort(key=lambda x: (x["score"], x["published"]), reverse=True)

    scored = [it for it in new_items if it["score"] > 0]
    to_send = scored[:12] if scored else new_items[:5]

    if not to_send:
        print("No new relevant items this run.")
        return

    for it in to_send:
        age_hrs = round((now - it["published"]).total_seconds() / 3600, 1)
        emoji = "🚨" if it["score"] >= 3 else "📢"
        tweet_draft = generate_tweet_draft(it)
        msg = (
            f"{emoji} <b>{it['title']}</b>\n"
            f"Source: {it['source']} | {age_hrs}h ago\n"
            f"{it['link']}\n\n"
            f"✍️ <b>Tweet draft:</b>\n{tweet_draft}"
        )
        send_telegram(msg)
        seen.add(it["id"])
        time.sleep(1)

    save_seen(seen)
    print(f"Sent {len(to_send)} alerts.")


if __name__ == "__main__":
    main()
