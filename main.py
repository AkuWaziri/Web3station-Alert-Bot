"""
Crypto/NFT Intelligence Bot
Collects crypto/NFT/DeFi/AI-crypto signal from free sources, then runs it through
an LLM "editor" pass that aggressively filters down to only genuine content
opportunities -- important, trending, surprising, controversial, or connected to
your watched protocols -- and generates ready-to-post drafts for each.

Runs on a schedule via GitHub Actions (see .github/workflows/alert.yml)
"""

import os
import re
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
CRYPTOPANIC_KEY = os.environ.get("CRYPTOPANIC_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# comma-separated list of protocols you actively watch/follow
PROTOCOLS = [p.strip() for p in os.environ.get("PROTOCOLS", "Arc Network,Base").split(",") if p.strip()]

# your content focus areas -- edit this list any time to steer the editor
CONTENT_AREAS = [
    "Crypto", "DeFi", "AI x Crypto", "AI agents", "Stablecoins", "RWA",
    "Onchain activity", "Wallet infrastructure", "Payments", "Airdrops",
    "Protocol launches", "Crypto culture", "Emerging narratives", "Crypto memes",
]

RECENCY_HOURS = 72
SEEN_FILE = "seen_ids.json"
MAX_ITEMS_TO_EDITOR = 70  # cap prompt size

RSS_FEEDS = {
    "CoinTelegraph": "https://cointelegraph.com/rss",
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Decrypt": "https://decrypt.co/feed",
    "Medium-Crypto": "https://medium.com/feed/tag/cryptocurrency",
    "Medium-NFT": "https://medium.com/feed/tag/nft",
    "Reddit-CryptoCurrency": "https://www.reddit.com/r/CryptoCurrency/new/.rss",
    "Reddit-NFT": "https://www.reddit.com/r/NFT/new/.rss",
    "Reddit-CryptoMoonShots": "https://www.reddit.com/r/CryptoMoonShots/new/.rss",
    "Reddit-defi": "https://www.reddit.com/r/defi/new/.rss",
}


# ---------- HELPERS ----------
def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    trimmed = list(seen)[-3000:]
    with open(SEEN_FILE, "w") as f:
        json.dump(trimmed, f)


def item_id(title, link):
    return hashlib.sha256((title + link).encode()).hexdigest()[:16]


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
            summary = re.sub("<[^<]+?>", "", entry.get("summary", ""))[:280]
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
                "title": f"Trending on CoinGecko: {c['name']} ({c['symbol'].upper()}) - rank #{c.get('market_cap_rank', 'N/A')}",
                "link": f"https://www.coingecko.com/en/coins/{c['id']}",
                "summary": "",
                "published": now,
            })
    except Exception as e:
        print(f"CoinGecko fetch failed: {e}")
    return items


# ---------- LLM EDITOR ----------
def build_editor_system_prompt():
    protocols_str = ", ".join(PROTOCOLS)
    areas_str = ", ".join(CONTENT_AREAS)
    return f"""You are a sharp, highly selective personal crypto editor. Your job is to look at a
batch of raw crypto/NFT/DeFi news, Reddit posts, and trending signals, and pick out ONLY the items
that represent a genuinely good opportunity for your user to create original X (Twitter) content.

USER'S CONTENT FOCUS AREAS: {areas_str}
PROTOCOLS THE USER ACTIVELY FOLLOWS: {protocols_str}

FILTER AGGRESSIVELY. Most items should be REJECTED. Only pick items that are:
- important, rapidly trending, surprising, or controversial
- useful or under-covered (not something everyone already posted about)
- relevant to the user's content focus areas above
- connected to one of the user's followed protocols, OR
- capable of producing a genuinely original insight or meme

It is completely fine and expected to return an EMPTY list if nothing in the batch is worth posting about.
Do not force opportunities that aren't there. No artificial shilling of the followed protocols --
only mention a protocol connection if it's real and natural.

For each item you select, determine:
- priority: "BREAKING" (urgent, send now), "HIGH" (strong opportunity, send now), or "DAILY" (good but can wait for a digest)
- why_now: 1-2 short bullet-style reasons this deserves attention right now
- protocol_connection: if relevant to a followed protocol, explain the natural connection; otherwise null
- angle: the single strongest angle to take (analytical, contrarian, educational, humorous/meme, or "what people are missing") -- pick the angle with the most intellectual value, not automatically the most bullish one
- draft_post: ONE ready-to-post X draft in the chosen angle. Sound like a real, sharp crypto-native
  professional with strong opinions: concise, specific, some personality, skepticism where warranted.
  Make a clear, confident claim or observation -- do NOT default to ending with a question. Professional
  content creators state a position and let people react to it; they don't beg for engagement with
  "what's your take?", "thoughts?", "bullish or bearish?" or similar question hooks. A question is only
  acceptable if it's genuinely the sharpest way to make the point (rare), not a default closer.
  Vary the structure: sometimes a bold claim, sometimes a specific number/detail with an implication,
  sometimes a contrarian statement, sometimes "everyone's saying X, but Y is what actually matters."
  NEVER use phrases like "this changes everything", "the future is here", "revolutionary" unless truly
  warranted. No hashtag spam (max 1-2 if natural). No corporate/marketing tone. No forced excitement.
  Hard limit 280 characters.
- is_meme: true if this is primarily a meme/culture opportunity rather than a news opportunity

Respond with ONLY valid JSON, no markdown fences, no commentary, in this exact shape:
{{"opportunities": [
  {{"priority": "HIGH", "headline": "...", "why_now": "...", "protocol_connection": null,
    "angle": "contrarian", "draft_post": "...", "is_meme": false, "source_index": 3}}
]}}

source_index refers to the numbered item in the batch you were given, so the user can trace back to the original source."""


