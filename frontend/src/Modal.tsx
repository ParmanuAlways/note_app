// Shared overlay modal. Click the backdrop to dismiss.
export default function Modal({ children, onClose, width = 380 }: { children: React.ReactNode; onClose: () => void; width?: number }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" style={{ width }} onClick={(e) => e.stopPropagation()}>
        {children}
      </div>
    </div>
  );
}
