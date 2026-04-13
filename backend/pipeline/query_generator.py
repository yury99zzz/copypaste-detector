"""
STEP 3: 検索キー生成
特許第5510912号 図22・S111-S119に対応
形態素解析結果から出現頻度上位の単語を検索キーとして選定
"""
from collections import Counter
from dataclasses import dataclass

# 機能語・形式名詞・指示語・接続詞などのストップワード
# SudachiPyで名詞として抽出されうるが検索キーとして不適切な語を除外
STOPWORDS: frozenset[str] = frozenset([
    # 形式名詞・汎用名詞
    "こと", "もの", "ため", "とき", "ところ", "わけ", "はず", "うえ",
    "なか", "まま", "ほう", "かた", "つもり", "おり", "ゆえ", "さい",
    # 指示語
    "これ", "それ", "あれ", "どれ", "ここ", "そこ", "あそこ",
    "この", "その", "あの", "どの", "こちら", "そちら", "あちら",
    # 動詞（SudachiPyが名詞化して返す場合がある）
    "する", "ある", "いる", "なる", "できる", "おこなう", "行う",
    "おける", "おいて", "ついて", "よる", "たる", "みる",
    # 接続・副詞的表現
    "また", "および", "さらに", "ただし", "なお", "すなわち",
    "したがって", "よって", "ゆえに", "しかし", "ところが", "ために",
    "つまり", "もしくは", "あるいは", "または", "かつ", "ならびに",
    # 数量・程度
    "など", "ほど", "くらい", "ごと", "以上", "以下", "以外",
    "全て", "すべて", "各", "各々", "それぞれ",
    # その他の高頻度汎用語
    "場合", "必要", "可能", "問題", "方法", "結果", "影響",
    "関係", "状態", "内容", "情報", "利用", "使用", "対象",
])


@dataclass
class QueryResult:
    queries: list[str]         # 検索キー（出現頻度順）
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
        tokens: 形態素解析済みトークンリスト（normalized_form・名詞のみ）
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

    # S114: ストップワードを除外したうえで上位max_queries個を選定
    queries = [
        word for word, _ in sorted_words
        if word not in STOPWORDS
    ][:max_queries]

    return QueryResult(
        queries=queries,
        word_freq=dict(freq),
    )
