import React, { useEffect, useMemo, useRef, useState } from "react";
import { startOfWeek, addWeeks, addDays, format, isSameDay, isToday } from "date-fns";
import { calendarService } from "../services/calendarService";
import { useTheme } from "../theme";

const HOUR_H = 46;          // pixels per hour
const SNAP_MIN = 15;        // drag snaps to 15-minute increments
const HOURS = Array.from({ length: 24 }, (_, h) => h);

// ── date helpers ──────────────────────────────────────────────────────────────
const toInput = (d) => format(d, "yyyy-MM-dd'T'HH:mm");           // Date -> local datetime-local value
const toUtcIso = (localStr) => new Date(localStr).toISOString();  // local datetime-local value -> UTC ISO for the API
const minutesOfDay = (d) => d.getHours() * 60 + d.getMinutes();
const dayAtMinutes = (day, mins) => {
  const d = new Date(day.getFullYear(), day.getMonth(), day.getDate(), 0, 0, 0, 0);
  d.setMinutes(mins);
  return d;
};
const hourLabel = (h) => `${h % 12 || 12} ${h < 12 ? "AM" : "PM"}`;
const emptyForm = { title: "", description: "", start_time: "", end_time: "", priority: 3, is_flexible: false };

// Lay overlapping events into side-by-side columns within a single day.
function packColumns(items) {
  const sorted = [...items].sort((a, b) => a.s - b.s || b.e - a.e);
  let cluster = [];
  let clusterEnd = -Infinity;
  const flush = () => {
    const colEnds = [];
    cluster.forEach((it) => {
      let col = colEnds.findIndex((end) => it.s >= end);
      if (col === -1) { col = colEnds.length; colEnds.push(it.e); }
      else colEnds[col] = it.e;
      it.col = col;
    });
    cluster.forEach((it) => { it.cols = colEnds.length; });
    cluster = [];
  };
  sorted.forEach((it) => {
    if (cluster.length && it.s >= clusterEnd) flush();
    cluster.push(it);
    clusterEnd = Math.max(clusterEnd, it.e);
  });
  flush();
  return sorted;
}

