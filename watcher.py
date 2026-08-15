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
SORSA_API_KEY = os.getenv("SORSA_API_KEY", "")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
)

TRACKED_X_ACCOUNTS = [
    x.strip().lstrip("@")
    for x in os.getenv(
        "TRACKED_X_ACCOUNTS",
        ""
    ).split(",")
    if x.strip()
]

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
    "User-Agent": "Web3Station-X-Watcher/2.0"
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

        # Keep the state manageable.
        # 10,000 tweet IDs is plenty for
        # duplicate protection.

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

        if response.status_code == 429:

            print(
                "[TWITTERAPIS] "
                "Rate limited"
            )

            return None

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
            f"[SORSA] "
            f"{len(tweets)} posts"
        )

        return tweets

    except Exception as exc:

        print(
            f"[SORSA ERROR] {exc}"
        )

        return []


# ============================================================
# EXTRACT TWITTERAPIS TWEETS
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
# NORMALIZE TWITTERAPIS TWEET
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
        or tweet.get(
            "name",
            username
        )
    )

    created_at = tweet.get(
        "created_at",
        ""
    )

    username = str(
        username or ""
    ).lstrip("@")

    tweet_id = str(
        tweet_id
    )

    return {

        "id":
            tweet_id,

        "text":
            text,

        "username":
            username,

        "name":
            str(name or ""),

        "created_at":
            created_at,

        "url":
            f"https://x.com/"
            f"{username}/status/"
            f"{tweet_id}",

        "provider":
            "TwitterAPIs"

    }


# ============================================================
# NORMALIZE SORSA TWEET
# ============================================================

def normalize_sorsa_tweet(
    tweet
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
        tweet.get(
            "created_at",
            ""
        )
    )

    username = str(
        username or ""
    ).lstrip("@")

    tweet_id = str(
        tweet_id
    )

    return {

        "id":
            tweet_id,

        "text":
            text,

        "username":
            username,

        "name":
            str(name or ""),

        "created_at":
            created_at,

        "url":
            f"https://x.com/"
            f"{username}/status/"
            f"{tweet_id}",

        "provider":
            "Sorsa"

    }


# ============================================================
# FETCH ACCOUNT FROM TWITTERAPIS
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
            "username":
                username
        }
    )

    if not data:

        print(
            "[TWITTERAPIS ACCOUNT] "
            "no response"
        )

        return []

    tweets = extract_tweets(
        data
    )

    results = []

    for tweet in tweets:

        normalized = (
            normalize_twitterapis_tweet(
                tweet,
                username
            )
        )

        if normalized:

            results.append(
                normalized
            )

    print(
        f"[TWITTERAPIS ACCOUNT] "
        f"{len(results)} posts"
    )

    return results


# ============================================================
# FETCH ACCOUNT FROM SORSA
# ============================================================

def fetch_account_sorsa(
    username
):

    query = (
        f"from:{username}"
    )

    raw_tweets = sorsa_search(
        query,
        order="latest"
    )

    results = []

    for tweet in raw_tweets:

        normalized = (
            normalize_sorsa_tweet(
                tweet
            )
        )

        if normalized:

            results.append(
                normalized
            )

    print(
        f"[SORSA ACCOUNT] "
        f"@{username}: "
        f"{len(results)} posts"
    )

    return results


# ============================================================
# FETCH SEARCH FROM TWITTERAPIS
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
            "query":
                query,

            "product":
                "Latest"
        }
    )

    if not data:

        return []

    tweets = extract_tweets(
        data
    )

    results = []

    for tweet in tweets:

        normalized = (
            normalize_twitterapis_tweet(
                tweet
            )
        )

        if normalized:

            results.append(
                normalized
            )

    print(
        f"[TWITTERAPIS SEARCH] "
        f"{len(results)} posts"
    )

    return results


