import React, { useEffect, useState } from "react";
import { listProposals, declineProposal, analyzeAndPropose } from "../api/client";
import { useTheme } from "../theme";
import ProposalChat from "./ProposalChat";

function decayColor(score) {
  if (score >= 0.8) return "#ef4444";
  if (score >= 0.5) return "#f97316";
  if (score >= 0.25) return "#eab308";
  return "#22c55e";
}

export default function ScheduleProposals({ userId }) {
  const { theme } = useTheme();
  const [proposals, setProposals] = useState([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [activeProposal, setActiveProposal] = useState(null);

  const load = async () => {
    try {
      const { data } = await listProposals(userId);
      setProposals(data);
    } catch (e) {}
  };

  useEffect(() => {
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, []);

  const analyze = async () => {
    setAnalyzing(true);
    try { await analyzeAndPropose(userId); load(); } catch (e) { console.error(e); } finally { setAnalyzing(false); }
  };

  const decline = async (id, e) => {
    e.stopPropagation();
    try { await declineProposal(id); load(); } catch (e) {}
  };

  const pending = proposals.filter(p => p.status === "pending");
  const done = proposals.filter(p => p.status !== "pending");

  if (activeProposal) {
    return (
      <ProposalChat
        proposal={activeProposal}
        onBack={() => { setActiveProposal(null); load(); }}
        onApplied={() => { setActiveProposal(null); load(); }}
      />
    );
  }

  const s = {
    wrap: { padding: 24, height: "100%", overflowY: "auto", background: theme.bg, color: theme.text },
    header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 },
    title: { fontSize: 18, fontWeight: 600, color: theme.text },
    analyzeBtn: { background: analyzing ? theme.surfaceAlt : theme.accent, border: "none", color: analyzing ? theme.textMuted : "#fff", padding: "8px 18px", borderRadius: 6, cursor: analyzing ? "default" : "pointer", fontSize: 13 },
    grid: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16, marginBottom: 32 },
    tile: { background: theme.surface, border: `1px solid ${theme.border}`, borderRadius: 12, padding: 20, cursor: "pointer", transition: "border-color .15s", display: "flex", flexDirection: "column", gap: 10 },
    topicName: { fontWeight: 700, fontSize: 15, color: theme.text },
    decayRow: { display: "flex", alignItems: "center", gap: 8 },
    decayBar: (score) => ({ height: 4, borderRadius: 2, background: theme.surfaceAlt, position: "relative", flex: 1, overflow: "hidden" }),
    decayFill: (score) => ({ position: "absolute", left: 0, top: 0, bottom: 0, width: `${Math.round(score * 100)}%`, background: decayColor(score), borderRadius: 2 }),
    decayLabel: (score) => ({ fontSize: 11, color: decayColor(score), fontWeight: 600, minWidth: 36 }),
    reasoning: { fontSize: 12, color: theme.textMuted, lineHeight: 1.5, display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden" },
    actions: { display: "flex", gap: 8, marginTop: 4 },
    scheduleBtn: { flex: 1, background: theme.accent, border: "none", color: "#fff", padding: "7px 0", borderRadius: 6, cursor: "pointer", fontSize: 13, fontWeight: 500 },
    declineBtn: { background: "transparent", border: `1px solid ${theme.border}`, color: theme.textMuted, padding: "7px 12px", borderRadius: 6, cursor: "pointer", fontSize: 13 },
    sectionTitle: { fontSize: 13, fontWeight: 600, color: theme.textMuted, marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.05em" },
    doneCard: { background: theme.surface, border: `1px solid ${theme.border}`, borderRadius: 8, padding: "12px 16px", marginBottom: 8, display: "flex", justifyContent: "space-between", alignItems: "center" },
    statusBadge: (status) => {
      const c = { accepted: theme.badge.accepted, declined: theme.badge.declined }[status] || theme.badge.pending;
      return { fontSize: 11, padding: "2px 8px", borderRadius: 4, ...c };
    },
    empty: { color: theme.textDim, textAlign: "center", marginTop: 60, lineHeight: 2 },
  };

  return (
    <div style={s.wrap}>
      <div style={s.header}>
        <span style={s.title}>Schedule Proposals</span>
        <button style={s.analyzeBtn} onClick={analyze} disabled={analyzing}>
          {analyzing ? "Analyzing…" : "Run Analysis"}
        </button>
      </div>

      {pending.length === 0 ? (
        <div style={s.empty}>
          No pending proposals.<br />
          Click <em>Run Analysis</em> to generate review suggestions for decaying topics.
        </div>
      ) : (
        <>
          <div style={s.sectionTitle}>Pending — {pending.length}</div>
          <div style={s.grid}>
            {pending.map(p => (
              <div key={p.id} style={s.tile} onClick={() => setActiveProposal({ ...p, user_id: userId })}>
                <div style={s.topicName}>{p.topic_title || "Untitled topic"}</div>
                <div style={s.decayRow}>
                  <div style={s.decayBar(p.topic_decay_score ?? 0)}>
                    <div style={s.decayFill(p.topic_decay_score ?? 0)} />
                  </div>
                  <span style={s.decayLabel(p.topic_decay_score ?? 0)}>{Math.round((p.topic_decay_score ?? 0) * 100)}%</span>
                </div>
                {p.ai_reasoning && <div style={s.reasoning}>{p.ai_reasoning}</div>}
                <div style={s.actions}>
                  <button style={s.scheduleBtn} onClick={e => { e.stopPropagation(); setActiveProposal({ ...p, user_id: userId }); }}>
                    Schedule →
                  </button>
                  <button style={s.declineBtn} onClick={e => decline(p.id, e)}>Decline</button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {done.length > 0 && (
        <>
          <div style={s.sectionTitle}>History</div>
          {done.map(p => (
            <div key={p.id} style={s.doneCard}>
              <span style={{ color: theme.textMuted, fontSize: 13 }}>{p.topic_title || p.topic_id.slice(0, 8)}</span>
              <span style={s.statusBadge(p.status)}>{p.status}</span>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
