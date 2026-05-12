"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import { api } from "@/lib/api";
import type {
  AnswerMode,
  ChatMessage,
  ChatResponse,
  DocumentInfo,
  HealthResponse,
} from "@/types";
import { TopBar } from "@/components/TopBar";
import { Sidebar } from "@/components/Sidebar";
import { ChatArea } from "@/components/ChatArea";
import { EvidencePanel } from "@/components/EvidencePanel";

type SidebarMode = "open" | "rail" | "hidden";

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [answerMode, setAnswerMode] = useState<AnswerMode>("standard");
  const [isIndexing, setIsIndexing] = useState(false);
  const [isAnswering, setIsAnswering] = useState(false);
  const [indexError, setIndexError] = useState<string | null>(null);
  const [chatError, setChatError] = useState<string | null>(null);
  const [activeEvidence, setActiveEvidence] = useState<ChatResponse | null>(null);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [sidebarMode, setSidebarMode] = useState<SidebarMode>("open");
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);

  const chatHistoryRef = useRef<Array<{ role: string; content: string }>>([]);

  useEffect(() => {
    api.health().then(setHealth).catch(() => {});
    api.listDocuments().then(setDocuments).catch(() => {});
  }, []);

  const handleUpload = useCallback(async (files: File[]) => {
    setIndexError(null);
    setIsIndexing(true);
    try {
      const { documents: updated } = await api.uploadDocuments(files);
      setDocuments(updated);
    } catch (err: unknown) {
      setIndexError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setIsIndexing(false);
    }
  }, []);

  const handleSelectDocument = useCallback((id: string) => {
    setSelectedDocumentId((prev) => (prev === id ? null : id));
  }, []);

  const handleRemoveDocument = useCallback(async (id: string) => {
    try {
      await api.removeDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      if (selectedDocumentId === id) setSelectedDocumentId(null);
      if (documents.length <= 1) {
        chatHistoryRef.current = [];
        setMessages([]);
        setActiveEvidence(null);
      }
    } catch (err: unknown) {
      setIndexError(err instanceof Error ? err.message : "Remove failed.");
    }
  }, [documents.length, selectedDocumentId]);

  const handleRemoveAll = useCallback(async () => {
    try {
      await api.removeAllDocuments();
      setDocuments([]);
      setSelectedDocumentId(null);
      chatHistoryRef.current = [];
      setMessages([]);
      setActiveEvidence(null);
      setEvidenceOpen(false);
    } catch (err: unknown) {
      setIndexError(err instanceof Error ? err.message : "Remove failed.");
    }
  }, []);

  const handleSend = useCallback(async (question: string) => {
    if (!question.trim() || isAnswering) return;
    setChatError(null);

    const userMsg: ChatMessage = {
      id: uuidv4(),
      role: "user",
      content: question,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    chatHistoryRef.current.push({ role: "user", content: question });

    setIsAnswering(true);
    const scope = selectedDocumentId ? "selected" : "all";
    try {
      const response = await api.chat(question, answerMode, chatHistoryRef.current.slice(-8), scope, selectedDocumentId);
      const assistantMsg: ChatMessage = {
        id: uuidv4(),
        role: "assistant",
        content: response.answer,
        evidence: response,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      chatHistoryRef.current.push({ role: "assistant", content: response.answer });
      setActiveEvidence(response);
      setEvidenceOpen(true);
    } catch (err: unknown) {
      setChatError(err instanceof Error ? err.message : "Chat request failed.");
      chatHistoryRef.current.pop();
      setMessages((prev) => prev.filter((m) => m.id !== userMsg.id));
    } finally {
      setIsAnswering(false);
    }
  }, [isAnswering, answerMode, selectedDocumentId]);

  const handleSummary = useCallback(async () => {
    if (isAnswering) return;
    setChatError(null);
    setIsAnswering(true);
    try {
      const result = await api.summary();
      const parts = result.summaries.map((s) => {
        const pageNote = s.pages.length ? ` · pages ${s.pages.join(", ")}` : "";
        return `### ${s.file_name}${pageNote}\n\n${s.summary}`;
      });
      const summaryMsg: ChatMessage = {
        id: uuidv4(),
        role: "assistant",
        content: parts.join("\n\n---\n\n") || "No summary available.",
        isSummary: true,
        summaryData: result,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, summaryMsg]);
    } catch (err: unknown) {
      setChatError(err instanceof Error ? err.message : "Summary failed.");
    } finally {
      setIsAnswering(false);
    }
  }, [isAnswering]);

  const handleShowEvidence = useCallback((evidence: ChatResponse) => {
    setActiveEvidence(evidence);
    setEvidenceOpen(true);
  }, []);

  const handleToggleSidebar = useCallback(() => {
    setSidebarMode((mode) => {
      if (mode === "open") return "rail";
      if (mode === "rail") return "hidden";
      return "open";
    });
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-bg-base">
      <Sidebar
        sidebarMode={sidebarMode}
        documents={documents}
        answerMode={answerMode}
        isIndexing={isIndexing}
        indexError={indexError}
        onUpload={handleUpload}
        onRemoveDocument={handleRemoveDocument}
        onRemoveAll={handleRemoveAll}
        onAnswerModeChange={setAnswerMode}
        onSummary={handleSummary}
        isAnswering={isAnswering}
        selectedDocumentId={selectedDocumentId}
        onSelectDocument={handleSelectDocument}
      />

      <div className="flex flex-col flex-1 min-w-0">
        <TopBar
          health={health}
          sidebarMode={sidebarMode}
          onToggleSidebar={handleToggleSidebar}
        />
        <ChatArea
          messages={messages}
          isAnswering={isAnswering}
          chatError={chatError}
          hasDocuments={documents.length > 0}
          isIndexing={isIndexing}
          onSend={handleSend}
          onShowEvidence={handleShowEvidence}
          selectedDocumentName={
            selectedDocumentId
              ? (documents.find((d) => d.id === selectedDocumentId)?.name ?? null)
              : null
          }
          onClearSelection={() => setSelectedDocumentId(null)}
        />
      </div>

      <EvidencePanel
        open={evidenceOpen}
        evidence={activeEvidence}
        onClose={() => setEvidenceOpen(false)}
      />
    </div>
  );
}
