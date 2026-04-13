"""
STEP 3: 検索キー生成 + Web検索 + 比較対象URL選定
特許第5510912号 図21（S91-S99）準拠

処理フロー:
  S94-S98: テキスト全体を 32 文字ずつ区切って全チャンクを生成
           → 代表的な SEARCH_QUERY_COUNT（10）個を均等サンプリング
  S95-S96: 各チャンクを引用符付きクエリ("...")として Serper API で並列検索
           → asyncio.gather で最大 SEARCH_QUERY_COUNT リクエストを同時実行
  S99    : 全クエリ横断で URL 出現頻度を集計し、上位 TOP_URLS_COUNT（3）件を選定
           → 分散コピペでも頻出 URL が浮かび上がる仕組み

除外ドメイン:
  jstage.jst.go.jp — ペイウォール・構造化テキスト取得不可のため除外
"""
import asyncio
import hashlib
import logging
import os
from collections import Counter
from dataclasses import dataclass
from typing import Optional

import httpx

from cache.search_cache import SearchCache

logger = logging.getLogger(__name__)

# S93: 制限文字数
WINDOW_SIZE: int = 32
# 全チャンクから検索に使う代表チャンク数
SEARCH_QUERY_COUNT: int = 10
# S99: 比較対象として返す最頻出 URL の件数
TOP_URLS_COUNT: int = 3

SERPER_API_URL = "https://google.serper.dev/search"
SERPER_TIMEOUT = 10.0   # 1リクエストあたりのタイムアウト（秒）
SERPER_NUM_RESULTS = 5  # 1クエリあたりの取得件数

# 比較対象から除外するドメイン
EXCLUDED_DOMAINS: frozenset[str] = frozenset([
    "jstage.jst.go.jp",
])


@dataclass
class QueryResult:
    queries: list[str]        # 実際に使用した検索クエリ（ログ用）
    top_urls: list[str]       # 出現頻度順の比較対象 URL（S99 選定結果）
    url_freq: dict[str, int]  # URL → 全クエリ横断の出現頻度


# ------------------------------------------------------------------ #
# 図21 S94-S98: スライディングウィンドウ
# ------------------------------------------------------------------ #

def _build_windows(text: str) -> list[str]:
    """テキストを先頭から WINDOW_SIZE 文字ずつ非重複で分割する。"""
    windows: list[str] = []
    i = 0
    while i < len(text):
        chunk = text[i : i + WINDOW_SIZE].strip()
        if chunk:
            windows.append(chunk)
        i += WINDOW_SIZE
    return windows


def _sample_windows(windows: list[str], max_count: int) -> list[str]:
    """全ウィンドウから max_count 個を均等サンプリングしてテキスト全体をカバーする。"""
    if len(windows) <= max_count:
        return windows
    step = (len(windows) - 1) / (max_count - 1)
    indices = sorted({round(i * step) for i in range(max_count)})
    return [windows[idx] for idx in indices]


# ------------------------------------------------------------------ #
# URL フィルタリング
# ------------------------------------------------------------------ #

def _is_excluded(url: str) -> bool:
    """EXCLUDED_DOMAINS に含まれるドメインなら True を返す。"""
    return any(domain in url for domain in EXCLUDED_DOMAINS)


# ------------------------------------------------------------------ #
# 図21 S95-S96: Serper API 非同期検索
# ------------------------------------------------------------------ #

