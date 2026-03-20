# ChainBounty X Integration

## Goal

Connect `cryptonewsbot` to the ChainBounty X posting flow so one scheduled run can:

1. collect recent crypto security news
2. rewrite each article in the ChainBounty company voice
3. post selected output to X automatically
4. keep Telegram delivery and X delivery histories separate

## Current State

`cryptonewsbot` already provides:

- RSS/Atom news collection
- relevance filtering for ChainBounty-style security stories
- article summarization
- ChainBounty-formatted `GeneratedPost` output
- Telegram delivery
- SQLite persistence for article and Telegram delivery history

`chainbounty-x-automation` already provides:

- X API credentials pattern
- X posting logic via Tweepy
- posted tweet history pattern

## Integration Direction

Keep `cryptonewsbot` as the orchestration entrypoint.

Reason:

- article collection and ChainBounty rewriting already live here
- scheduled runtime and repeat-suppression already live here
- adding X as another delivery channel is simpler than moving article logic into the X automation repo

## Proposed Flow

```text
run_daily_digest()
  -> collect and filter articles
  -> generate ChainBounty posts
  -> send Telegram messages
  -> post selected X messages
  -> persist run, Telegram delivery, X delivery
```

## First Implementation Scope

### In scope

- optional X credentials in `.env`
- optional X posting client in `cryptonewsbot`
- posting generated `body` text as a regular tweet or thread
- persistence for X-delivered article fingerprints and tweet ids
- keeping Telegram and X delivery decisions independent
- CLI support for X test posting

### Out of scope

- reusing the existing tweet-search flow from `chainbounty-x-automation`
- quote-tweeting third-party tweets
- dashboard migration
- Jira automation hooks

## Data Model Changes

Add separate X delivery tracking so Telegram dedupe and X dedupe can evolve independently.

Suggested schema additions:

- `runs.delivered_to_x`
- `generated_posts.x_posted_tweet_id`
- `delivered_x_posts`
  - `run_id`
  - `fingerprint`
  - `canonical_url`
  - `title`
  - `tweet_id`
  - `delivered_at`

## Config Changes

Add optional environment variables:

- `CRYPTO_NEWSBOT_ENABLE_X_POSTING`
- `CRYPTO_NEWSBOT_X_DRY_RUN`
- `CRYPTO_NEWSBOT_X_MAX_POSTS`
- `TWITTER_API_KEY`
- `TWITTER_API_SECRET`
- `TWITTER_ACCESS_TOKEN`
- `TWITTER_ACCESS_TOKEN_SECRET`
- `TWITTER_BEARER_TOKEN`

## Posting Strategy

- use `GeneratedPost.body` as the X payload
- if the body exceeds 280 chars, split into a thread
- store the root tweet id for auditability
- only mark a post as delivered when the full X publish call succeeds

## Reuse from `chainbounty-x-automation`

Reused concepts:

- Tweepy-based X client
- environment variable naming
- posting history discipline

Not directly reused:

- tweet search
- Claude commentary generation
- quote-tweet workflow

## Risks

- Tweepy introduces the first non-stdlib runtime dependency into `cryptonewsbot`
- X API write permissions and rate limits must be configured correctly
- thread posting needs careful failure handling to avoid partial publication

## Recommended Rollout

1. add optional X client and config
2. add DB persistence for X delivery
3. add CLI test command
4. enable X posting in production `.env` only after a manual test succeeds
