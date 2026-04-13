"""
FastAPI エントリポイント
POST /check エンドポイントでコピペ検出パイプラインを実行

タイムアウト設計:
  - Serper API リクエスト: 各 10 秒（並列 5 件）
  - スクレイピング:        各 10 秒（並列 N 件）
  - パイプライン全体:      25 秒でタイムアウト → HTTP 504
    （Heroku の 30 秒制限に 5 秒のマージンを確保）

Heroku スリープ対策:
  - 起動時にバックグラウンドタスクを起動
  - 25 分ごとに GET /ping を自分自身に送信してスリープを防ぐ
  - 環境変数 APP_URL にデプロイ先 URL を設定すること
    （例: https://your-app.herokuapp.com）
"""
import asyncio
import os
import time
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from cache.search_cache import SearchCache
from pipeline.preprocessor import preprocess
from pipeline.query_generator import generate_queries
from pipeline.web_searcher import scrape_urls
from pipeline.similarity import compute_similarity
from pipeline.legality_checker import check_legality
from pipeline.scorer import compute_score

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PIPELINE_TIMEOUT = 25.0        # 秒（Heroku 30s - 5s マージン）
KEEPALIVE_INTERVAL = 25 * 60   # 25 分（Heroku の 30 分スリープより短く）

_cache: SearchCache = SearchCache(ttl=86400)


async def _keepalive_loop(self_url: str) -> None:
    """25 分ごとに自分自身の /ping を叩いて Heroku のスリープを防ぐ"""
    while True:
        await asyncio.sleep(KEEPALIVE_INTERVAL)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self_url}/ping")
            logger.info(f"Keepalive ping → {resp.status_code}")
        except Exception as e:
            logger.warning(f"Keepalive ping failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("CopypasteDetector backend starting up")
    self_url = os.environ.get("APP_URL", "").rstrip("/")
    task = None
    if self_url:
        task = asyncio.create_task(_keepalive_loop(self_url))
        logger.info(f"Keepalive task started (target: {self_url}/ping every {KEEPALIVE_INTERVAL}s)")
    else:
        logger.info("APP_URL not set — keepalive disabled")
    yield
    if task:
        task.cancel()
    logger.info("CopypasteDetector backend shutting down")


app = FastAPI(
    title="Copypaste Detector API",
    description="大学レポートのコピペ・剽窃検出API（特許第5510912号準拠）",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------ #
# リクエスト / レスポンスモデル
# ------------------------------------------------------------------ #

class CheckOptions(BaseModel):
    threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="類似度閾値")
    max_queries: int = Field(default=5, ge=1, le=10, description="最大検索キー数")
    exclude_quotes: bool = Field(default=True, description="引用符内テキストを除外するか")


class CheckRequest(BaseModel):
    text: str = Field(..., min_length=1, description="レポート本文テキスト")
    options: CheckOptions = Field(default_factory=CheckOptions)


class MatchResult(BaseModel):
    text: str
    start: int
    end: int
    similarity: float
    source_url: str
    is_legal_citation: bool


class CheckResponse(BaseModel):
    total_score: float
    status: str
    matches: list[MatchResult]
    processing_time: float
    per_source_scores: dict[str, float] = {}  # 文献ごとの引用割合(%)


# ------------------------------------------------------------------ #
# パイプライン本体（25 秒タイムアウト対象）
# ------------------------------------------------------------------ #

async def _run_pipeline(req: CheckRequest, start_time: float) -> CheckResponse:
    """
    コピペ検出の全パイプラインを実行する。
    asyncio.wait_for でラップされ、PIPELINE_TIMEOUT 秒を超えると
    asyncio.TimeoutError が発生する。
    """
    # STEP 1-2: 構造解析・正規化（同期処理）
    logger.info("STEP 1-2: Preprocessing")
    prep_result = preprocess(req.text)

    if not prep_result.body_text.strip():
        raise HTTPException(status_code=400, detail="判定対象の本文が見つかりませんでした")

    # STEP 3: スライディングウィンドウ → Serper 並列検索 → URL 選定（図21 S91-S99）
    # asyncio.gather で最大 5 リクエストを同時実行（各 10 秒タイムアウト）
    logger.info("STEP 3: Sliding window queries + parallel Serper search + URL selection")
    query_result = await generate_queries(
        body_text=prep_result.body_text,
        cache=_cache,
        max_queries=req.options.max_queries,
        synonym_variants=prep_result.synonym_variants,
    )

    if not query_result.top_urls:
        return CheckResponse(
            total_score=0.0,
            status="ok",
            matches=[],
            processing_time=round(time.time() - start_time, 2),
        )

    # STEP 4: 選定 URL を並列スクレイピング（各 10 秒タイムアウト）
    logger.info(f"STEP 4: Parallel scraping of {len(query_result.top_urls)} URLs")
    web_results = await scrape_urls(
        urls=query_result.top_urls,
        cache=_cache,
    )

    # STEP 5: 類似度算出（同期処理）
    logger.info("STEP 5: Computing similarity")
    sim_result = compute_similarity(
        body_text=prep_result.body_text,
        web_results=web_results,
        threshold=req.options.threshold,
    )

    # STEP 6: 適法性判定（同期処理）
    logger.info("STEP 6: Checking legality")
    legality_results = check_legality(sim_result.spans, prep_result.body_text)

    # STEP 7: スコア集計（同期処理）
    logger.info("STEP 7: Computing score")
    score_output = compute_score(legality_results, prep_result.body_text)

    processing_time = round(time.time() - start_time, 2)
    logger.info(
        f"Done. score={score_output.total_score}% "
        f"status={score_output.status} time={processing_time}s"
    )

    return CheckResponse(
        total_score=score_output.total_score,
        status=score_output.status,
        matches=[
            MatchResult(
                text=m.text,
                start=m.start,
                end=m.end,
                similarity=round(m.similarity, 3),
                source_url=m.source_url,
                is_legal_citation=m.is_legal_citation,
            )
            for m in score_output.matches
        ],
        processing_time=processing_time,
        per_source_scores=score_output.per_source_scores,
    )


# ------------------------------------------------------------------ #
# エンドポイント
# ------------------------------------------------------------------ #

@app.post("/check", response_model=CheckResponse)
async def check_text(req: CheckRequest) -> CheckResponse:
    """
    コピペ検出の全パイプラインを実行する。
    PIPELINE_TIMEOUT 秒（25 秒）を超えた場合は HTTP 504 を返す。
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="テキストが空です")

    start_time = time.time()
    try:
        return await asyncio.wait_for(
            _run_pipeline(req, start_time),
            timeout=PIPELINE_TIMEOUT,
        )
    except asyncio.TimeoutError:
        elapsed = round(time.time() - start_time, 1)
        logger.warning(f"Pipeline timeout after {elapsed}s")
        raise HTTPException(
            status_code=504,
            detail=f"処理が {PIPELINE_TIMEOUT:.0f} 秒を超えました。テキストを短くして再試行してください。",
        )


@app.post("/cache/clear")
async def clear_cache():
    """キャッシュを全削除する。Serper API の検索結果・スクレイピング結果がすべて消える。"""
    deleted = _cache.clear()
    logger.info(f"Cache cleared: {deleted} entries deleted")
    return {"deleted": deleted}


@app.get("/ping")
async def ping():
    """Heroku スリープ防止用 ping エンドポイント"""
    return {"status": "pong"}


@app.get("/health")
async def health():
    return {"status": "ok"}
