import os
import json
import hashlib
import time
import html
from datetime import datetime, timezone
from html import unescape

import requests
import feedparser


# ============================================================
# WEB3STATION INTELLIGENCE
# main.py
# ============================================================


# ============================================================
# CONFIG
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

CMC_API_KEY = os.getenv("CMC_API_KEY", "").strip()
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
LUNARCRUSH_API_KEY = os.getenv("LUNARCRUSH_API_KEY", "").strip()
NEYNAR_API_KEY = os.getenv("NEYNAR_API_KEY", "").strip()
SORSA_API_KEY = os.getenv("SORSA_API_KEY", "").strip()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
).strip()

MIN_SIGNAL_SCORE = 6.0
MAX_ALERTS = 5

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
# BRAND / NICHE
# ============================================================

TIER_1_TOPICS = [
    "stablecoin",
    "stablecoins",
    "payments",
    "crypto payments",
    "ai agents",
    "ai agent",
    "agentic commerce",
    "agentic",
    "financial infrastructure",
    "onchain finance",
    "rwa",
    "real world assets",
    "tokenization",
    "tokenisation",
    "wallet",
    "wallets",
    "usdc",
    "usdt",
    "remittance",
    "cross-border payments",
    "cross border payments",
    "settlement",
]

TIER_2_TOPICS = [
    "defi",
    "ethereum",
    "bitcoin",
    "solana",
    "base",
    "arbitrum",
    "layer 2",
    "layer2",
    "l2",
    "account abstraction",
    "smart wallet",
    "security",
    "institutional",
    "regulation",
    "regulatory",
    "mainnet",
    "stablecoin infrastructure",
]

TIER_3_TOPICS = [
    "nft",
    "nfts",
    "digital ownership",
    "memecoin",
    "memecoins",
    "crypto culture",
]


ALL_TOPICS = (
    TIER_1_TOPICS
    + TIER_2_TOPICS
    + TIER_3_TOPICS
)


# ============================================================
# RSS
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


# ============================================================
# GITHUB SEARCHES
# ============================================================

GITHUB_SEARCHES = [
    "stablecoin",
    "crypto payments",
    "AI agents crypto",
    "DeFi",
    "RWA tokenization",
]


# ============================================================
# SESSION
# ============================================================

SESSION = requests.Session()

SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 "
        "(compatible; Web3Station/3.0; "
        "+https://github.com/)"
    )
})


# ============================================================
# HELPERS
# ============================================================

def now():
    return datetime.now(
        timezone.utc
    ).isoformat()


def safe_get(url, **kwargs):

    try:

        response = SESSION.get(
            url,
            timeout=25,
            **kwargs
        )

        if response.status_code == 200:
            return response

        print(
            f"[HTTP {response.status_code}] "
            f"{url}"
        )

        print(
            response.text[:500]
        )

    except Exception as exc:

        print(
            f"[REQUEST ERROR] "
            f"{url}: {exc}"
        )

    return None


def safe_post(url, **kwargs):

    try:

        response = SESSION.post(
            url,
            timeout=60,
            **kwargs
        )

        if 200 <= response.status_code < 300:
            return response

        print(
            f"[POST HTTP {response.status_code}] "
            f"{url}"
        )

        print(
            response.text[:1000]
        )

    except Exception as exc:

        print(
            f"[POST ERROR] "
            f"{url}: {exc}"
        )

    return None


def clean_text(text):

    if not text:
        return ""

    text = unescape(
        str(text)
    )

    return " ".join(
        text
        .replace("\n", " ")
        .split()
    )


