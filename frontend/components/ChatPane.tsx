"use client";

import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { Check, Copy, Layers, Upload } from "lucide-react";
import { Composer } from "@/components/Composer";
import { Logo } from "@/components/Logo";
import { stripMarkdown } from "@/lib/text";
import type { ChatMessage, ChatResponse, ChunkInfo, DocumentInfo } from "@/types";

type ChatPaneProps = {
  documents: DocumentInfo[];
  messages: ChatMessage[];
  isAnswering: boolean;
  isIndexing: boolean;
  chatError: string | null;
  selectedDocumentIds: string[];
  streamingId?: string | null;
  onSend: (question: string) => void;
  onUpload: (files: File[]) => void;
  onClearScope: () => void;
  onCitationClick?: (chunkIndex: number, evidence: ChatResponse) => void;
};

export function ChatPane({
  documents,
  messages,
  isAnswering,
  isIndexing,
  chatError,
  selectedDocumentIds,
  streamingId,
  onSend,
  onUpload,
  onClearScope,
  onCitationClick,
}: ChatPaneProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Track the streaming message's content length so we keep the view
  // pinned to the bottom as tokens arrive (in addition to scrolling on
  // new messages and when answering toggles).
  const streamingLength = streamingId
    ? messages.find((m) => m.id === streamingId)?.content.length ?? 0
    : 0;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: streamingId ? "auto" : "smooth",
      block:    "end",
    });
  }, [messages.length, isAnswering, streamingId, streamingLength]);

  const documentCount = documents.length;
  const selectedDocuments = documents.filter((doc) =>
    selectedDocumentIds.includes(doc.id),
  );
  const activeCount = selectedDocuments.length;
  const isAllFiles = activeCount === 0 || activeCount === documentCount;
  const scopeLabel = isAllFiles
    ? "All files"
    : activeCount === 1
      ? selectedDocuments[0]?.name ?? "1 file"
      : `${activeCount} files`;

  if (!documentCount) {
    return (
      <section className="flex min-w-0 flex-1 flex-col bg-app/20 backdrop-blur-2xl">
        <EmptyState onUpload={onUpload} isIndexing={isIndexing} />
      </section>
    );
  }

  return (
    <section className="relative flex min-w-0 flex-1 flex-col bg-app/20 backdrop-blur-2xl">
      <header className="shrink-0 px-11 pt-8">
        <div className="mx-auto flex h-[52px] max-w-[760px] items-center justify-between border-b border-line">
          <div className="flex min-w-0 items-center gap-6">
            <span className="max-w-[300px] truncate text-[13px] font-medium text-primary">
              Documents
            </span>

            <span className="text-[13px] text-secondary">
              {documentCount} file{documentCount === 1 ? "" : "s"}
            </span>

            <span className="inline-flex items-center gap-2 text-[13px] text-secondary">
              <span className="h-1.5 w-1.5 rounded-full bg-ready" />
              Ready
            </span>
          </div>
        </div>
      </header>

      {documentCount > 1 && (
        <div className="shrink-0 px-11">
          <div className="mx-auto flex max-w-[760px] items-center gap-3 py-3">
            <span className="shrink-0 text-[11px] font-medium uppercase tracking-[0.06em] text-muted">
              Searching in
            </span>
            <span className={`inline-flex max-w-[420px] items-center gap-1.5 rounded-full px-3 py-1 text-[12px] font-medium border ${
              isAllFiles
                ? "border-accent/30 bg-accent/15 text-accent"
                : "border-accent/40 bg-accent/10 text-accent"
            }`}>
              {!isAllFiles && <Layers size={11} strokeWidth={1.8} />}
              {isAllFiles
                ? <><Layers size={11} strokeWidth={1.8} /> All {documentCount} files</>
                : <span className="truncate">{scopeLabel} selected</span>
              }
            </span>
            {!isAllFiles && (
              <button
                type="button"
                onClick={onClearScope}
                className="text-[11px] text-secondary underline-offset-2 hover:text-primary hover:underline transition-colors"
              >
                Clear
              </button>
            )}
          </div>
        </div>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto px-11 pb-[172px] pt-8">
        <div className="mx-auto flex max-w-[760px] flex-col gap-10">
          {!messages.length && !isAnswering && (
            <div className="pt-24 text-center">
              <Logo className="justify-center" />
              <p className="mt-5 text-[16px] font-medium text-primary">
                Ask a question about your uploaded documents.
              </p>
              <p className="mt-2 text-[13px] text-secondary">
                Answers and evidence will come from your indexed files.
              </p>
            </div>
          )}

          {messages.map((msg) => (
            <MessageRow
              key={msg.id}
              message={msg}
              isStreaming={msg.id === streamingId}
              onCitationClick={onCitationClick}
            />
          ))}

          {chatError && (
            <p className="rounded-md border border-line bg-elevated px-4 py-3 text-[13px] leading-5 text-[#fca5a5]">
              {chatError}
            </p>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-app via-app/85 to-transparent px-11 pb-6 pt-10">
        <div className="pointer-events-auto mx-auto max-w-[760px]">
          <Composer
            disabled={!documentCount || isIndexing}
            busy={isAnswering}
            onSend={onSend}
            onUpload={onUpload}
          />
        </div>
      </div>
    </section>
  );
}

function MessageRow({
  message,
  isStreaming,
  onCitationClick,
}: {
  message: ChatMessage;
  isStreaming?: boolean;
  onCitationClick?: (chunkIndex: number, evidence: ChatResponse) => void;
}) {
  const [copied, setCopied] = useState(false);
  const isUser   = message.role === "user";
  const evidence = message.evidence;
  const chunks   = evidence?.documents ?? [];
  const isEmptyStream = isStreaming && !message.content;

  const handleCitation = evidence && onCitationClick
    ? (idx: number) => onCitationClick(idx, evidence)
    : undefined;

  const time = message.timestamp.toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18, ease: "easeOut" }}
      className={`flex w-full ${isUser ? "justify-end" : "justify-start"}`}
    >
      {isUser ? (
        <div className="flex max-w-[520px] items-end gap-3">
          <div className="rounded-[14px] bg-elevated px-5 py-4 text-[16px] leading-7 text-primary">
            {message.content}
          </div>
          <time className="mb-1 shrink-0 text-[11px] text-muted">{time}</time>
        </div>
      ) : (
        <div className="group w-full max-w-[590px]">
          {isEmptyStream ? (
            <p className="text-[16px] leading-[1.7] text-primary">
              Searching your documents and checking evidence
              <span className="lumen-caret ml-1 inline-block h-[18px] w-px translate-y-0.5 bg-primary" />
            </p>
          ) : (
            <p className="whitespace-pre-wrap text-[16px] leading-[1.7] text-primary">
              {renderAnswerWithCitations(message.content, chunks, handleCitation)}
              {isStreaming && (
                <span className="lumen-caret ml-1 inline-block h-[18px] w-px translate-y-0.5 bg-primary" />
              )}
            </p>
          )}

          <div className={`mt-3 flex items-center gap-3 transition-opacity duration-150 ${isStreaming ? "opacity-0" : "opacity-0 group-hover:opacity-100"}`}>
            <button
              type="button"
              onClick={handleCopy}
              className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[12px] text-secondary transition-colors hover:bg-hover hover:text-primary"
            >
              {copied
                ? <Check size={13} className="text-accent" />
                : <Copy size={13} />}
              <span>{copied ? "Copied" : "Copy"}</span>
            </button>
            <time className="text-[11px] text-muted">{time}</time>
          </div>
        </div>
      )}
    </motion.div>
  );
}

