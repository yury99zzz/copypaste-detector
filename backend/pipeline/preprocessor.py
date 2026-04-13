"""
STEP 1-2: 構造解析・前処理・正規化
特許第5510912号 S12-S13に対応

同義語展開（特許図14・段落0105-0107）:
  SudachiPy の同義語辞書（sudachidict_core/resources/synonym.txt）を使い、
  入力テキストの単語を同義語に置換した複数バリアントを生成する。
  バリアントを検索クエリとして使うことで、
  言い換えコピペ（パラフレーズ）を検出できる。
"""
import logging
import os
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache

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

logger = logging.getLogger(__name__)


@dataclass
class PreprocessResult:
    original_text: str
    body_text: str                          # 判定対象の本文
    normalized_text: str                    # 正規化済みテキスト
    tokens: list[str]                       # 形態素解析結果（normalized_form）
    excluded_ranges: list[tuple[int, int]]  # 引用符で除外した範囲
    synonym_variants: list[str] = field(default_factory=list)
    # 同義語変換バリアント（言い換えコピペ検出用）


# ------------------------------------------------------------------ #
# 構造解析（STEP 1）
# ------------------------------------------------------------------ #

EXCLUDED_SECTION_PATTERNS = [
    r"^(はじめに|序論|序章|まとめ|おわりに|結論|結語|謝辞|参考文献|引用文献|注|脚注)\s*$",
    r"^(Introduction|Conclusion|References|Acknowledgements?)\s*$",
]

QUOTE_PATTERNS = [
    r"「[^」]*」",
    r"『[^』]*』",
    r"'[^']*'",
    r'"[^"]*"',
    r"\"[^\"]*\"",
]


def _is_excluded_section(line: str) -> bool:
    stripped = line.strip()
    for pattern in EXCLUDED_SECTION_PATTERNS:
        if re.match(pattern, stripped, re.IGNORECASE):
            return True
    return False


def extract_body(text: str) -> str:
    """STEP 1: 構造解析 - 本文部分のみを抽出（特許S12-S13）"""
    lines = text.splitlines()
    body_lines = []
    in_excluded_section = False

    for line in lines:
        stripped = line.strip()
        if _is_excluded_section(stripped):
            in_excluded_section = True
            continue
        if re.match(r"^(\d+[\.\s]|第\d+章|Chapter\s+\d+)", stripped):
            in_excluded_section = False
        if not in_excluded_section:
            body_lines.append(line)

    return "\n".join(body_lines).strip()


def find_quoted_ranges(text: str) -> list[tuple[int, int]]:
    """引用符で括られた箇所のオフセットを検出"""
    ranges = []
    for pattern in QUOTE_PATTERNS:
        for m in re.finditer(pattern, text):
            ranges.append((m.start(), m.end()))
    return sorted(ranges)


# ------------------------------------------------------------------ #
# 正規化・形態素解析（STEP 2）
# ------------------------------------------------------------------ #

def normalize_text(text: str) -> str:
    """Unicode NFKC 正規化（全角→半角など）"""
    normalized = unicodedata.normalize("NFKC", text)
    if NEOLOGDN_AVAILABLE:
        normalized = neologdn.normalize(normalized)
    return normalized


def tokenize(text: str) -> list[str]:
    """
    SudachiPy で形態素解析し normalized_form() を返す。
    名詞-普通名詞・名詞-固有名詞のみ抽出。
    SudachiPy 非対応時は正規表現でフォールバック。
    """
    if not SUDACHI_AVAILABLE:
        tokens = re.findall(r"[一-龥ぁ-んァ-ヶａ-ｚＡ-Ｚ\w]+", text)
        return [t for t in tokens if len(t) > 1]

    try:
        tokenizer_obj = dictionary.Dictionary().create()
        mode = tokenizer.Tokenizer.SplitMode.C
        morphemes = tokenizer_obj.tokenize(text, mode)
        tokens = []
        for m in morphemes:
            pos = m.part_of_speech()
            if pos[0] == "名詞" and pos[1] in ("普通名詞", "固有名詞"):
                norm = m.normalized_form()
                if len(norm) > 1:
                    tokens.append(norm)
        return tokens
    except Exception:
        tokens = re.findall(r"[一-龥ぁ-んァ-ヶａ-ｚＡ-Ｚ\w]+", text)
        return [t for t in tokens if len(t) > 1]


# ------------------------------------------------------------------ #
# 同義語辞書のロード（特許図14・段落0105-0107）
# ------------------------------------------------------------------ #

