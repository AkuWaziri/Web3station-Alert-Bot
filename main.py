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

CMC_API_KEY = os.getenv("CMC_API_KEY", "").strip()
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
LUNARCRUSH_API_KEY = os.getenv("LUNARCRUSH_API_KEY", "").strip()
NEYNAR_API_KEY = os.getenv("NEYNAR_API_KEY", "").strip()
SORSA_API_KEY = os.getenv("SORSA_API_KEY", "").strip()

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
).strip()

SEEN_FILE = "seen_ids.json"


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
# NEWS SOURCES
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
# SOCIAL SEARCHES
# ============================================================

SOCIAL_QUERIES = [
    "stablecoin",
    "crypto payments",
    "AI agents",
    "DeFi",
    "RWA",
]


# ============================================================
# GITHUB
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
    "User-Agent": "Web3Station/4.0"
})


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    if not value:
        return ""

    value = unescape(str(value))

    return " ".join(
        value
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


def now():
    return datetime.now(
        timezone.utc
    ).isoformat()


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

    except Exception as exc:
        print(f"[SEEN] Could not load file: {exc}")

    return set()


def save_seen(seen):
    try:
        with open(
            SEEN_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                list(seen)[-5000:],
                file,
                indent=2
            )

        print(
            f"[SEEN] Saved {len(seen)} IDs"
        )

    except Exception as exc:
        print(
            f"[SEEN ERROR] {exc}"
        )


def http_get(url, **kwargs):

    try:

        response = SESSION.get(
            url,
            timeout=25,
            **kwargs
        )

        print(
            f"[GET] {response.status_code} {url}"
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

    print("")
    print("======================================")
    print("TELEGRAM DELIVERY")
    print("======================================")

    if not TELEGRAM_TOKEN:

        print(
            "[TELEGRAM ERROR] TELEGRAM_TOKEN is empty"
        )

        return False

    if not TELEGRAM_CHAT_ID:

        print(
            "[TELEGRAM ERROR] TELEGRAM_CHAT_ID is empty"
        )

        return False

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "disable_web_page_preview": False
    }

    print(
        f"[TELEGRAM] Chat ID: {TELEGRAM_CHAT_ID}"
    )

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=30
        )

        print(
            f"[TELEGRAM] HTTP STATUS: "
            f"{response.status_code}"
        )

        print(
            f"[TELEGRAM] RESPONSE: "
            f"{response.text[:1000]}"
        )

        if response.ok:

            try:

                data = response.json()

                if data.get("ok") is True:

                    print(
                        "[TELEGRAM] MESSAGE SENT SUCCESSFULLY"
                    )

                    return True

                print(
                    "[TELEGRAM ERROR] Telegram returned ok=false"
                )

            except Exception:

                print(
                    "[TELEGRAM ERROR] Could not parse Telegram response"
                )

            return False

        print(
            "[TELEGRAM ERROR] Telegram rejected the request"
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

def relevance_score(item):

    text = (
        item.get("title", "")
        + " "
        + item.get("text", "")
    ).lower()

    score = 0

    for topic in PRIORITY_TOPICS:

        if topic in text:

            if topic in [
                "stablecoin",
                "stablecoins",
                "payment",
                "payments",
                "crypto payments",
                "onchain payments",
                "ai agent",
                "ai agents",
                "agentic commerce",
                "rwa",
                "real world assets",
                "tokenization",
                "tokenisation",
                "financial infrastructure",
                "onchain finance",
                "defi",
            ]:

                score += 3

            else:

                score += 1

    for word in [
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
    ]:

        if word in text:

            score += 2

    comments = item.get(
        "comments",
        0
    )

    if isinstance(comments, int):

        if comments >= 100:
            score += 4

        elif comments >= 30:
            score += 2

    return score


def is_relevant(item):

    return relevance_score(item) >= 2


# ============================================================
# COINMARKETCAP
# ============================================================

def fetch_coinmarketcap():

    results = []

    if not CMC_API_KEY:

        print(
            "[CoinMarketCap] API key missing - skipped"
        )

        return results

    response = http_get(
        "https://pro-api.coinmarketcap.com/"
        "v3/cryptocurrency/listings/latest",

        headers={
            "X-CMC_PRO_API_KEY":
                CMC_API_KEY
        },

        params={
            "start": 1,
            "limit": 50,
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
                "percent_change_24h",
                0
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

            price = quote.get(
                "price",
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

            slug = coin.get(
                "slug",
                ""
            )

            results.append({

                "source":
                    "CoinMarketCap",

                "title":
                    f"{name} market movement",

                "text":
                    (
                        f"{name} ({symbol}) "
                        f"price ${price:,.6f}; "
                        f"24h change {change:.2f}%; "
                        f"24h volume ${volume:,.0f}; "
                        f"market cap ${market_cap:,.0f}"
                    ),

                "url":
                    f"https://coinmarketcap.com/"
                    f"currencies/{slug}",

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

    headers = {}

    if COINGECKO_API_KEY:

        headers[
            "x-cg-demo-api-key"
        ] = COINGECKO_API_KEY

    response = http_get(
        "https://api.coingecko.com/api/v3/"
        "coins/markets",

        headers=headers,

        params={
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 50,
            "page": 1,
            "sparkline": "false"
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

            symbol = str(
                coin.get(
                    "symbol",
                    ""
                )
            ).upper()

            results.append({

                "source":
                    "CoinGecko",

                "title":
                    f"{name} market movement",

                "text":
                    (
                        f"{name} ({symbol}) "
                        f"price ${coin.get('current_price', 0):,.6f}; "
                        f"24h change {change:.2f}%; "
                        f"market cap ${coin.get('market_cap', 0):,.0f}; "
                        f"24h volume ${coin.get('total_volume', 0):,.0f}"
                    ),

                "url":
                    (
                        "https://www.coingecko.com/en/coins/"
                        f"{coin.get('id', '')}"
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
# RSS NEWS
# ============================================================

def fetch_news():

    results = []

    for source, url in RSS_FEEDS:

        print(
            f"[NEWS] Checking {source}"
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
                        f"{title}. {summary}"[
                            :4000
                        ],

                    "url":
                        link,

                    "id":
                        make_id(
                            source,
                            link
                        )

                }

                if is_relevant(item):

                    results.append(
                        item
                    )

        except Exception as exc:

            print(
                f"[NEWS ERROR] {source}: {exc}"
            )

    return results


# ============================================================
# REDDIT
# ============================================================

def fetch_reddit():

    results = []

    for subreddit in REDDIT_SUBREDDITS:

        print(
            f"[REDDIT] Checking r/{subreddit}"
        )

        response = http_get(
            f"https://www.reddit.com/"
            f"r/{subreddit}/new.json",

            params={
                "limit": 20,
                "raw_json": 1
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

                d = post.get(
                    "data",
                    {}
                )

                title = clean_text(
                    d.get(
                        "title",
                        ""
                    )
                )

                body = clean_text(
                    d.get(
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
                        f"{title}. {body}"[
                            :4000
                        ],

                    "url":
                        (
                            "https://www.reddit.com"
                            + d.get(
                                "permalink",
                                ""
                            )
                        ),

                    "comments":
                        d.get(
                            "num_comments",
                            0
                        ),

                    "id":
                        make_id(
                            "reddit",
                            subreddit,
                            d.get("id")
                        )

                }

                if is_relevant(item):

                    results.append(
                        item
                    )

        except Exception as exc:

            print(
                f"[REDDIT ERROR] "
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
            "[LunarCrush] API key missing - skipped"
        )

        return results

    response = http_get(

        "https://lunarcrush.com/"
        "api4/public/coins/list/v1",

        headers={
            "Authorization":
                f"Bearer {LUNARCRUSH_API_KEY}"
        },

        params={
            "limit": 50
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

            text = json.dumps(
                coin,
                ensure_ascii=False
            )

            item = {

                "source":
                    "LunarCrush",

                "title":
                    f"{symbol} social activity",

                "text":
                    text[:4000],

                "url":
                    "https://lunarcrush.com/",

                "id":
                    make_id(
                        "lunarcrush",
                        symbol,
                        text[:500]
                    )

            }

            results.append(
                item
            )

    except Exception as exc:

        print(
            f"[LUNARCRUSH ERROR] {exc}"
        )

    return results


# ============================================================
# NEYNAR / FARCASTER
# ============================================================

def fetch_neynar():

    results = []

    if not NEYNAR_API_KEY:

        print(
            "[Neynar] API key missing - skipped"
        )

        return results

    for query in SOCIAL_QUERIES:

        response = http_get(

            "https://api.neynar.com/v2/"
            "farcaster/cast/search/",

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

                if not is_relevant({
                    "title": query,
                    "text": text
                }):
                    continue

                username = (
                    cast
                    .get("author", {})
                    .get("username", "")
                )

                item = {

                    "source":
                        "Farcaster / Neynar",

                    "title":
                        f"Farcaster: {query}",

                    "text":
                        text[:4000],

                    "url":
                        (
                            "https://warpcast.com/"
                            f"{username}/{cast_hash}"
                        ),

                    "id":
                        make_id(
                            "neynar",
                            cast_hash
                        )

                }

                results.append(
                    item
                )

        except Exception as exc:

            print(
                f"[NEYNAR ERROR] {exc}"
            )

    return results


# ============================================================
# SORSA / X
# ============================================================

def fetch_sorsa():

    results = []

    if not SORSA_API_KEY:

        print(
            "[Sorsa] API key missing - skipped"
        )

        return results

    for query in SOCIAL_QUERIES:

        response = http_get(

            "https://api.sorsa.io/v3/"
            "tweets/search",

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

                if not is_relevant({
                    "title": query,
                    "text": text
                }):
                    continue

                item = {

                    "source":
                        "X / Sorsa",

                    "title":
                        f"X discussion: {query}",

                    "text":
                        text[:4000],

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

                results.append(
                    item
                )

        except Exception as exc:

            print(
                f"[SORSA ERROR] {exc}"
            )

    return results


# ============================================================
# GITHUB
# ============================================================

def fetch_github():

    results = []

    for query in GITHUB_SEARCHES:

        print(
            f"[GITHUB] Searching: {query}"
        )

        response = http_get(

            "https://api.github.com/"
            "search/repositories",

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
                    5
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

                stars = repo.get(
                    "stargazers_count",
                    0
                )

                forks = repo.get(
                    "forks_count",
                    0
                )

                updated = repo.get(
                    "updated_at",
                    ""
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
                            f"{stars} stars. "
                            f"{forks} forks. "
                            f"Updated: {updated}."
                        )[:4000],

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

                    results.append(
                        item
                    )

        except Exception as exc:

            print(
                f"[GITHUB ERROR] {exc}"
            )

    return results


# ============================================================
# GROQ
# ============================================================

def groq_analyze(item):

    print("")
    print("======================================")
    print("GROQ")
    print("======================================")

    if not GROQ_API_KEY:

        print(
            "[GROQ ERROR] GROQ_API_KEY is missing"
        )

        return None

    print(
        f"[GROQ] Model: {GROQ_MODEL}"
    )

    system_prompt = """
You are the editorial AI for WEB3STATION.

Turn one crypto/Web3 signal into a concise social-media
content opportunity.

Return EXACTLY:

CATEGORY:
short category

ANGLE:
one or two concise sentences explaining the interesting
content angle.

DRAFT:
a natural social-media post based ONLY on the supplied
information.

RULES:

- Never invent facts.
- Never invent numbers.
- Never invent partnerships.
- Never invent quotes.
- Never invent events.
- Do not exaggerate.
- Do not use fake certainty.
- Do not write a news article.
- Do not add confidence scores.
- Do not add evidence scores.
- Do not add narratives.
- Do not add "what we know".
- Do not add "what we're inferring".
- Do not add "what could happen next".
- Do not add hashtags unless they naturally belong.
- Keep the draft concise.
- Make the angle more interesting than simply repeating
  the headline.
- If the signal is weak, make the angle cautious.
- If it is developer activity, focus on what builders
  are building.
- If it is payments, focus on infrastructure and utility.
- If it is AI, focus on the AI x crypto connection.
- If it is DeFi, focus on mechanism, adoption or risk.
- If it is regulation, focus on the practical implication.
- If it is security, remain factual and serious.
- If it is a community discussion, preserve the uncertainty.

Do not write anything outside CATEGORY, ANGLE and DRAFT.
"""

    user_prompt = f"""
SOURCE:
{item.get("source", "")}

TITLE:
{item.get("title", "")}

SIGNAL:
{item.get("text", "")[:4000]}

SOURCE URL:
{item.get("url", "")}
"""

    url = (
        "https://api.groq.com/openai/v1/"
        "chat/completions"
    )

    payload = {
        "model": GROQ_MODEL,
        "temperature": 0.6,
        "max_tokens": 600,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ]
    }

    try:

        response = requests.post(

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
            f"[GROQ] HTTP STATUS: "
            f"{response.status_code}"
        )

        print(
            f"[GROQ] RESPONSE: "
            f"{response.text[:1500]}"
        )

        if not response.ok:

            print(
                "[GROQ ERROR] API request failed"
            )

            return None

        data = response.json()

        choices = data.get(
            "choices",
            []
        )

        if not choices:

            print(
                "[GROQ ERROR] No choices returned"
            )

            return None

        content = (
            choices[0]
            .get("message", {})
            .get("content", "")
        )

        if not content:

            print(
                "[GROQ ERROR] Empty content returned"
            )

            return None

        print(
            "[GROQ] Editorial response received"
        )

        return parse_groq(
            content
        )

    except Exception as exc:

        print(
            f"[GROQ EXCEPTION] {exc}"
        )

        return None


# ============================================================
# GROQ PARSER
# ============================================================

def parse_groq(text):

    text = text.strip()

    upper = text.upper()

    category_marker = "CATEGORY:"
    angle_marker = "ANGLE:"
    draft_marker = "DRAFT:"

    category_pos = upper.find(
        category_marker
    )

    angle_pos = upper.find(
        angle_marker
    )

    draft_pos = upper.find(
        draft_marker
    )

    if category_pos == -1:
        print(
            "[GROQ PARSE ERROR] CATEGORY missing"
        )
        return None

    if angle_pos == -1:
        print(
            "[GROQ PARSE ERROR] ANGLE missing"
        )
        return None

    if draft_pos == -1:
        print(
            "[GROQ PARSE ERROR] DRAFT missing"
        )
        return None

    category = text[
        category_pos + len(category_marker):
        angle_pos
    ].strip()

    angle = text[
        angle_pos + len(angle_marker):
        draft_pos
    ].strip()

    draft = text[
        draft_pos + len(draft_marker):
    ].strip()

    if not category:
        print(
            "[GROQ PARSE ERROR] Empty category"
        )
        return None

    if not angle:
        print(
            "[GROQ PARSE ERROR] Empty angle"
        )
        return None

    if not draft:
        print(
            "[GROQ PARSE ERROR] Empty draft"
        )
        return None

    return {
        "category": category,
        "angle": angle,
        "draft": draft
    }


# ============================================================
# TELEGRAM MESSAGE
# ============================================================

def build_message(item, editorial):

    return (
        "🧠 WEB3STATION\n\n"

        f"CATEGORY\n"
        f"{editorial['category']}\n\n"

        f"ANGLE\n"
        f"{editorial['angle']}\n\n"

        f"DRAFT\n"
        f"{editorial['draft']}\n\n"

        f"SOURCE\n"
        f"{item['source']}\n"
        f"{item['url']}"
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

        print("")
        print("======================================")
        print(f"COLLECTING: {name}")
        print("======================================")

        try:

            items = function()

            print(
                f"[{name}] {len(items)} signals"
            )

            all_items.extend(
                items
            )

        except Exception as exc:

            print(
                f"[{name} ERROR] {exc}"
            )

    return all_items


# ============================================================
# SELECT ONE BEST SIGNAL PER SOURCE
# ============================================================

def select_signals(items, seen):

    available = []

    local_ids = set()

    for item in items:

        item_id = item.get(
            "id",
            ""
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

        item["_score"] = relevance_score(
            item
        )

        available.append(
            item
        )

    # Highest relevance first
    available.sort(
        key=lambda x:
            x.get("_score", 0),
        reverse=True
    )

    selected = []

    source_used = set()

    for item in available:

        source = item.get(
            "source",
            "Unknown"
        )

        # One report per source per run
        if source in source_used:
            continue

        # Weak signals are ignored
        if item.get(
            "_score",
            0
        ) < 2:
            continue

        selected.append(
            item
        )

        source_used.add(
            source
        )

    return selected


# ============================================================
# MAIN
# ============================================================

def main():

    print("")
    print("======================================")
    print("WEB3STATION")
    print("SIMPLE CONTENT RADAR")
    print("======================================")
    print(
        f"Time: {now()}"
    )

    # --------------------------------------------------------
    # CHECK TELEGRAM BEFORE DOING ANYTHING
    # --------------------------------------------------------

    if not TELEGRAM_TOKEN:

        print(
            "[FATAL] TELEGRAM_TOKEN is missing"
        )

        return

    if not TELEGRAM_CHAT_ID:

        print(
            "[FATAL] TELEGRAM_CHAT_ID is missing"
        )

        return

    if not GROQ_API_KEY:

        print(
            "[FATAL] GROQ_API_KEY is missing"
        )

        return

    print(
        "[CONFIG] Telegram credentials found"
    )

    print(
        "[CONFIG] Groq API key found"
    )

    print(
        f"[CONFIG] Groq model: {GROQ_MODEL}"
    )

    # --------------------------------------------------------
    # LOAD SEEN
    # --------------------------------------------------------

    seen = load_seen()

    print(
        f"[SEEN] {len(seen)} previously sent signals"
    )

    # --------------------------------------------------------
    # COLLECT
    # --------------------------------------------------------

    all_items = collect_all()

    print("")
    print(
        f"TOTAL COLLECTED: {len(all_items)}"
    )

    # --------------------------------------------------------
    # SELECT
    # --------------------------------------------------------

    selected = select_signals(
        all_items,
        seen
    )

    print(
        f"SELECTED: {len(selected)}"
    )

    if not selected:

        print(
            "No new relevant signals."
        )

        print(
            "No Telegram message will be sent."
        )

        return

    # --------------------------------------------------------
    # PROCESS
    # --------------------------------------------------------

    sent_count = 0
    failed_count = 0

    for index, item in enumerate(
        selected,
        start=1
    ):

        print("")
        print("======================================")
        print(
            f"REPORT {index}/{len(selected)}"
        )
        print("======================================")

        print(
            f"Source: {item.get('source')}"
        )

        print(
            f"Title: {item.get('title')}"
        )

        print(
            f"Score: {item.get('_score', 0)}"
        )

        # ----------------------------------------------------
        # GROQ
        # ----------------------------------------------------

        editorial = groq_analyze(
            item
        )

        if not editorial:

            print(
                "[REPORT FAILED] Groq failed"
            )

            print(
                "[IMPORTANT] Signal NOT marked as seen"
            )

            failed_count += 1

            continue

        # ----------------------------------------------------
        # BUILD MESSAGE
        # ----------------------------------------------------

        message = build_message(
            item,
            editorial
        )

        # Telegram max message size is 4096 characters.
        if len(message) > 4000:

            message = (
                message[:3950]
                + "\n\n[truncated]"
            )

        print("")
        print(
            "MESSAGE TO TELEGRAM:"
        )
        print("--------------------------------------")
        print(message)
        print("--------------------------------------")

        # ----------------------------------------------------
        # SEND TELEGRAM
        # ----------------------------------------------------

        sent = send_telegram(
            message
        )

        if sent:

            print(
                "[SUCCESS] Telegram delivery confirmed"
            )

            # ONLY NOW mark as seen
            seen.add(
                item["id"]
            )

            save_seen(
                seen
            )

            sent_count += 1

        else:

            print(
                "[FAILED] Telegram delivery failed"
            )

            print(
                "[IMPORTANT] Signal NOT marked as seen"
            )

            failed_count += 1

    # --------------------------------------------------------
    # FINAL STATUS
    # --------------------------------------------------------

    print("")
    print("======================================")
    print("WEB3STATION RUN COMPLETE")
    print("======================================")

    print(
        f"Collected: {len(all_items)}"
    )

    print(
        f"Selected: {len(selected)}"
    )

    print(
        f"Sent: {sent_count}"
    )

    print(
        f"Failed: {failed_count}"
    )

    print(
        f"Seen IDs: {len(seen)}"
    )

    print("======================================")


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()