def call_groq_editor(items):
    if not GROQ_API_KEY or not items:
        return None
    # build compact numbered batch
    lines = []
    for i, it in enumerate(items):
        age_hrs = round((datetime.now(timezone.utc) - it["published"]).total_seconds() / 3600, 1)
        lines.append(f"[{i}] ({it['source']}, {age_hrs}h ago) {it['title']} -- {it['summary'][:150]}")
    batch_text = "\n".join(lines)

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": build_editor_system_prompt()},
                    {"role": "user", "content": f"Here is the batch of {len(items)} items:\n\n{batch_text}"},
                ],
                "temperature": 0.6,
                "max_tokens": 3000,
            },
            timeout=45,
        )
        data = r.json()
        text = data["choices"][0]["message"]["content"].strip()
        # strip markdown fences if the model added them anyway
        text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
        parsed = json.loads(text)
        return parsed.get("opportunities", [])
    except Exception as e:
        print(f"Groq editor call failed: {e}")
        return None


# ---------- FORMATTING ----------
PRIORITY_EMOJI = {"BREAKING": "🔴", "HIGH": "🟠", "DAILY": "🟡"}


def format_opportunity(opp, source_item):
    emoji = PRIORITY_EMOJI.get(opp.get("priority", "DAILY"), "🟡")
    meme_tag = "😂 MEME OPPORTUNITY\n" if opp.get("is_meme") else ""
    lines = [
        f"{emoji} <b>{opp.get('headline', 'Untitled')}</b>",
        meme_tag.strip(),
        f"\n<b>Why now:</b> {opp.get('why_now', '')}",
    ]
    if opp.get("protocol_connection"):
        lines.append(f"\n<b>Protocol angle:</b> {opp['protocol_connection']}")
    lines.append(f"\n<b>Angle:</b> {opp.get('angle', '')}")
    lines.append(f"\n✍️ <b>Draft:</b>\n{opp.get('draft_post', '')}")
    if source_item:
        lines.append(f"\nSource: {source_item['source']} | {source_item['link']}")
    return "\n".join(l for l in lines if l.strip())


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

    # filter unseen
    new_items = []
    for it in all_items:
        iid = item_id(it["title"], it["link"])
        if iid in seen:
            continue
        it["id"] = iid
        new_items.append(it)

    print(f"New (unseen) items: {len(new_items)}")

    if not new_items:
        print("Nothing new this run.")
        return

    # most recent first, cap batch size for the editor prompt
    new_items.sort(key=lambda x: x["published"], reverse=True)
    batch = new_items[:MAX_ITEMS_TO_EDITOR]

    opportunities = call_groq_editor(batch)

    if opportunities is None:
        print("Editor call failed -- not sending anything this run (avoiding noisy fallback).")
        return

    if not opportunities:
        print("Editor reviewed the batch and found nothing worth posting about. Staying quiet.")
        # still mark batch as seen so we don't re-review the same items next run
        for it in batch:
            seen.add(it["id"])
        save_seen(seen)
        return

    print(f"Editor selected {len(opportunities)} opportunities out of {len(batch)} candidates.")

    # send BREAKING/HIGH immediately, bundle DAILY into one digest
    daily_batch = []
    for opp in opportunities:
        idx = opp.get("source_index")
        source_item = batch[idx] if isinstance(idx, int) and 0 <= idx < len(batch) else None
        priority = opp.get("priority", "DAILY")
        if priority in ("BREAKING", "HIGH"):
            send_telegram(format_opportunity(opp, source_item))
            time.sleep(1)
        else:
            daily_batch.append((opp, source_item))

    if daily_batch:
        digest_lines = ["🟡 <b>DAILY OPPORTUNITIES</b>\n"]
        for opp, source_item in daily_batch:
            digest_lines.append(format_opportunity(opp, source_item))
            digest_lines.append("\n---\n")
        send_telegram("\n".join(digest_lines))

    for it in batch:
        seen.add(it["id"])
    save_seen(seen)
    print(f"Sent {len(opportunities)} opportunities.")


if __name__ == "__main__":
    main()
