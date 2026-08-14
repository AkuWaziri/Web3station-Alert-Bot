import os
import json
import time
import hashlib
from datetime import datetime, timezone
from html import unescape

import requests
import feedparser


# ============================================================
# CONFIGURATION
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

CMC_API_KEY = os.getenv("CMC_API_KEY", "")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LUNARCRUSH_API_KEY = os.getenv("LUNARCRUSH_API_KEY", "")
NEYNAR_API_KEY = os.getenv("NEYNAR_API_KEY", "")
SORSA_API_KEY = os.getenv("SORSA_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
)

MIN_SIGNAL_SCORE = float(
    os.getenv("MIN_SIGNAL_SCORE", "6")
)

MAX_ALERTS = int(
    os.getenv("MAX_ALERTS", "5")
)

WATCHLIST = [
    x.strip().upper()
    for x in os.getenv(
        "WATCHLIST",
        "BTC,ETH,SOL,USDC,USDT"
    ).split(",")
    if x.strip()
]

SEEN_FILE = "seen_ids.json"
TOPIC_FILE = "topic_history.json"


# ============================================================
# YOUR CORE NICHE
# ============================================================

TOPICS = [
    "stablecoin",
    "stablecoins",
    "payments",
    "crypto payments",
    "ai",
    "ai agent",
    "ai agents",
    "agentic",
    "defi",
    "rwa",
    "real world assets",
    "tokenization",
    "wallet",
    "wallets",
    "financial infrastructure",
    "onchain finance",
    "remittance",
    "usdc",
    "usdt",
    "ethereum",
    "bitcoin",
    "solana",
    "base",
    "arbitrum",
    "layer 2",
    "account abstraction",
    "security",
    "hack",
    "exploit",
    "funding",
    "mainnet",
    "launch",
    "regulation",
    "institutional",
    "nft",
    "digital ownership",
]


# ============================================================
# RSS SOURCES
# ============================================================

RSS_FEEDS = [
    (
        "CoinDesk",
        "https://www.coindesk.com/arc/outboundfeeds/rss/"
    ),
    (
        "Cointelegraph",
        "https://cointelegraph.com/rss"
    ),
]


# ============================================================
# HELPERS
# ============================================================

SESSION = requests.Session()

SESSION.headers.update({
    "User-Agent": "Web3Station/1.0"
})


def now():
    return datetime.now(timezone.utc).isoformat()


def safe_get(url, **kwargs):
    try:
        response = SESSION.get(
            url,
            timeout=20,
            **kwargs
        )

        if response.status_code == 200:
            return response

        print(
            f"[HTTP {response.status_code}] {url}"
        )

    except Exception as exc:
        print(
            f"[REQUEST ERROR] {url}: {exc}"
        )

    return None


def safe_post(url, **kwargs):
    try:
        response = SESSION.post(
            url,
            timeout=30,
            **kwargs
        )

        if response.status_code == 200:
            return response

        print(
            f"[POST HTTP {response.status_code}] {url}"
        )

        print(response.text[:500])

    except Exception as exc:
        print(
            f"[POST ERROR] {url}: {exc}"
        )

    return None


def load_json(path, default):
    try:
        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)

    except Exception:
        return default


def save_json(path, data):
    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False
        )


def clean_text(text):
    if not text:
        return ""

    text = unescape(str(text))

    return " ".join(
        text.replace("\n", " ").split()
    )


def make_id(*parts):
    raw = "|".join(
        str(part)
        for part in parts
        if part is not None
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def contains_topic(text):
    text = text.lower()

    return [
        topic
        for topic in TOPICS
        if topic.lower() in text
    ]


# ============================================================
# TELEGRAM
# ============================================================

def telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[TELEGRAM] Missing credentials")
        return False

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/sendMessage"
    )

    response = safe_post(
        url,
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
    )

    return response is not None


# ============================================================
# COINMARKETCAP
# ============================================================

