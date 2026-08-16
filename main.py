import os
import json
import hashlib
from datetime import datetime, timezone, timedelta
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

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
)

SEEN_FILE = "seen_ids.json"
TOPIC_FILE = "topic_history.json"

# Farcaster maximum age
FARCASTER_MAX_AGE_HOURS = 72


# ============================================================
# CORE CONTENT NICHE
# ============================================================

PRIORITY_TOPICS = [
    "ai",
    "ai agent",
    "ai agents",
    "agentic",
    "agentic commerce",
    "stablecoin",
    "stablecoins",
    "payments",
    "payment",
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
    "arc",
    "base",
    "arbitrum",
    "layer 2",
    "l2",
    "institutional",
    "regulation",
    "security",
    "hack",
    "exploit",
    "nft",
    "nfts",
    "crypto",
    "meme",
    "memecomics",
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
# SOCIAL / RESEARCH QUERIES
# ============================================================

SOCIAL_QUERIES = [
    "stablecoin",
    "crypto payments",
    "AI agents",
    "DeFi",
    "RWA",
]


# ============================================================
# SESSION
# ============================================================

SESSION = requests.Session()

SESSION.headers.update({
    "User-Agent": "Web3Station/4.0 crypto intelligence bot"
})


# ============================================================
# BASIC HELPERS
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
        str(x)
        for x in parts
        if x is not None
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def now():
    return datetime.now(
        timezone.utc
    ).isoformat()


def load_json(filename, default):
    try:
        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except Exception:
        return default


def save_json(filename, data):
    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )


def get(url, **kwargs):
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


