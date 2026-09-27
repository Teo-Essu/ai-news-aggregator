# AI News Aggregator

Collects AI news from YouTube channels, the OpenAI news feed, and Anthropic's news, research, and engineering feeds, summarizes each item with OpenAI, ranks the summaries against a user profile, and emails a personalized daily digest.

## How it works

`app/daily_runner.py` runs the pipeline in order:

1. **Scrape** new items from the last N hours (`app/runner.py`, `app/scrapers/`) and store them in Postgres.
2. **Fetch YouTube transcripts** for new videos (`app/services/process_youtube.py`).
3. **Summarize** every item that doesn't have a digest yet (`app/agent/digest_agent.py`).
4. **Rank** recent digests against the profile in `app/profiles/user_profile.py` (`app/agent/curator_agent.py`).
5. **Email** the top-ranked articles via Gmail SMTP (`app/services/process_email.py`).

## Setup

Requirements: Python 3.11+, [uv](https://docs.astral.sh/uv/), and Docker (or any Postgres instance).

```bash
uv sync
cp example.env .env   # then fill in the values
docker compose up -d  # starts Postgres using the POSTGRES_* values from .env
uv run python -m app.database.create_tables
```

### Environment variables

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | Used for summarizing, ranking, and writing the email intro |
| `FROM_EMAIL` | Gmail address that sends the digest |
| `TO_EMAIL` | Address that receives the digest |
| `APP_PASSWORD` | [Gmail app password](https://support.google.com/accounts/answer/185833) for `FROM_EMAIL` |
| `PROXY_USERNAME`, `PROXY_PASSWORD` | Optional Webshare proxy credentials; YouTube often blocks transcript requests from cloud IPs |
| `POSTGRES_*` | Database connection settings |

## Running

```bash
uv run python -m app.daily_runner
```

The process exits with status 0 if the email was sent and 1 otherwise, so it can be scheduled with cron or a CI scheduler.

Individual steps can also be run on their own:

```bash
uv run python -m app.runner                      # scrape only
uv run python -m app.services.process_youtube    # fetch transcripts
uv run python -m app.services.process_digest     # summarize
uv run python -m app.services.process_curator    # rank and print
uv run python -m app.services.process_email      # rank and send email
```

## Scheduling with GitHub Actions

`.github/workflows/daily-digest.yml` runs the pipeline every day at 06:00 UTC (edit the `cron` line to change it) and can be started manually from the Actions tab. Add these repository secrets under **Settings > Secrets and variables > Actions**:

- Required: `OPENAI_API_KEY`, `FROM_EMAIL`, `TO_EMAIL`, `APP_PASSWORD`
- Recommended: `PROXY_USERNAME`, `PROXY_PASSWORD`. GitHub's runners are blocked by YouTube, so without a proxy YouTube videos are skipped.
- Optional: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` to keep history in a hosted database. Without them, each run uses a fresh Postgres container, which is enough to email the last 24 hours of news.

A run fails when no email is sent, including days with nothing new to summarize.

## Tests

```bash
uv run pytest
```

The tests use in-memory SQLite and fake the RSS feeds, OpenAI, and SMTP, so they need no credentials or network access. They also run on every pull request via `.github/workflows/tests.yml`.

## Customizing

- **Sources:** YouTube channel IDs live in `app/config.py`; RSS feed URLs are in the scrapers under `app/scrapers/`.
- **Profile:** edit `app/profiles/user_profile.py` to change the name, interests, and preferences used for ranking.
