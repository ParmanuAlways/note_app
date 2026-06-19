import { useEffect, useRef, useState } from "react";
import {
  uploadDocuments,
  listDocuments,
  documentFileUrl,
  extractDocument,
  type DocumentRecord,
  type UploadItem,
  type Extraction,
} from "./api";
import ConfirmScreen from "./ConfirmScreen";

// Intake panel: upload scanned letters (FR-1/2/3), see per-file status, open
// the stored original (FR-27). Extraction is Phase 2 — here we only capture.
export default function DocumentsPanel({ onConfirmed }: { onConfirmed?: () => void }) {
  const [docs, setDocs] = useState<DocumentRecord[]>([]);
  const [results, setResults] = useState<UploadItem[]>([]);
  const [pending, setPending] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [extracting, setExtracting] = useState<string | null>(null);
  const [extraction, setExtraction] = useState<Extraction | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  async function runExtract(id: string) {
    setExtracting(id);
    setMsg(null);
    try {
      setExtraction(await extractDocument(id));
    } catch (e) {
      setMsg(String(e));
    } finally {
      setExtracting(null);
    }
  }

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
    <div className="card panel-docs">
      <div className="panel-head"><h3>📄 Documents</h3></div>

      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <input ref={fileInput} type="file" multiple accept=".pdf,.jpg,.jpeg,.png,.tif,.tiff" onChange={onPick} style={{ fontSize: 12, padding: 5 }} />
        <button className="primary sm" disabled={busy || pending.length === 0} onClick={() => send(pending, false)} style={{ whiteSpace: "nowrap" }}>
          {busy ? "Uploading…" : `Upload ${pending.length || ""}`}
        </button>
      </div>

      {results.length > 0 && (
        <div style={{ marginTop: 10, fontSize: 12 }}>
          {results.map((r, i) => (
            <div key={i} style={{ color: r.status === "uploaded" ? "var(--success)" : r.status === "duplicate" ? "var(--warn)" : "var(--danger)", padding: "2px 0" }}>
              {r.status === "uploaded" ? "✓" : r.status === "duplicate" ? "⚠" : "✗"} {r.filename}
              {r.reason ? ` — ${r.reason}` : ""}
              {r.status === "duplicate" ? " — already uploaded" : ""}
            </div>
          ))}
          {dupes.length > 0 && (
            <button className="sm" style={{ marginTop: 6 }} disabled={busy} onClick={() => send(pending, true)}>
              Upload anyway ({dupes.length} duplicate)
            </button>
          )}
        </div>
      )}

      <div style={{ marginTop: 12 }}>
        {docs.length === 0 && <div className="empty">No documents yet.</div>}
        {docs.map((d) => (
          <div key={d.id} className="row">
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              📄 <a href={documentFileUrl(d.id)} target="_blank" rel="noreferrer">{d.filename}</a>
              <span className="faint"> · {d.page_count}p</span>
            </span>
            <button className="sm" onClick={() => runExtract(d.id)} disabled={extracting === d.id}>
              {extracting === d.id ? "Reading…" : "✨ Extract"}
            </button>
          </div>
        ))}
      </div>

      {msg && <div style={{ marginTop: 8, fontSize: 12, color: "var(--warn)" }}>{msg}</div>}

      {extraction && (
        <ConfirmScreen
          extraction={extraction}
          onClose={() => setExtraction(null)}
          onConfirmed={(m) => { setExtraction(null); setMsg(m); reload(); onConfirmed?.(); }}
        />
      )}
    </div>
  );
}
