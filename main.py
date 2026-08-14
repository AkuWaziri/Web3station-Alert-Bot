import os
import json
import hashlib
from datetime import datetime, timezone
from html import unescape

import requests
import feedparser


# ============================================================
# CONFIG
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
).strip()

CMC_API_KEY = os.getenv("CMC_API_KEY", "").strip()
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "").strip()
CRYPTOPANIC_KEY = os.getenv("CRYPTOPANIC_KEY", "").strip()

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


SEEN_FILE = "seen_ids.json"


# ============================================================
# SETTINGS
# ============================================================

MAX_REPORTS_PER_SOURCE = 1
MAX_SOURCE_TEXT = 3500
TELEGRAM_LIMIT = 3900


# ============================================================
# TOPICS
# ============================================================

PRIORITY_TOPICS = [
    "ai",
    "ai agent",
    "ai agents",
    "agentic",
    "agentic commerce",

    "stablecoin",
    "stablecoins",

    "payment",
    "payments",
    "crypto payments",
    "onchain payments",

    "cross-border",
    "remittance",

    "rwa",
    "real world assets",
    "tokenization",
    "tokenisation",

    "wallet",
    "wallets",

    "financial infrastructure",
    "onchain finance",
    "defi",

    "bitcoin",
    "ethereum",
    "solana",
    "base",
    "arbitrum",
    "layer 2",
    "l2",

    "institutional",
    "regulation",

    "security",
    "hack",
    "exploit",
    "attack",

    "nft",
    "nfts",

    "crypto",
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
# FARCASTER / X SEARCHES
# ============================================================

SOCIAL_QUERIES = [

    "stablecoin",
    "crypto payments",
    "AI agents",
    "DeFi",
    "RWA",

]


# ============================================================
# GITHUB SEARCHES
# ============================================================

GITHUB_SEARCHES = [

    "stablecoin payments",
    "AI agents crypto",
    "RWA tokenization",
    "DeFi payments",
    "crypto wallet AI",

]


# ============================================================
# HTTP SESSION
# ============================================================

SESSION = requests.Session()

SESSION.headers.update({

    "User-Agent":
        "Web3Station/4.0 crypto intelligence bot"

})


# ============================================================
# BASIC HELPERS
# ============================================================

def now():

    return datetime.now(
        timezone.utc
    ).isoformat()


def clean_text(value):

    if not value:
        return ""

    value = unescape(
        str(value)
    )

    return " ".join(
        value
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


def load_seen():

    try:

        with open(
            SEEN_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(data, list):

            return set(data)

        return set()

    except Exception:

        return set()


def save_seen(seen):

    with open(
        SEEN_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            list(seen)[-5000:],
            file,
            indent=2,
            ensure_ascii=False
        )


def http_get(url, **kwargs):

    try:

        response = SESSION.get(
            url,
            timeout=25,
            **kwargs
        )

        print(
            f"[GET] {url} -> {response.status_code}"
        )

        if response.ok:

            return response

        print(
            f"[GET ERROR] {response.text[:500]}"
        )

    except Exception as exc:

        print(
            f"[GET EXCEPTION] {url}: {exc}"
        )

    return None


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):

    print("[TELEGRAM] Sending message...")

    if not TELEGRAM_TOKEN:

        print(
            "[TELEGRAM ERROR] TELEGRAM_TOKEN is missing"
        )

        return False

    if not TELEGRAM_CHAT_ID:

        print(
            "[TELEGRAM ERROR] TELEGRAM_CHAT_ID is missing"
        )

        return False

    url = (
        "https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/sendMessage"
    )

    payload = {

        "chat_id":
            TELEGRAM_CHAT_ID,

        "text":
            message,

        "disable_web_page_preview":
            False

    }

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=30
        )

        print(
            f"[TELEGRAM STATUS] "
            f"{response.status_code}"
        )

        print(
            f"[TELEGRAM RESPONSE] "
            f"{response.text[:1000]}"
        )

        if response.ok:

            print(
                "[TELEGRAM] SENT SUCCESSFULLY"
            )

            return True

        print(
            "[TELEGRAM] FAILED"
        )

        return False

    except Exception as exc:

        print(
            f"[TELEGRAM EXCEPTION] {exc}"
        )

        return False


# ============================================================
# RELEVANCE
# ============================================================

def is_relevant(item):

    text = (
        item.get("title", "")
        + " "
        + item.get("text", "")
    ).lower()

    return any(
        topic in text
        for topic in PRIORITY_TOPICS
    )


def relevance_score(item):

    text = (
        item.get("title", "")
        + " "
        + item.get("text", "")
    ).lower()

    score = 0

    high_value = [

        "stablecoin",
        "payments",
        "payment",
        "ai agents",
        "ai agent",
        "agentic commerce",
        "rwa",
        "tokenization",
        "tokenisation",
        "financial infrastructure",
        "onchain finance",

    ]

    for topic in PRIORITY_TOPICS:

        if topic in text:

            if topic in high_value:

                score += 3

            else:

                score += 1

    important_events = [

        "launch",
        "mainnet",
        "integration",
        "partnership",
        "funding",
        "adoption",
        "acquisition",
        "upgrade",
        "release",
        "approval",
        "regulation",
        "hack",
        "exploit",
        "attack",
        "outage",

    ]

    for word in important_events:

        if word in text:

            score += 2

    return score


# ============================================================
# COINMARKETCAP
# ============================================================

def fetch_coinmarketcap():

    results = []

    if not CMC_API_KEY:

        print(
            "[CoinMarketCap] API key not configured"
        )

        return results

    url = (
        "https://pro-api.coinmarketcap.com/"
        "v3/cryptocurrency/listings/latest"
    )

    response = http_get(

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

        return results

    try:

        data = response.json()

        for coin in data.get(
            "data",
            []
        ):

            quote = (
                coin
                .get("quote", {})
                .get("USD", {})
            )

            change = quote.get(
                "percent_change_24h"
            )

            if not isinstance(
                change,
                (int, float)
            ):

                continue

            if abs(change) < 5:

                continue

            name = coin.get(
                "name",
                ""
            )

            symbol = coin.get(
                "symbol",
                ""
            )

            text = (

                f"{name} ({symbol}) "

                f"price: "
                f"${quote.get('price', 0):,.6f}. "

                f"24h change: "
                f"{change:.2f}%. "

                f"24h volume: "
                f"${quote.get('volume_24h', 0):,.0f}. "

                f"Market cap: "
                f"${quote.get('market_cap', 0):,.0f}."

            )

            results.append({

                "source":
                    "CoinMarketCap",

                "title":
                    f"{name} market movement",

                "text":
                    text,

                "url":
                    (
                        "https://coinmarketcap.com/"
                        "currencies/"
                        + str(
                            coin.get(
                                "slug",
                                ""
                            )
                        )
                    ),

                "id":
                    make_id(
                        "cmc",
                        coin.get("id"),
                        round(change, 1)
                    )

            })

    except Exception as exc:

        print(
            f"[CoinMarketCap ERROR] {exc}"
        )

    return results


# ============================================================
# COINGECKO
# ============================================================

def fetch_coingecko():

    results = []

    url = (
        "https://api.coingecko.com/api/v3/"
        "coins/markets"
    )

    headers = {}

    if COINGECKO_API_KEY:

        headers[
            "x-cg-demo-api-key"
        ] = COINGECKO_API_KEY

    response = http_get(

        url,

        headers=headers,

        params={

            "vs_currency":
                "usd",

            "order":
                "market_cap_desc",

            "per_page":
                100,

            "page":
                1,

            "sparkline":
                "false"

        }

    )

    if not response:

        return results

    try:

        data = response.json()

        for coin in data:

            change = coin.get(
                "price_change_percentage_24h"
            )

            if not isinstance(
                change,
                (int, float)
            ):

                continue

            if abs(change) < 7:

                continue

            name = coin.get(
                "name",
                ""
            )

            symbol = coin.get(
                "symbol",
                ""
            ).upper()

            results.append({

                "source":
                    "CoinGecko",

                "title":
                    f"{name} market movement",

                "text":
                    (

                        f"{name} ({symbol}) "

                        f"price: "
                        f"${coin.get('current_price', 0):,.6f}. "

                        f"24h change: "
                        f"{change:.2f}%. "

                        f"Market cap: "
                        f"${coin.get('market_cap', 0):,.0f}. "

                        f"24h volume: "
                        f"${coin.get('total_volume', 0):,.0f}."

                    ),

                "url":
                    (
                        "https://www.coingecko.com/"
                        "en/coins/"
                        + str(
                            coin.get(
                                "id",
                                ""
                            )
                        )
                    ),

                "id":
                    make_id(
                        "coingecko",
                        coin.get("id"),
                        round(change, 1)
                    )

            })

    except Exception as exc:

        print(
            f"[CoinGecko ERROR] {exc}"
        )

    return results


# ============================================================
# CRYPTOPANIC
# ============================================================

def fetch_cryptopanic():

    results = []

    if not CRYPTOPANIC_KEY:

        print(
            "[CryptoPanic] API key not configured"
        )

        return results

    url = (
        "https://cryptopanic.com/api/developer/v2/"
        "posts/"
    )

    response = http_get(

        url,

        params={

            "auth_token":
                CRYPTOPANIC_KEY,

            "public":
                "true",

            "kind":
                "news",

            "filter":
                "rising",

        }

    )

    if not response:

        return results

    try:

        data = response.json()

        posts = data.get(
            "results",
            []
        )

        for post in posts[:20]:

            title = clean_text(
                post.get(
                    "title",
                    ""
                )
            )

            url_value = (
                post.get("url")
                or post.get("source", {}).get(
                    "url",
                    ""
                )
            )

            if not title:

                continue

            text = clean_text(
                post.get(
                    "title",
                    ""
                )
            )

            item = {

                "source":
                    "CryptoPanic",

                "title":
                    title,

                "text":
                    text,

                "url":
                    url_value,

                "id":
                    make_id(
                        "cryptopanic",
                        post.get("id"),
                        title
                    )

            }

            if is_relevant(item):

                results.append(item)

    except Exception as exc:

        print(
            f"[CryptoPanic ERROR] {exc}"
        )

    return results


# ============================================================
# RSS NEWS
# ============================================================

def fetch_news():

    results = []

    for source, url in RSS_FEEDS:

        print(
            f"[{source}] checking RSS"
        )

        try:

            feed = feedparser.parse(
                url
            )

            for entry in feed.entries[:20]:

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

                item = {

                    "source":
                        source,

                    "title":
                        title,

                    "text":
                        (
                            f"{title}. "
                            f"{summary}"
                        )[:MAX_SOURCE_TEXT],

                    "url":
                        link,

                    "id":
                        make_id(
                            source,
                            link
                        )

                }

                if is_relevant(item):

                    results.append(item)

        except Exception as exc:

            print(
                f"[{source} ERROR] {exc}"
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

        response = http_get(

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

            data = response.json()

            posts = (
                data
                .get("data", {})
                .get("children", [])
            )

            for post in posts:

                item_data = post.get(
                    "data",
                    {}
                )

                title = clean_text(
                    item_data.get(
                        "title",
                        ""
                    )
                )

                body = clean_text(
                    item_data.get(
                        "selftext",
                        ""
                    )
                )

                if not title:

                    continue

                item = {

                    "source":
                        f"Reddit / r/{subreddit}",

                    "title":
                        title,

                    "text":
                        (
                            f"{title}. "
                            f"{body}"
                        )[:MAX_SOURCE_TEXT],

                    "url":
                        (
                            "https://www.reddit.com"
                            + item_data.get(
                                "permalink",
                                ""
                            )
                        ),

                    "comments":
                        item_data.get(
                            "num_comments",
                            0
                        ),

                    "id":
                        make_id(
                            "reddit",
                            subreddit,
                            item_data.get(
                                "id"
                            )
                        )

                }

                if is_relevant(item):

                    results.append(item)

        except Exception as exc:

            print(
                f"[Reddit ERROR] "
                f"{subreddit}: {exc}"
            )

    return results


# ============================================================
# LUNARCRUSH
# ============================================================

def fetch_lunarcrush():

    results = []

    if not LUNARCRUSH_API_KEY:

        print(
            "[LunarCrush] API key not configured"
        )

        return results

    url = (
        "https://lunarcrush.com/"
        "api4/public/coins/list/v1"
    )

    response = http_get(

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

        return results

    try:

        data = response.json()

        for coin in data.get(
            "data",
            []
        ):

            symbol = str(
                coin.get(
                    "symbol",
                    ""
                )
            ).upper()

            if not symbol:

                continue

            text = clean_text(
                json.dumps(
                    coin,
                    ensure_ascii=False
                )
            )

            item = {

                "source":
                    "LunarCrush",

                "title":
                    f"{symbol} social activity",

                "text":
                    text[:MAX_SOURCE_TEXT],

                "url":
                    "https://lunarcrush.com/",

                "id":
                    make_id(
                        "lunarcrush",
                        symbol,
                        text[:500]
                    )

            }

            if is_relevant(item):

                results.append(item)

    except Exception as exc:

        print(
            f"[LunarCrush ERROR] {exc}"
        )

    return results


# ============================================================
# NEYNAR / FARCASTER
# ============================================================

def fetch_neynar():

    results = []

    if not NEYNAR_API_KEY:

        print(
            "[Neynar] API key not configured"
        )

        return results

    url = (
        "https://api.neynar.com/v2/"
        "farcaster/cast/search/"
    )

    for query in SOCIAL_QUERIES:

        response = http_get(

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

            data = response.json()

            casts = (
                data
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

                username = (
                    cast
                    .get("author", {})
                    .get(
                        "username",
                        ""
                    )
                )

                item = {

                    "source":
                        "Farcaster / Neynar",

                    "title":
                        (
                            "Farcaster discussion: "
                            f"{query}"
                        ),

                    "text":
                        text[:MAX_SOURCE_TEXT],

                    "url":
                        (
                            "https://warpcast.com/"
                            f"{username}/"
                            f"{cast_hash}"
                        ),

                    "id":
                        make_id(
                            "neynar",
                            cast_hash
                        )

                }

                if is_relevant(item):

                    results.append(item)

        except Exception as exc:

            print(
                f"[Neynar ERROR] {query}: {exc}"
            )

    return results


# ============================================================
# SORSA / X
# ============================================================

def fetch_sorsa():

    results = []

    if not SORSA_API_KEY:

        print(
            "[Sorsa] API key not configured"
        )

        return results

    url = (
        "https://api.sorsa.io/v3/"
        "tweets/search"
    )

    for query in SOCIAL_QUERIES:

        response = http_get(

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

            data = response.json()

            tweets = data.get(
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

                item = {

                    "source":
                        "X / Sorsa",

                    "title":
                        (
                            "X discussion: "
                            f"{query}"
                        ),

                    "text":
                        text[:MAX_SOURCE_TEXT],

                    "url":
                        (
                            "https://x.com/i/web/status/"
                            f"{tweet_id}"
                        ),

                    "id":
                        make_id(
                            "sorsa",
                            tweet_id,
                            text
                        )

                }

                if is_relevant(item):

                    results.append(item)

        except Exception as exc:

            print(
                f"[Sorsa ERROR] {query}: {exc}"
            )

    return results


# ============================================================
# GITHUB
# ============================================================

def fetch_github():

    results = []

    for query in GITHUB_SEARCHES:

        url = (
            "https://api.github.com/"
            "search/repositories"
        )

        response = http_get(

            url,

            headers={

                "Accept":
                    "application/vnd.github+json"

            },

            params={

                "q":
                    query,

                "sort":
                    "updated",

                "order":
                    "desc",

                "per_page":
                    10

            }

        )

        if not response:

            continue

        try:

            data = response.json()

            for repo in data.get(
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

                stars = repo.get(
                    "stargazers_count",
                    0
                )

                forks = repo.get(
                    "forks_count",
                    0
                )

                item = {

                    "source":
                        "GitHub",

                    "title":
                        f"GitHub: {name}",

                    "text":
                        (

                            f"{description}. "

                            f"Repository: {name}. "

                            f"Stars: {stars}. "

                            f"Forks: {forks}. "

                            f"Updated: {updated}."

                        )[:MAX_SOURCE_TEXT],

                    "url":
                        repo.get(
                            "html_url",
                            ""
                        ),

                    "id":
                        make_id(
                            "github",
                            repo.get("id"),
                            updated
                        )

                }

                if is_relevant(item):

                    results.append(item)

        except Exception as exc:

            print(
                f"[GitHub ERROR] {query}: {exc}"
            )

    return results


# ============================================================
# GROQ
# ============================================================

def groq_edit(item):

    if not GROQ_API_KEY:

        print(
            "[GROQ] API key missing"
        )

        return None

    system_prompt = """
You are the editorial AI for Web3Station,
a serious crypto intelligence and content radar.

Your job is to turn a real source signal into
a concise social-media content opportunity.

Focus on:

AI x crypto
AI agents
stablecoins
payments
financial infrastructure
RWA
tokenization
wallets
DeFi
onchain finance
Bitcoin
Ethereum
Solana
emerging crypto technology

Rules:

- Use ONLY facts contained in the supplied source.
- Do not invent facts.
- Do not invent numbers.
- Do not invent partnerships.
- Do not invent quotes.
- Do not pretend speculation is fact.
- Do not exaggerate.
- Do not use corporate PR language.
- Do not say "game changer".
- Do not say "revolutionary".
- Do not say "the future is here".
- Do not say "this is huge".
- Do not use fake certainty.
- The angle should explain why the signal is interesting.
- The draft should sound like a knowledgeable crypto creator.
- Keep the draft concise.
- Do not add hashtags unless they are genuinely useful.

Return ONLY valid JSON.

Required structure:

{
  "category": "...",
  "angle": "...",
  "draft": "..."
}

category:
short label such as "stablecoins", "ai x crypto",
"payments", "defi", "rwa", "developer activity",
"market", "security", "regulation", etc.

angle:
one or two concise sentences.

draft:
the actual social-media post.
"""


    user_prompt = f"""
SOURCE:
{item.get('source', '')}

TITLE:
{item.get('title', '')}

SOURCE INFORMATION:
{item.get('text', '')[:MAX_SOURCE_TEXT]}

SOURCE URL:
{item.get('url', '')}
"""


    url = (
        "https://api.groq.com/openai/v1/"
        "chat/completions"
    )

    payload = {

        "model":
            GROQ_MODEL,

        "temperature":
            0.6,

        "max_completion_tokens":
            600,

        "response_format": {
            "type": "json_object"
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
                    user_prompt
            }

        ]

    }

    try:

        response = SESSION.post(

            url,

            headers={

                "Authorization":
                    f"Bearer {GROQ_API_KEY}",

                "Content-Type":
                    "application/json"

            },

            json=payload,

            timeout=60

        )

        print(
            f"[GROQ STATUS] "
            f"{response.status_code}"
        )

        if not response.ok:

            print(
                f"[GROQ ERROR] "
                f"{response.text[:1000]}"
            )

            return None

        data = response.json()

        content = (
            data
            .get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )

        if not content:

            print(
                "[GROQ ERROR] Empty response"
            )

            return None

        result = json.loads(
            content
        )

        category = clean_text(
            result.get(
                "category",
                ""
            )
        )

        angle = clean_text(
            result.get(
                "angle",
                ""
            )
        )

        draft = clean_text(
            result.get(
                "draft",
                ""
            )
        )

        if not category or not angle or not draft:

            print(
                "[GROQ ERROR] "
                "Incomplete editorial response"
            )

            return None

        return {

            "category":
                category,

            "angle":
                angle,

            "draft":
                draft

        }

    except json.JSONDecodeError as exc:

        print(
            f"[GROQ JSON ERROR] {exc}"
        )

        return None

    except Exception as exc:

        print(
            f"[GROQ EXCEPTION] {exc}"
        )

        return None


# ============================================================
# FALLBACK EDITORIAL
# ============================================================

def fallback_editorial(item):

    title = clean_text(
        item.get(
            "title",
            ""
        )
    )

    text = clean_text(
        item.get(
            "text",
            ""
        )
    )

    category = "crypto"

    lower = (
        title + " " + text
    ).lower()

    if "stablecoin" in lower:

        category = "stablecoins"

    elif (
        "payment" in lower
        or "payments" in lower
    ):

        category = "payments"

    elif (
        "ai agent" in lower
        or "ai agents" in lower
        or "agentic" in lower
    ):

        category = "ai x crypto"

    elif (
        "defi" in lower
    ):

        category = "defi"

    elif (
        "rwa" in lower
        or "tokenization" in lower
        or "tokenisation" in lower
    ):

        category = "rwa"

    elif (
        "hack" in lower
        or "exploit" in lower
        or "security" in lower
    ):

        category = "security"

    elif (
        "regulation" in lower
    ):

        category = "regulation"

    elif (
        item.get("source")
        == "GitHub"
    ):

        category = "developer activity"

    angle = (
        "This signal is worth watching because "
        "it could reveal a meaningful development "
        "in the crypto ecosystem."
    )

    draft = (
        f"{title}\n\n"
        f"{text[:1200]}"
    )

    return {

        "category":
            category,

        "angle":
            angle,

        "draft":
            draft

    }


# ============================================================
# FORMAT TELEGRAM MESSAGE
# ============================================================

def format_message(
    item,
    editorial
):

    return (
        "🧠 WEB3STATION\n\n"

        "SOURCE\n"
        f"{item.get('source', 'Unknown')}\n\n"

        "CATEGORY\n"
        f"{editorial.get('category', '')}\n\n"

        "ANGLE\n"
        f"{editorial.get('angle', '')}\n\n"

        "DRAFT\n"
        f"{editorial.get('draft', '')}\n\n"

        "SOURCE\n"
        f"{item.get('url', '')}"
    )


# ============================================================
# COLLECT ALL SOURCES
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
            "CryptoPanic",
            fetch_cryptopanic
        ),

        (
            "News",
            fetch_news
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

    for name, function in collectors:

        print(
            "\n======================================"
        )

        print(
            f"COLLECTING: {name}"
        )

        try:

            items = function()

            print(
                f"{name}: {len(items)} signals"
            )

            all_items.extend(
                items
            )

        except Exception as exc:

            print(
                f"{name} FAILED: {exc}"
            )

    return all_items


# ============================================================
# SELECT ONE NEW SIGNAL PER SOURCE
# ============================================================

def select_reports(
    all_items,
    seen
):

    unique = {}

    for item in all_items:

        item_id = item.get(
            "id"
        )

        if not item_id:

            continue

        if item_id in seen:

            continue

        if item_id not in unique:

            unique[item_id] = item

    candidates = list(
        unique.values()
    )

    candidates.sort(

        key=lambda item:
            relevance_score(item),

        reverse=True

    )

    selected = []

    source_count = {}

    for item in candidates:

        source = item.get(
            "source",
            "Unknown"
        )

        if source_count.get(
            source,
            0
        ) >= MAX_REPORTS_PER_SOURCE:

            continue

        selected.append(
            item
        )

        source_count[source] = (
            source_count.get(
                source,
                0
            ) + 1
        )

    return selected


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n======================================"
    )

    print(
        "WEB3STATION REAL CRYPTO ALERT BOT"
    )

    print(
        "======================================"
    )

    print(
        f"UTC: {now()}"
    )

    print(
        f"Groq model: {GROQ_MODEL}"
    )

    # --------------------------------------------------------
    # VERIFY TELEGRAM CONFIGURATION
    # --------------------------------------------------------

    if not TELEGRAM_TOKEN:

        raise RuntimeError(
            "TELEGRAM_TOKEN is missing"
        )

    if not TELEGRAM_CHAT_ID:

        raise RuntimeError(
            "TELEGRAM_CHAT_ID is missing"
        )

    # --------------------------------------------------------
    # LOAD SEEN STATE
    # --------------------------------------------------------

    seen = load_seen()

    print(
        f"Previously seen signals: {len(seen)}"
    )

    # --------------------------------------------------------
    # COLLECT
    # --------------------------------------------------------

    all_items = collect_all()

    print(
        "\n======================================"
    )

    print(
        f"TOTAL REAL SIGNALS: {len(all_items)}"
    )

    print(
        "======================================"
    )

    # --------------------------------------------------------
    # SELECT
    # --------------------------------------------------------

    selected = select_reports(
        all_items,
        seen
    )

    print(
        f"NEW SOURCE REPORTS: {len(selected)}"
    )

    # --------------------------------------------------------
    # NOTHING NEW
    # --------------------------------------------------------

    if not selected:

        print(
            "No new qualifying signals."
        )

        return

    # --------------------------------------------------------
    # PROCESS EACH SOURCE
    # --------------------------------------------------------

    sent_count = 0
    failed_count = 0

    for item in selected:

        print(
            "\n--------------------------------------"
        )

        print(
            f"SOURCE: {item.get('source')}"
        )

        print(
            f"TITLE: {item.get('title')}"
        )

        print(
            f"URL: {item.get('url')}"
        )

        # ----------------------------------------------------
        # GROQ
        # ----------------------------------------------------

        editorial = groq_edit(
            item
        )

        if editorial:

            print(
                "[EDITOR] Groq editorial generated"
            )

        else:

            print(
                "[EDITOR] Groq unavailable"
            )

            print(
                "[EDITOR] Using real-source fallback"
            )

            editorial = fallback_editorial(
                item
            )

        # ----------------------------------------------------
        # TELEGRAM
        # ----------------------------------------------------

        message = format_message(
            item,
            editorial
        )

        if len(message) > TELEGRAM_LIMIT:

            message = (
                message[:TELEGRAM_LIMIT]
                + "\n\n[truncated]"
            )

        sent = send_telegram(
            message
        )

        # ----------------------------------------------------
        # ONLY MARK SEEN AFTER TELEGRAM SUCCESS
        # ----------------------------------------------------

        if sent:

            seen.add(
                item["id"]
            )

            sent_count += 1

            print(
                "[SUCCESS] "
                "Signal marked as seen."
            )

        else:

            failed_count += 1

            print(
                "[FAILED] "
                "Signal NOT marked as seen."
            )

    # --------------------------------------------------------
    # SAVE STATE
    # --------------------------------------------------------

    save_seen(
        seen
    )

    # --------------------------------------------------------
    # FINAL STATUS
    # --------------------------------------------------------

    print(
        "\n======================================"
    )

    print(
        "WEB3STATION RUN COMPLETE"
    )

    print(
        "======================================"
    )

    print(
        f"Signals collected: {len(all_items)}"
    )

    print(
        f"Reports selected: {len(selected)}"
    )

    print(
        f"Telegram sent: {sent_count}"
    )

    print(
        f"Telegram failed: {failed_count}"
    )

    print(
        "======================================"
    )

    # If Telegram failed for everything,
    # make GitHub Actions visibly fail.
    if sent_count == 0 and selected:

        raise RuntimeError(
            "No selected reports were delivered to Telegram."
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
