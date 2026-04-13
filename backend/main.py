"""
FastAPI エントリポイント
POST /check エンドポイントでコピペ検出パイプラインを実行
"""
import time
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from cache.search_cache import SearchCache
from pipeline.preprocessor import preprocess
from pipeline.query_generator import generate_queries
from pipeline.web_searcher import search_web
from pipeline.similarity import compute_similarity
from pipeline.legality_checker import check_legality
from pipeline.scorer import compute_score

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# アプリ起動時にキャッシュを初期化
_cache: SearchCache = SearchCache(ttl=86400)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("CopypasteDetector backend starting up")
    yield
    logger.info("CopypasteDetector backend shutting down")


app = FastAPI(
    title="Copypaste Detector API",
    description="大学レポートのコピペ・剽窃検出API（特許第5510912号準拠）",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # GitHub Pagesからのアクセスを許可
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- リクエスト/レスポンスモデル ---

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


# --- エンドポイント ---

@app.post("/check", response_model=CheckResponse)
async def check_text(req: CheckRequest) -> CheckResponse:
    """
    コピペ検出の全パイプラインを実行

    処理フロー（特許第5510912号準拠）:
      STEP 1-2: 構造解析・正規化
      STEP 3:   検索キー生成
      STEP 4:   Web照合
      STEP 5:   類似度算出
      STEP 6:   適法性判定
      STEP 7:   スコア集計
    """
    start_time = time.time()

    if len(req.text.strip()) == 0:
        raise HTTPException(status_code=400, detail="テキストが空です")

    # STEP 1-2: 前処理・正規化
    logger.info("STEP 1-2: Preprocessing")
    prep_result = preprocess(req.text)

    if not prep_result.body_text.strip():
        raise HTTPException(status_code=400, detail="判定対象の本文が見つかりませんでした")

    # STEP 3: 検索キー生成
    logger.info("STEP 3: Generating queries")
    query_result = generate_queries(prep_result.tokens, max_queries=req.options.max_queries)

    if not query_result.queries:
        return CheckResponse(
            total_score=0.0,
            status="ok",
            matches=[],
            processing_time=round(time.time() - start_time, 2),
        )

    # STEP 4: Web照合
    logger.info(f"STEP 4: Web search with queries: {query_result.queries}")
    web_results = search_web(
        queries=query_result.queries,
        cache=_cache,
    )

    # STEP 5: 類似度算出
    logger.info("STEP 5: Computing similarity")
    sim_result = compute_similarity(
        body_text=prep_result.body_text,
        web_results=web_results,
        threshold=req.options.threshold,
    )

    # STEP 6: 適法性判定
    logger.info("STEP 6: Checking legality")
    legality_results = check_legality(sim_result.spans, prep_result.body_text)

    # STEP 7: スコア集計
    logger.info("STEP 7: Computing score")
    score_output = compute_score(legality_results, prep_result.body_text)

    processing_time = round(time.time() - start_time, 2)
    logger.info(f"Done. score={score_output.total_score}% status={score_output.status} time={processing_time}s")

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
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
