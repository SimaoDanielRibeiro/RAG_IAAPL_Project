"""Streamlit UI for the document RAG app."""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.rag_pipeline import PDFRAGPipeline
from src.utils import combined_files_sha256, configure_logging


load_dotenv()
LOGGER = configure_logging()

DEFAULT_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "llama3.2:3b")
DEFAULT_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
MAX_FILE_UPLOAD_SIZE = 200 * 1024 * 1024
SOFT_TOTAL_UPLOAD_WARNING_SIZE = 500 * 1024 * 1024
LEFT_PANEL_HEIGHT = 920
RIGHT_PANEL_HEIGHT = 920
CHAT_MESSAGES_HEIGHT = 660


def initialize_session_state() -> None:
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("vectorstore", None)
    st.session_state.setdefault("pdf_names", [])
    st.session_state.setdefault("pdf_hash", None)
    st.session_state.setdefault("last_sources", [])
    st.session_state.setdefault("last_result", None)
    st.session_state.setdefault("summary_result", None)
    st.session_state.setdefault("summary_minimized", False)
    st.session_state.setdefault("answer_mode", "Standard Q&A")


def apply_app_styles() -> None:
    st.markdown(
        """
<style>
    .block-container {
        max-width: none;
        padding-top: 3.1rem;
        padding-bottom: 1rem;
        padding-left: 1.1rem;
        padding-right: 1.1rem;
    }
    .app-title {
        font-size: 2.15rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
        text-align: center;
        color: #fff7f7;
        letter-spacing: -0.02em;
    }
    .app-subtitle {
        color: #a7afbf;
        font-size: 0.98rem;
        margin-bottom: 1.35rem;
        text-align: center;
    }
    .panel-heading {
        font-size: 1.35rem;
        font-weight: 700;
        margin-bottom: 0.45rem;
        color: #fff5f5;
    }
    .panel-text {
        color: #f0b4b4;
        font-size: 0.93rem;
        line-height: 1.5;
        margin-bottom: 1.05rem;
    }
    .meta-line {
        color: #f3c1c1;
        font-size: 0.92rem;
        line-height: 1.6;
        margin-bottom: 1rem;
    }
    .section-label {
        color: #ffffff;
        font-size: 1rem;
        font-weight: 600;
        margin-top: 0.3rem;
        margin-bottom: 0.55rem;
    }
    .summary-wrap {
        border: 1.5px solid rgba(239, 68, 68, 0.65);
        border-radius: 14px;
        padding: 0.85rem 0.95rem;
        margin-bottom: 1rem;
        background: rgba(127, 29, 29, 0.10);
    }
    div[data-testid="stVerticalBlock"] > div[data-testid="stContainer"][data-border="true"] {
        background: linear-gradient(180deg, rgba(30, 18, 20, 0.95), rgba(20, 22, 28, 0.95));
        border: 2px solid #ef4444;
        border-radius: 18px;
        box-shadow: 0 16px 34px rgba(0, 0, 0, 0.28);
        overflow: hidden;
    }
    div[data-testid="stVerticalBlock"] > div[data-testid="stContainer"][data-border="true"] > div {
        padding: 0.15rem 0.15rem 0.25rem 0.15rem;
    }
    div[data-testid="stVerticalBlock"] div[data-testid="stContainer"] textarea,
    div[data-testid="stVerticalBlock"] div[data-testid="stContainer"] input {
        border-radius: 12px;
    }
    div[data-testid="stFileUploader"] section {
        border: 1.5px dashed rgba(248, 113, 113, 0.7);
        border-radius: 16px;
        background: rgba(127, 29, 29, 0.08);
    }
    div[data-testid="stChatInput"] textarea,
    div[data-testid="stChatInput"] input {
        border: 1.5px solid rgba(248, 113, 113, 0.65) !important;
        background: rgba(24, 24, 30, 0.95) !important;
    }
    .stButton > button {
        border: 1px solid rgba(248, 113, 113, 0.72);
        border-radius: 12px;
        background: linear-gradient(180deg, rgba(38, 22, 24, 0.98), rgba(28, 24, 28, 0.98));
        color: #fff5f5;
        padding-top: 0.55rem;
        padding-bottom: 0.55rem;
    }
    .stButton > button:hover {
        border-color: rgba(252, 165, 165, 0.92);
        color: #ffffff;
        box-shadow: 0 0 0 1px rgba(248, 113, 113, 0.28);
    }
    .stCaption {
        color: #c9a7a7;
    }
    hr {
        border-color: rgba(239, 68, 68, 0.22);
    }
</style>
""",
        unsafe_allow_html=True,
    )


