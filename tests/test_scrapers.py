import feedparser
import pytest
from youtube_transcript_api._errors import TranscriptsDisabled

from app.scrapers import anthropic, openai, youtube
from tests.conftest import make_entry, make_feed


def test_openai_scraper_filters_by_age(monkeypatch):
    feed = make_feed(
        make_entry(2, title="New", link="https://openai.com/a", id="a", description="d",
                   tags=[{"term": "Research"}]),
        make_entry(48, title="Old", link="https://openai.com/b", id="b"),
    )
    monkeypatch.setattr(openai.feedparser, "parse", lambda url: feed)

    articles = openai.OpenAIScraper().get_articles(hours=24)

    assert [a.guid for a in articles] == ["a"]
    assert articles[0].category == "Research"


def test_anthropic_scraper_dedupes_across_feeds(monkeypatch):
    feed = make_feed(make_entry(1, title="Post", link="https://anthropic.com/p", id="p"))
    monkeypatch.setattr(anthropic.feedparser, "parse", lambda url: feed)

    articles = anthropic.AnthropicScraper().get_articles(hours=24)

    assert [a.guid for a in articles] == ["p"]


def test_anthropic_scraper_skips_entries_without_date(monkeypatch):
    feed = make_feed(make_entry(1, title="Dated", link="l", id="dated"))
    feed.entries.append(feedparser.FeedParserDict(title="Undated", link="l2", id="undated"))
    monkeypatch.setattr(anthropic.feedparser, "parse", lambda url: feed)

    articles = anthropic.AnthropicScraper().get_articles(hours=24)

    assert [a.guid for a in articles] == ["dated"]


def test_youtube_scraper_skips_shorts_and_old_videos(monkeypatch):
    feed = make_feed(
        make_entry(1, title="Video", link="https://www.youtube.com/watch?v=abc123&t=5"),
        make_entry(1, title="Short", link="https://www.youtube.com/shorts/xyz"),
        make_entry(72, title="Old", link="https://www.youtube.com/watch?v=old"),
    )
    monkeypatch.setattr(youtube.feedparser, "parse", lambda url: feed)

    videos = youtube.YouTubeScraper().get_latest_videos("channel", hours=24)

    assert [v.video_id for v in videos] == ["abc123"]


@pytest.mark.parametrize("url,expected", [
    ("https://www.youtube.com/watch?v=abc&list=x", "abc"),
    ("https://www.youtube.com/shorts/def?feature=share", "def"),
    ("https://youtu.be/ghi?t=10", "ghi"),
    ("plainid", "plainid"),
])
def test_extract_video_id(url, expected):
    assert youtube.YouTubeScraper()._extract_video_id(url) == expected


def test_get_transcript_returns_none_when_disabled(monkeypatch):
    scraper = youtube.YouTubeScraper()

    def raise_disabled(video_id):
        raise TranscriptsDisabled(video_id)

    monkeypatch.setattr(scraper.transcript_api, "fetch", raise_disabled)

    assert scraper.get_transcript("vid") is None


def test_get_transcript_propagates_other_errors(monkeypatch):
    scraper = youtube.YouTubeScraper()

    def raise_blocked(video_id):
        raise RuntimeError("blocked")

    monkeypatch.setattr(scraper.transcript_api, "fetch", raise_blocked)

    with pytest.raises(RuntimeError):
        scraper.get_transcript("vid")


def test_proxy_config_is_used_when_credentials_set(monkeypatch):
    monkeypatch.setenv("PROXY_USERNAME", "user")
    monkeypatch.setenv("PROXY_PASSWORD", "pass")
    captured = {}
    monkeypatch.setattr(youtube, "YouTubeTranscriptApi", lambda **kwargs: captured.update(kwargs))

    youtube.YouTubeScraper()

    assert isinstance(captured["proxy_config"], youtube.WebshareProxyConfig)
