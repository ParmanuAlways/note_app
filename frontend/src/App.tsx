import { useEffect, useState } from "react";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import timeGridPlugin from "@fullcalendar/timegrid";
import multiMonthPlugin from "@fullcalendar/multimonth";
import interactionPlugin from "@fullcalendar/interaction";
import type { EventClickArg, DatesSetArg } from "@fullcalendar/core";
import TasksPanel from "./TasksPanel";
import DocumentsPanel from "./DocumentsPanel";
import NotesPanel from "./NotesPanel";
import TrashModal from "./TrashModal";
import Modal from "./Modal";
import {
  getStatus,
  listEvents,
  createEvent,
  deleteEvent,
  type SystemStatus,
  type Occurrence,
} from "./api";

function StatusBadge() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    getStatus().then(setStatus).catch((e) => setErr(String(e)));
  }, []);
  if (err) return <span style={{ color: "#b00" }}>backend unreachable</span>;
  if (!status) return <span>checking…</span>;
  const dot = (s: string) => (s === "ready" ? "🟢" : s === "disabled" ? "⚪" : "🔴");
  return (
    <span style={{ fontSize: 13 }}>
      {dot(status.inference.extraction)} extract&nbsp;
      {dot(status.inference.transcription)} voice&nbsp;
      {dot(status.inference.embedding)} search&nbsp; | &nbsp;
      {status.disk.free_gb} GB free
    </span>
  );
}

type Repeat = "none" | "daily" | "weekly" | "monthly";

interface FormState {
  title: string;
  date: string;
  time: string;
  venue: string;
  attendees: string;
  repeat: Repeat;
}

const EMPTY: FormState = {
  title: "",
  date: "",
  time: "09:00",
  venue: "",
  attendees: "",
  repeat: "none",
};

const RRULE: Record<Repeat, string | null> = {
  none: null,
  daily: "FREQ=DAILY",
  weekly: "FREQ=WEEKLY",
  monthly: "FREQ=MONTHLY",
};

const inp: React.CSSProperties = { width: "100%", padding: "6px 8px", marginTop: 2, boxSizing: "border-box" };

function NewEventForm({ initial, onSaved, onClose }: { initial: FormState; onSaved: () => void; onClose: () => void }) {
  const [form, setForm] = useState<FormState>(initial);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const set = (k: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm({ ...form, [k]: e.target.value });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      await createEvent({
        title: form.title,
        starts_at: `${form.date}T${form.time}:00`,
        venue: form.venue || null,
        attendees: form.attendees || null,
        rrule: RRULE[form.repeat],
      });
      onSaved();
    } catch (e2) {
      setErr(String(e2));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal onClose={onClose}>
      <form onSubmit={submit} style={{ display: "grid", gap: 10 }}>
        <h3 style={{ margin: 0 }}>New event</h3>
        <label>Title<input required value={form.title} onChange={set("title")} style={inp} /></label>
        <div style={{ display: "flex", gap: 8 }}>
          <label style={{ flex: 1 }}>Date<input required type="date" value={form.date} onChange={set("date")} style={inp} /></label>
          <label style={{ width: 110 }}>Time<input type="time" value={form.time} onChange={set("time")} style={inp} /></label>
        </div>
        <label>Venue<input value={form.venue} onChange={set("venue")} style={inp} /></label>
        <label>Attendees<input value={form.attendees} onChange={set("attendees")} style={inp} /></label>
        <label>
          Repeat
          <select value={form.repeat} onChange={set("repeat")} style={inp}>
            <option value="none">Does not repeat</option>
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </label>
        {err && <div style={{ color: "#b00", fontSize: 13 }}>{err}</div>}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <button type="button" onClick={onClose}>Cancel</button>
          <button type="submit" disabled={busy || !form.title || !form.date}>{busy ? "Saving…" : "Save"}</button>
        </div>
      </form>
    </Modal>
  );
}

interface ClickedOcc {
  eventId: string;
  title: string;
  start: string;
  recurring: boolean;
}

