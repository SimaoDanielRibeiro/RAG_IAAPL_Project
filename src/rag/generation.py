"""Answer and summary generation from retrieved context."""

from __future__ import annotations

import re
from typing import AsyncIterator

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama


# Markdown artefacts the small chat model occasionally produces despite the
# "plain text" instruction. Stripping them here keeps the chat history sent
# back into the rewriter clean too. Single `*` / `_` are preserved so list
# items ("* foo") and underscored filenames survive.
_MARKDOWN_BOLD_OR_RULE    = re.compile(r"\*{2,}")
_MARKDOWN_BOLD_UNDERSCORE = re.compile(r"_{2,}")
_MARKDOWN_HEADER          = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_MARKDOWN_HORIZONTAL_RULE = re.compile(r"^-{3,}\s*$", re.MULTILINE)


def _strip_markdown(text: str) -> str:
    text = _MARKDOWN_BOLD_OR_RULE.sub("", text)
    text = _MARKDOWN_BOLD_UNDERSCORE.sub("", text)
    text = _MARKDOWN_HEADER.sub("", text)
    text = _MARKDOWN_HORIZONTAL_RULE.sub("", text)
    return text


def _strip_trailing_fallback(text: str, fallback: str) -> str:
    """Remove a trailing fallback sentence the model sometimes appends as a
    closing disclaimer even when the rest of the answer is valid.

    The fallback is only removed when there is meaningful content before it;
    if the entire answer IS the fallback, it is left untouched so the user
    still sees the "no relevant context" signal.
    """
    if not text or not fallback:
        return text
    stripped = text.rstrip()
    if not stripped.endswith(fallback):
        return text
    prefix = stripped[: -len(fallback)].rstrip(" \t\r\n.,;:-")
    if not prefix:
        return text
    return prefix


from src.rag.config import FALLBACK_ANSWER, SUMMARY_FALLBACK
from src.rag.prompts import (
    ANSWER_PROMPT_TEMPLATE,
    EXHAUSTIVE_ANSWER_PROMPT_TEMPLATE,
    SUMMARY_PROMPT_TEMPLATE,
    SYSTEM_PROMPT,
)


_ANSWER_PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM_PROMPT), ("human", ANSWER_PROMPT_TEMPLATE)]
)
_EXHAUSTIVE_ANSWER_PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM_PROMPT), ("human", EXHAUSTIVE_ANSWER_PROMPT_TEMPLATE)]
)
_SUMMARY_PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM_PROMPT), ("human", SUMMARY_PROMPT_TEMPLATE)]
)


class AnswerGenerator:
    """Use the chat model to generate grounded answers and summaries."""

    def __init__(self, chat_model: ChatOllama) -> None:
        self.chat_model = chat_model

    def answer(self, context: str, question: str, answer_mode: str) -> str:
        """Generate an answer using only the retrieved context.

        Returns `FALLBACK_ANSWER` if the model returns an empty string.
        Exceptions from the chat model propagate to the caller, which is
        expected to surface them in the UI.
        """
        prompt = (
            _EXHAUSTIVE_ANSWER_PROMPT
            if answer_mode == "exhaustive"
            else _ANSWER_PROMPT
        )
        chain = prompt | self.chat_model | StrOutputParser()
        result = chain.invoke({"context": context, "question": question}).strip()
        result = _strip_markdown(result)
        result = _strip_trailing_fallback(result, FALLBACK_ANSWER).rstrip()
        return result or FALLBACK_ANSWER

    async def astream(
        self, context: str, question: str, answer_mode: str
    ) -> AsyncIterator[str]:
        """Stream answer tokens. Token chunks are non-empty strings.

        A tail buffer holds back the last few characters so a trailing
        `FALLBACK_ANSWER` the model occasionally appends as a closing
        disclaimer can be removed before the tokens reach the UI.

        Errors propagate; the caller surfaces them to the UI.
        """
        prompt = (
            _EXHAUSTIVE_ANSWER_PROMPT
            if answer_mode == "exhaustive"
            else _ANSWER_PROMPT
        )
        chain = prompt | self.chat_model | StrOutputParser()

        # Keep enough of the trailing text in the buffer to recognise the
        # fallback phrase plus any wrapping whitespace / punctuation.
        tail_size = len(FALLBACK_ANSWER) + 32
        buffer = ""

        async for chunk in chain.astream({"context": context, "question": question}):
            if not chunk:
                continue
            buffer += chunk
            if len(buffer) > tail_size:
                emit = buffer[: len(buffer) - tail_size]
                buffer = buffer[len(buffer) - tail_size :]
                yield emit

        # Flush: only strip the fallback when it ends a non-empty answer.
        if buffer:
            cleaned = _strip_trailing_fallback(buffer, FALLBACK_ANSWER)
            if cleaned:
                yield cleaned

    def summarize(self, context: str) -> str:
        """Summarize one source file using only retrieved context."""
        if not context.strip():
            return SUMMARY_FALLBACK

        chain = _SUMMARY_PROMPT | self.chat_model | StrOutputParser()
        result = chain.invoke({"context": context}).strip()
        return result or SUMMARY_FALLBACK
