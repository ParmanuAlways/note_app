import { useEffect, useRef, useState } from "react";
import {
  uploadDocuments,
  listDocuments,
  documentFileUrl,
  type DocumentRecord,
  type UploadItem,
} from "./api";
import { ddMMMyyyy } from "./format";

// Intake panel: upload scanned letters (FR-1/2/3), see per-file status, open
// the stored original (FR-27). Extraction is Phase 2 — here we only capture.
export default function DocumentsPanel() {
  const [docs, setDocs] = useState<DocumentRecord[]>([]);
  const [results, setResults] = useState<UploadItem[]>([]);
  const [pending, setPending] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const reload = () => {
    listDocuments().then(setDocs).catch(() => setDocs([]));
  };
  useEffect(reload, []);

  async function send(files: File[], force: boolean) {
    setBusy(true);
    try {
      const items = await uploadDocuments(files, force);
      setResults(items);
      reload();
    } catch (e) {
      setResults([{ filename: "(batch)", status: "rejected", reason: String(e), document_id: null, duplicate_of: null }]);
    } finally {
      setBusy(false);
    }
  }

  function onPick(e: React.ChangeEvent<HTMLInputElement>) {
    setPending(Array.from(e.target.files ?? []));
    setResults([]);
  }

  const dupes = results.filter((r) => r.status === "duplicate");

  return (
    <section style={{ marginBottom: 20, fontSize: 14 }}>
      <h3 style={{ margin: "0 0 8px" }}>Documents</h3>

      <input ref={fileInput} type="file" multiple accept=".pdf,.jpg,.jpeg,.png,.tif,.tiff" onChange={onPick} style={{ fontSize: 12 }} />
      <button disabled={busy || pending.length === 0} onClick={() => send(pending, false)} style={{ marginTop: 6 }}>
        {busy ? "Uploading…" : `Upload ${pending.length || ""}`}
      </button>

      {results.length > 0 && (
        <div style={{ marginTop: 8, fontSize: 12 }}>
          {results.map((r, i) => (
            <div key={i} style={{ color: r.status === "uploaded" ? "#181" : r.status === "duplicate" ? "#a60" : "#b00" }}>
              {r.status === "uploaded" ? "✓" : r.status === "duplicate" ? "⚠" : "✗"} {r.filename}
              {r.reason ? ` — ${r.reason}` : ""}
              {r.status === "duplicate" ? " — already uploaded" : ""}
            </div>
          ))}
          {dupes.length > 0 && (
            // FR-3: a likely duplicate prompts — proceed anyway, or not.
            <button style={{ marginTop: 6 }} disabled={busy} onClick={() => send(pending, true)}>
              Upload anyway ({dupes.length} duplicate)
            </button>
          )}
        </div>
      )}

      <div style={{ marginTop: 10 }}>
        {docs.length === 0 && <div style={{ color: "#888" }}>No documents yet.</div>}
        {docs.map((d) => (
          <div key={d.id} style={{ padding: "3px 0" }}>
            📄 <a href={documentFileUrl(d.id)} target="_blank" rel="noreferrer">{d.filename}</a>
            <span style={{ color: "#666" }}> · {d.page_count}p · {ddMMMyyyy(d.created_at)}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
