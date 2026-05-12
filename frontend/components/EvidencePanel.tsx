import { motion } from "framer-motion";
import { X } from "lucide-react";
import { EvidenceCard } from "@/components/EvidenceCard";
import type { ChatResponse } from "@/types";

type EvidencePanelProps = {
  evidence: ChatResponse | null;
  onClose: () => void;
};

const CONFIDENCE_STYLES: Record<
  "High" | "Medium" | "Low",
  { dot: string; text: string; label: string }
> = {
  High:   { dot: "bg-[#4ADE80]", text: "text-[#4ADE80]", label: "High confidence"   },
  Medium: { dot: "bg-accent",    text: "text-accent",     label: "Medium confidence" },
  Low:    { dot: "bg-[#F97316]", text: "text-[#F97316]",  label: "Low confidence"   },
};

export function EvidencePanel({ evidence, onClose }: EvidencePanelProps) {
  const chunks     = evidence?.documents ?? [];
  const confidence = evidence?.confidence ?? null;
  const conf       = confidence ? CONFIDENCE_STYLES[confidence] : null;

  const citations        = evidence?.citations ?? [];
  const sourceDistrib    = evidence?.source_distribution ?? {};
  const sourceCount      = Object.keys(sourceDistrib).length;

  return (
    <motion.aside
      initial={{ x: 40, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 40, opacity: 0 }}
      transition={{ duration: 0.18, ease: "easeOut" }}
      className="h-full w-[380px] shrink-0 overflow-hidden border-l border-line bg-app"
    >
      <div className="flex h-full flex-col">
        {/* ── Header ─────────────────────────────── */}
        <header className="flex shrink-0 items-start justify-between px-7 pb-5 pt-8">
          <div>
            <h2 className="text-[16px] font-semibold leading-6 text-primary">
              Evidence
            </h2>

            <p className="mt-1 text-[12px] font-normal text-secondary">
              {chunks.length
                ? `${chunks.length} supporting excerpt${chunks.length === 1 ? "" : "s"}`
                : "Evidence will appear after an answer"}
            </p>

            {/* Confidence badge */}
            {conf && (
              <span
                className={`mt-2 inline-flex items-center gap-1.5 text-[12px] font-medium ${conf.text}`}
              >
                <span className={`h-1.5 w-1.5 rounded-full ${conf.dot}`} />
                {conf.label}
              </span>
            )}
          </div>

          <button
            type="button"
            aria-label="Close evidence panel"
            onClick={onClose}
            className="rounded-md p-1 text-secondary transition-colors hover:bg-hover hover:text-primary"
          >
            <X size={18} strokeWidth={1.8} />
          </button>
        </header>

        {/* ── Scrollable body ─────────────────────── */}
        <div className="min-h-0 flex-1 overflow-y-auto px-7 pb-6">

          {/* Citations */}
          {citations.length > 0 && (
            <section className="mb-5">
              <p className="mb-2.5 text-[11px] font-medium uppercase tracking-[0.06em] text-muted">
                Citations
              </p>
              <ul className="space-y-1.5">
                {citations.map((c, i) => (
                  <li key={i} className="flex items-start gap-2 text-[13px] leading-5 text-secondary">
                    <span className="mt-px shrink-0 text-accent">›</span>
                    {c}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Source distribution — only when multiple files contributed */}
          {sourceCount > 1 && (
            <section className="mb-5">
              <p className="mb-2.5 text-[11px] font-medium uppercase tracking-[0.06em] text-muted">
                Source distribution
              </p>
              <ul className="space-y-3">
                {Object.entries(sourceDistrib)
                  .sort((a, b) => b[1] - a[1])
                  .map(([source, count]) => {
                    const total = Object.values(sourceDistrib).reduce((s, n) => s + n, 0);
                    const pct   = Math.round((count / total) * 100);
                    return (
                      <li key={source} className="space-y-1">
                        <div className="flex items-center justify-between gap-2 text-[12px]">
                          <span className="min-w-0 truncate text-secondary" title={source}>
                            {source}
                          </span>
                          <span className="shrink-0 text-muted">
                            {count} chunk{count !== 1 ? "s" : ""} · {pct}%
                          </span>
                        </div>
                        <div className="h-1 w-full rounded-full bg-elevated">
                          <div
                            className="h-1 rounded-full bg-accent transition-all"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </li>
                    );
                  })}
              </ul>
            </section>
          )}

          {/* ── Cards ──────────────────────────────── */}
          {chunks.length ? (
            <div className="space-y-3">
              {chunks.map((chunk, index) => (
                <EvidenceCard
                  key={`${chunk.source}-${chunk.page ?? "x"}-${index}`}
                  chunk={chunk}
                  index={index}
                />
              ))}
            </div>
          ) : (
            <div className="rounded-[10px] border border-line bg-sidebar p-4 text-[13px] leading-5 text-secondary">
              Ask a question after uploading files. Lumen will show only the
              retrieved excerpts returned by your backend.
            </div>
          )}
        </div>
      </div>
    </motion.aside>
  );
}
