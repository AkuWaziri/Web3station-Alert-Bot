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


def get_float_env(name, default):
    value = os.getenv(name)

    if not value or not value.strip():
        return default

    try:
        return float(value)
    except ValueError:
        return default


def get_int_env(name, default):
    value = os.getenv(name)

    if not value or not value.strip():
        return default

    try:
        return int(value)
    except ValueError:
        return default


MIN_SIGNAL_SCORE = get_float_env(
    "MIN_SIGNAL_SCORE",
    6
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
# BRAND / NICHE PRIORITY
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
    "wallet",
    "wallets",
    "usdc",
    "usdt",
    "remittance",
    "cross-border payments",
]

TIER_2_TOPICS = [
    "defi",
    "ethereum",
    "bitcoin",
    "solana",
    "base",
    "arbitrum",
    "layer 2",
    "l2",
    "account abstraction",
    "smart wallet",
    "security",
    "institutional",
    "regulation",
    "mainnet",
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
# SESSION
# ============================================================

SESSION = requests.Session()

SESSION.headers.update({
    "User-Agent": "Web3Station/2.0"
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
            f"[POST HTTP {response.status_code}] "
            f"{url}"
        )

        print(
            response.text[:500]
        )

    except Exception as exc:

        print(
            f"[POST ERROR] {url}: {exc}"
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


def make_id(*parts):

    raw = "|".join(
        str(part)
        for part in parts
        if part is not None
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


def matched_topics(text):

    text = text.lower()

    return [
        topic
        for topic in ALL_TOPICS
        if topic.lower() in text
    ]


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

            if (
                symbol not in WATCHLIST
                and len(results) >= 25
            ):
                continue

            quote = (
                coin
                .get("quote", {})
                .get("USD", {})
            )

            results.append({
                "source": "CoinMarketCap",
                "type": "market",
                "id": f"cmc:{symbol}",
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
                    f"https://coinmarketcap.com/"
                    f"currencies/"
                    f"{coin.get('slug', '')}/",
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
                    f"https://www.coingecko.com/"
                    f"en/coins/{coin_id}",
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
                        f"{title} {summary}"[
                            :3000
                        ],
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
                "limit":
                    15,
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
                        f"{title} {body}"[
                            :3000
                        ],
                    "url":
                        f"https://www.reddit.com"
                        f"{permalink}",
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
                f"[REDDIT PARSE] {exc}"
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
                f"Bearer "
                f"{LUNARCRUSH_API_KEY}"
        },
        params={
            "limit":
                25
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
# NEYNAR
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
                            cast_hash
                        ),
                    "title":
                        f"Farcaster: {query}",
                    "text":
                        text[:3000],
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
                        text[:3000],
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
                        f"GitHub activity: "
                        f"{name}",
                    "text":
                        (
                            f"{description} "
                            f"Repository: {name}. "
                            f"Stars: "
                            f"{repo.get('stargazers_count', 0)}. "
                            f"Forks: "
                            f"{repo.get('forks_count', 0)}. "
                            f"Updated: {updated}."
                        ),
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
    # DEVELOPMENT SIGNAL
    # --------------------------------------------------------

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
        "acquisition",
        "upgrade",
        "release",
        "volume",
        "settlement"
    ]

    for word in high_value:

        if word in text:
            score += 1

    # --------------------------------------------------------
    # BREAKING / RISK
    # --------------------------------------------------------

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
        "outage"
    ]

    for word in urgent:

        if word in text:
            score += 2.5

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

        if abs(change) >= 10:
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

        if comments >= 100:
            score += 2

        elif comments >= 30:
            score += 1

    return round(
        min(score, 20),
        2
    )


# ============================================================
# SOURCE DIVERSITY
# ============================================================

def calculate_source_diversity(
    items
):

    sources = set(
        item.get(
            "source",
            ""
        )
        for item in items
    )

    return len(sources)


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
            ].append(item)

            clusters[key][
                "sources"
            ].add(
                item.get(
                    "source"
                )
            )

            clusters[key][
                "score"
            ] += item.get(
                "signal_score",
                0
            )

    output = []

    for topic, cluster in clusters.items():

        source_count = len(
            cluster["sources"]
        )

        item_count = len(
            cluster["items"]
        )

        # Multi-source confirmation
        confirmation = min(
            source_count * 2,
            8
        )

        # More independent signals
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
        key=lambda x: x["score"],
        reverse=True
    )

    return output


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

    compact_items = []

    for index, item in enumerate(
        items[:20],
        start=1
    ):

        compact_items.append({
            "id":
                index,
            "source":
                item.get("source"),
            "type":
                item.get("type"),
            "title":
                item.get("title"),
            "text":
                item.get("text", "")[:1800],
            "url":
                item.get("url"),
            "score":
                item.get("signal_score"),
            "topics":
                item.get(
                    "matched_topics",
                    []
                )
        })

    system_prompt = """
You are the senior editorial intelligence
engine for a crypto creator.

The creator is building a reputation around:

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
NFTs and crypto culture

The objective is NOT to produce maximum content.

The objective is to identify the few things
worth talking about.

==================================================
EDITORIAL PRINCIPLES
==================================================

1. FACTS FIRST

Never present an inference as a fact.

Separate:

VERIFIED FACT
what the sources explicitly support.

INTERPRETATION
what the evidence reasonably suggests.

FORECAST
what could happen next.

UNVERIFIED
claims that should not be published as fact.

2. SOURCE DISCIPLINE

Multiple independent sources are stronger than
one source.

Do not treat:
- social chatter
- AI-generated summaries
- one anonymous account
- one Reddit post

as proof of a major claim.

If a numerical claim is important, identify
the source supporting it.

3. DO NOT INVENT

Never invent:
- numbers
- partnerships
- users
- volumes
- dates
- outages
- funding
- quotes
- adoption
- technical capabilities

4. DO NOT FORCE A STORY

Sometimes the correct answer is:

NO POST.

If evidence is weak, say:

"interesting signal, insufficient evidence."

5. NARRATIVE DETECTION

Look for changes across multiple sources.

A strong narrative may have:

market movement
+
social discussion
+
news
+
builder activity
+
community activity

6. KOL OPPORTUNITY

A story is valuable when it has:

relevance
+
novelty
+
evidence
+
discussion
+
timing
+
a clear angle

7. WRITING STYLE

Never sound like corporate PR.

Avoid generic phrases:

"game changer"
"revolutionary"
"the future is here"
"this is huge"
"mass adoption is coming"
"bullish"
"exciting times ahead"

unless they are specifically necessary
and supported.

The creator should sound:

crypto-native
observant
sharp
curious
analytical
human
occasionally skeptical

Use short sentences where appropriate.

Do not over-explain.

Do not use excessive emojis.

Do not automatically add hashtags.

==================================================
WRITING MODES
==================================================

Choose ONE based on the story.

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

==================================================
CONTENT FORMATS
==================================================

Possible formats:

short_post
thread
quote_post
reply
research_note

Do not generate a thread unless the topic
benefits from multiple connected points.

==================================================
QUALITY CONTROL
==================================================

Before recommending a post ask:

Would a knowledgeable crypto user learn
something from this?

Is there a specific observation?

Is the evidence strong enough?

Is the angle differentiated?

Could this post be written by 10,000 other
crypto AI accounts?

If yes, improve it.

==================================================
OUTPUT
==================================================

Return valid JSON only.

Use this structure:

{
  "decision": "POST|WATCH|NO_POST",

  "summary": "...",

  "confidence": 0,

  "evidence_score": 0,

  "kol_opportunity_score": 0,

  "writing_mode": "...",

  "narratives": [],

  "narrative_status": "new|emerging|accelerating|cooling|stable",

  "verified_facts": [],

  "interpretations": [],

  "forecasts": [],

  "unverified_claims": [],

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
      "post": "..."
    }
  ],

  "sources": [
    {
      "claim": "...",
      "source_ids": []
    }
  ]
}

IMPORTANT:

If evidence is weak:

decision = "WATCH" or "NO_POST"

and recommended_posts should be empty.

Do not manufacture content simply because
the model was asked to create content.
"""


    user_prompt = {
        "previous_narratives":
            previous_topics[-50:],

        "narrative_clusters":
            narratives[:12],

        "signals":
            compact_items,

        "task":
            """
Analyze the supplied signals.

Determine whether there is a meaningful
crypto narrative.

Cross-check claims conceptually against
the available source diversity.

Do not assume that a claim appearing in
one source is verified.

Identify:

1. what is known
2. what is inferred
3. what remains uncertain
4. whether the narrative is accelerating
5. whether the creator should post
6. the strongest differentiated angle
7. the most appropriate writing mode
8. the best content format

Remember:

The creator is building a long-term reputation,
not chasing every trend.
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
                0.55,

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
            data
            ["choices"]
            [0]
            ["message"]
            ["content"]
        )

        return json.loads(
            content
        )

    except Exception as exc:

        print(
            f"[GROQ PARSE] {exc}"
        )

        return None


# ============================================================
# TELEGRAM EDITORIAL FORMATTER
# ============================================================

def format_opportunity(
    opportunity
):

    if isinstance(
        opportunity,
        dict
    ):

        title = opportunity.get(
            "title",
            ""
        )

        angle = opportunity.get(
            "angle",
            ""
        )

        return (
            f"• <b>{title}</b>\n"
            f"  → {angle}"
        )

    return (
        f"• {str(opportunity)}"
    )


def format_alert(
    analysis,
    items,
    narratives
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

    summary = analysis.get(
        "summary",
        ""
    )

    if summary:

        lines.append(
            f"<b>{summary}</b>"
        )

    lines.append("")

    # --------------------------------------------------------
    # SCORES
    # --------------------------------------------------------

    lines.append(
        f"🎯 confidence: "
        f"<b>{analysis.get('confidence', 0)}/100</b>"
    )

    lines.append(
        f"🔎 evidence: "
        f"<b>{analysis.get('evidence_score', 0)}/10</b>"
    )

    lines.append(
        f"💡 KOL opportunity: "
        f"<b>{analysis.get('kol_opportunity_score', 0)}/10</b>"
    )

    lines.append(
        f"✍️ mode: "
        f"<b>{analysis.get('writing_mode', 'n/a')}</b>"
    )

    lines.append(
        f"📈 narrative: "
        f"<b>{analysis.get('narrative_status', 'stable')}</b>"
    )

    # --------------------------------------------------------
    # NARRATIVES
    # --------------------------------------------------------

    story_narratives = analysis.get(
        "narratives",
        []
    )

    if story_narratives:

        lines.append("")

        lines.append(
            "<b>narratives</b>"
        )

        for narrative in story_narratives[:5]:

            lines.append(
                f"• {narrative}"
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
            "<b>what we know</b>"
        )

        for fact in facts[:5]:

            lines.append(
                f"✓ {fact}"
            )

    # --------------------------------------------------------
    # INTERPRETATION
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
                f"→ {point}"
            )

    # --------------------------------------------------------
    # FORECAST
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
                f"↗ {point}"
            )

    # --------------------------------------------------------
    # UNCERTAINTY
    # --------------------------------------------------------

    uncertain = analysis.get(
        "unverified_claims",
        []
    )

    if uncertain:

        lines.append("")

        lines.append(
            "<b>⚠ what we don't know</b>"
        )

        for point in uncertain[:4]:

            lines.append(
                f"⚠ {point}"
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
                f"• {point}"
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
    # POSTS
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

            fmt = post.get(
                "format",
                ""
            )

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
    # SOURCES
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

        for source in sources[:6]:

            claim = source.get(
                "claim",
                ""
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
    # RAW SOURCE LINKS
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

            lines.append(
                f'• <a href="{url}">'
                f'{title[:90]}</a>'
            )

    return "\n".join(
        lines
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "======================================"
    )

    print(
        "WEB3STATION INTELLIGENCE v2"
    )

    print(
        f"Started: {now()}"
    )

    print(
        "======================================"
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
    # COLLECT
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
        ),
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

    for cluster in narrative_clusters[:10]:

        print(
            f"  {cluster['topic']} "
            f"| signals={cluster['item_count']} "
            f"| sources={cluster['source_count']} "
            f"| score={cluster['score']}"
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
        strong_candidates[:30]
    )

    # ========================================================
    # NO SIGNAL
    # ========================================================

    if not strong_candidates:

        print(
            "No strong signals."
        )

        for item in candidates[:50]:

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
            "⚠️ <b>Web3Station</b>\n\n"
            "Signals were collected but the "
            "editorial analysis layer failed.\n\n"
            "Next scan will retry."
        )

        return

    # ========================================================
    # TELEGRAM
    # ========================================================

    message = format_alert(
        analysis,
        strong_candidates,
        narrative_clusters
    )

    if message:

        # Telegram message safety
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


if __name__ == "__main__":
    main()
