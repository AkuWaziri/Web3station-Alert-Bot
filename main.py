"""
Crypto/NFT Intelligence Bot
Collects crypto/NFT/DeFi/AI-crypto signal from free sources, clusters duplicate
stories, tracks trend velocity across runs, then hands the result to an LLM
"editor" that aggressively filters down to only genuine content opportunities
and generates ready-to-post drafts for each.

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

PROTOCOLS = [p.strip() for p in os.environ.get("PROTOCOLS", "Arc Network,Base").split(",") if p.strip()]

CONTENT_AREAS = [
    "Crypto", "DeFi", "AI x Crypto", "AI agents", "Stablecoins", "RWA",
    "Onchain activity", "Wallet infrastructure", "Payments", "Airdrops",
    "Protocol launches", "Crypto culture", "Emerging narratives", "Crypto memes",
]

RECENCY_HOURS = 72
SEEN_FILE = "seen_ids.json"
TOPIC_HISTORY_FILE = "topic_history.json"
MAX_CLUSTERS_TO_EDITOR = 60
CLUSTER_SIMILARITY_THRESHOLD = 0.42  # jaccard on significant words
HISTORY_RETENTION_DAYS = 14

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

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "be",
    "been", "being", "to", "of", "in", "on", "at", "for", "with", "by",
    "from", "as", "this", "that", "these", "those", "it", "its", "will",
    "has", "have", "had", "not", "no", "how", "what", "why", "when", "who",
    "new", "says", "say", "said", "after", "over", "into", "amid", "amid",
    "now", "just", "about", "than", "more", "most", "up", "down", "out",
}


# ---------- HELPERS ----------
def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)


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
                "source": name, "title": title, "link": link,
                "summary": summary, "published": pub_dt,
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
                "source": "CryptoPanic", "title": post.get("title", ""),
                "link": post.get("url", ""), "summary": "", "published": pub_dt,
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
                "summary": "", "published": now,
            })
    except Exception as e:
        print(f"CoinGecko fetch failed: {e}")
    return items


# ---------- DEDUP CLUSTERING ----------
def significant_words(title):
    words = re.findall(r"[a-zA-Z0-9]+", title.lower())
    return {w for w in words if len(w) > 3 and w not in STOPWORDS}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def cluster_items(items):
    """Greedy clustering: group items whose titles share enough significant words."""
    clusters = []  # each: {"representative": item, "members": [items], "words": set}
    for it in items:
        words = significant_words(it["title"])
        best_cluster = None
        best_score = 0.0
        for c in clusters:
            score = jaccard(words, c["words"])
            if score > best_score:
                best_score = score
                best_cluster = c
        if best_cluster and best_score >= CLUSTER_SIMILARITY_THRESHOLD:
            best_cluster["members"].append(it)
            best_cluster["words"] |= words
            # keep the most detailed (longest summary) as representative
            if len(it.get("summary", "")) > len(best_cluster["representative"].get("summary", "")):
                best_cluster["representative"] = it
        else:
            clusters.append({"representative": it, "members": [it], "words": words})
    return clusters


def extract_topic_key(cluster):
    """A stable-ish key for tracking this topic's mentions over time."""
    words = sorted(cluster["words"], key=len, reverse=True)[:3]
    if not words:
        return "misc"
    return "-".join(sorted(words))


# ---------- TREND VELOCITY ----------
def prune_history(history, now):
    cutoff_iso = (now - timedelta(days=HISTORY_RETENTION_DAYS)).isoformat()
    for key in list(history.keys()):
        history[key] = [e for e in history[key] if e["ts"] >= cutoff_iso]
        if not history[key]:
            del history[key]


def compute_trend(topic_key, current_count, history, now):
    """Compare current cluster size to this topic's recent history to classify trend."""
    entries = history.get(topic_key, [])
    day_ago = (now - timedelta(hours=24)).isoformat()
    prior_entries = [e for e in entries if e["ts"] >= day_ago]
    prior_total = sum(e["count"] for e in prior_entries)
    has_history = len(entries) > 0

    if not has_history:
        status = "EMERGING" if current_count >= 1 else "NEW"
        pct = None
    elif prior_total == 0:
        status = "EMERGING"
        pct = None
    else:
        pct = round(((current_count - prior_total) / prior_total) * 100)
        if pct >= 80:
            status = "RISING" if current_count < 4 else "TRENDING"
        elif pct >= 20:
            status = "RISING"
        elif pct > -20:
            status = "TRENDING" if current_count >= 4 else "STEADY"
        else:
            status = "SATURATED" if current_count >= 4 else "DECLINING"

    # record this run's observation
    history.setdefault(topic_key, []).append({"ts": now.isoformat(), "count": current_count})
    return status, pct


