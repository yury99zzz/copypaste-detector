import React from "react";
import { MatchResult } from "../api/client";

interface ResultViewProps {
  originalText: string;
  matches: MatchResult[];
}

/**
 * 特許第5510912号 図37に準拠したハイライトスタイル
 *   0  ≤ S < 20%: 通常（ハイライトなし）
 *   20 ≤ S < 80%: 黄色ハイライト（太字）
 *   80 ≤ S ≤ 100%: 赤反転（白文字・赤背景）
 *
 * 適法引用は青下線のみで示す（コピペとはカウントしない）
 */
function getHighlightStyle(match: MatchResult): React.CSSProperties | null {
  if (match.is_legal_citation) {
    return {
      borderBottom: "2px solid #3b82f6",
      textDecoration: "underline",
      textDecorationColor: "#3b82f6",
    };
  }
  const pct = match.similarity * 100;
  if (pct < 20) return null; // 通常表示
  if (pct < 80) {
    // 黄色ハイライト（太字）
    return { backgroundColor: "#fef08a", fontWeight: "bold" };
  }
  // 赤反転
  return { backgroundColor: "#dc2626", color: "#ffffff", fontWeight: "bold" };
}

interface Segment {
  text: string;
  match?: MatchResult;
}

function buildSegments(text: string, matches: MatchResult[]): Segment[] {
  if (matches.length === 0) return [{ text }];

  const sorted = [...matches].sort((a, b) => a.start - b.start);
  const segments: Segment[] = [];
  let cursor = 0;

  for (const match of sorted) {
    if (match.start > cursor) {
      segments.push({ text: text.slice(cursor, match.start) });
    }
    if (match.end > match.start) {
      segments.push({ text: text.slice(match.start, match.end), match });
    }
    cursor = match.end;
  }

  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor) });
  }

  return segments;
}

