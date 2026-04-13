import React from "react";

interface TextInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  isLoading: boolean;
  threshold: number;
  onThresholdChange: (v: number) => void;
  maxQueries: number;
  onMaxQueriesChange: (v: number) => void;
}

const TextInput: React.FC<TextInputProps> = ({
  value,
  onChange,
  onSubmit,
  isLoading,
  threshold,
  onThresholdChange,
  maxQueries,
  onMaxQueriesChange,
}) => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      <label style={{ fontWeight: 600, fontSize: "14px", color: "#374151" }}>
        レポート本文を貼り付けてください
      </label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="ここにレポートのテキストを貼り付けてください..."
        rows={12}
        style={{
          width: "100%",
          padding: "12px",
          border: "1px solid #d1d5db",
          borderRadius: "8px",
          fontSize: "14px",
          fontFamily: "inherit",
          resize: "vertical",
          boxSizing: "border-box",
          outline: "none",
          lineHeight: "1.6",
        }}
        onFocus={(e) => (e.target.style.borderColor = "#6366f1")}
        onBlur={(e) => (e.target.style.borderColor = "#d1d5db")}
      />

      <div style={{ display: "flex", gap: "24px", flexWrap: "wrap" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label style={{ fontSize: "12px", color: "#6b7280" }}>
            類似度閾値: {Math.round(threshold * 100)}%
          </label>
          <input
            type="range"
            min={0.3}
            max={0.9}
            step={0.05}
            value={threshold}
            onChange={(e) => onThresholdChange(Number(e.target.value))}
            style={{ width: "160px" }}
          />
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label style={{ fontSize: "12px", color: "#6b7280" }}>
            検索キー数: {maxQueries}
          </label>
          <input
            type="range"
            min={1}
            max={10}
            step={1}
            value={maxQueries}
            onChange={(e) => onMaxQueriesChange(Number(e.target.value))}
            style={{ width: "160px" }}
          />
        </div>
      </div>

      <button
        onClick={onSubmit}
        disabled={isLoading || !value.trim()}
        style={{
          alignSelf: "flex-start",
          padding: "10px 24px",
          backgroundColor: isLoading || !value.trim() ? "#9ca3af" : "#6366f1",
          color: "#fff",
          border: "none",
          borderRadius: "8px",
          fontSize: "14px",
          fontWeight: 600,
          cursor: isLoading || !value.trim() ? "not-allowed" : "pointer",
          transition: "background-color 0.2s",
        }}
      >
        {isLoading ? "検査中..." : "コピペ検出を実行"}
      </button>
    </div>
  );
};

export default TextInput;