def telegram_escape(text):

    if text is None:
        return ""

    return html.escape(
        str(text),
        quote=False
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

    try:

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

    except Exception as exc:

        print(
            f"[SAVE ERROR] "
            f"{path}: {exc}"
        )


def matched_topics(text):

    text = text.lower()

    matches = []

    for topic in ALL_TOPICS:

        if topic.lower() in text:

            matches.append(topic)

    return list(
        dict.fromkeys(matches)
    )


# ============================================================
# TELEGRAM
# ============================================================

def telegram(message):

    if not TELEGRAM_TOKEN:

        print(
            "[TELEGRAM] token missing"
        )

        return False

    if not TELEGRAM_CHAT_ID:

        print(
            "[TELEGRAM] chat id missing"
        )

        return False

    url = (
        "https://api.telegram.org/"
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

        print(
            "[CMC] API key missing"
        )

        return []

    url = (
        "https://pro-api.coinmarketcap.com/"
        "v1/cryptocurrency/listings/latest"
    )

    response = safe_get(
        url,
        headers={
            "X-CMC_PRO_API_KEY":
                CMC_API_KEY
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

            quote = (
                coin
                .get("quote", {})
                .get("USD", {})
            )

            if (
                symbol not in WATCHLIST
                and len(results) >= 25
            ):
                continue

            results.append({
                "source":
                    "CoinMarketCap",

                "type":
                    "market",

                "id":
                    f"cmc:{symbol}",

                "title":
                    f"{symbol} market update",

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

                "url":
                    (
                        "https://coinmarketcap.com/"
                        "currencies/"
                        f"{coin.get('slug', '')}/"
                    ),

                "symbol":
                    symbol,

                "price":
                    quote.get("price"),

                "change_24h":
                    quote.get(
                        "percent_change_24h"
                    )
            })

        return results

    except Exception as exc:

        print(
            f"[CMC PARSE] {exc}"
        )

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

        headers[
            "x-cg-demo-api-key"
        ] = COINGECKO_API_KEY

    response = safe_get(
        url,
        headers=headers,
        params={
            "ids":
                ",".join(selected),

            "vs_currencies":
                "usd",

            "include_24hr_change":
                "true",

            "include_24hr_vol":
                "true"
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
                "source":
                    "CoinGecko",

                "type":
                    "market_validation",

                "id":
                    f"coingecko:{symbol}",

                "title":
                    f"{symbol} market validation",

                "text": (
                    f"{symbol} is trading around "
                    f"${coin.get('usd', 0):,.4f}; "
                    f"24h change "
                    f"{coin.get('usd_24h_change', 0):.2f}%"
                ),

                "url":
                    (
                        "https://www.coingecko.com/"
                        f"en/coins/{coin_id}"
                    ),

                "symbol":
                    symbol,

                "price":
                    coin.get("usd"),

                "change_24h":
                    coin.get(
                        "usd_24h_change"
                    )
            })

        return results

    except Exception as exc:

        print(
            f"[COINGECKO PARSE] {exc}"
        )

        return []


# ============================================================
# RSS
# ============================================================

def fetch_rss():

    results = []

    for source, url in RSS_FEEDS:

        try:

            feed = feedparser.parse(
                url
            )

            for entry in feed.entries[:25]:

                title = clean_text(
                    entry.get(
                        "title",
                        ""
                    )
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

                results.append({
                    "source":
                        source,

                    "type":
                        "news",

                    "id":
                        make_id(
                            source,
                            link
                        ),

                    "title":
                        title,

                    "text":
                        (
                            f"{title} "
                            f"{summary}"
                        )[:4000],

                    "url":
                        link
                })

        except Exception as exc:

            print(
                f"[RSS ERROR] "
                f"{source}: {exc}"
            )

    return results


# ============================================================
# REDDIT
# ============================================================

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
                    "source":
                        f"Reddit/r/{subreddit}",

                    "type":
                        "community",

                    "id":
                        make_id(
                            "reddit",
                            subreddit,
                            data.get("id")
                        ),

                    "title":
                        title,

                    "text":
                        (
                            f"{title} "
                            f"{body}"
                        )[:4000],

                    "url":
                        (
                            "https://www.reddit.com"
                            f"{permalink}"
                        ),

                    "score":
                        data.get(
                            "score",
                            0
                        ),

                    "comments":
                        data.get(
                            "num_comments",
                            0
                        )
                })

        except Exception as exc:

            print(
                f"[REDDIT PARSE] "
                f"{exc}"
            )

    return results


# ============================================================
# LUNARCRUSH
# ============================================================

def fetch_lunarcrush():

    if not LUNARCRUSH_API_KEY:

        print(
            "[LUNARCRUSH] API key missing"
        )

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
                "source":
                    "LunarCrush",

                "type":
                    "social",

                "id":
                    f"lunarcrush:{symbol}",

                "title":
                    f"{symbol} social activity",

                "text":
                    json.dumps(
                        coin,
                        ensure_ascii=False
                    )[:4000],

                "url":
                    "https://lunarcrush.com/",

                "symbol":
                    symbol
            })

        return results

    except Exception as exc:

        print(
            f"[LUNARCRUSH PARSE] "
            f"{exc}"
        )

        return []


# ============================================================
# NEYNAR / FARCASTER
# ============================================================

def fetch_neynar():

    if not NEYNAR_API_KEY:

        print(
            "[NEYNAR] API key missing"
        )

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
                "q":
                    query,

                "limit":
                    10
            }
        )

        if not response:
            continue

        try:

            payload = response.json()

            casts = (
                payload
                .get("result", {})
                .get("casts", [])
            )

            for cast in casts:

                text = clean_text(
                    cast.get(
                        "text",
                        ""
                    )
                )

                cast_hash = cast.get(
                    "hash",
                    ""
                )

                if not text:
                    continue

                results.append({
                    "source":
                        "Farcaster",

                    "type":
                        "social",

                    "id":
                        make_id(
                            "farcaster",
                            cast_hash,
                            text
                        ),

                    "title":
                        f"Farcaster: {query}",

                    "text":
                        text[:4000],

                    "url":
                        "https://warpcast.com/"
                })

        except Exception as exc:

            print(
                f"[NEYNAR PARSE] "
                f"{exc}"
            )

    return results


# ============================================================
# SORSA
# ============================================================

