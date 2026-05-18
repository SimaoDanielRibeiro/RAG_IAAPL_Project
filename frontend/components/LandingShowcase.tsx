"use client";

import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowRight,
  BarChart3,
  Check,
  ChevronDown,
  Copy,
  Database,
  FileText,
  Filter,
  Hash,
  Heading1,
  LayoutGrid,
  Layers,
  MessagesSquare,
  MousePointerClick,
  Network,
  Quote,
  Search,
  ShieldCheck,
  Sparkles,
  Terminal,
  Upload,
  User,
} from "lucide-react";
import { Logo } from "@/components/Logo";
import { stripMarkdown } from "@/lib/text";

type LandingShowcaseProps = {
  onEnter: () => void;
};

export function LandingShowcase({ onEnter }: LandingShowcaseProps) {
  return (
    <div className="relative isolate">
      <ShowcaseBackdrop />
      <LiveDemoSection />
      <FeaturesBento />
      <PipelineSection />
      <FAQSection />
      <FinalCTA onEnter={onEnter} />
    </div>
  );
}

function ShowcaseBackdrop() {
  // Three layers, each pegged behind every section with -z-10:
  //   1. A 28px dot grid for quiet texture (so the page isn't pure black).
  //   2. A soft gold radial glow drifting slowly near the top.
  //   3. A cool indigo glow near the bottom to balance the warm tones.
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      {/* Dot grid */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage:
            "radial-gradient(circle at 1px 1px, rgba(255,255,255,0.04) 1px, transparent 0)",
          backgroundSize: "28px 28px",
          maskImage:
            "linear-gradient(to bottom, transparent, black 8%, black 92%, transparent)",
        }}
      />

      {/* Warm gold glow */}
      <motion.div
        animate={{ x: [0, 40, -20, 0], y: [0, 30, -20, 0] }}
        transition={{ duration: 32, repeat: Infinity, ease: "easeInOut" }}
        className="absolute left-1/2 top-[8%] h-[520px] w-[680px] -translate-x-1/2 rounded-full blur-[140px]"
        style={{
          background:
            "radial-gradient(circle, rgba(224,177,91,0.06), transparent 70%)",
        }}
      />

      {/* Cool indigo glow */}
      <motion.div
        animate={{ x: [0, -30, 20, 0], y: [0, -25, 15, 0] }}
        transition={{ duration: 38, repeat: Infinity, ease: "easeInOut" }}
        className="absolute bottom-[10%] left-[10%] h-[480px] w-[560px] rounded-full blur-[140px]"
        style={{
          background:
            "radial-gradient(circle, rgba(120,140,220,0.05), transparent 70%)",
        }}
      />
    </div>
  );
}

/* ── Section header helpers ─────────────────────────────── */

function SectionLabel({ index, label }: { index: string; label: string }) {
  return (
    <div className="flex items-center gap-3 text-[10.5px] font-medium uppercase tracking-[0.22em]">
      <span className="font-mono text-muted">{index}</span>
      <span className="h-px w-8 bg-line" />
      <span className="text-accent">{label}</span>
    </div>
  );
}

function SectionHeading({
  title,
  subtitle,
  description,
}: {
  title: string;
  subtitle?: string;
  description?: string;
}) {
  return (
    <>
      <motion.h2
        initial={{ opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-100px" }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="mt-6 max-w-2xl text-[40px] font-semibold leading-[1.1] tracking-[-0.02em] text-primary sm:text-[44px]"
      >
        {title}
        {subtitle && (
          <>
            <br />
            <span className="text-secondary">{subtitle}</span>
          </>
        )}
      </motion.h2>
      {description && (
        <motion.p
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6, ease: "easeOut", delay: 0.1 }}
          className="mt-5 max-w-xl text-[14px] leading-[1.7] text-secondary"
        >
          {description}
        </motion.p>
      )}
    </>
  );
}

/* ── Card primitives ────────────────────────────────────── */

function BentoCard({
  className = "",
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className={`group relative flex flex-col overflow-hidden rounded-[14px] border border-line bg-sidebar/60 p-7 backdrop-blur-sm transition-colors hover:border-[rgba(255,255,255,0.10)] ${className}`}
    >
      {children}
    </motion.div>
  );
}

function CardHeader({ icon, title }: { icon: ReactNode; title: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="grid h-9 w-9 place-items-center rounded-md border border-line bg-elevated/60 text-accent">
        {icon}
      </span>
      <h3 className="text-[16px] font-semibold text-primary">{title}</h3>
    </div>
  );
}

function CardBody({ children }: { children: ReactNode }) {
  return (
    <p className="mt-3 text-[13.5px] leading-[1.65] text-secondary">
      {children}
    </p>
  );
}

/* ── Section 1 — Features bento ─────────────────────────── */

function FeaturesBento() {
  return (
    <section className="relative px-6 py-24 sm:px-10 sm:py-32">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px"
           style={{ background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.06), transparent)" }} />

      <div className="mx-auto max-w-6xl">
        <SectionLabel index="02" label="Features" />
        <SectionHeading
          title="Every layer pulls weight."
          subtitle="One grounded answer."
          description="Eight stages between upload and answer. Each one keeps the model honest to what the document actually says."
        />

        <div className="mt-14 grid grid-cols-12 gap-4">
          <LocalFirstCard       className="col-span-12 md:col-span-7" />
          <MultiFormatCard      className="col-span-12 md:col-span-5" />
          <LayoutAwareCard      className="col-span-12 md:col-span-5" />
          <HeadingChunkingCard  className="col-span-12 md:col-span-7" />
          <HybridRetrievalCard  className="col-span-12 md:col-span-5" />
          <RerankingCard        className="col-span-12 md:col-span-7" />
          <CitedEvidenceCard    className="col-span-12 md:col-span-7" />
          <SmartQueriesCard     className="col-span-12 md:col-span-5" />
        </div>
      </div>
    </section>
  );
}

/* ── Bento cards ────────────────────────────────────────── */

function LocalFirstCard({ className }: { className?: string }) {
  return (
    <BentoCard className={className}>
      <CardHeader icon={<ShieldCheck size={18} strokeWidth={1.8} />} title="Runs on your machine" />
      <CardBody>
        No tokens leave your computer. Embeddings, retrieval, and generation
        all run locally — your documents stay yours.
      </CardBody>

      <div className="mt-6 grid grid-cols-2 gap-2.5">
        <TechBadge layer="Chat"        name="Ollama · qwen2.5:7b-instruct" />
        <TechBadge layer="Embeddings"  name="nomic-embed-text" />
        <TechBadge layer="Vector"      name="Chroma DB" />
        <TechBadge layer="Runtime"     name="FastAPI + Next.js" />
      </div>

      <div className="mt-5 flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.18em] text-muted">
        <span className="relative flex h-1.5 w-1.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-ready opacity-60" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-ready" />
        </span>
        Offline-capable · Zero cloud calls
      </div>
    </BentoCard>
  );
}

function TechBadge({ layer, name }: { layer: string; name: string }) {
  return (
    <div className="rounded-md border border-line bg-app/40 px-3 py-2.5">
      <p className="text-[9.5px] font-medium uppercase tracking-[0.18em] text-muted">
        {layer}
      </p>
      <p className="mt-1 text-[12.5px] font-medium text-primary">{name}</p>
    </div>
  );
}

function MultiFormatCard({ className }: { className?: string }) {
  const formats = ["PDF", "DOCX", "TXT", "MD"];
  return (
    <BentoCard className={className}>
      <CardHeader icon={<FileText size={18} strokeWidth={1.8} />} title="Bring any format" />
      <CardBody>
        Mix PDFs, Word docs, plain text, and markdown — Lumen indexes them
        side-by-side.
      </CardBody>

      <div className="mt-6 grid grid-cols-4 gap-2">
        {formats.map((f) => (
          <div
            key={f}
            className="grid aspect-square place-items-center rounded-md border border-line bg-app/40 text-[12px] font-semibold tracking-[0.06em] text-secondary transition-colors group-hover:border-accent/30 group-hover:text-accent"
          >
            {f}
          </div>
        ))}
      </div>

      <div className="mt-5 text-[11px] text-muted">
        Up to <span className="text-secondary">10 files</span> ·{" "}
        <span className="text-secondary">200 MB</span> each
      </div>
    </BentoCard>
  );
}

