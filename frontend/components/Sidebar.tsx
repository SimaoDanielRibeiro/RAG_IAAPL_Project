"use client";

import { useState } from "react";
import type { ChangeEvent, ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  FileText,
  Plus,
  Settings,
  Upload,
  X,
} from "lucide-react";
import type { AnswerMode, DocumentInfo } from "@/types";
import { Logo } from "@/components/Logo";

type SidebarProps = {
  documents: DocumentInfo[];
  selectedDocumentId: string | null;
  isIndexing: boolean;
  uploadError: string | null;
  statusMessage: string | null;
  answerMode: AnswerMode;
  onAnswerModeChange: (mode: AnswerMode) => void;
  onUpload: (files: File[]) => void;
  onSelectDocument: (id: string) => void;
  onNewChat: () => void;
  onRemoveDocument: (id: string) => void;
};

export function Sidebar({
  documents,
  selectedDocumentId,
  isIndexing,
  uploadError,
  statusMessage,
  answerMode,
  onAnswerModeChange,
  onUpload,
  onSelectDocument,
  onNewChat,
  onRemoveDocument,
}: SidebarProps) {
  const [collapsed,    setCollapsed]    = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [helpOpen,     setHelpOpen]     = useState(false);
  const [errorVisible, setErrorVisible] = useState(true);

  // Reset dismissal whenever error/status actually changes
  const notice = uploadError ?? statusMessage ?? null;

  const handleFiles = (event: ChangeEvent<HTMLInputElement>) => {
    onUpload(Array.from(event.target.files ?? []));
    event.target.value = "";
    setErrorVisible(true); // re-show for next message
  };

  return (
    <motion.aside
      animate={{ width: collapsed ? 64 : 260 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className="flex h-full shrink-0 flex-col bg-sidebar overflow-hidden"
    >
      <AnimatePresence mode="wait" initial={false}>
        {collapsed ? (
          /* ── COLLAPSED ICON STRIP ─────────────────────── */
          <motion.div
            key="collapsed"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.12 }}
            className="flex h-full w-16 flex-col items-center py-7"
          >
            <div className="mb-5">
              <Logo />
            </div>

            <IconBtn title="Expand sidebar" onClick={() => setCollapsed(false)}>
              <ChevronRight size={16} strokeWidth={1.7} />
            </IconBtn>

            <IconBtn title="New Chat" onClick={onNewChat} className="mt-1">
              <Plus size={18} strokeWidth={1.8} />
            </IconBtn>

            {/* One icon per document */}
            <div className="mt-4 flex min-h-0 flex-1 flex-col items-center gap-1.5 overflow-y-auto w-full px-3">
              {documents.map((doc) => (
                <button
                  key={doc.id}
                  type="button"
                  title={doc.name}
                  onClick={() => onSelectDocument(doc.id)}
                  className={`flex w-full items-center justify-center rounded-md p-2 transition-colors hover:bg-hover ${
                    doc.id === selectedDocumentId ? "text-accent" : "text-secondary"
                  }`}
                >
                  <FileText size={18} strokeWidth={1.55} />
                </button>
              ))}
            </div>

            {/* Expand sidebar when clicking Settings or Help while collapsed */}
            <div className="mt-auto flex flex-col items-center gap-1 w-full px-3">
              <IconBtn title="Settings" onClick={() => setCollapsed(false)}>
                <Settings size={17} strokeWidth={1.7} />
              </IconBtn>
              <IconBtn title="Help" onClick={() => setCollapsed(false)}>
                <CircleHelp size={17} strokeWidth={1.7} />
              </IconBtn>
            </div>
          </motion.div>

        ) : (
          /* ── EXPANDED FULL SIDEBAR ────────────────────── */
          <motion.div
            key="expanded"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.12 }}
            className="flex h-full w-[260px] flex-col px-5 py-7"
          >
            {/* Header */}
            <div className="mb-8 flex items-center justify-between">
              <Logo showWordmark />
              <button
                type="button"
                aria-label="Collapse sidebar"
                onClick={() => setCollapsed(true)}
                className="rounded-md p-1 text-secondary transition-colors hover:bg-hover hover:text-primary"
              >
                <ChevronLeft size={18} strokeWidth={1.7} />
              </button>
            </div>

            {/* New Chat + Upload */}
            <div className="space-y-2">
              <button
                type="button"
                onClick={onNewChat}
                className="flex h-[42px] w-full items-center justify-center gap-2 rounded-md border border-line bg-elevated/50 text-[13px] font-medium text-primary transition-colors hover:bg-hover"
              >
                <Plus size={15} strokeWidth={1.8} />
                New Chat
              </button>

              <label
                className={`flex h-[42px] w-full items-center justify-center gap-2 rounded-md bg-primary text-[13px] font-medium text-app transition-opacity ${
                  isIndexing
                    ? "cursor-not-allowed opacity-60"
                    : "cursor-pointer hover:opacity-90"
                }`}
              >
                <Upload size={15} strokeWidth={1.8} />
                {isIndexing ? "Indexing..." : "Upload files"}
                <input
                  type="file"
                  multiple
                  accept=".pdf,.docx,.txt,.md"
                  className="hidden"
                  onChange={handleFiles}
                  disabled={isIndexing}
                />
              </label>
            </div>

            {/* Documents label */}
            <div className="mb-4 mt-9">
              <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted">
                Documents
              </p>
            </div>

            {/* Document list */}
            <nav className="min-h-0 flex-1 space-y-1.5 overflow-y-auto">
              {documents.length ? (
                documents.map((doc) => (
                  <DocumentRow
                    key={doc.id}
                    document={doc}
                    selected={doc.id === selectedDocumentId}
                    onSelect={() => onSelectDocument(doc.id)}
                    onRemove={() => onRemoveDocument(doc.id)}
                  />
                ))
              ) : (
                <div className="rounded-md border border-line bg-elevated/40 px-3 py-4 text-[13px] leading-5 text-secondary">
                  Upload PDF, DOCX, TXT, or Markdown files to begin.
                </div>
              )}
            </nav>

            {/* Bottom area */}
            <div className="mt-5 space-y-1">

              {/* Dismissible error / status notice */}
              <AnimatePresence initial={false}>
                {notice && errorVisible && (
                  <motion.div
                    key="notice"
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.15 }}
                    className="overflow-hidden mb-2"
                  >
                    <div
                      className={`flex items-start gap-2 rounded-md px-3 py-2.5 text-[12px] leading-5 ${
                        uploadError
                          ? "border border-[rgba(252,165,165,0.2)] bg-[rgba(252,165,165,0.06)] text-[#fca5a5]"
                          : "border border-line bg-elevated/40 text-secondary"
                      }`}
                    >
                      <span className="flex-1">{notice}</span>
                      <button
                        type="button"
                        aria-label="Dismiss"
                        onClick={() => setErrorVisible(false)}
                        className="mt-px shrink-0 text-current opacity-60 transition-opacity hover:opacity-100"
                      >
                        <X size={13} strokeWidth={1.8} />
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Settings panel */}
              <AnimatePresence initial={false}>
                {settingsOpen && (
                  <motion.div
                    key="settings-panel"
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.18, ease: "easeOut" }}
                    className="overflow-hidden"
                  >
                    <div className="mb-2 rounded-md bg-elevated/45 p-1">
                      <button
                        type="button"
                        onClick={() => onAnswerModeChange("standard")}
                        className={`h-8 w-1/2 rounded text-[12px] font-medium transition-colors ${
                          answerMode === "standard"
                            ? "bg-hover text-primary"
                            : "text-secondary hover:text-primary"
                        }`}
                      >
                        Standard
                      </button>
                      <button
                        type="button"
                        onClick={() => onAnswerModeChange("exhaustive")}
                        className={`h-8 w-1/2 rounded text-[12px] font-medium transition-colors ${
                          answerMode === "exhaustive"
                            ? "bg-hover text-primary"
                            : "text-secondary hover:text-primary"
                        }`}
                      >
                        Exhaustive
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Help panel */}
              <AnimatePresence initial={false}>
                {helpOpen && (
                  <motion.div
                    key="help-panel"
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.18, ease: "easeOut" }}
                    className="overflow-hidden"
                  >
                    <div className="mb-2 rounded-md border border-line bg-elevated/40 px-3 py-3 text-[12px] leading-[1.6] text-secondary">
                      <p className="mb-1 font-medium text-primary">About Lumen</p>
                      <p>
                        Upload documents and ask questions. Lumen retrieves the most
                        relevant excerpts and synthesises a sourced answer from your
                        indexed files.
                      </p>
                      <p className="mt-2 text-muted">
                        Supports PDF, DOCX, TXT, and Markdown.
                      </p>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Settings button — icon turns gold when panel is open */}
              <SidebarAction
                icon={<Settings size={17} strokeWidth={1.7} />}
                label="Settings"
                active={settingsOpen}
                onClick={() => { setSettingsOpen((v) => !v); setHelpOpen(false); }}
              />
              <SidebarAction
                icon={<CircleHelp size={17} strokeWidth={1.7} />}
                label="Help"
                active={helpOpen}
                onClick={() => { setHelpOpen((v) => !v); setSettingsOpen(false); }}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.aside>
  );
}

