import React, { useState } from "react";
import TextInput from "./components/TextInput";
import ScoreBar from "./components/ScoreBar";
import ResultView from "./components/ResultView";
import { checkText, CheckResponse } from "./api/client";

// ------------------------------------------------------------------ //
// フッターデータ
// ------------------------------------------------------------------ //

const FOOTER_SECTIONS = [
  {
    title: "このツールについて",
    full: true,
    content: `特許第5510912号（コピペルナー・株式会社アンク）のメカニズムを参考に実装したコピペ検出ツールです。32文字単位でテキストを区切りWeb上の文献と照合するスライディングウィンドウ方式と、約6万語の同義語辞書（SudachiDict）による同義語・類義語の展開を組み合わせることで以下のコピペパターンを検出できます。`,
    bullets: [
      "Webページからの全文コピー（検出率約99%）",
      "語尾や文末表現を変えたコピー（検出率約94〜100%）",
      "複数箇所から少しずつコピーして組み合わせたもの（検出率約91%）",
      "「主張した→説いた」「誕生→生じ」などの同義語・類義語への言い換え（検出率約50%）",
    ],
  },
];

const FOOTER_COLS = [
  {
    title: "使用上の注意",
    items: [
      "J-STAGE等の学術論文からのコピーは検出されます",
      "このツールで検出されなくても安全とは限りません",
      "検出結果はあくまで参考値です",
    ],
  },
  {
    title: "免責事項",
    items: [
      "本ツールは教育・研究目的で作成された非商用ツールです",
      "検出結果の正確性を保証するものではありません",
      "個人・非商用利用のみを想定しています",
    ],
  },
  {
    title: "製作者",
    items: [
      "Y.S.",
      "参考：特許第5510912号",
      "（引用判定支援装置および引用判定支援プログラム）",
    ],
  },
];

// ------------------------------------------------------------------ //
// App
// ------------------------------------------------------------------ //

const App: React.FC = () => {
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<CheckResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await checkText(inputText, {
        threshold: 0.2,
        max_queries: 5,
        exclude_quotes: true,
      });
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "不明なエラーが発生しました");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: "#f1f5f9",
        fontFamily: "'Hiragino Sans', 'Noto Sans JP', sans-serif",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* ── ヘッダー ── */}
      <header
        style={{
          background: "linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)",
          color: "#fff",
          padding: "0",
          boxShadow: "0 4px 24px rgba(0,0,0,0.35)",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* 装飾グロー */}
        <div
          style={{
            position: "absolute",
            top: "-60px",
            right: "-60px",
            width: "280px",
            height: "280px",
            background: "radial-gradient(circle, rgba(99,102,241,0.25) 0%, transparent 70%)",
            pointerEvents: "none",
          }}
        />
        <div style={{ maxWidth: "900px", margin: "0 auto", padding: "22px 24px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
            {/* アイコンバッジ */}
            <div
              style={{
                width: "40px",
                height: "40px",
                borderRadius: "10px",
                background: "linear-gradient(135deg, #6366f1, #818cf8)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "20px",
                flexShrink: 0,
                boxShadow: "0 2px 8px rgba(99,102,241,0.5)",
              }}
            >
              🔍
            </div>
            <div>
              <h1 style={{ margin: 0, fontSize: "20px", fontWeight: 800, letterSpacing: "-0.3px" }}>
                コピペ検出ツール
              </h1>
              <p style={{ margin: "2px 0 0", fontSize: "12px", color: "#a5b4fc", fontWeight: 400 }}>
                大学レポートのコピペ・剽窃をWebと照合して検出 / 特許第5510912号準拠
              </p>
            </div>
          </div>
        </div>
        {/* 下部アクセントライン */}
        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            right: 0,
            height: "2px",
            background: "linear-gradient(90deg, #6366f1, #a78bfa, #38bdf8)",
          }}
        />
      </header>

      {/* ── メインコンテンツ ── */}
      <main style={{ flex: 1, maxWidth: "900px", width: "100%", margin: "0 auto", padding: "32px 16px 40px" }}>

        {/* 入力パネル */}
        <Card>
          <SectionTitle>レポート本文を貼り付けてください</SectionTitle>
          <TextInput
            value={inputText}
            onChange={setInputText}
            onSubmit={handleSubmit}
            isLoading={isLoading}
          />
        </Card>

        {/* ローディング */}
        {isLoading && (
          <Card style={{ textAlign: "center", padding: "40px 24px" }}>
            <Spinner />
            <p style={{ margin: "14px 0 0", fontSize: "14px", color: "#64748b" }}>
              Webと照合中です。しばらくお待ちください…
            </p>
            <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#94a3b8" }}>
              最大25秒かかる場合があります
            </p>
          </Card>
        )}

        {/* エラー */}
        {error && (
          <div
            style={{
              marginTop: "20px",
              padding: "16px 20px",
              backgroundColor: "#fef2f2",
              border: "1px solid #fca5a5",
              borderLeft: "4px solid #ef4444",
              borderRadius: "12px",
              color: "#991b1b",
              fontSize: "14px",
            }}
          >
            <strong>エラー:</strong> {error}
          </div>
        )}

        {/* 結果 */}
        {result && !isLoading && (
          <>
            {/* スコアカード */}
            <Card style={{ marginTop: "20px" }}>
              <SectionTitle>判定結果</SectionTitle>
              <ScoreBar
                score={result.total_score}
                status={result.status}
                processingTime={result.processing_time}
                perSourceScores={result.per_source_scores}
              />
            </Card>

            {/* ハイライトカード */}
            <Card style={{ marginTop: "20px" }}>
              <SectionTitle>
                本文ハイライト
                {result.matches.length > 0 && (
                  <span
                    style={{
                      marginLeft: "10px",
                      fontSize: "12px",
                      fontWeight: 500,
                      color: "#6b7280",
                    }}
                  >
                    {result.matches.filter(m => !m.is_legal_citation).length} 件のコピペ疑い箇所
                  </span>
                )}
              </SectionTitle>
              {result.matches.length === 0 ? (
                <div
                  style={{
                    padding: "24px",
                    textAlign: "center",
                    color: "#64748b",
                    fontSize: "14px",
                    background: "#f8fafc",
                    borderRadius: "10px",
                  }}
                >
                  コピペと判定された箇所はありませんでした。
                </div>
              ) : (
                <ResultView originalText={inputText} matches={result.matches} />
              )}
            </Card>
          </>
        )}
      </main>

      {/* ── フッター ── */}
      <Footer />
    </div>
  );
};

