"""
STEP 6: 適法性判定
類似箇所が適法な引用かどうかを判定
特許第5510912号 図29・SC1-SC5に対応
"""
import re
from dataclasses import dataclass

from pipeline.similarity import MatchSpan


@dataclass
class LegalityResult:
    span: MatchSpan
    is_legal: bool
    reason: str   # 適法と判定した根拠


# 出典情報のパターン（URL、著者名、書名など）
_URL_PATTERN = re.compile(r"https?://\S+")
_REFERENCE_PATTERNS = [
    re.compile(r"（\d+）"),           # 参考文献番号 （1）
    re.compile(r"\[\d+\]"),           # 参考文献番号 [1]
    re.compile(r"（著者[:：]"),
    re.compile(r"（出典[:：]"),
    re.compile(r"（参照[:：]"),
    re.compile(r"参考文献"),
    re.compile(r"出典"),
    re.compile(r"引用元"),
]

# 引用符パターン
_QUOTE_OPEN = re.compile(r"[「『""']")
_QUOTE_CLOSE = re.compile(r"[」』""']")

# 出典情報として認識する単語
_CITATION_KEYWORDS = ["著", "著者", "出版", "発行", "p\.", "pp\.", "vol\.", "頁"]
_CITATION_PATTERN = re.compile("|".join(_CITATION_KEYWORDS), re.IGNORECASE)


def _context_window(text: str, start: int, end: int, window: int = 50) -> tuple[str, str]:
    """スパンの前後window文字のコンテキストを返す"""
    before = text[max(0, start - window):start]
    after = text[end:min(len(text), end + window)]
    return before, after


def check_legality(spans: list[MatchSpan], body_text: str) -> list[LegalityResult]:
    """
    STEP 6: 適法性判定
    特許SC3に対応する4条件を確認:
      ① 引用部分の前後に「」や""がある
      ② 引用部分の直後に参考文献番号がある
      ③ 引用部分の下方近傍に書籍名・著者名・出版社名がある
      ④ URLが近傍にある

    Args:
        spans: 類似箇所のリスト
        body_text: 判定対象の本文テキスト

    Returns:
        list[LegalityResult]
    """
    results = []

    for span in spans:
        before, after = _context_window(body_text, span.start, span.end, window=80)
        is_legal = False
        reason = ""

        # ① 前後に引用符がある
        if _QUOTE_OPEN.search(before) and _QUOTE_CLOSE.search(after):
            is_legal = True
            reason = "引用符で囲まれている"

        # ② 直後に参考文献番号がある
        elif any(p.search(after[:30]) for p in _REFERENCE_PATTERNS):
            is_legal = True
            reason = "参考文献番号が直後にある"

        # ③ 近傍に著者名・出版社名・URL がある
        elif _URL_PATTERN.search(after) or _URL_PATTERN.search(before):
            is_legal = True
            reason = "出典URLが近傍にある"

        elif _CITATION_PATTERN.search(after) or _CITATION_PATTERN.search(before):
            is_legal = True
            reason = "出典情報（著者・出版等）が近傍にある"

        results.append(LegalityResult(span=span, is_legal=is_legal, reason=reason))

    return results