def fetch_coinmarketcap():
    if not CMC_API_KEY:
        print("[CMC] API key missing")
        return []

    url = (
        "https://pro-api.coinmarketcap.com/"
        "v1/cryptocurrency/listings/latest"
    )

    response = safe_get(
        url,
        headers={
            "X-CMC_PRO_API_KEY": CMC_API_KEY
        },
        params={
            "start": 1,
            "limit": 100,
            "convert": "USD"
        }
    )

    if not response:
        return []

    try:
        payload = response.json()

        results = []

        for coin in payload.get("data", []):

            symbol = coin.get(
                "symbol",
                ""
            ).upper()

            if (
                symbol not in WATCHLIST
                and len(results) >= 25
            ):
                continue

            quote = (
                coin.get("quote", {})
                .get("USD", {})
            )

            results.append({
                "source": "CoinMarketCap",
                "type": "market",
                "id": f"cmc:{symbol}",
                "title": (
                    f"{symbol} market update"
                ),
                "text": (
                    f"{symbol} price "
                    f"${quote.get('price', 0):,.4f}; "
                    f"24h change "
                    f"{quote.get('percent_change_24h', 0):.2f}%; "
                    f"24h volume "
                    f"${quote.get('volume_24h', 0):,.0f}; "
                    f"market cap "
                    f"${quote.get('market_cap', 0):,.0f}"
                ),
                "url": (
                    f"https://coinmarketcap.com/"
                    f"currencies/{coin.get('slug', '')}/"
                ),
                "symbol": symbol,
                "price": quote.get("price"),
                "change_24h": quote.get(
                    "percent_change_24h"
                ),
                "volume_24h": quote.get(
                    "volume_24h"
                )
            })

        return results

    except Exception as exc:
        print(f"[CMC PARSE] {exc}")
        return []


# ============================================================
# COINGECKO
# ============================================================

def fetch_coingecko():
    url = (
        "https://api.coingecko.com/api/v3/"
        "simple/price"
    )

    ids = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
        "USDC": "usd-coin",
        "USDT": "tether"
    }

    selected = [
        ids[symbol]
        for symbol in WATCHLIST
        if symbol in ids
    ]

    if not selected:
        return []

    headers = {}

    if COINGECKO_API_KEY:
        headers["x-cg-demo-api-key"] = (
            COINGECKO_API_KEY
        )

    response = safe_get(
        url,
        headers=headers,
        params={
            "ids": ",".join(selected),
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_24hr_vol": "true"
        }
    )

    if not response:
        return []

    try:
        data = response.json()

        results = []

        for symbol, coin_id in ids.items():

            if symbol not in WATCHLIST:
                continue

            coin = data.get(
                coin_id,
                {}
            )

            results.append({
                "source": "CoinGecko",
                "type": "market_validation",
                "id": f"coingecko:{symbol}",
                "title": (
                    f"{symbol} market validation"
                ),
                "text": (
                    f"{symbol} is trading around "
                    f"${coin.get('usd', 0):,.4f}; "
                    f"24h change "
                    f"{coin.get('usd_24h_change', 0):.2f}%"
                ),
                "url": (
                    f"https://www.coingecko.com/"
                    f"en/coins/{coin_id}"
                ),
                "symbol": symbol,
                "price": coin.get("usd"),
                "change_24h": coin.get(
                    "usd_24h_change"
                )
            })

        return results

    except Exception as exc:
        print(f"[COINGECKO PARSE] {exc}")
        return []


# ============================================================
# RSS / NEWS
# ============================================================

def fetch_rss():
    results = []

    for source, url in RSS_FEEDS:

        try:
            feed = feedparser.parse(url)

            for entry in feed.entries[:20]:

                title = clean_text(
                    entry.get("title", "")
                )

                summary = clean_text(
                    entry.get(
                        "summary",
                        entry.get(
                            "description",
                            ""
                        )
                    )
                )

                link = entry.get(
                    "link",
                    ""
                )

                if not title or not link:
                    continue

                text = f"{title} {summary}"

                results.append({
                    "source": source,
                    "type": "news",
                    "id": make_id(
                        source,
                        link
                    ),
                    "title": title,
                    "text": text[:3000],
                    "url": link
                })

        except Exception as exc:
            print(
                f"[RSS ERROR] {source}: {exc}"
            )

    return results


