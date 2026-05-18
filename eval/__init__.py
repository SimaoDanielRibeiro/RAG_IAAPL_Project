"""Offline evaluation harness for the RAG pipeline.

Loads a golden set of questions, runs them through the live RAG service,
scores deterministic metrics (source recall, must-contain, fallback
correctness, citation presence, ...), and saves results for comparison.

Entry points:
    python -m eval.run       — run the golden set
    python -m eval.compare   — diff two saved runs
"""
