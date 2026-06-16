import { useEffect, useState } from "react";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import timeGridPlugin from "@fullcalendar/timegrid";
import multiMonthPlugin from "@fullcalendar/multimonth";
import interactionPlugin from "@fullcalendar/interaction";
import {
  getStatus,
  listEvents,
  createEvent,
  type SystemStatus,
  type EventRecord,
} from "./api";

function StatusBadge() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    getStatus().then(setStatus).catch((e) => setErr(String(e)));
  }, []);

  if (err) return <span style={{ color: "#b00" }}>backend unreachable</span>;
  if (!status) return <span>checking…</span>;

  const dot = (s: string) =>
    s === "ready" ? "🟢" : s === "disabled" ? "⚪" : "🔴";

  return (
    <span style={{ fontSize: 13 }}>
      {dot(status.inference.extraction)} extract&nbsp;
      {dot(status.inference.transcription)} voice&nbsp;
      {dot(status.inference.embedding)} search&nbsp; | &nbsp;
      {status.disk.free_gb} GB free
    </span>
  );
}

interface FormState {
  title: string;
  date: string; // yyyy-mm-dd (native input)
  time: string; // HH:mm
  venue: string;
  attendees: string;
}

const EMPTY: FormState = { title: "", date: "", time: "09:00", venue: "", attendees: "" };

function NewEventForm({
  initial,
  onSaved,
  onClose,
}: {
  initial: FormState;
  onSaved: () => void;
  onClose: () => void;
}) {
  const [form, setForm] = useState<FormState>(initial);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const set = (k: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement>) =>
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
      });
      onSaved();
    } catch (e2) {
      setErr(String(e2));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.35)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
      onClick={onClose}
    >
      <form
        onClick={(e) => e.stopPropagation()}
        onSubmit={submit}
        style={{
          background: "#fff",
          padding: 20,
          borderRadius: 8,
          width: 360,
          display: "grid",
          gap: 10,
        }}
      >
        <h3 style={{ margin: 0 }}>New event</h3>
        <label>
          Title
          <input required value={form.title} onChange={set("title")} style={inp} />
        </label>
        <div style={{ display: "flex", gap: 8 }}>
          <label style={{ flex: 1 }}>
            Date
            <input required type="date" value={form.date} onChange={set("date")} style={inp} />
          </label>
          <label style={{ width: 110 }}>
            Time
            <input type="time" value={form.time} onChange={set("time")} style={inp} />
          </label>
        </div>
        <label>
          Venue
          <input value={form.venue} onChange={set("venue")} style={inp} />
        </label>
        <label>
          Attendees
          <input value={form.attendees} onChange={set("attendees")} style={inp} />
        </label>
        {err && <div style={{ color: "#b00", fontSize: 13 }}>{err}</div>}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <button type="button" onClick={onClose}>Cancel</button>
          <button type="submit" disabled={busy || !form.title || !form.date}>
            {busy ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </div>
  );
}

const inp: React.CSSProperties = {
  width: "100%",
  padding: "6px 8px",
  marginTop: 2,
  boxSizing: "border-box",
};

export default function App() {
  const [events, setEvents] = useState<EventRecord[]>([]);
  const [form, setForm] = useState<FormState | null>(null);

  const reload = () => listEvents().then(setEvents).catch(() => setEvents([]));
  useEffect(() => {
    reload();
  }, []);

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: 16 }}>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 12,
        }}
      >
        <h1 style={{ fontSize: 20, margin: 0 }}>AI Notes &amp; Scheduler</h1>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <StatusBadge />
          <button onClick={() => setForm({ ...EMPTY })}>+ New event</button>
        </div>
      </header>

      <FullCalendar
        plugins={[dayGridPlugin, timeGridPlugin, multiMonthPlugin, interactionPlugin]}
        initialView="dayGridMonth"
        headerToolbar={{
          left: "prev,next today",
          center: "title",
          right: "timeGridDay,timeGridWeek,dayGridMonth,multiMonthYear",
        }}
        // DD MMM YYYY everywhere (NFR-5) — no US MM/DD.
        titleFormat={{ year: "numeric", month: "short" }}
        dayHeaderFormat={{ weekday: "short" }}
        height="auto"
        events={events.map((e) => ({
          id: e.id,
          title: e.title,
          start: e.starts_at,
          end: e.ends_at ?? undefined,
        }))}
        dateClick={(arg) =>
          setForm({ ...EMPTY, date: arg.dateStr.slice(0, 10) })
        }
      />

      {form && (
        <NewEventForm
          initial={form}
          onClose={() => setForm(null)}
          onSaved={() => {
            setForm(null);
            reload();
          }}
        />
      )}
    </div>
  );
}