function LayoutAwareCard({ className }: { className?: string }) {
  return (
    <BentoCard className={className}>
      <CardHeader
        icon={<LayoutGrid size={18} strokeWidth={1.8} />}
        title="Layout-aware extraction"
      />
      <CardBody>
        PyMuPDF reads the page. Headings, tables, and figure captions survive
        as their own retrievable blocks — never flattened into wall-of-text.
      </CardBody>

      <div className="mt-6 space-y-2.5 rounded-md border border-line bg-app/40 p-4">
        <BlockRow tag="H1" tone="accent">
          <div className="h-1.5 w-32 rounded-sm bg-primary/60" />
        </BlockRow>
        <BlockRow tag="¶">
          <div className="space-y-1">
            <div className="h-1 w-full rounded-sm bg-secondary/40" />
            <div className="h-1 w-4/5 rounded-sm bg-secondary/40" />
          </div>
        </BlockRow>
        <BlockRow tag="Table" tone="accent">
          <div className="grid grid-cols-4 gap-px overflow-hidden rounded-sm border border-accent/30">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-3 bg-accent/10" />
            ))}
          </div>
        </BlockRow>
        <BlockRow tag="Cap" tone="muted">
          <div className="h-1 w-24 rounded-sm bg-muted/60" />
        </BlockRow>
      </div>
    </BentoCard>
  );
}

function BlockRow({
  tag,
  tone,
  children,
}: {
  tag: string;
  tone?: "accent" | "muted";
  children: ReactNode;
}) {
  const toneClass =
    tone === "accent"
      ? "bg-accent/15 text-accent border-accent/30"
      : tone === "muted"
        ? "bg-elevated/30 text-muted border-line"
        : "bg-elevated/60 text-secondary border-line";
  return (
    <div className="flex items-center gap-2.5">
      <span
        className={`shrink-0 rounded border px-1.5 py-0.5 font-mono text-[9.5px] font-medium uppercase tracking-[0.06em] ${toneClass}`}
      >
        {tag}
      </span>
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}

function HeadingChunkingCard({ className }: { className?: string }) {
  const sections = [
    { tag: "1.0", title: "Introduction",  chunks: 1 },
    { tag: "1.1", title: "Background",    chunks: 2 },
    { tag: "2.0", title: "Architecture",  chunks: 3 },
  ];

  return (
    <BentoCard className={className}>
      <CardHeader
        icon={<Heading1 size={18} strokeWidth={1.8} />}
        title="Heading-aware chunking"
      />
      <CardBody>
        Chunks break at section boundaries — not arbitrary character counts.
        Citations land where the meaning starts.
      </CardBody>

      <div className="mt-6 space-y-2">
        {sections.map((sec, i) => (
          <motion.div
            key={sec.tag}
            initial={{ opacity: 0, x: -8 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: "-50px" }}
            transition={{ duration: 0.4, ease: "easeOut", delay: 0.08 * i }}
            className="rounded-md border border-line bg-app/30 px-3 py-2"
          >
            <div className="flex items-center justify-between">
              <span className="flex min-w-0 items-center gap-2 truncate font-mono text-[10.5px] font-medium">
                <span className="text-accent">§ {sec.tag}</span>
                <span className="text-secondary">{sec.title}</span>
              </span>
              <span className="shrink-0 text-[10px] font-medium uppercase tracking-[0.12em] text-muted">
                {sec.chunks} chunk{sec.chunks > 1 ? "s" : ""}
              </span>
            </div>
            <div className="mt-2 flex gap-1.5">
              {Array.from({ length: sec.chunks }).map((_, idx) => (
                <div
                  key={idx}
                  className="h-1 flex-1 rounded-full bg-accent/40"
                />
              ))}
            </div>
          </motion.div>
        ))}
      </div>
    </BentoCard>
  );
}

function HybridRetrievalCard({ className }: { className?: string }) {
  return (
    <BentoCard className={className}>
      <CardHeader icon={<Network size={18} strokeWidth={1.8} />} title="Hybrid retrieval" />
      <CardBody>
        Vector MMR catches meaning. BM25 catches exact terms.
        Their candidates merge before reranking.
      </CardBody>

      <div className="mt-6 flex-1">
        <div className="grid grid-cols-2 gap-6">
          <RetrievalColumn label="Vector · MMR" />
          <RetrievalColumn label="BM25 · keyword" />
        </div>

        <div className="my-4 flex items-center justify-center">
          <div className="h-4 w-px bg-line" />
          <ChevronDown size={14} className="mx-1 text-accent" />
          <div className="h-4 w-px bg-line" />
        </div>

        <div>
          <p className="mb-2 text-center text-[9.5px] font-medium uppercase tracking-[0.18em] text-accent">
            Reranking pool
          </p>
          <div className="flex justify-center gap-1.5">
            {Array.from({ length: 8 }).map((_, i) => (
              <span
                key={i}
                className="h-1.5 w-1.5 rounded-full bg-accent/70"
              />
            ))}
          </div>
        </div>
      </div>
    </BentoCard>
  );
}

function RetrievalColumn({ label }: { label: string }) {
  return (
    <div>
      <p className="mb-2 text-[9.5px] font-medium uppercase tracking-[0.18em] text-muted">
        {label}
      </p>
      <div className="flex justify-center gap-1.5">
        {Array.from({ length: 4 }).map((_, i) => (
          <span
            key={i}
            className="h-1.5 w-1.5 rounded-full bg-accent/35"
          />
        ))}
      </div>
    </div>
  );
}

function RerankingCard({ className }: { className?: string }) {
  const items = [
    { name: "pipeline.pdf",   page: 4,  score: 9 },
    { name: "retrieval.pdf",  page: 2,  score: 8 },
    { name: "pipeline.pdf",   page: 7,  score: 7 },
    { name: "handbook.pdf",   page: 11, score: 5 },
    { name: "pipeline.pdf",   page: 9,  score: 3 },
  ];

  return (
    <BentoCard className={className}>
      <CardHeader icon={<BarChart3 size={18} strokeWidth={1.8} />} title="CrossEncoder reranking" />
      <CardBody>
        Every candidate gets rescored 1–10 by a CrossEncoder (with an LLM
        fallback). Only the most relevant chunks survive into the answer.
      </CardBody>

      <div className="mt-6 space-y-2.5">
        {items.map((it, i) => (
          <div key={i} className="flex items-center gap-3">
            <span className="w-[140px] shrink-0 truncate font-mono text-[11.5px] text-secondary">
              {it.name}:p{it.page}
            </span>
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-elevated">
              <motion.div
                initial={{ width: 0 }}
                whileInView={{ width: `${it.score * 10}%` }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.9, ease: "easeOut", delay: 0.08 * i }}
                className="h-full rounded-full bg-accent"
              />
            </div>
            <span className="w-6 shrink-0 text-right font-mono text-[12px] font-medium text-accent">
              {it.score}
            </span>
          </div>
        ))}
      </div>
    </BentoCard>
  );
}

function CitedEvidenceCard({ className }: { className?: string }) {
  return (
    <BentoCard className={className}>
      <CardHeader icon={<Quote size={18} strokeWidth={1.8} />} title="Every claim, sourced" />
      <CardBody>
        Numbered chips at the end of each paragraph. Click one to jump
        straight to the chunk that backed it — page, score, exact text.
      </CardBody>

      <EvidencePreview />
    </BentoCard>
  );
}

function EvidencePreview() {
  return (
    <div className="mt-6 rounded-[10px] border border-line bg-app/40 p-4">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-1.5 text-[11.5px] font-medium text-[#4ADE80]">
          <span className="h-1.5 w-1.5 rounded-full bg-[#4ADE80]" />
          High confidence
        </span>
        <span className="text-[10.5px] font-medium uppercase tracking-[0.12em] text-muted">
          6 chunks
        </span>
      </div>

      <p className="mt-4 text-[9.5px] font-medium uppercase tracking-[0.16em] text-muted">
        Citations
      </p>
      <ul className="mt-1.5 space-y-1 text-[12.5px] text-secondary">
        <li className="flex items-start gap-2">
          <span className="mt-px text-accent">›</span>
          pipeline.pdf (Pages 4, 7, 9)
        </li>
        <li className="flex items-start gap-2">
          <span className="mt-px text-accent">›</span>
          retrieval.pdf (Pages 2, 5)
        </li>
      </ul>

      <p className="mt-4 text-[9.5px] font-medium uppercase tracking-[0.16em] text-muted">
        Source distribution
      </p>
      <div className="mt-2.5 space-y-2.5">
        <SourceBar name="pipeline.pdf"  chunks={4} pct={67} delay={0} />
        <SourceBar name="retrieval.pdf" chunks={2} pct={33} delay={0.15} />
      </div>
    </div>
  );
}

function SourceBar({
  name,
  chunks,
  pct,
  delay,
}: {
  name: string;
  chunks: number;
  pct: number;
  delay: number;
}) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between gap-2 text-[11.5px]">
        <span className="min-w-0 truncate text-secondary">{name}</span>
        <span className="shrink-0 font-mono text-muted">
          {chunks} chunks · {pct}%
        </span>
      </div>
      <div className="h-1 w-full overflow-hidden rounded-full bg-elevated">
        <motion.div
          initial={{ width: 0 }}
          whileInView={{ width: `${pct}%` }}
          viewport={{ once: true, margin: "-50px" }}
          transition={{ duration: 0.9, ease: "easeOut", delay }}
          className="h-full rounded-full bg-accent"
        />
      </div>
    </div>
  );
}

