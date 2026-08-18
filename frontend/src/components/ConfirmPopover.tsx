"use client";

import { useEffect, useRef, useState } from "react";
import { AlertTriangle } from "lucide-react";

type ConfirmPopoverProps = {
  /** The element that anchors the popover and toggles it on click. */
  trigger: (open: () => void) => React.ReactNode;
  title: string;
  body: React.ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void | Promise<void>;
  /** Disables confirm/cancel buttons while the async action is in flight. */
  busy?: boolean;
  /** Visual tone for the confirm button. Defaults to danger (red). */
  tone?: "danger" | "neutral";
};

/**
 * Lightweight inline confirm popover — the first modal/popover in the
 * project. No portal, no focus-trap, no Radix — just an absolutely-
 * positioned dialog anchored to its trigger. Escape and outside-click
 * both dismiss it.
 *
 * Reused by both the /resumes tab (delete a resume row) and the
 * /analyze page (delete the currently-selected resume).
 */
export function ConfirmPopover({
  trigger,
  title,
  body,
  confirmLabel = "Delete",
  cancelLabel = "Cancel",
  onConfirm,
  busy = false,
  tone = "danger",
}: ConfirmPopoverProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Escape closes the popover. Outside-click on `document` closes it too
  // (we compare against the container so clicks on the trigger or inside
  // the popover don't immediately close it).
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    function onMouseDown(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onMouseDown);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onMouseDown);
    };
  }, [open]);

  async function handleConfirm() {
    try {
      await onConfirm();
      setOpen(false);
    } catch {
      // Keep the popover open so the user sees the error in the parent
      // component (which renders it inline) and can retry.
    }
  }

  const confirmClass =
    tone === "danger"
      ? "bg-red-600 hover:bg-red-700 text-white"
      : "bg-gray-800 hover:bg-gray-900 text-white";

  return (
    <div ref={containerRef} className="relative inline-block">
      {trigger(() => setOpen(true))}
      {open && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={title}
          className="absolute right-0 top-full mt-2 z-50 w-72 rounded-xl border border-gray-200 bg-white shadow-lg p-4"
        >
          <div className="flex items-start gap-2">
            <AlertTriangle
              className={`w-4 h-4 mt-0.5 shrink-0 ${
                tone === "danger" ? "text-red-600" : "text-gray-500"
              }`}
            />
            <div className="text-sm font-semibold text-gray-900">{title}</div>
          </div>
          <div className="mt-1.5 text-xs text-gray-600 pl-6">{body}</div>
          <div className="mt-3 flex justify-end gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={() => setOpen(false)}
              className="px-3 py-1.5 text-xs rounded-md border border-gray-200 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              {cancelLabel}
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={handleConfirm}
              className={`px-3 py-1.5 text-xs rounded-md disabled:opacity-50 ${confirmClass}`}
            >
              {busy ? "Working…" : confirmLabel}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}