// Shared overlay modal. Click the backdrop to dismiss.
export default function Modal({ children, onClose, width = 360 }: { children: React.ReactNode; onClose: () => void; width?: number }) {
  return (
    <div
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 10 }}
      onClick={onClose}
    >
      <div onClick={(e) => e.stopPropagation()} style={{ background: "#fff", padding: 20, borderRadius: 8, width, maxHeight: "85vh", overflow: "auto" }}>
        {children}
      </div>
    </div>
  );
}