function EmptyState({
  onUpload,
  isIndexing,
}: {
  onUpload: (files: File[]) => void;
  isIndexing: boolean;
}) {
  return (
    <div className="grid h-full place-items-center">
      <div className="flex flex-col items-center gap-5 text-center">
        <Logo className="scale-125" />
        <div>
          <p className="text-[16px] font-medium text-primary">
            Upload a PDF to begin
          </p>
          <p className="mt-2 text-[13px] text-secondary">
            You can also upload DOCX, TXT, and Markdown files.
          </p>
        </div>
        <label className="inline-flex h-10 cursor-pointer items-center gap-2 rounded-md bg-primary px-4 text-[13px] font-medium text-app transition-opacity hover:opacity-90">
          <Upload size={15} strokeWidth={1.8} />
          {isIndexing ? "Indexing..." : "Upload files"}
          <input
            type="file"
            multiple
            accept=".pdf,.docx,.txt,.md"
            className="hidden"
            disabled={isIndexing}
            onChange={(e) => {
              onUpload(Array.from(e.target.files ?? []));
              e.target.value = "";
            }}
          />
        </label>
      </div>
    </div>
  );
}

/* ── Inline citation rendering ───────────────────────────────
   The LLM emits citations like [main_48.pdf, p.5]. We replace
   those with compact accent chips numbered to MATCH the
   1-based position of the matched chunk in the Evidence panel.
   Clicking a chip scrolls that chunk into view and pulses its
   card so the user can see exactly where the claim came from. */