function SmartQueriesCard({ className }: { className?: string }) {
  return (
    <BentoCard className={className}>
      <CardHeader icon={<Sparkles size={18} strokeWidth={1.8} />} title="Smarter queries" />
      <CardBody>
        Three layers stack before retrieval even runs.
      </CardBody>

      <div className="mt-6 space-y-2.5">
        <SubFeature
          icon={<MessagesSquare size={13} strokeWidth={1.8} />}
          name="Conversational"
          detail="Follow-ups rewritten using prior chat history."
        />
        <SubFeature
          icon={<Layers size={13} strokeWidth={1.8} />}
          name="Multi-query"
          detail="LLM generates 2 alternative phrasings to broaden recall."
        />
        <SubFeature
          icon={<Filter size={13} strokeWidth={1.8} />}
          name="Scope"
          detail="Restrict retrieval to a subset of files at query time."
        />
      </div>

      <div className="mt-5 rounded-md border border-line bg-app/40 p-3 font-mono text-[11px] text-secondary">
        <span className="text-muted">user&gt;</span> what does the report say?
        <br />
        <span className="text-accent">rewritten&gt;</span> what does the Q3
        compliance report state about audit findings?
      </div>
    </BentoCard>
  );
}

function SubFeature({
  icon,
  name,
  detail,
}: {
  icon: ReactNode;
  name: string;
  detail: string;
}) {
  return (
    <div className="flex items-start gap-3 rounded-md border border-line bg-app/30 px-3 py-2.5">
      <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded border border-line bg-elevated/60 text-accent">
        {icon}
      </span>
      <div className="min-w-0">
        <p className="text-[12.5px] font-medium text-primary">{name}</p>
        <p className="mt-0.5 text-[11.5px] leading-[1.45] text-muted">
          {detail}
        </p>
      </div>
    </div>
  );
}

/* ── Section 2 — Pipeline ───────────────────────────────── */

type Step = {
  n: string;
  name: string;
  icon: ReactNode;
  detail: string;
  description: string;
};

const PIPELINE_STEPS: Step[] = [
  {
    n: "01",
    name: "Upload",
    icon: <Upload size={16} strokeWidth={1.8} />,
    detail: "PDF · DOCX · TXT · MD",
    description:
      "Drop files into the sidebar — up to 10 per session, 200 MB each. Path-traversal protection keeps writes inside the project's data folder so an unsafe filename can't escape the index.",
  },
  {
    n: "02",
    name: "Extract",
    icon: <LayoutGrid size={16} strokeWidth={1.8} />,
    detail: "Layout · tables · captions",
    description:
      "PyMuPDF reads the page structure. Headings, paragraphs, tables (as markdown), and figure captions survive as their own blocks; multi-column layouts are reassembled in real reading order.",
  },
  {
    n: "03",
    name: "Chunk",
    icon: <Heading1 size={16} strokeWidth={1.8} />,
    detail: "Heading-aware boundaries",
    description:
      "Text splits at section boundaries detected during extraction — never mid-sentence in another section. Each chunk records its section title and page so retrieval surfaces meaningful starts.",
  },
  {
    n: "04",
    name: "Embed",
    icon: <Hash size={16} strokeWidth={1.8} />,
    detail: "nomic-embed-text",
    description:
      "Every chunk becomes a 768-dimensional vector through nomic-embed-text, running locally on Ollama. No API call leaves your machine; no token leaves your hardware.",
  },
  {
    n: "05",
    name: "Index",
    icon: <Database size={16} strokeWidth={1.8} />,
    detail: "Chroma vector store",
    description:
      "Vectors persist in a Chroma collection keyed by content hash. Re-uploading the same file reuses the existing collection — zero reprocessing, instant warm starts across restarts.",
  },
  {
    n: "06",
    name: "Retrieve",
    icon: <Search size={16} strokeWidth={1.8} />,
    detail: "Vector + BM25 hybrid",
    description:
      "Each question expands into multiple search variants. Vector MMR catches semantic neighbours; BM25 catches exact terms. Their candidates merge, then expand with neighbouring chunks for context.",
  },
  {
    n: "07",
    name: "Rerank",
    icon: <BarChart3 size={16} strokeWidth={1.8} />,
    detail: "CrossEncoder 1–10",
    description:
      "Every candidate is rescored 1–10 by a CrossEncoder (with an LLM fallback). Only the highest-ranked chunks survive; if the average score is too low, the answer is held back rather than guessed.",
  },
  {
    n: "08",
    name: "Cite",
    icon: <MousePointerClick size={16} strokeWidth={1.8} />,
    detail: "Click chip → evidence",
    description:
      "The generator is bound to use only the surviving chunks. Each claim ends with a numbered chip — click it to jump to the exact excerpt in the Evidence panel, page and score included.",
  },
];

const PIPELINE_AUTOPLAY_MS = 7000;

function PipelineSection() {
  return (
    <section className="relative px-6 py-24 sm:px-10 sm:py-32">
      <div className="mx-auto max-w-6xl">
        <SectionLabel index="03" label="Pipeline" />
        <SectionHeading
          title="From upload to answer."
          subtitle="Eight stages. Fully local."
          description="Hover or tap a stage to see what runs there. The flow auto-advances; the dot keeps moving regardless."
        />

        <PipelineDiagram steps={PIPELINE_STEPS} />
      </div>
    </section>
  );
}

function PipelineDiagram({ steps }: { steps: Step[] }) {
  const [active, setActive] = useState(0);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (paused) return;
    const interval = window.setInterval(() => {
      setActive((current) => (current + 1) % steps.length);
    }, PIPELINE_AUTOPLAY_MS);
    return () => window.clearInterval(interval);
  }, [paused, steps.length]);

  const activeStep   = steps[active];
  const progressPct  = steps.length > 1 ? (active / (steps.length - 1)) * 100 : 0;

  const focusStep = (index: number) => {
    setActive(index);
    setPaused(true);
  };

  return (
    <div className="mt-16">
      <div
        className="relative"
        onMouseLeave={() => setPaused(false)}
      >
        {/* Background connecting line (single column screens hide it) */}
        <div
          className="pointer-events-none absolute left-[34px] right-[34px] top-[34px] hidden h-px bg-line lg:block"
        />

        {/* Filled segment up to the active step */}
        <motion.div
          aria-hidden
          animate={{ width: `calc(${progressPct}% - ${(progressPct / 100) * 68}px)` }}
          transition={{ duration: 0.45, ease: "easeOut" }}
          className="pointer-events-none absolute left-[34px] top-[34px] hidden h-px bg-accent lg:block"
        />

        {/* Decorative dot — continues flowing regardless of active state */}
        <motion.div
          aria-hidden
          animate={{ left: ["0%", "100%"] }}
          transition={{ duration: 6, repeat: Infinity, ease: "linear" }}
          className="pointer-events-none absolute top-[30px] hidden h-2 w-2 -translate-x-1/2 rounded-full bg-accent shadow-[0_0_12px_rgba(224,177,91,0.8)] lg:block"
        />

        <div className="grid grid-cols-2 gap-y-10 sm:grid-cols-4 sm:gap-x-4 lg:grid-cols-8">
          {steps.map((step, i) => (
            <PipelineNode
              key={step.n}
              step={step}
              index={i}
              isActive={i === active}
              onFocus={() => focusStep(i)}
            />
          ))}
        </div>
      </div>

      {/* Description panel + autoplay progress bar */}
      <div className="relative mt-12 lg:mt-14">
        <PipelineProgressBar
          activeKey={`${active}-${paused}`}
          paused={paused}
        />
        <AnimatePresence mode="wait">
          <motion.div
            key={activeStep.n}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.22, ease: "easeOut" }}
            className="overflow-hidden rounded-[14px] border border-line bg-sidebar/60 backdrop-blur-sm"
          >
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_minmax(320px,380px)]">
              {/* Text side */}
              <div className="px-6 py-6 sm:px-8 sm:py-7">
                <div className="flex items-center gap-3">
                  <span className="grid h-10 w-10 place-items-center rounded-md border border-accent/40 bg-accent/10 text-accent">
                    {activeStep.icon}
                  </span>
                  <div>
                    <p className="font-mono text-[10px] font-medium uppercase tracking-[0.22em] text-muted">
                      Stage {activeStep.n}
                    </p>
                    <p className="text-[16px] font-semibold leading-snug text-primary">
                      {activeStep.name}
                      <span className="ml-2 text-[12px] font-medium uppercase tracking-[0.06em] text-accent/80">
                        {activeStep.detail}
                      </span>
                    </p>
                  </div>
                </div>
                <p className="mt-4 text-[13.5px] leading-[1.7] text-secondary">
                  {activeStep.description}
                </p>
              </div>

              {/* Visualizer side */}
              <div className="border-t border-line bg-app/40 px-6 py-6 sm:px-8 sm:py-7 lg:border-l lg:border-t-0">
                <p className="mb-4 flex items-center gap-2 font-mono text-[9.5px] font-medium uppercase tracking-[0.22em] text-muted">
                  <span className="relative flex h-1.5 w-1.5">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent/50 opacity-70" />
                    <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-accent" />
                  </span>
                  Live · what runs here
                </p>
                <div className="grid place-items-center">
                  <PipelineVisualizer stepNumber={activeStep.n} />
                </div>
              </div>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}

