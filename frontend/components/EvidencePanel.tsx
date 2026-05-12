"use client";

import { useState } from "react";
import { X, Search, FileText, Hash, Star, Quote, Layers } from "lucide-react";
import type { ChatResponse, ChunkInfo } from "@/types";

interface Props {
  open: boolean;
  evidence: ChatResponse | null;
  onClose: () => void;
}

const confidenceColors: Record<string, string> = {
  High: "bg-emerald-900/40 text-emerald-400 border-emerald-800/60",
  Medium: "bg-amber-900/40 text-amber-400 border-amber-800/60",
  Low: "bg-red-900/40 text-red-400 border-red-800/60",
};

export function EvidencePanel({ open, evidence, onClose }: Props) {
  if (!evidence) return null;

  return (
    <>
      {open && (
        <button
          type="button"
          aria-label="Close evidence drawer"
          onClick={onClose}
          className="fixed inset-0 z-40 bg-black/40"
        />
      )}

      <aside
        className={`fixed right-0 top-0 z-50 flex h-full w-[520px] max-w-[95vw] flex-col border-l border-bg-border bg-bg-surface shadow-2xl transition-transform duration-300 ease-in-out ${
          open ? "translate-x-0" : "translate-x-full pointer-events-none"
        }`}
      >
        <div className="h-1 bg-blue-500" />
        <div className="border-b border-bg-border bg-bg-elevated px-5 py-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold uppercase tracking-wider text-slate-300">
              Evidence
            </span>
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-bg-border bg-bg-surface p-2 text-slate-500 transition-colors hover:border-blue-500 hover:text-slate-300"
              title="Close evidence"
            >
              <X size={16} />
            </button>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <span
              className={`rounded-full border px-2.5 py-1 text-sm font-medium ${
                confidenceColors[evidence.confidence] ?? confidenceColors.Low
              }`}
            >
              {evidence.confidence} confidence
            </span>
            <span className="rounded-full border border-bg-border bg-bg-elevated px-2.5 py-1 text-sm text-slate-400">
              {evidence.chunks_used} chunk{evidence.chunks_used !== 1 ? "s" : ""}
            </span>
            {evidence.average_score !== null && evidence.average_score !== undefined && (
              <span className="rounded-full border border-bg-border bg-bg-elevated px-2.5 py-1 text-sm text-slate-400">
                avg {evidence.average_score}/10
              </span>
            )}
            <span className="rounded-full border border-bg-border bg-bg-elevated px-2.5 py-1 text-sm text-slate-400">
              {evidence.answer_mode}
            </span>
          </div>
        </div>

        <div className="relative min-h-0 flex-1">
          <div className="h-full overflow-y-auto px-5 py-5 pb-12 space-y-4">
            {evidence.queries.length > 0 && (
              <Section icon={<Search size={13} />} title="Search queries">
                <ul className="space-y-2">
                  {evidence.queries.map((q, i) => (
                    <li key={i} className="flex items-start gap-3 text-sm text-slate-400">
                      <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-bg-border bg-bg-surface font-mono text-blue-500">
                        {i + 1}
                      </span>
                      <span className="leading-relaxed">{q}</span>
                    </li>
                  ))}
                </ul>
              </Section>
            )}

            {evidence.citations.length > 0 && (
              <Section icon={<Quote size={13} />} title="Citations">
                <ul className="space-y-2">
                  {evidence.citations.map((c, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-slate-400">
                      <FileText size={14} className="mt-0.5 shrink-0 text-slate-400" />
                      {c}
                    </li>
                  ))}
                </ul>
              </Section>
            )}

            {Object.keys(evidence.source_distribution ?? {}).length > 1 && (
              <Section icon={<Layers size={13} />} title="Source distribution">
                <ul className="space-y-2">
                  {Object.entries(evidence.source_distribution)
                    .sort((a, b) => b[1] - a[1])
                    .map(([source, count]) => {
                      const total = Object.values(evidence.source_distribution).reduce((s, n) => s + n, 0);
                      const pct = Math.round((count / total) * 100);
                      return (
                        <li key={source} className="space-y-1">
                          <div className="flex items-center justify-between text-xs">
                            <span className="max-w-[320px] truncate text-slate-400" title={source}>{source}</span>
                            <span className="shrink-0 text-slate-500">{count} chunk{count !== 1 ? "s" : ""} · {pct}%</span>
                          </div>
                          <div className="h-1 w-full rounded-full bg-bg-border">
                            <div
                              className="h-1 rounded-full bg-blue-500 transition-all"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </li>
                      );
                    })}
                </ul>
              </Section>
            )}

            {evidence.pages.length > 0 && (
              <Section icon={<Hash size={13} />} title="Pages referenced">
                <div className="flex flex-wrap gap-1.5">
                  {evidence.pages.map((p) => (
                    <span
                      key={p}
                      className="rounded border border-blue-900/40 bg-blue-950/40 px-2 py-0.5 font-mono text-sm text-blue-400"
                    >
                      p.{p}
                    </span>
                  ))}
                </div>
              </Section>
            )}

            {evidence.documents.length > 0 && (
              <Section icon={<Star size={13} />} title={`Retrieved chunks (${evidence.documents.length})`}>
                <div className="space-y-3">
                  {evidence.documents.map((chunk, i) => (
                    <ChunkCard key={`${chunk.source}-${i}`} index={i + 1} chunk={chunk} />
                  ))}
                </div>
              </Section>
            )}
          </div>
          <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-bg-surface to-transparent" />
        </div>
      </aside>
    </>
  );
}

function Section({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-bg-border bg-bg-elevated p-4">
      <div className="mb-2 flex items-center gap-1.5">
        <span className="text-slate-400">{icon}</span>
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          {title}
        </h3>
      </div>
      {children}
    </div>
  );
}

function ChunkCard({ index, chunk }: { index: number; chunk: ChunkInfo }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="space-y-3 rounded-2xl border border-bg-border bg-bg-surface p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-bg-border bg-bg-elevated font-mono text-sm text-blue-500">
            {index}
          </span>
          <span className="truncate text-sm text-slate-400" title={chunk.source}>
            {chunk.source}
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          {chunk.page !== null && chunk.page !== undefined && (
            <span className="text-sm text-slate-500">p.{chunk.page + 1}</span>
          )}
          {chunk.score !== null && chunk.score !== undefined && (
            <span
              className={`rounded px-1.5 py-0.5 font-mono text-sm ${
                chunk.score >= 7
                  ? "text-emerald-400 bg-emerald-950/30"
                  : chunk.score >= 5
                  ? "text-amber-400 bg-amber-950/30"
                  : "text-red-400 bg-red-950/30"
              }`}
            >
              {chunk.score}/10
            </span>
          )}
        </div>
      </div>
      <p className={`text-sm leading-relaxed text-slate-400 ${expanded ? "" : "line-clamp-5"}`}>
        {chunk.snippet}
      </p>
      <button
        type="button"
        onClick={() => setExpanded((value) => !value)}
        className="rounded-full border border-bg-border px-3 py-1 text-sm text-slate-300 transition-colors hover:border-blue-500 hover:text-blue-400"
      >
        {expanded ? "Show less" : "Show more"}
      </button>
    </div>
  );
}
