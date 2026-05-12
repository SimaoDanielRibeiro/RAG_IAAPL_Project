"use client";

import { useEffect, useRef, useState } from "react";
import { AlertCircle, FileUp, Loader2, Send } from "lucide-react";
import { MessageBubble } from "./MessageBubble";
import type { ChatMessage, ChatResponse } from "@/types";

interface Props {
  messages: ChatMessage[];
  isAnswering: boolean;
  chatError: string | null;
  hasDocuments: boolean;
  isIndexing: boolean;
  onSend: (question: string) => void;
  onShowEvidence: (evidence: ChatResponse) => void;
}

export function ChatArea({
  messages,
  isAnswering,
  chatError,
  hasDocuments,
  isIndexing,
  onSend,
  onShowEvidence,
}: Props) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const disabled = !hasDocuments || isAnswering || isIndexing;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isAnswering]);

  const submit = () => {
    const q = input.trim();
    if (!q || disabled) return;
    setInput("");
    onSend(q);
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  return (
    <main className="min-h-0 flex-1 bg-bg-base p-4 sm:p-6 lg:p-8">
      <section className="mx-auto flex h-full max-w-5xl flex-col overflow-hidden rounded-[28px] border border-bg-border bg-bg-surface shadow-2xl">
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="min-h-0 flex-1 overflow-y-auto px-5 py-8 sm:px-8 lg:px-10">
            <div className="mx-auto flex w-full max-w-3xl flex-col space-y-8">
              {messages.length === 0 && (
                <EmptyState hasDocuments={hasDocuments} isIndexing={isIndexing} />
              )}
              {messages.map((msg) => (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  onShowEvidence={msg.evidence ? onShowEvidence : undefined}
                />
              ))}

              {isAnswering && (
                <div className="flex w-full items-center gap-1.5 py-3 pl-4">
                  <span className="h-2 w-2 rounded-full bg-slate-500 animate-bounce [animation-delay:0ms]" />
                  <span className="h-2 w-2 rounded-full bg-slate-500 animate-bounce [animation-delay:150ms]" />
                  <span className="h-2 w-2 rounded-full bg-slate-500 animate-bounce [animation-delay:300ms]" />
                </div>
              )}

              <div ref={bottomRef} />
            </div>
          </div>

          <div className="border-t border-bg-border px-5 py-4 sm:px-8 lg:px-10">
            {chatError && (
              <div className="mx-auto mb-3 flex w-full max-w-3xl items-start gap-2 rounded-xl border border-red-900/40 bg-red-950/30 px-3 py-2 text-sm text-red-400">
                <AlertCircle size={14} className="mt-0.5 shrink-0" />
                <span>{chatError}</span>
              </div>
            )}

            <div
              className={`mx-auto flex min-h-[58px] w-full max-w-3xl items-end gap-2 rounded-2xl border bg-bg-elevated px-3 py-3.5 transition-colors ${
                disabled ? "border-bg-border opacity-70" : "border-bg-border focus-within:border-blue-500"
              }`}
            >
              <textarea
                ref={textareaRef}
                rows={1}
                value={input}
                onChange={handleInput}
                onKeyDown={handleKeyDown}
                disabled={disabled}
                placeholder={
                  isIndexing
                    ? "Indexing..."
                    : !hasDocuments
                    ? "Upload a document to begin"
                    : "Ask Lumen"
                }
                className="min-h-[30px] max-h-[160px] flex-1 resize-none bg-transparent py-1 text-sm leading-relaxed text-slate-200 placeholder:text-slate-600 focus:outline-none disabled:cursor-not-allowed"
              />
              <button
                type="button"
                onClick={submit}
                disabled={disabled || !input.trim()}
                className="shrink-0 rounded-xl bg-blue-500 p-2.5 text-white transition-colors hover:bg-blue-400 disabled:cursor-not-allowed disabled:opacity-30"
                title="Send"
              >
                <Send size={16} />
              </button>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}

function EmptyState({ hasDocuments, isIndexing }: { hasDocuments: boolean; isIndexing: boolean }) {
  return (
    <div className="flex min-h-[360px] flex-col items-center justify-center gap-4 px-6 text-center">
      {isIndexing ? (
        <>
          <Loader2 size={30} className="text-blue-400 animate-spin" />
          <p className="text-sm text-slate-400">Indexing...</p>
        </>
      ) : !hasDocuments ? (
        <>
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-bg-border bg-bg-elevated">
            <FileUp size={24} className="text-slate-500" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-300">Upload a document</p>
            <p className="mt-1 text-sm text-slate-600">Then ask anything about it.</p>
          </div>
        </>
      ) : (
        <div>
          <p className="text-sm font-medium text-slate-300">Ready</p>
          <p className="mt-1 text-sm text-slate-600">Ask a question below.</p>
        </div>
      )}
    </div>
  );
}