/* ── Pipeline visualizers ───────────────────────────────── */

function PipelineVisualizer({ stepNumber }: { stepNumber: string }) {
  switch (stepNumber) {
    case "01": return <UploadVisual />;
    case "02": return <ExtractVisual />;
    case "03": return <ChunkVisual />;
    case "04": return <EmbedVisual />;
    case "05": return <IndexVisual />;
    case "06": return <RetrieveVisual />;
    case "07": return <RerankVisual />;
    case "08": return <CiteVisual />;
    default:   return null;
  }
}

function UploadVisual() {
  const files = [
    { name: "policy.pdf",    size: "2.4 MB" },
    { name: "handbook.docx", size: "812 KB" },
    { name: "notes.md",      size: "14 KB"  },
    { name: "spec.pdf",      size: "1.1 MB" },
  ];
  return (
    <div className="w-full max-w-[300px] space-y-1.5">
      {files.map((f, i) => (
        <motion.div
          key={f.name}
          initial={{ x: -36, opacity: 0 }}
          animate={{ x: [-36, 0, 0, -36], opacity: [0, 1, 1, 0] }}
          transition={{
            duration: 4.5,
            times: [0, 0.18, 0.85, 1],
            delay: i * 0.3,
            repeat: Infinity,
            ease: "easeOut",
          }}
          className="flex items-center justify-between rounded-md border border-line bg-app/50 px-3 py-2"
        >
          <span className="flex min-w-0 items-center gap-2">
            <Upload size={11} className="text-accent" strokeWidth={1.8} />
            <span className="truncate font-mono text-[10.5px] text-secondary">{f.name}</span>
          </span>
          <span className="shrink-0 font-mono text-[9.5px] text-muted">{f.size}</span>
        </motion.div>
      ))}
    </div>
  );
}

function ExtractVisual() {
  // A scan line sweeps top-to-bottom across a page wireframe; as it crosses
  // each region, a classification label pops out to the right. Each region
  // also tints itself when the scan line passes over it, so the user sees
  // "the extractor reading the page".
  const SCAN_DURATION = 6;
  const regions = [
    { kind: "heading", label: "H1",    cross: 0.12, render: () => <div className="h-2 w-3/5 rounded-sm bg-primary/55" /> },
    { kind: "para",    label: "¶",     cross: 0.34, render: () => (
      <div className="space-y-1">
        <div className="h-1 w-full rounded-sm bg-secondary/40" />
        <div className="h-1 w-4/5 rounded-sm bg-secondary/40" />
        <div className="h-1 w-3/4 rounded-sm bg-secondary/40" />
      </div>
    ) },
    { kind: "table", label: "Table",   cross: 0.62, render: () => (
      <div className="grid grid-cols-4 gap-px overflow-hidden rounded-sm border border-line/60">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-2.5 bg-elevated/40" />
        ))}
      </div>
    ) },
    { kind: "cap",   label: "Caption", cross: 0.86, render: () => (
      <div className="flex items-center gap-1.5">
        <span className="h-1 w-1 rounded-full bg-accent" />
        <div className="h-1 w-24 rounded-sm bg-secondary/40" />
      </div>
    ) },
  ];

  return (
    <div className="grid w-full max-w-[300px] grid-cols-[1fr_82px] gap-3">
      <div className="relative overflow-hidden rounded-md border border-line bg-app/40 p-3">
        {/* Scan line */}
        <motion.div
          animate={{ top: ["-4%", "104%"] }}
          transition={{ duration: SCAN_DURATION, repeat: Infinity, ease: "linear" }}
          className="pointer-events-none absolute inset-x-0 z-10 h-px bg-accent shadow-[0_0_10px_rgba(224,177,91,0.7)]"
        />

        {/* Page regions — tint when the scan passes them */}
        <div className="relative space-y-2.5">
          {regions.map((r) => (
            <motion.div
              key={r.label}
              animate={{
                backgroundColor: [
                  "rgba(255,255,255,0)",
                  "rgba(255,255,255,0)",
                  "rgba(224,177,91,0.12)",
                  "rgba(224,177,91,0.06)",
                ],
              }}
              transition={{
                duration: SCAN_DURATION,
                times: [0, r.cross - 0.03, r.cross + 0.02, 1],
                repeat: Infinity,
                ease: "easeOut",
              }}
              className="rounded-sm px-1.5 py-1"
            >
              {r.render()}
            </motion.div>
          ))}
        </div>
      </div>

      {/* Classification labels pop out as scan hits each region */}
      <div className="flex flex-col gap-1.5 pt-1">
        {regions.map((r) => (
          <motion.span
            key={r.label}
            animate={{
              opacity: [0, 0, 1, 1, 0],
              x:       [-12, -12, 0, 0, -4],
            }}
            transition={{
              duration: SCAN_DURATION,
              times: [0, r.cross - 0.02, r.cross + 0.01, 0.94, 1],
              repeat: Infinity,
              ease: "easeOut",
            }}
            className="inline-flex items-center justify-center rounded border border-accent/40 bg-accent/10 px-1.5 py-0.5 font-mono text-[9.5px] font-medium text-accent"
          >
            {r.label}
          </motion.span>
        ))}
      </div>
    </div>
  );
}