def fetch_sorsa():

    if not SORSA_API_KEY:

        print(
            "[SORSA] API key missing"
        )

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
                "ApiKey":
                    SORSA_API_KEY
            },
            params={
                "query":
                    query,

                "limit":
                    10
            }
        )

        if not response:
            continue

        try:

            payload = response.json()

            tweets = payload.get(
                "data",
                []
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

                tweet_id = tweet.get(
                    "id",
                    ""
                )

                if not text:
                    continue

                results.append({
                    "source":
                        "Sorsa / X",

                    "type":
                        "social",

                    "id":
                        make_id(
                            "sorsa",
                            tweet_id,
                            text
                        ),

                    "title":
                        f"X discussion: {query}",

                    "text":
                        text[:4000],

                    "url":
                        "https://x.com/"
                })

        except Exception as exc:

            print(
                f"[SORSA PARSE] "
                f"{exc}"
            )

    return results


# ============================================================
# GITHUB
# ============================================================

def fetch_github():

    results = []

    headers = {
        "Accept":
            "application/vnd.github+json"
    }

    if GITHUB_TOKEN:

        headers[
            "Authorization"
        ] = f"Bearer {GITHUB_TOKEN}"

    for query in GITHUB_SEARCHES:

        url = (
            "https://api.github.com/"
            "search/repositories"
        )

        response = safe_get(
            url,
            headers=headers,
            params={
                "q":
                    query,

                "sort":
                    "updated",

                "order":
                    "desc",

                "per_page":
                    5
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
                    "source":
                        "GitHub",

                    "type":
                        "builder",

                    "id":
                        make_id(
                            "github",
                            repo.get("id"),
                            updated
                        ),

                    "title":
                        f"GitHub activity: {name}",

                    "text":
                        (
                            f"{description} "
                            f"Repository: {name}. "
                            f"Stars: "
                            f"{repo.get('stargazers_count', 0)}. "
                            f"Forks: "
                            f"{repo.get('forks_count', 0)}. "
                            f"Updated: {updated}."
                        )[:4000],

                    "url":
                        repo.get(
                            "html_url",
                            ""
                        )
                })

        except Exception as exc:

            print(
                f"[GITHUB PARSE] "
                f"{exc}"
            )

    return results


# ============================================================
# LOCAL SIGNAL SCORING
# ============================================================

def score_signal(item):

    text = (
        f"{item.get('title', '')} "
        f"{item.get('text', '')}"
    ).lower()

    score = 0

    topics = matched_topics(
        text
    )

    for topic in topics:

        if topic in TIER_1_TOPICS:

            score += 2.5

        elif topic in TIER_2_TOPICS:

            score += 1.5

        elif topic in TIER_3_TOPICS:

            score += 0.75

    high_value = [
        "launch",
        "mainnet",
        "integration",
        "partnership",
        "funding",
        "adoption",
        "payment",
        "payments",
        "stablecoin",
        "institutional",
        "tokenization",
        "tokenisation",
        "acquisition",
        "upgrade",
        "release",
        "volume",
        "settlement",
        "audit",
        "approval",
    ]

    for word in high_value:

        if word in text:
            score += 1

    urgent = [
        "hack",
        "exploit",
        "attack",
        "breach",
        "halt",
        "shutdown",
        "lawsuit",
        "ban",
        "approval",
        "outage",
        "vulnerability",
    ]

    for word in urgent:

        if word in text:
            score += 2.5

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
# NARRATIVE CLUSTERS
# ============================================================

def build_narrative_clusters(items):

    clusters = {}

    for item in items:

        topics = item.get(
            "matched_topics",
            []
        )

        for topic in topics:

            key = topic.lower()

            if key not in clusters:

                clusters[key] = {
                    "topic":
                        topic,

                    "items":
                        [],

                    "sources":
                        set(),

                    "score":
                        0
                }

            clusters[key][
                "items"
            ].append(item)

            clusters[key][
                "sources"
            ].add(
                item.get(
                    "source",
                    ""
                )
            )

            clusters[key][
                "score"
            ] += item.get(
                "signal_score",
                0
            )

    output = []

    for cluster in clusters.values():

        source_count = len(
            cluster["sources"]
        )

        item_count = len(
            cluster["items"]
        )

        confirmation = min(
            source_count * 2,
            8
        )

        volume = min(
            item_count,
            6
        )

        narrative_score = round(
            min(
                cluster["score"]
                + confirmation
                + volume,
                30
            ),
            2
        )

        output.append({
            "topic":
                cluster["topic"],

            "item_count":
                item_count,

            "source_count":
                source_count,

            "sources":
                list(
                    cluster["sources"]
                ),

            "score":
                narrative_score
        })

    output.sort(
        key=lambda x:
            x["score"],
        reverse=True
    )

    return output


# ============================================================
# GROQ SCHEMA
# ============================================================

EDITORIAL_SCHEMA = {
    "type": "object",

    "properties": {

        "decision": {
            "type": "string",
            "enum": [
                "POST",
                "WATCH",
                "NO_POST"
            ]
        },

        "summary": {
            "type": "string"
        },

        "confidence": {
            "type": "number"
        },

        "evidence_score": {
            "type": "number"
        },

        "kol_opportunity_score": {
            "type": "number"
        },

        "writing_mode": {
            "type": "string"
        },

        "narratives": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },

        "narrative_status": {
            "type": "string",
            "enum": [
                "new",
                "emerging",
                "accelerating",
                "cooling",
                "stable"
            ]
        },

        "verified_facts": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },

        "interpretations": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },

        "forecasts": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },

        "unverified_claims": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },

        "why_it_matters": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },

        "content_opportunities": {
            "type": "array",

            "items": {
                "type": "object",

                "properties": {

                    "title": {
                        "type": "string"
                    },

                    "angle": {
                        "type": "string"
                    }
                },

                "required": [
                    "title",
                    "angle"
                ],

                "additionalProperties": False
            }
        },

        "recommended_posts": {
            "type": "array",

            "items": {
                "type": "object",

                "properties": {

                    "format": {
                        "type": "string"
                    },

                    "hook": {
                        "type": "string"
                    },

                    "angle": {
                        "type": "string"
                    },

                    "post": {
                        "type": "string"
                    }
                },

                "required": [
                    "format",
                    "hook",
                    "angle",
                    "post"
                ],

                "additionalProperties": False
            }
        },

        "sources": {
            "type": "array",

            "items": {
                "type": "object",

                "properties": {

                    "claim": {
                        "type": "string"
                    },

                    "source_ids": {
                        "type": "array",

                        "items": {
                            "type": "integer"
                        }
                    }
                },

                "required": [
                    "claim",
                    "source_ids"
                ],

                "additionalProperties": False
            }
        }
    },

    "required": [
        "decision",
        "summary",
        "confidence",
        "evidence_score",
        "kol_opportunity_score",
        "writing_mode",
        "narratives",
        "narrative_status",
        "verified_facts",
        "interpretations",
        "forecasts",
        "unverified_claims",
        "why_it_matters",
        "content_opportunities",
        "recommended_posts",
        "sources"
    ],

    "additionalProperties": False
}


