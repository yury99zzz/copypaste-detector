"""
STEP 4: Web照合（スクレイピング専用・非同期版）
query_generator が Serper API 検索と URL 選定を担うため、
このモジュールは選定済み URL のページテキスト取得のみを行う。
asyncio.gather で全 URL を並列スクレイピングし、タイムアウトを 10 秒に設定する。
特許第5510912号 S15・S22に対応
"""
import asyncio
import hashlib
import logging
from dataclasses import dataclass, field

import httpx
from bs4 import BeautifulSoup

from cache.search_cache import SearchCache

logger = logging.getLogger(__name__)

SCRAPE_TIMEOUT = 10.0   # 1 URL あたりのタイムアウト（秒）
USER_AGENT = "Mozilla/5.0 (compatible; CopypasteDetector/1.0)"


@dataclass
class SearchResult:
    url: str
    title: str
    snippet: str
    page_text: str = ""


@dataclass
class WebSearchResult:
    query: str
    results: list[SearchResult] = field(default_factory=list)


# ------------------------------------------------------------------ #
# 非同期スクレイピング
# ------------------------------------------------------------------ #

async def _scrape_page_async(url: str, client: httpx.AsyncClient) -> str:
    """
    URL から非同期でページテキストを取得する。
    タイムアウト・エラー時は空文字を返す。
    """
    try:
        resp = await client.get(url, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        lines = [line for line in text.splitlines() if line.strip()]
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"Scraping failed for {url}: {e}")
        return ""


# ------------------------------------------------------------------ #
# メイン関数
# ------------------------------------------------------------------ #

async def scrape_urls(
    urls: list[str],
    cache: SearchCache,
) -> list[WebSearchResult]:
    """
    STEP 4: query_generator が選定した URL のページテキストを非同期で取得する。

    処理フロー:
      1. キャッシュヒット分は即座に結果に追加
      2. キャッシュミス分を asyncio.gather で並列スクレイピング（各 SCRAPE_TIMEOUT 秒）
      3. 取得結果をキャッシュに保存し、元の URL 順で結果を返す

    Args:
        urls:  比較対象 URL のリスト（QueryResult.top_urls）
        cache: SearchCache（24 時間 TTL）
    """
    if not urls:
        return []

    # キャッシュヒット / ミスを仕分け
    cached_map: dict[str, list[SearchResult]] = {}
    to_fetch: list[str] = []

    for url in urls:
        cache_key = "scrape_" + hashlib.md5(url.encode()).hexdigest()
        cached: list[SearchResult] | None = cache.get(cache_key)
        if cached is not None:
            cached_map[url] = cached
            logger.debug(f"Scrape cache hit: {url}")
        else:
            to_fetch.append(url)

    # キャッシュミス分を asyncio.gather で並列スクレイピング
    fetched_texts: dict[str, str] = {}
    if to_fetch:
        timeout = httpx.Timeout(SCRAPE_TIMEOUT)
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            page_texts = await asyncio.gather(
                *[_scrape_page_async(url, client) for url in to_fetch],
                return_exceptions=True,
            )

        for url, result in zip(to_fetch, page_texts):
            text: str = result if isinstance(result, str) else ""
            fetched_texts[url] = text
            scraped = [SearchResult(url=url, title="", snippet="", page_text=text)]
            cache_key = "scrape_" + hashlib.md5(url.encode()).hexdigest()
            cache.set(cache_key, scraped)
            logger.debug(f"Scraped {url}: {len(text)} chars")

    # 元の URL 順で結果を組み立て
    results: list[WebSearchResult] = []
    for url in urls:
        if url in cached_map:
            results.append(WebSearchResult(query=url, results=cached_map[url]))
        else:
            page_text = fetched_texts.get(url, "")
            results.append(WebSearchResult(
                query=url,
                results=[SearchResult(url=url, title="", snippet="", page_text=page_text)],
            ))

    return results
