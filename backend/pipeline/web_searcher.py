"""
STEP 4: Web照合
Serper APIで検索し、URLからテキストをスクレイピング
特許第5510912号 S15・S22に対応
"""
import os
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Optional

import requests
from bs4 import BeautifulSoup

from cache.search_cache import SearchCache

logger = logging.getLogger(__name__)

SERPER_API_URL = "https://google.serper.dev/search"
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


def _serper_search(query: str, api_key: str, num_results: int = 5) -> list[dict]:
    """Serper APIで検索を実行"""
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }
    payload = {"q": query, "num": num_results, "gl": "jp", "hl": "ja"}

    resp = requests.post(SERPER_API_URL, json=payload, headers=headers, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    return data.get("organic", [])


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


def search_web(
    queries: list[str],
    cache: SearchCache,
    api_key: Optional[str] = None,
    num_results: int = 5,
) -> list[WebSearchResult]:
    """
    STEP 4: Web照合
    各検索キーでSerper APIを使って検索し、結果ページのテキストを取得

    特許S115-S119に対応:
      S115: 検索キーで比較範囲を検索
      S116: 検索結果をメモリ（キャッシュ）に記憶
      S119: 出現頻度の高いデータを選択

    Args:
        queries: 検索キーのリスト
        cache: SearchCacheインスタンス
        api_key: Serper APIキー（Noneの場合は環境変数から取得）
        num_results: 1クエリあたりの検索結果数

    Returns:
        list[WebSearchResult]
    """
    if api_key is None:
        api_key = os.environ.get("SERPER_API_KEY", "")

    all_results: list[WebSearchResult] = []

    for query in queries:
        cache_key = hashlib.md5(query.encode()).hexdigest()
        cached = cache.get(cache_key)

        if cached is not None:
            all_results.append(WebSearchResult(query=query, results=cached))
            continue

        if not api_key:
            logger.warning("SERPER_API_KEY not set, skipping web search")
            all_results.append(WebSearchResult(query=query, results=[]))
            continue

        try:
            raw_results = _serper_search(query, api_key, num_results)
        except Exception as e:
            logger.error(f"Serper search failed for '{query}': {e}")
            all_results.append(WebSearchResult(query=query, results=[]))
            continue

        search_results = []
        for item in raw_results:
            url = item.get("link", "")
            title = item.get("title", "")
            snippet = item.get("snippet", "")

            # ページのテキストをスクレイピング
            page_text = _scrape_page(url)

            search_results.append(SearchResult(
                url=url,
                title=title,
                snippet=snippet,
                page_text=page_text,
            ))

        # S116: キャッシュに保存
        cache.set(cache_key, search_results)
        all_results.append(WebSearchResult(query=query, results=search_results))

    return all_results
