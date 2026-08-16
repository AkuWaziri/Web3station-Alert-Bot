import os
import json
import hashlib
import requests
from datetime import datetime, timezone, timedelta


# ============================================================
# CONFIG
# ============================================================

TWITTERAPIS_KEY = os.getenv("TWITTERAPIS_KEY", "")
SORSA_API_KEY = os.getenv("SORSA_API_KEY", "")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# IMPORTANT:
# GitHub secret must be named TRACKED_X_ACCOUNTS
TRACKED_X_ACCOUNTS = [
    x.strip().lstrip("@")
    for x in os.getenv("TRACKED_X_ACCOUNTS", "").split(",")
    if x.strip()
]

X_SEARCH_QUERIES = [
    x.strip()
    for x in os.getenv("X_SEARCH_QUERIES", "").split(",")
    if x.strip()
]

SEEN_FILE = "x_seen_ids.json"

# Do not process posts older than this.
MAX_POST_AGE_HOURS = 24

# Search results are intentionally limited to avoid flooding Telegram.
MAX_SEARCH_POSTS_PER_QUERY = 5

# Tracked accounts get priority.
MAX_ACCOUNT_POSTS_PER_ACCOUNT = 10


# ============================================================
# NICHE FILTER
# ============================================================

NICHE_TERMS = [
    "crypto",
    "web3",
    "defi",
    "stablecoin",
    "stablecoins",
    "usdc",
    "usdt",
    "payments",
    "payment",
    "crypto payments",
    "onchain",
    "on-chain",
    "wallet",
    "wallets",
    "rwa",
    "real world assets",
    "tokenization",
    "tokenisation",
    "ai agent",
    "ai agents",
    "agentic",
    "agentic commerce",
    "ai crypto",
    "token",
    "remittance",
    "financial infrastructure",
    "onchain finance",
    "crypto infrastructure",
    "institutional crypto",
    "crypto regulation",
]


# ============================================================
# SESSION
# ============================================================

SESSION = requests.Session()

SESSION.headers.update({
    "User-Agent": "Web3Station-X-Watcher/3.0"
})


# ============================================================
# BASIC HELPERS
# ============================================================

def now():
    return datetime.now(timezone.utc).isoformat()


def clean_text(value):
    if not value:
        return ""

    return " ".join(
        str(value)
        .replace("\n", " ")
        .split()
    ).strip()


def make_id(*parts):
    raw = "|".join(
        str(x)
        for x in parts
        if x is not None
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def is_niche_relevant(text):
    text = clean_text(text).lower()

    return any(
        term in text
        for term in NICHE_TERMS
    )


def is_tracked_account(username):
    username = str(
        username or ""
    ).lstrip("@").lower()

    return username in {
        account.lower()
        for account in TRACKED_X_ACCOUNTS
    }


# ============================================================
# DATE HANDLING
# ============================================================

def parse_date(value):

    if not value:
        return None

    value = str(value).strip()

    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%a %b %d %H:%M:%S %z %Y",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
    ]

    for fmt in formats:

        try:

            dt = datetime.strptime(
                value,
                fmt
            )

            if dt.tzinfo is None:
                dt = dt.replace(
                    tzinfo=timezone.utc
                )

            return dt.astimezone(
                timezone.utc
            )

        except ValueError:
            continue

    return None


def is_fresh(tweet):

    created = parse_date(
        tweet.get("created_at", "")
    )

    # If provider gives no usable date,
    # don't automatically reject the post.
    if created is None:
        return True

    age = (
        datetime.now(timezone.utc)
        - created
    )

    return age <= timedelta(
        hours=MAX_POST_AGE_HOURS
    )


# ============================================================
# STATE
# ============================================================

