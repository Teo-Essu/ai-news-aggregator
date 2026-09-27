from datetime import datetime
from types import SimpleNamespace

import pytest

from app.agent.curator_agent import CuratorAgent
from app.agent.digest_agent import DigestAgent
from app.agent.email_agent import EmailDigestResponse, EmailIntroduction, RankedArticleDetail
from app.profiles.user_profile import USER_PROFILE
from app.services import email, process_youtube


class FakeScraper:
    def __init__(self, results):
        self.results = results

    def get_transcript(self, video_id):
        result = self.results[video_id]
        if isinstance(result, Exception):
            raise result
        return SimpleNamespace(text=result) if result else None


class FailingResponses:
    def parse(self, **kwargs):
        raise RuntimeError("api down")


def _digest_response(title="Title", url="https://example.com"):
    return EmailDigestResponse(
        introduction=EmailIntroduction(greeting="Hey Teo", introduction="Today's news."),
        articles=[RankedArticleDetail(
            digest_id="openai:1", rank=1, relevance_score=9.0, title=title,
            summary="A **summary**.", url=url, article_type="openai",
        )],
        total_ranked=1,
        top_n=10,
    )


def test_process_youtube_transcripts_counts_outcomes(repo, monkeypatch):
    repo.bulk_create_youtube_videos([
        {"video_id": vid, "title": vid, "url": "u", "channel_id": "c",
         "published_at": datetime(2026, 1, 1)}
        for vid in ("ok", "none", "blocked")
    ])
    scraper = FakeScraper({"ok": "transcript", "none": None, "blocked": RuntimeError("blocked")})
    monkeypatch.setattr(process_youtube, "YouTubeScraper", lambda: scraper)
    monkeypatch.setattr(process_youtube, "Repository", lambda: repo)

    result = process_youtube.process_youtube_transcripts()

    assert result == {"total": 3, "processed": 1, "unavailable": 1, "failed": 1}
    remaining = [v.video_id for v in repo.get_youtube_videos_without_transcript()]
    assert remaining == ["blocked"]


def test_digest_to_markdown():
    markdown = _digest_response().to_markdown()

    assert markdown.startswith("Hey Teo\n\nToday's news.")
    assert "## Title" in markdown
    assert "[Read more →](https://example.com)" in markdown


def test_digest_to_html_escapes_title_and_url():
    html = email.digest_to_html(_digest_response(title="<script>", url='https://x.com/"a'))

    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert 'href="https://x.com/&quot;a"' in html
    assert "<strong>summary</strong>" in html


def test_send_email_requires_from_address(monkeypatch):
    monkeypatch.setattr(email, "FROM_EMAIL", None)
    monkeypatch.setattr(email, "APP_PASSWORD", "pw")

    with pytest.raises(ValueError, match="FROM_EMAIL"):
        email.send_email("s", "body", recipients=["to@example.com"])


def test_send_email_uses_explicit_recipients_without_to_email(monkeypatch):
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def login(self, user, password):
            sent["login"] = (user, password)

        def sendmail(self, from_addr, to_addrs, message):
            sent["to"] = to_addrs

    monkeypatch.setattr(email, "FROM_EMAIL", "from@example.com")
    monkeypatch.setattr(email, "TO_EMAIL", None)
    monkeypatch.setattr(email, "APP_PASSWORD", "pw")
    monkeypatch.setattr(email.smtplib, "SMTP_SSL", FakeSMTP)

    email.send_email("s", "body", recipients=["someone@example.com"])

    assert sent == {"login": ("from@example.com", "pw"), "to": ["someone@example.com"]}


def test_agents_handle_api_errors():
    digest_agent = DigestAgent()
    digest_agent.client = SimpleNamespace(responses=FailingResponses())
    curator = CuratorAgent(USER_PROFILE)
    curator.client = SimpleNamespace(responses=FailingResponses())

    assert digest_agent.generate_digest("t", "c", "openai") is None
    assert curator.rank_digests([{"id": "a:1", "title": "t", "summary": "s", "article_type": "a"}]) == []
