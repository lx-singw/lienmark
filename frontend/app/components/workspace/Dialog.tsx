'use client';
import { useEffect, useRef, type ReactNode } from 'react';
export function Dialog({ open, onClose, label, drawer = false, children }: {
  open: boolean; onClose: () => void; label: string; drawer?: boolean; children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const element = ref.current;
    if (!element || !open) return;
    element.showModal();
    const prior = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { element.close(); document.body.style.overflow = prior; };
  }, [open]);
  if (!open) return null;
  return <dialog ref={ref} className="ws-native-dialog" aria-label={label}
    onCancel={onClose} onClick={event => { if (event.target === event.currentTarget) onClose(); }}>
    <div className={drawer ? 'ws-drawer' : 'ws-dialog'}>{children}</div>
  </dialog>;
}