// Matches citation variants the LLM tends to produce in both modes:
//   [file.pdf]                  · just filename
//   [file.pdf, p.5]             · canonical
//   [file.pdf, p. 5]            · space after p.
//   [file.pdf p5]               · no comma, no dot
//   [file.pdf, page 5]          · "page" word
//   [file.pdf, pp.3-5]          · page range (first page captured)
//   [file.pdf, 5]               · bare number, no p/page marker
//   [**file.pdf**, p.5]         · markdown bold around filename
//   [Source: file.pdf, p.5]     · common prefix
const CITATION_PATTERN =
  /\[\s*\**\s*([^\[\]*]+?\.(?:pdf|docx|txt|md))\s*\**\s*(?:[,\s]+(?:pp?\.?|pages?)?\s*(\d+)[^\]]*)?\s*\]/gi;

function cleanFilename(raw: string): string {
  return raw
    .replace(/^\*+|\*+$/g, "")
    .replace(/^(?:source|see|ref|cite)s?:\s*/i, "")
    .trim();
}

/**
 * Map a citation `[filename, p.N]` to the index of the best-matching chunk in
 * the Evidence panel. The returned index is what the chip's number reflects
 * (1-based: chipNumber === chunkIndex + 1), and is also what gets passed back
 * to `onCitationClick` so the matching card animates.
 *
 * Matching is intentionally forgiving because small chat models drift from
 * the requested `[filename, p.N]` format:
 *   1. Filename match by lowercase equality, then by substring containment
 *      (handles truncated or basename-only citations).
 *   2. Within the matched source, prefer an exact page hit (LLM's 1-based
 *      page minus 1 == chunk.page which is 0-based).
 *   3. If no exact page is available, fall back to the chunk on the
 *      nearest page — never just "first chunk by source", which is what
 *      caused chip ↔ card number drift before.
 */
function findChunkIndex(
  chunks: ChunkInfo[],
  filename: string,
  pageStr: string | undefined,
): number {
  const target     = cleanFilename(filename).toLowerCase();
  const targetPage = pageStr ? parseInt(pageStr, 10) - 1 : null;

  if (!target || !chunks.length) return -1;

  let sourceMatches = collectMatchingIndices(chunks, (c) =>
    c.source.toLowerCase() === target,
  );
  if (sourceMatches.length === 0) {
    sourceMatches = collectMatchingIndices(chunks, (c) => {
      const s = c.source.toLowerCase();
      return s.includes(target) || target.includes(s);
    });
  }
  if (sourceMatches.length === 0) return -1;
  if (targetPage === null)        return sourceMatches[0];

  // Exact page match — what we usually expect.
  const exact = sourceMatches.find((i) => chunks[i].page === targetPage);
  if (exact !== undefined) return exact;

  // Nearest page within the same source.
  let best     = sourceMatches[0];
  let bestDist = Infinity;
  for (const i of sourceMatches) {
    const p = chunks[i].page;
    if (p === null || p === undefined) continue;
    const d = Math.abs(p - targetPage);
    if (d < bestDist) {
      bestDist = d;
      best     = i;
    }
  }
  return best;
}

