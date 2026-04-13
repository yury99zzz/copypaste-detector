import React from "react";

type Status = "ok" | "warning" | "danger" | "critical";

const STATUS_CONFIG: Record<Status, { label: string; color: string; bg: string; border: string }> = {
  ok:       { label: "引用なし",   color: "#166534", bg: "#dcfce7", border: "#86efac" },
  warning:  { label: "要注意",     color: "#92400e", bg: "#fef3c7", border: "#fcd34d" },
  danger:   { label: "高リスク",   color: "#9a3412", bg: "#ffedd5", border: "#fb923c" },
  critical: { label: "ほぼ確実",   color: "#7f1d1d", bg: "#fee2e2", border: "#fca5a5" },
};

const SCORE_COLOR: Record<Status, string> = {
  ok:       "#16a34a",
  warning:  "#d97706",
  danger:   "#ea580c",
  critical: "#dc2626",
};

const BAR_GRADIENT: Record<Status, string> = {
  ok:       "linear-gradient(90deg, #4ade80, #16a34a)",
  warning:  "linear-gradient(90deg, #fde68a, #d97706)",
  danger:   "linear-gradient(90deg, #fdba74, #ea580c)",
  critical: "linear-gradient(90deg, #fca5a5, #dc2626)",
};

interface ScoreBarProps {
  score: number;
  status: Status;
  processingTime?: number;
  perSourceScores?: Record<string, number>;
}

function _hostname(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

const ScoreBar: React.FC<ScoreBarProps> = ({ score, status, processingTime, perSourceScores }) => {
  const cfg = STATUS_CONFIG[status];
  const barWidth = Math.min(score, 100);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>

      {/* スコア + ステータスバッジ */}
      <div style={{ display: "flex", alignItems: "center", gap: "20px", flexWrap: "wrap" }}>
        {/* 大きな数字 */}
        <div style={{ lineHeight: 1 }}>
          <div style={{ fontSize: "11px", fontWeight: 600, color: "#94a3b8", marginBottom: "4px", letterSpacing: "0.05em", textTransform: "uppercase" }}>
            引用割合
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: "2px" }}>
            <span
              style={{
                fontSize: "64px",
                fontWeight: 900,
                color: SCORE_COLOR[status],
                letterSpacing: "-3px",
                lineHeight: 1,
                fontVariantNumeric: "tabular-nums",
              }}
            >
              {score.toFixed(1)}
            </span>
            <span style={{ fontSize: "24px", fontWeight: 700, color: SCORE_COLOR[status], letterSpacing: "-1px" }}>
              %
            </span>
          </div>
        </div>

        {/* ステータスバッジ + 処理時間 */}
        <div style={{ display: "flex", flexDirection: "column", gap: "8px", paddingBottom: "4px" }}>
          <span
            style={{
              display: "inline-block",
              padding: "6px 18px",
              borderRadius: "9999px",
              fontSize: "14px",
              fontWeight: 700,
              color: cfg.color,
              backgroundColor: cfg.bg,
              border: `1px solid ${cfg.border}`,
              letterSpacing: "0.02em",
            }}
          >
            {cfg.label}
          </span>
          {processingTime !== undefined && (
            <span style={{ fontSize: "11px", color: "#94a3b8" }}>
              処理時間: {processingTime}秒
            </span>
          )}
        </div>
      </div>

      {/* プログレスバー */}
      <div>
        <div
          style={{
            width: "100%",
            height: "8px",
            backgroundColor: "#e2e8f0",
            borderRadius: "9999px",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              width: `${barWidth}%`,
              height: "100%",
              background: BAR_GRADIENT[status],
              borderRadius: "9999px",
              transition: "width 0.6s cubic-bezier(0.4,0,0.2,1)",
            }}
          />
        </div>

        {/* 閾値マーカー */}
        <div style={{ position: "relative", height: "18px", marginTop: "4px", fontSize: "10px", color: "#94a3b8" }}>
          <div style={{ position: "absolute", left: "20%", transform: "translateX(-50%)", display: "flex", flexDirection: "column", alignItems: "center", gap: "2px" }}>
            <div style={{ width: "1px", height: "6px", backgroundColor: "#cbd5e1" }} />
            <span>20%</span>
          </div>
          <div style={{ position: "absolute", left: "80%", transform: "translateX(-50%)", display: "flex", flexDirection: "column", alignItems: "center", gap: "2px" }}>
            <div style={{ width: "1px", height: "6px", backgroundColor: "#cbd5e1" }} />
            <span>80%</span>
          </div>
        </div>
      </div>

      {/* 文献ごとの引用割合（特許図31・33準拠） */}
      {perSourceScores && Object.keys(perSourceScores).length > 0 && (
        <div
          style={{
            padding: "16px 18px",
            backgroundColor: "#f8fafc",
            border: "1px solid #e2e8f0",
            borderRadius: "12px",
          }}
        >
          <div style={{ fontSize: "11px", fontWeight: 700, color: "#64748b", marginBottom: "12px", letterSpacing: "0.06em", textTransform: "uppercase" }}>
            文献別引用割合
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {Object.entries(perSourceScores)
              .sort((a, b) => b[1] - a[1])
              .map(([url, pct]) => {
                const host = _hostname(url);
                const barColor =
                  pct >= 80 ? "#dc2626" : pct >= 20 ? "#d97706" : "#16a34a";
                const barBg =
                  pct >= 80 ? "linear-gradient(90deg,#fca5a5,#dc2626)"
                  : pct >= 20 ? "linear-gradient(90deg,#fde68a,#d97706)"
                  : "linear-gradient(90deg,#4ade80,#16a34a)";
                return (
                  <div key={url} style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <a
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      title={url}
                      style={{
                        color: "#4f46e5",
                        fontSize: "12px",
                        minWidth: "140px",
                        maxWidth: "260px",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        textDecoration: "none",
                        fontWeight: 500,
                      }}
                    >
                      {host}
                    </a>
                    <div
                      style={{
                        flex: 1,
                        height: "6px",
                        backgroundColor: "#e2e8f0",
                        borderRadius: "9999px",
                        overflow: "hidden",
                      }}
                    >
                      <div
                        style={{
                          width: `${Math.min(pct, 100)}%`,
                          height: "100%",
                          background: barBg,
                          borderRadius: "9999px",
                          transition: "width 0.5s ease",
                        }}
                      />
                    </div>
                    <span
                      style={{
                        fontWeight: 800,
                        color: barColor,
                        fontSize: "13px",
                        minWidth: "42px",
                        textAlign: "right",
                        fontVariantNumeric: "tabular-nums",
                      }}
                    >
                      {pct.toFixed(1)}%
                    </span>
                  </div>
                );
              })}
          </div>
        </div>
      )}
    </div>
  );
};

export default ScoreBar;
