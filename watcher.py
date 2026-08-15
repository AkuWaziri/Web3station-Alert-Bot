import os
import json
import time
import hashlib
import requests
from datetime import datetime, timezone


# ============================================================
# CONFIG
# ============================================================

TWITTERAPIS_KEY = os.getenv("TWITTERAPIS_KEY", "")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
)

# ------------------------------------------------------------
# ADD YOUR X ACCOUNTS HERE
#
# Do NOT include @
#
# Example:
#
# TRACKED_X_ACCOUNTS=elonmusk,balajis,base,ethereum
#
# You can also put them directly here.
# ------------------------------------------------------------

TRACKED_X_ACCOUNTS = [
    x.strip().lstrip("@")
    for x in os.getenv(
        "TRACKED_X_ACCOUNTS",
        ""
    ).split(",")
    if x.strip()
]


# ------------------------------------------------------------
# X KEYWORD SEARCHES
#
# These are optional.
#
# Example GitHub secret:
#
# X_SEARCH_QUERIES=
# stablecoin payments,
# "AI agents" crypto,
# tokenization,
# RWA
#
# The watcher will monitor both:
#
# 1. specific accounts
# 2. broader X searches
# ------------------------------------------------------------

X_SEARCH_QUERIES = [
    x.strip()
    for x in os.getenv(
        "X_SEARCH_QUERIES",
        ""
    ).split(",")
    if x.strip()
]


SEEN_FILE = "x_seen_ids.json"


# ============================================================
# SESSION
# ============================================================

SESSION = requests.Session()

SESSION.headers.update({
    "User-Agent": "Web3Station-X-Watcher/1.0"
})


# ============================================================
# HELPERS
# ============================================================

def now():
    return datetime.now(
        timezone.utc
    ).isoformat()


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


def load_seen():
    try:

        with open(
            SEEN_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

            if isinstance(data, list):
                return set(data)

            if isinstance(data, dict):
                return set(
                    data.get(
                        "ids",
                        []
                    )
                )

    except Exception as exc:

        print(
            f"[STATE] no existing state: {exc}"
        )

    return set()


def save_seen(seen):
    try:

        # Keep state reasonably small.
        # The newest 10000 IDs are enough
        # to prevent duplicate alerts.

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
# TWITTERAPIS REQUEST
# ============================================================

BASE_URL = (
    "https://api.twitterapis.com/twitter"
)


def twitter_get(
    endpoint,
    params=None,
    retries=4
):

    if not TWITTERAPIS_KEY:

        print(
            "[TWITTERAPIS ERROR] "
            "TWITTERAPIS_KEY is missing"
        )

        return None

    url = (
        BASE_URL
        + endpoint
    )

    headers = {
        "Authorization":
            f"Bearer {TWITTERAPIS_KEY}"
    }

    for attempt in range(retries):

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
                    "[TWITTERAPIS] "
                    "Invalid API key"
                )

                return None

            if response.status_code == 402:

                print(
                    "[TWITTERAPIS] "
                    "API credits exhausted"
                )

                return None

            if response.status_code == 404:

                print(
                    "[TWITTERAPIS] "
                    "Account/resource not found"
                )

                return None

            if response.status_code == 429:

                wait = 10 * (
                    attempt + 1
                )

                print(
                    f"[TWITTERAPIS] "
                    f"Rate limited. "
                    f"Waiting {wait}s"
                )

                time.sleep(wait)

                continue

            if response.status_code >= 500:

                wait = 5 * (
                    attempt + 1
                )

                print(
                    f"[TWITTERAPIS] "
                    f"Server error. "
                    f"Waiting {wait}s"
                )

                time.sleep(wait)

                continue

            print(
                "[TWITTERAPIS ERROR]"
            )

            print(
                response.text[:1000]
            )

            return None

        except Exception as exc:

            print(
                f"[TWITTERAPIS REQUEST ERROR] "
                f"{exc}"
            )

            if attempt < retries - 1:

                time.sleep(
                    5 * (attempt + 1)
                )

    return None


# ============================================================
# EXTRACT TWEETS
# ============================================================

def extract_tweets(data):

    if not isinstance(
        data,
        dict
    ):
        return []

    possible_keys = [
        "tweets",
        "data",
        "results"
    ]

    for key in possible_keys:

        value = data.get(
            key
        )

        if isinstance(
            value,
            list
        ):

            return value

    return []


# ============================================================
# NORMALIZE TWEET
# ============================================================