@lru_cache(maxsize=1)
def _build_synonym_index() -> dict[int, list[str]]:
    """
    sudachidict の synonym.txt を読み込み、
    グループID → [語1, 語2, ...] の逆引きインデックスを構築する。

    synonym.txt のCSV列構成（Sudachi公式フォーマット）:
      col[0]  グループID
      col[1]  グループ内番号
      col[2]  出現形使用フラグ
      col[3]  結合フラグ
      col[4]  省略語フラグ
      col[5]  省略形フラグ
      col[6]  修正フラグ
      col[7]  表外語フラグ
      col[8]  品詞
      col[9]  品詞引継ぎフラグ
      col[10] 語義番号
      col[11] 代表語表記  ← ここが語の文字列

    ファイルが見つからない・解析失敗時は空 dict を返す。
    """
    if not SUDACHI_AVAILABLE:
        return {}

    # sudachidict_core / small / full の順に探す
    search_packages = ["sudachidict_core", "sudachidict_small", "sudachidict_full"]
    synonym_path: str | None = None
    for pkg_name in search_packages:
        try:
            pkg = __import__(pkg_name)
            candidate = os.path.join(
                os.path.dirname(pkg.__file__), "resources", "synonym.txt"
            )
            if os.path.exists(candidate):
                synonym_path = candidate
                break
        except ImportError:
            continue

    if synonym_path is None:
        logger.info("synonym.txt not found — synonym expansion disabled")
        return {}

    index: dict[int, list[str]] = {}
    try:
        with open(synonym_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                cols = [c.strip() for c in line.split(",")]
                if len(cols) < 12:
                    continue
                try:
                    group_id = int(cols[0])
                    word = cols[11]
                    if word:
                        index.setdefault(group_id, []).append(word)
                except (ValueError, IndexError):
                    continue
        logger.info(f"Synonym index loaded: {len(index)} groups from {synonym_path}")
    except Exception as e:
        logger.warning(f"Failed to load synonym.txt: {e}")
        return {}

    return index


# ------------------------------------------------------------------ #
# 同義語変換バリアント生成（特許図14）
# ------------------------------------------------------------------ #

def generate_synonym_variants(
    body_text: str,
    max_variants: int = 3,
) -> list[str]:
    """
    SudachiPy の同義語辞書を使って入力テキストの同義語置換バリアントを生成する。

    処理フロー（特許図14 準拠）:
      1. テキストを SudachiPy で形態素解析（SplitMode C）
      2. synonym_group_ids() を持つ形態素を特定
      3. 同義語インデックスから代替語を取得
      4. 代替語に置換したテキストバリアントを生成（1バリアント = 1語置換）

    例:
      入力:  "強酸性電解水は殺菌効果が高い"
      出力:  ["強酸性電解水は抗菌効果が高い",   # 殺菌→抗菌
              "強酸性電解水は除菌効果が高い",   # 殺菌→除菌
              "電解水は殺菌効果が高い"]          # 強酸性電解水→電解水

    Args:
        body_text:    元テキスト
        max_variants: 生成するバリアント数の上限（デフォルト 3）

    Returns:
        同義語置換したテキストのリスト（最大 max_variants 件）
        SudachiPy 非対応・同義語なし・エラー時は空リスト
    """
    if not SUDACHI_AVAILABLE:
        return []

    synonym_index = _build_synonym_index()
    if not synonym_index:
        return []

    try:
        tokenizer_obj = dictionary.Dictionary().create()
        mode = tokenizer.Tokenizer.SplitMode.C
        morphemes = list(tokenizer_obj.tokenize(body_text, mode))

        # 同義語を持つ形態素の収集: (begin, end, surface, [synonym1, synonym2, ...])
        candidates: list[tuple[int, int, str, list[str]]] = []
        for m in morphemes:
            group_ids = m.synonym_group_ids()
            if not group_ids:
                continue

            surface = m.surface()
            synonyms: list[str] = []
            for gid in group_ids:
                for word in synonym_index.get(gid, []):
                    # 表記が同じ語・重複は除外
                    if word != surface and word != m.normalized_form() and word not in synonyms:
                        synonyms.append(word)

            if synonyms:
                candidates.append((m.begin(), m.end(), surface, synonyms[:3]))

        if not candidates:
            return []

        # バリアント生成: 候補の先頭から max_variants 個を 1 語ずつ置換
        variants: list[str] = []
        for begin, end, _surface, synonyms in candidates[:max_variants]:
            variant = body_text[:begin] + synonyms[0] + body_text[end:]
            if variant not in variants:
                variants.append(variant)

        logger.debug(
            f"Synonym variants generated: {len(variants)} "
            f"(candidates={len(candidates)})"
        )
        return variants

    except Exception as e:
        logger.warning(f"Synonym variant generation failed: {e}")
        return []


# ------------------------------------------------------------------ #
# メイン関数
# ------------------------------------------------------------------ #

def preprocess(text: str) -> PreprocessResult:
    """STEP 1-2 の全処理を実行する"""
    # STEP 1: 構造解析・本文抽出
    body_text = extract_body(text)

    # 引用符で除外された範囲を検出
    excluded_ranges = find_quoted_ranges(body_text)

    # 引用符内テキストを除いた本文（正規化・形態素解析用）
    text_without_quotes = body_text
    for start, end in sorted(excluded_ranges, reverse=True):
        text_without_quotes = text_without_quotes[:start] + text_without_quotes[end:]

    # STEP 2: 正規化・形態素解析
    normalized_text = normalize_text(text_without_quotes)
    tokens = tokenize(normalized_text)

    # 同義語変換バリアントを生成（言い換えコピペ検出用）
    synonym_variants = generate_synonym_variants(body_text)

    return PreprocessResult(
        original_text=text,
        body_text=body_text,
        normalized_text=normalized_text,
        tokens=tokens,
        excluded_ranges=excluded_ranges,
        synonym_variants=synonym_variants,
    )
