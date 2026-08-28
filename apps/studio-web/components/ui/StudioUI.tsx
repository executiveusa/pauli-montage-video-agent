"use client";

import type { ReactNode } from "react";
import { useRef } from "react";

type NoticeState = "loading" | "ready" | "error";

export function StudioNotice({ detail, state, title }: { detail: string; state: NoticeState; title: string }) {
  return (
    <div aria-live="polite" className={`service-banner ${state}`} role="status">
      <span className="status-pill">
        <span aria-hidden="true" className={`status-dot ${state}`} />
        {title}
      </span>
      <span className="muted">{detail}</span>
    </div>
  );
}

export function StudioLoadingState({ label }: { label: string }) {
  return <div aria-busy="true" aria-live="polite" className="empty studio-state"><span aria-hidden="true" className="spinner" /><strong>{label}</strong></div>;
}

export function StudioEmptyState({ action, detail, title }: { action?: ReactNode; detail: string; title: string }) {
  return <div className="empty empty-product studio-state"><strong>{title}</strong><p>{detail}</p>{action}</div>;
}

export function StudioErrorState({ detail, title = "Something went wrong." }: { detail: string; title?: string }) {
  return <div className="empty studio-state error-state" role="alert"><strong>{title}</strong><p>{detail}</p></div>;
}

export function StudioDialog({ children, label, trigger }: { children: ReactNode; label: string; trigger: string }) {
  const dialog = useRef<HTMLDialogElement>(null);
  return (
    <>
      <button className="button secondary" onClick={() => dialog.current?.showModal()} type="button">{trigger}</button>
      <dialog aria-label={label} className="studio-dialog" ref={dialog}>
        <div className="dialog-body">{children}</div>
        <form method="dialog"><button className="button ink" type="submit">Close</button></form>
      </dialog>
    </>
  );
}
