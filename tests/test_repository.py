from datetime import datetime, timedelta, timezone

from app.services.process_youtube import TRANSCRIPT_UNAVAILABLE_MARKER


def _video(video_id, transcript=None):
    return {
        "video_id": video_id,
        "title": f"Video {video_id}",
        "url": f"https://youtube.com/watch?v={video_id}",
        "channel_id": "channel",
        "published_at": datetime.now(timezone.utc),
        "transcript": transcript,
    }


def _article(guid):
    return {
        "guid": guid,
        "title": f"Article {guid}",
        "url": f"https://example.com/{guid}",
        "published_at": datetime.now(timezone.utc),
        "description": "desc",
    }


def test_bulk_create_skips_existing_rows(repo):
    assert repo.bulk_create_openai_articles([_article("a"), _article("b")]) == 2
    assert repo.bulk_create_openai_articles([_article("a"), _article("c")]) == 1


def test_videos_without_transcript(repo):
    repo.bulk_create_youtube_videos([_video("v1"), _video("v2", transcript="text")])

    assert [v.video_id for v in repo.get_youtube_videos_without_transcript()] == ["v1"]


def test_articles_without_digest_excludes_digested_and_unavailable(repo):
    repo.bulk_create_youtube_videos([
        _video("with_transcript", transcript="hello"),
        _video("unavailable", transcript=TRANSCRIPT_UNAVAILABLE_MARKER),
        _video("pending"),
    ])
    repo.bulk_create_openai_articles([_article("o1"), _article("o2")])
    repo.bulk_create_anthropic_articles([_article("a1")])
    repo.create_digest("openai", "o1", "url", "title", "summary")

    pending = {(a["type"], a["id"]) for a in repo.get_articles_without_digest()}

    assert pending == {("youtube", "with_transcript"), ("openai", "o2"), ("anthropic", "a1")}


def test_create_digest_is_idempotent(repo):
    assert repo.create_digest("openai", "o1", "url", "title", "summary") is not None
    assert repo.create_digest("openai", "o1", "url", "title", "summary") is None


def test_recent_digests_respects_window(repo):
    now = datetime.now(timezone.utc)
    repo.create_digest("openai", "new", "url", "New", "s", published_at=now - timedelta(hours=1))
    repo.create_digest("openai", "old", "url", "Old", "s", published_at=now - timedelta(hours=48))

    assert [d["id"] for d in repo.get_recent_digests(hours=24)] == ["openai:new"]
