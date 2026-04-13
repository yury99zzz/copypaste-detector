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
 * 適法引用は青下線のみ
 */
function getHighlightStyle(match: MatchResult): React.CSSProperties | null {
  if (match.is_legal_citation) {
    return {
      borderBottom: "2px solid #3b82f6",
      textDecorationColor: "#3b82f6",
      paddingBottom: "1px",
    };
  }
  const pct = match.similarity * 100;
  if (pct < 20) return null;
  if (pct < 80) {
    return { backgroundColor: "#fef08a", fontWeight: "bold", borderRadius: "2px" };
  }
  return {
    backgroundColor: "#dc2626",
    color: "#ffffff",
    fontWeight: "bold",
    borderRadius: "2px",
  };
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

      {/* 凡例 */}
      <div
        style={{
          display: "flex",
          gap: "16px",
          flexWrap: "wrap",
          padding: "10px 14px",
          backgroundColor: "#f8fafc",
          borderRadius: "8px",
          border: "1px solid #e2e8f0",
        }}
      >
        {[
          { color: "#fef08a", border: "#ca8a04", label: "類似度 20〜80%（要注意）" },
          { color: "#dc2626", border: undefined, label: "類似度 80%以上（ほぼ確実）", textColor: "#fff" },
        ].map(({ color, border, label, textColor }) => (
          <span key={label} style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "11px", color: "#475569" }}>
            <span
              style={{
                display: "inline-block",
                width: "24px",
                height: "12px",
                backgroundColor: color,
                border: border ? `1px solid ${border}` : undefined,
                borderRadius: "2px",
              }}
            />
            {label}
          </span>
        ))}
        <span style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "11px", color: "#475569" }}>
          <span style={{ display: "inline-block", width: "24px", height: "12px", borderBottom: "2px solid #3b82f6" }} />
          適法引用
        </span>
      </div>

      {/* ハイライトテキスト */}
      <div
        style={{
          padding: "18px 20px",
          backgroundColor: "#f8fafc",
          borderRadius: "10px",
          border: "1px solid #e2e8f0",
          lineHeight: "2.0",
          fontSize: "14px",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          color: "#1e293b",
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
                padding: "1px 1px",
                cursor: "pointer",
                outline:
                  activeMatch === seg.match
                    ? "2px solid #6366f1"
                    : undefined,
                outlineOffset: "1px",
                transition: "outline 0.1s",
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

      {/* 選択中箇所の引用元カード */}
      {activeMatch && (
        <div
          style={{
            padding: "14px 18px",
            backgroundColor: "#eff6ff",
            border: "1px solid #bfdbfe",
            borderLeft: "4px solid #3b82f6",
            borderRadius: "10px",
            fontSize: "13px",
          }}
        >
          <div style={{ marginBottom: "6px", color: "#1e40af", fontWeight: 700, fontSize: "12px", letterSpacing: "0.04em", textTransform: "uppercase" }}>
            選択中の一致箇所
          </div>
          <div style={{ marginBottom: "4px", color: "#374151" }}>
            類似度:{" "}
            <strong style={{ color: activeMatch.similarity * 100 >= 80 ? "#dc2626" : "#d97706" }}>
              {Math.round(activeMatch.similarity * 100)}%
            </strong>
            {activeMatch.is_legal_citation && (
              <span style={{ marginLeft: "8px", fontSize: "12px", color: "#2563eb" }}>
                （適法引用）
              </span>
            )}
          </div>
          <div style={{ color: "#374151" }}>
            引用元:{" "}
            <a
              href={activeMatch.source_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "#2563eb", wordBreak: "break-all", fontWeight: 500 }}
            >
              {activeMatch.source_url}
            </a>
          </div>
        </div>
      )}

      {/* 不適切コピペ一覧 */}
      {illegalMatches.length > 0 && (
        <div>
          <div
            style={{
              fontSize: "12px",
              fontWeight: 700,
              color: "#64748b",
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              marginBottom: "10px",
            }}
          >
            コピペ疑い箇所一覧（{illegalMatches.length}件）
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {illegalMatches.map((m, i) => {
              const pct = Math.round(m.similarity * 100);
              const isHigh = pct >= 80;
              return (
                <div
                  key={i}
                  style={{
                    padding: "12px 16px",
                    backgroundColor: "#fff",
                    border: "1px solid #f1f5f9",
                    borderLeft: `4px solid ${isHigh ? "#dc2626" : "#d97706"}`,
                    borderRadius: "8px",
                    fontSize: "13px",
                    boxShadow: "0 1px 4px rgba(0,0,0,0.04)",
                  }}
                >
                  <div style={{ marginBottom: "8px", color: "#1e293b", lineHeight: "1.6" }}>
                    「{m.text.length > 100 ? m.text.slice(0, 100) + "…" : m.text}」
                  </div>
                  <div
                    style={{
                      display: "flex",
                      gap: "12px",
                      alignItems: "center",
                      fontSize: "12px",
                      flexWrap: "wrap",
                    }}
                  >
                    <span
                      style={{
                        fontWeight: 800,
                        color: isHigh ? "#dc2626" : "#d97706",
                        backgroundColor: isHigh ? "#fee2e2" : "#fef3c7",
                        padding: "2px 8px",
                        borderRadius: "4px",
                      }}
                    >
                      類似度 {pct}%
                    </span>
                    <a
                      href={m.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        color: "#4f46e5",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        maxWidth: "500px",
                        fontWeight: 500,
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
          <div
            style={{
              fontSize: "12px",
              fontWeight: 700,
              color: "#64748b",
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              marginBottom: "10px",
            }}
          >
            適法引用箇所（{legalMatches.length}件）
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {legalMatches.map((m, i) => (
              <div
                key={i}
                style={{
                  padding: "12px 16px",
                  backgroundColor: "#fff",
                  border: "1px solid #f1f5f9",
                  borderLeft: "4px solid #3b82f6",
                  borderRadius: "8px",
                  fontSize: "13px",
                  boxShadow: "0 1px 4px rgba(0,0,0,0.04)",
                }}
              >
                <div style={{ marginBottom: "8px", color: "#1e293b", lineHeight: "1.6" }}>
                  「{m.text.length > 100 ? m.text.slice(0, 100) + "…" : m.text}」
                </div>
                <div style={{ display: "flex", gap: "12px", alignItems: "center", fontSize: "12px", flexWrap: "wrap" }}>
                  <span
                    style={{
                      fontWeight: 800,
                      color: "#2563eb",
                      backgroundColor: "#eff6ff",
                      padding: "2px 8px",
                      borderRadius: "4px",
                    }}
                  >
                    類似度 {Math.round(m.similarity * 100)}%
                  </span>
                  <a
                    href={m.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      color: "#4f46e5",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      maxWidth: "500px",
                      fontWeight: 500,
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