def load_seen():

    try:

        with open(
            SEEN_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

            if isinstance(data, list):

                return set(
                    str(x)
                    for x in data
                )

            if isinstance(data, dict):

                return set(
                    str(x)
                    for x in data.get(
                        "ids",
                        []
                    )
                )

    except FileNotFoundError:

        print(
            "[STATE] no existing state file"
        )

    except Exception as exc:

        print(
            f"[STATE ERROR] {exc}"
        )

    return set()


def save_seen(seen):

    try:

        ids = list(seen)[-10000:]

        with open(
            SEEN_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                ids,
                f,
                indent=2
            )

        print(
            f"[STATE] saved {len(ids)} IDs"
        )

    except Exception as exc:

        print(
            f"[STATE ERROR] {exc}"
        )


# ============================================================
# TWITTERAPIS
# ============================================================

TWITTERAPIS_BASE = (
    "https://api.twitterapis.com/twitter"
)


def twitterapis_get(
    endpoint,
    params=None
):

    if not TWITTERAPIS_KEY:

        print(
            "[TWITTERAPIS] key not configured"
        )

        return None

    url = (
        TWITTERAPIS_BASE
        + endpoint
    )

    headers = {
        "Authorization":
            f"Bearer {TWITTERAPIS_KEY}"
    }

    try:

        response = SESSION.get(
            url,
            headers=headers,
            params=params or {},
            timeout=30
        )

        print(
            f"[TWITTERAPIS] "
            f"{response.status_code} "
            f"{endpoint}"
        )

        if response.status_code == 200:
            return response.json()

        if response.status_code == 401:
            print(
                "[TWITTERAPIS] Invalid API key"
            )

        elif response.status_code == 402:
            print(
                "[TWITTERAPIS] API credits exhausted"
            )

        elif response.status_code == 429:
            print(
                "[TWITTERAPIS] Rate limited"
            )

        else:
            print(
                response.text[:1000]
            )

    except Exception as exc:

        print(
            f"[TWITTERAPIS ERROR] {exc}"
        )

    return None


# ============================================================
# SORSA
# ============================================================

SORSA_SEARCH_URL = (
    "https://api.sorsa.io/v3/search-tweets"
)


def sorsa_search(
    query,
    order="latest"
):

    if not SORSA_API_KEY:

        print(
            "[SORSA] key not configured"
        )

        return []

    print(
        f"[SORSA SEARCH] {query}"
    )

    headers = {
        "ApiKey":
            SORSA_API_KEY,

        "Content-Type":
            "application/json"
    }

    payload = {
        "query":
            query,

        "order":
            order
    }

    try:

        response = SESSION.post(
            SORSA_SEARCH_URL,
            headers=headers,
            json=payload,
            timeout=30
        )

        print(
            f"[SORSA] "
            f"{response.status_code}"
        )

        if response.status_code == 401:

            print(
                "[SORSA] Invalid API key"
            )

            return []

        if response.status_code == 402:

            print(
                "[SORSA] API credits exhausted"
            )

            return []

        if response.status_code == 429:

            print(
                "[SORSA] Rate limited"
            )

            return []

        if not response.ok:

            print(
                response.text[:1000]
            )

            return []

        data = response.json()

        tweets = data.get(
            "tweets",
            []
        )

        if not isinstance(
            tweets,
            list
        ):

            return []

        print(
            f"[SORSA] {len(tweets)} posts"
        )

        return tweets

    except Exception as exc:

        print(
            f"[SORSA ERROR] {exc}"
        )

        return []


# ============================================================
# EXTRACT
# ============================================================

def extract_tweets(data):

    if not isinstance(
        data,
        dict
    ):

        return []

    for key in [
        "tweets",
        "data",
        "results"
    ]:

        value = data.get(key)

        if isinstance(
            value,
            list
        ):

            return value

    return []


# ============================================================
# NORMALIZE TWITTERAPIS
# ============================================================

def normalize_twitterapis_tweet(
    tweet,
    fallback_username=""
):

    if not isinstance(
        tweet,
        dict
    ):

        return None

    tweet_id = (
        tweet.get("id")
        or tweet.get("tweet_id")
    )

    if not tweet_id:
        return None

    text = clean_text(
        tweet.get(
            "text",
            tweet.get(
                "full_text",
                ""
            )
        )
    )

    if not text:
        return None

    author = tweet.get(
        "author",
        {}
    )

    if not isinstance(
        author,
        dict
    ):
        author = {}

    username = (
        author.get("username")
        or tweet.get("username")
        or fallback_username
    )

    name = (
        author.get("name")
        or tweet.get("name")
        or username
    )

    created_at = (
        tweet.get("created_at")
        or tweet.get("createdAt")
        or ""
    )

    username = str(
        username or ""
    ).lstrip("@")

    tweet_id = str(
        tweet_id
    )

    return {
        "id": tweet_id,
        "text": text,
        "username": username,
        "name": str(name or ""),
        "created_at": created_at,
        "url":
            f"https://x.com/"
            f"{username}/status/"
            f"{tweet_id}",
        "provider": "TwitterAPIs"
    }


# ============================================================
# NORMALIZE SORSA
# ============================================================

def normalize_sorsa_tweet(tweet):

    if not isinstance(
        tweet,
        dict
    ):
        return None

    tweet_id = (
        tweet.get("id")
        or tweet.get("tweet_id")
    )

    if not tweet_id:
        return None

    text = clean_text(
        tweet.get(
            "full_text",
            tweet.get(
                "text",
                ""
            )
        )
    )

    if not text:
        return None

    user = tweet.get(
        "user",
        {}
    )

    if not isinstance(
        user,
        dict
    ):
        user = {}

    username = (
        user.get("username")
        or tweet.get("username")
        or ""
    )

    name = (
        user.get("display_name")
        or user.get("name")
        or tweet.get("name")
        or username
    )

    created_at = (
        tweet.get("created_at")
        or tweet.get("createdAt")
        or ""
    )

    username = str(
        username or ""
    ).lstrip("@")

    tweet_id = str(
        tweet_id
    )

    return {
        "id": tweet_id,
        "text": text,
        "username": username,
        "name": str(name or ""),
        "created_at": created_at,
        "url":
            f"https://x.com/"
            f"{username}/status/"
            f"{tweet_id}",
        "provider": "Sorsa"
    }


# ============================================================
# ACCOUNT FETCH
# ============================================================

def fetch_account_twitterapis(
    username
):

    print(
        f"\n[TWITTERAPIS ACCOUNT] "
        f"@{username}"
    )

    data = twitterapis_get(
        "/user/tweets",
        params={
            "username": username
        }
    )

    if not data:
        return []

    tweets = extract_tweets(data)

    results = []

    for tweet in tweets:

        normalized = (
            normalize_twitterapis_tweet(
                tweet,
                username
            )
        )

        if not normalized:
            continue

        if not is_fresh(normalized):
            continue

        # Tracked accounts are still subject
        # to niche filtering.
        if not is_niche_relevant(
            normalized["text"]
        ):
            continue

        results.append(
            normalized
        )

        if len(results) >= MAX_ACCOUNT_POSTS_PER_ACCOUNT:
            break

    print(
        f"[TWITTERAPIS ACCOUNT] "
        f"usable posts: {len(results)}"
    )

    return results


def fetch_account_sorsa(
    username
):

    query = f"from:{username}"

    raw_tweets = sorsa_search(
        query,
        order="latest"
    )

    results = []

    for tweet in raw_tweets:

        normalized = (
            normalize_sorsa_tweet(tweet)
        )

        if not normalized:
            continue

        if not is_fresh(normalized):
            continue

        if not is_niche_relevant(
            normalized["text"]
        ):
            continue

        # Ensure this really belongs
        # to the tracked account.
        if (
            normalized["username"]
            and
            normalized["username"].lower()
            != username.lower()
        ):
            continue

        results.append(
            normalized
        )

        if len(results) >= MAX_ACCOUNT_POSTS_PER_ACCOUNT:
            break

    print(
        f"[SORSA ACCOUNT] "
        f"@{username}: "
        f"{len(results)} usable posts"
    )

    return results


# ============================================================
# SEARCH
# ============================================================

def fetch_search_twitterapis(
    query
):

    print(
        f"\n[TWITTERAPIS SEARCH] "
        f"{query}"
    )

    data = twitterapis_get(
        "/tweet/advanced_search",
        params={
            "query": query,
            "product": "Latest"
        }
    )

    if not data:
        return []

    tweets = extract_tweets(data)

    results = []

    for tweet in tweets:

        normalized = (
            normalize_twitterapis_tweet(
                tweet
            )
        )

        if not normalized:
            continue

        if not is_fresh(normalized):
            continue

        if not is_niche_relevant(
            normalized["text"]
        ):
            continue

        results.append(
            normalized
        )

        if len(results) >= MAX_SEARCH_POSTS_PER_QUERY:
            break

    print(
        f"[TWITTERAPIS SEARCH] "
        f"usable posts: {len(results)}"
    )

    return results


def fetch_search_sorsa(
    query
):

    raw_tweets = sorsa_search(
        query,
        order="latest"
    )

    results = []

    for tweet in raw_tweets:

        normalized = (
            normalize_sorsa_tweet(tweet)
        )

        if not normalized:
            continue

        if not is_fresh(normalized):
            continue

        if not is_niche_relevant(
            normalized["text"]
        ):
            continue

        results.append(
            normalized
        )

        if len(results) >= MAX_SEARCH_POSTS_PER_QUERY:
            break

    print(
        f"[SORSA SEARCH] "
        f"usable posts: {len(results)}"
    )

    return results


# ============================================================
# GROQ
# ============================================================

def groq_edit(tweet):

    if not GROQ_API_KEY:

        print(
            "[GROQ ERROR] GROQ_API_KEY missing"
        )

        return None

    system_prompt = """
You are the senior editorial writer for
Web3Station, a serious crypto and technology
intelligence feed.

Turn the supplied fresh X post into a useful,
human-sounding social-media draft.

The draft must sound written by an intelligent
human who understands crypto, technology,
markets and internet culture.

Do not sound like an AI summary.

Do not simply paraphrase the source.

Find the underlying idea and develop it.

==================================================
WRITING STYLE
==================================================

Choose ONE style naturally based on the source.

Possible styles:

Professional and formal
Casual and friendly
Educational
Explanatory
Analytical
My take
Curious
Skeptical
Assertive
Optimistic
Worried
Encouraging
Surprised
Leadership
Builder-focused
Investor-focused
Technical
Philosophical
Observational
Contrarian
Narrative
Creative and character-driven
Protagonist-style
Comparative
Historical
Provocative

Do not tell the reader which style you selected.

Do not use the same opening pattern repeatedly.

Sometimes begin with:

a question
an observation
a surprising detail
a contrast
a direct statement
a short story
a technical explanation
a strong opinion

Sometimes use:

metaphor
analogy
contrast
irony
rhythm
repetition
understatement
rhetorical questions
narrative progression

Use these only when natural.

Do not make every post poetic.

==================================================
HUMAN WRITING
==================================================

Use natural sentence rhythm.

Mix short and medium sentences.

Do not make every sentence the same length.

Avoid generic AI phrases.

Avoid:

"this is a game changer"
"revolutionary"
"the future is here"
"this is huge"
"mass adoption is coming"
"paradigm shift"
"the crypto landscape is evolving"

unless directly discussing those phrases.

Do not force enthusiasm.

Do not force negativity.

Do not use excessive emojis.

Do not use unnecessary hashtags.

Do not use corporate PR language.

Do not sound like a news headline.

==================================================
LENGTH
==================================================

The DRAFT must be medium length.

Target approximately 70-150 words.

It can be shorter when the source is simple.

It can be slightly longer when explanation
is necessary.

Do not pad the writing.

Do not repeat the same point.

==================================================
EDITORIAL DEPTH
==================================================

Depending on the source, the draft may:

teach the reader something

explain why the development matters

identify a second-order effect

challenge the obvious interpretation

connect two ideas

highlight an overlooked detail

compare it with an existing model

explain the infrastructure underneath it

discuss an opportunity

discuss a risk

make a reasoned prediction

give an editorial viewpoint

But never invent information.

==================================================
FACTUAL RULES
==================================================

Never invent:

facts
numbers
dates
people
quotes
funding
partnerships
products
technical capabilities
events

Never turn speculation into fact.

If the source is speculative,
keep the draft speculative.

If the source is uncertain,
preserve that uncertainty.

Do not claim personal experience.

==================================================
CATEGORY
==================================================

Use a concise category such as:

AI x Crypto Infrastructure
Stablecoin Payments
Onchain Finance
RWA & Tokenization
Crypto Infrastructure
DeFi
Bitcoin
Ethereum
Solana
Wallets
Crypto Regulation
Security
NFTs
AI Agents
Developer Ecosystem
Crypto Markets

Choose the category that best fits the source.

==================================================
ANGLE
==================================================

Write one or two concise sentences explaining
what makes the source interesting.

The angle should NOT merely repeat the headline.

==================================================
OUTPUT
==================================================

Return EXACTLY:

CATEGORY:
...

ANGLE:
...

DRAFT:
...

Nothing before CATEGORY.

Nothing after the DRAFT.
"""

    user_prompt = f"""
SOURCE ACCOUNT:
@{tweet.get('username', '')}

AUTHOR:
{tweet.get('name', '')}

ORIGINAL X POST:
{tweet.get('text', '')}

POST DATE:
{tweet.get('created_at', '')}

SOURCE PROVIDER:
{tweet.get('provider', '')}

SOURCE URL:
{tweet.get('url', '')}
"""

    url = (
        "https://api.groq.com/openai/v1/"
        "chat/completions"
    )

    try:

        response = SESSION.post(
            url,
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
                    0.9,

                "max_tokens":
                    650,

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
            },
            timeout=90
        )

        print(
            f"[GROQ] {response.status_code}"
        )

        if not response.ok:

            print(
                response.text[:1500]
            )

            return None

        data = response.json()

        choices = data.get(
            "choices",
            []
        )

        if not choices:
            return None

        content = (
            choices[0]
            .get("message", {})
            .get("content", "")
        )

        if not content:
            return None

        return parse_groq(
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

    if (
        category_pos == -1
        or angle_pos == -1
        or draft_pos == -1
    ):

        print(
            "[GROQ PARSE ERROR]"
        )

        print(
            text[:1500]
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

    if not category or not angle or not draft:
        return None

    return {
        "category": category,
        "angle": angle,
        "draft": draft
    }


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):

    if not TELEGRAM_TOKEN:

        print(
            "[TELEGRAM ERROR] "
            "TELEGRAM_TOKEN missing"
        )

        return False

    if not TELEGRAM_CHAT_ID:

        print(
            "[TELEGRAM ERROR] "
            "TELEGRAM_CHAT_ID missing"
        )

        return False

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/sendMessage"
    )

    try:

        response = requests.post(
            url,
            json={
                "chat_id":
                    TELEGRAM_CHAT_ID,

                "text":
                    message,

                "disable_web_page_preview":
                    False
            },
            timeout=30
        )

        print(
            f"[TELEGRAM] "
            f"{response.status_code}"
        )

        if response.ok:

            print(
                "[TELEGRAM] SENT"
            )

            return True

        print(
            response.text[:1500]
        )

    except Exception as exc:

        print(
            f"[TELEGRAM ERROR] {exc}"
        )

    return False