function ChunkVisual() {
  // Source text bars with heading markers at three positions. Cut lines
  // animate in at the heading boundaries, then the chunks form below with
  // a "§ X.X" tag flying in for each.
  const CYCLE = 6;
  const lines = [
    { kind: "heading", tag: "§ 1.0" },
    { kind: "text"    },
    { kind: "heading", tag: "§ 1.1" },
    { kind: "text"    },
    { kind: "text"    },
    { kind: "heading", tag: "§ 2.0" },
    { kind: "text"    },
  ] as const;

  // Heading boundaries fall before indices 2 and 5 → two cut lines.
  const cuts = [2, 5];

  return (
    <div className="w-full max-w-[300px] space-y-3">
      {/* Source stream with cuts */}
      <div className="relative overflow-hidden rounded-md border border-line bg-app/40 px-3 py-3">
        <div className="relative space-y-1.5">
          {lines.map((line, i) => (
            <div key={i} className="relative">
              {line.kind === "heading" ? (
                <motion.div
                  animate={{ backgroundColor: ["rgba(224,177,91,0.18)", "rgba(224,177,91,0.4)", "rgba(224,177,91,0.18)"] }}
                  transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut", delay: i * 0.1 }}
                  className="flex h-3 items-center rounded-sm px-1.5 font-mono text-[9px] font-medium text-accent"
                >
                  {line.tag}
                </motion.div>
              ) : (
                <div className="h-1.5 w-full rounded-sm bg-secondary/35" />
              )}
              {/* Dashed cut line that animates in at heading boundaries */}
              {cuts.includes(i) && (
                <motion.div
                  initial={{ scaleX: 0, opacity: 0 }}
                  animate={{ scaleX: [0, 1, 1, 0], opacity: [0, 1, 1, 0] }}
                  transition={{
                    duration: CYCLE,
                    times: [0, 0.18 + cuts.indexOf(i) * 0.08, 0.85, 1],
                    repeat: Infinity,
                    ease: "easeOut",
                  }}
                  className="pointer-events-none absolute -top-1 left-0 right-0 border-t border-dashed border-accent/70"
                  style={{ originX: 0 }}
                >
                  <span className="absolute right-1 -top-2 rounded bg-app px-1 font-mono text-[8px] text-accent">
                    cut
                  </span>
                </motion.div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Result chunks form below */}
      <div className="grid grid-cols-3 gap-1.5">
        {[
          { tag: "§ 1.0", title: "Intro"        },
          { tag: "§ 1.1", title: "Background"   },
          { tag: "§ 2.0", title: "Architecture" },
        ].map((c, i) => (
          <motion.div
            key={c.tag}
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: [0, 0, 1, 1, 0], y: [-6, -6, 0, 0, -6] }}
            transition={{
              duration: CYCLE,
              times: [0, 0.35 + i * 0.06, 0.42 + i * 0.06, 0.9, 1],
              repeat: Infinity,
              ease: "easeOut",
            }}
            className="rounded-md border border-accent/30 bg-accent/10 px-2 py-1.5 text-center"
          >
            <p className="font-mono text-[9px] font-medium text-accent">{c.tag}</p>
            <p className="mt-0.5 font-mono text-[9px] text-secondary">{c.title}</p>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

function EmbedVisual() {
  const dims = ["0.421", "-0.183", "0.547", "0.214", "-0.892", "0.063", "0.318", "-0.471"];
  return (
    <div className="grid w-full max-w-[300px] grid-cols-[auto_auto_1fr] items-center gap-3">
      <div className="rounded-md border border-line bg-app/50 p-2.5">
        <p className="font-mono text-[9px] uppercase tracking-[0.16em] text-muted">chunk</p>
        <div className="mt-1.5 space-y-0.5">
          <div className="h-0.5 w-12 rounded-sm bg-secondary/40" />
          <div className="h-0.5 w-10 rounded-sm bg-secondary/40" />
          <div className="h-0.5 w-11 rounded-sm bg-secondary/40" />
        </div>
      </div>

      <motion.div
        animate={{ x: [0, 6, 0] }}
        transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
        className="text-accent"
      >
        <ArrowRight size={14} strokeWidth={1.8} />
      </motion.div>

      <div>
        <p className="font-mono text-[9px] uppercase tracking-[0.16em] text-muted">
          Vector · 768d
        </p>
        <div className="mt-2 grid grid-cols-2 gap-1">
          {dims.map((d, i) => (
            <motion.span
              key={d + i}
              animate={{ opacity: [0, 1, 1, 0.4] }}
              transition={{
                duration: 3.5,
                delay: i * 0.18,
                repeat: Infinity,
                repeatDelay: 0.5,
                times: [0, 0.25, 0.85, 1],
                ease: "easeOut",
              }}
              className="rounded bg-accent/10 px-1.5 py-0.5 text-center font-mono text-[9.5px] text-accent"
            >
              {d}
            </motion.span>
          ))}
        </div>
      </div>
    </div>
  );
}

function IndexVisual() {
  // A vector pill repeatedly flies from the left edge into a cell of the
  // grid, which lights up on impact. We stagger 4 successive pills so it
  // feels like a continuous stream of vectors being persisted.
  const CYCLE = 6;
  const COLS = 8;
  const ROWS = 4;
  // Cells that "get hit" during this cycle (in flight order)
  const hits = [10, 23, 17, 4, 28, 13, 30, 8];

  return (
    <div className="w-full max-w-[300px]">
      <div className="flex items-center justify-between">
        <p className="font-mono text-[9.5px] uppercase tracking-[0.16em] text-muted">
          Chroma collection
        </p>
        <span className="font-mono text-[9.5px] text-accent">sha · a1b2c3…</span>
      </div>

      <div className="relative mt-3">
        {/* Grid (the index) */}
        <div className="relative grid grid-cols-8 gap-1 rounded-md border border-line bg-app/40 p-2">
          {Array.from({ length: COLS * ROWS }).map((_, i) => {
            const hitOrder = hits.indexOf(i);
            const isHit    = hitOrder >= 0;
            const tHit     = isHit ? 0.1 + hitOrder * (0.78 / hits.length) : 0;
            return (
              <motion.div
                key={i}
                animate={
                  isHit
                    ? {
                        backgroundColor: [
                          "rgba(255,255,255,0.05)",
                          "rgba(255,255,255,0.05)",
                          "rgba(224,177,91,0.85)",
                          "rgba(224,177,91,0.4)",
                          "rgba(224,177,91,0.4)",
                        ],
                        scale: [1, 1, 1.25, 1, 1],
                      }
                    : { backgroundColor: "rgba(255,255,255,0.05)" }
                }
                transition={{
                  duration: CYCLE,
                  times: isHit ? [0, tHit - 0.01, tHit, tHit + 0.05, 1] : [0, 1],
                  repeat: Infinity,
                  ease: "easeOut",
                }}
                className="aspect-square rounded-sm"
              />
            );
          })}
        </div>

        {/* Flying vector pills — each lands on one of the hit cells */}
        {hits.slice(0, 4).map((cellIndex, k) => {
          const col       = cellIndex % COLS;
          const row       = Math.floor(cellIndex / COLS);
          const tStart    = 0.05 + k * (0.78 / hits.length);
          const tLand     = tStart + 0.05;
          // grid is ~280px wide minus padding; rough cell size in % for x
          const targetX = `${(col / (COLS - 1)) * 88 + 6}%`;
          const targetY = `${row * 28 + 14}px`;
          return (
            <motion.div
              key={k}
              animate={{
                left:    ["-12%", "-12%", targetX,  targetX,  "-12%"],
                top:     ["50%", "50%", targetY, targetY, "50%"],
                opacity: [0, 0, 1, 0, 0],
                scale:   [0.85, 0.85, 1, 0.6, 0.85],
              }}
              transition={{
                duration: CYCLE,
                times: [0, tStart, tLand, tLand + 0.04, 1],
                repeat: Infinity,
                ease: "easeIn",
              }}
              className="pointer-events-none absolute -translate-x-1/2 -translate-y-1/2 rounded border border-accent/60 bg-accent/25 px-1.5 py-0.5 font-mono text-[8.5px] text-accent shadow-[0_4px_10px_rgba(224,177,91,0.35)]"
            >
              [0.42, …]
            </motion.div>
          );
        })}
      </div>

      <p className="mt-2.5 font-mono text-[9.5px] text-muted">
        Vectors persisted · keyed by hash
      </p>
    </div>
  );
}

function RetrieveVisual() {
  // Story across one 6s cycle:
  //   0.00 – 0.20  question pill pulses, 3 query rewrites fan down
  //   0.20 – 0.55  rewrites sweep across the index, matching dots light up
  //   0.55 – 0.95  matched dots fly into the results pool
  //   0.95 – 1.00  pool stays steady, then fades for the next loop
  const CYCLE = 6;
  const COLS  = 12;
  const ROWS  = 4;
  // Indexes in the index grid that count as "matches"
  const matchSet = new Set([5, 14, 23, 28, 34, 41, 7, 19]);

  const rewrites = ["rewrite 1", "rewrite 2", "rewrite 3"];

  return (
    <div className="w-full max-w-[300px]">
      {/* Question pill */}
      <div className="flex justify-center">
        <motion.span
          animate={{
            scale: [1, 1.05, 1, 1, 1],
            opacity: [1, 1, 0.7, 0.7, 1],
          }}
          transition={{ duration: CYCLE, times: [0, 0.1, 0.25, 0.95, 1], repeat: Infinity, ease: "easeInOut" }}
          className="rounded-full border border-accent/50 bg-accent/10 px-3.5 py-1 font-mono text-[10.5px] text-accent"
        >
          question
        </motion.span>
      </div>

      {/* Rewrite pills fan down */}
      <div className="mt-2 grid grid-cols-3 gap-1">
        {rewrites.map((q, i) => (
          <motion.div
            key={q}
            animate={{
              opacity: [0, 0, 1, 1, 0, 0],
              y:       [-8, -8, 0, 0, 4, 4],
            }}
            transition={{
              duration: CYCLE,
              times: [0, 0.07 + i * 0.03, 0.16 + i * 0.03, 0.5, 0.6, 1],
              repeat: Infinity,
              ease: "easeOut",
            }}
            className="rounded border border-accent/30 bg-accent/5 px-1.5 py-0.5 text-center font-mono text-[8.5px] text-accent"
          >
            {q}
          </motion.div>
        ))}
      </div>

      {/* Index grid */}
      <div className="relative mt-3 rounded-md border border-line bg-app/40 p-2">
        {/* Scanning sweep — moves left to right while rewrites are active */}
        <motion.div
          animate={{ left: ["-10%", "100%", "100%"] }}
          transition={{ duration: CYCLE, times: [0.25, 0.55, 1], repeat: Infinity, ease: "linear" }}
          className="pointer-events-none absolute inset-y-0 z-10 w-px bg-accent/70 shadow-[0_0_8px_rgba(224,177,91,0.6)]"
        />

        <div className="relative grid grid-cols-12 gap-0.5">
          {Array.from({ length: COLS * ROWS }).map((_, i) => {
            const isMatch = matchSet.has(i);
            return (
              <motion.div
                key={i}
                animate={
                  isMatch
                    ? {
                        backgroundColor: [
                          "rgba(255,255,255,0.07)",
                          "rgba(255,255,255,0.07)",
                          "rgba(224,177,91,0.85)",
                          "rgba(224,177,91,0.45)",
                          "rgba(255,255,255,0.07)",
                          "rgba(255,255,255,0.07)",
                        ],
                        scale: [1, 1, 1.6, 1.1, 1, 1],
                      }
                    : { backgroundColor: "rgba(255,255,255,0.07)" }
                }
                transition={{
                  duration: CYCLE,
                  times: isMatch
                    ? [0, 0.28 + (i % COLS) * 0.005, 0.32 + (i % COLS) * 0.005, 0.55, 0.95, 1]
                    : [0, 1],
                  repeat: Infinity,
                  ease: "easeOut",
                }}
                className="h-1.5 w-1.5 rounded-full"
              />
            );
          })}
        </div>
      </div>

      {/* Results pool */}
      <motion.div
        animate={{
          opacity: [0, 0, 0, 1, 1, 0],
          y:       [6, 6, 6, 0, 0, 6],
        }}
        transition={{
          duration: CYCLE,
          times: [0, 0.55, 0.6, 0.7, 0.92, 1],
          repeat: Infinity,
          ease: "easeOut",
        }}
        className="mt-3 flex items-center justify-between rounded-md border border-accent/40 bg-accent/10 px-3 py-1.5 font-mono text-[9.5px] text-accent"
      >
        <span>merged pool</span>
        <span>8 chunks</span>
      </motion.div>
    </div>
  );
}

function RerankVisual() {
  const bars = [
    { initial: 50, score: 9, survives: true  },
    { initial: 60, score: 8, survives: true  },
    { initial: 40, score: 7, survives: true  },
    { initial: 70, score: 5, survives: false },
    { initial: 50, score: 3, survives: false },
    { initial: 65, score: 2, survives: false },
  ];
  return (
    <div className="w-full max-w-[300px]">
      <div className="flex h-[120px] items-end justify-between gap-1.5">
        {bars.map((b, i) => (
          <div key={i} className="flex flex-1 flex-col items-center gap-1.5">
            <motion.div
              initial={{ height: `${b.initial}%` }}
              animate={{
                height: [`${b.initial}%`, `${b.score * 10}%`, `${b.score * 10}%`, `${b.initial}%`],
              }}
              transition={{
                duration: 4.5,
                times: [0, 0.3, 0.85, 1],
                repeat: Infinity,
                ease: "easeOut",
                delay: i * 0.04,
              }}
              className={`w-full rounded-t-sm ${
                b.survives ? "bg-accent" : "bg-secondary/30"
              }`}
            />
            <motion.span
              animate={{
                color: b.survives
                  ? ["#7a7268", "#e0b15b", "#e0b15b", "#7a7268"]
                  : ["#7a7268", "#5a5a5a", "#5a5a5a", "#7a7268"],
              }}
              transition={{
                duration: 4.5,
                times: [0, 0.3, 0.85, 1],
                repeat: Infinity,
                ease: "easeOut",
                delay: i * 0.04,
              }}
              className="font-mono text-[9.5px]"
            >
              {b.score}
            </motion.span>
          </div>
        ))}
      </div>
      <div className="mt-2 flex justify-between font-mono text-[9px] uppercase tracking-[0.14em]">
        <span className="text-accent">3 survive</span>
        <span className="text-muted">3 rejected</span>
      </div>
    </div>
  );
}

function CiteVisual() {
  return (
    <div className="w-full max-w-[300px] space-y-2.5">
      {/* Mini answer */}
      <div className="rounded-md border border-line bg-app/40 px-3 py-2 text-[11px] leading-[1.55] text-secondary">
        The pipeline ranks every candidate by score
        <motion.span
          animate={{
            scale: [1, 1.18, 1],
            boxShadow: [
              "0 0 0 0 rgba(224,177,91,0)",
              "0 0 0 4px rgba(224,177,91,0.32)",
              "0 0 0 0 rgba(224,177,91,0)",
            ],
          }}
          transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
          className="ml-1 inline-flex h-[16px] min-w-[16px] items-center justify-center rounded-[4px] border border-accent/40 bg-accent/15 px-1 align-middle font-mono text-[9.5px] font-medium leading-none text-accent"
        >
          3
        </motion.span>
      </div>

      {/* Connector */}
      <motion.div
        animate={{ y: [0, 4, 0] }}
        transition={{ duration: 1.3, repeat: Infinity, ease: "easeInOut" }}
        className="flex justify-center text-accent"
      >
        <ChevronDown size={14} strokeWidth={1.8} />
      </motion.div>

      {/* Highlighted evidence card */}
      <motion.div
        animate={{
          borderColor: [
            "rgba(255,255,255,0.07)",
            "rgba(224,177,91,0.5)",
            "rgba(255,255,255,0.07)",
          ],
          boxShadow: [
            "0 0 0 0 rgba(224,177,91,0)",
            "0 0 12px rgba(224,177,91,0.25)",
            "0 0 0 0 rgba(224,177,91,0)",
          ],
        }}
        transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
        className="rounded-md border border-line bg-app/40 p-3"
      >
        <div className="flex items-center gap-2">
          <span className="grid h-5 w-5 place-items-center rounded-full bg-accent font-mono text-[9.5px] font-semibold text-app">
            3
          </span>
          <span className="font-mono text-[10.5px] text-primary">pipeline.pdf</span>
          <span className="ml-auto font-mono text-[9.5px] text-accent">85%</span>
        </div>
        <div className="mt-2 space-y-1">
          <div className="h-1 w-full rounded-sm bg-secondary/30" />
          <div className="h-1 w-4/5 rounded-sm bg-secondary/30" />
          <div className="h-1 w-2/3 rounded-sm bg-secondary/30" />
        </div>
      </motion.div>
    </div>
  );
}

function PipelineNode({
  step,
  index,
  isActive,
  onFocus,
}: {
  step: Step;
  index: number;
  isActive: boolean;
  onFocus: () => void;
}) {
  return (
    <motion.button
      type="button"
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ duration: 0.5, ease: "easeOut", delay: 0.06 * index }}
      onMouseEnter={onFocus}
      onFocus={onFocus}
      onClick={onFocus}
      className="group relative flex flex-col items-center text-center focus:outline-none"
      aria-label={`Stage ${step.n} ${step.name}`}
      aria-pressed={isActive}
    >
      <motion.span
        animate={{
          scale: isActive ? 1.08 : 1,
        }}
        transition={{ duration: 0.3, ease: "easeOut" }}
        className={`relative z-10 grid h-[68px] w-[68px] place-items-center rounded-full border transition-colors duration-300 ${
          isActive
            ? "border-accent bg-accent/15 text-accent shadow-[0_0_24px_rgba(224,177,91,0.4)]"
            : "border-line bg-sidebar text-accent group-hover:border-[rgba(255,255,255,0.18)]"
        }`}
      >
        {step.icon}
      </motion.span>
      <span
        className={`mt-3 font-mono text-[10px] font-medium tracking-[0.18em] transition-colors ${
          isActive ? "text-accent" : "text-muted"
        }`}
      >
        {step.n}
      </span>
      <span
        className={`mt-1 text-[13.5px] font-semibold transition-colors ${
          isActive ? "text-primary" : "text-primary/85 group-hover:text-primary"
        }`}
      >
        {step.name}
      </span>
      <span
        className={`mt-1 max-w-[130px] text-[10.5px] leading-[1.4] transition-colors ${
          isActive ? "text-secondary" : "text-muted"
        }`}
      >
        {step.detail}
      </span>
    </motion.button>
  );
}

function PipelineProgressBar({
  activeKey,
  paused,
}: {
  activeKey: string;
  paused: boolean;
}) {
  return (
    <div className="pointer-events-none absolute -top-px left-6 right-6 h-px overflow-hidden rounded-full bg-line">
      <motion.div
        key={activeKey}
        initial={{ width: "0%" }}
        animate={{ width: paused ? "0%" : "100%" }}
        transition={{ duration: paused ? 0 : PIPELINE_AUTOPLAY_MS / 1000, ease: "linear" }}
        className="h-full rounded-full bg-accent/70"
      />
    </div>
  );
}

/* ── Section 3 — Final CTA ──────────────────────────────── */

function FinalCTA({ onEnter }: { onEnter: () => void }) {
  return (
    <section className="relative px-6 py-32 sm:px-10 sm:py-40">
      {/* Soft accent glow */}
      <motion.div
        animate={{ opacity: [0.5, 1, 0.5] }}
        transition={{ duration: 4.5, repeat: Infinity, ease: "easeInOut" }}
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 45% 45% at 50% 55%, rgba(224,177,91,0.12), transparent 70%)",
        }}
      />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px"
           style={{ background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.06), transparent)" }} />

      <div className="relative mx-auto max-w-3xl text-center">
        <div className="flex justify-center">
          <SectionLabel index="05" label="Ready?" />
        </div>

        <motion.h2
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="mt-7 text-[52px] font-semibold leading-[1.05] tracking-[-0.025em] text-primary sm:text-[60px]"
        >
          Try it now.
        </motion.h2>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6, ease: "easeOut", delay: 0.2 }}
          className="mt-10 flex justify-center"
        >
          <button
            type="button"
            onClick={onEnter}
            className="group inline-flex items-center gap-3 rounded-full border border-accent/50 bg-accent/10 px-8 py-4 text-[13px] font-medium uppercase tracking-[0.22em] text-accent transition-all hover:border-accent hover:bg-accent/20 hover:tracking-[0.26em] focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/40"
          >
            Enter Lumen
            <ArrowRight
              size={16}
              strokeWidth={1.8}
              className="transition-transform group-hover:translate-x-1"
            />
          </button>
        </motion.div>

        <p className="mt-6 text-[10.5px] font-medium uppercase tracking-[0.2em] text-muted">
          Your documents are waiting.
        </p>
      </div>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════ */
/* Section — Live demo (01)                                         */
/* ═══════════════════════════════════════════════════════════════ */

const DEMO_QUESTION = "How does retrieval stay grounded?";
const DEMO_ANSWER =
  "Every retrieved chunk is rescored by a CrossEncoder; only the top-ranked " +
  "excerpts enter the answer context. The generator is bound by a system " +
  "prompt that bars outside knowledge entirely. [pipeline.pdf, p.4]\n\n" +
  "A confidence label is attached to every response from the average rerank " +
  "score, so weak retrievals are flagged before the user trusts the answer. " +
  "[pipeline.pdf, p.7] [retrieval.pdf, p.2]";

function LiveDemoSection() {
  return (
    <section className="relative px-6 py-24 sm:px-10 sm:py-32">
      <div className="mx-auto max-w-3xl">
        <SectionLabel index="01" label="See it in action" />
        <SectionHeading
          title="A real interaction."
          subtitle="What Lumen actually returns."
        />
        <DemoCard />
      </div>
    </section>
  );
}

function DemoCard() {
  const ref         = useRef<HTMLDivElement>(null);
  const startedRef  = useRef(false);
  const [phase, setPhase] = useState<"idle" | "thinking" | "typing" | "done">("idle");
  const [typed, setTyped] = useState("");

  // Trigger the demo once the card enters the viewport
  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !startedRef.current) {
          startedRef.current = true;
          setPhase("thinking");
          window.setTimeout(() => setPhase("typing"), 1400);
        }
      },
      { threshold: 0.35 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  // Typewriter
  useEffect(() => {
    if (phase !== "typing") return;
    let i = 0;
    const interval = window.setInterval(() => {
      i++;
      setTyped(DEMO_ANSWER.slice(0, i));
      if (i >= DEMO_ANSWER.length) {
        window.clearInterval(interval);
        window.setTimeout(() => setPhase("done"), 600);
      }
    }, 38);
    return () => window.clearInterval(interval);
  }, [phase]);

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className="mt-14 rounded-[14px] border border-line bg-sidebar/60 p-6 backdrop-blur-sm sm:p-8"
    >
      {/* Header strip */}
      <div className="mb-6 flex items-center justify-between border-b border-line pb-4">
        <span className="flex items-center gap-2 text-[10.5px] font-medium uppercase tracking-[0.22em] text-muted">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-ready opacity-60" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-ready" />
          </span>
          Demo · Live preview
        </span>
        <span className="font-mono text-[10.5px] text-muted">2 docs indexed</span>
      </div>

      {/* User message */}
      <div className="flex justify-end gap-3">
        <div className="max-w-[80%] rounded-[14px] bg-elevated px-5 py-3.5 text-[14.5px] leading-[1.55] text-primary">
          {DEMO_QUESTION}
        </div>
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-elevated/80 text-secondary">
          <User size={14} strokeWidth={1.8} />
        </span>
      </div>

      {/* Lumen response */}
      <div className="mt-6 flex gap-3">
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-accent/15 text-accent">
          <Logo size={16} />
        </span>
        <div className="min-w-0 flex-1">
          {phase === "thinking" ? (
            <ThinkingDots />
          ) : phase === "idle" ? (
            <p className="text-[12.5px] uppercase tracking-[0.18em] text-muted">
              Scroll into view to start
            </p>
          ) : (
            <p className="text-[14.5px] leading-[1.7] text-primary">
              {renderWithCitations(typed)}
              {phase === "typing" && (
                <span className="lumen-caret ml-0.5 inline-block h-[16px] w-px translate-y-0.5 bg-primary" />
              )}
            </p>
          )}

          {/* Evidence reveal */}
          <AnimatePresence>
            {phase === "done" && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, ease: "easeOut" }}
                className="mt-5 rounded-[10px] border border-line bg-app/40 p-4"
              >
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5 text-[11.5px] font-medium text-[#4ADE80]">
                    <span className="h-1.5 w-1.5 rounded-full bg-[#4ADE80]" />
                    High confidence
                  </span>
                  <span className="text-[10.5px] font-medium uppercase tracking-[0.12em] text-muted">
                    4 chunks
                  </span>
                </div>
                <p className="mt-3 text-[9.5px] font-medium uppercase tracking-[0.16em] text-muted">
                  Citations
                </p>
                <ul className="mt-1.5 space-y-1 text-[12.5px] text-secondary">
                  <li className="flex items-start gap-2">
                    <span className="mt-px text-accent">›</span>
                    pipeline.pdf (Pages 4, 7)
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="mt-px text-accent">›</span>
                    retrieval.pdf (Page 2)
                  </li>
                </ul>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
}

function ThinkingDots() {
  return (
    <div className="flex items-center gap-1.5 py-1 text-secondary">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{
            duration: 1.2,
            repeat:   Infinity,
            delay:    i * 0.18,
            ease:     "easeInOut",
          }}
          className="h-1.5 w-1.5 rounded-full bg-secondary"
        />
      ))}
      <span className="ml-2 text-[12.5px] uppercase tracking-[0.18em] text-muted">
        Retrieving + reranking
      </span>
    </div>
  );
}

