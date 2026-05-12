"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { PanelRightOpen } from "lucide-react";
import { v4 as uuidv4 } from "uuid";
import { ChatPane } from "@/components/ChatPane";
import { EvidencePanel } from "@/components/EvidencePanel";
import { Sidebar } from "@/components/Sidebar";
import { api } from "@/lib/api";
import type {
  AnswerMode,
  ChatMessage,
  ChatResponse,
  DocumentInfo,
} from "@/types";

export default function App() {
  const [documents,          setDocuments]          = useState<DocumentInfo[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [chatScope,          setChatScope]          = useState<"all" | "selected">("all");
  const [messages,           setMessages]           = useState<ChatMessage[]>([]);
  const [activeEvidence,     setActiveEvidence]     = useState<ChatResponse | null>(null);
  const [evidenceOpen,       setEvidenceOpen]       = useState(true);
  const [answerMode,         setAnswerMode]         = useState<AnswerMode>("standard");
  const [isIndexing,         setIsIndexing]         = useState(false);
  const [isAnswering,        setIsAnswering]        = useState(false);
  const [uploadError,        setUploadError]        = useState<string | null>(null);
  const [chatError,          setChatError]          = useState<string | null>(null);
  const [statusMessage,      setStatusMessage]      = useState<string | null>(null);

  const chatHistoryRef = useRef<Array<{ role: string; content: string }>>([]);

  /* When every document is removed, reset the conversation */
  useEffect(() => {
    if (documents.length === 0) {
      setMessages([]);
      chatHistoryRef.current = [];
      setActiveEvidence(null);
    }
  }, [documents.length]);

  const selectedDocument = useMemo(
    () =>
      documents.find((d) => d.id === selectedDocumentId) ??
      documents[0] ??
      null,
    [documents, selectedDocumentId],
  );

  /* ── Initial load ───────────────────────────────── */
  const refreshDocuments = useCallback(async () => {
    const current = await api.listDocuments();
    setDocuments(current);
    setSelectedDocumentId((sel) =>
      current.some((d) => d.id === sel) ? sel : (current[0]?.id ?? null),
    );
  }, []);

  useEffect(() => {
    refreshDocuments().catch(() => {
      setUploadError("Could not reach the backend at http://localhost:8000.");
    });
  }, [refreshDocuments]);

  /* ── Upload ─────────────────────────────────────── */
  const handleUpload = useCallback(async (files: File[]) => {
    if (!files.length) return;
    setUploadError(null);
    setStatusMessage(null);
    setIsIndexing(true);
    try {
      const result = await api.uploadDocuments(files);
      setDocuments(result.documents);
      setSelectedDocumentId(result.documents[0]?.id ?? null);
      setStatusMessage(result.message);
      // Uploading new files starts a fresh chat session
      setMessages([]);
      chatHistoryRef.current = [];
      setActiveEvidence(null);
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Upload failed.");
    } finally {
      setIsIndexing(false);
    }
  }, []);

  /* ── Select document (focuses scope) ───────────── */
  const handleSelectDocument = useCallback((id: string) => {
    setSelectedDocumentId(id);
    setChatScope("selected");
  }, []);

  /* ── Remove single document ─────────────────────── */
  // Uses functional setState to avoid stale closure on `documents`
  const handleRemoveDocument = useCallback(async (id: string) => {
    setUploadError(null);
    setStatusMessage(null);
    try {
      await api.removeDocument(id);
      // Use functional form — reads latest state, not closure snapshot
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      setSelectedDocumentId((sel) => {
        if (sel === id) { setChatScope("all"); return null; }
        return sel;
      });
    } catch (error) {
      setUploadError(
        error instanceof Error ? error.message : "Could not remove document.",
      );
    }
  }, []); // no deps needed — only uses functional setters

  /* ── New chat ───────────────────────────────────── */
  const handleNewChat = useCallback(() => {
    setMessages([]);
    setChatError(null);
    setActiveEvidence(null);
    chatHistoryRef.current = [];
  }, []);

  /* ── Send question ──────────────────────────────── */
  const handleSend = useCallback(
    async (question: string) => {
      if (!question.trim() || isAnswering || !documents.length) return;

      const userMessage: ChatMessage = {
        id: uuidv4(),
        role: "user",
        content: question.trim(),
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setChatError(null);
      setIsAnswering(true);
      chatHistoryRef.current.push({ role: "user", content: userMessage.content });

      try {
        const response = await api.chat(
          userMessage.content,
          answerMode,
          chatHistoryRef.current.slice(-8),
          chatScope,
          chatScope === "selected" ? selectedDocumentId : null,
        );
        const assistantMessage: ChatMessage = {
          id: uuidv4(),
          role: "assistant",
          content: response.answer,
          evidence: response,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, assistantMessage]);
        chatHistoryRef.current.push({
          role: "assistant",
          content: response.answer,
        });
        setActiveEvidence(response);
        setEvidenceOpen(true);
      } catch (error) {
        chatHistoryRef.current.pop(); // revert optimistic push
        setChatError(
          error instanceof Error ? error.message : "Chat request failed.",
        );
      } finally {
        setIsAnswering(false);
      }
    },
    [answerMode, chatScope, documents.length, isAnswering, selectedDocumentId],
  );

  return (
    <main className="h-screen overflow-hidden bg-app text-primary">
      <div className="flex h-full min-w-[900px]">

        <Sidebar
          documents={documents}
          selectedDocumentId={selectedDocument?.id ?? null}
          isIndexing={isIndexing}
          uploadError={uploadError}
          statusMessage={statusMessage}
          answerMode={answerMode}
          onAnswerModeChange={setAnswerMode}
          onUpload={handleUpload}
          onSelectDocument={handleSelectDocument}
          onNewChat={handleNewChat}
          onRemoveDocument={handleRemoveDocument}
        />

        <ChatPane
          document={selectedDocument}
          documentCount={documents.length}
          messages={messages}
          isAnswering={isAnswering}
          isIndexing={isIndexing}
          chatError={chatError}
          chatScope={chatScope}
          onSend={handleSend}
          onUpload={handleUpload}
          onClearScope={() => setChatScope("all")}
        />

        <AnimatePresence initial={false}>
          {evidenceOpen ? (
            <EvidencePanel
              key="evidence-panel"
              evidence={activeEvidence}
              onClose={() => setEvidenceOpen(false)}
            />
          ) : (
            <motion.button
              key="evidence-tab"
              type="button"
              aria-label="Open evidence panel"
              onClick={() => setEvidenceOpen(true)}
              initial={{ opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 12 }}
              transition={{ duration: 0.18, ease: "easeOut" }}
              className="fixed right-0 top-1/2 z-30 flex h-24 w-7 -translate-y-1/2 items-center justify-center rounded-l-md border border-r-0 border-line bg-sidebar text-accent transition-colors hover:bg-hover"
            >
              <PanelRightOpen size={15} strokeWidth={1.8} />
            </motion.button>
          )}
        </AnimatePresence>

      </div>
    </main>
  );
}
