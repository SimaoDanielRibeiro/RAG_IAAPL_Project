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

        {/* ── Cards ──────────────────────────────── */}
        <div className="min-h-0 flex-1 overflow-y-auto px-7 pb-6">
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