/* ── DocumentRow ────────────────────────────────────── */

function DocumentRow({
  document,
  selected,
  onSelect,
  onRemove,
}: {
  document: DocumentInfo;
  selected: boolean;
  onSelect: () => void;
  onRemove: () => void;
}) {
  return (
    <div
      className={`group relative flex min-h-[64px] w-full items-center gap-3 rounded-md px-3 transition-colors hover:bg-hover ${
        selected ? "bg-elevated" : "bg-transparent"
      }`}
    >
      <button
        type="button"
        onClick={onSelect}
        className="flex min-w-0 flex-1 items-center gap-3 text-left"
      >
        <FileText
          size={21}
          strokeWidth={1.55}
          className={`shrink-0 ${selected ? "text-accent" : "text-primary"}`}
        />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[13px] font-medium text-primary">
            {document.name}
          </span>
          <span className="mt-1 flex items-center gap-1.5 text-[12px] text-secondary">
            <span>{formatBytes(document.size_bytes)}</span>
            <span className="text-muted">·</span>
            <span>Indexed</span>
          </span>
        </span>
      </button>

      {/* Selected dot → delete × on hover */}
      <div className="relative flex h-5 w-5 shrink-0 items-center justify-center">
        {selected && (
          <span className="absolute h-1.5 w-1.5 rounded-full bg-accent transition-opacity group-hover:opacity-0" />
        )}
        <button
          type="button"
          aria-label={`Remove ${document.name}`}
          onClick={(e) => { e.stopPropagation(); onRemove(); }}
          className="absolute rounded p-0.5 text-muted opacity-0 transition-all hover:text-primary group-hover:opacity-100"
        >
          <X size={13} strokeWidth={1.8} />
        </button>
      </div>
    </div>
  );
}

/* ── SidebarAction ──────────────────────────────────── */

function SidebarAction({
  icon,
  label,
  active = false,
  onClick,
}: {
  icon: ReactNode;
  label: string;
  active?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex h-10 w-full items-center gap-3 rounded-md px-2 text-[13px] font-medium text-primary transition-colors hover:bg-hover ${
        active ? "bg-hover" : ""
      }`}
    >
      {/* Icon turns gold while its panel is open */}
      <span className={`transition-colors ${active ? "text-accent" : "text-secondary"}`}>
        {icon}
      </span>
      {label}
    </button>
  );
}

/* ── IconBtn ────────────────────────────────────────── */

function IconBtn({
  children,
  title,
  onClick,
  className = "",
}: {
  children: ReactNode;
  title?: string;
  onClick?: () => void;
  className?: string;
}) {
  return (
    <button
      type="button"
      title={title}
      onClick={onClick}
      className={`rounded-md p-2 text-secondary transition-colors hover:bg-hover hover:text-primary ${className}`}
    >
      {children}
    </button>
  );
}

/* ── Helpers ────────────────────────────────────────── */

function formatBytes(bytes: number) {
  if (bytes < 1024)            return `${bytes} B`;
  if (bytes < 1024 * 1024)    return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
