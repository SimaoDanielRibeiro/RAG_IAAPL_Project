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

  chat(
    question: string,
    answerMode: AnswerMode,
    chatHistory: Array<{ role: string; content: string }>,
    scope: "all" | "selected" = "all",
    documentId: string | null = null
  ): Promise<ChatResponse> {
    return request("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        answer_mode: answerMode,
        chat_history: chatHistory,
        scope,
        document_id: documentId,
      }),
    });
  },

  summary(): Promise<SummaryResponse> {
    return request("/api/summary", { method: "POST" });
  },
};
