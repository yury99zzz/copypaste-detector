"""
STEP 1-2: 構造解析・前処理・正規化
特許第5510912号 S12-S13に対応
"""
import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

try:
    import sudachipy
    from sudachipy import tokenizer, dictionary
    SUDACHI_AVAILABLE = True
except ImportError:
    SUDACHI_AVAILABLE = False

try:
    import neologdn
    NEOLOGDN_AVAILABLE = True
except ImportError:
    NEOLOGDN_AVAILABLE = False


@dataclass
class PreprocessResult:
    original_text: str
    body_text: str           # 判定対象の本文
    normalized_text: str     # 正規化済みテキスト
    tokens: list[str]        # 形態素解析結果（normalized_form）
    excluded_ranges: list[tuple[int, int]]  # 引用符で除外した範囲


# 構造解析で除外するセクション見出しパターン
EXCLUDED_SECTION_PATTERNS = [
    r"^(はじめに|序論|序章|まとめ|おわりに|結論|結語|謝辞|参考文献|引用文献|注|脚注)\s*$",
    r"^(Introduction|Conclusion|References|Acknowledgements?)\s*$",
]

# 引用符パターン（適法引用として除外）
QUOTE_PATTERNS = [
    r"「[^」]*」",
    r"『[^』]*』",
    r"'[^']*'",
    r'"[^"]*"',
    r"\"[^\"]*\"",
]


def _is_excluded_section(line: str) -> bool:
    """セクション見出しが除外対象かどうかを判定"""
    stripped = line.strip()
    for pattern in EXCLUDED_SECTION_PATTERNS:
        if re.match(pattern, stripped, re.IGNORECASE):
            return True
    return False


def extract_body(text: str) -> str:
    """
    STEP 1: 構造解析 - 本文部分のみを抽出
    「はじめに」「まとめ」「謝辞」「参考文献」等のセクションを除外
    特許S12-S13に対応
    """
    lines = text.splitlines()
    body_lines = []
    in_excluded_section = False

    for line in lines:
        stripped = line.strip()

        # セクション見出しの検出
        if _is_excluded_section(stripped):
            in_excluded_section = True
            continue

        # 新たなセクション（数字付き見出しなど）で除外解除
        if re.match(r"^(\d+[\.\s]|第\d+章|Chapter\s+\d+)", stripped):
            in_excluded_section = False

        if not in_excluded_section:
            body_lines.append(line)

    return "\n".join(body_lines).strip()


def normalize_text(text: str) -> str:
    """
    STEP 2: Unicode NFKC正規化（全角→半角など）
    """
    # Unicode NFKC正規化
    normalized = unicodedata.normalize("NFKC", text)

    # neologdnが使える場合はさらに正規化
    if NEOLOGDN_AVAILABLE:
        normalized = neologdn.normalize(normalized)

    return normalized


def find_quoted_ranges(text: str) -> list[tuple[int, int]]:
    """
    引用符「」''""で括られた箇所のオフセットを検出
    適法引用として除外するための範囲を返す
    """
    ranges = []
    for pattern in QUOTE_PATTERNS:
        for m in re.finditer(pattern, text):
            ranges.append((m.start(), m.end()))
    # ソートして返す
    return sorted(ranges)


def tokenize(text: str) -> list[str]:
    """
    SudachiPyで形態素解析し、normalized_form()を返す
    SudachiPyが利用できない場合は単純な空白分割にフォールバック
    """
    if not SUDACHI_AVAILABLE:
        # フォールバック: 単純な分割（英数字・日本語混在対応）
        tokens = re.findall(r"[一-龥ぁ-んァ-ヶａ-ｚＡ-Ｚ\w]+", text)
        return [t for t in tokens if len(t) > 1]

    try:
        tokenizer_obj = dictionary.Dictionary().create()
        mode = tokenizer.Tokenizer.SplitMode.C
        morphemes = tokenizer_obj.tokenize(text, mode)
        tokens = []
        for m in morphemes:
            part_of_speech = m.part_of_speech()[0]
            # 名詞・動詞・形容詞のみ抽出（助詞・助動詞・記号を除外）
            if part_of_speech in ("名詞", "動詞", "形容詞", "副詞"):
                norm = m.normalized_form()
                if len(norm) > 1:
                    tokens.append(norm)
        return tokens
    except Exception:
        # SudachiPyエラー時のフォールバック
        tokens = re.findall(r"[一-龥ぁ-んァ-ヶａ-ｚＡ-Ｚ\w]+", text)
        return [t for t in tokens if len(t) > 1]


def preprocess(text: str) -> PreprocessResult:
    """
    STEP 1-2の全処理を実行
    Returns PreprocessResult
    """
    # STEP 1: 構造解析・本文抽出
    body_text = extract_body(text)

    # 引用符で除外された範囲を検出（元テキスト上の位置）
    excluded_ranges = find_quoted_ranges(body_text)

    # 引用符内テキストを除いた本文を生成（正規化・形態素解析用）
    text_without_quotes = body_text
    for start, end in sorted(excluded_ranges, reverse=True):
        text_without_quotes = text_without_quotes[:start] + text_without_quotes[end:]

    # STEP 2: 正規化
    normalized_text = normalize_text(text_without_quotes)

    # 形態素解析
    tokens = tokenize(normalized_text)

    return PreprocessResult(
        original_text=text,
        body_text=body_text,
        normalized_text=normalized_text,
        tokens=tokens,
        excluded_ranges=excluded_ranges,
    )
