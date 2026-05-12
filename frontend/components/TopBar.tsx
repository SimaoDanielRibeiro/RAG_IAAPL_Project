"use client";

import { Bot, CheckCircle2, PanelLeftClose, XCircle } from "lucide-react";
import type { HealthResponse } from "@/types";

interface Props {
  health: HealthResponse | null;
  sidebarMode: "open" | "rail" | "hidden";
  onToggleSidebar: () => void;
}

export function TopBar({ health, sidebarMode, onToggleSidebar }: Props) {
  const online = health?.status === "ok";
  const toggleTitle =
    sidebarMode === "open"
      ? "Collapse sidebar"
      : sidebarMode === "rail"
      ? "Hide sidebar"
      : "Show sidebar";

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-bg-border bg-bg-surface px-4">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="rounded-xl border border-bg-border bg-bg-elevated p-2 text-slate-400 transition-colors hover:border-blue-500 hover:text-slate-200"
          title={toggleTitle}
        >
          <PanelLeftClose size={16} />
        </button>
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-xl border border-bg-border bg-bg-elevated">
            <Bot size={16} className="text-blue-400" />
          </span>
          <span className="text-sm font-semibold tracking-tight text-slate-200">Lumen</span>
        </div>
      </div>

      {health && (
        <div className="hidden items-center gap-4 text-xs text-slate-500 sm:flex">
          <span>
            <span className="text-slate-400">chat</span>{" "}
            <code className="text-blue-400">{health.chat_model}</code>
          </span>
          <span className="text-slate-700">·</span>
          <span>
            <span className="text-slate-400">embed</span>{" "}
            <code className="text-blue-400">{health.embedding_model}</code>
          </span>
        </div>
      )}

      <div className="flex items-center gap-1.5 text-xs">
        {online ? (
          <CheckCircle2 size={13} className="text-emerald-400" />
        ) : (
          <XCircle size={13} className="text-red-400" />
        )}
        <span className={online ? "text-emerald-400" : "text-red-400"}>
          {online ? "online" : "offline"}
        </span>
      </div>
    </header>
  );
}