async def _serper_search_async(
    query: str,
    api_key: str,
    client: httpx.AsyncClient,
) -> list[str]:
    """
    1 クエリを Serper API で非同期検索し、除外ドメイン以外の URL リストを返す。
    タイムアウト・エラー時は空リストを返す。
    """
    try:
        resp = await client.post(
            SERPER_API_URL,
            json={"q": query, "num": SERPER_NUM_RESULTS, "gl": "jp", "hl": "ja"},
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        urls = [item["link"] for item in resp.json().get("organic", []) if item.get("link")]
        filtered = [u for u in urls if not _is_excluded(u)]
        if len(urls) != len(filtered):
            logger.debug(f"Excluded {len(urls) - len(filtered)} URL(s) for: {query}")
        return filtered
    except Exception as e:
        logger.error(f"Serper search failed for '{query}': {e}")
        return []


# ------------------------------------------------------------------ #
# メイン関数
# ------------------------------------------------------------------ #

async def generate_queries(
    body_text: str,
    cache: SearchCache,
    api_key: Optional[str] = None,
    max_queries: int = SEARCH_QUERY_COUNT,
) -> QueryResult:
    """
    図21 S91-S99 の全処理を実行する（非同期版）。

    1. テキスト全体を 32 文字ずつ区切って全チャンクを生成（S94-S98）
    2. 全チャンクから代表的な max_queries 個を均等サンプリング
    3. キャッシュミス分を asyncio.gather で並列検索（S95-S96・各 SERPER_TIMEOUT 秒）
    4. URL 出現頻度を集計し上位 TOP_URLS_COUNT 件を比較対象として返す（S99）
       → テキスト各所から同一 URL が検出されるほどスコアが上がる分散コピペ検出

    Args:
        body_text:   判定対象の本文テキスト
        cache:       SearchCache（24 時間 TTL）
        api_key:     Serper API キー（None なら環境変数 SERPER_API_KEY を使用）
        max_queries: サンプリングするチャンク数（デフォルト SEARCH_QUERY_COUNT=10）
    """
    if not body_text.strip():
        return QueryResult(queries=[], top_urls=[], url_freq={})

    if api_key is None:
        api_key = os.environ.get("SERPER_API_KEY", "")

    # S94-S98: テキスト全体を 32 文字チャンクに分割 → max_queries 個を均等サンプリング
    all_windows = _build_windows(body_text)
    selected = _sample_windows(all_windows, max_queries)
    queries = [f'"{w}"' for w in selected]

    logger.info(
        f"Window queries: {len(queries)}/{len(all_windows)} chunks "
        f"(text={len(body_text)} chars)"
    )

    if not api_key:
        logger.warning("SERPER_API_KEY not set — skipping web search")
        return QueryResult(queries=queries, top_urls=[], url_freq={})

    url_counter: Counter[str] = Counter()

    # キャッシュヒット分を先に処理し、ミス分だけ並列リクエスト対象にする
    to_fetch: list[str] = []
    for query in queries:
        cache_key = "qgen_" + hashlib.md5(query.encode()).hexdigest()
        cached: Optional[list[str]] = cache.get(cache_key)
        if cached is not None:
            url_counter.update(cached)
            logger.debug(f"Cache hit: {query}")
        else:
            to_fetch.append(query)

    # S95-S96: キャッシュミス分を asyncio.gather で並列実行
    if to_fetch:
        timeout = httpx.Timeout(SERPER_TIMEOUT)
        async with httpx.AsyncClient(timeout=timeout) as client:
            raw_results = await asyncio.gather(
                *[_serper_search_async(q, api_key, client) for q in to_fetch],
                return_exceptions=True,
            )

        for query, result in zip(to_fetch, raw_results):
            urls: list[str] = result if isinstance(result, list) else []
            cache_key = "qgen_" + hashlib.md5(query.encode()).hexdigest()
            cache.set(cache_key, urls)   # S96: キャッシュに記憶
            url_counter.update(urls)
            logger.debug(f"{query} → {len(urls)} URLs")

    # S99: 出現頻度の高い URL 上位 TOP_URLS_COUNT 件を比較対象として選定
    # 複数チャンクで同一 URL がヒットするほど頻度が上がり、分散コピペを検出できる
    top_urls = [url for url, _ in url_counter.most_common(TOP_URLS_COUNT)]
    logger.info(
        f"URL frequency: {len(url_counter)} unique, "
        f"top{TOP_URLS_COUNT}={top_urls}"
    )

    return QueryResult(
        queries=queries,
        top_urls=top_urls,
        url_freq=dict(url_counter),
    )