@st.cache_resource(show_spinner=False)
def get_pipeline(chat_model: str, embedding_model: str) -> PDFRAGPipeline:
    return PDFRAGPipeline(
        data_dir=Path("data"),
        persist_dir=Path("chroma_db"),
        chat_model=chat_model,
        embedding_model=embedding_model,
        logger=LOGGER,
    )


def reset_current_document() -> None:
    st.session_state["messages"] = []
    st.session_state["last_sources"] = []
    st.session_state["last_result"] = None
    st.session_state["summary_result"] = None
    st.session_state["summary_minimized"] = False


def handle_upload(pipeline: PDFRAGPipeline) -> None:
    uploaded_files = st.file_uploader(
        "Upload one or more files",
        type=["pdf", "docx", "txt", "md"],
        accept_multiple_files=True,
        help="Supported formats: PDF, DOCX, TXT, and Markdown. Each file can be up to 200 MB.",
    )
    if not uploaded_files:
        return

    file_payloads = [(uploaded_file.name, uploaded_file.getvalue()) for uploaded_file in uploaded_files]
    total_size = sum(len(file_bytes) for _, file_bytes in file_payloads)
    oversized_files = [
        file_name for file_name, file_bytes in file_payloads if len(file_bytes) > MAX_FILE_UPLOAD_SIZE
    ]
    if oversized_files:
        st.error(
            "Each file must be 200 MB or smaller. These files are too large: "
            + ", ".join(f"'{file_name}'" for file_name in oversized_files)
            + "."
        )
        return

    if total_size > SOFT_TOTAL_UPLOAD_WARNING_SIZE:
        st.warning(
            f"You uploaded {total_size / (1024 * 1024):.2f} MB in total. "
            "This is allowed, but indexing may be slower on smaller machines."
        )

    file_hash = combined_files_sha256(file_payloads)
    file_names = [file_name for file_name, _ in file_payloads]
    same_document = (
        st.session_state.get("pdf_hash") == file_hash
        and st.session_state.get("vectorstore") is not None
    )
    if same_document:
        st.success("These files are already indexed and ready for questions.")
        return

    try:
        with st.spinner("Saving and indexing files..."):
            saved_paths = pipeline.save_uploaded_documents(file_payloads)
            vectorstore = pipeline.index_documents(saved_paths, file_hash)
    except Exception as error:
        LOGGER.exception("Failed to process uploaded files")
        st.error(f"Could not process the uploaded files: {error}")
        return

    st.session_state["vectorstore"] = vectorstore
    st.session_state["pdf_names"] = file_names
    st.session_state["pdf_hash"] = file_hash
    st.session_state["messages"] = []
    st.session_state["last_sources"] = []
    st.session_state["last_result"] = None
    st.session_state["summary_result"] = None
    st.session_state["summary_minimized"] = False
    st.success(
        f"Uploaded and indexed {len(file_names)} file(s) successfully "
        f"({total_size / (1024 * 1024):.2f} MB total)."
    )


