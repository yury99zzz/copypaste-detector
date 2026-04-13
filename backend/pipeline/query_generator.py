"""
STEP 3: 検索キー生成 + Web検索 + 比較対象URL選定
特許第5510912号 図21（S91-S99）準拠

処理フロー:
  S94-S98: 判定範囲を 32 文字以内のスライディングウィンドウで分割
  S95-S96: 各ウィンドウを引用符付きクエリ("...")として Serper API で検索
  S99    : 全クエリ横断で最も出現頻度の高い URL を比較対象として選定

除外ドメイン:
  jstage.jst.go.jp — ペイウォール・構造化テキスト取得不可のため除外
"""
import hashlib
import logging
import os
from collections import Counter
from dataclasses import dataclass
from typing import Optional

import requests

from cache.search_cache import SearchCache

logger = logging.getLogger(__name__)

# S93: 制限文字数
WINDOW_SIZE: int = 32
# 検索に使うウィンドウの最大数
MAX_QUERIES: int = 5

SERPER_API_URL = "https://google.serper.dev/search"
SERPER_TIMEOUT = 10        # seconds
SERPER_NUM_RESULTS = 5     # 1クエリあたりの取得件数

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
    """
    テキストを先頭から WINDOW_SIZE 文字ずつ非重複で分割する。
    空白のみのチャンクは除外する。
    """
    windows: list[str] = []
    i = 0
    while i < len(text):
        chunk = text[i : i + WINDOW_SIZE].strip()
        if chunk:
            windows.append(chunk)
        i += WINDOW_SIZE
    return windows


def _sample_windows(windows: list[str], max_count: int) -> list[str]:
    """
    全ウィンドウからテキスト全体をカバーするよう max_count 個を均等サンプリングする。
    ウィンドウ数が max_count 以下ならそのまま返す。
    """
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
# 図21 S95-S96: Serper API 検索
# ------------------------------------------------------------------ #

def _serper_search(query: str, api_key: str) -> list[str]:
    """
    1 クエリを Serper API で検索し、除外ドメイン以外の URL リストを返す。
    クエリは "..." 形式の完全一致検索。
    """
    try:
        resp = requests.post(
            SERPER_API_URL,
            json={"q": query, "num": SERPER_NUM_RESULTS, "gl": "jp", "hl": "ja"},
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            timeout=SERPER_TIMEOUT,
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

def generate_queries(
    body_text: str,
    cache: SearchCache,
    api_key: Optional[str] = None,
    max_queries: int = MAX_QUERIES,
) -> QueryResult:
    """
    図21 S91-S99 の全処理を実行する。

    1. 32 文字ウィンドウに分割し、テキスト全体を max_queries 個で均等カバー（S94-S98）
    2. 各ウィンドウを "..." 形式でクエリ化し Serper API を検索（S95-S96）
    3. 全クエリの結果 URL を集計し出現頻度順に並べる（S99）

    Args:
        body_text:   判定対象の本文テキスト
        cache:       SearchCache（24 時間 TTL）
        api_key:     Serper API キー（None なら環境変数 SERPER_API_KEY を使用）
        max_queries: 使用するウィンドウ数の上限（デフォルト 5）

    Returns:
        QueryResult
    """
    if not body_text.strip():
        return QueryResult(queries=[], top_urls=[], url_freq={})

    if api_key is None:
        api_key = os.environ.get("SERPER_API_KEY", "")

    # S94-S98: 32 文字ウィンドウ生成 → max_queries 個を均等サンプリング
    all_windows = _build_windows(body_text)
    selected = _sample_windows(all_windows, max_queries)
    queries = [f'"{w}"' for w in selected]

    logger.info(f"Window queries: {len(queries)}/{len(all_windows)} (text={len(body_text)} chars)")

    if not api_key:
        logger.warning("SERPER_API_KEY not set — skipping web search")
        return QueryResult(queries=queries, top_urls=[], url_freq={})

    # S95-S96: 各クエリで検索し URL を収集
    url_counter: Counter[str] = Counter()

    for query in queries:
        cache_key = "qgen_" + hashlib.md5(query.encode()).hexdigest()
        cached: Optional[list[str]] = cache.get(cache_key)

        if cached is not None:
            url_counter.update(cached)
            logger.debug(f"Cache hit: {query}")
            continue

        urls = _serper_search(query, api_key)
        cache.set(cache_key, urls)   # S96: キャッシュに記憶
        url_counter.update(urls)
        logger.debug(f"{query} → {len(urls)} URLs")

    # S99: 出現頻度の高い URL を比較対象として選定
    top_urls = [url for url, _ in url_counter.most_common()]
    logger.info(f"Selected {len(top_urls)} URLs, top={top_urls[:3]}")

    return QueryResult(
        queries=queries,
        top_urls=top_urls,
        url_freq=dict(url_counter),
    )
