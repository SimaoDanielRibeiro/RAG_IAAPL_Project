"use client";

import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { Check, Copy, Expand } from "lucide-react";
import type { ChunkInfo } from "@/types";

// Constant outside the component — not recreated on every render
const SNIPPET_THRESHOLD = 280;

type EvidenceCardProps = {
  chunk: ChunkInfo;
  index: number;
  isHighlighted?: boolean;
};

export function EvidenceCard({ chunk, index, isHighlighted }: EvidenceCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [copied,   setCopied]   = useState(false);
  const articleRef               = useRef<HTMLElement>(null);

  // Scroll into view when this card becomes the highlighted one
  useEffect(() => {
    if (isHighlighted) {
      articleRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [isHighlighted]);

  const fullText    = (chunk.snippet ?? "").replace(/\s+/g, " ").trim();
  const needsMore   = fullText.length > SNIPPET_THRESHOLD;
  const displayText = needsMore && !expanded
    ? `${fullText.slice(0, SNIPPET_THRESHOLD - 1)}…`
    : fullText;

  const previewLines = toPreviewLines(fullText);

  /* ── Clipboard actions ──────────────────────────── */
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(fullText || "No text available.");
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };

  return (
    <motion.article
      ref={articleRef}
      animate={
        isHighlighted
          ? {
              boxShadow: [
                "0 0 0 0px rgba(224,177,91,0)",
                "0 0 0 2px rgba(224,177,91,0.55), 0 0 24px rgba(224,177,91,0.35)",
                "0 0 0 1px rgba(224,177,91,0.25), 0 0 12px rgba(224,177,91,0.10)",
              ],
            }
          : { boxShadow: "0 0 0 0px rgba(224,177,91,0)" }
      }
      transition={{ duration: 1.6, ease: "easeOut" }}
      className="group rounded-[10px] border border-line bg-sidebar/70 p-4 backdrop-blur-sm transition-colors hover:border-[rgba(255,255,255,0.10)]">

      {/* ── Card header ──────────────────────────────── */}
      <div className="flex items-start gap-3">
        <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-accent text-[12px] font-semibold text-app">
          {index + 1}
        </span>

        <div className="min-w-0 flex-1">
          <p className="truncate text-[13px] font-medium text-primary">
            {chunk.source || "Source"}
          </p>
          <div className="mt-1.5 flex items-center justify-between gap-3">
            <p className="min-w-0 truncate text-[12px] text-secondary">
              {formatPage(chunk.page)}
              <span className="mx-1.5 text-muted">·</span>
              Retrieved excerpt
            </p>
            {chunk.score !== null && chunk.score !== undefined && (
              <span className="shrink-0 text-[12px] font-medium text-accent">
                {formatScore(chunk.score)}
              </span>
            )}
          </div>
        </div>
        {/* MoreHorizontal removed — all actions live in the hover bar */}
      </div>

      {/* ── PDF-style preview ─────────────────────────── */}
      <div className="mt-4 rounded-md bg-[#FAFAFA] px-7 py-5 shadow-paper">
        <div className="mx-auto max-w-[250px]">
          <div className="mb-3 flex items-baseline gap-3">
            <span className="text-[10px] font-semibold text-[#404040]">
              {formatPage(chunk.page)}
            </span>
            <span className="text-[10px] font-semibold uppercase tracking-[0.03em] text-[#171717]">
              Extract
            </span>
          </div>
          <div className="space-y-1.5 text-[11px] font-medium leading-[1.45] text-[#2a2a2a]">
            {previewLines.map((line, i) => (
              <p
                key={`${i}-${line.slice(0, 8)}`}
                className={
                  i === 1
                    ? "rounded-sm bg-[rgba(224,177,91,0.25)] px-1"
                    : "blur-[0.18px]"
                }
              >
                {line}
              </p>
            ))}
          </div>
        </div>
      </div>

      {/* ── Excerpt text ──────────────────────────────── */}
      <p className="mt-3 text-[14px] leading-[1.6] text-secondary">
        {displayText || "No excerpt text was returned for this source."}
      </p>

      {/* "View all" — always visible when there is more text */}
      {needsMore && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="mt-2 text-[13px] font-medium text-accent transition-colors hover:text-accent-hover"
        >
          {expanded ? "Show less ↑" : "View all →"}
        </button>
      )}

      {/* ── Hover-only action bar ─────────────────────── */}
      <div className="mt-4 flex items-center justify-end gap-1 opacity-0 transition-opacity duration-150 ease-out group-hover:opacity-100">
        <ActionBtn label={copied ? "Copied!" : "Copy"} onClick={handleCopy}>
          {copied
            ? <Check size={14} className="text-accent" />
            : <Copy size={14} />}
        </ActionBtn>

        <ActionBtn
          label={expanded ? "Collapse" : "Expand"}
          onClick={() => setExpanded((v) => !v)}
        >
          <Expand size={14} />
        </ActionBtn>
      </div>
    </motion.article>
  );
}

/* ── Helpers ─────────────────────────────────────────── */

function ActionBtn({
  children,
  label,
  onClick,
}: {
  children: ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className="rounded-md p-1.5 text-secondary transition-colors hover:bg-hover hover:text-primary"
    >
      {children}
    </button>
  );
}

function formatPage(page: number | null | undefined) {
  if (page === null || page === undefined) return "Page unknown";
  return `Page ${page + 1}`;
}

function formatScore(score: number) {
  if (score <= 1)  return `${Math.round(score * 100)}% match`;
  if (score <= 10) return `${Math.round(score * 10)}% match`;
  return `${Math.round(score)}% match`;
}

function toPreviewLines(text: string): string[] {
  if (!text) return [" ", " ", " "];
  const words = text.split(" ");
  const lines: string[] = [];

  for (let i = 0; i < words.length && lines.length < 4; ) {
    lines.push(words.slice(i, i + 8).join(" "));
    i += 8;
  }

  while (lines.length < 3) lines.push(" ");
  return lines;
}
