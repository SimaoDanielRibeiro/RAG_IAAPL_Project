"use client";

import { useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Download, ExternalLink, X } from "lucide-react";
import { api } from "@/lib/api";

export type SourcePreviewTarget = {
  documentId: string;
  source: string;
  page: number | null;       // 0-based, as stored on the chunk
  snippet?: string | null;
};

type SourcePreviewModalProps = {
  target: SourcePreviewTarget | null;
  onClose: () => void;
};

export function SourcePreviewModal({ target, onClose }: SourcePreviewModalProps) {
  // Close on Escape.
  useEffect(() => {
    if (!target) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [target, onClose]);

  return (
    <AnimatePresence>
      {target && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.97, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: 8 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            className="relative flex h-[88vh] w-[min(1100px,94vw)] flex-col overflow-hidden rounded-[14px] border border-line bg-sidebar/95 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <PreviewHeader target={target} onClose={onClose} />
            <PreviewBody target={target} />
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function PreviewHeader({
  target,
  onClose,
}: {
  target: SourcePreviewTarget;
  onClose: () => void;
}) {
  const pageLabel = target.page !== null ? `Page ${target.page + 1}` : "Page unknown";
  const fileUrl = api.documentFileUrl(target.documentId, pageNumber(target.page));

  return (
    <header className="flex shrink-0 items-center justify-between gap-4 border-b border-line bg-elevated/40 px-5 py-3">
      <div className="min-w-0 flex-1">
        <p className="truncate text-[14px] font-medium text-primary">
          {target.source}
        </p>
        <p className="mt-0.5 truncate text-[12px] text-secondary">{pageLabel}</p>
      </div>

      <div className="flex shrink-0 items-center gap-1.5">
        <a
          href={fileUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-[12px] text-secondary transition-colors hover:bg-hover hover:text-primary"
          title="Open in new tab"
        >
          <ExternalLink size={13} strokeWidth={1.8} />
          Open
        </a>
        <a
          href={api.documentFileUrl(target.documentId)}
          download={target.source}
          className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-[12px] text-secondary transition-colors hover:bg-hover hover:text-primary"
          title="Download original file"
        >
          <Download size={13} strokeWidth={1.8} />
          Download
        </a>
        <button
          type="button"
          aria-label="Close preview"
          onClick={onClose}
          className="grid h-8 w-8 place-items-center rounded-md text-secondary transition-colors hover:bg-hover hover:text-primary"
        >
          <X size={16} strokeWidth={1.8} />
        </button>
      </div>
    </header>
  );
}

function PreviewBody({ target }: { target: SourcePreviewTarget }) {
  const ext = extensionOf(target.source);
  const fileUrl = api.documentFileUrl(target.documentId, pageNumber(target.page));

  if (ext === "pdf") {
    return (
      <iframe
        key={fileUrl}
        title={`Preview of ${target.source}`}
        src={fileUrl}
        className="h-full w-full flex-1 border-0 bg-[#1f1f1f]"
      />
    );
  }

  // Browsers won't render DOCX inline. For TXT / MD we render the snippet as
  // a fallback so the user still sees the cited content in context, with a
  // download button in the header.
  return (
    <div className="flex-1 overflow-y-auto px-8 py-6">
      <div className="mx-auto max-w-[760px]">
        <p className="text-[12px] font-medium uppercase tracking-[0.06em] text-muted">
          Inline preview not available
        </p>
        <p className="mt-2 text-[14px] leading-6 text-secondary">
          The browser cannot render <span className="text-primary">.{ext}</span>{" "}
          files inline. Use the Download button above to open the original
          file, or read the retrieved excerpt below:
        </p>
        {target.snippet && (
          <pre className="mt-5 whitespace-pre-wrap rounded-[10px] border border-line bg-app/40 p-5 text-[13px] leading-[1.7] text-primary">
            {target.snippet}
          </pre>
        )}
      </div>
    </div>
  );
}

function extensionOf(source: string): string {
  const dot = source.lastIndexOf(".");
  return dot >= 0 ? source.slice(dot + 1).toLowerCase() : "";
}

function pageNumber(page: number | null): number | null {
  // Chunks store 0-based pages; the PDF anchor expects 1-based.
  return page === null || page === undefined ? null : page + 1;
}