function collectMatchingIndices(
  chunks: ChunkInfo[],
  predicate: (chunk: ChunkInfo) => boolean,
): number[] {
  const out: number[] = [];
  for (let i = 0; i < chunks.length; i++) {
    if (predicate(chunks[i])) out.push(i);
  }
  return out;
}

function renderAnswerWithCitations(
  text: string,
  chunks: ChunkInfo[],
  onCitationClick?: (chunkIndex: number) => void,
): ReactNode[] {
  if (!text) return [];
  const clean = stripMarkdown(text);

  // Process per line so each paragraph (and each bullet) gets its OWN cluster
  // of chips appended at its end. The body text is never altered; we only
  // strip the LLM's bracket markers and tidy the whitespace they leave behind.
  const lines = clean.split("\n");
  const parts: ReactNode[] = [];

  lines.forEach((line, lineIdx) => {
    const found: Array<{ chunkIdx: number; label: string }> = [];
    const seen  = new Set<string>();

    for (const m of line.matchAll(CITATION_PATTERN)) {
      const chunkIdx = findChunkIndex(chunks, m[1], m[2]);
      const label    = m[2] ? `${m[1]}, p.${m[2]}` : m[1];
      // Dedupe so a paragraph that cites the same chunk twice gets only one
      // chip at the end. Unmatched citations are deduped on their label.
      const key = chunkIdx >= 0 ? `c${chunkIdx}` : `u${label.toLowerCase()}`;
      if (seen.has(key)) continue;
      seen.add(key);
      found.push({ chunkIdx, label });
    }

    // Remove the bracket markers and clean up whitespace artifacts they leave
    // (double spaces, an orphan space before punctuation, trailing spaces).
    const stripped = line
      .replace(CITATION_PATTERN, "")
      .replace(/[ \t]+([.,!?;:])/g, "$1")
      .replace(/[ \t]{2,}/g, " ")
      .replace(/^[ \t]+|[ \t]+$/g, "");

    if (stripped) parts.push(<span key={`t-${lineIdx}`}>{stripped}</span>);

    if (found.length > 0) {
      // Single space between the last word and the first chip; chips have
      // their own mx-0.5 so subsequent ones space themselves.
      if (stripped) parts.push(" ");
      found.forEach((f, i) => {
        parts.push(
          <CitationChip
            key={`c-${lineIdx}-${i}`}
            index={f.chunkIdx >= 0 ? f.chunkIdx + 1 : null}
            label={f.label}
            onClick={
              f.chunkIdx >= 0 && onCitationClick
                ? () => onCitationClick(f.chunkIdx)
                : undefined
            }
          />,
        );
      });
    }

    // Preserve the original newline so paragraph spacing carries through the
    // parent <p>'s whitespace-pre-wrap.
    if (lineIdx < lines.length - 1) parts.push("\n");
  });

  return parts;
}

function CitationChip({
  index,
  label,
  onClick,
}: {
  index: number | null;
  label: string;
  onClick?: () => void;
}) {
  const interactive = !!onClick;
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!interactive}
      title={
        interactive
          ? `Open evidence ${index} — ${label}`
          : `${label} (no matching chunk)`
      }
      className={`mx-0.5 inline-flex h-[20px] min-w-[20px] -translate-y-px items-center justify-center rounded-[5px] border border-accent/40 bg-accent/10 px-1 align-middle text-[10.5px] font-medium leading-none text-accent transition-all ${
        interactive
          ? "cursor-pointer hover:border-accent hover:bg-accent/25 hover:shadow-[0_0_8px_rgba(224,177,91,0.4)]"
          : "cursor-default opacity-50"
      }`}
    >
      {index ?? "?"}
    </button>
  );
}
