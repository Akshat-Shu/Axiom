import React, { useEffect, useRef, useState } from "react";
import { chatProposal, applyProposalChanges, listEvents } from "../api/client";
import { useTheme } from "../theme";

function decayBar(score) {
  const pct = Math.round(score * 100);
  const color = pct >= 80 ? "#ef4444" : pct >= 50 ? "#f97316" : pct >= 25 ? "#eab308" : "#22c55e";
  return { pct, color };
}

function isPast(isoStr) {
  return isoStr && new Date(isoStr) <= new Date();
}

function fmt(isoStr) {
  if (!isoStr) return "";
  const d = new Date(isoStr);
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function ChangeCard({ change, events, theme }) {
  const s = {
    card: { borderRadius: 8, padding: "10px 14px", marginBottom: 8, fontSize: 13 },
    label: { fontWeight: 600, marginBottom: 4 },
    detail: { color: theme.textMuted, fontSize: 12 },
  };

  if (change.type === "create_event") {
    const past = isPast(change.start_time);
    return (
      <div style={{ ...s.card, background: past ? "#ef444422" : "#16a34a22", border: `1px solid ${past ? "#ef444455" : "#16a34a55"}` }}>
        <div style={{ ...s.label, color: past ? "#ef4444" : "#22c55e" }}>{past ? "⚠ Past time — cannot apply" : "+ New event"}</div>
        <div style={{ color: theme.text }}>{change.title}</div>
        <div style={s.detail}>{fmt(change.start_time)} → {fmt(change.end_time)}</div>
        <div style={s.detail}>Priority: {change.priority ?? 1}</div>
      </div>
    );
  }

  if (change.type === "move_event") {
    const existing = events.find(e => e.id === change.event_id);
    const past = isPast(change.new_start_time);
    return (
      <div style={{ ...s.card, background: past ? "#ef444422" : "#f9731622", border: `1px solid ${past ? "#ef444455" : "#f9731655"}` }}>
        <div style={{ ...s.label, color: past ? "#ef4444" : "#f97316" }}>{past ? "⚠ Past time — cannot apply" : "↕ Move event"}</div>
        <div style={{ color: theme.text }}>{change.event_title || existing?.title}</div>
        {existing && <div style={{ ...s.detail, textDecoration: "line-through" }}>{fmt(existing.start_time)} → {fmt(existing.end_time)}</div>}
        <div style={s.detail}>{fmt(change.new_start_time)} → {fmt(change.new_end_time)}</div>
      </div>
    );
  }

  if (change.type === "update_priority") {
    const existing = events.find(e => e.id === change.event_id);
    return (
      <div style={{ ...s.card, background: "#6366f122", border: "1px solid #6366f155" }}>
        <div style={{ ...s.label, color: "#818cf8" }}>✎ Priority change</div>
        <div style={{ color: theme.text }}>{change.event_title || existing?.title}</div>
        <div style={s.detail}>P{existing?.priority ?? "?"} → P{change.new_priority}</div>
      </div>
    );
  }

  return null;
}

export default function ProposalChat({ proposal, onBack, onApplied }) {
  const { theme } = useTheme();
  const [messages, setMessages] = useState([]);
  const [proposedChanges, setProposedChanges] = useState([]);
  const [calendarEvents, setCalendarEvents] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    listEvents(proposal.user_id).then(r => setCalendarEvents(r.data)).catch(() => {});
    sendMessage("", []);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (text, history) => {
    const newHistory = text ? [...history, { role: "user", content: text }] : history;
    if (text) setMessages(newHistory);
    setLoading(true);
    try {
      const { data } = await chatProposal(proposal.id, history, text);
      const aiMsg = { role: "assistant", content: data.message };
      setMessages(prev => [...prev, aiMsg]);
      setProposedChanges(data.proposed_changes || []);
    } catch (e) {
      setMessages(prev => [...prev, { role: "assistant", content: "Sorry, something went wrong. Please try again." }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSend = () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    sendMessage(text, messages);
  };

  const handleApply = async () => {
    if (!proposedChanges.length) return;
    setApplying(true);
    try {
      await applyProposalChanges(proposal.id, proposedChanges);
      onApplied();
    } catch (e) {
      console.error("Apply failed", e);
    } finally {
      setApplying(false);
    }
  };

  const decay = decayBar(proposal.topic_decay_score ?? 0);

  const s = {
    wrap: { display: "flex", height: "100%", background: theme.bg, overflow: "hidden" },
    left: { width: "45%", borderRight: `1px solid ${theme.border}`, display: "flex", flexDirection: "column" },
    right: { flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" },
    header: { padding: "14px 20px", borderBottom: `1px solid ${theme.border}`, background: theme.surface, flexShrink: 0 },
    backBtn: { background: "none", border: "none", color: theme.accent, cursor: "pointer", fontSize: 13, padding: 0, marginBottom: 8 },
    topicName: { fontWeight: 700, fontSize: 16, color: theme.text },
    decayBadge: { display: "inline-block", marginLeft: 10, fontSize: 11, padding: "2px 7px", borderRadius: 4, background: `${decay.color}22`, color: decay.color },
    messages: { flex: 1, overflowY: "auto", padding: "16px 20px" },
    bubble: (role) => ({
      maxWidth: "80%", padding: "10px 14px", borderRadius: 12, marginBottom: 10, fontSize: 14, lineHeight: 1.5,
      background: role === "user" ? theme.accent : theme.surface,
      color: role === "user" ? "#fff" : theme.text,
      border: role === "assistant" ? `1px solid ${theme.border}` : "none",
      alignSelf: role === "user" ? "flex-end" : "flex-start",
    }),
    bubbleWrap: (role) => ({ display: "flex", justifyContent: role === "user" ? "flex-end" : "flex-start" }),
    inputArea: { padding: "12px 16px", borderTop: `1px solid ${theme.border}`, display: "flex", gap: 8, background: theme.surface, flexShrink: 0 },
    input: { flex: 1, background: theme.surfaceAlt, border: `1px solid ${theme.border}`, color: theme.text, borderRadius: 8, padding: "9px 13px", fontSize: 14, outline: "none" },
    sendBtn: { background: theme.accent, border: "none", color: "#fff", borderRadius: 8, padding: "9px 18px", cursor: "pointer", fontSize: 14, opacity: loading ? 0.6 : 1 },
    rightHeader: { padding: "14px 20px", borderBottom: `1px solid ${theme.border}`, background: theme.surface, flexShrink: 0, fontWeight: 600, color: theme.text },
    changesArea: { flex: 1, overflowY: "auto", padding: "16px 20px" },
    applyBtn: { margin: "12px 20px", background: theme.success, border: "none", color: "#fff", borderRadius: 8, padding: "10px 0", cursor: applying ? "not-allowed" : "pointer", fontSize: 14, fontWeight: 600, opacity: applying ? 0.7 : 1, flexShrink: 0 },
    emptyChanges: { color: theme.textDim, fontSize: 13, textAlign: "center", marginTop: 40, lineHeight: 2 },
  };

  return (
    <div style={s.wrap}>
      {/* LEFT: Chat */}
      <div style={s.left}>
        <div style={s.header}>
          <button style={s.backBtn} onClick={onBack}>← Back to proposals</button>
          <div>
            <span style={s.topicName}>{proposal.topic_title}</span>
            <span style={s.decayBadge}>{decay.pct}% decay</span>
          </div>
        </div>
        <div style={s.messages}>
          {messages.map((m, i) => (
            <div key={i} style={s.bubbleWrap(m.role)}>
              <div style={s.bubble(m.role)}>{m.content}</div>
            </div>
          ))}
          {loading && (
            <div style={s.bubbleWrap("assistant")}>
              <div style={{ ...s.bubble("assistant"), color: theme.textMuted }}>Thinking…</div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
        <div style={s.inputArea}>
          <input
            style={s.input}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleSend()}
            placeholder="Tell me what you want to change…"
          />
          <button style={s.sendBtn} onClick={handleSend} disabled={loading}>Send</button>
        </div>
      </div>

      {/* RIGHT: Proposed Changes */}
      <div style={s.right}>
        <div style={s.rightHeader}>
          Proposed Changes
          {proposedChanges.length > 0 && <span style={{ fontWeight: 400, fontSize: 12, color: theme.textMuted, marginLeft: 8 }}>{proposedChanges.length} action{proposedChanges.length > 1 ? "s" : ""}</span>}
        </div>
        <div style={s.changesArea}>
          {proposedChanges.length === 0 ? (
            <div style={s.emptyChanges}>
              {loading ? "Generating a suggested schedule…" : "No changes proposed yet.\nDescribe when you'd like to review this topic."}
            </div>
          ) : (
            proposedChanges.map((c, i) => (
              <ChangeCard key={i} change={c} events={calendarEvents} theme={theme} />
            ))
          )}
        </div>
        {proposedChanges.length > 0 && (
          <button style={s.applyBtn} onClick={handleApply} disabled={applying}>
            {applying ? "Applying…" : "Apply Changes"}
          </button>
        )}
      </div>
    </div>
  );
}