export default function Calendar({ userId, service = calendarService }) {
  const { theme } = useTheme();
  const [events, setEvents] = useState([]);
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date(), { weekStartsOn: 0 }));
  const [banner, setBanner] = useState(null);   // transient warning for drag reschedule
  const [modal, setModal] = useState(null);      // { mode, id, ev, form, warning }
  const [drag, setDrag] = useState(null);        // { id, durationMin, grabOffset }
  const [nowTick, setNowTick] = useState(() => new Date());
  const gridRef = useRef(null);

  const days = useMemo(() => HOURS.length && Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)), [weekStart]);

  const load = async () => {
    try {
      const { data } = await service.listEvents(userId);
      setEvents(data);
      // The backend's auto-complete sweep compares in UTC, but events are shown in the
      // user's local time. Use the local clock (what the user sees) as the source of truth:
      // complete any event whose end has passed locally but isn't flagged done yet. This
      // keeps the green state in sync and triggers the linked-topic decay reset.
      const stale = data.filter((e) => !e.completed && new Date(e.end_time) < new Date());
      if (stale.length) {
        await Promise.all(stale.map((e) => service.completeEvent(e.id, userId)));
        const { data: fresh } = await service.listEvents(userId);
        setEvents(fresh);
      }
    } catch (e) {}
  };

  useEffect(() => {
    load();
    const id = setInterval(load, 15000);
    const tick = setInterval(() => setNowTick(new Date()), 60000);
    return () => { clearInterval(id); clearInterval(tick); };
  }, []);

  // Scroll to ~7am on first mount so the working day is visible.
  useEffect(() => { if (gridRef.current) gridRef.current.scrollTop = 7 * HOUR_H; }, []);

  const showBanner = (b) => { setBanner(b); window.clearTimeout(showBanner._t); showBanner._t = window.setTimeout(() => setBanner(null), 6000); };

  // ── event positioning ─────────────────────────────────────────────────────
  const eventsByDay = useMemo(() => {
    const map = days.map(() => []);
    events.forEach((ev) => {
      const start = new Date(ev.start_time);
      const end = new Date(ev.end_time);
      const di = days.findIndex((d) => isSameDay(d, start));
      if (di === -1) return;
      map[di].push({ ev, s: minutesOfDay(start), e: Math.max(minutesOfDay(start) + 15, minutesOfDay(start) + (end - start) / 60000) });
    });
    return map.map(packColumns);
  }, [events, days]);

  // ── reschedule via drag & drop ──────────────────────────────────────────────
  const onDrop = async (e, day) => {
    e.preventDefault();
    if (!drag) return;
    const rect = e.currentTarget.getBoundingClientRect();
    let topPx = e.clientY - rect.top - drag.grabOffset;
    let mins = Math.round((topPx / HOUR_H) * 60 / SNAP_MIN) * SNAP_MIN;
    mins = Math.max(0, Math.min(1440 - drag.durationMin, mins));
    const newStart = dayAtMinutes(day, mins);
    const newEnd = dayAtMinutes(day, mins + drag.durationMin);
    setDrag(null);
    const result = await service.updateEvent(drag.id, { start_time: newStart.toISOString(), end_time: newEnd.toISOString() });
    if (!result.ok) showBanner({ message: result.message, conflicts: result.conflicts });
    load();
  };

  // ── modal (create / edit) ─────────────────────────────────────────────────
  const openCreate = (prefillStart) => {
    const start = prefillStart || dayAtMinutes(days[0], 9 * 60);
    const end = new Date(start.getTime() + 60 * 60000);
    setModal({ mode: "create", form: { ...emptyForm, start_time: toInput(start), end_time: toInput(end) }, warning: null });
  };
  const openEdit = (ev) => {
    setModal({
      mode: "edit", id: ev.id, ev,
      form: {
        title: ev.title, description: ev.description || "",
        start_time: toInput(new Date(ev.start_time)), end_time: toInput(new Date(ev.end_time)),
        priority: ev.priority, is_flexible: ev.is_flexible,
      },
      warning: null,
    });
  };
  const setForm = (patch) => setModal((m) => ({ ...m, form: { ...m.form, ...patch }, warning: null }));

  const saveModal = async (e) => {
    e.preventDefault();
    const f = modal.form;
    const payload = { ...f, priority: Number(f.priority), start_time: toUtcIso(f.start_time), end_time: toUtcIso(f.end_time) };
    const result = modal.mode === "create"
      ? await service.createEvent(userId, payload)
      : await service.updateEvent(modal.id, payload);
    if (result.ok) { setModal(null); load(); }
    else setModal((m) => ({ ...m, warning: { message: result.message, conflicts: result.conflicts } }));
  };
  const removeEvent = async () => { try { await service.deleteEvent(modal.id); } catch (e) {} setModal(null); load(); };
  const completeEvent = async () => { try { await service.completeEvent(modal.id, userId); } catch (e) {} setModal(null); load(); };

  const priorityColor = (p) => (p <= 2 ? theme.textMuted : p === 3 ? theme.accent : p === 4 ? theme.warning : theme.danger);

  // ── styles ──────────────────────────────────────────────────────────────────
  const s = {
    wrap: { padding: 24, height: "100%", display: "flex", flexDirection: "column", background: theme.bg, color: theme.text, boxSizing: "border-box" },
    header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, gap: 12 },
    title: { fontSize: 18, fontWeight: 600 },
    nav: { display: "flex", alignItems: "center", gap: 8 },
    navBtn: { background: theme.surface, border: `1px solid ${theme.border}`, color: theme.text, width: 30, height: 30, borderRadius: 6, cursor: "pointer", fontSize: 15, lineHeight: "28px", padding: 0 },
    todayBtn: { background: theme.surface, border: `1px solid ${theme.border}`, color: theme.text, padding: "5px 12px", borderRadius: 6, cursor: "pointer", fontSize: 13 },
    rangeLabel: { fontSize: 14, fontWeight: 500, minWidth: 170, textAlign: "center" },
    newBtn: { background: theme.accent, border: "none", color: "#fff", padding: "7px 16px", borderRadius: 6, cursor: "pointer", fontSize: 13 },
    banner: { background: `${theme.warning}1a`, border: `1px solid ${theme.warning}`, color: theme.warning, borderRadius: 8, padding: "9px 14px", marginBottom: 12, fontSize: 13 },
    cal: { flex: 1, display: "flex", flexDirection: "column", border: `1px solid ${theme.border}`, borderRadius: 10, overflow: "hidden", minHeight: 0, background: theme.surface },
    headRow: { display: "flex", borderBottom: `1px solid ${theme.border}`, background: theme.surface },
    gutterHead: { width: 56, flexShrink: 0 },
    dayHead: (d) => ({ flex: 1, textAlign: "center", padding: "8px 4px", borderLeft: `1px solid ${theme.border}`, color: isToday(d) ? theme.accent : theme.textMuted }),
    dayName: { fontSize: 11, textTransform: "uppercase", letterSpacing: 0.5 },
    dayNum: (d) => ({ fontSize: 18, fontWeight: 600, marginTop: 2, color: isToday(d) ? "#fff" : theme.text, background: isToday(d) ? theme.accent : "transparent", borderRadius: 16, width: 28, height: 28, lineHeight: "28px", display: "inline-block" }),
    scroll: { flex: 1, overflowY: "auto", minHeight: 0 },
    body: { display: "flex", position: "relative" },
    gutter: { width: 56, flexShrink: 0 },
    hourCell: { height: HOUR_H, fontSize: 10, color: theme.textDim, textAlign: "right", paddingRight: 6, transform: "translateY(-6px)" },
    dayCol: { flex: 1, position: "relative", borderLeft: `1px solid ${theme.border}`, height: 24 * HOUR_H, backgroundImage: `repeating-linear-gradient(to bottom, ${theme.border}, ${theme.border} 1px, transparent 1px, transparent ${HOUR_H}px)` },
    nowLine: (top) => ({ position: "absolute", left: 0, right: 0, top, height: 2, background: theme.danger, zIndex: 5, pointerEvents: "none" }),
    modalOverlay: { position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 },
    modal: { background: theme.surface, border: `1px solid ${theme.border}`, borderRadius: 12, padding: 22, width: 420, maxWidth: "92vw", boxSizing: "border-box" },
    input: { width: "100%", minWidth: 0, background: theme.surfaceAlt, border: `1px solid ${theme.border}`, color: theme.text, padding: "7px 10px", borderRadius: 6, marginBottom: 10, fontSize: 13, boxSizing: "border-box", fontFamily: "inherit" },
    label: { fontSize: 12, color: theme.textMuted, marginBottom: 4 },
    row: { display: "flex", gap: 10 },
    col: { flex: 1, minWidth: 0 },
    btn: (color) => ({ background: color, border: "none", color: "#fff", padding: "7px 16px", borderRadius: 6, cursor: "pointer", fontSize: 13 }),
    ghostBtn: (color) => ({ background: "transparent", border: `1px solid ${color}44`, color, padding: "7px 14px", borderRadius: 6, cursor: "pointer", fontSize: 13 }),
    warn: { background: `${theme.warning}1a`, border: `1px solid ${theme.warning}`, color: theme.warning, borderRadius: 8, padding: "9px 12px", marginBottom: 12, fontSize: 12.5 },
    warnList: { margin: "6px 0 0", paddingLeft: 16, color: theme.text, fontSize: 12 },
  };

  const rangeLabel = `${format(days[0], "MMM d")} – ${format(days[6], "MMM d, yyyy")}`;

  return (
    <div style={s.wrap}>
      <div style={s.header}>
        <span style={s.title}>Calendar</span>
        <div style={s.nav}>
          <button style={s.todayBtn} onClick={() => setWeekStart(startOfWeek(new Date(), { weekStartsOn: 0 }))}>Today</button>
          <button style={s.navBtn} title="Previous week" onClick={() => setWeekStart((w) => addWeeks(w, -1))}>‹</button>
          <span style={s.rangeLabel}>{rangeLabel}</span>
          <button style={s.navBtn} title="Next week" onClick={() => setWeekStart((w) => addWeeks(w, 1))}>›</button>
        </div>
        <button style={s.newBtn} onClick={() => openCreate()}>+ New Event</button>
      </div>

      {banner && (
        <div style={s.banner} role="alert">
          <strong>⚠ Couldn’t reschedule.</strong> {banner.message}
          {banner.conflicts?.length > 0 && ` (conflicts with ${banner.conflicts.map((c) => c.title).join(", ")})`}
        </div>
      )}

      <div style={s.cal}>
        <div style={s.headRow}>
          <div style={s.gutterHead} />
          {days.map((d) => (
            <div key={d.toISOString()} style={s.dayHead(d)}>
              <div style={s.dayName}>{format(d, "EEE")}</div>
              <div style={s.dayNum(d)}>{format(d, "d")}</div>
            </div>
          ))}
        </div>

        <div style={s.scroll} ref={gridRef}>
          <div style={s.body}>
            <div style={s.gutter}>
              {HOURS.map((h) => (<div key={h} style={s.hourCell}>{h === 0 ? "" : hourLabel(h)}</div>))}
            </div>

            {days.map((day, di) => (
              <div
                key={day.toISOString()}
                style={s.dayCol}
                onDragOver={(e) => { if (drag) e.preventDefault(); }}
                onDrop={(e) => onDrop(e, day)}
                onClick={(e) => {
                  const rect = e.currentTarget.getBoundingClientRect();
                  let mins = Math.round(((e.clientY - rect.top) / HOUR_H) * 60 / SNAP_MIN) * SNAP_MIN;
                  mins = Math.max(0, Math.min(1410, mins));
                  openCreate(dayAtMinutes(day, mins));
                }}
              >
                {isToday(day) && <div style={s.nowLine((minutesOfDay(nowTick) / 60) * HOUR_H)} />}

                {eventsByDay[di].map(({ ev, s: startMin, e: endMin, col, cols }) => {
                  const done = ev.completed || new Date(ev.end_time) < nowTick;
                  const color = done ? theme.success : priorityColor(ev.priority);
                  const top = (startMin / 60) * HOUR_H;
                  const height = Math.max(18, ((endMin - startMin) / 60) * HOUR_H - 2);
                  const width = `calc(${100 / cols}% - 5px)`;
                  const left = `calc(${(col * 100) / cols}% + 2px)`;
                  const isReview = ev.description?.includes("Axiom");
                  return (
                    <div
                      key={ev.id}
                      draggable={!done}
                      onDragStart={(e) => {
                        if (done) { e.preventDefault(); return; }
                        setDrag({ id: ev.id, durationMin: endMin - startMin, grabOffset: e.nativeEvent.offsetY });
                        e.dataTransfer.effectAllowed = "move";
                      }}
                      onDragEnd={() => setDrag(null)}
                      onClick={(e) => { e.stopPropagation(); openEdit(ev); }}
                      title={done ? `${ev.title} — completed` : `${ev.title} — click to edit, drag to reschedule`}
                      style={{
                        position: "absolute", top, height, left, width,
                        background: `${color}26`, borderLeft: `3px solid ${color}`, borderRadius: 6,
                        padding: "3px 6px", overflow: "hidden", cursor: done ? "pointer" : "grab", zIndex: 2,
                        fontSize: 11.5, color: theme.text, boxSizing: "border-box",
                        opacity: done ? 0.85 : 1,
                      }}
                    >
                      <div style={{ fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", textDecoration: done ? "line-through" : "none" }}>
                        {done ? "✓ " : isReview ? "★ " : ""}{ev.title}
                      </div>
                      <div style={{ fontSize: 10, color: theme.textMuted }}>
                        {format(new Date(ev.start_time), "h:mm")}–{format(new Date(ev.end_time), "h:mm a")}
                      </div>
                      {ev.is_flexible && height > 38 && (
                        <span style={{ fontSize: 9, background: theme.badge.flexible.bg, color: theme.badge.flexible.color, borderRadius: 3, padding: "1px 5px" }}>Flexible</span>
                      )}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </div>

      {modal && (
        <div style={s.modalOverlay} onClick={() => setModal(null)}>
          <form style={s.modal} onClick={(e) => e.stopPropagation()} onSubmit={saveModal}>
            <div style={{ ...s.title, marginBottom: 14 }}>{modal.mode === "create" ? "New Event" : "Edit Event"}</div>

            {modal.warning && (
              <div style={s.warn} role="alert">
                <strong>⚠ Not saved.</strong> {modal.warning.message}
                {modal.warning.conflicts?.length > 0 && (
                  <ul style={s.warnList}>
                    {modal.warning.conflicts.map((c) => (
                      <li key={c.id}>{c.title} — {format(new Date(c.start_time), "MMM d, h:mm a")} → {format(new Date(c.end_time), "h:mm a")}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            <div style={s.label}>Title *</div>
            <input style={s.input} value={modal.form.title} onChange={(e) => setForm({ title: e.target.value })} required placeholder="Event title" />
            <div style={s.label}>Description</div>
            <input style={s.input} value={modal.form.description} onChange={(e) => setForm({ description: e.target.value })} placeholder="Optional description" />
            <div style={s.row}>
              <div style={s.col}>
                <div style={s.label}>Start *</div>
                <input type="datetime-local" lang="en-GB" style={s.input} value={modal.form.start_time} onChange={(e) => setForm({ start_time: e.target.value })} required />
              </div>
              <div style={s.col}>
                <div style={s.label}>End *</div>
                <input type="datetime-local" lang="en-GB" style={s.input} value={modal.form.end_time} onChange={(e) => setForm({ end_time: e.target.value })} required />
              </div>
            </div>
            <div style={s.row}>
              <div>
                <div style={s.label}>Priority (1–5)</div>
                <input type="number" min={1} max={5} style={{ ...s.input, width: 80 }} value={modal.form.priority} onChange={(e) => setForm({ priority: e.target.value })} />
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 22 }}>
                <input type="checkbox" checked={modal.form.is_flexible} onChange={(e) => setForm({ is_flexible: e.target.checked })} id="flex" />
                <label htmlFor="flex" style={{ color: theme.textMuted, fontSize: 13 }}>Flexible (AI may reschedule)</label>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 16 }}>
              <div style={{ display: "flex", gap: 8 }}>
                {modal.mode === "edit" && <button type="button" style={s.ghostBtn(theme.danger)} onClick={removeEvent}>Delete</button>}
                {modal.mode === "edit" && !modal.ev?.completed && (
                  <button type="button" style={s.btn(theme.success)} onClick={completeEvent}>✓ Complete</button>
                )}
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button type="button" style={s.ghostBtn(theme.textMuted)} onClick={() => setModal(null)}>Cancel</button>
                <button type="submit" style={s.btn(theme.accent)}>Save</button>
              </div>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
