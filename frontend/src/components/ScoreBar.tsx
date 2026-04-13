import React from "react";

type Status = "ok" | "warning" | "danger" | "critical";

// 特許図37の色分けに対応したステータス設定
// 0〜20%: 通常, 20〜80%: 要注意（黄）, 80%以上: ほぼ確実（赤）
const STATUS_CONFIG: Record<Status, { label: string; color: string; bg: string }> = {
  ok:       { label: "引用なし",   color: "#166534", bg: "#dcfce7" },
  warning:  { label: "要注意",     color: "#92400e", bg: "#fef3c7" },
  danger:   { label: "高リスク",   color: "#9a3412", bg: "#ffedd5" },
  critical: { label: "ほぼ確実",   color: "#7f1d1d", bg: "#fee2e2" },
};

const SCORE_COLOR: Record<Status, string> = {
  ok:       "#16a34a",
  warning:  "#ca8a04",
  danger:   "#ea580c",
  critical: "#dc2626",
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
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      {/* 引用割合を大きく表示 */}
      <div style={{ display: "flex", alignItems: "flex-end", gap: "16px" }}>
        <div style={{ lineHeight: 1 }}>
          <div style={{ fontSize: "11px", color: "#6b7280", marginBottom: "4px" }}>
            引用割合
          </div>
          <span
            style={{
              fontSize: "56px",
              fontWeight: 800,
              color: SCORE_COLOR[status],
              letterSpacing: "-2px",
              lineHeight: 1,
            }}
          >
            {score.toFixed(1)}
          </span>
          <span style={{ fontSize: "22px", fontWeight: 700, color: SCORE_COLOR[status] }}>
            %
          </span>
        </div>

        <div style={{ paddingBottom: "6px", display: "flex", flexDirection: "column", gap: "6px" }}>
          <span
            style={{
              display: "inline-block",
              padding: "4px 14px",
              borderRadius: "9999px",
              fontSize: "14px",
              fontWeight: 700,
              color: cfg.color,
              backgroundColor: cfg.bg,
            }}
          >
            {cfg.label}
          </span>
          {processingTime !== undefined && (
            <span style={{ fontSize: "11px", color: "#9ca3af" }}>
              処理時間: {processingTime}秒
            </span>
          )}
        </div>
      </div>

      {/* プログレスバー */}
      <div
        style={{
          width: "100%",
          height: "10px",
          backgroundColor: "#e5e7eb",
          borderRadius: "9999px",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${barWidth}%`,
            height: "100%",
            backgroundColor: SCORE_COLOR[status],
            borderRadius: "9999px",
            transition: "width 0.5s ease",
          }}
        />
      </div>

      {/* 閾値マーカー */}
      <div style={{ position: "relative", height: "16px", fontSize: "10px", color: "#9ca3af" }}>
        <span style={{ position: "absolute", left: "20%", transform: "translateX(-50%)" }}>
          20%
        </span>
        <span style={{ position: "absolute", left: "80%", transform: "translateX(-50%)" }}>
          80%
        </span>
        {/* 区切り線 */}
        <div style={{ position: "absolute", left: "20%", top: "-18px", width: "1px", height: "8px", backgroundColor: "#d1d5db" }} />
        <div style={{ position: "absolute", left: "80%", top: "-18px", width: "1px", height: "8px", backgroundColor: "#d1d5db" }} />
      </div>

      {/* 文献ごとの引用割合（特許図31・33準拠） */}
      {perSourceScores && Object.keys(perSourceScores).length > 0 && (
        <div style={{ marginTop: "4px" }}>
          <div style={{ fontSize: "11px", color: "#6b7280", marginBottom: "6px" }}>
            文献別引用割合
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            {Object.entries(perSourceScores)
              .sort((a, b) => b[1] - a[1])
              .map(([url, pct]) => {
                const host = _hostname(url);
                const barColor = pct >= 80 ? "#dc2626" : pct >= 20 ? "#ca8a04" : "#16a34a";
                return (
                  <div key={url} style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "12px" }}>
                    <a
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        color: "#2563eb",
                        minWidth: "160px",
                        maxWidth: "280px",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                      title={url}
                    >
                      {host}
                    </a>
                    <div
                      style={{
                        flex: 1,
                        height: "6px",
                        backgroundColor: "#e5e7eb",
                        borderRadius: "9999px",
                        overflow: "hidden",
                      }}
                    >
                      <div
                        style={{
                          width: `${Math.min(pct, 100)}%`,
                          height: "100%",
                          backgroundColor: barColor,
                          borderRadius: "9999px",
                        }}
                      />
                    </div>
                    <span style={{ fontWeight: 700, color: barColor, minWidth: "40px", textAlign: "right" }}>
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