# ---------- LLM EDITOR ----------
def build_editor_system_prompt():
    protocols_str = ", ".join(PROTOCOLS)
    areas_str = ", ".join(CONTENT_AREAS)
    return f"""You are a sharp, highly selective personal crypto editor. Your job is to look at a
batch of clustered crypto/NFT/DeFi story clusters -- each already deduplicated across sources, with a
trend status showing whether it's EMERGING, RISING, TRENDING, STEADY, SATURATED, or DECLINING -- and
pick out ONLY the ones that represent a genuinely good opportunity for your user to create original
X (Twitter) content.

USER'S CONTENT FOCUS AREAS: {areas_str}
PROTOCOLS THE USER ACTIVELY FOLLOWS: {protocols_str}

FILTER AGGRESSIVELY. Most clusters should be REJECTED. Strongly prioritize EMERGING and RISING topics --
the goal is to catch things BEFORE they're saturated, not to comment on something everyone already covered.
Be skeptical of SATURATED topics unless you have a genuinely fresh angle nobody else has taken.

Only pick clusters that are:
- important, rapidly trending, surprising, or controversial
- useful or under-covered
- relevant to the user's content focus areas above
- connected to one of the user's followed protocols, OR
- capable of producing a genuinely original insight or meme

It is completely fine and expected to return an EMPTY list if nothing is worth posting about.
Do not force protocol connections that aren't real.

For each cluster you select, determine:
- priority: "BREAKING", "HIGH", or "DAILY"
- why_now: 1-2 short reasons this deserves attention right now -- reference the trend status/velocity
  data you were given (e.g. "mentions up 140% in the last 24h across 5 independent sources")
- protocol_connection: natural connection to a followed protocol if relevant, else null
- angle: strongest angle (analytical, contrarian, educational, humorous/meme, or "what people are missing")
- draft_post: ONE ready-to-post X draft. Sound like a real, sharp crypto-native professional with strong
  opinions: concise, specific, some personality, skepticism where warranted. Make a clear, confident claim
  or observation -- do NOT default to ending with a question. Don't beg for engagement with "what's your
  take?" or similar. A question is only acceptable if it's genuinely the sharpest way to make the point.
  Vary structure: bold claim, specific detail with implication, contrarian statement, or "everyone's
  saying X, but Y is what matters." NEVER use "this changes everything", "the future is here",
  "revolutionary" unless truly warranted. No hashtag spam (max 1-2). No corporate tone. Hard limit 280 chars.
- is_meme: true if primarily a meme/culture opportunity

Respond with ONLY valid JSON, no markdown fences, no commentary:
{{"opportunities": [
  {{"priority": "HIGH", "headline": "...", "why_now": "...", "protocol_connection": null,
    "angle": "contrarian", "draft_post": "...", "is_meme": false, "cluster_index": 3}}
]}}

cluster_index refers to the numbered cluster in the batch you were given."""


def call_groq_editor(clusters_text, num_clusters):
    if not GROQ_API_KEY or num_clusters == 0:
        return None
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": build_editor_system_prompt()},
                    {"role": "user", "content": f"Here are {num_clusters} story clusters:\n\n{clusters_text}"},
                ],
                "temperature": 0.6,
                "max_tokens": 3000,
            },
            timeout=45,
        )
        data = r.json()
        text = data["choices"][0]["message"]["content"].strip()
        text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
        parsed = json.loads(text)
        return parsed.get("opportunities", [])
    except Exception as e:
        print(f"Groq editor call failed: {e}")
        return None


# ---------- FORMATTING ----------
PRIORITY_EMOJI = {"BREAKING": "🔴", "HIGH": "🟠", "DAILY": "🟡"}
TREND_EMOJI = {
    "EMERGING": "⚡", "RISING": "📈", "TRENDING": "🔥",
    "STEADY": "➡️", "SATURATED": "🌊", "DECLINING": "📉", "NEW": "🆕",
}


