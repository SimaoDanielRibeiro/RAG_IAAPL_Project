"""Formatting helpers for RAG context, citations, evidence, and confidence labels."""

from __future__ import annotations

import re
from dataclasses import dataclass
from math import log

from langchain_core.documents import Document

from src.rag.config import RAGConfig


_NUMBERED_CITATION_RE = re.compile(r"\[\s*(\d{1,3})\s*\]")
_TRAILING_CITATION_CLUSTER_RE = re.compile(
    r"(?:\s*\[\s*\d{1,3}\s*\])+\s*[.!?]?\s*$"
)
_FILE_CITATION_RE = re.compile(
    r"\[\s*\**\s*[^\[\]*]+?\.(?:pdf|docx|txt|md)\s*\**"
    r"(?:[,\s]+(?:pp?\.?|pages?)?\s*\d+[^\]]*)?\s*\]",
    re.IGNORECASE,
)
_REFERENCE_MARKER_RE = re.compile(
    r"(#\s*refer[eê]ncias\b|\[\d+\].*?(dispon[ií]vel em|último acesso|citado na p[aá]gina))",
    re.IGNORECASE | re.DOTALL,
)
_DOTTED_LEADER_RE = re.compile(r"(?:\.\s*){6,}|\.{6,}")
_TOKEN_RE = re.compile(r"\w{3,}", re.UNICODE)
_STOP_WORDS = {
    "the", "and", "for", "that", "this", "with", "from", "into", "about",
    "document", "documents", "also", "used", "uses", "using", "includes",
    "include", "including", "section", "sections", "como", "uma", "para",
    "que", "com", "por", "dos", "das", "este", "esta", "documento",
    "allows", "developers", "provide", "provides", "using", "without",
    "within", "through", "because", "while", "what", "which", "where",
}


def build_context(
    documents: list[Document],
    *,
    numbered_evidence: bool = False,
) -> str:
    """Format retrieved documents into a single context string for the LLM.

    Each section header carries source, page (1-based), chunk index, and
    optional section title so the model can cite faithfully.
    """
    sections: list[str] = []
    for evidence_index, document in enumerate(documents, start=1):
        page = document.metadata.get("page")
        chunk_index = document.metadata.get("chunk_index")
        section_title = document.metadata.get("section_title")
        source_name = document.metadata.get("source", "Unknown file")

        header = f"Page {page + 1}" if page is not None else "Page unknown"
        header = f"{source_name} | {header}"
        if numbered_evidence:
            header = f"EVIDENCE ID {evidence_index} | {header}"
        if chunk_index is not None:
            header = f"{header} | Chunk {chunk_index}"
        if section_title:
            header = f"{header} | Section: {section_title}"

        sections.append(f"{header}:\n{document.page_content.strip()}")
    return "\n\n".join(sections)


def extract_page_numbers(documents: list[Document]) -> list[int]:
    """Return sorted unique 1-based page numbers used in the final answer."""
    pages = {
        document.metadata["page"] + 1
        for document in documents
        if document.metadata.get("page") is not None
    }
    return sorted(pages)


def extract_source_names(documents: list[Document]) -> list[str]:
    """Return sorted unique source file names used in the final answer."""
    sources = {
        document.metadata["source"]
        for document in documents
        if document.metadata.get("source")
    }
    return sorted(sources)


def format_citations(documents: list[Document]) -> list[str]:
    """Build deterministic file-and-page citations from final documents.

    Output is one citation per source file: ``"my_file.pdf (Pages 3, 5, 9)"``.
    """
    citation_map: dict[str, set[int]] = {}
    for document in documents:
        source_name = document.metadata.get("source", "Unknown file")
        page_number = document.metadata.get("page")
        citation_map.setdefault(source_name, set())
        if page_number is not None:
            citation_map[source_name].add(page_number + 1)

    citations: list[str] = []
    for source_name in sorted(citation_map):
        pages = sorted(citation_map[source_name])
        if pages:
            pages_label = ", ".join(str(page) for page in pages)
            citations.append(f"{source_name} (Pages {pages_label})")
        else:
            citations.append(source_name)
    return citations


