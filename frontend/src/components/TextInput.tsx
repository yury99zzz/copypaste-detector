import React, { useState } from "react";

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
  const [focused, setFocused] = useState(false);
  const [hovered, setHovered] = useState(false);
  const disabled = isLoading || !value.trim();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="ここにレポートのテキストを貼り付けてください..."
        rows={12}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        style={{
          width: "100%",
          padding: "14px 16px",
          border: focused
            ? "1.5px solid #6366f1"
            : "1.5px solid #e2e8f0",
          borderRadius: "10px",
          fontSize: "14px",
          fontFamily: "inherit",
          resize: "vertical",
          boxSizing: "border-box",
          outline: "none",
          lineHeight: "1.7",
          color: "#1e293b",
          backgroundColor: focused ? "#fafafa" : "#f8fafc",
          transition: "border-color 0.2s, background-color 0.2s",
          boxShadow: focused ? "0 0 0 3px rgba(99,102,241,0.12)" : "none",
        }}
      />

      {/* フッター行：文字数 + ボタン */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: "12px", color: "#94a3b8" }}>
          {value.length.toLocaleString()} 文字
        </span>

        <button
          onClick={onSubmit}
          disabled={disabled}
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
          style={{
            padding: "11px 28px",
            background: disabled
              ? "#e2e8f0"
              : hovered
              ? "linear-gradient(135deg, #4f46e5, #7c3aed)"
              : "linear-gradient(135deg, #6366f1, #818cf8)",
            color: disabled ? "#94a3b8" : "#fff",
            border: "none",
            borderRadius: "10px",
            fontSize: "14px",
            fontWeight: 700,
            cursor: disabled ? "not-allowed" : "pointer",
            transition: "background 0.2s, transform 0.1s, box-shadow 0.2s",
            boxShadow: disabled
              ? "none"
              : hovered
              ? "0 4px 16px rgba(99,102,241,0.45)"
              : "0 2px 8px rgba(99,102,241,0.3)",
            transform: !disabled && hovered ? "translateY(-1px)" : "none",
            letterSpacing: "0.02em",
          }}
        >
          {isLoading ? "検査中…" : "コピペ検出を実行"}
        </button>
      </div>
    </div>
  );
};

export default TextInput;