def post(url, **kwargs):
    try:

        response = SESSION.post(
            url,
            timeout=30,
            **kwargs
        )

        if response.status_code == 200:
            return response

        print(
            f"[POST {response.status_code}] {url}"
        )

        print(
            response.text[:500]
        )

    except Exception as exc:

        print(
            f"[POST ERROR] {url}: {exc}"
        )

    return None


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):

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
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "disable_web_page_preview": False
    }

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=30
        )

        print(
            f"[TELEGRAM STATUS] {response.status_code}"
        )

        print(
            f"[TELEGRAM RESPONSE] "
            f"{response.text[:1000]}"
        )

        if response.ok:

            print(
                "[TELEGRAM] Message sent successfully"
            )

            return True

        print(
            "[TELEGRAM ERROR] Telegram rejected message"
        )

        return False

    except Exception as exc:

        print(
            f"[TELEGRAM ERROR] {exc}"
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

    for topic in PRIORITY_TOPICS:

        if topic in text:
            return True

    return False


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


# ============================================================
# DATE HELPERS
# ============================================================

def parse_datetime(value):

    if not value:
        return None

    if isinstance(
        value,
        datetime
    ):

        dt = value

    else:

        value = str(value).strip()

        # ISO format
        try:

            dt = datetime.fromisoformat(
                value.replace(
                    "Z",
                    "+00:00"
                )
            )

        except Exception:

            dt = None

        # Common Twitter/RSS style
        if dt is None:

            formats = [
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S%z",
                "%a %b %d %H:%M:%S %z %Y",
                "%Y-%m-%d %H:%M:%S",
            ]

            for fmt in formats:

                try:

                    dt = datetime.strptime(
                        value,
                        fmt
                    )

                    break

                except Exception:
                    continue

    if dt is None:
        return None

    if dt.tzinfo is None:

        dt = dt.replace(
            tzinfo=timezone.utc
        )

    return dt.astimezone(
        timezone.utc
    )


def is_recent_farcaster(created_at):

    dt = parse_datetime(
        created_at
    )

    if dt is None:

        print(
            "[FARCASTER] "
            "Rejected post with invalid date"
        )

        return False

    current = datetime.now(
        timezone.utc
    )

    # Reject future timestamps.
    if dt > current + timedelta(
        minutes=5
    ):

        print(
            "[FARCASTER] "
            "Rejected future-dated post"
        )

        return False

    age = current - dt

    max_age = timedelta(
        hours=FARCASTER_MAX_AGE_HOURS
    )

    if age > max_age:

        print(
            f"[FARCASTER] "
            f"Rejected old cast: "
            f"{age.total_seconds() / 3600:.1f}h old"
        )

        return False

    hours = age.total_seconds() / 3600

    if hours <= 24:

        print(
            f"[FARCASTER] "
            f"Accepted fresh cast: "
            f"{hours:.1f}h old"
        )

    elif hours <= 48:

        print(
            f"[FARCASTER] "
            f"Accepted 24-48h cast: "
            f"{hours:.1f}h old"
        )

    else:

        print(
            f"[FARCASTER] "
            f"Accepted 48-72h cast: "
            f"{hours:.1f}h old"
        )

    return True


# ============================================================
# COINMARKETCAP
# ============================================================

def fetch_coinmarketcap():

    results = []

    if not CMC_API_KEY:

        print(
            "[CMC] API key missing"
        )

        return results

    url = (
        "https://pro-api.coinmarketcap.com/"
        "v3/cryptocurrency/listings/latest"
    )

    response = get(
        url,

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

            symbol = coin.get(
                "symbol",
                ""
            )

            price = quote.get(
                "price",
                0
            )

            change = quote.get(
                "percent_change_24h",
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

            text = (
                f"{coin.get('name')} "
                f"({symbol}) price "
                f"${price:,.6f}; "
                f"24h change {change:.2f}%; "
                f"24h volume ${volume:,.0f}; "
                f"market cap ${market_cap:,.0f}"
            )

            if abs(change) < 5:
                continue

            results.append({

                "source":
                    "CoinMarketCap",

                "title":
                    f"{coin.get('name')} market movement",

                "text":
                    text,

                "url":
                    "https://coinmarketcap.com/currencies/"
                    + str(
                        coin.get(
                            "slug",
                            ""
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
            f"[CMC ERROR] {exc}"
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

    response = get(
        url,

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

            results.append({

                "source":
                    "CoinGecko",

                "title":
                    f"{coin.get('name')} market movement",

                "text":
                    (
                        f"{coin.get('name')} "
                        f"({coin.get('symbol', '').upper()}) "
                        f"price ${coin.get('current_price', 0):,.6f}; "
                        f"24h change {change:.2f}%; "
                        f"market cap ${coin.get('market_cap', 0):,.0f}; "
                        f"24h volume ${coin.get('total_volume', 0):,.0f}"
                    ),

                "url":
                    f"https://www.coingecko.com/en/coins/"
                    f"{coin.get('id', '')}",

                "id":
                    make_id(
                        "coingecko",
                        coin.get("id"),
                        round(change, 1)
                    )

            })

    except Exception as exc:

        print(
            f"[COINGECKO ERROR] {exc}"
        )

    return results


# ============================================================
# NEWS RSS
# ============================================================

def fetch_news():

    results = []

    for source, url in RSS_FEEDS:

        print(
            f"[NEWS] checking {source}"
        )

        try:

            feed = feedparser.parse(
                url
            )

            for entry in feed.entries[:15]:

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
                            :3000
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
                f"[NEWS ERROR] "
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

        response = get(
            url,

            params={
                "limit": 15,
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
                        f"{title}. {body}"[
                            :3000
                        ],

                    "url":
                        "https://www.reddit.com"
                        + item_data.get(
                            "permalink",
                            ""
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
                            item_data.get("id")
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
            "[LUNARCRUSH] API key missing"
        )

        return results

    url = (
        "https://lunarcrush.com/"
        "api4/public/coins/list/v1"
    )

    response = get(

        url,

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

            results.append({

                "source":
                    "LunarCrush",

                "title":
                    f"{symbol} social activity",

                "text":
                    json.dumps(
                        coin,
                        ensure_ascii=False
                    )[:3000],

                "url":
                    "https://lunarcrush.com/",

                "id":
                    make_id(
                        "lunarcrush",
                        symbol,
                        json.dumps(
                            coin,
                            sort_keys=True
                        )[:500]
                    )

            })

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
            "[NEYNAR] API key missing"
        )

        return results

    for query in SOCIAL_QUERIES:

        print(
            f"[NEYNAR] searching: {query}"
        )

        url = (
            "https://api.neynar.com/v2/"
            "farcaster/cast/search/"
        )

        response = get(

            url,

            headers={
                "x-api-key":
                    NEYNAR_API_KEY
            },

            params={
                "q":
                    query,

                "limit":
                    25
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

            print(
                f"[NEYNAR] "
                f"{len(casts)} raw casts"
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

                created_at = cast.get(
                    "timestamp",
                    cast.get(
                        "created_at",
                        ""
                    )
                )

                if not text:
                    continue

                # ------------------------------------------------
                # HARD 72-HOUR FARCASTER FILTER
                # ------------------------------------------------

                if not is_recent_farcaster(
                    created_at
                ):

                    continue

                author = cast.get(
                    "author",
                    {}
                )

                if not isinstance(
                    author,
                    dict
                ):

                    author = {}

                username = (
                    author.get(
                        "username",
                        ""
                    )
                )

                item = {

                    "source":
                        "Farcaster / Neynar",

                    "title":
                        f"Farcaster discussion: {query}",

                    "text":
                        text[:3000],

                    "url":
                        (
                            "https://warpcast.com/"
                            + str(username)
                            + "/"
                            + str(cast_hash)
                        ),

                    "created_at":
                        created_at,

                    "id":
                        make_id(
                            "neynar",
                            cast_hash
                        )

                }

                if is_relevant(item):

                    results.append(
                        item
                    )

        except Exception as exc:

            print(
                f"[NEYNAR ERROR] "
                f"{query}: {exc}"
            )

    return results


# ============================================================
# SORSA / X
# ============================================================

def fetch_sorsa():

    results = []

    if not SORSA_API_KEY:

        print(
            "[SORSA] API key missing"
        )

        return results

    for query in SOCIAL_QUERIES:

        url = (
            "https://api.sorsa.io/v3/"
            "tweets/search"
        )

        response = get(

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
                        f"X discussion: {query}",

                    "text":
                        text[:3000],

                    "url":
                        (
                            "https://x.com/i/web/status/"
                            + str(tweet_id)
                        ),

                    "id":
                        make_id(
                            "sorsa",
                            tweet_id,
                            text
                        )

                }

                if is_relevant(item):

                    results.append(
                        item
                    )

        except Exception as exc:

            print(
                f"[SORSA ERROR] "
                f"{query}: {exc}"
            )

    return results


# ============================================================
# GROQ EDITOR
# ============================================================

def groq_edit(item):

    if not GROQ_API_KEY:

        print(
            "[GROQ] API key missing"
        )

        return None

    system_prompt = """
You are the senior editorial writer
for Web3Station.

Turn the supplied crypto/Web3 signal
into a strong social-media draft.

The goal is to sound like a thoughtful
human crypto writer, not an AI-generated
news account.

The draft must have a genuine editorial
point rather than merely rewriting the
source.

STYLE

Choose the tone naturally according to
the subject and angle.

Randomly vary between appropriate styles
such as:

- Professional and formal
- Memeconic
- Degen
- optimistic
- Casual and friendly
- Educational
- Explanatory
- Analytical
- My take
- Curious
- Assertive
- Encouraging
- Optimistic
- Worried
- Skeptical
- Surprised
- Observational
- Contrarian
- Technical
- Builder-focused
- Investor-focused
- Leadership
- Protagonist/narrative
- Creative and character-driven
- Conversational

Do NOT announce which style you selected.

Do not use the same opening or structure
repeatedly.

Sometimes begin with an observation.

Sometimes with a question.

Sometimes with a strong statement.

Sometimes explain a concept.

Sometimes use contrast.

Sometimes tell a small narrative.

Sometimes use understated humor.

Sometimes use a metaphor or analogy.

Sometimes use literary techniques such
as rhythm, repetition, irony, contrast,
understatement or rhetorical questions,
but only when they naturally improve the
post.

The writing should still sound like a
real person who follows crypto closely.

VOICE

Avoid:

- AI news-summary language
- corporate PR
- generic influencer language
- exaggerated hype
- repetitive phrases
- empty conclusions
- unnecessary hashtags
- excessive emojis

Avoid phrases such as:

"game changer"
"revolutionary"
"the future is here"
"this is huge"
"mass adoption is coming"
"paradigm shift"

unless discussing them critically.

FACTS

Never invent facts.

Never invent numbers.

Never invent partnerships.

Never invent quotes.

Never invent dates.

Never invent product capabilities.

Never turn speculation into fact.

If the source is uncertain, preserve that
uncertainty.

DEPTH AND LENGTH

The draft should be MEDIUM length.

Target approximately 80-180 words.

Do not make every draft exactly the same
length.

Some can be closer to 80 words.

Some can be 120.

Some can be 160-180.

Do not pad the draft.

Do not repeat the source unnecessarily.

The draft should add interpretation,
context, explanation or a useful second-order
thought.

The reader should understand why the signal
matters.

PERSONAL STYLE

You may sometimes naturally use phrases like:

"my take:"

"what stands out to me is..."

"the part people may miss is..."

"i think the more interesting question is..."

"there's a bigger story here."

But do not repeatedly use these phrases.

If you use "my take", do not invent a
personal experience.

CATEGORY

Keep the category concise.

Examples:

AI x Crypto Infrastructure
Stablecoin Payments
Onchain Finance
RWA & Tokenization
DeFi
Crypto Security
Crypto Infrastructure
AI Agents
Web3 Adoption
Bitcoin
Ethereum
Solana
NFTs
Crypto Regulation

ANGLE

Give one or two sentences explaining
the interesting editorial angle.

OUTPUT

Return EXACTLY:

CATEGORY:
one concise category

ANGLE:
one or two sentences

DRAFT:
the complete medium-length social-media draft

Nothing before CATEGORY.

Nothing after the DRAFT.
"""

    user_prompt = f"""
SOURCE:
{item.get('source', '')}

TITLE:
{item.get('title', '')}

INFORMATION:
{item.get('text', '')[:3500]}

SOURCE URL:
{item.get('url', '')}

PUBLISHED:
{item.get('created_at', '')}
"""

    response = post(

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
                0.85,

            "max_tokens":
                900,

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
    )

    if not response:
        return None

    try:

        data = response.json()

        content = (
            data
            .get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )

        if not content:

            return None

        return parse_groq_output(
            content
        )

    except Exception as exc:

        print(
            f"[GROQ ERROR] {exc}"
        )

        return None


# ============================================================
# GROQ OUTPUT PARSER
# ============================================================

def parse_groq_output(text):

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
        return None

    if angle_pos == -1:
        return None

    if draft_pos == -1:
        return None

    category = text[
        category_pos
        + len(category_marker):
        angle_pos
    ].strip()

    angle = text[
        angle_pos
        + len(angle_marker):
        draft_pos
    ].strip()

    draft = text[
        draft_pos
        + len(draft_marker):
    ].strip()

    if not category:
        return None

    if not angle:
        return None

    if not draft:
        return None

    return {

        "category":
            category,

        "angle":
            angle,

        "draft":
            draft

    }


# ============================================================
# TELEGRAM FORMAT
# ============================================================

def format_message(
    item,
    editorial
):

    return (
        "🧠 WEB3STATION\n\n"

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
# MAIN
# ============================================================

def main():

    print(
        "======================================"
    )

    print(
        "WEB3STATION"
    )

    print(
        "Simple Crypto Content Radar"
    )

    print(
        now()
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

    # --------------------------------------------------------
    # COLLECT
    # --------------------------------------------------------

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
            "Neynar / Farcaster",
            fetch_neynar
        ),

        (
            "Sorsa",
            fetch_sorsa
        )

    ]

    all_items = []

    for name, function in collectors:

        print(
            f"\n[COLLECT] {name}"
        )

        try:

            items = function()

            print(
                f"[{name}] "
                f"{len(items)} signals"
            )

            all_items.extend(
                items
            )

        except Exception as exc:

            print(
                f"[{name} ERROR] {exc}"
            )

    print(
        f"\nTOTAL SIGNALS: "
        f"{len(all_items)}"
    )

    # --------------------------------------------------------
    # REMOVE DUPLICATES
    # --------------------------------------------------------

    unique = []

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

        item[
            "_score"
        ] = relevance_score(
            item
        )

        unique.append(
            item
        )

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    unique.sort(
        key=lambda item:
            item.get(
                "_score",
                0
            ),
        reverse=True
    )

    print(
        f"NEW SIGNALS: "
        f"{len(unique)}"
    )

    # --------------------------------------------------------
    # MAX ONE REPORT PER SOURCE
    # --------------------------------------------------------

    selected = []

    source_count = {}

    for item in unique:

        source = item.get(
            "source",
            "Unknown"
        )

        source_count.setdefault(
            source,
            0
        )

        if source_count[source] >= 1:
            continue

        if item.get(
            "_score",
            0
        ) < 2:

            continue

        selected.append(
            item
        )

        source_count[source] += 1

    print(
        f"SELECTED REPORTS: "
        f"{len(selected)}"
    )

    # --------------------------------------------------------
    # PROCESS
    # --------------------------------------------------------

    successful_ids = []

    for item in selected:

        print(
            "\n--------------------------------------"
        )

        print(
            f"SOURCE: "
            f"{item.get('source')}"
        )

        print(
            f"TITLE: "
            f"{item.get('title')}"
        )

        editorial = groq_edit(
            item
        )

        if not editorial:

            print(
                "[SKIP] Groq editorial failed"
            )

            continue

        message = format_message(
            item,
            editorial
        )

        if len(message) > 3900:

            message = (
                message[:3900]
                + "\n\n[truncated]"
            )

        sent = send_telegram(
            message
        )

        if sent:

            print(
                "[SENT]"
            )

            successful_ids.append(
                item["id"]
            )

            topic_history.append({

                "timestamp":
                    now(),

                "source":
                    item.get(
                        "source"
                    ),

                "category":
                    editorial.get(
                        "category"
                    ),

                "title":
                    item.get(
                        "title"
                    )

            })

        else:

            print(
                "[NOT SENT]"
            )

    # --------------------------------------------------------
    # SAVE ONLY SUCCESSFUL
    # --------------------------------------------------------

    for item_id in successful_ids:

        seen.add(
            item_id
        )

    save_json(
        SEEN_FILE,
        list(seen)[-5000:]
    )

    save_json(
        TOPIC_FILE,
        topic_history[-500:]
    )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    print(
        "\n======================================"
    )

    print(
        "RUN COMPLETE"
    )

    print(
        f"Signals collected: "
        f"{len(all_items)}"
    )

    print(
        f"New signals: "
        f"{len(unique)}"
    )

    print(
        f"Reports sent: "
        f"{len(successful_ids)}"
    )

    print(
        "======================================"
    )


if __name__ == "__main__":
    main()