@dataclass(frozen=True)
class CitationValidationResult:
    """Result of checking model-authored exhaustive-mode citations."""

    ok: bool
    feedback: str = ""


def validate_numbered_citations(
    answer: str,
    documents: list[Document],
    question: str = "",
) -> CitationValidationResult:
    """Validate model-authored Evidence [N] citations without rewriting them.

    Exhaustive-mode answers are generated from numbered evidence blocks. This
    validator only checks whether the model followed that contract: citations
    must exist, be in range, sit at the end of the paragraph, and point to
    evidence that has at least some textual support for the paragraph. When it
    fails, the caller retries generation with the feedback instead of assigning
    citations after the fact.
    """
    if not answer.strip():
        return CitationValidationResult(False, "The answer was empty.")
    if not documents:
        return CitationValidationResult(
            False,
            "No evidence blocks were available, so numbered citations cannot be validated.",
        )

    evidence_profiles = _build_evidence_profiles(documents)
    token_weights = _token_weights(evidence_profiles)
    allow_reference_chunks = _allows_reference_chunks(question)
    problems: list[str] = []

    paragraph_number = 0
    for raw_line in answer.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        paragraph_number += 1

        paragraph_problems = _validate_cited_line(
            line=line,
            paragraph_number=paragraph_number,
            document_count=len(documents),
            evidence_profiles=evidence_profiles,
            token_weights=token_weights,
            allow_reference_chunks=allow_reference_chunks,
        )
        problems.extend(paragraph_problems)

    if paragraph_number == 0:
        return CitationValidationResult(False, "The answer had no paragraph text.")
    if problems:
        summary = " ".join(problems[:5])
        return CitationValidationResult(False, summary)
    return CitationValidationResult(True)


def place_numbered_citations_at_line_end(answer: str) -> str:
    """Move model-authored numbered citations to each line's end.

    This is only a placement cleanup: it preserves the exact Evidence IDs the
    model wrote and never infers, adds, removes, or remaps citations.
    """
    if not answer.strip():
        return answer

    lines: list[str] = []
    for raw_line in answer.split("\n"):
        line = raw_line.strip()
        if not line:
            lines.append(raw_line)
            continue
        if re.search(r"\bevidence\s*\[\s*\d{1,3}\s*\]", line, re.IGNORECASE):
            lines.append(raw_line)
            continue

        numbers = _all_citation_numbers(line)
        if not numbers:
            if _looks_like_source_list_artifact(line):
                continue
            lines.append(raw_line)
            continue

        clean_line = _NUMBERED_CITATION_RE.sub("", line)
        clean_line = _tidy_citation_whitespace(clean_line)
        if not clean_line:
            lines.append(raw_line)
            continue

        unique_numbers = list(dict.fromkeys(numbers))
        citation_suffix = " ".join(f"[{number}]" for number in unique_numbers)
        lines.append(f"{clean_line} {citation_suffix}".rstrip())

    return "\n".join(lines).strip()


