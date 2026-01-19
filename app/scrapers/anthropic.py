from typing import List
from app.scrapers.base_scraper import Article, BaseScraper


class AnthropicArticle(Article):
    pass


class AnthropicScraper(BaseScraper):
    @property
    def rss_urls(self) -> List[str]:
        return [
            "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml",
            "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_research.xml",
            "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_engineering.xml",
        ]

    def get_articles(self, hours: int = 24) -> List[AnthropicArticle]:
        return [
            AnthropicArticle(**article.model_dump())
            for article in super().get_articles(hours=hours)
        ]

if __name__ == "__main__":
    scraper = AnthropicScraper()
    articles: List[AnthropicArticle] = scraper.get_articles(hours=1000)