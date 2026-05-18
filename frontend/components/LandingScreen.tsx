"use client";

import { useCallback, useEffect, useRef } from "react";
import type { MouseEvent as ReactMouseEvent } from "react";
import {
  motion,
  useAnimationControls,
  useMotionValue,
  useScroll,
  useSpring,
  useTransform,
} from "framer-motion";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Logo } from "@/components/Logo";
import { LandingShowcase } from "@/components/LandingShowcase";

type LandingScreenProps = {
  onEnter: () => void;
};

export function LandingScreen({ onEnter }: LandingScreenProps) {
  const controls     = useAnimationControls();
  const committedRef = useRef(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const featuresRef  = useRef<HTMLDivElement>(null);

  /* ── Scroll progress ────────────────────────────────── */
  const { scrollYProgress } = useScroll({ container: containerRef });
  const progressScaleX      = useSpring(scrollYProgress, {
    stiffness: 130,
    damping:    20,
    mass:        0.4,
  });

  /* ── Pointer-driven 3D tilt (hero only) ─────────────── */
  const pointerX = useMotionValue(0);
  const pointerY = useMotionValue(0);
  const spring   = { stiffness: 120, damping: 18, mass: 0.6 };
  const rotateX  = useSpring(useTransform(pointerY, [-0.5, 0.5], [6,  -6]), spring);
  const rotateY  = useSpring(useTransform(pointerX, [-0.5, 0.5], [-6,  6]), spring);
  const driftX   = useSpring(useTransform(pointerX, [-0.5, 0.5], [-10, 10]), spring);
  const driftY   = useSpring(useTransform(pointerY, [-0.5, 0.5], [-8,  8]),  spring);

  /* ── Commit (slide-up exit) ─────────────────────────── */
  const commit = useCallback(async () => {
    if (committedRef.current) return;
    committedRef.current = true;
    await controls.start({
      y: "-100vh",
      transition: { duration: 0.75, ease: [0.32, 0.72, 0, 1] },
    });
    onEnter();
  }, [controls, onEnter]);

  const scrollToFeatures = () => {
    featuresRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  /* ── Keyboard: ↑ / Space commit (only at top, no button focused) ─ */
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const container = containerRef.current;
      if (container && container.scrollTop > 80) return;
      const active = document.activeElement as HTMLElement | null;
      if (active && (active.tagName === "BUTTON" || active.tagName === "A")) return;
      if (e.key === "ArrowUp" || e.key === " " || e.code === "Space") {
        e.preventDefault();
        commit();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [commit]);

  /* ── Pointer tracking ───────────────────────────────── */
  const handlePointerMove = (e: ReactMouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    pointerX.set((e.clientX - rect.left) / rect.width  - 0.5);
    pointerY.set((e.clientY - rect.top)  / rect.height - 0.5);
  };
  const handlePointerLeave = () => {
    pointerX.set(0);
    pointerY.set(0);
  };

  return (
    <motion.div
      animate={controls}
      className="fixed inset-0 z-50 bg-app text-primary"
    >
      {/* ── Scroll progress bar ─────────────────────────── */}
      <motion.div
        style={{ scaleX: progressScaleX, transformOrigin: "0% 50%" }}
        className="pointer-events-none absolute left-0 right-0 top-0 z-30 h-[2px] bg-accent shadow-[0_0_10px_rgba(224,177,91,0.6)]"
      />

      {/* ── Scrollable inner container ──────────────────── */}
      <div
        ref={containerRef}
        className="h-full overflow-y-auto overflow-x-hidden"
      >
        {/* ═══════════════════════════════════════════════ */}
        {/* HERO SECTION                                    */}
        {/* ═══════════════════════════════════════════════ */}
        <section
          onMouseMove={handlePointerMove}
          onMouseLeave={handlePointerLeave}
          className="relative flex h-screen select-none flex-col overflow-hidden"
        >
          <Constellation />

          {/* Backdrop glow layers */}
          <div className="pointer-events-none absolute inset-0">
            <motion.div
              animate={{ opacity: [0.55, 1, 0.55], scale: [0.96, 1.04, 0.96] }}
              transition={{ duration: 4.2, repeat: Infinity, ease: "easeInOut" }}
              className="absolute inset-0"
              style={{
                background:
                  "radial-gradient(ellipse 60% 50% at 50% 40%, rgba(224,177,91,0.14), transparent 70%)",
              }}
            />
            <motion.div
              animate={{ opacity: [0.3, 0.7, 0.3] }}
              transition={{ duration: 2.6, repeat: Infinity, ease: "easeInOut", delay: 0.4 }}
              className="absolute inset-0"
              style={{
                background:
                  "radial-gradient(ellipse 30% 28% at 50% 40%, rgba(240,196,106,0.18), transparent 75%)",
              }}
            />
            <div
              className="absolute inset-x-0 top-0 h-px"
              style={{
                background:
                  "linear-gradient(90deg, transparent, rgba(255,255,255,0.06), transparent)",
              }}
            />
            <div
              className="absolute inset-x-0 bottom-0 h-px"
              style={{
                background:
                  "linear-gradient(90deg, transparent, rgba(255,255,255,0.06), transparent)",
              }}
            />
          </div>

          {/* Top status row */}
          <div className="relative z-10 flex shrink-0 items-center justify-between px-8 py-6 text-[10.5px] font-medium uppercase tracking-[0.18em] text-muted">
            <span className="flex items-center gap-2">
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-ready opacity-60" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-ready" />
              </span>
              Local · Online
            </span>
            <span className="tracking-[0.22em]">v1.0</span>
          </div>

          {/* Hero block with 3D tilt */}
          <div
            className="relative z-10 flex flex-1 items-center justify-center px-8"
            style={{ perspective: 1400 }}
          >
            <motion.div
              style={{
                rotateX,
                rotateY,
                x: driftX,
                y: driftY,
                transformStyle: "preserve-3d",
              }}
              className="flex flex-col items-center text-center"
            >
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, ease: "easeOut", delay: 0.05 }}
                style={{
                  transform: "translateZ(40px)",
                  filter:    "drop-shadow(0 6px 24px rgba(224,177,91,0.35))",
                }}
              >
                <Logo size={220} />
              </motion.div>

              <motion.h1
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, ease: "easeOut", delay: 0.15 }}
                className="mt-8 text-[44px] font-semibold uppercase leading-none tracking-[0.18em] text-primary"
                style={{ transform: "translateZ(30px)" }}
              >
                Lumen
              </motion.h1>

              <motion.div
                initial={{ opacity: 0, scaleX: 0 }}
                animate={{ opacity: 1, scaleX: 1 }}
                transition={{ duration: 0.5, ease: "easeOut", delay: 0.3 }}
                className="mt-6 h-px w-12 origin-center bg-accent/50"
              />

              <motion.p
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, ease: "easeOut", delay: 0.4 }}
                className="mt-6 text-[11px] font-medium uppercase tracking-[0.24em] text-accent"
                style={{ transform: "translateZ(20px)" }}
              >
                Retrieval-Augmented Generation
              </motion.p>

              <motion.p
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, ease: "easeOut", delay: 0.5 }}
                className="mt-5 max-w-[440px] text-[14px] leading-[1.65] text-secondary"
                style={{ transform: "translateZ(12px)" }}
              >
                Ask anything. Cite everything.
              </motion.p>
            </motion.div>
          </div>

          {/* Bottom CTAs */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: "easeOut", delay: 0.75 }}
            className="relative z-10 flex shrink-0 flex-col items-center pb-10"
          >
            <div className="flex items-center gap-3">
              <button
                type="button"
                aria-label="Enter Lumen"
                onClick={() => commit()}
                className="group flex flex-col items-center gap-2 rounded-md px-6 py-3 text-secondary transition-colors hover:text-primary focus:outline-none focus-visible:text-primary"
              >
                <motion.div
                  animate={{ y: [0, -6, 0] }}
                  transition={{ duration: 1.7, repeat: Infinity, ease: "easeInOut" }}
                  className="text-accent transition-colors group-hover:text-accent-hover"
                >
                  <ChevronUp size={22} strokeWidth={2} />
                </motion.div>
                <span className="text-[10.5px] font-medium uppercase tracking-[0.24em]">
                  Enter
                </span>
              </button>

              <span className="h-10 w-px bg-line" />

              <button
                type="button"
                aria-label="Scroll to explore features"
                onClick={scrollToFeatures}
                className="group flex flex-col items-center gap-2 rounded-md px-6 py-3 text-secondary transition-colors hover:text-primary focus:outline-none focus-visible:text-primary"
              >
                <motion.div
                  animate={{ y: [0, 6, 0] }}
                  transition={{ duration: 1.7, repeat: Infinity, ease: "easeInOut", delay: 0.85 }}
                  className="text-secondary transition-colors group-hover:text-accent"
                >
                  <ChevronDown size={20} strokeWidth={2} />
                </motion.div>
                <span className="text-[10.5px] font-medium uppercase tracking-[0.24em]">
                  Explore
                </span>
              </button>
            </div>

            <div className="mt-4 flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.18em] text-muted">
              <Kbd>↑</Kbd>
              <span className="opacity-70">or</span>
              <Kbd>Space</Kbd>
              <span className="ml-2 opacity-70">to enter</span>
            </div>

            <div className="mt-5 h-[3px] w-24 rounded-full bg-line" />
          </motion.div>
        </section>

        {/* ═══════════════════════════════════════════════ */}
        {/* SHOWCASE                                        */}
        {/* ═══════════════════════════════════════════════ */}
        <div ref={featuresRef}>
          <LandingShowcase onEnter={commit} />
        </div>
      </div>
    </motion.div>
  );
}

