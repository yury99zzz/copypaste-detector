import React from "react";

interface TextInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  isLoading: boolean;
}

const TextInput: React.FC<TextInputProps> = ({
  value,
  onChange,
  onSubmit,
  isLoading,
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
