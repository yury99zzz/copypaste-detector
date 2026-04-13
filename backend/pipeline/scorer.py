"""
STEP 7: スコア集計・出力
特許第5510912号 段落0171-0173・図37に対応
"""
from dataclasses import dataclass, field

from pipeline.legality_checker import LegalityResult


@dataclass
class MatchOutput:
    text: str
    start: int
    end: int
    similarity: float
    source_url: str
    is_legal_citation: bool


@dataclass
class ScoreOutput:
    total_score: float                          # 引用割合(%)
    status: str                                 # "ok" | "warning" | "danger" | "critical"
    matches: list[MatchOutput] = field(default_factory=list)
    per_source_scores: dict[str, float] = field(default_factory=dict)
    # 文献ごとの引用割合(%) — 特許図31・33準拠


def _status_from_score(score: float) -> str:
    """
    特許図37の色分けに対応するステータスを返す
      0〜20%  → ok      （緑・問題なし）
      20〜50% → warning （黄・要注意）
      50〜80% → danger  （オレンジ・高リスク）
      80%以上 → critical（赤・ほぼ確実）
    """
    if score < 20:
        return "ok"
    elif score < 50:
        return "warning"
    elif score < 80:
        return "danger"
    else:
        return "critical"


def compute_score(
    legality_results: list[LegalityResult],
    body_text: str,
) -> ScoreOutput:
    """
    STEP 7: スコア集計
    特許段落0171-0173に対応:
      引用割合(%) = 引用部分の文字数 / 判定範囲の文字数 × 100

    適法引用はスコアから除外（不適法な引用のみカウント）

    Args:
        legality_results: 適法性判定済みのリスト
        body_text: 判定対象の本文テキスト

    Returns:
        ScoreOutput
    """
    total_chars = len(body_text)
    if total_chars == 0:
        return ScoreOutput(total_score=0.0, status="ok")

    # 不適法な引用箇所の文字数を合算（重複範囲は1回カウント）
    illegal_ranges: list[tuple[int, int]] = []
    matches: list[MatchOutput] = []

    for lr in legality_results:
        span = lr.span
        matches.append(MatchOutput(
            text=span.text,
            start=span.start,
            end=span.end,
            similarity=span.similarity,
            source_url=span.source_url,
            is_legal_citation=lr.is_legal,
        ))

        if not lr.is_legal:
            illegal_ranges.append((span.start, span.end))

    # 重複範囲をマージしてユニークな文字数を算出
    merged = _merge_ranges(illegal_ranges)
    illegal_chars = sum(end - start for start, end in merged)

    total_score = (illegal_chars / total_chars) * 100

    # 文献ごとの引用割合（特許図31・33準拠）
    per_source_ranges: dict[str, list[tuple[int, int]]] = {}
    for lr in legality_results:
        if not lr.is_legal:
            url = lr.span.source_url
            per_source_ranges.setdefault(url, []).append((lr.span.start, lr.span.end))

    per_source_scores: dict[str, float] = {}
    for url, ranges in per_source_ranges.items():
        source_merged = _merge_ranges(ranges)
        source_chars = sum(end - start for start, end in source_merged)
        per_source_scores[url] = round((source_chars / total_chars) * 100, 1)

    return ScoreOutput(
        total_score=round(total_score, 1),
        status=_status_from_score(total_score),
        matches=matches,
        per_source_scores=per_source_scores,
    )


def _merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """重複・隣接する範囲をマージ"""
    if not ranges:
        return []
    sorted_ranges = sorted(ranges)
    merged = [sorted_ranges[0]]
    for start, end in sorted_ranges[1:]:
        if start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged
