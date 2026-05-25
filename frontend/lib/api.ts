import type {
  ChatResponse,
  DocumentInfo,
  HealthResponse,
  SummaryResponse,
  AnswerMode,
} from "@/types";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    let detail = `Request failed: ${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {}
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  health(): Promise<HealthResponse> {
    return request("/api/health");
  },

  listDocuments(): Promise<DocumentInfo[]> {
    return request("/api/documents");
  },

  uploadDocuments(files: File[]): Promise<{ documents: DocumentInfo[]; message: string }> {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    return request("/api/documents/upload", { method: "POST", body: form });
  },

  removeDocument(id: string): Promise<void> {
    return request(`/api/documents/${id}`, { method: "DELETE" });
  },

  removeAllDocuments(): Promise<void> {
    return request("/api/documents", { method: "DELETE" });
  },

  documentFileUrl(documentId: string, page?: number | null): string {
    // Page anchor `#page=N` is honored by built-in PDF viewers in Chrome,
    // Edge, and Firefox. For non-PDF documents the anchor is ignored.
    const base = `${BASE}/api/documents/${encodeURIComponent(documentId)}/file`;
    return page !== undefined && page !== null
      ? `${base}#page=${page}`
      : base;
  },

  chat(
    question: string,
    answerMode: AnswerMode,
    chatHistory: Array<{ role: string; content: string }>,
    documentIds: string[] = [],
  ): Promise<ChatResponse> {
    return request("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        answer_mode: answerMode,
        chat_history: chatHistory,
        document_ids: documentIds,
      }),
    });
  },

  async chatStream(
    question: string,
    answerMode: AnswerMode,
    chatHistory: Array<{ role: string; content: string }>,
    documentIds: string[],
    callbacks: ChatStreamCallbacks,
    signal?: AbortSignal,
  ): Promise<void> {
    const res = await fetch(`${BASE}/api/chat/stream`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({
        question,
        answer_mode:   answerMode,
        chat_history:  chatHistory,
        document_ids:  documentIds,
      }),
      signal,
    });
    if (!res.ok || !res.body) {
      let detail = `Stream failed: ${res.status} ${res.statusText}`;
      try {
        const body = await res.json();
        if (body?.detail) detail = body.detail;
      } catch {}
      throw new Error(detail);
    }

    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer    = "";

    const dispatch = (line: string) => {
      const trimmed = line.trim();
      if (!trimmed) return;
      let event: StreamEvent;
      try {
        event = JSON.parse(trimmed);
      } catch {
        return; // skip malformed lines
      }
      switch (event.type) {
        case "metadata": callbacks.onMetadata?.(event.data); break;
        case "token":    callbacks.onToken?.(event.text);    break;
        case "done":     callbacks.onDone?.();               break;
        case "error":    throw new Error(event.message);
      }
    };

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let nlIndex: number;
      while ((nlIndex = buffer.indexOf("\n")) >= 0) {
        const line = buffer.slice(0, nlIndex);
        buffer     = buffer.slice(nlIndex + 1);
        dispatch(line);
      }
    }
    if (buffer.length > 0) dispatch(buffer);
  },

  summary(documentIds: string[] = []): Promise<SummaryResponse> {
    return request("/api/summary", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document_ids: documentIds }),
    });
  },
};

/* ── Streaming types ──────────────────────────────────── */

export type StreamMetadata = Omit<ChatResponse, "answer">;

type StreamEvent =
  | { type: "metadata"; data: StreamMetadata }
  | { type: "token";    text: string }
  | { type: "done" }
  | { type: "error";    message: string };

export type ChatStreamCallbacks = {
  onMetadata?: (meta: StreamMetadata) => void;
  onToken?:    (token: string)        => void;
  onDone?:     ()                     => void;
};