# ============================================================
# REDDIT
# ============================================================

REDDIT_SUBREDDITS = [
    "CryptoCurrency",
    "ethereum",
    "defi",
    "solana",
    "Bitcoin",
    "artificial",
]


def fetch_reddit():
    results = []

    for subreddit in REDDIT_SUBREDDITS:

        url = (
            f"https://www.reddit.com/"
            f"r/{subreddit}/new.json"
        )

        response = safe_get(
            url,
            params={
                "limit": 15,
                "raw_json": 1
            }
        )

        if not response:
            continue

        try:
            payload = response.json()

            posts = (
                payload
                .get("data", {})
                .get("children", [])
            )

            for child in posts:

                data = child.get(
                    "data",
                    {}
                )

                title = clean_text(
                    data.get(
                        "title",
                        ""
                    )
                )

                body = clean_text(
                    data.get(
                        "selftext",
                        ""
                    )
                )

                permalink = data.get(
                    "permalink",
                    ""
                )

                if not title:
                    continue

                results.append({
                    "source": f"Reddit/r/{subreddit}",
                    "type": "community",
                    "id": make_id(
                        "reddit",
                        subreddit,
                        data.get("id")
                    ),
                    "title": title,
                    "text": (
                        f"{title} {body}"
                    )[:3000],
                    "url": (
                        f"https://www.reddit.com"
                        f"{permalink}"
                    ),
                    "score": data.get(
                        "score",
                        0
                    ),
                    "comments": data.get(
                        "num_comments",
                        0
                    )
                })

        except Exception as exc:
            print(
                f"[REDDIT PARSE] {exc}"
            )

    return results


# ============================================================
# LUNARCRUSH
# ============================================================

def fetch_lunarcrush():
    if not LUNARCRUSH_API_KEY:
        print("[LUNARCRUSH] API key missing")
        return []

    url = (
        "https://lunarcrush.com/"
        "api4/public/coins/list/v1"
    )

    response = safe_get(
        url,
        headers={
            "Authorization":
                f"Bearer {LUNARCRUSH_API_KEY}"
        },
        params={
            "limit": 25
        }
    )

    if not response:
        return []

    try:
        payload = response.json()

        results = []

        for coin in payload.get(
            "data",
            []
        ):

            symbol = (
                coin.get(
                    "symbol",
                    ""
                )
                .upper()
            )

            if symbol not in WATCHLIST:
                continue

            results.append({
                "source": "LunarCrush",
                "type": "social",
                "id": f"lunarcrush:{symbol}",
                "title": (
                    f"{symbol} social activity"
                ),
                "text": json.dumps(
                    coin,
                    ensure_ascii=False
                )[:4000],
                "url": (
                    f"https://lunarcrush.com/"
                ),
                "symbol": symbol
            })

        return results

    except Exception as exc:
        print(
            f"[LUNARCRUSH PARSE] {exc}"
        )
        return []


# ============================================================
# NEYNAR / FARCASTER
# ============================================================

def fetch_neynar():
    if not NEYNAR_API_KEY:
        print("[NEYNAR] API key missing")
        return []

    queries = [
        "stablecoin",
        "crypto payments",
        "AI agents",
        "DeFi",
        "RWA"
    ]

    results = []

    for query in queries:

        url = (
            "https://api.neynar.com/v2/"
            "farcaster/cast/search"
        )

        response = safe_get(
            url,
            headers={
                "x-api-key":
                    NEYNAR_API_KEY
            },
            params={
                "q": query,
                "limit": 10
            }
        )

        if not response:
            continue

        try:
            payload = response.json()

            casts = payload.get(
                "result",
                {}
            ).get(
                "casts",
                []
            )

            for cast in casts:

                text = clean_text(
                    cast.get(
                        "text",
                        ""
                    )
                )

                if not text:
                    continue

                cast_hash = cast.get(
                    "hash",
                    ""
                )

                results.append({
                    "source": "Farcaster",
                    "type": "social",
                    "id": make_id(
                        "farcaster",
                        cast_hash
                    ),
                    "title": (
                        f"Farcaster: {query}"
                    ),
                    "text": text[:3000],
                    "url": (
                        f"https://warpcast.com/"
                    )
                })

        except Exception as exc:
            print(
                f"[NEYNAR PARSE] {exc}"
            )

    return results


