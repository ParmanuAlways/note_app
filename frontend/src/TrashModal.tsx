import { useEffect, useState } from "react";
import { listTrash, restoreItem, type TrashItem } from "./api";
import { ddMMMyyyy } from "./format";
import Modal from "./Modal";

const ICON: Record<TrashItem["type"], string> = { event: "📅", task: "✅", note: "📝", document: "📄" };

// Restorable trash (FR-19). No hard-delete button — the only permanent removal
// is the timed purge (server-side), so nothing here can be lost by a misclick.
export default function TrashModal({ onClose, onRestored }: { onClose: () => void; onRestored: () => void }) {
  const [items, setItems] = useState<TrashItem[]>([]);
  const reload = () => {
    listTrash().then(setItems).catch(() => setItems([]));
  };
  useEffect(reload, []);

  async function restore(it: TrashItem) {
    await restoreItem(it.type, it.id);
    reload();
    onRestored();
  }

  return (
    <Modal onClose={onClose} width={420}>
      <h3 style={{ margin: "0 0 12px" }}>Trash</h3>
      {items.length === 0 && <div style={{ color: "#888" }}>Trash is empty.</div>}
      {items.map((it) => (
        <div key={`${it.type}-${it.id}`} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "5px 0", borderBottom: "1px solid #f0f0f0" }}>
          <span>{ICON[it.type]} {it.title} <span style={{ color: "#888", fontSize: 12 }}>· deleted {ddMMMyyyy(it.deleted_at)}</span></span>
          <button onClick={() => restore(it)}>Restore</button>
        </div>
      ))}
      <p style={{ color: "#888", fontSize: 12, marginTop: 12 }}>Items in trash are purged automatically after 30 days.</p>
    </Modal>
  );
}