# ============================================================
# FETCH SEARCH FROM SORSA
# ============================================================

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
            normalize_sorsa_tweet(
                tweet
            )
        )

        if normalized:

            results.append(
                normalized
            )

    print(
        f"[SORSA SEARCH] "
        f"{len(results)} posts"
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
human social-media content.

The result must sound like a real,
intelligent crypto writer thinking
through an idea.

Do NOT sound like:

- an AI news summary
- a press release
- a corporate marketing team
- a generic crypto influencer
- a content farm
- a chatbot

Do not simply paraphrase the original post.

Find the idea underneath it.

The draft should have an actual point.

STYLE VARIATION

Choose naturally based on the subject.

Possible modes include:

- educational
- explanatory
- analytical
- my take
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

Do not announce the mode.

Do not use the same style repeatedly.

Sometimes start directly.

Sometimes start with a question.

Sometimes start with an observation.

Sometimes build from a small detail.

Sometimes explain the concept from first principles.

Sometimes make a comparison.

Sometimes use contrast.

Sometimes use a short sentence
followed by a longer thought.

Sometimes use understated humor.

Sometimes use a literary device when
it genuinely improves the writing.

Useful literary techniques include:

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

Do not force literary language.

The writing should still sound like someone
who spends time on crypto and technology.

PERSONAL VOICE

You may sometimes use expressions such as:

"my take:"

"what stands out to me is..."

"the part people may miss is..."

"i think the more interesting question is..."

"there's a bigger story here."

But do NOT use these repeatedly.

If you use "my take", it represents an
editorial viewpoint, not a claim that the
writer personally witnessed the event.

FACTUAL RULES

Never invent:

- facts
- numbers
- partnerships
- people
- quotes
- funding
- product features
- dates
- technical capabilities

Do not turn speculation into fact.

Do not claim the writer personally
experienced something unless the source
supports it.

If something is uncertain, write about
the uncertainty.

DEPTH

Do not make every draft short.

Some posts should be concise.

Some should develop the idea across
multiple paragraphs.

Some should teach something.

Some should explain why a development
matters.

Some should examine a second-order effect.

Some should challenge the obvious
interpretation.

Vary the length naturally.

Do not pad the draft.

Do not repeat the same idea.

Do not use unnecessary hashtags.

Do not use excessive emojis.

Avoid corporate PR language.

Never casually use:

"game changer"
"revolutionary"
"the future is here"
"this is huge"
"mass adoption is coming"
"paradigm shift"

unless discussing those phrases critically.

The final draft should be useful enough
that a crypto reader would want to stop
and read it.

OUTPUT

Return EXACTLY:

CATEGORY:
one concise category

ANGLE:
one or two sentences describing
the editorial angle

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

PROVIDER:
{tweet.get('provider', '')}

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
            timeout=90
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

        choices = data.get(
            "choices",
            []
        )

        if not choices:

            print(
                "[GROQ] no choices"
            )

            return None

        content = (
            choices[0]
            .get("message", {})
            .get("content", "")
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
# TELEGRAM FORMAT
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

    # --------------------------------------------------------
    # PROVIDER STATUS
    # --------------------------------------------------------

    print(
        "\nPROVIDERS"
    )

    print(
        f"TwitterAPIs: "
        f"{'configured' if TWITTERAPIS_KEY else 'not configured'}"
    )

    print(
        f"Sorsa: "
        f"{'configured' if SORSA_API_KEY else 'not configured'}"
    )

    print(
        f"Groq: "
        f"{'configured' if GROQ_API_KEY else 'not configured'}"
    )

    print(
        f"Telegram: "
        f"{'configured' if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID else 'not configured'}"
    )

    # At least one X provider must exist.

    if (
        not TWITTERAPIS_KEY
        and not SORSA_API_KEY
    ):

        print(
            "ERROR: "
            "No X provider API key configured."
        )

        return

    # --------------------------------------------------------
    # INPUT STATUS
    # --------------------------------------------------------

    print(
        f"\nTRACKED ACCOUNTS: "
        f"{len(TRACKED_X_ACCOUNTS)}"
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
    # TRACKED ACCOUNTS
    # ========================================================

    for username in TRACKED_X_ACCOUNTS:

        print(
            "\n======================================"
        )

        print(
            f"ACCOUNT: @{username}"
        )

        # TwitterAPIs

        if TWITTERAPIS_KEY:

            tweets = (
                fetch_account_twitterapis(
                    username
                )
            )

            all_tweets.extend(
                tweets
            )

        # Sorsa

        if SORSA_API_KEY:

            tweets = (
                fetch_account_sorsa(
                    username
                )
            )

            all_tweets.extend(
                tweets
            )

    # ========================================================
    # SEARCH QUERIES
    # ========================================================

    for query in X_SEARCH_QUERIES:

        print(
            "\n======================================"
        )

        print(
            f"SEARCH: {query}"
        )

        # TwitterAPIs

        if TWITTERAPIS_KEY:

            tweets = (
                fetch_search_twitterapis(
                    query
                )
            )

            all_tweets.extend(
                tweets
            )

        # Sorsa

        if SORSA_API_KEY:

            tweets = (
                fetch_search_sorsa(
                    query
                )
            )

            all_tweets.extend(
                tweets
            )

    # ========================================================
    # TOTAL
    # ========================================================

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
            tweet.get(
                "id",
                ""
            )
        )

        if not tweet_id:
            continue

        if tweet_id in unique:

            # Prefer Sorsa if the same tweet
            # was returned by both providers.

            if (
                tweet.get("provider")
                == "Sorsa"
            ):

                unique[
                    tweet_id
                ] = tweet

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

    # ========================================================
    # NEW POSTS
    # ========================================================

    new_tweets = []

    for tweet in tweets:

        tweet_id = str(
            tweet["id"]
        )

        if tweet_id in seen:

            continue

        new_tweets.append(
            tweet
        )

    print(
        f"NEW POSTS: "
        f"{len(new_tweets)}"
    )

    # ========================================================
    # PROCESS EVERY NEW POST
    # ========================================================

    sent_count = 0

    # Newest first when timestamps are available.
    # If timestamps aren't parseable, preserve
    # provider order.

    def sort_key(tweet):

        return str(
            tweet.get(
                "created_at",
                ""
            )
        )

    new_tweets.sort(
        key=sort_key,
        reverse=True
    )

    for tweet in new_tweets:

        print(
            "\n--------------------------------------"
        )

        print(
            f"PROVIDER: "
            f"{tweet.get('provider')}"
        )

        print(
            f"ACCOUNT: "
            f"@{tweet.get('username')}"
        )

        print(
            f"POST: "
            f"{tweet.get('text', '')[:700]}"
        )

        editorial = groq_edit(
            tweet
        )

        if not editorial:

            print(
                "[SKIP] "
                "Editorial generation failed."
            )

            # DO NOT mark as seen.
            # Retry on the next run.

            continue

        message = format_message(
            tweet,
            editorial
        )

        # Telegram limit safety.

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
                str(tweet["id"])
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
