import React, { useRef, useState } from "react";
import { uploadDocument } from "../api/client";
import { useTheme } from "../theme";

const PRESETS = [
  { label: "1 week",   days: 7 },
  { label: "2 weeks",  days: 14 },
  { label: "1 month",  days: 30 },
  { label: "3 months", days: 90 },
];
const DEFAULT_DAYS = 14;

function toDays(value, unit) {
  const n = parseFloat(value);
  if (isNaN(n) || n <= 0) return null;
  if (unit === "hours")  return n / 24;
  if (unit === "weeks")  return n * 7;
  if (unit === "months") return n * 30;
  return n;
}

export default function UploadPanel({ userId }) {
  const { theme } = useTheme();
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [pendingFile, setPendingFile] = useState(null);
  const [selectedDays, setSelectedDays] = useState(DEFAULT_DAYS);
  const [customVal, setCustomVal] = useState("");
  const [customUnit, setCustomUnit] = useState("weeks");
  const [useCustom, setUseCustom] = useState(false);
  const inputRef = useRef();

  const effectiveDays = useCustom ? (toDays(customVal, customUnit) ?? selectedDays) : selectedDays;

  const handleFile = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPendingFile(file);
    setSelectedDays(DEFAULT_DAYS);
    setCustomVal("");
    setCustomUnit("weeks");
    setUseCustom(false);
    setMessage("");
  };

  const handleUpload = async () => {
    if (!pendingFile) return;
    setUploading(true);
    try {
      const { data } = await uploadDocument(userId, pendingFile, effectiveDays);
      setMessage(`✓ "${data.title}"`);
      setPendingFile(null);
      if (inputRef.current) inputRef.current.value = "";
      setTimeout(() => setMessage(""), 4000);
    } catch {
      setMessage("Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleCancel = () => {
    setPendingFile(null);
    if (inputRef.current) inputRef.current.value = "";
    setMessage("");
  };

  const customDays = toDays(customVal, customUnit);
  const uploadDisabled = uploading || (useCustom && !customDays);

  return (
    <div style={{ position: "relative", display: "flex", alignItems: "center", gap: 10 }}>
      {message && <span style={{ fontSize: 12, color: theme.accent }}>{message}</span>}
      <input ref={inputRef} type="file" accept=".txt,.md,.pdf,.docx" style={{ display: "none" }} onChange={handleFile} />
      <button
        onClick={() => inputRef.current.click()}
        style={{ background: theme.accent, border: "none", color: "#fff", padding: "7px 16px", borderRadius: 6, cursor: "pointer", fontSize: 13, whiteSpace: "nowrap" }}
      >
        Upload Notes
      </button>

      {pendingFile && (
        <div style={{
          position: "absolute", top: "calc(100% + 8px)", right: 0, zIndex: 200,
          background: theme.surface, border: `1px solid ${theme.border}`,
          borderRadius: 10, padding: "14px 16px", width: 280,
          boxShadow: "0 8px 24px rgba(0,0,0,0.35)", display: "flex", flexDirection: "column", gap: 12,
        }}>
          <div style={{ fontSize: 12, color: theme.textMuted, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            <span style={{ color: theme.text, fontWeight: 500 }}>{pendingFile.name}</span>
          </div>

          <div>
            <div style={{ fontSize: 12, color: theme.textMuted, marginBottom: 8 }}>
              How quickly do you forget this topic?
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {PRESETS.map((p) => {
                const active = !useCustom && selectedDays === p.days;
                return (
                  <button
                    key={p.days}
                    onClick={() => { setSelectedDays(p.days); setUseCustom(false); }}
                    style={{
                      textAlign: "left", padding: "7px 12px", borderRadius: 6,
                      border: `1px solid ${active ? theme.accent : theme.border}`,
                      background: active ? theme.accent : theme.surfaceAlt,
                      color: active ? "#fff" : theme.text,
                      fontSize: 13, cursor: "pointer",
                      display: "flex", justifyContent: "space-between", alignItems: "center",
                    }}
                  >
                    <span>{p.label}</span>
                    {p.days === DEFAULT_DAYS && !active && (
                      <span style={{ fontSize: 11, color: theme.textMuted }}>default</span>
                    )}
                  </button>
                );
              })}

              <button
                onClick={() => setUseCustom(true)}
                style={{
                  textAlign: "left", padding: "7px 12px", borderRadius: 6,
                  border: `1px solid ${useCustom ? theme.accent : theme.border}`,
                  background: useCustom ? theme.accent : theme.surfaceAlt,
                  color: useCustom ? "#fff" : theme.text,
                  fontSize: 13, cursor: "pointer",
                }}
              >
                Custom…
              </button>
            </div>
          </div>

          {useCustom && (
            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <input
                type="number" min="0.1" step="0.5" autoFocus
                value={customVal} onChange={(e) => setCustomVal(e.target.value)}
                placeholder="e.g. 6"
                style={{ flex: 1, minWidth: 0, padding: "6px 8px", borderRadius: 6, border: `1px solid ${theme.border}`, background: theme.surfaceAlt, color: theme.text, fontSize: 13 }}
              />
              <select
                value={customUnit} onChange={(e) => setCustomUnit(e.target.value)}
                style={{ padding: "6px 8px", borderRadius: 6, border: `1px solid ${theme.border}`, background: theme.surfaceAlt, color: theme.text, fontSize: 13, cursor: "pointer" }}
              >
                <option value="hours">hours</option>
                <option value="days">days</option>
                <option value="weeks">weeks</option>
                <option value="months">months</option>
              </select>
            </div>
          )}

          <div style={{ fontSize: 11, color: theme.textMuted, borderTop: `1px solid ${theme.border}`, paddingTop: 8 }}>
            50% forgotten after <strong style={{ color: theme.text }}>{
              effectiveDays >= 30
                ? `${Math.round(effectiveDays / 30)} month${Math.round(effectiveDays / 30) !== 1 ? "s" : ""}`
                : effectiveDays >= 7
                  ? `${Math.round(effectiveDays / 7)} week${Math.round(effectiveDays / 7) !== 1 ? "s" : ""}`
                  : effectiveDays >= 1
                    ? `${Math.round(effectiveDays * 10) / 10} day${effectiveDays !== 1 ? "s" : ""}`
                    : `${Math.round(effectiveDays * 24)} hour${Math.round(effectiveDays * 24) !== 1 ? "s" : ""}`
            }</strong>
          </div>

          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={handleUpload}
              disabled={uploadDisabled}
              style={{
                flex: 1, background: uploadDisabled ? theme.surfaceAlt : theme.accent,
                border: "none", color: uploadDisabled ? theme.textMuted : "#fff",
                padding: "8px 0", borderRadius: 6, cursor: uploadDisabled ? "default" : "pointer",
                fontSize: 13, fontWeight: 500,
              }}
            >
              {uploading ? "Uploading…" : "Upload"}
            </button>
            <button
              onClick={handleCancel} disabled={uploading}
              style={{ padding: "8px 14px", borderRadius: 6, border: `1px solid ${theme.border}`, background: "transparent", color: theme.textMuted, fontSize: 13, cursor: "pointer" }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
