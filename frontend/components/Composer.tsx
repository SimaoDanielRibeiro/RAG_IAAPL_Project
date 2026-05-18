"use client";

import { useCallback, useRef, useState } from "react";
import { ArrowUp, Paperclip } from "lucide-react";

type ComposerProps = {
  disabled: boolean;
  busy: boolean;
  onSend: (question: string) => void;
  onUpload: (files: File[]) => void;
};

// Single source of truth — paperclip, textarea (1 row), and send button
// are all this tall. items-center keeps them aligned on single-line input.
const CONTROL_HEIGHT = 36;
const MAX_HEIGHT     = 200;

export function Composer({ disabled, busy, onSend, onUpload }: ComposerProps) {
  const [value, setValue]   = useState("");
  const textareaRef         = useRef<HTMLTextAreaElement>(null);

  /* Grow the textarea to fit content, capped at MAX_HEIGHT */
  const autoResize = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`;
  }, []);

  const send = () => {
    if (!value.trim() || disabled || busy) return;
    onSend(value.trim());
    setValue("");
    // Reset to single row after submit
    requestAnimationFrame(() => {
      if (textareaRef.current) {
        textareaRef.current.style.height = `${CONTROL_HEIGHT}px`;
      }
    });
  };

  return (
    <form
      onSubmit={(e) => { e.preventDefault(); send(); }}
      className="w-full"
    >
      <div className="rounded-[14px] border border-line bg-elevated transition-colors focus-within:border-[rgba(224,177,91,0.34)]">
        <div className="flex items-center gap-2 px-3 py-3">

          {/* Attach — same height as send button */}
          <label
            className="grid shrink-0 cursor-pointer place-items-center rounded-md text-secondary transition-colors hover:bg-hover hover:text-primary"
            style={{ width: CONTROL_HEIGHT, height: CONTROL_HEIGHT }}
          >
            <Paperclip size={18} strokeWidth={1.8} />
            <span className="sr-only">Attach document</span>
            <input
              type="file"
              multiple
              accept=".pdf,.docx,.txt,.md"
              className="hidden"
              onChange={(e) => {
                onUpload(Array.from(e.target.files ?? []));
                e.target.value = "";
              }}
            />
          </label>

          {/* Auto-growing textarea — placeholder + caret sit vertically centred
              when single-line (24 px line-height + 6 px top/bottom padding = 36 px) */}
          <textarea
            ref={textareaRef}
            aria-label="Ask a question"
            rows={1}
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              autoResize();
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            disabled={disabled || busy}
            className="flex-1 resize-none bg-transparent px-1 text-[15px] leading-6 text-primary outline-none placeholder:text-secondary disabled:cursor-not-allowed disabled:opacity-60"
            style={{
              height:    CONTROL_HEIGHT,
              minHeight: CONTROL_HEIGHT,
              maxHeight: MAX_HEIGHT,
              paddingTop:    6,
              paddingBottom: 6,
              overflowY: "auto",
            }}
            placeholder={
              disabled
                ? "Upload a document to ask questions..."
                : "Ask a question about your documents..."
            }
          />

          {/* Send */}
          <button
            type="submit"
            aria-label="Send message"
            disabled={!value.trim() || disabled || busy}
            className="grid shrink-0 place-items-center rounded-full bg-accent text-app transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-45"
            style={{ width: CONTROL_HEIGHT, height: CONTROL_HEIGHT }}
          >
            <ArrowUp size={17} strokeWidth={2} />
          </button>
        </div>
      </div>

      <p className="mt-4 text-center text-[12px] text-muted">
        Lumen can make mistakes. Please verify important information.
      </p>
    </form>
  );
}
