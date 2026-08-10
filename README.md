# Crypto/NFT Alert Bot

Pushes recent (last 72h) crypto/NFT news, campaigns, hacks, trending coins,
and meme-worthy chatter to Telegram — every 2 hours, for free, via GitHub Actions.

## What it watches
- CoinTelegraph, CoinDesk, Decrypt (RSS)
- Medium crypto/NFT tags (RSS)
- Reddit r/CryptoCurrency, r/NFT, r/CryptoMoonShots (RSS, no login needed)
- CryptoPanic news feed (optional, free API key)
- CoinGecko trending coins

## Setup (5 minutes)

### 1. Create the repo
Push this folder to a new GitHub repository (public or private, doesn't matter).

### 2. Add your secrets
In your repo: **Settings → Secrets and variables → Actions → New repository secret**

Add these three:
| Secret name | Value |
|---|---|
| `TELEGRAM_TOKEN` | your bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | your chat ID (see below) |
| `CRYPTOPANIC_KEY` | optional — free key from cryptopanic.com/developers/api |

**Getting your chat ID:** message your bot on Telegram once, then visit
`https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser and copy
the number after `"chat":{"id":`.

### 3. Enable Actions
Go to the **Actions** tab in your repo, click "I understand my workflows, go ahead
and enable them" if prompted.

### 4. Test it manually
Actions tab → "Crypto Alert Bot" workflow → "Run workflow" button.
Check your Telegram — you should get alerts within ~30 seconds.

### 5. Let it run
It's now scheduled to run automatically every 2 hours. No further action needed.

## Tuning
- Change frequency: edit the `cron` line in `.github/workflows/alert.yml`
  (e.g. `0 */1 * * *` = every hour, `0 */3 * * *` = every 3 hours)
- Add/remove sources: edit the `RSS_FEEDS` dict in `main.py`
- Adjust sensitivity: edit `KEYWORDS_HOT` list in `main.py` — more keywords = more alerts
- Change recency window: edit `RECENCY_HOURS` in `main.py`

## Notes
- `seen_ids.json` is auto-committed after each run to avoid duplicate alerts —
  don't edit it manually.
- GitHub Actions free tier gives 2,000 minutes/month for private repos
  (unlimited for public repos) — this bot uses well under 1 minute per run,
  so you're nowhere near any limit even running hourly.
