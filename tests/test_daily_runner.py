import pytest

from app import daily_runner
from app.services import process_email

SENT = {"success": True, "sent": True, "subject": "s", "articles_count": 3}
NOTHING_TO_SEND = {"success": True, "sent": False, "reason": "No digests found"}
EMAIL_FAILED = {"success": False, "error": "Failed to rank articles"}


def _run(monkeypatch, digests_failed=0, email=SENT, scrape_error=None):
    def scrape(hours):
        if scrape_error:
            raise scrape_error
        return {}

    monkeypatch.setattr(daily_runner, "run_scrapers", scrape)
    monkeypatch.setattr(daily_runner, "process_youtube_transcripts",
                        lambda: {"total": 1, "processed": 0, "unavailable": 0, "failed": 1})
    monkeypatch.setattr(daily_runner, "process_digests",
                        lambda: {"total": 2, "processed": 2 - digests_failed, "failed": digests_failed})
    monkeypatch.setattr(daily_runner, "send_digest_email", lambda hours, top_n: email)
    return daily_runner.run_daily_pipeline()


@pytest.mark.parametrize("email", [SENT, NOTHING_TO_SEND])
def test_succeeds_when_email_sent_or_nothing_new(monkeypatch, email):
    result = _run(monkeypatch, email=email)

    assert result["success"] is True
    assert result["errors"] == []


def test_fails_when_digests_fail_even_if_nothing_is_sent(monkeypatch):
    result = _run(monkeypatch, digests_failed=2, email=NOTHING_TO_SEND)

    assert result["success"] is False
    assert result["errors"] == ["2 of 2 digests failed"]


def test_fails_when_email_step_fails(monkeypatch):
    result = _run(monkeypatch, email=EMAIL_FAILED)

    assert result["success"] is False
    assert result["errors"] == ["Email failed: Failed to rank articles"]


def test_fails_on_unexpected_exception(monkeypatch):
    result = _run(monkeypatch, scrape_error=RuntimeError("db down"))

    assert result["success"] is False
    assert result["errors"] == ["Pipeline error: db down"]


def test_send_digest_email_reports_nothing_to_send(repo, monkeypatch):
    monkeypatch.setattr(process_email, "Repository", lambda: repo)

    result = process_email.send_digest_email()

    assert result["success"] is True
    assert result["sent"] is False