const ResultView: React.FC<ResultViewProps> = ({ originalText, matches }) => {
  const [activeMatch, setActiveMatch] = React.useState<MatchResult | null>(null);
  const segments = buildSegments(originalText, matches);

  const illegalMatches = matches.filter((m) => !m.is_legal_citation);
  const legalMatches = matches.filter((m) => m.is_legal_citation);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* 凡例（特許図37準拠） */}
      <div style={{ display: "flex", gap: "20px", flexWrap: "wrap", fontSize: "12px", color: "#374151" }}>
        <span style={{ display: "flex", alignItems: "center", gap: "5px" }}>
          <span style={{ display: "inline-block", width: "28px", height: "14px", backgroundColor: "#fef08a", border: "1px solid #ca8a04" }} />
          類似度 20〜80%（要注意）
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: "5px" }}>
          <span style={{ display: "inline-block", width: "28px", height: "14px", backgroundColor: "#dc2626" }} />
          類似度 80%以上（ほぼ確実）
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: "5px" }}>
          <span style={{ display: "inline-block", width: "28px", height: "14px", borderBottom: "2px solid #3b82f6" }} />
          適法引用
        </span>
      </div>

      {/* ハイライトテキスト */}
      <div
        style={{
          padding: "16px",
          backgroundColor: "#f9fafb",
          borderRadius: "8px",
          border: "1px solid #e5e7eb",
          lineHeight: "1.9",
          fontSize: "14px",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}
      >
        {segments.map((seg, i) => {
          if (!seg.match) return <span key={i}>{seg.text}</span>;
          const style = getHighlightStyle(seg.match);
          if (!style) return <span key={i}>{seg.text}</span>;
          return (
            <mark
              key={i}
              style={{
                ...style,
                padding: "1px 0",
                cursor: "pointer",
                outline: activeMatch === seg.match ? "2px solid #6366f1" : undefined,
              }}
              onClick={() =>
                setActiveMatch(activeMatch === seg.match ? null : seg.match!)
              }
            >
              {seg.text}
            </mark>
          );
        })}
      </div>

      {/* クリックした箇所の引用元URL */}
      {activeMatch && (
        <div
          style={{
            padding: "12px 16px",
            backgroundColor: "#eff6ff",
            border: "1px solid #bfdbfe",
            borderRadius: "8px",
            fontSize: "13px",
          }}
        >
          <div style={{ marginBottom: "6px", color: "#1e40af", fontWeight: 600 }}>
            選択中の一致箇所
          </div>
          <div style={{ marginBottom: "4px", color: "#374151" }}>
            類似度:{" "}
            <strong>{Math.round(activeMatch.similarity * 100)}%</strong>
            {activeMatch.is_legal_citation && (
              <span style={{ marginLeft: "8px", color: "#2563eb" }}>（適法引用）</span>
            )}
          </div>
          <div style={{ color: "#374151" }}>
            引用元:{" "}
            <a
              href={activeMatch.source_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "#2563eb", wordBreak: "break-all" }}
            >
              {activeMatch.source_url}
            </a>
          </div>
        </div>
      )}

      {/* 不適切コピペ一覧 */}
      {illegalMatches.length > 0 && (
        <div>
          <h3
            style={{
              fontSize: "14px",
              fontWeight: 600,
              marginTop: 0,
              marginBottom: "8px",
              color: "#374151",
            }}
          >
            コピペ箇所一覧（{illegalMatches.length}件）
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            {illegalMatches.map((m, i) => {
              const pct = Math.round(m.similarity * 100);
              const isHigh = pct >= 80;
              return (
                <div
                  key={i}
                  style={{
                    padding: "10px 14px",
                    backgroundColor: "#fff",
                    border: "1px solid #e5e7eb",
                    borderLeft: `4px solid ${isHigh ? "#dc2626" : "#ca8a04"}`,
                    borderRadius: "6px",
                    fontSize: "13px",
                  }}
                >
                  <div style={{ marginBottom: "6px", color: "#111827" }}>
                    「{m.text.length > 80 ? m.text.slice(0, 80) + "…" : m.text}」
                  </div>
                  <div
                    style={{
                      display: "flex",
                      gap: "12px",
                      alignItems: "center",
                      fontSize: "12px",
                      color: "#6b7280",
                      flexWrap: "wrap",
                    }}
                  >
                    <span
                      style={{
                        fontWeight: 700,
                        color: isHigh ? "#dc2626" : "#ca8a04",
                      }}
                    >
                      類似度 {pct}%
                    </span>
                    <a
                      href={m.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        color: "#2563eb",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        maxWidth: "480px",
                      }}
                    >
                      {m.source_url}
                    </a>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 適法引用一覧 */}
      {legalMatches.length > 0 && (
        <div>
          <h3
            style={{
              fontSize: "14px",
              fontWeight: 600,
              marginTop: 0,
              marginBottom: "8px",
              color: "#374151",
            }}
          >
            適法引用箇所（{legalMatches.length}件）
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            {legalMatches.map((m, i) => (
              <div
                key={i}
                style={{
                  padding: "10px 14px",
                  backgroundColor: "#fff",
                  border: "1px solid #e5e7eb",
                  borderLeft: "4px solid #3b82f6",
                  borderRadius: "6px",
                  fontSize: "13px",
                }}
              >
                <div style={{ marginBottom: "6px", color: "#111827" }}>
                  「{m.text.length > 80 ? m.text.slice(0, 80) + "…" : m.text}」
                </div>
                <div
                  style={{
                    display: "flex",
                    gap: "12px",
                    alignItems: "center",
                    fontSize: "12px",
                    color: "#6b7280",
                    flexWrap: "wrap",
                  }}
                >
                  <span style={{ fontWeight: 700, color: "#2563eb" }}>
                    類似度 {Math.round(m.similarity * 100)}%
                  </span>
                  <a
                    href={m.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      color: "#2563eb",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      maxWidth: "480px",
                    }}
                  >
                    {m.source_url}
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ResultView;