/* Parse and render inline citations like [file.pdf, p.N] as compact chips.
   Matches the in-app behavior: brackets are stripped from the prose and the
   chips cluster at the end of each line / paragraph (deduplicated). */
const CITATION_PATTERN =
  /\[\s*([^\]]+?\.(?:pdf|docx|txt|md))\s*(?:[,\s]+(?:pp?\.?|pages?)?\s*(\d+))?\s*\]/gi;

function renderWithCitations(text: string): ReactNode[] {
  if (!text) return [];
  const clean = stripMarkdown(text);

  // First pass: assign a stable 1-based number per unique citation across
  // the whole answer so chip numbers stay consistent with the evidence list.
  const indexMap = new Map<string, number>();
  let counter    = 0;
  for (const m of clean.matchAll(CITATION_PATTERN)) {
    const key = `${m[1].toLowerCase()}|${m[2] || ""}`;
    if (!indexMap.has(key)) {
      counter++;
      indexMap.set(key, counter);
    }
  }

  const parts: ReactNode[] = [];
  clean.split("\n").forEach((line, lineIdx, lines) => {
    const found: Array<{ idx: number; label: string }> = [];
    const seen  = new Set<number>();
    for (const m of line.matchAll(CITATION_PATTERN)) {
      const key = `${m[1].toLowerCase()}|${m[2] || ""}`;
      const idx = indexMap.get(key)!;
      if (seen.has(idx)) continue;
      seen.add(idx);
      found.push({ idx, label: m[2] ? `${m[1]}, p.${m[2]}` : m[1] });
    }

    const stripped = line
      .replace(CITATION_PATTERN, "")
      .replace(/[ \t]+([.,!?;:])/g, "$1")
      .replace(/[ \t]{2,}/g, " ")
      .replace(/^[ \t]+|[ \t]+$/g, "");

    if (stripped) parts.push(<span key={`t-${lineIdx}`}>{stripped}</span>);
    if (found.length) {
      if (stripped) parts.push(" ");
      found.forEach((f, i) => {
        parts.push(<CitationChip key={`c-${lineIdx}-${i}`} index={f.idx} label={f.label} />);
      });
    }
    if (lineIdx < lines.length - 1) parts.push("\n");
  });
  return parts;
}