def format_opportunity(opp, cluster):
    emoji = PRIORITY_EMOJI.get(opp.get("priority", "DAILY"), "🟡")
    meme_tag = "😂 MEME OPPORTUNITY\n" if opp.get("is_meme") else ""
    trend_status = cluster.get("trend_status", "") if cluster else ""
    trend_emoji = TREND_EMOJI.get(trend_status, "")
    source_count = len(cluster["members"]) if cluster else 1
    rep = cluster["representative"] if cluster else None

    lines = [
        f"{emoji} <b>{opp.get('headline', 'Untitled')}</b>",
        meme_tag.strip(),
    ]
    if trend_status:
        lines.append(f"{trend_emoji} {trend_status} | {source_count} source(s)")
    lines.append(f"\n<b>Why now:</b> {opp.get('why_now', '')}")
    if opp.get("protocol_connection"):
        lines.append(f"\n<b>Protocol angle:</b> {opp['protocol_connection']}")
    lines.append(f"\n<b>Angle:</b> {opp.get('angle', '')}")
    lines.append(f"\n✍️ <b>Draft:</b>\n{opp.get('draft_post', '')}")
    if rep:
        lines.append(f"\nSource: {rep['source']} | {rep['link']}")
    return "\n".join(l for l in lines if l.strip())


# ---------- MAIN ----------
def main():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=RECENCY_HOURS)

    seen = load_json(SEEN_FILE, [])
    seen = set(seen)
    topic_history = load_json(TOPIC_HISTORY_FILE, {})

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
        it["id"] = iid
        new_items.append(it)

    print(f"New (unseen) items: {len(new_items)}")

    if not new_items:
        print("Nothing new this run.")
        return

    new_items.sort(key=lambda x: x["published"], reverse=True)

    # ---- cluster duplicate stories ----
    clusters = cluster_items(new_items)
    print(f"Clustered {len(new_items)} items into {len(clusters)} story clusters")

    # ---- compute trend velocity per cluster ----
    for c in clusters:
        topic_key = extract_topic_key(c)
        status, pct = compute_trend(topic_key, len(c["members"]), topic_history, now)
        c["trend_status"] = status
        c["trend_pct"] = pct
        c["topic_key"] = topic_key

    prune_history(topic_history, now)

    # sort clusters: EMERGING/RISING/TRENDING first, then by size
    priority_order = {"EMERGING": 0, "RISING": 1, "TRENDING": 2, "NEW": 3, "STEADY": 4, "SATURATED": 5, "DECLINING": 6}
    clusters.sort(key=lambda c: (priority_order.get(c["trend_status"], 9), -len(c["members"])))
    batch = clusters[:MAX_CLUSTERS_TO_EDITOR]

    # ---- build editor prompt text ----
    lines = []
    for i, c in enumerate(batch):
        rep = c["representative"]
        age_hrs = round((now - rep["published"]).total_seconds() / 3600, 1)
        pct_str = f", {c['trend_pct']:+d}% vs prior 24h" if c["trend_pct"] is not None else ""
        source_names = ", ".join(sorted({m["source"] for m in c["members"]}))
        lines.append(
            f"[{i}] [{c['trend_status']}{pct_str}] ({len(c['members'])} source(s): {source_names}, "
            f"{age_hrs}h ago) {rep['title']} -- {rep['summary'][:150]}"
        )
    batch_text = "\n".join(lines)

    opportunities = call_groq_editor(batch_text, len(batch))

    if opportunities is None:
        print("Editor call failed -- not sending anything this run.")
        save_json(TOPIC_HISTORY_FILE, topic_history)
        return

    if not opportunities:
        print("Editor reviewed the batch and found nothing worth posting about. Staying quiet.")
        for it in new_items:
            seen.add(it["id"])
        save_json(SEEN_FILE, list(seen)[-3000:])
        save_json(TOPIC_HISTORY_FILE, topic_history)
        return

    print(f"Editor selected {len(opportunities)} opportunities out of {len(batch)} clusters.")

    daily_batch = []
    for opp in opportunities:
        idx = opp.get("cluster_index")
        cluster = batch[idx] if isinstance(idx, int) and 0 <= idx < len(batch) else None
        priority = opp.get("priority", "DAILY")
        if priority in ("BREAKING", "HIGH"):
            send_telegram(format_opportunity(opp, cluster))
            time.sleep(1)
        else:
            daily_batch.append((opp, cluster))

    if daily_batch:
        digest_lines = ["🟡 <b>DAILY OPPORTUNITIES</b>\n"]
        for opp, cluster in daily_batch:
            digest_lines.append(format_opportunity(opp, cluster))
            digest_lines.append("\n---\n")
        send_telegram("\n".join(digest_lines))

    for it in new_items:
        seen.add(it["id"])
    save_json(SEEN_FILE, list(seen)[-3000:])
    save_json(TOPIC_HISTORY_FILE, topic_history)
    print(f"Sent {len(opportunities)} opportunities.")


if __name__ == "__main__":
    main()