// ------------------------------------------------------------------ //
// 共通コンポーネント
// ------------------------------------------------------------------ //

const Card: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({
  children,
  style,
}) => (
  <div
    style={{
      backgroundColor: "#fff",
      borderRadius: "16px",
      padding: "28px",
      boxShadow: "0 1px 3px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.06)",
      border: "1px solid rgba(0,0,0,0.05)",
      ...style,
    }}
  >
    {children}
  </div>
);

const SectionTitle: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div
    style={{
      fontSize: "14px",
      fontWeight: 700,
      color: "#1e293b",
      marginBottom: "16px",
      display: "flex",
      alignItems: "center",
      gap: "8px",
    }}
  >
    {children}
  </div>
);

const Spinner: React.FC = () => (
  <>
    <div
      style={{
        display: "inline-block",
        width: "36px",
        height: "36px",
        border: "3px solid #e2e8f0",
        borderTop: "3px solid #6366f1",
        borderRadius: "50%",
        animation: "spin 0.8s linear infinite",
      }}
    />
    <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
  </>
);

// ------------------------------------------------------------------ //
// フッター
// ------------------------------------------------------------------ //

const Footer: React.FC = () => (
  <footer
    style={{
      background: "linear-gradient(180deg, #0f172a 0%, #1e293b 100%)",
      color: "#cbd5e1",
      paddingTop: "48px",
      paddingBottom: "24px",
      marginTop: "auto",
    }}
  >
    <div style={{ maxWidth: "900px", margin: "0 auto", padding: "0 24px" }}>

      {/* このツールについて（フル幅） */}
      {FOOTER_SECTIONS.map((sec) => (
        <div key={sec.title} style={{ marginBottom: "36px" }}>
          <FooterHeading>{sec.title}</FooterHeading>
          <p style={{ margin: "0 0 12px", fontSize: "13px", lineHeight: "1.8", color: "#94a3b8" }}>
            {sec.content}
          </p>
          <ul style={{ margin: 0, padding: "0 0 0 18px", display: "flex", flexDirection: "column", gap: "4px" }}>
            {sec.bullets?.map((b) => (
              <li key={b} style={{ fontSize: "13px", lineHeight: "1.7", color: "#94a3b8" }}>
                {b}
              </li>
            ))}
          </ul>
        </div>
      ))}

      {/* 区切り線 */}
      <div style={{ height: "1px", background: "rgba(255,255,255,0.07)", marginBottom: "36px" }} />

      {/* 3カラム */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "32px",
          marginBottom: "36px",
        }}
      >
        {FOOTER_COLS.map((col) => (
          <div key={col.title}>
            <FooterHeading>{col.title}</FooterHeading>
            <ul style={{ margin: 0, padding: "0 0 0 0", listStyle: "none", display: "flex", flexDirection: "column", gap: "6px" }}>
              {col.items.map((item, i) => (
                <li key={i} style={{ fontSize: "13px", lineHeight: "1.7", color: "#94a3b8" }}>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {/* 区切り線 */}
      <div style={{ height: "1px", background: "rgba(255,255,255,0.07)", marginBottom: "20px" }} />

      {/* コピーライト */}
      <p style={{ margin: 0, fontSize: "11px", color: "#475569", textAlign: "center" }}>
        本ツールは非商用・教育目的で作成されました。特許権の侵害を意図するものではありません。
      </p>
    </div>
  </footer>
);

const FooterHeading: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <h3
    style={{
      margin: "0 0 12px",
      fontSize: "12px",
      fontWeight: 700,
      textTransform: "uppercase",
      letterSpacing: "0.08em",
      color: "#a5b4fc",
    }}
  >
    {children}
  </h3>
);

export default App;
