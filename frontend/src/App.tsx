import { useEffect, useState } from "react";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import timeGridPlugin from "@fullcalendar/timegrid";
import multiMonthPlugin from "@fullcalendar/multimonth";
import { getStatus, type SystemStatus } from "./api";

// Phase 0 shell: proves the calendar library (NFR-8) renders day/week/month/
// year views (FR-35) and that the status badge (FR-41) reads the backend.
// Real events, capture, and AI land in later phases.

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

export default function App() {
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
        <StatusBadge />
      </header>

      <FullCalendar
        plugins={[dayGridPlugin, timeGridPlugin, multiMonthPlugin]}
        initialView="dayGridMonth"
        headerToolbar={{
          left: "prev,next today",
          center: "title",
          right: "timeGridDay,timeGridWeek,dayGridMonth,multiMonthYear",
        }}
        // DD MMM YYYY everywhere (NFR-5) — no US MM/DD.
        titleFormat={{ year: "numeric", month: "short" }}
        height="auto"
        events={[]}
      />
    </div>
  );
}