# ============================================================
# SORSA / X
# ============================================================

def fetch_sorsa():
    if not SORSA_API_KEY:
        print("[SORSA] API key missing")
        return []

    queries = [
        "stablecoin payments",
        "AI agents crypto",
        "crypto payments",
        "RWA tokenization",
        "DeFi"
    ]

    results = []

    for query in queries:

        url = (
            "https://api.sorsa.io/v3/"
            "tweets/search"
        )

        response = safe_get(
            url,
            headers={
                "ApiKey": SORSA_API_KEY
            },
            params={
                "query": query,
                "limit": 10
            }
        )

        if not response:
            continue

        try:
            payload = response.json()

            tweets = payload.get(
                "data",
                payload if isinstance(
                    payload,
                    list
                )
                else []
            )

            if isinstance(
                tweets,
                dict
            ):
                tweets = tweets.get(
                    "tweets",
                    []
                )

            for tweet in tweets:

                text = clean_text(
                    tweet.get(
                        "text",
                        tweet.get(
                            "full_text",
                            ""
                        )
                    )
                )

                tweet_id = (
                    tweet.get(
                        "id",
                        ""
                    )
                )

                if not text:
                    continue

                results.append({
                    "source": "Sorsa / X",
                    "type": "social",
                    "id": make_id(
                        "sorsa",
                        tweet_id,
                        text
                    ),
                    "title": (
                        f"X discussion: {query}"
                    ),
                    "text": text[:3000],
                    "url": (
                        f"https://x.com/"
                    )
                })

        except Exception as exc:
            print(
                f"[SORSA PARSE] {exc}"
            )

    return results


# ============================================================
# GITHUB
# ============================================================

GITHUB_SEARCHES = [
    "stablecoin",
    "crypto payments",
    "AI agents crypto",
    "DeFi",
    "RWA tokenization",
]


def fetch_github():
    results = []

    headers = {
        "Accept":
            "application/vnd.github+json"
    }

    if GITHUB_TOKEN:
        headers["Authorization"] = (
            f"Bearer {GITHUB_TOKEN}"
        )

    for query in GITHUB_SEARCHES:

        url = (
            "https://api.github.com/"
            "search/repositories"
        )

        response = safe_get(
            url,
            headers=headers,
            params={
                "q": query,
                "sort": "updated",
                "order": "desc",
                "per_page": 5
            }
        )

        if not response:
            continue

        try:
            payload = response.json()

            for repo in payload.get(
                "items",
                []
            ):

                name = repo.get(
                    "full_name",
                    ""
                )

                description = clean_text(
                    repo.get(
                        "description",
                        ""
                    )
                )

                updated = repo.get(
                    "updated_at",
                    ""
                )

                results.append({
                    "source": "GitHub",
                    "type": "builder",
                    "id": make_id(
                        "github",
                        repo.get(
                            "id"
                        ),
                        updated
                    ),
                    "title": (
                        f"GitHub activity: "
                        f"{name}"
                    ),
                    "text": (
                        f"{description} "
                        f"Repository: {name}. "
                        f"Stars: "
                        f"{repo.get('stargazers_count', 0)}. "
                        f"Forks: "
                        f"{repo.get('forks_count', 0)}. "
                        f"Updated: {updated}."
                    ),
                    "url": repo.get(
                        "html_url",
                        ""
                    )
                })

        except Exception as exc:
            print(
                f"[GITHUB PARSE] {exc}"
            )

    return results


# ============================================================
# SIGNAL SCORING
# ============================================================

