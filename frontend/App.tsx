"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { PanelRightOpen } from "lucide-react";
import { v4 as uuidv4 } from "uuid";
import { ChatPane } from "@/components/ChatPane";
import { EvidencePanel } from "@/components/EvidencePanel";
import { LandingScreen } from "@/components/LandingScreen";
import { Sidebar } from "@/components/Sidebar";
import { SourcePreviewModal } from "@/components/SourcePreviewModal";
import type { SourcePreviewTarget } from "@/components/SourcePreviewModal";
import { api, API_BASE_URL } from "@/lib/api";
import { stripMarkdown } from "@/lib/text";
import type {
  AnswerMode,
  ChatMessage,
  ChatResponse,
  ChunkInfo,
  DocumentInfo,
  SummaryResponse,
} from "@/types";

type SummarySuggestion = {
  documentIds: string[];
  label: string;
};

export default function App() {
  const [showLanding, setShowLanding] = useState(true);
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [highlightedChunk, setHighlightedChunk] = useState<number | null>(null);
  const [streamingId, setStreamingId] = useState<string | null>(null);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activeEvidence, setActiveEvidence] = useState<ChatResponse | null>(null);
  const [evidenceOpen, setEvidenceOpen] = useState(true);
  const [answerMode, setAnswerMode] = useState<AnswerMode>("standard");
  const [isIndexing, setIsIndexing] = useState(false);
  const [isAnswering, setIsAnswering] = useState(false);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [summarySuggestion, setSummarySuggestion] = useState<SummarySuggestion | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [chatError, setChatError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [previewTarget, setPreviewTarget] = useState<SourcePreviewTarget | null>(null);

  const chatHistoryRef = useRef<Array<{ role: string; content: string }>>([]);

  useEffect(() => {
    if (documents.length === 0) {
      setMessages([]);
      chatHistoryRef.current = [];
      setActiveEvidence(null);
      setSelectedDocumentIds([]);
      setSummarySuggestion(null);
    }
  }, [documents.length]);

  const refreshDocuments = useCallback(async () => {
    const current = await api.listDocuments();
    setDocuments(current);
    setSelectedDocumentIds((prev) =>
      prev.filter((id) => current.some((d) => d.id === id)),
    );
  }, []);

  useEffect(() => {
    refreshDocuments().catch(() => {
      setUploadError(`Could not reach the backend at ${API_BASE_URL}.`);
    });
  }, [refreshDocuments]);

  const handleUpload = useCallback(async (files: File[]) => {
    if (!files.length) return;
    setUploadError(null);
    setStatusMessage(null);
    setIsIndexing(true);
    try {
      const result = await api.uploadDocuments(files);
      setDocuments(result.documents);
      setSelectedDocumentIds([]);
      setStatusMessage(result.message);
      setMessages([]);
      chatHistoryRef.current = [];
      setActiveEvidence(null);
      setSummarySuggestion(createSummarySuggestion(result.documents));
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Upload failed.");
    } finally {
      setIsIndexing(false);
    }
  }, []);

  const handleToggleDocument = useCallback((id: string) => {
    setSelectedDocumentIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }, []);

  const handleRemoveDocument = useCallback(async (id: string) => {
    setUploadError(null);
    setStatusMessage(null);
    try {
      await api.removeDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      setSelectedDocumentIds((prev) => prev.filter((x) => x !== id));
      setSummarySuggestion(null);
    } catch (error) {
      setUploadError(
        error instanceof Error ? error.message : "Could not remove document.",
      );
    }
  }, []);

  const handleNewChat = useCallback(() => {
    setMessages([]);
    setChatError(null);
    setActiveEvidence(null);
    chatHistoryRef.current = [];
    setSummarySuggestion(createSummarySuggestion(documents, selectedDocumentIds));
  }, [documents, selectedDocumentIds]);

  const handleSend = useCallback(
    async (question: string) => {
      if (!question.trim() || isAnswering || isSummarizing || !documents.length) return;

      const userMessage: ChatMessage = {
        id: uuidv4(),
        role: "user",
        content: question.trim(),
        timestamp: new Date(),
      };
      const assistantId = uuidv4();
      const assistantMessage: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setChatError(null);
      setSummarySuggestion(null);
      setIsAnswering(true);
      setStreamingId(assistantId);
      chatHistoryRef.current.push({ role: "user", content: userMessage.content });

      let accumulated = "";
      let evidenceResponse: ChatResponse | null = null;

      try {
        const scopeIds =
          selectedDocumentIds.length === 0 ||
          selectedDocumentIds.length === documents.length
            ? []
            : selectedDocumentIds;

        await api.chatStream(
          userMessage.content,
          answerMode,
          chatHistoryRef.current.slice(-8),
          scopeIds,
          {
            onMetadata: (meta) => {
              // The backend metadata is the full ChatResponse minus `answer`.
              // We cast to ChatResponse with answer filled in later from tokens.
              const initialEvidence = { ...meta, answer: "" } as ChatResponse;
              evidenceResponse = initialEvidence;
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId ? { ...m, evidence: initialEvidence } : m,
                ),
              );
              setActiveEvidence(initialEvidence);
              setEvidenceOpen(true);
            },
            onToken: (token) => {
              accumulated += token;
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId ? { ...m, content: accumulated } : m,
                ),
              );
            },
            onDone: () => {
              // Lock in the final answer on the evidence object too,
              // in case anything downstream reads from it.
              if (evidenceResponse) {
                const finalEvidence = { ...evidenceResponse, answer: accumulated };
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId ? { ...m, evidence: finalEvidence } : m,
                  ),
                );
                setActiveEvidence(finalEvidence);
              }
            },
          },
        );

        chatHistoryRef.current.push({
          role: "assistant",
          content: stripMarkdown(accumulated),
        });
        setSummarySuggestion(createSummarySuggestion(documents, scopeIds));
      } catch (error) {
        chatHistoryRef.current.pop();
        setMessages((prev) => prev.filter((m) => m.id !== assistantId));
        setChatError(
          error instanceof Error ? error.message : "Chat request failed.",
        );
      } finally {
        setIsAnswering(false);
        setStreamingId(null);
      }
    },
    [answerMode, documents, isAnswering, isSummarizing, selectedDocumentIds],
  );

  const handleSummary = useCallback(async () => {
    if (!summarySuggestion || isAnswering || isSummarizing || !documents.length) return;

    const suggestion = summarySuggestion;
    const assistantId = uuidv4();
    const placeholder: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: `Preparing a complete summary for ${suggestion.label}...`,
      isSummary: true,
      timestamp: new Date(),
    };

    setSummarySuggestion(null);
    setChatError(null);
    setIsSummarizing(true);
    setMessages((prev) => [...prev, placeholder]);

    try {
      const result = await api.summary(suggestion.documentIds);
      const content = formatSummaryResponse(result, suggestion.label);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content, summaryData: result }
            : m,
        ),
      );
    } catch (error) {
      setMessages((prev) => prev.filter((m) => m.id !== assistantId));
      setChatError(
        error instanceof Error ? error.message : "Summary request failed.",
      );
    } finally {
      setIsSummarizing(false);
    }
  }, [documents.length, isAnswering, isSummarizing, summarySuggestion]);

  const handleCitationClick = useCallback(
    (chunkIdx: number, evidence: ChatResponse) => {
      setActiveEvidence(evidence);
      setEvidenceOpen(true);
      setHighlightedChunk(chunkIdx);
      setTimeout(() => setHighlightedChunk(null), 2400);
    },
    [],
  );

  const handleOpenSource = useCallback((chunk: ChunkInfo) => {
    if (!chunk.document_id) return;
    setPreviewTarget({
      documentId: chunk.document_id,
      source:     chunk.source,
      page:       chunk.page,
      snippet:    chunk.snippet,
    });
  }, []);

  return (
    <main className="relative h-screen overflow-hidden bg-app text-primary">
      <MeshBackground />

      {showLanding && (
        <LandingScreen onEnter={() => setShowLanding(false)} />
      )}

      <div className="relative z-10 flex h-full min-w-[900px]">
        <Sidebar
          documents={documents}
          selectedDocumentIds={selectedDocumentIds}
          isIndexing={isIndexing}
          uploadError={uploadError}
          statusMessage={statusMessage}
          answerMode={answerMode}
          onAnswerModeChange={setAnswerMode}
          onUpload={handleUpload}
          onToggleDocument={handleToggleDocument}
          onNewChat={handleNewChat}
          onRemoveDocument={handleRemoveDocument}
        />

        <ChatPane
          documents={documents}
          messages={messages}
          isAnswering={isAnswering || isSummarizing}
          isIndexing={isIndexing}
          chatError={chatError}
          selectedDocumentIds={selectedDocumentIds}
          streamingId={streamingId}
          summarySuggestion={summarySuggestion}
          isSummarizing={isSummarizing}
          onSend={handleSend}
          onUpload={handleUpload}
          onClearScope={() => setSelectedDocumentIds([])}
          onSummary={handleSummary}
          onDismissSummary={() => setSummarySuggestion(null)}
          onCitationClick={handleCitationClick}
        />

        <AnimatePresence initial={false}>
          {evidenceOpen ? (
            <EvidencePanel
              key="evidence-panel"
              evidence={activeEvidence}
              highlightedIndex={highlightedChunk}
              onClose={() => setEvidenceOpen(false)}
              onOpenSource={handleOpenSource}
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
              className="fixed right-0 top-1/2 z-30 flex h-24 w-7 -translate-y-1/2 items-center justify-center rounded-l-md border border-r-0 border-line bg-sidebar/70 text-accent backdrop-blur-xl transition-colors hover:bg-hover/80"
            >
              <PanelRightOpen size={15} strokeWidth={1.8} />
            </motion.button>
          )}
        </AnimatePresence>
      </div>

      <SourcePreviewModal
        target={previewTarget}
        onClose={() => setPreviewTarget(null)}
      />
    </main>
  );
}