# ============================================================
# GROQ EDITORIAL ENGINE
# ============================================================

def groq_analyze(
    items,
    narratives,
    previous_topics
):

    if not GROQ_API_KEY:

        print(
            "[GROQ] API key missing"
        )

        return None

    # --------------------------------------------------------
    # COMPACT SIGNALS
    # --------------------------------------------------------

    compact_items = []

    for index, item in enumerate(
        items[:25],
        start=1
    ):

        compact_items.append({

            "id":
                index,

            "source":
                item.get(
                    "source",
                    ""
                ),

            "type":
                item.get(
                    "type",
                    ""
                ),

            "title":
                item.get(
                    "title",
                    ""
                )[:300],

            "text":
                item.get(
                    "text",
                    ""
                )[:1600],

            "url":
                item.get(
                    "url",
                    ""
                ),

            "signal_score":
                item.get(
                    "signal_score",
                    0
                ),

            "topics":
                item.get(
                    "matched_topics",
                    []
                )
        })

    # --------------------------------------------------------
    # SYSTEM PROMPT
    # --------------------------------------------------------

    system_prompt = """
You are WEB3STATION, a senior crypto intelligence
and editorial engine.

Your job is to help one crypto creator become known
for high-quality thinking around:

AI × crypto
stablecoins
payments
financial infrastructure
RWA
tokenization
wallets
onchain finance
DeFi
Bitcoin
Ethereum
Solana
NFTs
crypto culture

The creator does NOT want generic crypto news.

The creator wants to become known for seeing the
connection between crypto infrastructure, AI,
payments and the future of finance before the
mainstream does.

Your job is therefore:

SIGNAL → VERIFY → CONNECT → INTERPRET → CREATE

==================================================
1. FACTUAL DISCIPLINE
==================================================

Only call something a VERIFIED FACT when the supplied
signals explicitly support it.

Never invent:

numbers
dates
funding
partnerships
users
transaction volumes
technical capabilities
audits
regulatory decisions
quotes
adoption statistics
outages

If a claim appears in only one weak source, do not
upgrade it into certainty.

Social posts and Reddit posts are signals, not proof.

GitHub activity proves that code/repositories exist.
It does NOT prove adoption.

A repository description proves what the repository
claims to do. It does not prove real-world usage.

==================================================
2. THREE-LAYER THINKING
==================================================

Separate:

VERIFIED FACT
What the source says.

INTERPRETATION
What the evidence reasonably suggests.

FORECAST
What could happen if the trend continues.

UNVERIFIED
What we cannot establish from the supplied evidence.

==================================================
3. NARRATIVE DETECTION
==================================================

Do not treat every individual news item as a narrative.

A stronger narrative often combines independent
signals such as:

market movement
+
news
+
developer activity
+
social discussion
+
community activity

Look for convergence.

Also look for contradictions.

Contradictions are valuable.

Example:

institutional stablecoin confidence rising
while
merchant payment usage remains low

That is a stronger editorial opportunity than simply
saying "stablecoins are growing."

==================================================
4. KOL STANDARD
==================================================

The creator should NOT sound like:

a press release
a crypto news aggregator
an AI content farm
a token shiller

Avoid generic phrases:

"game changer"
"revolutionary"
"mass adoption"
"the future is here"
"this is huge"
"bullish"
"exciting times ahead"

unless the exact context genuinely requires them.

The voice should be:

crypto-native
sharp
observant
curious
analytical
skeptical when appropriate
human
occasionally witty

The strongest post should contain an observation
that another knowledgeable crypto user might not
have noticed.

==================================================
5. WRITING MODE
==================================================

Choose the mode that naturally fits the evidence.

Possible modes:

breaking
quick_take
analytical
contrarian
skeptical
explainer
technical
investigative
narrative
visionary
operator
market_observation
builder_perspective
cultural_observation

Do not force a contrarian angle.

Do not force a bullish angle.

Do not force a post.

==================================================
6. POST DECISION
==================================================

POST:
There is enough evidence and there is a differentiated
angle.

WATCH:
Interesting signal, but evidence or timing needs more
confirmation.

NO_POST:
Weak, repetitive, low-value, or unsupported.

If decision is WATCH or NO_POST:

recommended_posts MUST be empty.

==================================================
7. CONTENT QUALITY
==================================================

Before recommending a post ask:

Would an informed crypto user learn something?

Is there a specific observation?

Is the evidence strong enough?

Is the angle differentiated?

Could 10,000 crypto AI accounts write the same post?

If yes, improve it.

Do not write merely because there is a news item.

==================================================
8. FORMAT
==================================================

Possible formats:

short_post
thread
quote_post
reply
research_note

Use short_post by default.

Use thread only when the idea genuinely needs
multiple connected points.

Do not automatically add hashtags.

Do not use excessive emojis.

==================================================
9. SOURCE REFERENCES
==================================================

Every source reference must use the integer ID
provided in the supplied signals.

Example:

signal 3

must be referenced as:

3

Never invent source IDs.

==================================================
10. NUMERIC SCORES
==================================================

confidence:
0-100

evidence_score:
0-10

kol_opportunity_score:
0-10

Be conservative.

A story with one source should generally not receive
extreme evidence confidence.

A strong multi-source story can receive higher scores.

==================================================
11. IMPORTANT
==================================================

The creator's reputation matters more than posting
frequency.

A missed weak story is better than publishing a
confidently wrong one.

Find the signal worth thinking about.
"""


    # --------------------------------------------------------
    # USER PAYLOAD
    # --------------------------------------------------------

    user_payload = {

        "previous_narratives":
            previous_topics[-50:],

        "narrative_clusters":
            narratives[:15],

        "signals":
            compact_items,

        "task":
            """
Analyze these signals as an editorial intelligence
desk.

Return:

1. the strongest narrative
2. what is verified
3. what is inferred
4. what could happen next
5. what remains unknown
6. whether the creator should POST, WATCH or NO_POST
7. the strongest differentiated KOL angle
8. the appropriate writing mode
9. the best content opportunity
10. a high-quality draft only if POST is justified

Prioritize AI × crypto, stablecoins, payments,
financial infrastructure, RWA and onchain finance.

However, do not ignore a major Bitcoin, Ethereum,
Solana, DeFi, NFT or crypto-market story when it has
clear editorial value.

Use the supplied source IDs when citing evidence.
"""
    }

    # --------------------------------------------------------
    # REQUEST
    # --------------------------------------------------------

    url = (
        "https://api.groq.com/openai/v1/"
        "chat/completions"
    )

    payload = {

        "model":
            GROQ_MODEL,

        "messages": [

            {
                "role":
                    "system",

                "content":
                    system_prompt
            },

            {
                "role":
                    "user",

                "content":
                    json.dumps(
                        user_payload,
                        ensure_ascii=False
                    )
            }
        ],

        "temperature":
            0.35,

        "max_completion_tokens":
            6000,

        "response_format": {

            "type":
                "json_schema",

            "json_schema": {

                "name":
                    "web3station_editorial",

                "strict":
                    True,

                "schema":
                    EDITORIAL_SCHEMA
            }
        }
    }

    # --------------------------------------------------------
    # RETRIES
    # --------------------------------------------------------

    for attempt in range(1, 4):

        print(
            f"[GROQ] attempt "
            f"{attempt}/3"
        )

        response = safe_post(
            url,

            headers={
                "Authorization":
                    f"Bearer {GROQ_API_KEY}",

                "Content-Type":
                    "application/json"
            },

            json=payload
        )

        if not response:

            if attempt < 3:

                time.sleep(
                    2 * attempt
                )

                continue

            return None

        try:

            data = response.json()

        except Exception as exc:

            print(
                f"[GROQ RESPONSE JSON ERROR] "
                f"{exc}"
            )

            if attempt < 3:

                time.sleep(
                    2 * attempt
                )

                continue

            return None

        # ----------------------------------------------------
        # API ERROR
        # ----------------------------------------------------

        if "error" in data:

            print(
                "[GROQ API ERROR]"
            )

            print(
                json.dumps(
                    data,
                    indent=2,
                    ensure_ascii=False
                )[:3000]
            )

            if attempt < 3:

                time.sleep(
                    2 * attempt
                )

                continue

            return None

        # ----------------------------------------------------
        # CHOICES
        # ----------------------------------------------------

        choices = data.get(
            "choices",
            []
        )

        if not choices:

            print(
                "[GROQ] No choices returned"
            )

            if attempt < 3:

                time.sleep(
                    2 * attempt
                )

                continue

            return None

        message = choices[0].get(
            "message",
            {}
        )

        content = message.get(
            "content"
        )

        if not content:

            print(
                "[GROQ] Empty message content"
            )

            if attempt < 3:

                time.sleep(
                    2 * attempt
                )

                continue

            return None

        # ----------------------------------------------------
        # JSON PARSE
        # ----------------------------------------------------

        try:

            analysis = json.loads(
                content
            )

        except json.JSONDecodeError as exc:

            print(
                "[GROQ JSON PARSE ERROR]"
            )

            print(
                f"{exc}"
            )

            print(
                content[:3000]
            )

            if attempt < 3:

                time.sleep(
                    2 * attempt
                )

                continue

            return None

        # ----------------------------------------------------
        # NORMALIZE
        # ----------------------------------------------------

        analysis = normalize_analysis(
            analysis
        )

        print(
            "[GROQ] editorial analysis "
            "successful"
        )

        return analysis

    return None


