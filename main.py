import os
import json
import hashlib
from datetime import datetime, timezone
from html import unescape
from urllib.parse import quote

import requests
import feedparser


# ============================================================
# WEB3STATION INTELLIGENCE ENGINE
# ============================================================
#
# PURPOSE
# -------
# This bot is NOT a crypto news spammer.
#
# It is an editorial intelligence system designed to help
# the creator become known for:
#
# AI x Crypto
# Stablecoins
# Payments
# Financial Infrastructure
# RWA / Tokenization
# Wallets
# Onchain Finance
# DeFi
# Bitcoin / Ethereum / Solana when relevant
# NFT / Crypto Culture when there is a real angle
#
# PIPELINE
# --------
#
# SOURCES
#   ↓
# SIGNAL COLLECTION
#   ↓
# DEDUPLICATION
#   ↓
# TOPIC MATCHING
#   ↓
# SIGNAL SCORING
#   ↓
# NARRATIVE CLUSTERING
#   ↓
# SOURCE DIVERSITY
#   ↓
# GROQ EDITORIAL ANALYSIS
#   ↓
# FACT / INFERENCE / FORECAST SEPARATION
#   ↓
# KOL OPPORTUNITY SCORE
#   ↓
# ADAPTIVE WRITING MODE
#   ↓
# TELEGRAM
#
# ============================================================


# ============================================================
# CONFIG
# ============================================================

TELEGRAM_TOKEN = os.getenv(
    "TELEGRAM_TOKEN",
    ""
).strip()

TELEGRAM_CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID",
    ""
).strip()

CMC_API_KEY = os.getenv(
    "CMC_API_KEY",
    ""
).strip()

COINGECKO_API_KEY = os.getenv(
    "COINGECKO_API_KEY",
    ""
).strip()

GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY",
    ""
).strip()

LUNARCRUSH_API_KEY = os.getenv(
    "LUNARCRUSH_API_KEY",
    ""
).strip()

NEYNAR_API_KEY = os.getenv(
    "NEYNAR_API_KEY",
    ""
).strip()

SORSA_API_KEY = os.getenv(
    "SORSA_API_KEY",
    ""
).strip()

GITHUB_TOKEN = os.getenv(
    "GITHUB_TOKEN",
    ""
).strip()

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
).strip()


# ============================================================
# SAFE ENV PARSERS
# ============================================================

def get_float_env(name, default):
    value = os.getenv(name)

    if not value or not value.strip():
        return default

    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def get_int_env(name, default):
    value = os.getenv(name)

    if not value or not value.strip():
        return default

    try:
        return int(value)
    except (ValueError, TypeError):
        return default


MIN_SIGNAL_SCORE = get_float_env(
    "MIN_SIGNAL_SCORE",
    6.0
)