def prune_invalid_numbered_citations(
    answer: str,
    documents: list[Document],
    question: str = "",
) -> str:
    """Remove model-authored citation numbers that fail local support checks.

    The function never adds replacement citations. If removing bad citations
    leaves a paragraph uncited, validation will fail and the caller will retry.
    """
    if not answer.strip() or not documents:
        return answer

    evidence_profiles = _build_evidence_profiles(documents)
    token_weights = _token_weights(evidence_profiles)
    allow_reference_chunks = _allows_reference_chunks(question)
    lines: list[str] = []

    for raw_line in answer.split("\n"):
        line = raw_line.strip()
        if not line:
            lines.append(raw_line)
            continue
        if _looks_like_source_list_artifact(line):
            continue

        clean_line = _clean_citation_text(line)
        if not clean_line:
            continue

        numbers = _all_citation_numbers(line)
        if not numbers:
            lines.append(raw_line)
            continue

        score_by_index = _score_evidence_for_text(
            clean_line,
            evidence_profiles,
            token_weights,
        )
        ranked_numbers = _infer_evidence_numbers(
            clean_line,
            evidence_profiles,
            token_weights,
            max_refs=4,
        )
        top_score = score_by_index.get(ranked_numbers[0], 0.0) if ranked_numbers else 0.0
        minimum_support_score = max(1.0, top_score * 0.12)

        kept_numbers: list[int] = []
        seen: set[int] = set()
        for number in numbers:
            if number in seen or number < 1 or number > len(documents):
                continue
            profile = evidence_profiles[number - 1]
            if not allow_reference_chunks and (
                profile.get("reference_like") or profile.get("outline_like")
            ):
                continue
            if score_by_index.get(number, 0.0) < minimum_support_score:
                continue
            kept_numbers.append(number)
            seen.add(number)

        if not kept_numbers:
            valid_in_range = [
                number for number in dict.fromkeys(numbers)
                if 1 <= number <= len(documents)
            ]
            if valid_in_range and all(
                evidence_profiles[number - 1].get("reference_like")
                or evidence_profiles[number - 1].get("outline_like")
                for number in valid_in_range
            ):
                continue
            lines.append(raw_line)
            continue

        citation_suffix = " ".join(f"[{number}]" for number in kept_numbers)
        lines.append(f"{clean_line} {citation_suffix}".rstrip())

    return "\n".join(lines).strip()


def align_numbered_citations_to_documents(
    answer: str,
    documents: list[Document],
) -> tuple[str, list[Document]]:
    """Return only cited evidence and remap citations to the returned list.

    Exhaustive generation is prompted with a larger evidence set so the model
    has enough material to answer well. The UI, however, should show only the
    evidence blocks the final answer actually cites; otherwise a high-ranking
    but unused Evidence [1] looks like a broken reference. This compacts the
    evidence list while preserving the citation-to-document contract.
    """
    if not answer.strip() or not documents:
        return answer, []

    cited_original_numbers = sorted(
        {
            number
            for number in _all_citation_numbers(answer)
            if 1 <= number <= len(documents)
        }
    )
    if not cited_original_numbers:
        return answer, []

    number_map = {
        original_number: compact_number
        for compact_number, original_number in enumerate(cited_original_numbers, start=1)
    }
    cited_documents = [
        documents[original_number - 1]
        for original_number in cited_original_numbers
    ]

    def replace_citation(match: re.Match[str]) -> str:
        original_number = int(match.group(1))
        compact_number = number_map.get(original_number)
        return f"[{compact_number}]" if compact_number is not None else ""

    remapped_answer = _NUMBERED_CITATION_RE.sub(replace_citation, answer)
    remapped_answer = place_numbered_citations_at_line_end(remapped_answer)
    return remapped_answer, cited_documents


