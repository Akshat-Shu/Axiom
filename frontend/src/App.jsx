import React, { useState } from "react";
import { ThemeContext, themes } from "./theme";
import KnowledgeGraph from "./components/KnowledgeGraph";
import Calendar from "./components/Calendar";
import ScheduleProposals from "./components/ScheduleProposals";
import UploadPanel from "./components/UploadPanel";

const DEMO_USER_ID = "demo-user-001";

const NAV = [
  { id: "graph", label: "Knowledge Map" },
  { id: "calendar", label: "Calendar" },
  { id: "proposals", label: "Proposals" },
];

export default function App() {
  const [activeTab, setActiveTab] = useState("graph");
  const [isDark, setIsDark] = useState(true);
  const theme = isDark ? themes.dark : themes.light;

  const s = {
    app: { display: "flex", flexDirection: "column", height: "100vh", background: theme.bg, color: theme.text, transition: "background .2s, color .2s" },
    nav: { display: "flex", alignItems: "center", gap: 4, padding: "0 24px", height: 56, background: theme.surface, borderBottom: `1px solid ${theme.border}`, flexShrink: 0 },
    brand: { fontWeight: 700, fontSize: 18, color: theme.text, marginRight: 32, letterSpacing: "-0.5px" },
    tab: (active) => ({
      padding: "8px 16px", borderRadius: 6, cursor: "pointer", fontSize: 14,
      border: "none", background: active ? theme.surfaceAlt : "transparent",
      color: active ? theme.text : theme.textMuted, transition: "all .15s",
    }),
    toggleBtn: {
      marginLeft: 12, background: theme.surfaceAlt, border: `1px solid ${theme.border}`,
      color: theme.text, padding: "6px 12px", borderRadius: 6, cursor: "pointer",
      fontSize: 13, display: "flex", alignItems: "center", gap: 6,
    },
    content: { flex: 1, overflow: "hidden" },
  };

  return (
    <ThemeContext.Provider value={{ theme, isDark, toggle: () => setIsDark((d) => !d) }}>
      <div style={s.app}>
        <nav style={s.nav}>
          <span style={s.brand}>Axiom</span>
          {NAV.map((n) => (
            <button key={n.id} style={s.tab(activeTab === n.id)} onClick={() => setActiveTab(n.id)}>
              {n.label}
            </button>
          ))}
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
            <UploadPanel userId={DEMO_USER_ID} />
            <button style={s.toggleBtn} onClick={() => setIsDark((d) => !d)}>
              {isDark ? "☀ Light" : "☾ Dark"}
            </button>
          </div>
        </nav>
        <main style={s.content}>
          {activeTab === "graph"     && <KnowledgeGraph userId={DEMO_USER_ID} />}
          {activeTab === "calendar"  && <Calendar userId={DEMO_USER_ID} />}
          {activeTab === "proposals" && <ScheduleProposals userId={DEMO_USER_ID} />}
        </main>
      </div>
    </ThemeContext.Provider>
  );
}