def score_signal(item):
    text = (
        f"{item.get('title', '')} "
        f"{item.get('text', '')}"
    ).lower()

    score = 0.0

    matched = contains_topic(text)

    # Core niche relevance
    score += min(
        len(matched) * 1.5,
        7
    )

    # High-value developments
    high_value_words = [
        "launch",
        "mainnet",
        "integration",
        "partnership",
        "funding",
        "adoption",
        "payments",
        "stablecoin",
        "institutional",
        "tokenization",
        "acquisition",
        "upgrade",
        "release"
    ]

    for word in high_value_words:
        if word in text:
            score += 1

    # Risk / breaking events
    urgent_words = [
        "hack",
        "exploit",
        "attack",
        "breach",
        "halt",
        "shutdown",
        "lawsuit",
        "ban",
        "approval"
    ]

    for word in urgent_words:
        if word in text:
            score += 2.5

    # Market movement
    change = item.get(
        "change_24h"
    )

    if isinstance(
        change,
        (int, float)
    ):
        if abs(change) >= 10:
            score += 4
        elif abs(change) >= 5:
            score += 2

    # Reddit engagement
    comments = item.get(
        "comments",
        0
    )

    if isinstance(
        comments,
        (int, float)
    ):
        if comments >= 100:
            score += 2
        elif comments >= 30:
            score += 1

    return round(
        min(score, 20),
        2
    )


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate(items, seen):

    output = []
    local = set()

    for item in items:

        item_id = item.get("id")

        if not item_id:
            continue

        if item_id in seen:
            continue

        if item_id in local:
            continue

        local.add(item_id)

        item["matched_topics"] = (
            contains_topic(
                f"{item.get('title', '')} "
                f"{item.get('text', '')}"
            )
        )

        item["signal_score"] = (
            score_signal(item)
        )

        output.append(item)

    return output


# ============================================================
# GROQ INTELLIGENCE ENGINE
# ============================================================

def groq_analyze(items, previous_topics):

    if not GROQ_API_KEY:
        print("[GROQ] API key missing")
        return None

    compact_items = []

    for index, item in enumerate(
        items[:12],
        start=1
    ):

        compact_items.append({
            "id": index,
            "source": item.get(
                "source"
            ),
            "type": item.get(
                "type"
            ),
            "title": item.get(
                "title"
            ),
            "text": item.get(
                "text"
            )[:1500],
            "url": item.get(
                "url"
            ),
            "signal_score": item.get(
                "signal_score"
            ),
            "topics": item.get(
                "matched_topics",
                []
            )
        })

    system_prompt = """
You are the senior intelligence editor for a
crypto creator who wants to become known for
high-quality analysis around:

crypto
AI
stablecoins
payments
DeFi
financial infrastructure
tokenization
wallets
Bitcoin
Ethereum
Solana
NFTs and digital culture

Your job is NOT to manufacture hype.

Find what matters.

Separate:
- breaking events
- meaningful developments
- emerging narratives
- market noise
- content opportunities

Then determine the strongest angle.

WRITING RULES:

The creator must have a consistent identity but
an interchangeable writing mode.

Choose the writing mode based on the story.

Possible modes:

BREAKING:
short, direct, immediate.

ANALYTICAL:
data → interpretation → implication.

CONTRARIAN:
common assumption → challenge → evidence.

EXPLAINER:
simple explanation without sounding childish.

VISIONARY:
development → what it could mean for the future.

SKEPTICAL:
claim → evidence → risks.

CULTURAL:
internet-native, human, observant, especially
for NFT/community/culture stories.

TECHNICAL:
mechanism → architecture → practical implication.

HUMAN:
personal observation → lesson → conclusion.

Do not use generic phrases such as:
"the future is here"
"game changer"
"revolutionary"
"this is huge"
"mass adoption is coming"

Do not copy source wording.

Do not invent facts.

If evidence is weak, say so.

The creator should sound like a knowledgeable
crypto-native human, not a corporate PR account
and not an AI content farm.

Return valid JSON only.
"""

    user_prompt = {
        "previous_topics": previous_topics[-50:],
        "signals": compact_items,
        "task": """
Analyze these signals.

Return:

{
  "summary": "...",
  "important": true/false,
  "narratives": [],
  "top_story_ids": [],
  "why_it_matters": [],
  "content_opportunities": [],
  "writing_mode": "...",
  "confidence": 0-100,
  "recommended_posts": [
    {
      "hook": "...",
      "angle": "...",
      "post": "...",
      "format": "short_post|thread|reply|research_note"
    }
  ]
}

Only recommend content when there is a
reasonable evidence-based opportunity.
"""
    }

    url = (
        "https://api.groq.com/openai/v1/chat/completions"
    )

    response = safe_post(
        url,
        headers={
            "Authorization":
                f"Bearer {GROQ_API_KEY}",
            "Content-Type":
                "application/json"
        },
        json={
            "model": GROQ_MODEL,
            "temperature": 0.7,
            "response_format": {
                "type": "json_object"
            },
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        user_prompt,
                        ensure_ascii=False
                    )
                }
            ]
        }
    )

    if not response:
        return None

    try:
        data = response.json()

        content = (
            data["choices"][0]
            ["message"]["content"]
        )

        return json.loads(content)

    except Exception as exc:
        print(
            f"[GROQ PARSE] {exc}"
        )

    return None


