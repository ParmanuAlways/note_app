import { useEffect, useState } from "react";
import {
  confirmExtraction,
  checkConflicts,
  type Extraction,
  type Occurrence,
} from "./api";
import Modal from "./Modal";

// The confirm/edit screen (FR-14): every extraction is reviewed here before
// anything is saved. Flagged/low-confidence fields are highlighted; a clash
// with an existing event is warned about (FR-15). Dismiss keeps the document.

const FIELDS: { key: string; label: string; type: "text" | "date" | "time" }[] = [
  { key: "subject", label: "Subject", type: "text" },
  { key: "meeting_date", label: "Meeting date", type: "date" },
  { key: "meeting_time", label: "Time", type: "time" },
  { key: "venue", label: "Venue", type: "text" },
  { key: "attendees", label: "Attendees", type: "text" },
  { key: "reference_number", label: "Reference no.", type: "text" },
  { key: "deadline_action", label: "Action", type: "text" },
  { key: "reply_by_date", label: "Reply by", type: "date" },
];

const WARN = "var(--warn)";
const DANGER = "var(--danger)";
const FLAG: Record<string, [string, string]> = {
  missing: ["not found", WARN],
  low_confidence: ["low confidence", WARN],
  unreadable: ["unreadable date — please enter", DANGER],
  implausible_past: ["date is in the past!", DANGER],
  overdue: ["overdue", WARN],
};

export default function ConfirmScreen({ extraction, onClose, onConfirmed }: { extraction: Extraction; onClose: () => void; onConfirmed: (msg: string) => void }) {
  const initial: Record<string, string> = {};
  FIELDS.forEach((f) => (initial[f.key] = extraction.fields[f.key]?.value ?? ""));
  const [vals, setVals] = useState<Record<string, string>>(initial);
  const [conflicts, setConflicts] = useState<Occurrence[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const startsAt = vals.meeting_date ? `${vals.meeting_date}T${vals.meeting_time || "09:00"}:00` : null;

  // Re-check conflicts whenever the proposed date/time changes (FR-15).
  useEffect(() => {
    if (startsAt) checkConflicts(startsAt).then(setConflicts).catch(() => setConflicts([]));
    else setConflicts([]);
  }, [startsAt]);

  const editedFields = () => {
    const diff: Record<string, string | null> = {};
    FIELDS.forEach((f) => {
      const orig = extraction.fields[f.key]?.value ?? "";
      if (vals[f.key] !== orig) diff[f.key] = vals[f.key] || null;
    });
    return diff;
  };

  async function save(create: "event" | "task" | "none") {
    setBusy(true);
    setErr(null);
    try {
      const payload: Parameters<typeof confirmExtraction>[1] = { create, edited_fields: editedFields() };
      if (create === "event") {
        if (!startsAt) throw new Error("a meeting date is required to add to the calendar");
        payload.event = { title: vals.subject || "(untitled)", starts_at: startsAt, venue: vals.venue || null, attendees: vals.attendees || null };
      } else if (create === "task") {
        payload.task = { title: vals.deadline_action || vals.subject || "(task)", reply_by: vals.reply_by_date ? `${vals.reply_by_date}T17:00:00` : null };
      }
      const r = await confirmExtraction(extraction.id, payload);
      onConfirmed(r.created_type ? `Saved as ${r.created_type}.` : "Dismissed — document kept.");
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal onClose={onClose} width={560}>
      <h3 style={{ margin: "0 0 4px" }}>Confirm extracted details</h3>
      <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>
        Read by {extraction.model_used} · v{extraction.version} · review and correct before saving.
      </div>

      {conflicts.length > 0 && (
        <div style={{ background: "var(--danger-soft)", border: "1px solid var(--danger)", color: "var(--danger)", padding: 9, borderRadius: 8, marginBottom: 12, fontSize: 13, fontWeight: 550 }}>
          ⚠ Clashes with {conflicts.length} existing event(s): {conflicts.map((c) => c.title).join(", ")}
        </div>
      )}

      <div style={{ display: "grid", gap: 10 }}>
        {FIELDS.map((f) => {
          const flags = extraction.fields[f.key]?.flags ?? [];
          const conf = extraction.fields[f.key]?.confidence ?? 0;
          const src = extraction.fields[f.key]?.source_text;
          const worst = flags.find((fl) => FLAG[fl]?.[1] === DANGER) ?? flags[0];
          const color = worst ? FLAG[worst]?.[1] : undefined;
          return (
            <div key={f.key}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                <label style={{ fontWeight: 600 }}>{f.label}</label>
                <span style={{ color: color ?? "#999" }}>
                  {flags.map((fl) => FLAG[fl]?.[0] ?? fl).join(", ") || `${Math.round(conf * 100)}% conf`}
                </span>
              </div>
              <input
                type={f.type}
                value={vals[f.key]}
                onChange={(e) => setVals({ ...vals, [f.key]: e.target.value })}
                style={color ? { borderColor: color, boxShadow: `0 0 0 2px ${color}22` } : undefined}
              />
              {src && <div className="faint" style={{ fontSize: 11 }}>read from: “{src}”</div>}
            </div>
          );
        })}
      </div>

      {err && <div style={{ color: "#b00", fontSize: 13, marginTop: 10 }}>{err}</div>}

      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 18 }}>
        <button className="ghost" onClick={() => save("none")} disabled={busy}>Dismiss (keep document)</button>
        <span style={{ display: "flex", gap: 8 }}>
          <button onClick={() => save("task")} disabled={busy}>Save as task</button>
          <button className="primary" onClick={() => save("event")} disabled={busy || !startsAt}>
            {busy ? "Saving…" : "📅 Save to calendar"}
          </button>
        </span>
      </div>
    </Modal>
  );
}
