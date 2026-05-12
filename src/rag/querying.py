"""Question rewriting and multi-query expansion for retrieval."""

from __future__ import annotations

import logging

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_ollama import ChatOllama

from src.rag.config import RAGConfig
from src.rag.prompts import REWRITE_QUESTION_PROMPT_TEMPLATE


_QUERY_EXPANSION_PROMPT = PromptTemplate(
    input_variables=["question"],
    template=(
        "You are helping expand a user question for document retrieval.\n"
        "Generate exactly 2 alternative versions of the user's question.\n"
        "Focus on wording changes that improve recall.\n"
        "Return only the 2 alternative questions, one per line, and do not number them.\n"
        "Do not answer the question.\n\n"
        "Original question: {question}"
    ),
)

_REWRITE_PROMPT = PromptTemplate(
    input_variables=["chat_history", "question"],
    template=REWRITE_QUESTION_PROMPT_TEMPLATE,
)


class QueryProcessor:
    """Prepare user questions for retrieval.

    Two responsibilities:
    1. Rewrite follow-up questions into standalone retrieval questions when
       chat history makes the latest message ambiguous.
    2. Generate alternative phrasings of a question to broaden retrieval recall.
    """

    def __init__(self, chat_model: ChatOllama, config: RAGConfig, logger: logging.Logger) -> None:
        self.chat_model = chat_model
        self.config = config
        self.logger = logger

    def rewrite_with_history(
        self, question: str, chat_history: list[dict[str, str]]
    ) -> str:
        """Rewrite a follow-up question into a standalone retrieval question."""
        if not chat_history:
            return question

        history_text = self._format_chat_history(chat_history)
        if not history_text:
            return question

        chain = _REWRITE_PROMPT | self.chat_model | StrOutputParser()
        try:
            rewritten = chain.invoke(
                {"chat_history": history_text, "question": question}
            ).strip()
        except Exception as error:
            self.logger.warning(
                "Question rewriting failed; using original question. Error: %s", error
            )
            return question
        return self.sanitize_retrieval_question(rewritten, fallback=question)

    def generate_search_queries(self, question: str) -> list[str]:
        """Return the original question plus retrieval-focused rewrites.

        Returns up to `config.query_count` distinct queries. If the model
        produces too few alternatives, the result list is shorter rather than
        padded with duplicates (which would waste retrieval calls).
        """
        chain = _QUERY_EXPANSION_PROMPT | self.chat_model | StrOutputParser()
        try:
            response = chain.invoke({"question": question}).strip()
        except Exception as error:
            self.logger.warning(
                "Query expansion failed; using original question. Error: %s", error
            )
            response = ""

        alternatives = [
            self.sanitize_retrieval_question(line.strip("- ").strip(), fallback=question)
            for line in response.splitlines()
            if line.strip()
        ]
        base = self.sanitize_retrieval_question(question, fallback=question)
        queries: list[str] = [base]
        seen_lower = {base.lower()}
        for candidate in alternatives:
            if not candidate or candidate.lower() in seen_lower:
                continue
            queries.append(candidate)
            seen_lower.add(candidate.lower())
            if len(queries) >= self.config.query_count:
                break
        return queries

    def sanitize_retrieval_question(self, candidate: str, fallback: str) -> str:
        """Keep retrieval questions short, single-line, and question-like.

        Heuristics that have proven necessary in practice:
        - Strip leading/trailing whitespace and collapse runs of spaces.
        - If the model returned multiple lines, keep only the first.
        - Truncate at "answer-like" separators (". ", " Answer:", etc.).
        - Cap length to avoid blowing past the model's effective query window.
        - If the candidate looks like a *statement* rather than a question
          (contains "is/are/refers to/..." without a "?"), reject it and use
          the fallback — these come from models that ignore the prompt and
          start answering instead of paraphrasing.
        """
        cleaned = " ".join(candidate.split()).strip()
        fallback_clean = " ".join(fallback.split()).strip()
        if not cleaned:
            return fallback_clean

        if "\n" in candidate:
            cleaned = " ".join(candidate.splitlines()[0].split()).strip()

        for separator in (". ", "\n", " Answer:", " Explanation:", " Because "):
            if separator in cleaned:
                cleaned = cleaned.split(separator, 1)[0].strip()
        if not cleaned:
            return fallback_clean

        if len(cleaned) > self.config.max_query_length:
            cleaned = cleaned[: self.config.max_query_length].rsplit(" ", 1)[0].strip()
            if not cleaned:
                return fallback_clean

        lowered = cleaned.lower()
        answer_like_markers = (" is ", " are ", " refers to ", " means ", " can be defined as ")
        if not cleaned.endswith("?") and any(marker in lowered for marker in answer_like_markers):
            return fallback_clean

        if not cleaned.endswith("?"):
            cleaned = f"{cleaned}?"
        return cleaned

    @staticmethod
    def _format_chat_history(chat_history: list[dict[str, str]]) -> str:
        """Format the most recent (up to 4) messages as a transcript for the prompt."""
        lines: list[str] = []
        for message in chat_history[-4:]:
            role = message.get("role")
            content = (message.get("content") or "").strip()
            if role not in {"user", "assistant"} or not content:
                continue
            role_label = "User" if role == "user" else "Assistant"
            lines.append(f"{role_label}: {content}")
        return "\n".join(lines)
