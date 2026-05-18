# RAG eval harness

Small offline test suite for measuring answer + retrieval quality of the
RAG pipeline. No new Python dependencies — uses what is already in
`requirements.txt`.

## Layout

```
eval/
├── fixtures/         # small reference docs (markdown)
├── golden/           # JSONL files: one test case per line
├── metrics.py        # deterministic metric functions
├── run.py            # CLI entrypoint
├── compare.py        # diff two runs
└── results/          # per-run output (created on first run)
```

## How to run

From the project root, with the venv activated:

```powershell
# Full run (retrieval + generation), all 18 cases
venv\Scripts\python -m eval.run

# Faster: skip generation, measure retrieval only
venv\Scripts\python -m eval.run --retrieval-only

# Filter by tag or mode
venv\Scripts\python -m eval.run --filter tags=exhaustive
venv\Scripts\python -m eval.run --filter answer_mode=standard

# Custom golden file
venv\Scripts\python -m eval.run --golden eval/golden/set_v1.jsonl

# Custom output path
venv\Scripts\python -m eval.run --out eval/results/baseline.json
```

Ollama must be running and the configured chat + embedding models
(`qwen2.5:7b-instruct`, `nomic-embed-text` by default) must be available.

## How to compare two runs

```powershell
venv\Scripts\python -m eval.compare eval/results/baseline.json eval/results/with_rrf.json
```

Prints per-metric deltas, then lists cases that regressed (was passing,
now failing) and cases that newly pass.

## Metrics (deterministic, free, fast)

| Metric              | What it measures                                                     | Applies to                |
|---------------------|----------------------------------------------------------------------|---------------------------|
| `source_recall`     | Fraction of `expected_sources` that appeared in retrieval            | cases with expected_sources |
| `page_recall`       | Fraction of `expected_pages` that appeared in retrieval              | cases with expected_pages |
| `must_contain`      | Fraction of required substrings present in the answer                | cases with must_contain   |
| `must_not_contain`  | 1.0 if no forbidden substring appears, else 0.0                      | every case with an answer |
| `fallback_correct`  | 1.0 iff the fallback flag matches `expects_fallback`                 | every case                |
| `citation_present`  | 1.0 if the answer contains a `[file, p.N]` marker                    | exhaustive cases only     |

Metrics return `None` when not applicable (excluded from the mean).

## Golden case schema

```json
{
  "id": "unique_case_id",
  "question": "What is ...?",
  "documents": ["eval/fixtures/handbook.md"],
  "answer_mode": "standard",
  "expected_sources": ["handbook.md"],
  "expected_pages": [1],
  "must_contain": ["March 15"],
  "must_not_contain": ["could not find"],
  "expects_fallback": false,
  "tags": ["lookup", "easy"]
}
```

All fields except `id`, `question`, `documents` are optional.

## Side effects

- Indexes fixture files into `chroma_db/` (the same store the app uses).
  Collections are content-hashed, so they will not collide with your real
  documents. They can be deleted manually if `chroma_db/` grows too large.
- `eval/results/*.json` accumulates one file per run. Safe to delete.
- The runner calls `rag_service.remove_all_documents()` between cases, so
  do not run eval while the FastAPI dev server is serving real users.

## What this does not cover

- LLM-as-judge scoring (faithfulness, answer relevancy, context
  precision). Planned for a future `--judge` flag.
- Latency / cost metrics. Only correctness is measured today.
- Anything beyond the 18 hand-written cases. Extend `set_v1.jsonl` (or
  add new files under `golden/`) as you discover failure patterns.
