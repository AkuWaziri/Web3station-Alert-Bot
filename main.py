import os
import json
import hashlib
import random
from datetime import datetime, timezone
from html import unescape

import requests
import feedparser


# ============================================================
# WEB3STATION
# SIMPLE REAL-TIME CRYPTO CONTENT RADAR
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
    "nft",
    "nfts",
    "crypto",
]


# ============================================================
# NEWS
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
# SESSION
# ============================================================

SESSION = requests.Session()

SESSION.headers.update({
    "User-Agent": "Web3Station/4.0 crypto intelligence bot"
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
    try:
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

    except Exception as exc:
        print(
            f"[SAVE ERROR] {filename}: {exc}"
        )


def get(url, **kwargs):
    try:
        response = SESSION.get(
            url,
            timeout=25,
            **kwargs
        )

        print(
            f"[GET] {response.status_code} {url}"
        )

        if response.status_code == 200:
            return response

        print(
            response.text[:500]
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
            timeout=45,
            **kwargs
        )

        print(
            f"[POST] {response.status_code} {url}"
        )

        if response.status_code == 200:
            return response

        print(
            response.text[:1000]
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
            f"[TELEGRAM STATUS] "
            f"{response.status_code}"
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

    high_value_topics = [
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
    ]

    for topic in PRIORITY_TOPICS:

        if topic in text:

            if topic in high_value_topics:
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
        "audit",
        "announcement",
    ]

    for word in important_events:

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
            "X-CMC_PRO_API_KEY": CMC_API_KEY
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

            if not isinstance(
                change,
                (int, float)
            ):
                continue

            if abs(change) < 5:
                continue

            text = (
                f"{coin.get('name')} "
                f"({symbol}) price "
                f"${price:,.6f}; "
                f"24h change {change:.2f}%; "
                f"24h volume ${volume:,.0f}; "
                f"market cap ${market_cap:,.0f}"
            )

            results.append({

                "source":
                    "CoinMarketCap",

                "title":
                    f"{coin.get('name')} market movement",

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
            "per_page": 100,
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
                        f"price "
                        f"${coin.get('current_price', 0):,.6f}; "
                        f"24h change "
                        f"{change:.2f}%; "
                        f"market cap "
                        f"${coin.get('market_cap', 0):,.0f}; "
                        f"24h volume "
                        f"${coin.get('total_volume', 0):,.0f}"
                    ),

                "url":
                    (
                        "https://www.coingecko.com/"
                        "en/coins/"
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
            f"[COINGECKO ERROR] {exc}"
        )

    return results


# ============================================================
# RSS NEWS
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

            for entry in feed.entries:

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
                        )[:4000],

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
                "limit": 100,
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
                        (
                            f"{title}. "
                            f"{body}"
                        )[:4000],

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
                            item_data.get("id")
                        )
                }

                if is_relevant(item):
                    results.append(item)

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
            "limit": 100
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
            )[:4000]

            item = {

                "source":
                    "LunarCrush",

                "title":
                    f"{symbol} social activity",

                "text":
                    text,

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
                    50
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

                author = (
                    cast
                    .get("author", {})
                    .get("username", "")
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
                        text[:4000],

                    "url":
                        (
                            "https://warpcast.com/"
                            f"{author}/"
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
                f"[NEYNAR ERROR] "
                f"{exc}"
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
                    50
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

                if is_relevant(item):
                    results.append(item)

        except Exception as exc:

            print(
                f"[SORSA ERROR] "
                f"{exc}"
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

    writing_styles = [
        "educational",
        "analytical",
        "my take",
        "conversational",
        "skeptical",
        "deep observation",
        "explainer",
        "builder perspective",
        "market perspective",
        "contrarian",
        "elaborative",
        "short sharp thesis",
    ]

    selected_style = random.choice(
        writing_styles
    )

    system_prompt = f"""
You are the editorial intelligence behind
WEB3STATION, a crypto intelligence and content
radar for a human crypto creator.

Your job is to turn a real source signal into
a strong human social-media draft.

The draft must NOT sound like an AI-generated
crypto news summary.

CURRENT WRITING MODE:
{selected_style}

Use that mode naturally, but do not announce it.

IMPORTANT:

Write like an intelligent human who spends time
around crypto, technology and internet culture.

Human writing is not perfectly symmetrical.

Do not make every paragraph the same length.

Do not make every sentence the same length.

Sometimes use a short sentence after a longer one.

Sometimes start with an observation.

Sometimes start with a question.

Sometimes use contrast.

Sometimes use an analogy.

Sometimes use understatement.

Sometimes build an argument slowly.

Sometimes make the main point immediately.

Sometimes leave a little tension in the conclusion.

Sometimes use phrases such as:
"my take:"
"the interesting part is..."
"what stands out to me..."
"i think..."
"there's a bigger question here..."
"the part worth watching..."
But do NOT use these in every post.

The writing should vary naturally from post to post.

LITERARY FEATURES:

When appropriate, use:

- contrast
- metaphor
- analogy
- rhetorical questions
- rhythm
- repetition for emphasis
- understatement
- narrative progression
- cause and effect
- tension
- irony when justified
- vivid but restrained language

Do not force literary devices into technical news.

CRYPTO STYLE:

The audience understands crypto.

You can use terms such as:

onchain
liquidity
stablecoins
agents
wallets
DeFi
L2
RWA
tokenization
protocols
settlement
infrastructure
capital
builders

Do not over-explain basic crypto terminology.

However, when an unfamiliar technology appears,
explain it clearly enough that an intelligent
non-expert can follow the argument.

CONTENT QUALITY:

The post should contain an actual thought.

Do not simply rewrite the source headline.

Do not merely summarize what happened.

Find the interesting implication.

Ask:

Why does this matter?

What changes?

What does this reveal?

What should people watch?

What assumption does this challenge?

What is still unclear?

What could happen next?

Use only what the source supports.

NEVER:

- invent facts
- invent statistics
- invent partnerships
- invent quotes
- invent people
- invent dates
- invent adoption
- invent market reactions
- pretend speculation is fact
- manufacture certainty
- create fake urgency

If something is uncertain, preserve that uncertainty.

Do not automatically make the subject bullish.

Do not automatically make it bearish.

Do not use:

"game changer"
"revolutionary"
"the future is here"
"this is huge"
"mass adoption is coming"
"paradigm shift"

unless the source itself genuinely supports
the underlying claim, and even then prefer
more precise language.

Do not use excessive emojis.

Do not add hashtags unless genuinely useful.

Do not begin every post with a headline.

Do not make every post a thread.

Do not make every post sound like a journalist.

Some posts should feel like a personal observation.
Some should feel educational.
Some should feel analytical.
Some should feel like a knowledgeable person
thinking out loud.

LENGTH:

Make the draft detailed enough to contain a real idea.

Normally aim for roughly 120-250 words.

Shorter is acceptable when the story only supports
a short observation.

Longer is acceptable when the subject needs explanation.

Never pad the draft just to reach a word count.

OUTPUT:

Return EXACTLY:

CATEGORY
one short category

ANGLE
one or two concise sentences explaining the
interesting editorial angle

DRAFT
the complete social-media draft

SOURCE
the original source URL

Do not add:

confidence scores
evidence scores
KOL scores
narrative scores
"what we know"
"what we're inferring"
"what could happen next"
"what we don't know"
content opportunity sections
analysis labels
extra commentary

The output must contain ONLY:

CATEGORY
ANGLE
DRAFT
SOURCE
"""


    user_prompt = f"""
SOURCE NAME:
{item.get('source', '')}

TITLE:
{item.get('title', '')}

SOURCE INFORMATION:
{item.get('text', '')[:5000]}

ORIGINAL SOURCE URL:
{item.get('url', '')}

Create the editorial feed now.
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
                1200,

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
                "[GROQ ERROR] Empty content"
            )
            return None

        print(
            "[GROQ] Editorial generated"
        )

        return parse_groq_output(
            content
        )

    except Exception as exc:

        print(
            f"[GROQ ERROR] {exc}"
        )

        return None


# ============================================================
# GROQ PARSER
# ============================================================

def parse_groq_output(text):

    text = text.strip()

    upper = text.upper()

    category_pos = upper.find(
        "CATEGORY"
    )

    angle_pos = upper.find(
        "ANGLE"
    )

    draft_pos = upper.find(
        "DRAFT"
    )

    source_pos = upper.find(
        "SOURCE"
    )

    if (
        category_pos == -1
        or angle_pos == -1
        or draft_pos == -1
        or source_pos == -1
    ):

        print(
            "[GROQ PARSER] Required sections missing"
        )

        print(
            text[:1500]
        )

        return None

    category = text[
        category_pos + len("CATEGORY"):
        angle_pos
    ].strip(
        " :\n"
    )

    angle = text[
        angle_pos + len("ANGLE"):
        draft_pos
    ].strip(
        " :\n"
    )

    draft = text[
        draft_pos + len("DRAFT"):
        source_pos
    ].strip(
        " :\n"
    )

    source = text[
        source_pos + len("SOURCE"):
    ].strip(
        " :\n"
    )

    if not category:
        return None

    if not angle:
        return None

    if not draft:
        return None

    # Always use the real URL supplied by the collector.
    # This prevents Groq from accidentally inventing
    # or altering the source URL.
    return {

        "category":
            category,

        "angle":
            angle,

        "draft":
            draft,

        "source":
            source
    }


# ============================================================
# TELEGRAM FORMAT
# ============================================================

def format_message(
    item,
    editorial
):

    source_url = item.get(
        "url",
        ""
    )

    return (
        "🧠 WEB3STATION\n\n"

        "CATEGORY\n"
        f"{editorial.get('category', '')}\n\n"

        "ANGLE\n"
        f"{editorial.get('angle', '')}\n\n"

        "DRAFT\n"
        f"{editorial.get('draft', '')}\n\n"

        "SOURCE\n"
        f"{source_url}"
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

    ]

    all_items = []

    for name, function in collectors:

        print(
            "\n======================================"
        )

        print(
            f"[COLLECTING] {name}"
        )

        try:

            items = function()

            print(
                f"[{name}] "
                f"{len(items)} signals found"
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
# MAIN
# ============================================================

def main():

    print(
        "\n======================================"
    )

    print(
        "WEB3STATION"
    )

    print(
        "REAL CRYPTO CONTENT RADAR"
    )

    print(
        now()
    )

    print(
        "======================================\n"
    )


    # --------------------------------------------------------
    # CHECK TELEGRAM FIRST
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


    # --------------------------------------------------------
    # LOAD STATE
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

    all_items = collect_all()

    print(
        "\n======================================"
    )

    print(
        f"TOTAL SIGNALS FOUND: "
        f"{len(all_items)}"
    )

    print(
        "======================================"
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

        item["_score"] = relevance_score(
            item
        )

        unique.append(
            item
        )


    # --------------------------------------------------------
    # SORT STRONGER SIGNALS FIRST
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
        f"NEW UNSENT SIGNALS: "
        f"{len(unique)}"
    )


    # --------------------------------------------------------
    # PROCESS EVERY NEW SIGNAL
    # --------------------------------------------------------

    successful_ids = []

    for index, item in enumerate(
        unique,
        start=1
    ):

        print(
            "\n--------------------------------------"
        )

        print(
            f"PROCESSING "
            f"{index}/{len(unique)}"
        )

        print(
            f"SOURCE: "
            f"{item.get('source')}"
        )

        print(
            f"TITLE: "
            f"{item.get('title')}"
        )

        print(
            f"SCORE: "
            f"{item.get('_score', 0)}"
        )


        # ----------------------------------------------------
        # VERY WEAK SIGNALS
        # ----------------------------------------------------

        if item.get(
            "_score",
            0
        ) < 2:

            print(
                "[SKIP] Signal below relevance threshold"
            )

            # Important:
            # Do NOT mark weak signals as seen.
            # They can be reconsidered later if
            # the collector/source changes.
            continue


        # ----------------------------------------------------
        # GROQ
        # ----------------------------------------------------

        editorial = groq_edit(
            item
        )

        if not editorial:

            print(
                "[RETRY LATER] Groq failed"
            )

            # Do NOT mark as seen.
            continue


        # ----------------------------------------------------
        # TELEGRAM
        # ----------------------------------------------------

        message = format_message(
            item,
            editorial
        )


        # Telegram maximum safe size
        if len(message) > 4000:

            message = (
                message[:3950]
                + "\n\n[truncated]"
            )


        sent = send_telegram(
            message
        )


        # ----------------------------------------------------
        # ONLY SUCCESSFUL TELEGRAM SENDS
        # BECOME SEEN
        # ----------------------------------------------------

        if sent:

            print(
                "[SUCCESS] Signal delivered to Telegram"
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
                "[FAILED] Telegram delivery failed"
            )

            print(
                "[RETRY] Signal remains unseen"
            )


    # --------------------------------------------------------
    # SAVE SUCCESSFUL SIGNALS
    # --------------------------------------------------------

    for item_id in successful_ids:

        seen.add(
            item_id
        )


    save_json(
        SEEN_FILE,
        list(seen)[-10000:]
    )


    save_json(
        TOPIC_FILE,
        topic_history[-1000:]
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
        f"Signals collected: "
        f"{len(all_items)}"
    )

    print(
        f"New signals: "
        f"{len(unique)}"
    )

    print(
        f"Successfully sent: "
        f"{len(successful_ids)}"
    )

    print(
        f"Remaining for retry: "
        f"{len(unique) - len(successful_ids)}"
    )

    print(
        "======================================"
    )


if __name__ == "__main__":
    main()
