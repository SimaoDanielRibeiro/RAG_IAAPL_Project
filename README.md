<<<<<<< HEAD
# Document Q&A RAG App

A simple Streamlit application that lets you upload one or more documents and ask questions about their contents using a local Retrieval-Augmented Generation (RAG) pipeline.

## Features

- Upload one or more documents through Streamlit
- Support `.pdf`, `.docx`, `.txt`, and `.md`
- Support up to 200 MB per file
- Save uploaded files into `data/`
- Extract document text from supported file types
- Split content into smaller chunks with `RecursiveCharacterTextSplitter`
- Store rich metadata for each chunk
- Generate embeddings with Ollama
- Store vectors persistently in ChromaDB
- Reuse an existing Chroma collection for the same file set
- Expand each question into multiple retrieval queries
- Retrieve with MMR and neighbor chunk expansion
- Rerank chunks before final answer generation
- Answer only from retrieved document context
- Add deterministic file and page citations to answers
- Show retrieved chunks, page numbers, confidence, and retrieval score
- Show generated query variations for transparency
- Generate a retrieval-based per-file summary for demos
- Detect scanned PDFs that need OCR
- Reuse indexing metadata from `data/index_manifest.json`
- Cache the pipeline for faster Streamlit reruns

## Project Structure

```text
project/
|-- app.py
|-- requirements.txt
|-- .env
|-- .env.example
|-- README.md
|-- data/
|-- chroma_db/
`-- src/
    |-- __init__.py
    |-- document_loaders.py
    |-- prompts.py
    |-- rag_pipeline.py
    |-- ui.py
    `-- utils.py
```

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com/)

## Setup

### 1. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

These versions are pinned to make the project easier to reproduce during evaluation.

### 3. Install and start Ollama

Install Ollama from [https://ollama.com/download](https://ollama.com/download), then pull the required models:

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```

### 4. Optional model alternatives

If `llama3.2` is too slow or too large:

- `llama3.2:3b`
- `phi3`
- `mistral`
- `gemma:2b`

If `nomic-embed-text` is not available or does not work well:

- `mxbai-embed-large`
- `all-minilm`
- `bge-large`

To change models, copy `.env.example` to `.env` and edit the values:

```bash
cp .env.example .env
```

Example:

```env
OLLAMA_CHAT_MODEL=llama3.2
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

## Run the App

```bash
streamlit run app.py
```

## How It Works

1. Upload one or more documents in the Streamlit interface.
2. The files are saved into `data/`.
3. The app loads and extracts text from each file.
4. The text is split into chunks using:

```python
RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
    separators=["\n\n", "\n", ". ", " "]
)
```

5. Each chunk stores metadata such as page number, source file, chunk index, chunk size, previous chunk index, next chunk index, and an optional section title.
6. Ollama embeddings are created for each chunk.
7. Chunks from all uploaded documents are stored together in a persistent Chroma database under `chroma_db/`.
8. When the user asks a question, `MultiQueryRetriever` expands it into multiple similar queries.
9. Retrieval uses MMR, adds neighboring chunks, reranks the candidates, and keeps only the strongest chunks.
10. If the remaining evidence is too weak, the app returns the fallback answer instead of guessing.
11. The app answers using only the retrieved context from the uploaded documents.

## Interface Notes

- `Generate document summary` creates a separate retrieval-based summary for each uploaded file.
- `Clear current chat` resets the current chat session so you can test another file set.
- `Generated search queries` shows the original question plus the rewritten retrieval queries.
- `Retrieved chunks and snippets` shows short previews first, with file names and page numbers for each chunk.

## Evaluation Ideas

- Ask 5 to 10 questions whose answers you already know from the uploaded files.
- Check whether the answer is correct, grounded in the cited pages, and not hallucinated.
- Test at least one impossible question to confirm the fallback message appears.
- Try one scanned PDF to show that the app reports when OCR is needed.

## Fallback Behavior

If the answer cannot be found in the retrieved document context, the assistant responds with:

```text
I could not find that information in the uploaded document.
```

## Notes

- This app is designed to stay minimal and professional for a university project.
- Everything runs locally through Streamlit, Ollama, and ChromaDB.
- Each uploaded file can be up to 200 MB. Very large multi-file uploads may be slower to index.
- Chroma collections are reused when the same PDF content is uploaded again.
- Indexing metadata is stored in `data/index_manifest.json` for easier reuse and debugging.
- Streamlit caches the pipeline resource so reruns are faster after the first load.
- Logging is enabled to help with debugging.
=======
# RAG_IAAPL_Project
>>>>>>> 887299a071f7f5503af0abb63bccbfa83b8f34c3