def _validate_cited_line(
    *,
    line: str,
    paragraph_number: int,
    document_count: int,
    evidence_profiles: list[dict[str, object]],
    token_weights: dict[str, float],
    allow_reference_chunks: bool,
) -> list[str]:
    problems: list[str] = []
    prefix = f"Paragraph {paragraph_number}:"

    if _FILE_CITATION_RE.search(line):
        problems.append(
            f"{prefix} use numbered Evidence IDs like [2], not filename/page citations."
        )
    if re.search(r"\bevidence\s*\[\s*\d{1,3}\s*\]", line, re.IGNORECASE):
        problems.append(
            f"{prefix} do not narrate citations as 'Evidence [N]'; use plain [N] citations only at the paragraph end."
        )

    all_numbers = _all_citation_numbers(line)
    valid_numbers = _valid_citation_numbers(line, document_count)
    trailing_numbers = _trailing_citation_numbers(line)

    if not all_numbers:
        problems.append(f"{prefix} add at least one numbered evidence citation at the end.")
        return problems

    invalid_numbers = [
        number for number in all_numbers if number < 1 or number > document_count
    ]
    if invalid_numbers:
        invalid_label = ", ".join(f"[{number}]" for number in sorted(set(invalid_numbers)))
        problems.append(
            f"{prefix} {invalid_label} is outside the available Evidence [1]-[{document_count}] range."
        )

    if not trailing_numbers:
        problems.append(
            f"{prefix} move all citations to the very end of the paragraph."
        )
    elif set(valid_numbers) - set(trailing_numbers):
        problems.append(
            f"{prefix} every citation for the paragraph must be grouped at the end."
        )

    for number in valid_numbers:
        profile = evidence_profiles[number - 1]
        if not allow_reference_chunks and (
            profile.get("reference_like") or profile.get("outline_like")
        ):
            problems.append(
                f"{prefix} Evidence [{number}] looks like references, bibliography, or table-of-contents text; cite a content evidence block instead."
            )

    clean_line = _clean_citation_text(line)
    if not clean_line:
        problems.append(f"{prefix} remove citation-only lines; attach citations to prose.")
        return problems

    score_by_index = _score_evidence_for_text(
        clean_line,
        evidence_profiles,
        token_weights,
    )
    ranked_numbers = _infer_evidence_numbers(
        clean_line,
        evidence_profiles,
        token_weights,
        max_refs=4,
    )
    top_score = score_by_index.get(ranked_numbers[0], 0.0) if ranked_numbers else 0.0
    minimum_support_score = max(1.0, top_score * 0.12)

    unsupported = [
        number
        for number in valid_numbers
        if score_by_index.get(number, 0.0) < minimum_support_score
    ]
    if unsupported and ranked_numbers:
        cited_label = ", ".join(f"[{number}]" for number in unsupported)
        better_label = ", ".join(f"[{number}]" for number in ranked_numbers[:3])
        problems.append(
            f"{prefix} {cited_label} has little overlap with the paragraph; use only evidence that supports the claim. Likely relevant evidence: {better_label}."
        )

    return problems


def _all_citation_numbers(text: str) -> list[int]:
    return [int(match.group(1)) for match in _NUMBERED_CITATION_RE.finditer(text)]


def _looks_like_source_list_artifact(text: str) -> bool:
    stripped = text.strip()
    return bool(
        stripped.startswith("[")
        and len(stripped) <= 120
        and re.search(r"\[[A-Za-z]\d+\]", stripped)
    )


def _trailing_citation_numbers(text: str) -> list[int]:
    match = _TRAILING_CITATION_CLUSTER_RE.search(text)
    if not match:
        return []
    return _all_citation_numbers(match.group(0))


def _clean_citation_text(text: str) -> str:
    text = _NUMBERED_CITATION_RE.sub("", text)
    text = _FILE_CITATION_RE.sub("", text)
    return _tidy_citation_whitespace(text)


def _score_evidence_for_text(
    text: str,
    evidence_profiles: list[dict[str, object]],
    token_weights: dict[str, float],
) -> dict[int, float]:
    paragraph_sequence = _token_sequence(text)
    paragraph_tokens = set(paragraph_sequence)
    if not paragraph_tokens:
        return {}

    return {
        index: _evidence_overlap_score(
            paragraph_sequence,
            paragraph_tokens,
            profile,
            token_weights,
        )
        for index, profile in enumerate(evidence_profiles, start=1)
    }


def _allows_reference_chunks(question: str) -> bool:
    lower_question = question.lower()
    reference_terms = (
        "reference",
        "references",
        "bibliography",
        "citation",
        "citations",
        "referencia",
        "referencias",
        "bibliografia",
    )
    outline_terms = (
        "table of contents",
        "contents",
        "outline",
        "sections",
        "index",
        "indice",
    )
    return any(term in lower_question for term in reference_terms + outline_terms)