function CitationChip({ index, label }: { index: number; label: string }) {
  return (
    <span
      title={label}
      className="mx-0.5 inline-flex h-[18px] min-w-[18px] -translate-y-px items-center justify-center rounded-[5px] border border-accent/40 bg-accent/10 px-1 align-middle text-[10.5px] font-medium leading-none text-accent transition-colors hover:border-accent hover:bg-accent/20"
    >
      {index}
    </span>
  );
}

/* ═══════════════════════════════════════════════════════════════ */
/* Section — FAQ (04)                                               */
/* ═══════════════════════════════════════════════════════════════ */

const FAQ_ITEMS = [
  {
    q: "Why does Lumen run locally?",
    a: "Your documents never leave your machine. Embeddings, retrieval, and generation all run on your hardware through Ollama and Chroma — no cloud calls, no telemetry, no API keys required.",
  },
  {
    q: "Which models does it use?",
    a: "Qwen 2.5 (7B Instruct) for generation and nomic-embed-text for embeddings, both running locally through Ollama. Swap either via OLLAMA_CHAT_MODEL or OLLAMA_EMBEDDING_MODEL — the Models panel in the sidebar reports live status.",
  },
  {
    q: "How are PDFs read?",
    a: "PyMuPDF extracts the layout. Headings, paragraphs, tables, and figure captions are each kept as their own block; tables are converted to markdown so their structure stays intact through retrieval and generation.",
  },
  {
    q: "How is chunking done?",
    a: "PDFs are split along section boundaries detected from the layout pass, not at arbitrary character counts. Each chunk records its section title and page, so retrieved excerpts begin where the meaning begins.",
  },
  {
    q: "What file formats are supported?",
    a: "PDF, DOCX, plain text (TXT), and Markdown (MD). Up to 10 files per session, 200 MB each. Page-level metadata is preserved so citations point to the exact page.",
  },
  {
    q: "How accurate are the citations?",
    a: "Every answer is grounded in retrieved chunks — the model is instructed never to use outside knowledge. The Evidence panel shows the exact excerpts that backed the response, with a High / Medium / Low confidence badge based on retrieval quality. Click a chip in the answer to jump to its evidence card.",
  },
  {
    q: "Can I scope a question to specific files?",
    a: "Yes. Select one or more files in the sidebar and retrieval will be limited to those documents only. Useful when you have many files indexed but only want answers from a subset.",
  },
];

