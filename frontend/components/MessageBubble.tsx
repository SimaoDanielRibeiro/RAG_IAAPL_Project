"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Search } from "lucide-react";
import type { ChatMessage, ChatResponse } from "@/types";

interface Props {
  message: ChatMessage;
  onShowEvidence?: (evidence: ChatResponse) => void;
}

const confidenceColors: Record<string, string> = {
  High: "bg-emerald-900/40 text-emerald-400 border-emerald-800",
  Medium: "bg-amber-900/40 text-amber-400 border-amber-800",
  Low: "bg-red-900/40 text-red-400 border-red-800",
};

export function MessageBubble({ message, onShowEvidence }: Props) {
  const isUser = message.role === "user";
  const ev = message.evidence;

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[70%] rounded-2xl rounded-tr-md bg-blue-500 px-4 py-3 text-sm text-white shadow-lg">
          <p className="leading-relaxed">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full border-l border-bg-border pl-4">
      <div className="prose-dark text-base leading-[1.8] text-slate-200">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
      </div>

      {ev && (
        <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-bg-border pt-3">
          <span
            className={`rounded-full border px-2.5 py-1 text-xs font-medium ${
              confidenceColors[ev.confidence] ?? confidenceColors.Low
            }`}
          >
            {ev.confidence}
          </span>

          <span className="text-xs text-slate-600">
            {ev.answer_mode === "exhaustive" ? "exhaustive" : "standard"}
          </span>

          <span className="text-xs text-slate-600">
            {ev.chunks_used} chunk{ev.chunks_used !== 1 ? "s" : ""}
          </span>

          {ev.sources.length > 0 && (
            <span className="max-w-[220px] truncate text-xs text-slate-500">
              {ev.sources.join(", ")}
            </span>
          )}

          {onShowEvidence && (
            <button
              type="button"
              onClick={() => onShowEvidence(ev)}
              className="ml-auto flex items-center gap-1 rounded-full border border-bg-border bg-bg-elevated px-3 py-1.5 text-xs text-slate-300 transition-colors hover:border-blue-500 hover:text-blue-400"
            >
              <Search size={11} />
              Evidence
            </button>
          )}
        </div>
      )}
    </div>
  );
}