# ============================================================
# NORMALIZE AI OUTPUT
# ============================================================

def normalize_analysis(analysis):

    if not isinstance(
        analysis,
        dict
    ):

        return None

    analysis.setdefault(
        "decision",
        "WATCH"
    )

    analysis.setdefault(
        "summary",
        "Interesting signal detected."
    )

    analysis.setdefault(
        "confidence",
        0
    )

    analysis.setdefault(
        "evidence_score",
        0
    )

    analysis.setdefault(
        "kol_opportunity_score",
        0
    )

    analysis.setdefault(
        "writing_mode",
        "analytical"
    )

    analysis.setdefault(
        "narratives",
        []
    )

    analysis.setdefault(
        "narrative_status",
        "stable"
    )

    analysis.setdefault(
        "verified_facts",
        []
    )

    analysis.setdefault(
        "interpretations",
        []
    )

    analysis.setdefault(
        "forecasts",
        []
    )

    analysis.setdefault(
        "unverified_claims",
        []
    )

    analysis.setdefault(
        "why_it_matters",
        []
    )

    analysis.setdefault(
        "content_opportunities",
        []
    )

    analysis.setdefault(
        "recommended_posts",
        []
    )

    analysis.setdefault(
        "sources",
        []
    )

    # --------------------------------------------------------
    # NUMBERS
    # --------------------------------------------------------

    try:

        analysis["confidence"] = max(
            0,
            min(
                100,
                float(
                    analysis["confidence"]
                )
            )
        )

    except Exception:

        analysis["confidence"] = 0

    try:

        analysis["evidence_score"] = max(
            0,
            min(
                10,
                float(
                    analysis["evidence_score"]
                )
            )
        )

    except Exception:

        analysis["evidence_score"] = 0

    try:

        analysis[
            "kol_opportunity_score"
        ] = max(
            0,
            min(
                10,
                float(
                    analysis[
                        "kol_opportunity_score"
                    ]
                )
            )
        )

    except Exception:

        analysis[
            "kol_opportunity_score"
        ] = 0

    # --------------------------------------------------------
    # DECISION SAFETY
    # --------------------------------------------------------

    if analysis["decision"] not in [
        "POST",
        "WATCH",
        "NO_POST"
    ]:

        analysis["decision"] = "WATCH"

    # --------------------------------------------------------
    # IMPORTANT:
    # NO POST / WATCH MUST NOT HAVE DRAFTS
    # --------------------------------------------------------

    if analysis["decision"] != "POST":

        analysis[
            "recommended_posts"
        ] = []

    return analysis


