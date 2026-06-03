import React, { useEffect, useState } from "react";
import { listEvents, createEvent, deleteEvent, completeEvent } from "../api/client";
import { useTheme } from "../theme";

export default function Calendar({ userId }) {
  const { theme } = useTheme();
  const [events, setEvents] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", start_time: "", end_time: "", priority: 3, is_flexible: false });

  const s = {
    wrap: { padding: 24, height: "100%", overflowY: "auto", background: theme.bg, color: theme.text },
    header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 },
    title: { fontSize: 18, fontWeight: 600, color: theme.text },
    btn: (color) => ({ background: color, border: "none", color: "#fff", padding: "7px 16px", borderRadius: 6, cursor: "pointer", fontSize: 13 }),
    card: { background: theme.surface, border: `1px solid ${theme.border}`, borderRadius: 10, padding: "14px 18px", marginBottom: 10, display: "flex", justifyContent: "space-between", alignItems: "center" },
    cardTitle: { fontWeight: 500, color: theme.text, marginBottom: 4 },
    meta: { fontSize: 12, color: theme.textMuted },
    badge: { borderRadius: 4, padding: "2px 8px", fontSize: 11, fontWeight: 500 },
    form: { background: theme.surface, border: `1px solid ${theme.border}`, borderRadius: 10, padding: 20, marginBottom: 20 },
    input: { width: "100%", background: theme.surfaceAlt, border: `1px solid ${theme.border}`, color: theme.text, padding: "7px 10px", borderRadius: 6, marginBottom: 10, fontSize: 13 },
    row: { display: "flex", gap: 10 },
    label: { fontSize: 12, color: theme.textMuted, marginBottom: 4 },
    empty: { color: theme.textDim, textAlign: "center", marginTop: 60 },
  };

  const load = async () => {
    try { const { data } = await listEvents(userId); setEvents(data); } catch (e) {}
  };

  useEffect(() => {
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    try {
      await createEvent(userId, { ...form, priority: Number(form.priority) });
      setShowForm(false);
      setForm({ title: "", description: "", start_time: "", end_time: "", priority: 3, is_flexible: false });
      load();
    } catch (e) {}
  };

  const remove = async (id) => { try { await deleteEvent(id); } catch (e) {} load(); };
  const complete = async (id) => { try { await completeEvent(id, userId); } catch (e) { console.error(e); } load(); };

  const priorityColor = (p) => p <= 2 ? theme.textMuted : p === 3 ? theme.accent : p === 4 ? theme.warning : theme.danger;

  return (
    <div style={s.wrap}>
      <div style={s.header}>
        <span style={s.title}>Calendar</span>
        <button style={s.btn(theme.accent)} onClick={() => setShowForm(!showForm)}>+ New Event</button>
      </div>

      {showForm && (
        <form style={s.form} onSubmit={submit}>
          <div style={s.label}>Title *</div>
          <input style={s.input} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required placeholder="Event title" />
          <div style={s.label}>Description</div>
          <input style={s.input} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Optional description" />
          <div style={s.row}>
            <div style={{ flex: 1 }}>
              <div style={s.label}>Start *</div>
              <input type="datetime-local" style={s.input} value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} required />
            </div>
            <div style={{ flex: 1 }}>
              <div style={s.label}>End *</div>
              <input type="datetime-local" style={s.input} value={form.end_time} onChange={(e) => setForm({ ...form, end_time: e.target.value })} required />
            </div>
          </div>
          <div style={s.row}>
            <div>
              <div style={s.label}>Priority (1–5)</div>
              <input type="number" min={1} max={5} style={{ ...s.input, width: 80 }} value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })} />
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 22 }}>
              <input type="checkbox" checked={form.is_flexible} onChange={(e) => setForm({ ...form, is_flexible: e.target.checked })} id="flex" />
              <label htmlFor="flex" style={{ color: theme.textMuted, fontSize: 13 }}>Flexible (AI may reschedule this)</label>
            </div>
          </div>
          <button type="submit" style={s.btn(theme.accent)}>Save</button>
        </form>
      )}

      {events.length === 0 && <div style={s.empty}>No events yet. Add one above.</div>}

      {events.map((ev) => (
        <div key={ev.id} style={s.card}>
          <div>
            <div style={s.cardTitle}>{ev.title}</div>
            <div style={s.meta}>
              {new Date(ev.start_time).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })} → {new Date(ev.end_time).toLocaleString(undefined, { timeStyle: "short" })}
            </div>
            <div style={{ marginTop: 6, display: "flex", gap: 6 }}>
              <span style={{ ...s.badge, background: `${priorityColor(ev.priority)}22`, color: priorityColor(ev.priority) }}>P{ev.priority}</span>
              {ev.is_flexible && (
                <span style={{ ...s.badge, ...theme.badge.flexible }}>Flexible</span>
              )}
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6, alignItems: "flex-end" }}>
            {ev.description?.includes("Axiom") && (
              <button
                onClick={() => complete(ev.id)}
                style={{ background: theme.success, border: "none", color: "#fff", padding: "4px 10px", borderRadius: 5, cursor: "pointer", fontSize: 12, fontWeight: 500 }}
              >
                ✓ Complete
              </button>
            )}
            <button
              onClick={() => remove(ev.id)}
              style={{ background: "transparent", border: `1px solid ${theme.danger}44`, color: theme.danger, padding: "4px 10px", borderRadius: 5, cursor: "pointer", fontSize: 12 }}
            >
              Delete
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