def _infer_evidence_numbers(
    text: str,
    evidence_profiles: list[dict[str, object]],
    token_weights: dict[str, float],
    max_refs: int = 4,
) -> list[int]:
    score_by_index = _score_evidence_for_text(
        text,
        evidence_profiles,
        token_weights,
    )
    scored: list[tuple[float, int]] = []
    for index, score in score_by_index.items():
        if score > 0.0:
            scored.append((score, index))

    if not scored:
        return []

    scored.sort(key=lambda item: (-item[0], item[1]))
    top_score = scored[0][0]
    threshold = max(2.4, top_score * 0.58)
    return [
        index
        for score, index in scored
        if score >= threshold
    ][:max_refs]


def _valid_citation_numbers(text: str, max_number: int) -> list[int]:
    numbers: list[int] = []
    seen: set[int] = set()
    for match in _NUMBERED_CITATION_RE.finditer(text):
        number = int(match.group(1))
        if 1 <= number <= max_number and number not in seen:
            numbers.append(number)
            seen.add(number)
    return numbers


def _build_evidence_profiles(documents: list[Document]) -> list[dict[str, object]]:
    profiles: list[dict[str, object]] = []
    for document in documents:
        section_title = str(document.metadata.get("section_title", ""))
        text = f"{section_title} {document.page_content}"
        tokens = _token_sequence(text)
        low_value = is_low_value_evidence_text(text)
        profiles.append(
            {
                "tokens": set(tokens),
                "token_text": " ".join(tokens),
                "text": text.lower(),
                "reference_like": low_value or _is_reference_like(text),
                "outline_like": low_value or _is_outline_like(text),
            }
        )
    return profiles


def _token_weights(evidence_profiles: list[dict[str, object]]) -> dict[str, float]:
    document_count = max(1, len(evidence_profiles))
    frequency: dict[str, int] = {}
    for profile in evidence_profiles:
        for token in profile["tokens"]:
            frequency[token] = frequency.get(token, 0) + 1

    return {
        token: 1.0 + log((document_count + 1) / (count + 1))
        for token, count in frequency.items()
    }


def _evidence_overlap_score(
    paragraph_sequence: list[str],
    paragraph_tokens: set[str],
    evidence_profile: dict[str, object],
    token_weights: dict[str, float],
) -> float:
    evidence_tokens = evidence_profile["tokens"]
    if not isinstance(evidence_tokens, set):
        return 0.0

    overlap = paragraph_tokens & evidence_tokens
    if not overlap:
        return 0.0

    score = sum(token_weights.get(token, 1.0) for token in overlap)
    evidence_token_text = evidence_profile.get("token_text")
    if isinstance(evidence_token_text, str):
        score += _phrase_overlap_bonus(paragraph_sequence, evidence_token_text)

    if evidence_profile.get("reference_like"):
        score *= 0.35
    if evidence_profile.get("outline_like"):
        score *= 0.25
    return score


def _phrase_overlap_bonus(
    paragraph_sequence: list[str],
    evidence_token_text: str,
) -> float:
    bonus = 0.0
    seen: set[str] = set()
    for size, weight in ((3, 4.0), (2, 2.0)):
        if len(paragraph_sequence) < size:
            continue
        for index in range(len(paragraph_sequence) - size + 1):
            phrase = " ".join(paragraph_sequence[index:index + size])
            if phrase in seen:
                continue
            seen.add(phrase)
            if phrase in evidence_token_text:
                bonus += weight
    return bonus


def _is_reference_like(text: str) -> bool:
    lower_text = text.lower()
    if _REFERENCE_MARKER_RE.search(lower_text):
        return True
    reference_signals = (
        lower_text.count("disponível em")
        + lower_text.count("último acesso")
        + lower_text.count("citado na página")
        + lower_text.count("github")
        + lower_text.count("https://")
    )
    numbered_entries = len(re.findall(r"\[\d+\]", lower_text))
    return reference_signals >= 3 and numbered_entries >= 2


