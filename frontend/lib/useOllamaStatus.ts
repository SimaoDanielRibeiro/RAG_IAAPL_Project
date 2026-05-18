"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { HealthResponse } from "@/types";

const POLL_INTERVAL_MS = 8000;

export type OllamaStatus = {
  health: HealthResponse | null;
  error: string | null;
  loading: boolean;
  lastCheckedAt: Date | null;
  refresh: () => Promise<void>;
};

/**
 * Polls /api/health to surface whether the backend can talk to Ollama and
 * which chat / embedding models are configured. A successful response means
 * Ollama is reachable AND both models are pullable by the backend; a failure
 * means either the backend is down or Ollama is not responding.
 */
export function useOllamaStatus(): OllamaStatus {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastCheckedAt, setLastCheckedAt] = useState<Date | null>(null);
  const mounted = useRef(true);

  const refresh = useCallback(async () => {
    try {
      const result = await api.health();
      if (!mounted.current) return;
      setHealth(result);
      setError(null);
    } catch (e) {
      if (!mounted.current) return;
      setHealth(null);
      setError(e instanceof Error ? e.message : "Cannot reach backend");
    } finally {
      if (mounted.current) {
        setLoading(false);
        setLastCheckedAt(new Date());
      }
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    refresh();
    const interval = setInterval(refresh, POLL_INTERVAL_MS);
    return () => {
      mounted.current = false;
      clearInterval(interval);
    };
  }, [refresh]);

  return { health, error, loading, lastCheckedAt, refresh };
}
