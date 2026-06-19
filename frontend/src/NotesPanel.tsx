import { useEffect, useState } from "react";
import {
  listNotes,
  getNote,
  createNote,
  updateNote,
  listNoteVersions,
  getNoteVersion,
  type NoteMeta,
  type NoteVersion,
} from "./api";
import { ddMMMyyyy } from "./format";
import Modal from "./Modal";

// Notes: typed capture (FR-5), editable after creation with git version
// history viewable per note (FR-38/39, AC-17).
export default function NotesPanel() {
  const [notes, setNotes] = useState<NoteMeta[]>([]);
  const [editing, setEditing] = useState<NoteMeta | "new" | null>(null);

  const reload = () => {
    listNotes().then(setNotes).catch(() => setNotes([]));
  };
  useEffect(reload, []);

  return (
    <div className="card panel-notes">
      <div className="panel-head">
        <h3>📝 Notes</h3>
        <button className="sm" onClick={() => setEditing("new")}>+ Note</button>
      </div>
      {notes.length === 0 && <div className="empty">No notes yet.</div>}
      {notes.map((n) => (
        <div key={n.id} className="row">
          <a href="#" onClick={(e) => { e.preventDefault(); setEditing(n); }}>{n.title}</a>
          <span className="faint" style={{ fontSize: 12 }}>{ddMMMyyyy(n.updated_at)}</span>
        </div>
      ))}
      {editing && (
        <NoteEditor
          note={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); reload(); }}
        />
      )}
    </div>
  );
}

function NoteEditor({ note, onClose, onSaved }: { note: NoteMeta | null; onClose: () => void; onSaved: () => void }) {
  const [title, setTitle] = useState(note?.title ?? "");
  const [content, setContent] = useState("");
  const [versions, setVersions] = useState<NoteVersion[]>([]);
  const [viewing, setViewing] = useState<{ sha: string; content: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (note) {
      getNote(note.id).then((n) => setContent(n.content));
      listNoteVersions(note.id).then(setVersions).catch(() => setVersions([]));
    }
  }, [note]);

  async function save() {
    setBusy(true);
    try {
      if (note) await updateNote(note.id, { title, content });
      else await createNote({ title, content });
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal onClose={onClose} width={460}>
      <div style={{ display: "grid", gap: 10 }}>
        <input placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} style={{ padding: "6px 8px", fontSize: 15 }} />
        <textarea placeholder="Write your note (markdown)…" value={content} onChange={(e) => setContent(e.target.value)} rows={10} style={{ padding: 8, fontFamily: "monospace", fontSize: 13 }} />
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontSize: 12, color: "#666" }}>{note ? `${versions.length} version(s)` : "new note"}</span>
          <span>
            <button onClick={onClose} style={{ marginRight: 8 }}>Cancel</button>
            <button className="primary" onClick={save} disabled={busy || !title}>{busy ? "Saving…" : "Save"}</button>
          </span>
        </div>

        {note && versions.length > 0 && (
          <div style={{ borderTop: "1px solid #eee", paddingTop: 8, fontSize: 12 }}>
            <strong>History</strong>
            {versions.map((v) => (
              <div key={v.sha} style={{ display: "flex", justifyContent: "space-between", padding: "2px 0" }}>
                <span>{v.message}</span>
                <a href="#" onClick={(e) => { e.preventDefault(); getNoteVersion(note.id, v.sha).then(setViewing); }}>
                  {ddMMMyyyy(v.at)} · view
                </a>
              </div>
            ))}
          </div>
        )}

        {viewing && (
          <pre style={{ background: "#f6f6f6", padding: 8, fontSize: 12, whiteSpace: "pre-wrap" }}>
            <em>version {viewing.sha.slice(0, 8)}:</em>{"\n"}{viewing.content}
          </pre>
        )}
      </div>
    </Modal>
  );
}
