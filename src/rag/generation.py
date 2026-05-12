"""Answer and summary generation from retrieved context."""

from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

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
        return result or FALLBACK_ANSWER

    def summarize(self, context: str) -> str:
        """Summarize one source file using only retrieved context."""
        if not context.strip():
            return SUMMARY_FALLBACK

        chain = _SUMMARY_PROMPT | self.chat_model | StrOutputParser()
        result = chain.invoke({"context": context}).strip()
        return result or SUMMARY_FALLBACK