/* ── Kbd chip ─────────────────────────────────────────── */

function Kbd({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="inline-flex h-[22px] min-w-[22px] items-center justify-center rounded-[5px] border border-line bg-elevated/60 px-1.5 text-[11px] font-medium normal-case tracking-normal text-secondary shadow-[inset_0_-1px_0_rgba(0,0,0,0.4)]">
      {children}
    </kbd>
  );
}

/* ── Constellation canvas ─────────────────────────────── */

function Constellation() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let width  = 0;
    let height = 0;
    let dpr    = 1;
    type Node = { x: number; y: number; vx: number; vy: number; r: number };
    let nodes: Node[] = [];

    const resize = () => {
      dpr    = window.devicePixelRatio || 1;
      width  = canvas.clientWidth;
      height = canvas.clientHeight;
      canvas.width  = Math.floor(width  * dpr);
      canvas.height = Math.floor(height * dpr);
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.scale(dpr, dpr);
    };

    const seed = () => {
      const count = Math.max(36, Math.min(72, Math.floor((width * height) / 22000)));
      nodes = Array.from({ length: count }).map(() => ({
        x:  Math.random() * width,
        y:  Math.random() * height,
        vx: (Math.random() - 0.5) * 0.18,
        vy: (Math.random() - 0.5) * 0.18,
        r:  0.7 + Math.random() * 1.1,
      }));
    };

    resize();
    seed();

    const CONNECTION_DIST  = 140;
    const CONNECTION_DIST2 = CONNECTION_DIST * CONNECTION_DIST;
    let rafId = 0;

    const tick = () => {
      ctx.clearRect(0, 0, width, height);

      for (const n of nodes) {
        n.x += n.vx;
        n.y += n.vy;
        if (n.x <= 0 || n.x >= width)  n.vx = -n.vx;
        if (n.y <= 0 || n.y >= height) n.vy = -n.vy;
      }

      ctx.lineWidth = 0.5;
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a  = nodes[i];
          const b  = nodes[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const d2 = dx * dx + dy * dy;
          if (d2 < CONNECTION_DIST2) {
            const dist  = Math.sqrt(d2);
            const alpha = (1 - dist / CONNECTION_DIST) * 0.18;
            ctx.strokeStyle = `rgba(224, 177, 91, ${alpha})`;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
      }

      ctx.fillStyle = "rgba(224, 177, 91, 0.55)";
      for (const n of nodes) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx.fill();
      }

      rafId = requestAnimationFrame(tick);
    };

    tick();

    const onResize = () => {
      resize();
      seed();
    };
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(rafId);
      window.removeEventListener("resize", onResize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      className="pointer-events-none absolute inset-0 h-full w-full"
      style={{
        maskImage:
          "radial-gradient(ellipse 75% 65% at 50% 50%, transparent 0%, transparent 22%, black 80%)",
        WebkitMaskImage:
          "radial-gradient(ellipse 75% 65% at 50% 50%, transparent 0%, transparent 22%, black 80%)",
      }}
    />
  );
}
