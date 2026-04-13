"""
STEP 4: Web照合（スクレイピング専用）
query_generator が Serper API 検索と URL 選定を担うため、
このモジュールは選定済み URL のページテキスト取得のみを行う。
特許第5510912号 S15・S22に対応
"""
import hashlib
import logging
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

from cache.search_cache import SearchCache

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10  # seconds


@dataclass
class SearchResult:
    url: str
    title: str
    snippet: str
    page_text: str = ""      # スクレイピングしたページ本文


@dataclass
class WebSearchResult:
    query: str
    results: list[SearchResult] = field(default_factory=list)


def _scrape_page(url: str) -> str:
    """URLからページテキストを取得"""
    try:
        resp = requests.get(
            url,
            timeout=DEFAULT_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0 (compatible; CopypasteDetector/1.0)"},
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # script/style/nav/header/footerを除去
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()

        # メインコンテンツのテキストを抽出
        text = soup.get_text(separator="\n", strip=True)
        # 連続する空行を圧縮
        lines = [line for line in text.splitlines() if line.strip()]
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"Scraping failed for {url}: {e}")
        return ""


def scrape_urls(
    urls: list[str],
    cache: SearchCache,
) -> list[WebSearchResult]:
    """
    STEP 4: query_generator が選定した URL のページテキストを取得する。

    Serper API 検索と URL 頻度選定は query_generator.generate_queries() が担うため、
    このモジュールはスクレイピングのみを行う。

    Args:
        urls:  比較対象URL（QueryResult.top_urls の上位N件）
        cache: SearchCache（24時間TTL）

    Returns:
        list[WebSearchResult]（queryフィールドにはURLをそのまま使用）
    """
    results: list[WebSearchResult] = []

    for url in urls:
        cache_key = "scrape_" + hashlib.md5(url.encode()).hexdigest()
        cached: list[SearchResult] | None = cache.get(cache_key)

        if cached is not None:
            results.append(WebSearchResult(query=url, results=cached))
            continue

        page_text = _scrape_page(url)
        scraped = [SearchResult(url=url, title="", snippet="", page_text=page_text)]

        cache.set(cache_key, scraped)
        results.append(WebSearchResult(query=url, results=scraped))

    return results
