import os
from datetime import datetime, timedelta, timezone

import feedparser
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# The agents construct OpenAI clients at init time, which fails without a key.
os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app.database.models import Base
from app.database.repository import Repository


@pytest.fixture
def repo():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield Repository(session=session)
    session.close()


def make_entry(hours_ago: float, **fields) -> feedparser.FeedParserDict:
    published = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return feedparser.FeedParserDict(published_parsed=published.utctimetuple(), **fields)


def make_feed(*entries) -> feedparser.FeedParserDict:
    return feedparser.FeedParserDict(entries=list(entries))