def normalize_tweet(
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
        or tweet.get(
            "name",
            username
        )
    )

    created_at = (
        tweet.get(
            "created_at",
            ""
        )
    )

    return {

        "id":
            str(tweet_id),

        "text":
            text,

        "username":
            str(username or ""),

        "name":
            str(name or ""),

        "created_at":
            created_at,

        "url":
            (
                f"https://x.com/"
                f"{username}/status/"
                f"{tweet_id}"
            ),

        "raw":
            tweet

    }


# ============================================================
# FETCH ACCOUNT TIMELINE
# ============================================================

def fetch_account_tweets(
    username
):

    print(
        f"\n[X ACCOUNT] @{username}"
    )

    data = twitter_get(
        "/user/tweets",
        params={
            "username":
                username
        }
    )

    if not data:

        print(
            f"[X ACCOUNT] "
            f"no response for @{username}"
        )

        return []

    tweets = extract_tweets(
        data
    )

    print(
        f"[X ACCOUNT] "
        f"@{username}: "
        f"{len(tweets)} posts"
    )

    results = []

    for tweet in tweets:

        normalized = normalize_tweet(
            tweet,
            username
        )

        if normalized:

            results.append(
                normalized
            )

    return results


# ============================================================
# FETCH X SEARCH
# ============================================================

def fetch_search(
    query
):

    print(
        f"\n[X SEARCH] {query}"
    )

    data = twitter_get(
        "/tweet/advanced_search",
        params={
            "query":
                query,

            "product":
                "Latest"
        }
    )

    if not data:

        print(
            "[X SEARCH] no response"
        )

        return []

    tweets = extract_tweets(
        data
    )

    print(
        f"[X SEARCH] "
        f"{len(tweets)} posts"
    )

    results = []

    for tweet in tweets:

        normalized = normalize_tweet(
            tweet
        )

        if normalized:

            results.append(
                normalized
            )

    return results


# ============================================================
# GROQ EDITOR
# ============================================================

def groq_edit(
    tweet
):

    if not GROQ_API_KEY:

        print(
            "[GROQ ERROR] "
            "GROQ_API_KEY is missing"
        )

        return None

    system_prompt = """
You are the senior editorial writer
for Web3Station.

You turn fresh X posts into strong,
human social-media content ideas.

The writing must NOT sound like an AI
news summary.

It must sound like an intelligent human
crypto writer who has a point of view.

IMPORTANT:

Do not invent facts.

Do not invent numbers.

Do not invent events.

Do not pretend the writer personally
experienced something unless the source
supports it.

Do not copy the original post.

Do not simply paraphrase it.

Find the interesting idea underneath it.

The draft should sometimes be:

- educational
- explanatory
- analytical
- "my take"
- skeptical
- conversational
- observational
- provocative
- technical
- philosophical
- historical
- comparative
- narrative
- contrarian
- curious
- builder-focused
- investor-focused
- market-focused

Choose the style naturally based on the post.

Vary the opening.

Do NOT always begin with:

"this is..."
"the interesting thing..."
"we are seeing..."
"the future..."
"finally..."

Use natural human writing.

Sometimes use short sentences.

Sometimes use longer flowing sentences.

Sometimes use a rhetorical question.

Sometimes use contrast.

Sometimes use an analogy.

Sometimes explain an idea from first principles.

Sometimes make a small observation and build
from it.

Sometimes use understated humor.

Sometimes use a personal-sounding viewpoint
such as:

"my take:"
"what stands out to me:"
"i think the more interesting part is:"
"the part people may miss:"
"there's a bigger question here:"

But do NOT use these in every post.

Literary techniques may be used naturally
when appropriate:

- metaphor
- analogy
- contrast
- irony
- repetition
- rhythm
- understatement
- rhetorical questions
- narrative progression
- vivid but restrained imagery

Do not overdo them.

The result should sound like a person
thinking clearly, not an AI performing
"human writing."

DETAIL:

The draft should be sufficiently developed
to communicate an actual idea.

Do not make every draft short.

Some drafts can be concise.

Others should develop the thought over
multiple paragraphs.

Vary length naturally.

Do not add hashtags unless they are
essential.

Do not use excessive emojis.

Do not use corporate PR language.

Never use:

"game changer"
"revolutionary"
"the future is here"
"this is huge"
"mass adoption is coming"
"paradigm shift"

unless the phrase is being discussed
critically.

Return EXACTLY:

CATEGORY:
one concise category

ANGLE:
one or two sentences explaining the
interesting editorial angle

DRAFT:
the complete social-media draft

Nothing before CATEGORY.

Nothing after the DRAFT.
"""

    user_prompt = f"""
SOURCE ACCOUNT:
@{tweet.get('username', '')}

AUTHOR:
{tweet.get('name', '')}

ORIGINAL POST:
{tweet.get('text', '')}

POST DATE:
{tweet.get('created_at', '')}

SOURCE:
{tweet.get('url', '')}
"""

    url = (
        "https://api.groq.com/openai/v1/"
        "chat/completions"
    )

    headers = {
        "Authorization":
            f"Bearer {GROQ_API_KEY}",

        "Content-Type":
            "application/json"
    }

    payload = {

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

    try:

        response = SESSION.post(
            url,
            headers=headers,
            json=payload,
            timeout=60
        )

        print(
            f"[GROQ] "
            f"{response.status_code}"
        )

        if not response.ok:

            print(
                response.text[:1500]
            )

            return None

        data = response.json()

        content = (
            data
            .get(
                "choices",
                [{}]
            )[0]
            .get(
                "message",
                {}
            )
            .get(
                "content",
                ""
            )
        )

        if not content:

            print(
                "[GROQ] empty response"
            )

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
# PARSE GROQ
# ============================================================

def parse_groq(
    text
):

    text = text.strip()

    upper = text.upper()

    category_marker = (
        "CATEGORY:"
    )

    angle_marker = (
        "ANGLE:"
    )

    draft_marker = (
        "DRAFT:"
    )

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
            text[:2000]
        )

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
# TELEGRAM
# ============================================================

