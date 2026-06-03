import React, { useRef, useState } from "react";
import { uploadDocument } from "../api/client";
import { useTheme } from "../theme";

export default function UploadPanel({ userId }) {
  const { theme } = useTheme();
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const inputRef = useRef();

  const handleFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setMessage("");
    try {
      const { data } = await uploadDocument(userId, file);
      setMessage(`✓ "${data.title}"`);
      setTimeout(() => setMessage(""), 4000);
    } catch {
      setMessage("Upload failed");
    } finally {
      setUploading(false);
      inputRef.current.value = "";
    }
  };

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      {message && <span style={{ fontSize: 12, color: theme.accent }}>{message}</span>}
      <input ref={inputRef} type="file" accept=".txt,.md,.pdf,.docx" style={{ display: "none" }} onChange={handleFile} />
      <button
        onClick={() => inputRef.current.click()}
        disabled={uploading}
        style={{ background: uploading ? theme.surfaceAlt : theme.accent, border: "none", color: uploading ? theme.textMuted : "#fff", padding: "7px 16px", borderRadius: 6, cursor: uploading ? "default" : "pointer", fontSize: 13 }}
      >
        {uploading ? "Uploading…" : "Upload Notes"}
      </button>
    </div>
  );
}
