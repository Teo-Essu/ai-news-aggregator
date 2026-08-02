from typing import List
from app.scrapers.base_scraper import Article, BaseScraper


class GoogleArticle(Article):
    pass


class GoogleScraper(BaseScraper):
    @property
    def rss_urls(self) -> List[str]:
        return [
            "https://blog.google/technology/ai/rss/",
            "https://blog.google/products/rss/",
        ]

    def get_articles(self, hours: int = 24) -> List[GoogleArticle]:
        return [
            GoogleArticle(**article.model_dump())
            for article in super().get_articles(hours=hours)
        ]


if __name__ == "__main__":
    scraper = GoogleScraper()
    articles: List[GoogleArticle] = scraper.get_articles(hours=1000)
    print(f"Google articles: {len(articles)}")