# ============================================================
# TELEGRAM FORMAT
# ============================================================

def format_opportunity(
    opportunity
):

    if not isinstance(
        opportunity,
        dict
    ):

        return (
            f"• "
            f"{telegram_escape(opportunity)}"
        )

    title = telegram_escape(
        opportunity.get(
            "title",
            ""
        )
    )

    angle = telegram_escape(
        opportunity.get(
            "angle",
            ""
        )
    )

    return (
        f"• <b>{title}</b>\n"
        f"  → {angle}"
    )


def format_alert(
    analysis,
    items
):

    if not analysis:

        return None

    lines = []

    lines.append(
        "🧠 <b>WEB3STATION</b>"
    )

    lines.append("")

    decision = analysis.get(
        "decision",
        "WATCH"
    )

    if decision == "POST":

        lines.append(
            "🚨 <b>POST OPPORTUNITY</b>"
        )

    elif decision == "WATCH":

        lines.append(
            "🟡 <b>WATCH</b>"
        )

    else:

        lines.append(
            "⚪ <b>NO POST</b>"
        )

    lines.append("")

    summary = analysis.get(
        "summary",
        ""
    )

    if summary:

        lines.append(
            f"<b>"
            f"{telegram_escape(summary)}"
            f"</b>"
        )

    lines.append("")

    lines.append(
        "🎯 confidence: "
        f"<b>{analysis.get('confidence', 0):.0f}/100</b>"
    )

    lines.append(
        "🔎 evidence: "
        f"<b>{analysis.get('evidence_score', 0):.1f}/10</b>"
    )

    lines.append(
        "💡 KOL opportunity: "
        f"<b>{analysis.get('kol_opportunity_score', 0):.1f}/10</b>"
    )

    lines.append(
        "✍️ mode: "
        f"<b>{telegram_escape(analysis.get('writing_mode', 'n/a'))}</b>"
    )

    lines.append(
        "📈 narrative: "
        f"<b>{telegram_escape(analysis.get('narrative_status', 'stable'))}</b>"
    )

    # --------------------------------------------------------
    # NARRATIVES
    # --------------------------------------------------------

    narratives = analysis.get(
        "narratives",
        []
    )

    if narratives:

        lines.append("")

        lines.append(
            "<b>narratives</b>"
        )

        for narrative in narratives[:5]:

            lines.append(
                "• "
                + telegram_escape(
                    narrative
                )
            )

    # --------------------------------------------------------
    # VERIFIED
    # --------------------------------------------------------

    facts = analysis.get(
        "verified_facts",
        []
    )

    if facts:

        lines.append("")

        lines.append(
            "<b>what we know</b>"
        )

        for fact in facts[:5]:

            lines.append(
                "✓ "
                + telegram_escape(
                    fact
                )
            )

    # --------------------------------------------------------
    # INTERPRETATIONS
    # --------------------------------------------------------

    interpretations = analysis.get(
        "interpretations",
        []
    )

    if interpretations:

        lines.append("")

        lines.append(
            "<b>what we're inferring</b>"
        )

        for point in interpretations[:4]:

            lines.append(
                "→ "
                + telegram_escape(
                    point
                )
            )

    # --------------------------------------------------------
    # FORECASTS
    # --------------------------------------------------------

    forecasts = analysis.get(
        "forecasts",
        []
    )

    if forecasts:

        lines.append("")

        lines.append(
            "<b>what could happen next</b>"
        )

        for point in forecasts[:3]:

            lines.append(
                "↗ "
                + telegram_escape(
                    point
                )
            )

    # --------------------------------------------------------
    # UNCERTAINTY
    # --------------------------------------------------------

    unknowns = analysis.get(
        "unverified_claims",
        []
    )

    if unknowns:

        lines.append("")

        lines.append(
            "<b>⚠ what we don't know</b>"
        )

        for point in unknowns[:4]:

            lines.append(
                "⚠ "
                + telegram_escape(
                    point
                )
            )

    # --------------------------------------------------------
    # WHY IT MATTERS
    # --------------------------------------------------------

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
                "• "
                + telegram_escape(
                    point
                )
            )

    # --------------------------------------------------------
    # CONTENT OPPORTUNITIES
    # --------------------------------------------------------

    opportunities = analysis.get(
        "content_opportunities",
        []
    )

    if opportunities:

        lines.append("")

        lines.append(
            "━━━━━━━━━━━━━━━━━━"
        )

        lines.append(
            "<b>CONTENT OPPORTUNITIES</b>"
        )

        for opportunity in opportunities[:4]:

            lines.append(
                format_opportunity(
                    opportunity
                )
            )

    # --------------------------------------------------------
    # DRAFTS
    # --------------------------------------------------------

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
            "<b>DRAFT CONTENT</b>"
        )

        for index, post in enumerate(
            posts[:3],
            start=1
        ):

            fmt = telegram_escape(
                post.get(
                    "format",
                    ""
                )
            )

            hook = telegram_escape(
                post.get(
                    "hook",
                    ""
                )
            )

            angle = telegram_escape(
                post.get(
                    "angle",
                    ""
                )
            )

            body = telegram_escape(
                post.get(
                    "post",
                    ""
                )
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

                lines.append("")

                lines.append(
                    body
                )

    # --------------------------------------------------------
    # EVIDENCE
    # --------------------------------------------------------

    sources = analysis.get(
        "sources",
        []
    )

    if sources:

        lines.append("")

        lines.append(
            "━━━━━━━━━━━━━━━━━━"
        )

        lines.append(
            "<b>EVIDENCE</b>"
        )

        for source in sources[:8]:

            if not isinstance(
                source,
                dict
            ):

                continue

            claim = telegram_escape(
                source.get(
                    "claim",
                    ""
                )
            )

            source_ids = source.get(
                "source_ids",
                []
            )

            lines.append(
                f"• {claim}"
            )

            if source_ids:

                lines.append(
                    "  sources: "
                    + ", ".join(
                        str(x)
                        for x in source_ids
                    )
                )

    # --------------------------------------------------------
    # SOURCE LINKS
    # --------------------------------------------------------

    top_items = sorted(
        items,
        key=lambda x:
            x.get(
                "signal_score",
                0
            ),
        reverse=True
    )

    if top_items:

        lines.append("")

        lines.append(
            "<b>SOURCE LINKS</b>"
        )

        used_urls = set()

        for item in top_items[:7]:

            url = item.get(
                "url",
                ""
            )

            title = clean_text(
                item.get(
                    "title",
                    ""
                )
            )

            if not url:
                continue

            if url in used_urls:
                continue

            used_urls.add(
                url
            )

            safe_url = html.escape(
                url,
                quote=True
            )

            safe_title = telegram_escape(
                title[:90]
            )

            lines.append(
                f'• <a href="{safe_url}">'
                f'{safe_title}</a>'
            )

    message = "\n".join(
        lines
    )

    # Telegram limit
    if len(message) > 3900:

        message = (
            message[:3900]
            + "\n\n..."
        )

    return message


# ============================================================
# COLLECTOR RUNNER
# ============================================================

def collect_all():

    collectors = [

        (
            "CoinMarketCap",
            fetch_coinmarketcap
        ),

        (
            "CoinGecko",
            fetch_coingecko
        ),

        (
            "RSS",
            fetch_rss
        ),

        (
            "Reddit",
            fetch_reddit
        ),

        (
            "LunarCrush",
            fetch_lunarcrush
        ),

        (
            "Neynar",
            fetch_neynar
        ),

        (
            "Sorsa",
            fetch_sorsa
        ),

        (
            "GitHub",
            fetch_github
        ),
    ]

    all_items = []

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

            all_items.extend(
                items
            )

        except Exception as exc:

            print(
                f"[COLLECT ERROR] "
                f"{name}: {exc}"
            )

    return all_items, collectors


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "======================================"
    )

    print(
        "WEB3STATION INTELLIGENCE v3"
    )

    print(
        f"Started: {now()}"
    )

    print(
        f"Groq model: {GROQ_MODEL}"
    )

    print(
        "======================================"
    )

    # --------------------------------------------------------
    # LOAD MEMORY
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # COLLECT
    # --------------------------------------------------------

    all_items, collectors = collect_all()

    print(
        f"\nTOTAL RAW SIGNALS: "
        f"{len(all_items)}"
    )

    # --------------------------------------------------------
    # DEDUPLICATE
    # --------------------------------------------------------

    candidates = []

    local_ids = set()

    for item in all_items:

        item_id = item.get(
            "id"
        )

        if not item_id:
            continue

        if item_id in seen:
            continue

        if item_id in local_ids:
            continue

        local_ids.add(
            item_id
        )

        text = (
            f"{item.get('title', '')} "
            f"{item.get('text', '')}"
        )

        item[
            "matched_topics"
        ] = matched_topics(
            text
        )

        item[
            "signal_score"
        ] = score_signal(
            item
        )

        candidates.append(
            item
        )

    candidates.sort(
        key=lambda x:
            x.get(
                "signal_score",
                0
            ),
        reverse=True
    )

    print(
        f"NEW CANDIDATES: "
        f"{len(candidates)}"
    )

    # --------------------------------------------------------
    # NARRATIVES
    # --------------------------------------------------------

    narrative_clusters = (
        build_narrative_clusters(
            candidates
        )
    )

    print(
        "\nNARRATIVE CLUSTERS:"
    )

    for cluster in narrative_clusters[:10]:

        print(
            f"  "
            f"{cluster['topic']} "
            f"| signals="
            f"{cluster['item_count']} "
            f"| sources="
            f"{cluster['source_count']} "
            f"| score="
            f"{cluster['score']}"
        )

    # --------------------------------------------------------
    # STRONG SIGNALS
    # --------------------------------------------------------

    strong_candidates = [
        item
        for item in candidates
        if item.get(
            "signal_score",
            0
        ) >= MIN_SIGNAL_SCORE
    ]

    strong_candidates = (
        strong_candidates[:30]
    )

    print(
        f"STRONG SIGNALS: "
        f"{len(strong_candidates)}"
    )

    # --------------------------------------------------------
    # NO STRONG SIGNAL
    # --------------------------------------------------------

    if not strong_candidates:

        print(
            "[RESULT] "
            "No strong signals."
        )

        for item in candidates[:100]:

            seen.add(
                item["id"]
            )

        save_json(
            SEEN_FILE,
            list(seen)[-3000:]
        )

        telegram(
            "🛰 <b>Web3Station scan</b>\n\n"
            "No high-confidence narrative "
            "detected in this scan.\n\n"
            f"Sources scanned: "
            f"{len(collectors)}\n"
            f"New signals: "
            f"{len(candidates)}\n\n"
            "The bot will keep watching."
        )

        return

    # --------------------------------------------------------
    # GROQ
    # --------------------------------------------------------

    analysis = groq_analyze(
        strong_candidates,
        narrative_clusters,
        topic_history
    )

    # --------------------------------------------------------
    # AI FAILURE
    # --------------------------------------------------------

    if not analysis:

        print(
            "[RESULT] "
            "Editorial AI failed."
        )

        # Do NOT mark candidates as seen.
        # They will be retried on the next run.

        telegram(
            "⚠️ <b>WEB3STATION</b>\n\n"
            "Signals were collected, but the "
            "editorial AI layer failed during "
            "this scan.\n\n"
            "The signals were NOT marked as seen, "
            "so the next scheduled scan will retry."
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

        sent = telegram(
            message
        )

        print(
            f"[TELEGRAM] "
            f"sent={sent}"
        )

    # --------------------------------------------------------
    # MEMORY
    # --------------------------------------------------------

    for item in candidates:

        seen.add(
            item["id"]
        )

    narrative_names = [

        cluster["topic"]

        for cluster
        in narrative_clusters[:10]
    ]

    if narrative_names:

        topic_history.append({

            "timestamp":
                now(),

            "narratives":
                narrative_names,

            "confidence":
                analysis.get(
                    "confidence",
                    0
                ),

            "evidence_score":
                analysis.get(
                    "evidence_score",
                    0
                ),

            "kol_opportunity_score":
                analysis.get(
                    "kol_opportunity_score",
                    0
                ),

            "decision":
                analysis.get(
                    "decision",
                    "WATCH"
                ),

            "narrative_status":
                analysis.get(
                    "narrative_status",
                    "stable"
                ),

            "writing_mode":
                analysis.get(
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
        "\n======================================"
    )

    print(
        "RUN COMPLETE"
    )

    print(
        "======================================"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
