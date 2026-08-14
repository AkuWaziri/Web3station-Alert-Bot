import os
import json
import hashlib
import html
import re
from datetime import datetime, timezone

import requests
import feedparser


# ============================================================
# WEB3STATION INTELLIGENCE ENGINE
# v3 - editorial intelligence / KOL content system
# ============================================================

VERSION = "3.0"


# ============================================================
# CONFIG
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

CMC_API_KEY = os.getenv("CMC_API_KEY", "").strip()
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "").strip()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
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


def get_float_env(name, default):
    value = os.getenv(name, "")

    if not value or not value.strip():
        return default

    try:
        return float(value)
    except Exception:
        return default


def get_int_env(name, default):
    value = os.getenv(name, "")

    if not value or not value.strip():
        return default

    try:
        return int(value)
    except Exception:
        return default


MIN_SIGNAL_SCORE = get_float_env(
    "MIN_SIGNAL_SCORE",
    5.0
)

MAX_ALERTS = get_int_env(
    "MAX_ALERTS",
    3
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
# CREATOR NICHE
# ============================================================

TIER_1_TOPICS = [
    "stablecoin",
    "stablecoins",
    "stablecoin payments",
    "payments",
    "crypto payments",
    "onchain payments",
    "cross border payments",
    "cross-border payments",
    "remittance",
    "settlement",
    "settlements",
    "ai agents",
    "ai agent",
    "agentic commerce",
    "agentic economy",
    "agentic",
    "financial infrastructure",
    "onchain finance",
    "rwa",
    "real world assets",
    "tokenization",
    "tokenisation",
    "wallet",
    "wallets",
    "smart wallet",
    "smart wallets",
    "usdc",
    "usdt",
    "circle",
    "digital dollar",
    "digital dollars",
    "tokenized deposits",
    "tokenised deposits",
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
    "layer2",
    "l2",
    "account abstraction",
    "institutional",
    "regulation",
    "regulatory",
    "mainnet",
    "infrastructure",
    "oracle",
    "bridges",
    "bridge",
    "security",
    "hack",
    "exploit",
    "funding",
]


TIER_3_TOPICS = [
    "nft",
    "nfts",
    "digital ownership",
    "memecoin",
    "memecoins",
    "crypto culture",
    "creator economy",
]


ALL_TOPICS = (
    TIER_1_TOPICS
    + TIER_2_TOPICS
    + TIER_3_TOPICS
)


# ============================================================
# SEARCH TOPICS
# ============================================================

SORSA_QUERIES = [
    '"stablecoin" payments',
    '"USDC" payments',
    '"USDT" payments',
    '"AI agents" crypto',
    '"agentic commerce"',
    '"RWA" tokenization',
    '"tokenization" crypto',
    '"onchain finance"',
    '"crypto payments"',
    '"DeFi"',
]


NEYNAR_QUERIES = [
    "stablecoin",
    "crypto payments",
    "AI agents",
    "RWA",
    "tokenization",
    "DeFi",
]


GITHUB_SEARCHES = [
    "stablecoin payments",
    "crypto payments",
    "AI agents crypto",
    "agentic commerce crypto",
    "RWA tokenization",
    "onchain finance",
    "DeFi infrastructure",
]


REDDIT_SUBREDDITS = [
    "CryptoCurrency",
    "ethereum",
    "defi",
    "solana",
    "Bitcoin",
    "artificial",
    "CryptoTechnology",
]


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
# SESSION
# ============================================================

SESSION = requests.Session()

SESSION.headers.update({
    "User-Agent":
        "Web3Station-Intelligence/3.0"
})


# ============================================================
# TIME
# ============================================================

def now():
    return datetime.now(
        timezone.utc
    ).isoformat()


def time_bucket(minutes=30):
    current = datetime.now(timezone.utc)

    bucket = (
        current.hour * 60
        + current.minute
    ) // minutes

    return (
        current.strftime("%Y-%m-%d")
        + "-"
        + str(bucket)
    )


# ============================================================
# HTTP
# ============================================================

def safe_get(
    url,
    timeout=20,
    **kwargs
):

    try:

        response = SESSION.get(
            url,
            timeout=timeout,
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
            f"[GET ERROR] "
            f"{url}: {exc}"
        )

    return None


def safe_post(
    url,
    timeout=30,
    **kwargs
):

    try:

        response = SESSION.post(
            url,
            timeout=timeout,
            **kwargs
        )

        if response.status_code in (
            200,
            201
        ):
            return response

        print(
            f"[POST HTTP {response.status_code}] "
            f"{url}"
        )

        print(
            response.text[:800]
        )

    except Exception as exc:

        print(
            f"[POST ERROR] "
            f"{url}: {exc}"
        )

    return None


# ============================================================
# TEXT / JSON HELPERS
# ============================================================

def clean_text(text):

    if text is None:
        return ""

    text = html.unescape(
        str(text)
    )

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    return " ".join(
        text
        .replace("\n", " ")
        .replace("\r", " ")
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
        str(x)
        for x in parts
        if x is not None
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def load_json(
    path,
    default
):

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception:

        return default


def save_json(
    path,
    data
):

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


# ============================================================
# TOPIC MATCHING
# ============================================================

def matched_topics(text):

    text = clean_text(
        text
    ).lower()

    found = []

    for topic in ALL_TOPICS:

        if topic.lower() in text:

            found.append(
                topic
            )

    return list(
        dict.fromkeys(found)
    )


def primary_topic(item):

    topics = item.get(
        "matched_topics",
        []
    )

    if not topics:
        return "general crypto"

    for topic in TIER_1_TOPICS:

        if topic in topics:
            return topic

    for topic in TIER_2_TOPICS:

        if topic in topics:
            return topic

    return topics[0]


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

    symbols = [
        symbol
        for symbol in WATCHLIST
    ]

    if not symbols:
        return []

    url = (
        "https://pro-api.coinmarketcap.com/"
        "v3/cryptocurrency/quotes/latest"
    )

    response = safe_get(
        url,
        headers={
            "X-CMC_PRO_API_KEY":
                CMC_API_KEY,

            "Accept":
                "application/json"
        },
        params={
            "symbol":
                ",".join(symbols),

            "convert":
                "USD"
        }
    )

    if not response:
        return []

    try:

        payload = response.json()

        data = payload.get(
            "data",
            {}
        )

        results = []

        if isinstance(
            data,
            list
        ):

            records = data

        else:

            records = []

            for symbol, values in data.items():

                if isinstance(
                    values,
                    list
                ):
                    records.extend(
                        values
                    )

        bucket = time_bucket(
            30
        )

        for coin in records:

            symbol = (
                coin.get(
                    "symbol",
                    ""
                )
                .upper()
            )

            if symbol not in WATCHLIST:
                continue

            quote = (
                coin
                .get("quote", {})
                .get("USD", {})
            )

            price = quote.get(
                "price",
                0
            )

            change_1h = quote.get(
                "percent_change_1h",
                0
            )

            change_24h = quote.get(
                "percent_change_24h",
                0
            )

            change_7d = quote.get(
                "percent_change_7d",
                0
            )

            volume = quote.get(
                "volume_24h",
                0
            )

            market_cap = quote.get(
                "market_cap",
                0
            )

            results.append({
                "source":
                    "CoinMarketCap",

                "type":
                    "market",

                "id":
                    make_id(
                        "cmc",
                        symbol,
                        bucket
                    ),

                "title":
                    f"{symbol} market signal",

                "text":
                    (
                        f"{symbol} price "
                        f"${price:,.6f}; "
                        f"1h change "
                        f"{change_1h:.2f}%; "
                        f"24h change "
                        f"{change_24h:.2f}%; "
                        f"7d change "
                        f"{change_7d:.2f}%; "
                        f"24h volume "
                        f"${volume:,.0f}; "
                        f"market cap "
                        f"${market_cap:,.0f}."
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
                    price,

                "change_1h":
                    change_1h,

                "change_24h":
                    change_24h,

                "change_7d":
                    change_7d,

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
# COINGECKO VALIDATION
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
                "true"
        }
    )

    if not response:
        return []

    try:

        data = response.json()

        results = []

        bucket = time_bucket(
            30
        )

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
                    make_id(
                        "coingecko",
                        symbol,
                        bucket
                    ),

                "title":
                    f"{symbol} market validation",

                "text":
                    (
                        f"{symbol} is around "
                        f"${coin.get('usd', 0):,.6f}; "
                        f"24h change "
                        f"{coin.get('usd_24h_change', 0):.2f}%."
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
# RSS NEWS
# ============================================================

def fetch_rss():

    results = []

    for source, url in RSS_FEEDS:

        try:

            feed = feedparser.parse(
                url
            )

            for entry in feed.entries[:30]:

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
            "https://www.reddit.com/"
            f"r/{subreddit}/new.json"
        )

        response = safe_get(
            url,
            headers={
                "User-Agent":
                    "Web3Station/3.0"
            },
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

                post_id = data.get(
                    "id",
                    ""
                )

                if not title or not post_id:
                    continue

                permalink = data.get(
                    "permalink",
                    ""
                )

                results.append({
                    "source":
                        f"Reddit/r/{subreddit}",

                    "type":
                        "community",

                    "id":
                        make_id(
                            "reddit",
                            subreddit,
                            post_id
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
                    make_id(
                        "lunarcrush",
                        symbol,
                        time_bucket(60)
                    ),

                "title":
                    f"{symbol} social signal",

                "text":
                    json.dumps(
                        coin,
                        ensure_ascii=False
                    )[:5000],

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

                if not text or not cast_hash:
                    continue

                results.append({
                    "source":
                        "Farcaster",

                    "type":
                        "social",

                    "id":
                        make_id(
                            "farcaster",
                            cast_hash
                        ),

                    "title":
                        f"Farcaster discussion: "
                        f"{query}",

                    "text":
                        text[:4000],

                    "url":
                        (
                            "https://warpcast.com/"
                        ),

                    "engagement":
                        cast.get(
                            "reactions",
                            {}
                        )
                })

        except Exception as exc:

            print(
                f"[NEYNAR PARSE] "
                f"{exc}"
            )

    return results


# ============================================================
# SORSA / X
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
            "search-tweets"
        )

        response = safe_post(
            url,
            headers={
                "ApiKey":
                    SORSA_API_KEY,

                "Content-Type":
                    "application/json"
            },
            json={
                "query":
                    query,

                "order":
                    "latest"
            }
        )

        if not response:
            continue

        try:

            payload = response.json()

            tweets = payload.get(
                "tweets",
                []
            )

            if isinstance(
                tweets,
                dict
            ):

                tweets = tweets.get(
                    "data",
                    []
                )

            if not isinstance(
                tweets,
                list
            ):

                tweets = []

            for tweet in tweets[:15]:

                text = clean_text(
                    tweet.get(
                        "text",
                        tweet.get(
                            "full_text",
                            ""
                        )
                    )
                )

                tweet_id = str(
                    tweet.get(
                        "id",
                        tweet.get(
                            "rest_id",
                            ""
                        )
                    )
                )

                if not text:
                    continue

                if not tweet_id:
                    tweet_id = make_id(
                        "sorsa",
                        text
                    )

                username = (
                    tweet.get(
                        "username",
                        tweet.get(
                            "screen_name",
                            ""
                        )
                    )
                )

                tweet_url = (
                    tweet.get(
                        "url",
                        ""
                    )
                )

                if not tweet_url:

                    if username:

                        tweet_url = (
                            "https://x.com/"
                            f"{username}/status/"
                            f"{tweet_id}"
                        )

                    else:

                        tweet_url = (
                            "https://x.com/"
                        )

                results.append({
                    "source":
                        "Sorsa / X",

                    "type":
                        "social",

                    "id":
                        make_id(
                            "sorsa",
                            tweet_id
                        ),

                    "title":
                        f"X discussion: "
                        f"{query}",

                    "text":
                        text[:4000],

                    "url":
                        tweet_url,

                    "likes":
                        tweet.get(
                            "likes",
                            tweet.get(
                                "favorite_count",
                                0
                            )
                        ),

                    "reposts":
                        tweet.get(
                            "retweets",
                            tweet.get(
                                "retweet_count",
                                0
                            )
                        ),

                    "replies":
                        tweet.get(
                            "replies",
                            tweet.get(
                                "reply_count",
                                0
                            )
                        )
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
        ] = (
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

                if not name:
                    continue

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
                        (
                            "GitHub activity: "
                            f"{name}"
                        ),

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
# LOCAL SIGNAL SCORE
# ============================================================

def score_signal(item):

    text = (
        f"{item.get('title', '')} "
        f"{item.get('text', '')}"
    ).lower()

    score = 0.0

    topics = matched_topics(
        text
    )

    # --------------------------------------------------------
    # NICHE
    # --------------------------------------------------------

    for topic in topics:

        if topic in TIER_1_TOPICS:
            score += 2.2

        elif topic in TIER_2_TOPICS:
            score += 1.25

        elif topic in TIER_3_TOPICS:
            score += 0.5

    # --------------------------------------------------------
    # IMPORTANT EVENTS
    # --------------------------------------------------------

    event_words = [
        "launch",
        "launched",
        "mainnet",
        "integration",
        "integrated",
        "partnership",
        "funding",
        "adoption",
        "payment",
        "payments",
        "stablecoin",
        "institutional",
        "tokenization",
        "tokenisation",
        "settlement",
        "volume",
        "acquisition",
        "upgrade",
        "release",
        "approved",
        "approval",
        "etf",
    ]

    for word in event_words:

        if word in text:
            score += 0.75

    # --------------------------------------------------------
    # BREAKING / RISK
    # --------------------------------------------------------

    urgent_words = [
        "hack",
        "hacked",
        "exploit",
        "exploited",
        "attack",
        "breach",
        "stolen",
        "halt",
        "shutdown",
        "lawsuit",
        "ban",
        "banned",
        "outage",
        "paused",
        "freeze",
        "frozen",
    ]

    for word in urgent_words:

        if word in text:
            score += 2.5

    # --------------------------------------------------------
    # MARKET MOVEMENT
    # --------------------------------------------------------

    for field in [
        "change_1h",
        "change_24h",
        "change_7d"
    ]:

        change = item.get(
            field
        )

        if isinstance(
            change,
            (int, float)
        ):

            if abs(change) >= 15:
                score += 3.5

            elif abs(change) >= 10:
                score += 2.5

            elif abs(change) >= 5:
                score += 1.25

    # --------------------------------------------------------
    # REDDIT
    # --------------------------------------------------------

    comments = item.get(
        "comments",
        0
    )

    if isinstance(
        comments,
        (int, float)
    ):

        if comments >= 250:
            score += 2.5

        elif comments >= 100:
            score += 1.5

        elif comments >= 30:
            score += 0.75

    # --------------------------------------------------------
    # X
    # --------------------------------------------------------

    likes = item.get(
        "likes",
        0
    )

    reposts = item.get(
        "reposts",
        0
    )

    if isinstance(
        likes,
        (int, float)
    ):

        if likes >= 1000:
            score += 2

        elif likes >= 100:
            score += 1

    if isinstance(
        reposts,
        (int, float)
    ):

        if reposts >= 250:
            score += 2

        elif reposts >= 50:
            score += 1

    # --------------------------------------------------------
    # GITHUB
    # --------------------------------------------------------

    stars = item.get(
        "stars",
        0
    )

    if isinstance(
        stars,
        (int, float)
    ):

        if stars >= 1000:
            score += 2

        elif stars >= 100:
            score += 1

    return round(
        min(score, 20),
        2
    )


# ============================================================
# NARRATIVE CLUSTERING
# ============================================================

def build_narrative_clusters(
    items
):

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
            ].append(
                item
            )

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

    for _, cluster in clusters.items():

        item_count = len(
            cluster["items"]
        )

        source_count = len(
            cluster["sources"]
        )

        confirmation = min(
            source_count * 1.75,
            7
        )

        volume = min(
            item_count * 0.75,
            5
        )

        score = round(
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
                sorted(
                    cluster["sources"]
                ),

            "score":
                score
        })

    output.sort(
        key=lambda x:
            x["score"],
        reverse=True
    )

    return output


# ============================================================
# SOURCE QUALITY
# ============================================================

def source_class(source):

    source = (
        source or ""
    ).lower()

    if "coinmarketcap" in source:
        return "market"

    if "coingecko" in source:
        return "market"

    if "coindesk" in source:
        return "news"

    if "cointelegraph" in source:
        return "news"

    if "github" in source:
        return "builder"

    if "reddit" in source:
        return "community"

    if "farcaster" in source:
        return "social"

    if "sorsa" in source:
        return "social"

    if "lunarcrush" in source:
        return "social"

    return "unknown"


def source_diversity(items):

    classes = set()

    for item in items:

        classes.add(
            source_class(
                item.get(
                    "source",
                    ""
                )
            )
        )

    return len(
        classes
    )


# ============================================================
# AI EDITORIAL ENGINE
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

    compact_items = []

    for index, item in enumerate(
        items[:35],
        start=1
    ):

        compact_items.append({
            "source_id":
                index,

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
                    "signal_score",
                    0
                ),

            "topics":
                item.get(
                    "matched_topics",
                    []
                ),

            "market_data":
                {
                    "symbol":
                        item.get(
                            "symbol"
                        ),

                    "change_1h":
                        item.get(
                            "change_1h"
                        ),

                    "change_24h":
                        item.get(
                            "change_24h"
                        ),

                    "change_7d":
                        item.get(
                            "change_7d"
                        )
                }
        })

    editorial_prompt = r"""
You are the senior crypto editorial intelligence
engine for a serious individual crypto creator.

Your job is NOT to produce lots of posts.

Your job is to discover the few developments,
narratives and observations worth talking about.

THE CREATOR'S CORE NICHE:

AI × crypto
stablecoins
payments
financial infrastructure
onchain finance
RWA
tokenization
wallet infrastructure
agentic commerce
DeFi
Bitcoin
Ethereum
Solana
NFTs / digital ownership when strategically relevant

The creator wants to become known for explaining
where crypto is going, especially where:

AI + money
stablecoins + payments
onchain finance + real-world finance
wallets + autonomous agents
RWA + programmable finance

intersect.

==================================================
EDITORIAL STANDARD
==================================================

Think like a combination of:

crypto researcher
investigative journalist
KOL strategist
product operator
market analyst

Do not behave like a generic crypto-news bot.

The goal is:

SIGNAL → CONTEXT → INSIGHT → ANGLE → CONTENT

not:

NEWS → SUMMARY → POST

==================================================
SOURCE HIERARCHY
==================================================

Treat sources differently.

HIGHER CONFIDENCE:

CoinMarketCap
CoinGecko
GitHub
reputable news sources
official technical announcements

MEDIUM:

LunarCrush
Farcaster
X
Reddit

Social sources are useful for discovering:

narratives
sentiment
early signals
community reactions
questions
controversies

But social chatter alone does NOT prove:

funding
adoption
partnerships
technical capability
user numbers
volume
security incidents
institutional involvement

==================================================
CRITICAL RULE
==================================================

NEVER combine unrelated stories simply because
they contain the same keyword.

For example:

"Tether audit"
+
"ECB crypto payment adoption"
+
"random Solana GitHub repo"

does NOT automatically equal one narrative.

Instead ask:

Do these developments share a meaningful causal
or strategic relationship?

If not, separate them.

==================================================
FACT DISCIPLINE
==================================================

Separate:

VERIFIED_FACT

What the supplied sources explicitly support.

INTERPRETATION

A reasonable conclusion from the evidence.

FORECAST

What may happen next.

UNVERIFIED

Claims that should not be stated as facts.

Never invent:

numbers
dates
funding
partnerships
users
volume
quotes
technical capabilities
adoption
regulatory decisions

==================================================
NARRATIVE STAGES
==================================================

Choose:

new
emerging
accelerating
peak
cooling
stable
uncertain

Definitions:

new:
first meaningful signal.

emerging:
multiple signals beginning to align.

accelerating:
clear increase in activity or attention.

peak:
already widely discussed; harder to differentiate.

cooling:
attention/activity declining.

stable:
important but not changing rapidly.

uncertain:
interesting but evidence is weak.

==================================================
DECISION SYSTEM
==================================================

POST:

Use when there is a strong factual basis AND
a differentiated angle.

WATCH:

Use when the signal is interesting but evidence
or timing is not yet strong enough.

NO_POST:

Use when there is no meaningful creator advantage.

Do NOT create content merely because the system
found something.

==================================================
KOL OPPORTUNITY
==================================================

Score 0-10.

Consider:

1. relevance to creator niche
2. novelty
3. evidence quality
4. timing
5. discussion potential
6. differentiated angle
7. ability to explain something useful
8. longevity of the idea

A generic price move should score low unless
the move reveals something deeper.

==================================================
WRITING MODES
==================================================

Choose the mode that naturally fits:

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

Do not force a contrarian take.

Do not force controversy.

==================================================
CONTENT FORMATS
==================================================

Choose:

short_post
thread
quote_post
reply
research_note

Short post:

one strong observation.

Thread:

only when the idea requires multiple steps.

Quote post:

when reacting to a specific source or statement.

Reply:

when the insight works better as part of an
existing conversation.

Research note:

when the evidence is useful but not yet suitable
for public posting.

==================================================
WRITING STYLE
==================================================

Write like a sharp crypto-native human.

Characteristics:

specific
clear
confident without pretending certainty
curious
occasionally skeptical
observational
economically written

Avoid:

"game changer"
"revolutionary"
"the future is here"
"mass adoption is coming"
"this is huge"
"bullish"
"exciting times"
"we are still early"

unless genuinely justified.

Do not write like a corporate account.

Do not use excessive emojis.

Do not automatically add hashtags.

Do not use numbered lists unless they improve
the actual post.

Do not begin every post with:

"the future of..."
"crypto is..."
"this could be..."

Vary hooks.

==================================================
HOOK QUALITY
==================================================

A good hook may use:

an unexpected number
a contradiction
a hidden implication
a market misconception
a technical detail
a question
a tension between two facts
a strong observation

Bad:

"Stablecoins are changing finance."

Better:

"stablecoins may be getting institutional credibility
faster than they are getting everyday users."

But only use that claim if the evidence supports it.

==================================================
CONTENT MUST BE PUBLISHABLE
==================================================

The draft should sound like something the creator
could post with minimal editing.

Do not write:

"here is why this matters"

repeatedly.

Do not explain your writing process.

Do not mention that you are an AI.

==================================================
PREVIOUS NARRATIVES
==================================================

Use previous narratives only to detect:

continuation
acceleration
cooling
recurrence

Do not artificially manufacture continuity.

==================================================
OUTPUT
==================================================

Return VALID JSON ONLY.

Use exactly this structure:

{
  "decision": "POST|WATCH|NO_POST",

  "summary": "",

  "confidence": 0,

  "evidence_score": 0,

  "kol_opportunity_score": 0,

  "writing_mode": "",

  "narrative_status": "",

  "primary_narrative": "",

  "narratives": [],

  "verified_facts": [],

  "interpretations": [],

  "forecasts": [],

  "unverified_claims": [],

  "why_it_matters": [],

  "contrarian_angle": "",

  "content_opportunities": [
    {
      "title": "",
      "angle": "",
      "format": ""
    }
  ],

  "recommended_posts": [
    {
      "format": "",
      "hook": "",
      "angle": "",
      "post": ""
    }
  ],

  "sources": [
    {
      "claim": "",
      "source_ids": []
    }
  ]
}

If decision is WATCH or NO_POST,
recommended_posts should normally be [].

If evidence is weak, do not manufacture certainty.

==================================================
FINAL TEST
==================================================

Before returning POST, ask yourself:

Would a knowledgeable crypto user learn
something here?

Is there a specific observation?

Is there enough evidence?

Is the angle differentiated?

Could 10,000 generic crypto AI accounts write
the same thing?

If yes, improve it.

If you cannot improve it:

WATCH or NO_POST.
"""

    user_payload = {
        "previous_narratives":
            previous_topics[-75:],

        "narrative_clusters":
            narratives[:15],

        "signals":
            compact_items,

        "source_diversity":
            source_diversity(items),

        "instruction":
            (
                "Analyze these signals independently. "
                "Do not force unrelated signals into "
                "one story. Identify the strongest "
                "single narrative or, if appropriate, "
                "separate narrative opportunities."
            )
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
                0.55,

            "max_completion_tokens":
                5000,

            "response_format":
                {
                    "type":
                        "json_object"
                },

            "messages": [
                {
                    "role":
                        "system",

                    "content":
                        editorial_prompt
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

        payload = response.json()

        content = (
            payload
            .get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )

        if not content:
            return None

        # Strip accidental markdown fences
        content = content.strip()

        if content.startswith(
            "```"
        ):

            content = re.sub(
                r"^```(?:json)?",
                "",
                content,
                flags=re.I
            )

            content = re.sub(
                r"```$",
                "",
                content
            ).strip()

        result = json.loads(
            content
        )

        return result

    except Exception as exc:

        print(
            f"[GROQ PARSE ERROR] "
            f"{exc}"
        )

        try:

            print(
                response.text[:3000]
            )

        except Exception:
            pass

        return None


# ============================================================
# ANALYSIS SANITIZATION
# ============================================================

def normalize_analysis(
    analysis
):

    if not isinstance(
        analysis,
        dict
    ):

        return None

    decision = str(
        analysis.get(
            "decision",
            "WATCH"
        )
    ).upper()

    if decision not in (
        "POST",
        "WATCH",
        "NO_POST"
    ):

        decision = "WATCH"

    analysis[
        "decision"
    ] = decision

    # ---------------------------------------------
    # SCORES
    # ---------------------------------------------

    for field in [
        "confidence",
        "evidence_score",
        "kol_opportunity_score"
    ]:

        value = analysis.get(
            field,
            0
        )

        try:

            value = float(
                value
            )

        except Exception:

            value = 0

        if field == "confidence":

            value = max(
                0,
                min(
                    100,
                    value
                )
            )

        else:

            value = max(
                0,
                min(
                    10,
                    value
                )
            )

        analysis[
            field
        ] = round(
            value,
            2
        )

    # ---------------------------------------------
    # ARRAYS
    # ---------------------------------------------

    array_fields = [
        "narratives",
        "verified_facts",
        "interpretations",
        "forecasts",
        "unverified_claims",
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

    # ---------------------------------------------
    # SAFETY RULES
    # ---------------------------------------------

    if decision != "POST":

        analysis[
            "recommended_posts"
        ] = []

    # POST requires meaningful evidence
    if (
        decision == "POST"
        and analysis[
            "evidence_score"
        ] < 5
    ):

        analysis[
            "decision"
        ] = "WATCH"

        analysis[
            "recommended_posts"
        ] = []

    return analysis


# ============================================================
# TELEGRAM FORMATTER
# ============================================================

def safe_html(text):

    return telegram_escape(
        clean_text(text)
    )


def format_opportunity(
    opportunity
):

    if not isinstance(
        opportunity,
        dict
    ):

        return ""

    title = safe_html(
        opportunity.get(
            "title",
            ""
        )
    )

    angle = safe_html(
        opportunity.get(
            "angle",
            ""
        )
    )

    fmt = safe_html(
        opportunity.get(
            "format",
            ""
        )
    )

    if fmt:

        return (
            f"• <b>{title}</b> "
            f"[{fmt}]\n"
            f"  → {angle}"
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

    decision = analysis.get(
        "decision",
        "WATCH"
    )

    if decision == "POST":

        header = (
            "🚨 <b>POST OPPORTUNITY</b>"
        )

    elif decision == "WATCH":

        header = (
            "🟡 <b>WATCH SIGNAL</b>"
        )

    else:

        header = (
            "⚪ <b>NO POST</b>"
        )

    lines = [
        "🧠 <b>WEB3STATION INTELLIGENCE</b>",
        "",
        header,
        ""
    ]

    summary = analysis.get(
        "summary",
        ""
    )

    if summary:

        lines.append(
            f"<b>{safe_html(summary)}</b>"
        )

    lines.extend([
        "",
        (
            "🎯 confidence: "
            f"<b>{analysis.get('confidence', 0)}/100</b>"
        ),
        (
            "🔎 evidence: "
            f"<b>{analysis.get('evidence_score', 0)}/10</b>"
        ),
        (
            "💡 KOL opportunity: "
            f"<b>{analysis.get('kol_opportunity_score', 0)}/10</b>"
        ),
        (
            "✍️ mode: "
            f"<b>{safe_html(analysis.get('writing_mode', 'n/a'))}</b>"
        ),
        (
            "📈 narrative: "
            f"<b>{safe_html(analysis.get('narrative_status', 'uncertain'))}</b>"
        )
    ])

    primary = analysis.get(
        "primary_narrative",
        ""
    )

    if primary:

        lines.extend([
            "",
            "<b>primary narrative</b>",
            f"• {safe_html(primary)}"
        ])

    narratives = analysis.get(
        "narratives",
        []
    )

    if narratives:

        lines.extend([
            "",
            "<b>narratives</b>"
        ])

        for item in narratives[:5]:

            lines.append(
                f"• {safe_html(item)}"
            )

    facts = analysis.get(
        "verified_facts",
        []
    )

    if facts:

        lines.extend([
            "",
            "<b>what we know</b>"
        ])

        for fact in facts[:5]:

            lines.append(
                f"✓ {safe_html(fact)}"
            )

    interpretations = analysis.get(
        "interpretations",
        []
    )

    if interpretations:

        lines.extend([
            "",
            "<b>what we're inferring</b>"
        ])

        for item in interpretations[:4]:

            lines.append(
                f"→ {safe_html(item)}"
            )

    forecasts = analysis.get(
        "forecasts",
        []
    )

    if forecasts:

        lines.extend([
            "",
            "<b>what could happen next</b>"
        ])

        for item in forecasts[:3]:

            lines.append(
                f"↗ {safe_html(item)}"
            )

    unknowns = analysis.get(
        "unverified_claims",
        []
    )

    if unknowns:

        lines.extend([
            "",
            "<b>⚠ what we don't know</b>"
        ])

        for item in unknowns[:4]:

            lines.append(
                f"⚠ {safe_html(item)}"
            )

    why = analysis.get(
        "why_it_matters",
        []
    )

    if why:

        lines.extend([
            "",
            "<b>why it matters</b>"
        ])

        for item in why[:4]:

            lines.append(
                f"• {safe_html(item)}"
            )

    contrarian = analysis.get(
        "contrarian_angle",
        ""
    )

    if contrarian:

        lines.extend([
            "",
            "<b>possible edge</b>",
            f"↳ {safe_html(contrarian)}"
        ])

    opportunities = analysis.get(
        "content_opportunities",
        []
    )

    if opportunities:

        lines.extend([
            "",
            "━━━━━━━━━━━━━━━━━━",
            "<b>CONTENT OPPORTUNITIES</b>"
        ])

        for opportunity in opportunities[:4]:

            formatted = format_opportunity(
                opportunity
            )

            if formatted:
                lines.append(
                    formatted
                )

    posts = analysis.get(
        "recommended_posts",
        []
    )

    if posts:

        lines.extend([
            "",
            "━━━━━━━━━━━━━━━━━━",
            "<b>DRAFT CONTENT</b>"
        ])

        for index, post in enumerate(
            posts[:3],
            start=1
        ):

            if not isinstance(
                post,
                dict
            ):
                continue

            fmt = safe_html(
                post.get(
                    "format",
                    ""
                )
            )

            hook = safe_html(
                post.get(
                    "hook",
                    ""
                )
            )

            angle = safe_html(
                post.get(
                    "angle",
                    ""
                )
            )

            body = telegram_escape(
                str(
                    post.get(
                        "post",
                        ""
                    )
                )
            )

            lines.extend([
                "",
                f"<b>{index}. {fmt}</b>"
            ])

            if hook:

                lines.append(
                    f"hook: {hook}"
                )

            if angle:

                lines.append(
                    f"angle: {angle}"
                )

            if body:

                lines.extend([
                    "",
                    body
                ])

    sources = analysis.get(
        "sources",
        []
    )

    if sources:

        lines.extend([
            "",
            "━━━━━━━━━━━━━━━━━━",
            "<b>EVIDENCE MAP</b>"
        ])

        for source in sources[:8]:

            if not isinstance(
                source,
                dict
            ):
                continue

            claim = safe_html(
                source.get(
                    "claim",
                    ""
                )
            )

            source_ids = source.get(
                "source_ids",
                []
            )

            ids = ", ".join(
                str(x)
                for x in source_ids
            )

            if claim:

                if ids:

                    lines.append(
                        f"• {claim} "
                        f"<i>[signals {ids}]</i>"
                    )

                else:

                    lines.append(
                        f"• {claim}"
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

    used_urls = set()

    source_lines = []

    for item in top_items:

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

        if not url or url in used_urls:
            continue

        used_urls.add(
            url
        )

        safe_url = (
            str(url)
            .replace(
                "&",
                "&amp;"
            )
            .replace(
                '"',
                "&quot;"
            )
            .replace(
                "<",
                "&lt;"
            )
            .replace(
                ">",
                "&gt;"
            )
        )

        source_lines.append(
            f'• <a href="{safe_url}">'
            f'{telegram_escape(title[:100])}'
            f'</a>'
        )

        if len(source_lines) >= 7:
            break

    if source_lines:

        lines.extend([
            "",
            "<b>SOURCE LINKS</b>"
        ])

        lines.extend(
            source_lines
        )

    message = "\n".join(
        lines
    )

    return message


# ============================================================
# NO SIGNAL MESSAGE
# ============================================================

def format_no_signal(
    source_count,
    candidate_count
):

    return (
        "🛰 <b>WEB3STATION SCAN</b>\n\n"
        "No sufficiently strong narrative "
        "survived the editorial filter.\n\n"
        f"sources scanned: {source_count}\n"
        f"new signals: {candidate_count}\n\n"
        "nothing worth forcing into a post yet."
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=========================================="
    )

    print(
        f"WEB3STATION INTELLIGENCE v{VERSION}"
    )

    print(
        f"Started: {now()}"
    )

    print(
        "=========================================="
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

    if not isinstance(
        topic_history,
        list
    ):

        topic_history = []

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
    # DEDUPLICATION + SCORING
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

        if item[
            "matched_topics"
        ]:

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
        f"NEW RELEVANT SIGNALS: "
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
        "\nTOP NARRATIVES:"
    )

    for cluster in narrative_clusters[:12]:

        print(
            f"  {cluster['topic']} | "
            f"signals={cluster['item_count']} | "
            f"sources={cluster['source_count']} | "
            f"score={cluster['score']}"
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
        strong_candidates[:35]
    )

    print(
        f"STRONG SIGNALS: "
        f"{len(strong_candidates)}"
    )

    # ========================================================
    # NO SIGNAL
    # ========================================================

    if not strong_candidates:

        print(
            "\nNo strong signals."
        )

        for item in candidates[:100]:

            seen.add(
                item["id"]
            )

        save_json(
            SEEN_FILE,
            list(seen)[-5000:]
        )

        telegram(
            format_no_signal(
                len(collectors),
                len(candidates)
            )
        )

        return

    # ========================================================
    # AI ANALYSIS
    # ========================================================

    print(
        "\n[AI] editorial analysis..."
    )

    previous_topics = []

    for entry in topic_history:

        if not isinstance(
            entry,
            dict
        ):
            continue

        narratives = entry.get(
            "narratives",
            []
        )

        if isinstance(
            narratives,
            list
        ):

            previous_topics.extend(
                narratives
            )

    analysis = groq_analyze(
        strong_candidates,
        narrative_clusters,
        previous_topics
    )

    analysis = normalize_analysis(
        analysis
    )

    if not analysis:

        print(
            "[AI] analysis failed"
        )

        telegram(
            "⚠️ <b>WEB3STATION</b>\n\n"
            "Signals were collected, but "
            "the editorial AI layer failed "
            "during this scan.\n\n"
            "The next scheduled scan will retry."
        )

        return

    print(
        f"\nDECISION: "
        f"{analysis.get('decision')}"
    )

    print(
        f"CONFIDENCE: "
        f"{analysis.get('confidence')}"
    )

    print(
        f"EVIDENCE: "
        f"{analysis.get('evidence_score')}"
    )

    print(
        f"KOL OPPORTUNITY: "
        f"{analysis.get('kol_opportunity_score')}"
    )

    # ========================================================
    # TELEGRAM
    # ========================================================

    message = format_alert(
        analysis,
        strong_candidates
    )

    if message:

        # Telegram has a practical message limit.
        # Keep enough room for HTML.
        if len(message) > 3900:

            message = (
                message[:3900]
                + "\n\n..."
            )

        telegram(
            message
        )

    # ========================================================
    # MEMORY
    # ========================================================

    for item in candidates:

        seen.add(
            item["id"]
        )

    narrative_names = []

    for cluster in narrative_clusters[:12]:

        narrative_names.append(
            cluster["topic"]
        )

    if narrative_names:

        topic_history.append({
            "timestamp":
                now(),

            "narratives":
                narrative_names,

            "primary_narrative":
                analysis.get(
                    "primary_narrative",
                    ""
                ),

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
                    "uncertain"
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

    print(
        "\n=========================================="
    )

    print(
        "RUN COMPLETE"
    )

    print(
        "=========================================="
    )


if __name__ == "__main__":
    main()