function DeleteDialog({ occ, onDone, onClose }: { occ: ClickedOcc; onDone: () => void; onClose: () => void }) {
  const remove = async (scope: "series" | "occurrence") => {
    await deleteEvent(occ.eventId, scope, scope === "occurrence" ? occ.start : undefined);
    onDone();
  };
  return (
    <Modal onClose={onClose}>
      <div style={{ display: "grid", gap: 12, minWidth: 280 }}>
        <h3 style={{ margin: 0 }}>{occ.title}</h3>
        {occ.recurring ? (
          <>
            <p style={{ margin: 0, fontSize: 14 }}>This is a recurring event.</p>
            <button onClick={() => remove("occurrence")}>Delete this occurrence</button>
            <button onClick={() => remove("series")}>Delete entire series</button>
          </>
        ) : (
          <button onClick={() => remove("series")}>Delete event</button>
        )}
        <button onClick={onClose}>Cancel</button>
      </div>
    </Modal>
  );
}

// FullCalendar gives "2026-06-01" or "2026-06-01T..[+offset]"; storage is naive
// single-zone (v1), so strip any offset to a plain local timestamp.
const naive = (s: string) => (s.includes("T") ? s.slice(0, 19) : `${s}T00:00:00`);

export default function App() {
  const [occ, setOcc] = useState<Occurrence[]>([]);
  const [range, setRange] = useState<{ start: string; end: string } | null>(null);
  const [form, setForm] = useState<FormState | null>(null);
  const [toDelete, setToDelete] = useState<ClickedOcc | null>(null);
  const [showTrash, setShowTrash] = useState(false);
  const [sidebarKey, setSidebarKey] = useState(0); // bump to remount panels

  const reload = (r = range) => {
    if (!r) return;
    listEvents(r.start, r.end).then(setOcc).catch(() => setOcc([]));
  };
  useEffect(() => reload(), [range]); // eslint-disable-line react-hooks/exhaustive-deps

  const onDatesSet = (arg: DatesSetArg) =>
    setRange({ start: naive(arg.startStr), end: naive(arg.endStr) });

  const onEventClick = (arg: EventClickArg) => {
    const p = arg.event.extendedProps as { eventId: string; start: string; recurring: boolean };
    setToDelete({ eventId: p.eventId, title: arg.event.title, start: p.start, recurring: p.recurring });
  };

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: 16 }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h1 style={{ fontSize: 20, margin: 0 }}>AI Notes &amp; Scheduler</h1>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <StatusBadge />
          <button onClick={() => setShowTrash(true)}>🗑 Trash</button>
          <button onClick={() => setForm({ ...EMPTY })}>+ New event</button>
        </div>
      </header>

      <div style={{ display: "flex", gap: 20, alignItems: "flex-start" }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <FullCalendar
            plugins={[dayGridPlugin, timeGridPlugin, multiMonthPlugin, interactionPlugin]}
            initialView="dayGridMonth"
            headerToolbar={{ left: "prev,next today", center: "title", right: "timeGridDay,timeGridWeek,dayGridMonth,multiMonthYear" }}
            titleFormat={{ year: "numeric", month: "short" }}
            dayHeaderFormat={{ weekday: "short" }}
            height="auto"
            datesSet={onDatesSet}
            eventClick={onEventClick}
            dateClick={(arg) => setForm({ ...EMPTY, date: arg.dateStr.slice(0, 10) })}
            events={occ.map((o) => ({
              title: o.title + (o.is_override ? " *" : ""),
              start: o.occurrence_start,
              end: o.occurrence_end ?? undefined,
              extendedProps: { eventId: o.event_id, start: o.occurrence_start, recurring: o.is_recurring },
            }))}
          />
        </div>
        <div style={{ width: 300, flexShrink: 0 }} key={sidebarKey}>
          <DocumentsPanel onConfirmed={() => reload()} />
          <NotesPanel />
          <TasksPanel />
        </div>
      </div>

      {form && <NewEventForm initial={form} onClose={() => setForm(null)} onSaved={() => { setForm(null); reload(); }} />}
      {toDelete && <DeleteDialog occ={toDelete} onClose={() => setToDelete(null)} onDone={() => { setToDelete(null); reload(); }} />}
      {showTrash && <TrashModal onClose={() => setShowTrash(false)} onRestored={() => { reload(); setSidebarKey((k) => k + 1); }} />}
    </div>
  );
}