# ============================================================
# TELEGRAM FORMAT
# ============================================================

def format_message(
    tweet,
    editorial
):

    return (
        "CATEGORY\n"
        f"{editorial['category']}\n\n"

        "ANGLE\n"
        f"{editorial['angle']}\n\n"

        "DRAFT\n"
        f"{editorial['draft']}\n\n"

        "SOURCE\n"
        f"{tweet['url']}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n======================================"
    )

    print(
        "WEB3STATION X WATCHER"
    )

    print(
        now()
    )

    print(
        "======================================"
    )

    print("\nPROVIDERS")

    print(
        "TwitterAPIs:",
        "configured"
        if TWITTERAPIS_KEY
        else "not configured"
    )

    print(
        "Sorsa:",
        "configured"
        if SORSA_API_KEY
        else "not configured"
    )

    print(
        "Groq:",
        "configured"
        if GROQ_API_KEY
        else "not configured"
    )

    print(
        "Telegram:",
        "configured"
        if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID
        else "not configured"
    )

    if not TWITTERAPIS_KEY and not SORSA_API_KEY:

        print(
            "\nERROR: No X provider configured."
        )

        return

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:

        print(
            "\nERROR: Telegram is not configured."
        )

        return

    if not GROQ_API_KEY:

        print(
            "\nERROR: Groq is not configured."
        )

        return

    print(
        f"\nTRACKED ACCOUNTS: "
        f"{len(TRACKED_X_ACCOUNTS)}"
    )

    for account in TRACKED_X_ACCOUNTS:

        print(
            f"  @{account}"
        )

    print(
        f"SEARCH QUERIES: "
        f"{len(X_SEARCH_QUERIES)}"
    )

    seen = load_seen()

    print(
        f"[STATE] "
        f"{len(seen)} previously seen posts"
    )

    all_tweets = []

    # ========================================================
    # 1. TRACKED ACCOUNTS
    # ========================================================

    for username in TRACKED_X_ACCOUNTS:

        print(
            "\n======================================"
        )

        print(
            f"TRACKED ACCOUNT: @{username}"
        )

        if TWITTERAPIS_KEY:

            all_tweets.extend(
                fetch_account_twitterapis(
                    username
                )
            )

        if SORSA_API_KEY:

            all_tweets.extend(
                fetch_account_sorsa(
                    username
                )
            )

    # ========================================================
    # 2. SEARCH
    # ========================================================

    for query in X_SEARCH_QUERIES:

        print(
            "\n======================================"
        )

        print(
            f"SEARCH: {query}"
        )

        if TWITTERAPIS_KEY:

            all_tweets.extend(
                fetch_search_twitterapis(
                    query
                )
            )

        if SORSA_API_KEY:

            all_tweets.extend(
                fetch_search_sorsa(
                    query
                )
            )

    print(
        "\n======================================"
    )

    print(
        f"TOTAL POSTS FOUND: "
        f"{len(all_tweets)}"
    )

    # ========================================================
    # DEDUPLICATE
    # ========================================================

    unique = {}

    for tweet in all_tweets:

        tweet_id = str(
            tweet.get("id", "")
        )

        if not tweet_id:
            continue

        if tweet_id not in unique:

            unique[tweet_id] = tweet

        else:

            # Prefer TwitterAPIs for account
            # information when available.
            if (
                tweet.get("provider")
                == "TwitterAPIs"
                and
                unique[tweet_id].get("provider")
                != "TwitterAPIs"
            ):

                unique[tweet_id] = tweet

    tweets = list(
        unique.values()
    )

    print(
        f"UNIQUE POSTS: "
        f"{len(tweets)}"
    )

    # ========================================================
    # NEW POSTS
    # ========================================================

    new_tweets = []

    for tweet in tweets:

        tweet_id = str(
            tweet.get("id", "")
        )

        if not tweet_id:
            continue

        if tweet_id in seen:
            continue

        if not is_fresh(tweet):

            print(
                f"[OLD] skipping "
                f"@{tweet.get('username', '')}"
            )

            continue

        if not is_niche_relevant(
            tweet.get("text", "")
        ):

            print(
                f"[IRRELEVANT] skipping "
                f"@{tweet.get('username', '')}"
            )

            continue

        new_tweets.append(
            tweet
        )

    # ========================================================
    # PRIORITY
    # ========================================================

    # Tracked accounts always come first.
    new_tweets.sort(
        key=lambda tweet: (
            1
            if is_tracked_account(
                tweet.get("username", "")
            )
            else 0,

            parse_date(
                tweet.get(
                    "created_at",
                    ""
                )
            )
            or datetime.min.replace(
                tzinfo=timezone.utc
            )
        ),
        reverse=True
    )

    print(
        f"NEW POSTS: "
        f"{len(new_tweets)}"
    )

    # ========================================================
    # PROCESS
    # ========================================================

    sent_count = 0

    for tweet in new_tweets:

        print(
            "\n--------------------------------------"
        )

        print(
            f"@{tweet.get('username', '')}"
        )

        print(
            f"{tweet.get('provider', '')}"
        )

        print(
            tweet.get(
                "text",
                ""
            )[:500]
        )

        editorial = groq_edit(
            tweet
        )

        if not editorial:

            print(
                "[SKIP] Groq failed"
            )

            continue

        message = format_message(
            tweet,
            editorial
        )

        # Telegram maximum safety.
        if len(message) > 3900:

            print(
                "[TELEGRAM] message too long, truncating"
            )

            message = (
                message[:3900]
                + "\n\n[truncated]"
            )

        sent = send_telegram(
            message
        )

        if sent:

            seen.add(
                str(tweet["id"])
            )

            sent_count += 1

            print(
                "[SUCCESS] "
                "sent and marked as seen"
            )

        else:

            print(
                "[FAILED] "
                "not marked as seen"
            )

    # ========================================================
    # SAVE
    # ========================================================

    save_seen(
        seen
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    print(
        "\n======================================"
    )

    print(
        "X WATCHER COMPLETE"
    )

    print(
        f"Accounts: "
        f"{len(TRACKED_X_ACCOUNTS)}"
    )

    print(
        f"Searches: "
        f"{len(X_SEARCH_QUERIES)}"
    )

    print(
        f"Posts found: "
        f"{len(all_tweets)}"
    )

    print(
        f"Unique posts: "
        f"{len(tweets)}"
    )

    print(
        f"New posts: "
        f"{len(new_tweets)}"
    )

    print(
        f"Telegram feeds sent: "
        f"{sent_count}"
    )

    print(
        "======================================" 
    )


if __name__ == "__main__":
    main()
