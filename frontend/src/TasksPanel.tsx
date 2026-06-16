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
    <aside style={{ width: 300, flexShrink: 0, fontSize: 14 }}>
      <section style={{ marginBottom: 20 }}>
        <h3 style={{ margin: "0 0 8px" }}>Pending replies</h3>
        {suspense.length === 0 && <div style={{ color: "#888" }}>Nothing due.</div>}
        {suspense.map((t) => (
          <div key={t.id} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0" }}>
            <span>
              <input type="checkbox" onChange={() => done(t.id)} />{" "}
              {t.title}
            </span>
            <span style={{ color: t.overdue ? "#b00" : "#666", whiteSpace: "nowrap" }}>
              {t.reply_by ? ddMMMyyyy(t.reply_by) : ""}{t.overdue ? " ⚠" : ""}
            </span>
          </div>
        ))}
      </section>

      <section>
        <h3 style={{ margin: "0 0 8px" }}>Open tasks</h3>
        {open.length === 0 && <div style={{ color: "#888" }}>No open tasks.</div>}
        {open.map((t) => (
          <div key={t.id} style={{ padding: "4px 0" }}>
            <input type="checkbox" onChange={() => done(t.id)} /> {t.title}
            {t.due_at && <span style={{ color: "#666" }}> — {ddMMMyyyy(t.due_at)}</span>}
          </div>
        ))}

        <form onSubmit={add} style={{ marginTop: 10, display: "grid", gap: 6 }}>
          <input
            placeholder="New task…"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            style={{ padding: "6px 8px" }}
          />
          <label style={{ fontSize: 12, color: "#666" }}>
            Reply-by (optional)
            <input type="date" value={replyBy} onChange={(e) => setReplyBy(e.target.value)} style={{ width: "100%", padding: "4px 6px" }} />
          </label>
          <button type="submit" disabled={!title}>Add task</button>
        </form>
      </section>
    </aside>
  );
}