MAX_ALERTS = get_int_env(
    "MAX_ALERTS",
    5
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
# EDITORIAL THRESHOLDS
# ============================================================

# KOL opportunity is scored 0-10.

POST_THRESHOLD = 7.0
WATCH_THRESHOLD = 5.0

# Breaking/security/regulatory events can deserve attention
# even when the normal narrative score is lower.
URGENT_THRESHOLD = 5.5


# ============================================================
# BRAND / NICHE
# ============================================================

TIER_1_TOPICS = [
    "stablecoin",
    "stablecoins",
    "stablecoin payments",
    "crypto payments",
    "payments",
    "payment infrastructure",
    "ai agents",
    "ai agent",
    "agentic commerce",
    "agentic economy",
    "agentic",
    "financial infrastructure",
    "onchain finance",
    "on-chain finance",
    "rwa",
    "real world assets",
    "real-world assets",
    "tokenization",
    "tokenisation",
    "wallet",
    "wallets",
    "smart wallet",
    "smart wallets",
    "usdc",
    "usdt",
    "remittance",
    "cross-border payments",
    "cross border payments",
    "settlement",
    "merchant payments",
]


TIER_2_TOPICS = [
    "defi",
    "ethereum",
    "bitcoin",
    "solana",
    "base",
    "arbitrum",
    "optimism",
    "layer 2",
    "l2",
    "account abstraction",
    "institutional",
    "regulation",
    "regulatory",
    "mainnet",
    "testnet",
    "security",
    "protocol",
    "infrastructure",
    "liquidity",
    "yield",
]


TIER_3_TOPICS = [
    "nft",
    "nfts",
    "digital ownership",
    "memecoin",
    "memecoins",
    "crypto culture",
    "meme",
    "creator economy",
]


ALL_TOPICS = (
    TIER_1_TOPICS
    + TIER_2_TOPICS
    + TIER_3_TOPICS
)


# ============================================================
# HIGH-VALUE EVENT TERMS
# ============================================================

BREAKING_TERMS = [
    "hack",
    "hacked",
    "exploit",
    "exploited",
    "attack",
    "attacked",
    "breach",
    "stolen",
    "drained",
    "drain",
    "halt",
    "halted",
    "outage",
    "shutdown",
    "insolvent",
    "bankrupt",
    "lawsuit",
    "indictment",
    "ban",
    "banned",
    "approval",
    "approved",
    "rejected",
    "etf",
    "regulator",
    "sec",
    "cftc",
]


HIGH_VALUE_TERMS = [
    "launch",
    "launched",
    "mainnet",
    "integration",
    "integrated",
    "partnership",
    "funding",
    "funded",
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
    "released",
    "volume",
    "settlement",
    "merchant",
    "remittance",
    "cross-border",
    "cross border",
    "treasury",
    "rwa",
]


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
# SOCIAL SEARCHES
# ============================================================

NEYNAR_QUERIES = [
    "stablecoin",
    "crypto payments",
    "AI agents",
    "DeFi",
    "RWA",
]


SORSA_QUERIES = [
    "stablecoin payments",
    "AI agents crypto",
    "crypto payments",
    "RWA tokenization",
    "DeFi",
]


# ============================================================
# HTTP SESSION
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
# BASIC HELPERS
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
            response.text[:300]
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
            timeout=45,
            **kwargs
        )

        if 200 <= response.status_code < 300:
            return response

        print(
            f"[POST HTTP {response.status_code}] "
            f"{url}"
        )

        print(
            response.text[:500]
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
        .replace("\r", " ")
        .split()
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


def safe_number(value, default=0):

    try:

        if value is None:
            return default

        return float(value)

    except (
        ValueError,
        TypeError
    ):

        return default


def matched_topics(text):

    text = clean_text(
        text
    ).lower()

    found = []

    for topic in ALL_TOPICS:

        if topic.lower() in text:
            found.append(topic)

    # Preserve order while removing duplicates.
    return list(
        dict.fromkeys(found)
    )


def contains_any(text, words):

    text = clean_text(
        text
    ).lower()

    return any(
        word.lower() in text
        for word in words
    )


def source_domain(source):

    source = (
        source or ""
    ).lower()

    if "reddit" in source:
        return "reddit"

    if "farcaster" in source:
        return "farcaster"

    if "github" in source:
        return "github"

    if "coindesk" in source:
        return "coindesk"

    if "cointelegraph" in source:
        return "cointelegraph"

    if "coinmarketcap" in source:
        return "coinmarketcap"

    if "coingecko" in source:
        return "coingecko"

    if "lunarcrush" in source:
        return "lunarcrush"

    if "sorsa" in source:
        return "sorsa"

    return source


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
            "chat_id":
                TELEGRAM_CHAT_ID,

            "text":
                message,

            "parse_mode":
                "HTML",

            "disable_web_page_preview":
                False
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
            "start":
                1,

            "limit":
                100,

            "convert":
                "USD"
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

            if (
                symbol not in WATCHLIST
                and len(results) >= 30
            ):
                continue

            quote = (
                coin
                .get("quote", {})
                .get("USD", {})
            )

            price = safe_number(
                quote.get("price")
            )

            change = safe_number(
                quote.get(
                    "percent_change_24h"
                )
            )

            volume = safe_number(
                quote.get(
                    "volume_24h"
                )
            )

            market_cap = safe_number(
                quote.get(
                    "market_cap"
                )
            )

            slug = coin.get(
                "slug",
                ""
            )

            results.append({

                "source":
                    "CoinMarketCap",

                "type":
                    "market",

                "id":
                    f"cmc:{symbol}",

                "title":
                    f"{symbol} market update",

                "text":
                    (
                        f"{symbol} price "
                        f"${price:,.6f}; "
                        f"24h change "
                        f"{change:.2f}%; "
                        f"24h volume "
                        f"${volume:,.0f}; "
                        f"market cap "
                        f"${market_cap:,.0f}"
                    ),

                "url":
                    (
                        "https://coinmarketcap.com/"
                        f"currencies/{slug}/"
                    ),

                "symbol":
                    symbol,

                "price":
                    price,

                "change_24h":
                    change,

                "volume_24h":
                    volume,

                "market_cap":
                    market_cap
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
        "BTC":
            "bitcoin",

        "ETH":
            "ethereum",

        "SOL":
            "solana",

        "USDC":
            "usd-coin",

        "USDT":
            "tether"
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

                "text":
                    (
                        f"{symbol} is trading around "
                        f"${safe_number(coin.get('usd')):,.6f}; "
                        f"24h change "
                        f"{safe_number(coin.get('usd_24h_change')):.2f}%"
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
                    ),

                "volume_24h":
                    coin.get(
                        "usd_24h_vol"
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

                published = clean_text(
                    entry.get(
                        "published",
                        entry.get(
                            "updated",
                            ""
                        )
                    )
                )

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
                        link,

                    "published":
                        published
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
            "https://www.reddit.com/"
            f"r/{subreddit}/new.json"
        )

        response = safe_get(
            url,
            params={
                "limit":
                    20,

                "raw_json":
                    1
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
                        safe_number(
                            data.get(
                                "score",
                                0
                            )
                        ),

                    "comments":
                        safe_number(
                            data.get(
                                "num_comments",
                                0
                            )
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
            "[LUNARCRUSH] "
            "API key missing"
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
            "limit":
                50
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

    results = []

    for query in NEYNAR_QUERIES:

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
                        f"Farcaster discussion: {query}",

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

    results = []

    for query in SORSA_QUERIES:

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
                        ),

                    "stars":
                        repo.get(
                            "stargazers_count",
                            0
                        ),

                    "forks":
                        repo.get(
                            "forks_count",
                            0
                        )
                })

        except Exception as exc:

            print(
                f"[GITHUB PARSE] "
                f"{exc}"
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

    score = 0

    topics = matched_topics(
        text
    )

    # --------------------------------------------------------
    # NICHE RELEVANCE
    # --------------------------------------------------------

    for topic in topics:

        if topic in TIER_1_TOPICS:
            score += 2.5

        elif topic in TIER_2_TOPICS:
            score += 1.5

        elif topic in TIER_3_TOPICS:
            score += 0.75

    # --------------------------------------------------------
    # HIGH VALUE EVENTS
    # --------------------------------------------------------

    for word in HIGH_VALUE_TERMS:

        if word in text:
            score += 1.0

    # --------------------------------------------------------
    # BREAKING EVENTS
    # --------------------------------------------------------

    for word in BREAKING_TERMS:

        if word in text:
            score += 2.0

    # --------------------------------------------------------
    # MARKET MOVEMENT
    # --------------------------------------------------------

    change = item.get(
        "change_24h"
    )

    if isinstance(
        change,
        (int, float)
    ):

        if abs(change) >= 15:
            score += 5

        elif abs(change) >= 10:
            score += 4

        elif abs(change) >= 5:
            score += 2

    # --------------------------------------------------------
    # COMMUNITY ENGAGEMENT
    # --------------------------------------------------------

    comments = item.get(
        "comments",
        0
    )

    if isinstance(
        comments,
        (int, float)
    ):

        if comments >= 500:
            score += 3

        elif comments >= 100:
            score += 2

        elif comments >= 30:
            score += 1

    # --------------------------------------------------------
    # GITHUB TRACTION
    # --------------------------------------------------------

    stars = item.get(
        "stars",
        0
    )

    if isinstance(
        stars,
        (int, float)
    ):

        if stars >= 500:
            score += 3

        elif stars >= 100:
            score += 2

        elif stars >= 25:
            score += 1

    return round(
        min(score, 25),
        2
    )


# ============================================================
# NARRATIVE CLUSTERING
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

                    "domains":
                        set(),

                    "score":
                        0
                }

            clusters[key]["items"].append(
                item
            )

            source = item.get(
                "source",
                ""
            )

            clusters[key]["sources"].add(
                source
            )

            clusters[key]["domains"].add(
                source_domain(source)
            )

            clusters[key]["score"] += (
                item.get(
                    "signal_score",
                    0
                )
            )

    output = []

    for cluster in clusters.values():

        item_count = len(
            cluster["items"]
        )

        source_count = len(
            cluster["sources"]
        )

        domain_count = len(
            cluster["domains"]
        )

        confirmation = min(
            domain_count * 2.5,
            10
        )

        volume = min(
            item_count * 0.75,
            6
        )

        narrative_score = round(
            min(
                cluster["score"]
                + confirmation
                + volume,
                35
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

            "domain_count":
                domain_count,

            "sources":
                sorted(
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
# EDITORIAL MODE PRE-SELECTION
# ============================================================

def choose_editorial_mode(
    items,
    narratives
):

    combined = " ".join(
        (
            item.get(
                "title",
                ""
            )
            + " "
            + item.get(
                "text",
                ""
            )
        )
        for item in items[:15]
    ).lower()

    if contains_any(
        combined,
        [
            "hack",
            "exploit",
            "breach",
            "stolen",
            "drained",
            "outage",
            "halted"
        ]
    ):
        return "breaking"

    if contains_any(
        combined,
        [
            "lawsuit",
            "regulator",
            "regulation",
            "sec",
            "ban",
            "approval"
        ]
    ):
        return "investigative"

    if contains_any(
        combined,
        [
            "github",
            "repository",
            "open source",
            "developer",
            "sdk",
            "api",
            "protocol"
        ]
    ):
        if contains_any(
            combined,
            [
                "ai agent",
                "ai agents",
                "stablecoin",
                "payment"
            ]
        ):
            return "technical"

        return "builder_perspective"

    if contains_any(
        combined,
        [
            "payment",
            "payments",
            "stablecoin",
            "settlement",
            "remittance"
        ]
    ):
        return "analytical"

    if contains_any(
        combined,
        [
            "nft",
            "nfts",
            "memecoin",
            "meme",
            "culture"
        ]
    ):
        return "cultural_observation"

    if narratives:

        top_topic = (
            narratives[0]
            .get(
                "topic",
                ""
            )
            .lower()
        )

        if "defi" in top_topic:
            return "analytical"

        if "rwa" in top_topic:
            return "investigative"

    return "market_observation"


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

    editorial_mode = choose_editorial_mode(
        items,
        narratives
    )

    compact_items = []

    for index, item in enumerate(
        items[:30],
        start=1
    ):

        compact_items.append({

            "source_id":
                f"S{index}",

            "source":
                item.get(
                    "source"
                ),

            "type":
                item.get(
                    "type"
                ),

            "title":
                item.get(
                    "title"
                ),

            "text":
                item.get(
                    "text",
                    ""
                )[:2200],

            "url":
                item.get(
                    "url"
                ),

            "signal_score":
                item.get(
                    "signal_score"
                ),

            "topics":
                item.get(
                    "matched_topics",
                    []
                ),

            "change_24h":
                item.get(
                    "change_24h"
                ),

            "comments":
                item.get(
                    "comments"
                ),

            "stars":
                item.get(
                    "stars"
                )
        })

    system_prompt = r"""
You are the senior editorial intelligence
engine for a serious crypto creator.

Your job is NOT to summarize the internet.

Your job is to find the small number of
crypto developments worth talking about and
turn them into differentiated content.

==================================================
CREATOR POSITIONING
==================================================

The creator is building long-term authority around:

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
Solana when relevant
NFTs and crypto culture when there is a genuine angle

The creator wants to become known for:

seeing important narratives early
understanding infrastructure
connecting technology to real-world use
explaining why something matters
questioning weak narratives
finding the second-order effect

Do NOT turn the creator into a generic
"crypto news" account.

==================================================
MOST IMPORTANT RULE
==================================================

DO NOT INVENT FACTS.

Never manufacture:

numbers
dates
users
transaction volumes
funding
partnerships
adoption
technical capabilities
quotes
audits
regulatory decisions
outages
investor behavior
future timelines

If the supplied sources do not establish
something, say that it is unknown.

==================================================
SOURCE DISCIPLINE
==================================================

Every supplied signal has a source_id.

Example:

S1
S2
S3

Use those source IDs in the final evidence
section.

A single source is NOT automatically
independent confirmation.

Social posts are evidence of discussion,
not necessarily evidence that the underlying
claim is true.

Reddit discussion is evidence of community
interest, not proof.

GitHub activity proves repository activity,
not user adoption.

A company's own announcement proves that
the company made the announcement, not that
the announcement's claims are independently
verified.

Market APIs provide market data, not
explanations for why the market moved.

==================================================
FACT / INFERENCE / FORECAST
==================================================

Keep these categories completely separate.

VERIFIED FACT

The supplied source explicitly supports it.

INTERPRETATION

A reasonable conclusion derived from facts.

FORECAST

A possible future outcome.

UNKNOWN

Something the evidence does not establish.

Never write an interpretation as if it were
a verified fact.

Never write a forecast as if it were certain.

==================================================
IMPORTANT CLAIM RULE
==================================================

If a claim is unusually important, controversial,
numerical, or likely to affect reputation,
require stronger evidence.

Examples:

"USDT reserves increased by $X"
"Base processed $X"
"Solana lost X% of stake"
"Protocol has X users"
"company raised $X"
"X adopted the protocol"

If only one source supports the claim,
do not present it as independently confirmed.

Use wording such as:

"the company says..."
"according to..."
"one report claims..."
"the repository describes..."

when appropriate.

==================================================
NARRATIVE DETECTION
==================================================

A strong narrative is more than a collection
of articles.

Look for convergence between:

news
market data
developer activity
social discussion
community interest
institutional activity
regulatory activity

The strongest stories often have:

signal + timing + evidence + tension

Examples of useful tension:

institutional confidence
vs
real-world adoption

high TPS
vs
reliability

stablecoin growth
vs
merchant usage

AI agent capability
vs
payment infrastructure

regulatory clarity
vs
actual implementation

capital inflows
vs
fundamental usage

==================================================
KOL OPPORTUNITY
==================================================

Score KOL opportunity from 0 to 10.

Consider:

relevance
novelty
evidence
timing
discussion potential
differentiation
second-order insight

0-3:

weak

4-5:

interesting but not strong

6:

worth monitoring

7:

good post opportunity

8:

strong post opportunity

9:

high-value narrative

10:

rare / exceptional opportunity

Do not give 8-10 merely because something
is trending.

==================================================
CONFIDENCE
==================================================

Confidence is 0-100.

This measures confidence in the overall
editorial assessment.

It does NOT mean probability that a forecast
will happen.

Examples:

85 means strong evidence for the assessment.

60 means meaningful but incomplete evidence.

35 means speculative.

==================================================
EVIDENCE SCORE
==================================================

Evidence score is 0-10.

Consider:

source quality
independent confirmation
specificity
recency
direct evidence

Do not give 9-10 to a story based primarily
on social chatter.

==================================================
DECISION
==================================================

POST

Use when there is a differentiated and
well-supported opportunity.

WATCH

Use when the signal is interesting but
evidence or differentiation is insufficient.

NO_POST

Use when the signal is weak, repetitive,
misleading, trivial, or unsupported.

IMPORTANT:

Do not generate draft content for NO_POST.

For WATCH, generate a draft only if there is
a clear research angle and confidence is high
enough to be useful.

==================================================
WRITING MODES
==================================================

Choose based on the actual story.

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

Do NOT always choose analytical.

==================================================
WRITING STYLE
==================================================

Sound:

crypto-native
sharp
human
observant
curious
specific
occasionally skeptical

Do not sound like:

corporate PR
AI-generated newsletters
generic crypto influencers
marketing copy

Avoid clichés:

"game changer"
"revolutionary"
"the future is here"
"this is huge"
"mass adoption is coming"
"bullish"
"exciting times ahead"

unless there is an extremely specific reason.

Do not use "finally" as a generic hook.

Do not manufacture certainty.

Do not use excessive emojis.

Do not automatically add hashtags.

Do not stuff keywords.

==================================================
HOOK RULES
==================================================

Hooks should create curiosity through:

a surprising fact
a tension
a contradiction
a useful observation
a specific number
a question worth answering

Bad:

"AI is changing crypto."

Better:

"the interesting part of AI agents isn't
what they can do. it's how they will pay
for it."

Only use a numerical hook when the supplied
evidence supports the number.

==================================================
CONTENT FORMATS
==================================================

Choose the format that best fits the story.

short_post
thread
quote_post
reply
research_note

Do not produce a thread simply because a
topic is important.

==================================================
POST QUALITY TEST
==================================================

Before generating content ask:

Would an informed crypto user learn something?

Is there a specific observation?

Is the angle differentiated?

Is the evidence sufficient?

Is there a second-order implication?

Could 10,000 crypto AI accounts post this
exact same thing?

If yes, improve the angle.

==================================================
NO-FORCED-CONTENT RULE
==================================================

The system must be comfortable saying:

NO_POST

or:

WATCH

There is no reward for producing content
about everything.

The creator's reputation is more important
than posting frequency.

==================================================
OUTPUT
==================================================

Return VALID JSON ONLY.

Use exactly this general structure:

{
  "decision": "POST|WATCH|NO_POST",

  "summary": "...",

  "confidence": 0,

  "evidence_score": 0,

  "kol_opportunity_score": 0,

  "writing_mode": "...",

  "narratives": [],

  "narrative_status":
    "new|emerging|accelerating|cooling|stable",

  "verified_facts": [],

  "interpretations": [],

  "forecasts": [],

  "unknowns": [],

  "why_it_matters": [],

  "content_opportunities": [
    {
      "title": "...",
      "angle": "..."
    }
  ],

  "recommended_posts": [
    {
      "format": "...",
      "hook": "...",
      "angle": "...",
      "post": "...",
      "source_ids": []
    }
  ],

  "sources": [
    {
      "claim": "...",
      "source_ids": []
    }
  ]
}

==================================================
STRICT OUTPUT RULE
==================================================

confidence MUST be a number between 0 and 100.

evidence_score MUST be a number between 0 and 10.

kol_opportunity_score MUST be a number between
0 and 10.

Never return confidence such as 0.85 when the
intended meaning is 85.

==================================================
FINAL EDITORIAL RULE
==================================================

The creator is building a reputation over years.

Protect credibility.

A missed story is better than publishing
something wrong.

A cautious observation with a sharp angle
is better than an exaggerated prediction.
"""


    user_payload = {

        "editorial_mode_hint":
            editorial_mode,

        "previous_narratives":
            previous_topics[-75:],

        "narrative_clusters":
            narratives[:15],

        "signals":
            compact_items,

        "task":
            """
Analyze these signals as a senior crypto
editorial desk.

Find the strongest narrative.

Determine:

1. What is verified?
2. What is only an interpretation?
3. What is a forecast?
4. What remains unknown?
5. How strong is the evidence?
6. How much independent source support exists?
7. Is the narrative new, emerging, accelerating,
   cooling, or stable?
8. Is this worth posting?
9. What angle would differentiate the creator?
10. What writing mode fits the story?
11. What content format fits the story?

Do not force a post.

Use source IDs.

If a major claim comes from only one source,
make that explicit.

If the story is weak, return WATCH or NO_POST.
"""
    }


    response = safe_post(

        "https://api.groq.com/openai/v1/"
        "chat/completions",

        headers={

            "Authorization":
                f"Bearer {GROQ_API_KEY}",

            "Content-Type":
                "application/json"
        },

        json={

            "model":
                GROQ_MODEL,

            "temperature":
                0.35,

            "max_tokens":
                7000,

            "response_format": {
                "type":
                    "json_object"
            },

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
            ]
        }
    )

    if not response:
        return None

    try:

        data = response.json()

        choices = data.get(
            "choices",
            []
        )

        if not choices:
            print(
                "[GROQ] No choices returned"
            )
            return None

        content = (
            choices[0]
            .get("message", {})
            .get("content", "")
        )

        if not content:
            print(
                "[GROQ] Empty content"
            )
            return None

        # Defensive JSON cleanup.
        content = content.strip()

        if content.startswith(
            "```json"
        ):

            content = content[
                7:
            ].strip()

        if content.endswith(
            "```"
        ):

            content = content[
                :-3
            ].strip()

        result = json.loads(
            content
        )

        return normalize_analysis(
            result
        )

    except Exception as exc:

        print(
            f"[GROQ PARSE ERROR] "
            f"{exc}"
        )

        try:

            print(
                response.text[:2000]
            )

        except Exception:
            pass

        return None


# ============================================================
# NORMALIZE AI OUTPUT
# ============================================================

def normalize_analysis(
    analysis
):

    if not isinstance(
        analysis,
        dict
    ):
        return None

    # --------------------------------------------------------
    # DECISION
    # --------------------------------------------------------

    decision = str(
        analysis.get(
            "decision",
            "WATCH"
        )
    ).upper().strip()

    if decision not in {
        "POST",
        "WATCH",
        "NO_POST"
    }:

        decision = "WATCH"

    analysis[
        "decision"
    ] = decision

    # --------------------------------------------------------
    # CONFIDENCE
    # --------------------------------------------------------

    confidence = safe_number(
        analysis.get(
            "confidence",
            0
        )
    )

    # If model accidentally returns 0.85,
    # interpret it as 85 only when it is <= 1.
    if 0 < confidence <= 1:
        confidence *= 100

    analysis[
        "confidence"
    ] = round(
        max(
            0,
            min(
                confidence,
                100
            )
        ),
        1
    )

    # --------------------------------------------------------
    # EVIDENCE
    # --------------------------------------------------------

    evidence = safe_number(
        analysis.get(
            "evidence_score",
            0
        )
    )

    if 0 < evidence <= 1:
        evidence *= 10

    analysis[
        "evidence_score"
    ] = round(
        max(
            0,
            min(
                evidence,
                10
            )
        ),
        1
    )

    # --------------------------------------------------------
    # KOL SCORE
    # --------------------------------------------------------

    kol = safe_number(
        analysis.get(
            "kol_opportunity_score",
            0
        )
    )

    if 0 < kol <= 1:
        kol *= 10

    analysis[
        "kol_opportunity_score"
    ] = round(
        max(
            0,
            min(
                kol,
                10
            )
        ),
        1
    )

    # --------------------------------------------------------
    # ARRAYS
    # --------------------------------------------------------

    array_fields = [
        "narratives",
        "verified_facts",
        "interpretations",
        "forecasts",
        "unknowns",
        "why_it_matters",
        "content_opportunities",
        "recommended_posts",
        "sources"
    ]

    for field in array_fields:

        if not isinstance(
            analysis.get(field),
            list
        ):

            analysis[field] = []

    # --------------------------------------------------------
    # DECISION SAFETY
    # --------------------------------------------------------

    # Don't allow a weak opportunity to masquerade
    # as a strong POST.
    if (
        decision == "POST"
        and (
            analysis["kol_opportunity_score"]
            < POST_THRESHOLD
            or analysis["evidence_score"]
            < 5.5
        )
    ):

        analysis[
            "decision"
        ] = "WATCH"

    # --------------------------------------------------------
    # NO POST MUST NOT CONTAIN CONTENT DRAFTS
    # --------------------------------------------------------

    if analysis[
        "decision"
    ] == "NO_POST":

        analysis[
            "recommended_posts"
        ] = []

    return analysis


# ============================================================
# TELEGRAM FORMAT HELPERS
# ============================================================

def escape_html(text):

    if text is None:
        return ""

    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def format_opportunity(
    opportunity
):

    if isinstance(
        opportunity,
        dict
    ):

        title = escape_html(
            opportunity.get(
                "title",
                ""
            )
        )

        angle = escape_html(
            opportunity.get(
                "angle",
                ""
            )
        )

        return (
            f"• <b>{title}</b>\n"
            f"  → {angle}"
        )

    return (
        f"• "
        f"{escape_html(opportunity)}"
    )


# ============================================================
# TELEGRAM ALERT FORMAT
# ============================================================

def format_alert(
    analysis,
    items
):

    if not analysis:
        return None

    decision = analysis.get(
        "decision",
        "WATCH"
    )

    lines = []

    lines.append(
        "🧠 <b>WEB3STATION</b>"
    )

    lines.append("")

    # --------------------------------------------------------
    # DECISION
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    summary = escape_html(
        analysis.get(
            "summary",
            ""
        )
    )

    if summary:

        lines.append(
            summary
        )

        lines.append("")

    # --------------------------------------------------------
    # SCORES
    # --------------------------------------------------------

    confidence = analysis.get(
        "confidence",
        0
    )

    evidence = analysis.get(
        "evidence_score",
        0
    )

    kol = analysis.get(
        "kol_opportunity_score",
        0
    )

    mode = escape_html(
        analysis.get(
            "writing_mode",
            "n/a"
        )
    )

    narrative_status = escape_html(
        analysis.get(
            "narrative_status",
            "stable"
        )
    )

    lines.append(
        f"🎯 confidence: "
        f"<b>{confidence}/100</b>"
    )

    lines.append(
        f"🔎 evidence: "
        f"<b>{evidence}/10</b>"
    )

    lines.append(
        f"💡 KOL opportunity: "
        f"<b>{kol}/10</b>"
    )

    lines.append(
        f"✍️ mode: "
        f"<b>{mode}</b>"
    )

    lines.append(
        f"📈 narrative: "
        f"<b>{narrative_status}</b>"
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
            "<b>NARRATIVES</b>"
        )

        for narrative in narratives[:5]:

            lines.append(
                "• "
                + escape_html(
                    narrative
                )
            )

    # --------------------------------------------------------
    # VERIFIED FACTS
    # --------------------------------------------------------

    facts = analysis.get(
        "verified_facts",
        []
    )

    if facts:

        lines.append("")

        lines.append(
            "<b>WHAT WE KNOW</b>"
        )

        for fact in facts[:5]:

            lines.append(
                "✓ "
                + escape_html(
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
            "<b>WHAT WE'RE INFERRING</b>"
        )

        for point in interpretations[:4]:

            lines.append(
                "→ "
                + escape_html(
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
            "<b>WHAT COULD HAPPEN NEXT</b>"
        )

        for point in forecasts[:3]:

            lines.append(
                "↗ "
                + escape_html(
                    point
                )
            )

    # --------------------------------------------------------
    # UNKNOWN
    # --------------------------------------------------------

    unknowns = analysis.get(
        "unknowns",
        []
    )

    if unknowns:

        lines.append("")

        lines.append(
            "<b>⚠ WHAT WE DON'T KNOW</b>"
        )

        for point in unknowns[:4]:

            lines.append(
                "⚠ "
                + escape_html(
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
            "<b>WHY IT MATTERS</b>"
        )

        for point in why[:4]:

            lines.append(
                "• "
                + escape_html(
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
    # DRAFT CONTENT
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

            if not isinstance(
                post,
                dict
            ):
                continue

            fmt = escape_html(
                post.get(
                    "format",
                    ""
                )
            )

            hook = escape_html(
                post.get(
                    "hook",
                    ""
                )
            )

            angle = escape_html(
                post.get(
                    "angle",
                    ""
                )
            )

            body = escape_html(
                post.get(
                    "post",
                    ""
                )
            )

            source_ids = post.get(
                "source_ids",
                []
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

            if source_ids:

                lines.append("")

                lines.append(
                    "sources: "
                    + escape_html(
                        ", ".join(
                            str(x)
                            for x in source_ids
                        )
                    )
                )

    # --------------------------------------------------------
    # EVIDENCE MAP
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
            "<b>EVIDENCE MAP</b>"
        )

        for source in sources[:8]:

            if not isinstance(
                source,
                dict
            ):
                continue

            claim = escape_html(
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
                    "  "
                    + escape_html(
                        ", ".join(
                            str(x)
                            for x in source_ids
                        )
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

        for index, item in enumerate(
            top_items[:8],
            start=1
        ):

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

            safe_url = escape_html(
                url
            )

            safe_title = escape_html(
                title[:100]
            )

            lines.append(
                f'• <a href="{safe_url}">'
                f'{safe_title}</a>'
            )

    return "\n".join(
        lines
    )


# ============================================================
# TELEGRAM MESSAGE LENGTH
# ============================================================

def send_long_telegram(
    message
):

    if len(message) <= 3900:

        return telegram(
            message
        )

    # Telegram limit safety.
    chunks = []

    remaining = message

    while remaining:

        if len(remaining) <= 3900:

            chunks.append(
                remaining
            )

            break

        split_at = remaining.rfind(
            "\n",
            0,
            3900
        )

        if split_at < 1000:

            split_at = 3900

        chunks.append(
            remaining[
                :split_at
            ]
        )

        remaining = remaining[
            split_at:
        ].lstrip()

    success = True

    for chunk in chunks:

        if not telegram(
            chunk
        ):

            success = False

    return success


# ============================================================
# MEMORY
# ============================================================

def update_memory(
    seen,
    candidates,
    topic_history,
    narrative_clusters,
    analysis
):

    for item in candidates:

        item_id = item.get(
            "id"
        )

        if item_id:

            seen.add(
                item_id
            )

    narrative_names = [

        cluster.get(
            "topic"
        )

        for cluster
        in narrative_clusters[:10]

        if cluster.get(
            "topic"
        )
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
        list(seen)[-5000:]
    )

    save_json(
        TOPIC_FILE,
        topic_history[-750:]
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=============================================="
    )

    print(
        "WEB3STATION INTELLIGENCE v3"
    )

    print(
        f"Started: {now()}"
    )

    print(
        "=============================================="
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

    # ========================================================
    # COLLECTORS
    # ========================================================

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
        )
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

            all_items.extend(
                items
            )

        except Exception as exc:

            print(
                f"[COLLECT ERROR] "
                f"{name}: {exc}"
            )

    print(
        f"\nTOTAL RAW SIGNALS: "
        f"{len(all_items)}"
    )

    # ========================================================
    # DEDUPLICATE
    # ========================================================

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

    # ========================================================
    # NARRATIVE CLUSTERS
    # ========================================================

    narrative_clusters = (
        build_narrative_clusters(
            candidates
        )
    )

    print(
        "\nNARRATIVE CLUSTERS:"
    )

    for cluster in narrative_clusters[:12]:

        print(
            f"  "
            f"{cluster.get('topic')} "
            f"| signals="
            f"{cluster.get('item_count')} "
            f"| sources="
            f"{cluster.get('source_count')} "
            f"| domains="
            f"{cluster.get('domain_count')} "
            f"| score="
            f"{cluster.get('score')}"
        )

    # ========================================================
    # STRONG SIGNALS
    # ========================================================

    strong_candidates = [

        item

        for item in candidates

        if item.get(
            "signal_score",
            0
        ) >= MIN_SIGNAL_SCORE
    ]

    strong_candidates = (
        strong_candidates[:40]
    )

    # ========================================================
    # NO SIGNAL
    # ========================================================

    if not strong_candidates:

        print(
            "No strong signals."
        )

        # Mark scanned items as seen.
        for item in candidates[:100]:

            if item.get("id"):

                seen.add(
                    item["id"]
                )

        save_json(
            SEEN_FILE,
            list(seen)[-5000:]
        )

        telegram(

            "🛰 <b>WEB3STATION SCAN</b>\n\n"

            "No high-confidence narrative "
            "detected in this scan.\n\n"

            f"Sources scanned: "
            f"{len(collectors)}\n"

            f"New signals: "
            f"{len(candidates)}\n\n"

            "The desk is still watching."
        )

        return

    # ========================================================
    # AI ANALYSIS
    # ========================================================

    analysis = groq_analyze(

        strong_candidates,

        narrative_clusters,

        topic_history
    )

    if not analysis:

        print(
            "AI analysis failed."
        )

        telegram(

            "⚠️ <b>WEB3STATION</b>\n\n"

            "Signals were collected, but "
            "the editorial AI layer failed "
            "during this scan.\n\n"

            "The next scheduled scan will retry."
        )

        return

    # ========================================================
    # SECONDARY SAFETY CHECK
    # ========================================================

    decision = analysis.get(
        "decision",
        "WATCH"
    )

    confidence = analysis.get(
        "confidence",
        0
    )

    evidence = analysis.get(
        "evidence_score",
        0
    )

    kol = analysis.get(
        "kol_opportunity_score",
        0
    )

    # If model says POST but evidence is poor,
    # downgrade it.
    if (

        decision == "POST"

        and (

            evidence < 5.5

            or kol < POST_THRESHOLD

        )

    ):

        analysis[
            "decision"
        ] = "WATCH"

        decision = "WATCH"

    # --------------------------------------------------------
    # Extremely low evidence
    # --------------------------------------------------------

    if evidence < 3.5:

        analysis[
            "decision"
        ] = "NO_POST"

        analysis[
            "recommended_posts"
        ] = []

        decision = "NO_POST"

    # ========================================================
    # TELEGRAM
    # ========================================================

    message = format_alert(

        analysis,

        strong_candidates
    )

    if message:

        send_long_telegram(
            message
        )

    # ========================================================
    # MEMORY
    # ========================================================

    update_memory(

        seen,

        candidates,

        topic_history,

        narrative_clusters,

        analysis
    )

    # ========================================================
    # RUN SUMMARY
    # ========================================================

    print(
        "\n=============================================="
    )

    print(
        "RUN COMPLETE"
    )

    print(
        f"Decision: {decision}"
    )

    print(
        f"Confidence: {confidence}/100"
    )

    print(
        f"Evidence: {evidence}/10"
    )

    print(
        f"KOL opportunity: {kol}/10"
    )

    print(
        f"Writing mode: "
        f"{analysis.get('writing_mode', 'n/a')}"
    )

    print(
        "=============================================="
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