def render_left_panel(pipeline: PDFRAGPipeline) -> None:
    with st.container(border=True, height=LEFT_PANEL_HEIGHT):
        st.markdown('<div class="panel-heading">Documents</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="panel-text">Upload documents, review the active file set, and keep the local RAG workspace organized.</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
<div class="meta-line">
<strong>Chat model:</strong> {DEFAULT_CHAT_MODEL}<br>
<strong>Embedding model:</strong> {DEFAULT_EMBEDDING_MODEL}
</div>
""",
            unsafe_allow_html=True,
        )
        st.markdown('<div class="section-label">Upload Files</div>', unsafe_allow_html=True)
        handle_upload(pipeline)

        current_files = st.session_state.get("pdf_names", [])
        st.markdown('<div class="section-label">Active Files</div>', unsafe_allow_html=True)
        if current_files and st.session_state.get("vectorstore") is not None:
            for file_name in current_files:
                st.write(f"- `{file_name}`")
        else:
            st.caption("No indexed files yet.")


def render_summary_panel() -> None:
    summary_result = st.session_state.get("summary_result")
    if not summary_result:
        return

    header1, header2 = st.columns([0.9, 0.1])
    with header1:
        st.markdown("### Summary")
    with header2:
        button_label = "^" if not st.session_state.get("summary_minimized") else "v"
        if st.button(button_label, use_container_width=True):
            st.session_state["summary_minimized"] = not st.session_state["summary_minimized"]

    if st.session_state.get("summary_minimized"):
        return

    st.markdown('<div class="summary-wrap">', unsafe_allow_html=True)
    for item in summary_result.get("summaries", []):
        st.markdown(f"**{item['file_name']}**")
        st.markdown(item["summary"])
        pages = item.get("pages", [])
        if pages:
            st.caption(f"Summary pages: {', '.join(str(page) for page in pages)}")
        st.divider()
    st.markdown("</div>", unsafe_allow_html=True)


def render_chat_actions(pipeline: PDFRAGPipeline) -> None:
    current_files = st.session_state.get("pdf_names", [])
    if current_files and st.session_state.get("vectorstore") is not None:
        st.caption(f"Searching across: {', '.join(f'`{file_name}`' for file_name in current_files)}")

    mode_col, col1, col2 = st.columns([0.9, 1, 1])
    with mode_col:
        st.selectbox(
            "Answer mode",
            options=["Standard Q&A", "Exhaustive extraction"],
            key="answer_mode",
            help="Use Standard Q&A for concise answers. Use Exhaustive extraction for broader requests like 'list all' or 'show everything'.",
        )
    with col1:
        if st.button("Generate document summary", use_container_width=True):
            if not current_files or st.session_state.get("vectorstore") is None:
                st.info("Upload files first.")
            else:
                try:
                    with st.spinner("Summarizing file set..."):
                        summary_result = pipeline.summarize_documents(
                            st.session_state["vectorstore"],
                            current_files,
                        )
                except Exception as error:
                    LOGGER.exception("Failed to summarize document")
                    st.error(f"Could not summarize the document: {error}")
                else:
                    st.session_state["summary_result"] = summary_result
                    st.session_state["summary_minimized"] = False
    with col2:
        if st.button("Clear current chat", use_container_width=True):
            reset_current_document()


def render_message_history(messages_placeholder: st.delta_generator.DeltaGenerator, height: int) -> None:
    with messages_placeholder.container(height=height, border=False):
        for message in st.session_state["messages"]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if message["role"] != "assistant":
                    continue

                meta = message.get("meta")
                if not meta:
                    continue

                pages = meta.get("pages", [])
                sources = meta.get("sources", [])
                confidence = meta.get("confidence", "Low")
                chunks_used = meta.get("chunks_used", 0)
                average_score = meta.get("average_score")
                queries = meta.get("queries", [])
                documents = meta.get("documents", [])
                retrieval_question = meta.get("retrieval_question")
                answer_mode = meta.get("answer_mode")

                detail_parts = []
                if answer_mode:
                    mode_label = "Exhaustive extraction" if answer_mode == "exhaustive" else "Standard Q&A"
                    detail_parts.append(f"Mode: {mode_label}")
                detail_parts.extend([f"Confidence: {confidence}", f"Chunks used: {chunks_used}"])
                if sources:
                    detail_parts.append(f"Files: {', '.join(sources)}")
                if pages:
                    detail_parts.append(f"Pages: {', '.join(str(page) for page in pages)}")
                if average_score is not None:
                    detail_parts.append(f"Average retrieval score: {average_score}/10")
                st.caption(" | ".join(detail_parts))

                if retrieval_question and retrieval_question.strip() != message.get("question", "").strip():
                    with st.expander("Retrieval question used", expanded=False):
                        st.markdown(retrieval_question)

                if queries:
                    with st.expander("Generated search queries", expanded=False):
                        for index, query in enumerate(queries, start=1):
                            label = "Standalone retrieval question" if index == 1 else f"Query variation {index - 1}"
                            st.markdown(f"**{label}:** {query}")

                if documents:
                    with st.expander("Retrieved chunks and snippets", expanded=False):
                        for index, document in enumerate(documents, start=1):
                            source_name = document.metadata.get("source", "Unknown file")
                            page_number = document.metadata.get("page")
                            page_label = f"Page {page_number + 1}" if page_number is not None else "Page unknown"
                            rerank_score = document.metadata.get("rerank_score", "N/A")
                            st.markdown(
                                f"**Chunk {index} - {source_name} - {page_label} - Score: {rerank_score}/10**"
                            )
                            snippet = document.page_content.strip()
                            preview = snippet[:350] + ("..." if len(snippet) > 350 else "")
                            st.write(preview)


def render_chat(pipeline: PDFRAGPipeline) -> None:
    with st.container(border=True, height=RIGHT_PANEL_HEIGHT):
        render_chat_actions(pipeline)
        render_summary_panel()

        if st.session_state.get("vectorstore") is None:
            st.info("Upload one or more documents to start asking questions.")
            return

        messages_height = CHAT_MESSAGES_HEIGHT
        if st.session_state.get("summary_result") and not st.session_state.get("summary_minimized"):
            messages_height = CHAT_MESSAGES_HEIGHT - 180

        messages_placeholder = st.empty()
        render_message_history(messages_placeholder, messages_height)

        recent_history = [
            {"role": message["role"], "content": message["content"]}
            for message in st.session_state["messages"][-4:]
        ]
        question = st.chat_input("Ask a question about the uploaded files")
        if not question:
            return

        st.session_state["messages"].append({"role": "user", "content": question})
        render_message_history(messages_placeholder, messages_height)

        try:
            with st.spinner("Searching the document set..."):
                answer_mode = (
                    "exhaustive" if st.session_state.get("answer_mode") == "Exhaustive extraction" else "standard"
                )
                result = pipeline.answer_question(
                    st.session_state["vectorstore"],
                    question,
                    chat_history=recent_history,
                    answer_mode=answer_mode,
                )
        except Exception as error:
            LOGGER.exception("Failed to answer question")
            st.error(f"Could not generate an answer: {error}")
            st.session_state["messages"].pop()
            render_message_history(messages_placeholder, messages_height)
            return

        answer = result["answer"]
        documents = result["documents"]
        st.session_state["messages"].append(
            {
                "role": "assistant",
                "content": answer,
                "meta": result,
                "question": question,
            }
        )
        st.session_state["last_sources"] = documents
        st.session_state["last_result"] = result
        render_message_history(messages_placeholder, messages_height)


def run_app() -> None:
    st.set_page_config(page_title="PDF Q&A RAG App", page_icon="📄", layout="wide")
    initialize_session_state()
    apply_app_styles()

    pipeline = get_pipeline(DEFAULT_CHAT_MODEL, DEFAULT_EMBEDDING_MODEL)

    st.markdown('<div class="app-title">PDF Q&A RAG App</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="app-subtitle">Ask questions about your uploaded documents and review grounded answers with retrieved evidence.</div>',
        unsafe_allow_html=True,
    )

    left_col, right_col = st.columns([0.32, 0.68], gap="medium")
    with left_col:
        render_left_panel(pipeline)
    with right_col:
        render_chat(pipeline)