function FAQSection() {
  return (
    <section className="relative px-6 py-24 sm:px-10 sm:py-32">
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-px"
        style={{
          background:
            "linear-gradient(90deg, transparent, rgba(255,255,255,0.06), transparent)",
        }}
      />

      <div className="mx-auto max-w-3xl">
        <SectionLabel index="04" label="FAQ" />
        <SectionHeading title="Common questions." subtitle="Local-first, by design." />

        <div className="mt-12 space-y-2">
          {FAQ_ITEMS.map((item, i) => (
            <FAQItem key={i} question={item.q} answer={item.a} />
          ))}
        </div>

        <InstallTerminal />
      </div>
    </section>
  );
}

const INSTALL_COMMANDS: { command: string; note: string }[] = [
  { command: "ollama pull qwen2.5:7b-instruct", note: "Chat model" },
  { command: "ollama pull nomic-embed-text",    note: "Embeddings" },
];

function InstallTerminal() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ duration: 0.55, ease: "easeOut" }}
      className="mt-10 overflow-hidden rounded-[12px] border border-line bg-app/60 shadow-[0_12px_36px_rgba(0,0,0,0.35)] backdrop-blur-sm"
    >
      {/* Title bar — Windows Terminal style */}
      <div className="flex items-center justify-between gap-3 border-b border-line bg-elevated/40 pl-4 pr-1.5">
        <div className="flex items-center gap-2 py-2.5">
          <Terminal size={12} strokeWidth={1.8} className="text-muted" />
          <span className="font-mono text-[11px] text-muted">PowerShell — lumen</span>
        </div>
        <div className="flex items-center">
          <span className="hidden pr-3 text-[9.5px] font-medium uppercase tracking-[0.18em] text-muted sm:inline">
            Install in two commands
          </span>
          <WindowControl variant="min" />
          <WindowControl variant="max" />
          <WindowControl variant="close" />
        </div>
      </div>

      {/* Commands */}
      <div className="px-5 py-4 font-mono text-[12.5px] leading-[2]">
        {INSTALL_COMMANDS.map(({ command, note }) => (
          <TerminalLine key={command} command={command} note={note} />
        ))}
      </div>
    </motion.div>
  );
}

function WindowControl({ variant }: { variant: "min" | "max" | "close" }) {
  // Inert chrome — purely decorative, not interactive.
  return (
    <span
      aria-hidden
      className={`grid h-7 w-9 cursor-default place-items-center text-muted transition-colors ${
        variant === "close" ? "hover:bg-[#e81123]/80 hover:text-primary" : "hover:bg-hover"
      }`}
    >
      {variant === "min" && <span className="h-px w-2.5 bg-current" />}
      {variant === "max" && <span className="h-2 w-2 border border-current" />}
      {variant === "close" && (
        <svg viewBox="0 0 10 10" className="h-2.5 w-2.5" aria-hidden>
          <path d="M0 0 L10 10 M10 0 L0 10" stroke="currentColor" strokeWidth="1" />
        </svg>
      )}
    </span>
  );
}

function TerminalLine({ command, note }: { command: string; note: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {}
  };

  return (
    <motion.div
      whileHover={{ x: 2 }}
      transition={{ duration: 0.15 }}
      className="group -mx-2 flex items-center gap-2.5 rounded px-2 py-0.5 transition-colors hover:bg-hover/40"
    >
      <span className="select-none text-accent/70">$</span>
      <code className="min-w-0 flex-1 truncate text-primary">{command}</code>
      <span className="hidden shrink-0 text-[9px] font-medium uppercase tracking-[0.16em] text-muted sm:inline">
        {note}
      </span>
      <button
        type="button"
        onClick={handleCopy}
        title={copied ? "Copied!" : "Copy command"}
        aria-label={copied ? "Copied" : `Copy: ${command}`}
        className="shrink-0 rounded p-1 text-muted transition-colors hover:bg-hover hover:text-primary focus:opacity-100 focus:outline-none focus-visible:ring-1 focus-visible:ring-accent/40"
      >
        <AnimatePresence mode="wait" initial={false}>
          {copied ? (
            <motion.span
              key="check"
              initial={{ scale: 0.6, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.6, opacity: 0 }}
              transition={{ duration: 0.18, ease: "easeOut" }}
              className="block text-accent"
            >
              <Check size={13} strokeWidth={2} />
            </motion.span>
          ) : (
            <motion.span
              key="copy"
              initial={{ scale: 0.6, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.6, opacity: 0 }}
              transition={{ duration: 0.18, ease: "easeOut" }}
              className="block"
            >
              <Copy size={13} strokeWidth={1.8} />
            </motion.span>
          )}
        </AnimatePresence>
      </button>
    </motion.div>
  );
}

function FAQItem({ question, answer }: { question: string; answer: string }) {
  const [open, setOpen] = useState(false);
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="overflow-hidden rounded-[12px] border border-line bg-sidebar/40 backdrop-blur-sm transition-colors hover:border-[rgba(255,255,255,0.10)]"
    >
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left transition-colors hover:bg-hover/30 focus:outline-none focus-visible:bg-hover/30"
      >
        <span className="text-[14px] font-medium text-primary">{question}</span>
        <motion.span
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.25, ease: "easeOut" }}
          className="shrink-0 text-secondary"
        >
          <ChevronDown size={16} strokeWidth={1.8} />
        </motion.span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.28, ease: "easeOut" }}
            className="overflow-hidden"
          >
            <p className="px-5 pb-5 text-[13px] leading-[1.7] text-secondary">
              {answer}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