/* ── Animated mesh-gradient backdrop ──────────────────────
   Three large blurred radial blobs drifting slowly. Sits
   behind the glassmorphic Sidebar / EvidencePanel so the
   backdrop-blur picks up motion and color. */

function createSummarySuggestion(
  documents: DocumentInfo[],
  documentIds: string[] = [],
): SummarySuggestion | null {
  const scopedDocuments = documentIds.length
    ? documents.filter((document) => documentIds.includes(document.id))
    : documents;
  if (!scopedDocuments.length) return null;

  const label =
    scopedDocuments.length === 1
      ? scopedDocuments[0].name
      : `${scopedDocuments.length} documents`;
  return { documentIds, label };
}

function formatSummaryResponse(result: SummaryResponse, fallbackLabel: string): string {
  if (!result.summaries.length) {
    return `No summary could be generated for ${fallbackLabel}.`;
  }

  return result.summaries
    .map((entry) => {
      const pages = entry.pages.length
        ? `\nPages used: ${entry.pages.join(", ")}`
        : "";
      return `Complete summary of ${entry.file_name}\n\n${entry.summary}${pages}`;
    })
    .join("\n\n");
}

function MeshBackground() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
      <motion.div
        animate={{ x: [0, 80, -40, 0], y: [0, 50, -30, 0] }}
        transition={{ duration: 28, repeat: Infinity, ease: "easeInOut" }}
        className="absolute -top-40 left-[10%] h-[720px] w-[720px] rounded-full opacity-70 blur-[120px]"
        style={{
          background:
            "radial-gradient(circle, rgba(224,177,91,0.55), transparent 70%)",
        }}
      />
      <motion.div
        animate={{ x: [0, -60, 40, 0], y: [0, 40, -50, 0] }}
        transition={{ duration: 34, repeat: Infinity, ease: "easeInOut" }}
        className="absolute top-[15%] right-[5%] h-[640px] w-[640px] rounded-full opacity-55 blur-[110px]"
        style={{
          background:
            "radial-gradient(circle, rgba(120,140,220,0.45), transparent 70%)",
        }}
      />
      <motion.div
        animate={{ x: [0, 50, -30, 0], y: [0, -50, 30, 0] }}
        transition={{ duration: 38, repeat: Infinity, ease: "easeInOut" }}
        className="absolute -bottom-40 left-[30%] h-[800px] w-[800px] rounded-full opacity-65 blur-[130px]"
        style={{
          background:
            "radial-gradient(circle, rgba(224,177,91,0.45), transparent 70%)",
        }}
      />
      <motion.div
        animate={{ x: [0, -40, 30, 0], y: [0, 30, -20, 0] }}
        transition={{ duration: 32, repeat: Infinity, ease: "easeInOut" }}
        className="absolute top-[55%] right-[35%] h-[480px] w-[480px] rounded-full opacity-45 blur-[100px]"
        style={{
          background:
            "radial-gradient(circle, rgba(180,120,200,0.35), transparent 70%)",
        }}
      />
    </div>
  );
}
