import React, { useState } from "react";
import TextInput from "./components/TextInput";
import ScoreBar from "./components/ScoreBar";
import ResultView from "./components/ResultView";
import { checkText, CheckResponse } from "./api/client";

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
        // 特許図37に合わせ、20%以上の類似箇所をすべて検出
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
        backgroundColor: "#f3f4f6",
        fontFamily: "'Hiragino Sans', 'Noto Sans JP', sans-serif",
      }}
    >
      {/* ヘッダー */}
      <header
        style={{
          backgroundColor: "#6366f1",
          color: "#fff",
          padding: "16px 24px",
          boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
        }}
      >
        <div style={{ maxWidth: "860px", margin: "0 auto" }}>
          <h1 style={{ margin: 0, fontSize: "20px", fontWeight: 700 }}>
            コピペ検出ツール
          </h1>
          <p style={{ margin: "4px 0 0", fontSize: "13px", opacity: 0.85 }}>
            大学レポートのコピペ・剽窃をWebと照合して検出します
          </p>
        </div>
      </header>

      {/* メインコンテンツ */}
      <main style={{ maxWidth: "860px", margin: "0 auto", padding: "24px 16px" }}>
        {/* 入力パネル */}
        <div
          style={{
            backgroundColor: "#fff",
            borderRadius: "12px",
            padding: "24px",
            boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
            marginBottom: "20px",
          }}
        >
          <TextInput
            value={inputText}
            onChange={setInputText}
            onSubmit={handleSubmit}
            isLoading={isLoading}
          />
        </div>

        {/* ローディング */}
        {isLoading && (
          <div
            style={{
              backgroundColor: "#fff",
              borderRadius: "12px",
              padding: "32px",
              textAlign: "center",
              boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
              color: "#6b7280",
            }}
          >
            <div
              style={{
                display: "inline-block",
                width: "32px",
                height: "32px",
                border: "3px solid #e5e7eb",
                borderTop: "3px solid #6366f1",
                borderRadius: "50%",
                animation: "spin 0.8s linear infinite",
                marginBottom: "12px",
              }}
            />
            <p style={{ margin: 0, fontSize: "14px" }}>
              Webと照合中です。しばらくお待ちください...
            </p>
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          </div>
        )}

        {/* エラー */}
        {error && (
          <div
            style={{
              backgroundColor: "#fef2f2",
              border: "1px solid #fca5a5",
              borderRadius: "12px",
              padding: "16px 20px",
              color: "#991b1b",
              fontSize: "14px",
            }}
          >
            エラー: {error}
          </div>
        )}

        {/* 結果 */}
        {result && !isLoading && (
          <>
            {/* 引用割合スコア（画面上部に大きく） */}
            <div
              style={{
                backgroundColor: "#fff",
                borderRadius: "12px",
                padding: "24px",
                boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
                marginBottom: "20px",
              }}
            >
              <ScoreBar
                score={result.total_score}
                status={result.status}
                processingTime={result.processing_time}
              />
            </div>

            {/* ハイライト結果 */}
            <div
              style={{
                backgroundColor: "#fff",
                borderRadius: "12px",
                padding: "24px",
                boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
              }}
            >
              <h2
                style={{
                  fontSize: "15px",
                  fontWeight: 600,
                  marginTop: 0,
                  marginBottom: "16px",
                  color: "#374151",
                }}
              >
                検出結果
              </h2>
              {result.matches.length === 0 ? (
                <p style={{ color: "#6b7280", fontSize: "14px" }}>
                  コピペと判定された箇所はありませんでした。
                </p>
              ) : (
                <ResultView
                  originalText={inputText}
                  matches={result.matches}
                />
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
};

export default App;