def _is_outline_like(text: str) -> bool:
    lower_text = text.lower()
    dotted_leaders = lower_text.count(". . .")
    section_number_lines = len(re.findall(r"(?m)^\s*\d+(?:\.\d+)*\s*$", lower_text))
    return dotted_leaders >= 3 or section_number_lines >= 6


def is_low_value_evidence_text(text: str) -> bool:
    """Return True for bibliography, index, table-of-contents, or outline chunks."""
    lower_text = text.lower()
    reference_signals = (
        lower_text.count("http://")
        + lower_text.count("https://")
        + lower_text.count("github")
        + lower_text.count("available")
        + lower_text.count("accessed")
        + lower_text.count("online")
        + lower_text.count("doi")
        + lower_text.count("citado na p")
        + lower_text.count("refer")
    )
    numbered_entries = len(re.findall(r"\[\d+\]", lower_text))
    dotted_leaders = len(_DOTTED_LEADER_RE.findall(lower_text))
    index_terms = (
        lower_text.count("indice")
        + lower_text.count("index")
        + lower_text.count("table of contents")
        + lower_text.count("agradecimentos")
        + lower_text.count("acronimos")
    )
    return (
        _is_reference_like(text)
        or _is_outline_like(text)
        or (reference_signals >= 2 and numbered_entries >= 2)
        or dotted_leaders >= 3
        or (dotted_leaders >= 1 and index_terms >= 1)
    )


def _tokenize(text: str) -> set[str]:
    return set(_token_sequence(text))


def _token_sequence(text: str) -> list[str]:
    return [
        token.lower()
        for token in _TOKEN_RE.findall(text)
        if token.lower() not in _STOP_WORDS
    ]


def _tidy_citation_whitespace(text: str) -> str:
    text = re.sub(r",\s*([.!?])", r"\1", text)
    text = re.sub(r"[ \t]+([.,!?;:])", r"\1", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip().rstrip(" ,;:")


def average_rerank_score(documents: list[Document]) -> float | None:
    """Compute the average rerank score of final chunks, or None when missing."""
    scores = [document.metadata.get("rerank_score") for document in documents]
    valid_scores = [score for score in scores if isinstance(score, (int, float))]
    if not valid_scores:
        return None
    return round(sum(valid_scores) / len(valid_scores), 2)


def confidence_label(average_score: float | None, config: RAGConfig) -> str:
    """Map the average rerank score to a simple confidence label."""
    if average_score is None:
        return "Low"
    if average_score >= config.confidence_high_cutoff:
        return "High"
    if average_score >= config.confidence_medium_cutoff:
        return "Medium"
    return "Low"


def has_weak_evidence(
    documents: list[Document],
    average_score: float | None,
    config: RAGConfig,
) -> bool:
    """Return True when retrieved evidence is too weak to support an answer.

    Evidence is "weak" when:
    - Fewer than `minimum_supporting_chunks` chunks survived selection, OR
    - Scores were produced on the absolute (LLM) scale and the average is
      below `weak_evidence_average_threshold`.

    For relative-scale (CrossEncoder) scores the only check is the chunk
    count. CrossEncoder raw logits cannot reliably distinguish off-topic
    questions from valid meta-questions ("what is this about?",
    "summarize this") — both score in the -10 logit range against MS-MARCO
    cross-encoders. The hallucination-on-off-topic trade-off is accepted
    here so legitimate meta-questions continue to work.
    """
    if len(documents) < config.minimum_supporting_chunks:
        return True

    score_scale = _dominant_score_scale(documents)
    if score_scale == "absolute":
        if average_score is None:
            return True
        return average_score < config.weak_evidence_average_threshold

    return False


def _dominant_score_scale(documents: list[Document]) -> str:
    """Return whichever score scale most chunks were rated on ("absolute" by default)."""
    scales = [
        document.metadata.get("rerank_score_scale", "absolute")
        for document in documents
    ]
    if not scales:
        return "absolute"
    return "relative" if scales.count("relative") > len(scales) // 2 else "absolute"
