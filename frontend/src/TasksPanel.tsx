import { useEffect, useState } from "react";
import {
  listTasks,
  listSuspense,
  createTask,
  setTaskStatus,
  type Task,
  type SuspenseItem,
} from "./api";
import { ddMMMyyyy } from "./format";

// Compact side panel: open tasks + the suspense / pending-replies view (FR-23).
export default function TasksPanel() {
  const [open, setOpen] = useState<Task[]>([]);
  const [suspense, setSuspense] = useState<SuspenseItem[]>([]);
  const [title, setTitle] = useState("");
  const [replyBy, setReplyBy] = useState("");

  const reload = () => {
    listTasks("open").then(setOpen).catch(() => setOpen([]));
    listSuspense().then(setSuspense).catch(() => setSuspense([]));
  };
  useEffect(reload, []);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    if (!title) return;
    await createTask({ title, reply_by: replyBy ? `${replyBy}T17:00:00` : null });
    setTitle("");
    setReplyBy("");
    reload();
  }

  const done = async (id: string) => {
    await setTaskStatus(id, "done");
    reload();
  };

  return (
    <div className="card panel-tasks">
      <div style={{ marginBottom: 16 }}>
        <div className="panel-head"><h3>⏰ Pending replies</h3></div>
        {suspense.length === 0 && <div className="empty">Nothing due.</div>}
        {suspense.map((t) => (
          <div key={t.id} className="row">
            <label style={{ display: "flex", gap: 7, alignItems: "center", fontWeight: 400, color: "var(--text)" }}>
              <input type="checkbox" style={{ width: "auto" }} onChange={() => done(t.id)} /> {t.title}
            </label>
            <span style={{ color: t.overdue ? "var(--danger)" : "var(--muted)", whiteSpace: "nowrap", fontSize: 12, fontWeight: t.overdue ? 600 : 400 }}>
              {t.reply_by ? ddMMMyyyy(t.reply_by) : ""}{t.overdue ? " ⚠" : ""}
            </span>
          </div>
        ))}
      </div>

      <div>
        <div className="panel-head"><h3>✅ Open tasks</h3></div>
        {open.length === 0 && <div className="empty">No open tasks.</div>}
        {open.map((t) => (
          <div key={t.id} className="row">
            <label style={{ display: "flex", gap: 7, alignItems: "center", fontWeight: 400, color: "var(--text)" }}>
              <input type="checkbox" style={{ width: "auto" }} onChange={() => done(t.id)} /> {t.title}
            </label>
            {t.due_at && <span className="faint" style={{ fontSize: 12 }}>{ddMMMyyyy(t.due_at)}</span>}
          </div>
        ))}

        <form onSubmit={add} style={{ marginTop: 12, display: "grid", gap: 8 }}>
          <input placeholder="New task…" value={title} onChange={(e) => setTitle(e.target.value)} />
          <label>Reply-by (optional)
            <input type="date" value={replyBy} onChange={(e) => setReplyBy(e.target.value)} style={{ marginTop: 3 }} />
          </label>
          <button className="primary" type="submit" disabled={!title}>Add task</button>
        </form>
      </div>
    </div>
  );
}
