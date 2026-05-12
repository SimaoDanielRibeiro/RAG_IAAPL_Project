"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Check, Copy, Upload } from "lucide-react";
import { Composer } from "@/components/Composer";
import { Logo } from "@/components/Logo";
import type { ChatMessage, DocumentInfo } from "@/types";

type ChatPaneProps = {
  document: DocumentInfo | null;
  documentCount: number;
  messages: ChatMessage[];
  isAnswering: boolean;
  isIndexing: boolean;
  chatError: string | null;
  onSend: (question: string) => void;
  onUpload: (files: File[]) => void;
};

export function ChatPane({
  document,
  documentCount,
  messages,
  isAnswering,
  isIndexing,
  chatError,
  onSend,
  onUpload,
}: ChatPaneProps) {
  // Scroll anchor — sits at the very bottom of the message list
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, isAnswering]);

  if (!documentCount) {
    return (
      <section className="flex min-w-0 flex-1 flex-col bg-app">
        <EmptyState onUpload={onUpload} isIndexing={isIndexing} />
      </section>
    );
  }

  return (
    <section className="relative flex min-w-0 flex-1 flex-col bg-app">

      {/* ── Top bar ─────────────────────────────────── */}
      <header className="shrink-0 px-11 pt-8">
        <div className="mx-auto flex h-[52px] max-w-[760px] items-center justify-between border-b border-line">
          <div className="flex min-w-0 items-center gap-6">
            {/* Document name — display only, no dead button */}
            <span className="max-w-[300px] truncate text-[13px] font-medium text-primary">
              {document?.name ?? "Documents"}
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

      {/* ── Message list ──────────────────────────────── */}
      <div className="min-h-0 flex-1 overflow-y-auto px-11 pb-[172px] pt-8">
        <div className="mx-auto flex max-w-[760px] flex-col gap-10">

          {/* Welcome state */}
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
            <MessageRow key={msg.id} message={msg} />
          ))}

          {isAnswering && <StreamingRow />}

          {chatError && (
            <p className="rounded-md border border-line bg-elevated px-4 py-3 text-[13px] leading-5 text-[#fca5a5]">
              {chatError}
            </p>
          )}

          {/* Invisible anchor for auto-scroll */}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* ── Composer ──────────────────────────────────── */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-app px-11 pb-6 pt-6">
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

/* ── MessageRow ───────────────────────────────────────── */

function MessageRow({ message }: { message: ChatMessage }) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";

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
        /* ── User bubble ─────────────────── */
        <div className="flex max-w-[520px] items-end gap-3">
          <div className="rounded-[14px] bg-elevated px-5 py-4 text-[16px] leading-7 text-primary">
            {message.content}
          </div>
          <time className="mb-1 shrink-0 text-[11px] text-muted">{time}</time>
        </div>
      ) : (
        /* ── Assistant reply ─────────────── */
        <div className="group w-full max-w-[590px]">
          <p className="whitespace-pre-wrap text-[16px] leading-[1.7] text-primary">
            {message.content}
          </p>

          {/* Copy + timestamp — fade in on hover */}
          <div className="mt-3 flex items-center gap-3 opacity-0 transition-opacity duration-150 group-hover:opacity-100">
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

/* ── Streaming indicator ──────────────────────────────── */

function StreamingRow() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18, ease: "easeOut" }}
      className="w-full max-w-[590px]"
    >
      <p className="text-[16px] leading-[1.7] text-primary">
        Searching your documents and checking evidence
        <span className="lumen-caret ml-1 inline-block h-[18px] w-px translate-y-0.5 bg-primary" />
      </p>
    </motion.div>
  );
}

/* ── Empty / upload state ─────────────────────────────── */

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
