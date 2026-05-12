"use client";

import { useRef, useState } from "react";
import {
  AlertCircle,
  BookOpen,
  ChevronDown,
  ChevronRight,
  FileText,
  Loader2,
  Trash,
  Trash2,
  Upload,
} from "lucide-react";
import { FileDropZone } from "./FileDropZone";
import type { AnswerMode, DocumentInfo } from "@/types";

interface Props {
  sidebarMode: "open" | "rail" | "hidden";
  documents: DocumentInfo[];
  answerMode: AnswerMode;
  isIndexing: boolean;
  indexError: string | null;
  isAnswering: boolean;
  onUpload: (files: File[]) => void;
  onRemoveDocument: (id: string) => void;
  onRemoveAll: () => void;
  onAnswerModeChange: (mode: AnswerMode) => void;
  onSummary: () => void;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function Sidebar({
  sidebarMode,
  documents,
  answerMode,
  isIndexing,
  indexError,
  isAnswering,
  onUpload,
  onRemoveDocument,
  onRemoveAll,
  onAnswerModeChange,
  onSummary,
}: Props) {
  const [documentsCollapsed, setDocumentsCollapsed] = useState(false);
  const [toolsCollapsed, setToolsCollapsed] = useState(false);
  const railInputRef = useRef<HTMLInputElement>(null);

  if (sidebarMode === "hidden") return null;

  if (sidebarMode === "rail") {
    return (
      <aside className="flex h-full w-14 shrink-0 flex-col items-center gap-3 border-r border-bg-border bg-bg-surface py-3">
        <input
          ref={railInputRef}
          type="file"
          accept=".pdf,.docx,.txt,.md"
          multiple
          className="hidden"
          onChange={(event) => {
            const files = Array.from(event.target.files ?? []);
            if (files.length > 0) onUpload(files);
            event.target.value = "";
          }}
        />
        <button
          type="button"
          onClick={() => railInputRef.current?.click()}
          disabled={isIndexing}
          className="relative flex h-10 w-10 items-center justify-center rounded-xl border border-transparent text-slate-400 transition-colors hover:border-bg-border hover:bg-bg-elevated hover:text-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
          title="Upload documents"
        >
          {isIndexing ? <Loader2 size={18} className="animate-spin" /> : <Upload size={18} />}
          {documents.length > 0 && (
            <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-blue-500" />
          )}
        </button>
        <button
          type="button"
          onClick={onSummary}
          disabled={documents.length === 0 || isAnswering || isIndexing}
          className="flex h-10 w-10 items-center justify-center rounded-xl border border-transparent text-slate-400 transition-colors hover:border-bg-border hover:bg-bg-elevated hover:text-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
          title="Summarize"
        >
          {isAnswering ? <Loader2 size={18} className="animate-spin" /> : <BookOpen size={18} />}
        </button>
      </aside>
    );
  }

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col overflow-y-auto border-r border-bg-border bg-bg-surface">
      <div className="px-4 pb-2 pt-4">
        <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Workspace</p>
      </div>
      <div className="border-b border-bg-border">
        <button
          type="button"
          onClick={() => setDocumentsCollapsed((value) => !value)}
          className="flex w-full items-center justify-between px-4 py-3 text-[11px] font-medium text-slate-500 uppercase tracking-wider hover:text-slate-300 transition-colors"
        >
          <span>Documents</span>
          {documentsCollapsed ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
        </button>
        {!documentsCollapsed && (
          <div className="px-4 pb-4">
            <FileDropZone onFiles={onUpload} isLoading={isIndexing} />
            {indexError && (
              <div className="mt-2 flex items-start gap-1.5 text-xs text-red-400 bg-red-950/30 border border-red-900/40 rounded px-2.5 py-2">
                <AlertCircle size={13} className="mt-0.5 shrink-0" />
                <span>{indexError}</span>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="flex-1 p-4">
        {documents.length === 0 ? (
          <p className="text-xs text-slate-600 text-center mt-4">No documents loaded.</p>
        ) : (
          <ul className="space-y-1">
            {documents.map((doc) => (
              <li
                key={doc.id}
                className="group flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-bg-elevated transition-colors"
              >
                <FileText size={14} className="text-slate-400 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-[13px] text-slate-300 truncate" title={doc.name}>
                    {doc.name}
                  </p>
                  <p className="text-[10px] text-slate-600">{formatBytes(doc.size_bytes)}</p>
                </div>
                <button
                  type="button"
                  onClick={() => onRemoveDocument(doc.id)}
                  className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-900/30 hover:text-red-400 text-slate-600 transition-all"
                  title="Remove document"
                >
                  <Trash2 size={12} />
                </button>
              </li>
            ))}
          </ul>
        )}

        {documents.length > 1 && (
          <button
            type="button"
            onClick={onRemoveAll}
            className="mt-3 w-full flex items-center justify-center gap-1.5 text-xs text-slate-600 hover:text-red-400 hover:bg-red-950/20 rounded-md py-1.5 transition-colors"
          >
            <Trash size={12} />
            Remove all
          </button>
        )}
      </div>

      <div className="border-t border-bg-border">
        <button
          type="button"
          onClick={() => setToolsCollapsed((value) => !value)}
          className="flex w-full items-center justify-between px-4 py-3 text-[11px] font-medium text-slate-500 uppercase tracking-wider hover:text-slate-300 transition-colors"
        >
          <span>Answer mode</span>
          {toolsCollapsed ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
        </button>
        {!toolsCollapsed && (
          <div className="px-4 pb-4 space-y-2">
            <div className="relative">
              <select
                value={answerMode}
                onChange={(e) => onAnswerModeChange(e.target.value as AnswerMode)}
                className="w-full appearance-none bg-bg-elevated border border-bg-border text-slate-300 text-xs rounded-md px-3 py-2 pr-7 focus:outline-none focus:border-blue-500 cursor-pointer"
              >
                <option value="standard">Standard Q&amp;A</option>
                <option value="exhaustive">Exhaustive extraction</option>
              </select>
              <ChevronDown
                size={13}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none"
              />
            </div>

            <button
              type="button"
              onClick={onSummary}
              disabled={documents.length === 0 || isAnswering || isIndexing}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-md text-xs font-medium bg-bg-elevated border border-bg-border text-slate-300 hover:border-blue-500 hover:text-blue-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {isAnswering ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <BookOpen size={13} />
              )}
              Summarize documents
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}
