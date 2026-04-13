import React from "react";

type Status = "ok" | "warning" | "danger" | "critical";

const STATUS_CONFIG: Record<Status, { label: string; color: string; bg: string }> = {
  ok:       { label: "問題なし",     color: "#166534", bg: "#dcfce7" },
  warning:  { label: "要注意",       color: "#92400e", bg: "#fef3c7" },
  danger:   { label: "高リスク",     color: "#9a3412", bg: "#ffedd5" },
  critical: { label: "ほぼ確実",     color: "#7f1d1d", bg: "#fee2e2" },
};

const BAR_COLOR: Record<Status, string> = {
  ok:       "#22c55e",
  warning:  "#eab308",
  danger:   "#f97316",
  critical: "#ef4444",
};

interface ScoreBarProps {
  score: number;
  status: Status;
  processingTime?: number;
}

const ScoreBar: React.FC<ScoreBarProps> = ({ score, status, processingTime }) => {
  const cfg = STATUS_CONFIG[status];
  const barWidth = Math.min(score, 100);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: "16px", fontWeight: 700 }}>
          コピペスコア: {score.toFixed(1)}%
        </span>
        <span
          style={{
            padding: "4px 12px",
            borderRadius: "9999px",
            fontSize: "13px",
            fontWeight: 600,
            color: cfg.color,
            backgroundColor: cfg.bg,
          }}
        >
          {cfg.label}
        </span>
      </div>

      <div
        style={{
          width: "100%",
          height: "12px",
          backgroundColor: "#e5e7eb",
          borderRadius: "9999px",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${barWidth}%`,
            height: "100%",
            backgroundColor: BAR_COLOR[status],
            borderRadius: "9999px",
            transition: "width 0.4s ease",
          }}
        />
      </div>

      <div style={{ display: "flex", gap: "16px", fontSize: "11px", color: "#9ca3af" }}>
        <span style={{ color: "#22c55e" }}>0% 問題なし</span>
        <span style={{ color: "#eab308" }}>20% 要注意</span>
        <span style={{ color: "#f97316" }}>50% 高リスク</span>
        <span style={{ color: "#ef4444" }}>80% ほぼ確実</span>
        {processingTime !== undefined && (
          <span style={{ marginLeft: "auto" }}>処理時間: {processingTime}秒</span>
        )}
      </div>
    </div>
  );
};

export default ScoreBar;