# ============================================================
# TELEGRAM FORMAT
# ============================================================

def format_alert(analysis, items):

    if not analysis:
        return None

    lines = []

    lines.append(
        "🧠 <b>WEB3STATION INTELLIGENCE</b>"
    )

    lines.append("")

    if analysis.get(
        "summary"
    ):
        lines.append(
            f"<b>{analysis['summary']}</b>"
        )

    lines.append("")

    confidence = analysis.get(
        "confidence",
        0
    )

    mode = analysis.get(
        "writing_mode",
        "analytical"
    )

    lines.append(
        f"🎯 confidence: "
        f"<b>{confidence}%</b>"
    )

    lines.append(
        f"✍️ mode: "
        f"<b>{mode}</b>"
    )

    narratives = analysis.get(
        "narratives",
        []
    )

    if narratives:

        lines.append("")
        lines.append(
            "<b>emerging narratives</b>"
        )

        for narrative in narratives[:5]:
            lines.append(
                f"• {narrative}"
            )

    why = analysis.get(
        "why_it_matters",
        []
    )

    if why:

        lines.append("")
        lines.append(
            "<b>why it matters</b>"
        )

        for point in why[:4]:
            lines.append(
                f"• {point}"
            )

    opportunities = analysis.get(
        "content_opportunities",
        []
    )

    if opportunities:

        lines.append("")
        lines.append(
            "<b>content opportunities</b>"
        )

        for opportunity in opportunities[:4]:
            lines.append(
                f"• {opportunity}"
            )

    posts = analysis.get(
        "recommended_posts",
        []
    )

    if posts:

        lines.append("")
        lines.append(
            "━━━━━━━━━━━━━━━━━━"
        )
        lines.append(
            "<b>CONTENT OPTIONS</b>"
        )

        for index, post in enumerate(
            posts[:3],
            start=1
        ):

            hook = post.get(
                "hook",
                ""
            )

            angle = post.get(
                "angle",
                ""
            )

            body = post.get(
                "post",
                ""
            )

            fmt = post.get(
                "format",
                ""
            )

            lines.append("")
            lines.append(
                f"<b>{index}. {fmt}</b>"
            )

            if hook:
                lines.append(
                    f"hook: {hook}"
                )

            if angle:
                lines.append(
                    f"angle: {angle}"
                )

            if body:
                lines.append(
                    f"\n{body}"
                )

    # Supporting sources
    top_ids = set(
        analysis.get(
            "top_story_ids",
            []
        )
    )

    relevant = []

    for index, item in enumerate(
        items[:12],
        start=1
    ):

        if (
            index in top_ids
            or not top_ids
        ):
            relevant.append(item)

    if relevant:

        lines.append("")
        lines.append(
            "━━━━━━━━━━━━━━━━━━"
        )
        lines.append(
            "<b>SOURCES</b>"
        )

        for item in relevant[:5]:

            title = item.get(
                "title",
                ""
            )[:100]

            url = item.get(
                "url",
                ""
            )

            if url:
                lines.append(
                    f'• <a href="{url}">'
                    f'{title}</a>'
                )
            else:
                lines.append(
                    f"• {title}"
                )

    return "\n".join(lines)


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "===================================="
    )

    print(
        "WEB3STATION INTELLIGENCE ENGINE"
    )

    print(
        f"Started: {now()}"
    )

    print(
        "===================================="
    )

    seen = set(
        load_json(
            SEEN_FILE,
            []
        )
    )

    topic_history = load_json(
        TOPIC_FILE,
        []
    )

    all_items = []

    # --------------------------------------------------------
    # COLLECT
    # --------------------------------------------------------

    collectors = [
        ("CoinMarketCap", fetch_coinmarketcap),
        ("CoinGecko", fetch_coingecko),
        ("RSS", fetch_rss),
        ("Reddit", fetch_reddit),
        ("LunarCrush", fetch_lunarcrush),
        ("Neynar", fetch_neynar),
        ("Sorsa", fetch_sorsa),
        ("GitHub", fetch_github),
    ]

    for name, collector in collectors:

        print(
            f"\n[COLLECT] {name}"
        )

        try:

            items = collector()

            print(
                f"[COLLECT] {name}: "
                f"{len(items)} items"
            )

            all_items.extend(items)

        except Exception as exc:

            print(
                f"[COLLECT ERROR] "
                f"{name}: {exc}"
            )

    print(
        f"\nTOTAL RAW SIGNALS: "
        f"{len(all_items)}"
    )

    # --------------------------------------------------------
    # DEDUPLICATE + SCORE
    # --------------------------------------------------------

    candidates = deduplicate(
        all_items,
        seen
    )

    candidates.sort(
        key=lambda x: x.get(
            "signal_score",
            0
        ),
        reverse=True
    )

    print(
        f"NEW CANDIDATES: "
        f"{len(candidates)}"
    )

    # Keep enough context for Groq
    candidates = candidates[:30]

    strong_candidates = [
        item
        for item in candidates
        if item.get(
            "signal_score",
            0
        ) >= MIN_SIGNAL_SCORE
    ]

    # --------------------------------------------------------
    # NO SIGNAL
    # --------------------------------------------------------

    if not strong_candidates:

        print(
            "No high-signal story."
        )

        # Mark a small number of scanned
        # items so repeated unchanged
        # sources don't grow forever.
        for item in candidates[:50]:
            seen.add(
                item["id"]
            )

        save_json(
            SEEN_FILE,
            list(seen)[-3000:]
        )

        telegram(
            "🛰 <b>Web3Station scan complete</b>\n\n"
            "No high-signal crypto narrative "
            "detected in this scan.\n\n"
            f"Sources scanned: {len(collectors)}\n"
            f"New signals: {len(candidates)}"
        )

        return

    # --------------------------------------------------------
    # AI ANALYSIS
    # --------------------------------------------------------

    analysis = groq_analyze(
        strong_candidates,
        topic_history
    )

    if not analysis:

        print(
            "Groq analysis failed."
        )

        telegram(
            "⚠️ <b>Web3Station</b>\n\n"
            "Signals were collected, but the "
            "AI analysis layer failed this run.\n"
            "The bot will retry on the next scan."
        )

        return

    # --------------------------------------------------------
    # TELEGRAM
    # --------------------------------------------------------

    message = format_alert(
        analysis,
        strong_candidates
    )

    if message:

        # Telegram has a message limit.
        if len(message) > 3900:
            message = message[:3900] + "\n\n..."

        telegram(message)

    # --------------------------------------------------------
    # MEMORY
    # --------------------------------------------------------

    for item in candidates:

        seen.add(
            item["id"]
        )

    narratives = analysis.get(
        "narratives",
        []
    )

    if narratives:

        topic_history.append({
            "timestamp": now(),
            "narratives": narratives,
            "confidence": analysis.get(
                "confidence",
                0
            ),
            "writing_mode": analysis.get(
                "writing_mode",
                ""
            )
        })

    save_json(
        SEEN_FILE,
        list(seen)[-3000:]
    )

    save_json(
        TOPIC_FILE,
        topic_history[-500:]
    )

    print(
        "\nRUN COMPLETE"
    )


if __name__ == "__main__":
    main()
