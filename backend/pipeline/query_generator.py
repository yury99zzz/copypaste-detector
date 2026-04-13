"""
STEP 3: 検索キー生成
特許第5510912号 図22・S111-S119に対応
形態素解析結果から出現頻度上位の単語を検索キーとして選定
"""
from collections import Counter
from dataclasses import dataclass


@dataclass
class QueryResult:
    queries: list[str]       # 検索キー（出現頻度順）
    word_freq: dict[str, int]  # 単語→出現頻度


def generate_queries(tokens: list[str], max_queries: int = 5) -> QueryResult:
    """
    STEP 3: 検索キー生成
    特許S111-S119に対応:
      S111: 形態素解析結果を受け取る
      S112: 単語ごとの出現頻度を算出
      S113: 出現頻度の高い順にソート
      S114: 上位N個を検索キーとして指定

    Args:
        tokens: 形態素解析済みトークンリスト（normalized_form）
        max_queries: 最大検索キー数（デフォルト5）

    Returns:
        QueryResult
    """
    if not tokens:
        return QueryResult(queries=[], word_freq={})

    # S112: 出現頻度を算出
    freq = Counter(tokens)

    # S113: 出現頻度の高い順にソート
    sorted_words = freq.most_common()

    # S114: 上位max_queries個を検索キーとして選定
    # ストップワード的な短い単語は除外（1文字は既にpreprocessorで除外済み）
    queries = [word for word, _ in sorted_words[:max_queries]]

    return QueryResult(
        queries=queries,
        word_freq=dict(freq),
    )
