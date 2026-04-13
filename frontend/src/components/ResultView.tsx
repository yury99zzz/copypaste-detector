import React from "react";
import { MatchResult } from "../api/client";

interface ResultViewProps {
  originalText: string;
  matches: MatchResult[];
}

// 類似度に応じたハイライト色
function getHighlightStyle(match: MatchResult): React.CSSProperties {
  if (match.is_legal_citation) {
    return { backgroundColor: "#dbeafe", borderBottom: "2px solid #3b82f6" }; // 青: 適法引用
  }
  const s = match.similarity;
  if (s >= 0.8) return { backgroundColor: "#fecaca", borderBottom: "2px solid #ef4444" };
  if (s >= 0.5) return { backgroundColor: "#fed7aa", borderBottom: "2px solid #f97316" };
  return { backgroundColor: "#fef9c3", borderBottom: "2px solid #eab308" };
}

interface Segment {
  text: string;
  match?: MatchResult;
}

function buildSegments(text: string, matches: MatchResult[]): Segment[] {
  if (matches.length === 0) return [{ text }];

  // 範囲が重複しないようにソート済みを前提（scorer.pyで保証）
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
  const [tooltip, setTooltip] = React.useState<{ match: MatchResult; x: number; y: number } | null>(null);
  const segments = buildSegments(originalText, matches);

  const illegalMatches = matches.filter((m) => !m.is_legal_citation);
  const legalMatches = matches.filter((m) => m.is_legal_citation);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      {/* 凡例 */}
      <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", fontSize: "12px" }}>
        {[
          { color: "#fecaca", border: "#ef4444", label: "高類似度（≥80%）" },
          { color: "#fed7aa", border: "#f97316", label: "中類似度（50-80%）" },
          { color: "#fef9c3", border: "#eab308", label: "低類似度（<50%）" },
          { color: "#dbeafe", border: "#3b82f6", label: "適法引用" },
        ].map(({ color, border, label }) => (
          <span key={label} style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <span
              style={{
                display: "inline-block",
                width: "14px",
                height: "14px",
                backgroundColor: color,
                borderBottom: `2px solid ${border}`,
              }}
            />
            {label}
          </span>
        ))}
      </div>

      {/* ハイライトテキスト */}
      <div
        style={{
          padding: "16px",
          backgroundColor: "#f9fafb",
          borderRadius: "8px",
          border: "1px solid #e5e7eb",
          lineHeight: "1.8",
          fontSize: "14px",
          whiteSpace: "pre-wrap",
          wordBreak: "break-all",
          position: "relative",
        }}
      >
        {segments.map((seg, i) =>
          seg.match ? (
            <mark
              key={i}
              style={{
                ...getHighlightStyle(seg.match),
                padding: "1px 0",
                cursor: "pointer",
                position: "relative",
              }}
              onMouseEnter={(e) => {
                const rect = (e.target as HTMLElement).getBoundingClientRect();
                setTooltip({ match: seg.match!, x: rect.left, y: rect.bottom + window.scrollY });
              }}
              onMouseLeave={() => setTooltip(null)}
            >
              {seg.text}
            </mark>
          ) : (
            <span key={i}>{seg.text}</span>
          )
        )}
      </div>

      {/* ツールチップ */}
      {tooltip && (
        <div
          style={{
            position: "fixed",
            left: Math.min(tooltip.x, window.innerWidth - 320),
            top: tooltip.y + 4,
            zIndex: 1000,
            backgroundColor: "#1f2937",
            color: "#f9fafb",
            borderRadius: "8px",
            padding: "10px 14px",
            fontSize: "12px",
            maxWidth: "300px",
            boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
            pointerEvents: "none",
          }}
        >
          <div style={{ marginBottom: "4px" }}>
            類似度: <strong>{Math.round(tooltip.match.similarity * 100)}%</strong>
            {tooltip.match.is_legal_citation && (
              <span style={{ marginLeft: "8px", color: "#93c5fd" }}>（適法引用）</span>
            )}
          </div>
          <div
            style={{
              fontSize: "11px",
              color: "#9ca3af",
              wordBreak: "break-all",
            }}
          >
            出典:{" "}
            <a
              href={tooltip.match.source_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "#60a5fa" }}
            >
              {tooltip.match.source_url}
            </a>
          </div>
        </div>
      )}

      {/* 一致箇所リスト */}
      {illegalMatches.length > 0 && (
        <div>
          <h3 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "8px", color: "#374151" }}>
            不適切なコピペ箇所 ({illegalMatches.length}件)
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {illegalMatches.map((m, i) => (
              <div
                key={i}
                style={{
                  padding: "10px 12px",
                  backgroundColor: "#fff",
                  border: "1px solid #e5e7eb",
                  borderLeft: "3px solid #ef4444",
                  borderRadius: "6px",
                  fontSize: "13px",
                }}
              >
                <div style={{ marginBottom: "4px", color: "#374151" }}>
                  「{m.text.length > 60 ? m.text.slice(0, 60) + "…" : m.text}」
                </div>
                <div style={{ display: "flex", gap: "12px", fontSize: "11px", color: "#6b7280" }}>
                  <span>類似度: {Math.round(m.similarity * 100)}%</span>
                  <a
                    href={m.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: "#6366f1", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "300px" }}
                  >
                    {m.source_url}
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {legalMatches.length > 0 && (
        <div>
          <h3 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "8px", color: "#374151" }}>
            適法引用箇所 ({legalMatches.length}件)
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {legalMatches.map((m, i) => (
              <div
                key={i}
                style={{
                  padding: "10px 12px",
                  backgroundColor: "#fff",
                  border: "1px solid #e5e7eb",
                  borderLeft: "3px solid #3b82f6",
                  borderRadius: "6px",
                  fontSize: "13px",
                }}
              >
                <div style={{ marginBottom: "4px", color: "#374151" }}>
                  「{m.text.length > 60 ? m.text.slice(0, 60) + "…" : m.text}」
                </div>
                <div style={{ display: "flex", gap: "12px", fontSize: "11px", color: "#6b7280" }}>
                  <span>類似度: {Math.round(m.similarity * 100)}%</span>
                  <a
                    href={m.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: "#6366f1", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "300px" }}
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
