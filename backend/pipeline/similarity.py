"""
STEP 5: 類似度算出
RapidFuzzによる文節単位のファジーマッチング
特許第5510912号 S16に対応
"""
import re
from dataclasses import dataclass, field

from rapidfuzz import fuzz, process


@dataclass
class MatchSpan:
    text: str          # 一致した文字列（入力テキスト側）
    start: int         # 入力テキスト内の開始位置
    end: int           # 入力テキスト内の終了位置
    similarity: float  # 類似度 (0.0〜1.0)
    source_url: str    # 照合元URL
    matched_text: str  # 照合元テキスト側の一致文字列


@dataclass
class SimilarityResult:
    spans: list[MatchSpan] = field(default_factory=list)


# 文節・センテンス分割のパターン
_SENTENCE_SPLIT = re.compile(r"(?<=[。．.!?！？\n])")


def _split_into_chunks(text: str, min_len: int = 10) -> list[tuple[str, int]]:
    """
    テキストを文節/センテンス単位に分割し、(chunk, offset)のリストを返す
    """
    chunks = []
    pos = 0
    for sent in _SENTENCE_SPLIT.split(text):
        stripped = sent.strip()
        if len(stripped) >= min_len:
            # 元テキスト内でのオフセットを計算
            offset = text.find(stripped, pos)
            if offset == -1:
                offset = pos
            chunks.append((stripped, offset))
            pos = offset + len(stripped)
    return chunks


def _split_source_into_chunks(text: str, chunk_size: int = 200) -> list[str]:
    """
    照合元テキストを固定長チャンクに分割（スライディングウィンドウ）
    特許図21のスライディングウィンドウ処理に対応
    """
    chunks = []
    step = chunk_size // 2  # 50%オーバーラップ
    for i in range(0, max(1, len(text) - chunk_size + 1), step):
        chunks.append(text[i:i + chunk_size])
    if not chunks and text:
        chunks.append(text)
    return chunks


def compute_similarity(
    body_text: str,
    web_results: list,  # list[WebSearchResult]
    threshold: float = 0.5,
) -> SimilarityResult:
    """
    STEP 5: 類似度算出
    入力テキストの各文節と照合元テキストをRapidFuzzでファジーマッチング

    特許S16に対応:
      - 判定範囲と比較範囲のデータの類似度を算出
      - 類似箇所のオフセット（開始・終了位置）を記録

    Args:
        body_text: 判定対象の本文テキスト
        web_results: WebSearchResultのリスト
        threshold: 類似度閾値 (0.0〜1.0)

    Returns:
        SimilarityResult
    """
    result = SimilarityResult()

    # 入力テキストを文節単位に分割
    input_chunks = _split_into_chunks(body_text)
    if not input_chunks:
        return result

    for web_result in web_results:
        for search_result in web_result.results:
            if not search_result.page_text:
                continue

            source_url = search_result.url
            # 照合元テキストをチャンクに分割
            source_chunks = _split_source_into_chunks(search_result.page_text)
            if not source_chunks:
                continue

            # 各入力チャンクを照合元チャンクと比較
            for input_chunk, offset in input_chunks:
                # RapidFuzzのprocess.extractOneで最も類似したソースチャンクを探す
                match = process.extractOne(
                    input_chunk,
                    source_chunks,
                    scorer=fuzz.token_sort_ratio,
                    score_cutoff=threshold * 100,
                )
                if match is None:
                    continue

                matched_text, score, _ = match
                similarity = score / 100.0

                span = MatchSpan(
                    text=input_chunk,
                    start=offset,
                    end=offset + len(input_chunk),
                    similarity=similarity,
                    source_url=source_url,
                    matched_text=matched_text,
                )
                result.spans.append(span)

    # 重複除去: 同じ範囲で複数マッチした場合は最高スコアのみ残す
    result.spans = _deduplicate_spans(result.spans)

    return result


def _deduplicate_spans(spans: list[MatchSpan]) -> list[MatchSpan]:
    """
    重複・包含するスパンを除去し、最高スコアのものを残す
    """
    if not spans:
        return spans

    # 類似度の高い順にソート
    spans_sorted = sorted(spans, key=lambda s: s.similarity, reverse=True)
    kept = []

    for span in spans_sorted:
        overlaps = False
        for existing in kept:
            # オーバーラップ判定
            if span.start < existing.end and span.end > existing.start:
                overlaps = True
                break
        if not overlaps:
            kept.append(span)

    # 位置順にソート
    return sorted(kept, key=lambda s: s.start)