def send_telegram(
    message
):

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

        return False

    except Exception as exc:

        print(
            f"[TELEGRAM ERROR] {exc}"
        )

        return False


# ============================================================
# FORMAT TELEGRAM
# ============================================================

def format_message(
    tweet,
    editorial
):

    return (
        "🧠 WEB3STATION\n\n"

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

    if not TWITTERAPIS_KEY:

        print(
            "ERROR: "
            "TWITTERAPIS_KEY is not configured."
        )

        return

    if not TRACKED_X_ACCOUNTS:

        print(
            "WARNING: "
            "TRACKED_X_ACCOUNTS is empty."
        )

    seen = load_seen()

    print(
        f"[STATE] "
        f"{len(seen)} previously seen posts"
    )

    all_tweets = []

    # --------------------------------------------------------
    # TRACKED ACCOUNTS
    # --------------------------------------------------------

    for username in TRACKED_X_ACCOUNTS:

        tweets = fetch_account_tweets(
            username
        )

        all_tweets.extend(
            tweets
        )

    # --------------------------------------------------------
    # KEYWORD SEARCH
    # --------------------------------------------------------

    for query in X_SEARCH_QUERIES:

        tweets = fetch_search(
            query
        )

        all_tweets.extend(
            tweets
        )

    print(
        f"\nTOTAL X POSTS FOUND: "
        f"{len(all_tweets)}"
    )

    # --------------------------------------------------------
    # DEDUPLICATE
    # --------------------------------------------------------

    unique = {}

    for tweet in all_tweets:

        tweet_id = tweet.get(
            "id"
        )

        if not tweet_id:
            continue

        if tweet_id in unique:
            continue

        unique[
            tweet_id
        ] = tweet

    tweets = list(
        unique.values()
    )

    print(
        f"UNIQUE POSTS: "
        f"{len(tweets)}"
    )

    # --------------------------------------------------------
    # ONLY NEW POSTS
    # --------------------------------------------------------

    new_tweets = []

    for tweet in tweets:

        tweet_id = tweet[
            "id"
        ]

        if tweet_id in seen:

            continue

        new_tweets.append(
            tweet
        )

    print(
        f"NEW POSTS: "
        f"{len(new_tweets)}"
    )

    # --------------------------------------------------------
    # PROCESS EVERY NEW POST
    #
    # IMPORTANT:
    # THERE IS NO "ONE PER SOURCE" LIMIT.
    # EVERY NEW POST IS PROCESSED.
    # --------------------------------------------------------

    sent_count = 0

    for tweet in reversed(
        new_tweets
    ):

        print(
            "\n--------------------------------------"
        )

        print(
            f"@{tweet.get('username')}"
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
                "[SKIP] "
                "Editorial generation failed."
            )

            # IMPORTANT:
            # Do NOT mark as seen.
            # It will be retried next run.

            continue

        message = format_message(
            tweet,
            editorial
        )

        # Telegram maximum message size
        if len(message) > 3900:

            message = (
                message[:3900]
                + "\n\n[truncated]"
            )

        sent = send_telegram(
            message
        )

        if sent:

            seen.add(
                tweet["id"]
            )

            sent_count += 1

            print(
                "[POST] "
                "marked as seen"
            )

        else:

            print(
                "[POST] "
                "NOT marked as seen"
            )

    # --------------------------------------------------------
    # SAVE STATE
    # --------------------------------------------------------

    save_seen(
        seen
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

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
