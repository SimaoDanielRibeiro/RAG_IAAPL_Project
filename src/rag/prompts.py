"""Prompt templates used by the document RAG application."""

SYSTEM_PROMPT = """
You are a document question-answering assistant.
Answer only using the retrieved context.
If the answer is not clearly present in the context, say:
"I could not find that information in the uploaded document."
Do not invent facts.
Do not use outside knowledge.
Always mention page numbers and source file names when possible.
""".strip()


_CITATION_FORMAT_RULE = (
    "CITATION FORMAT (CRITICAL): cite every claim using square brackets in EXACTLY "
    "this format: [filename, p.N] — for example [report.pdf, p.3]. Use this exact "
    "format inside bullet points and lists too. If no page is known: [report.pdf]. "
    "Do NOT wrap citations in bold/italic, do NOT use parentheses, do NOT add "
    '"Source:" or any prefix inside the brackets. Do not fabricate citations.'
)

_FORMAT_RULE = (
    "PLAIN TEXT FORMAT (CRITICAL): write the answer as plain prose. "
    "Do NOT use markdown formatting — no asterisks for bold (**), no asterisks for "
    "italic (*), no underscores for emphasis (__ or _), no hash signs for headers "
    "(#, ##, ###), no horizontal rules (---). Use plain paragraphs separated by "
    "blank lines. Plain hyphen bullets (- item) are allowed only when the answer is "
    "clearly a list."
)


_NO_SOURCE_NARRATION_RULE = (
    "ANSWER STYLE (CRITICAL): write the prose as if the user cannot see which file "
    "or page the information came from. Do NOT narrate the source location in the "
    "answer text. Specifically, do NOT use phrases such as: "
    '"on page X", "on page X of [file]", "page N of [file]", "according to [file]", '
    '"as mentioned in [file]", "as stated in", "the document says", "the file says", '
    '"where it says", "this is stated in", "is emphasized on page X", '
    '"is explicitly stated in". '
    "The citation markers at the end of each paragraph already tell the user where "
    "the information came from — the prose itself must read as a direct answer. "
    "Paraphrase the content in your own words. Do NOT copy long verbatim quotations "
    "from the source; convert any quoted text into concise paraphrased wording. "
    "Short technical phrases (a method name, a header, a literal value) may stay as "
    "is when paraphrasing would distort the meaning."
)


_STANDARD_CITATION_RULE = (
    'Do NOT add any inline citations in the answer text. No "[filename, p.N]", '
    'no "(filename)", no parenthetical sources. The user already sees the '
    "supporting sources separately in the Evidence panel."
)

_EXHAUSTIVE_CITATION_RULE = (
    _CITATION_FORMAT_RULE
    + " CITATION PLACEMENT: every paragraph MUST contain at least one inline "
    "citation in the [filename, p.N] format. Place the citation at the very END "
    "of the paragraph it supports — never inside a sentence and never narrated "
    "as part of the prose. If a paragraph combines facts from two or more "
    "sources, put ALL the citations together at the end of that paragraph. "
    "A paragraph with no citation is not acceptable."
)


_STANDARD_LENGTH_RULE = (
    "Keep the answer direct and concise — typically 2 to 4 sentences in plain "
    "prose. Synthesize the relevant facts smoothly."
)

_EXHAUSTIVE_LENGTH_RULE = (
    "Give a thorough, complete answer that extracts as much relevant information "
    "from the context as possible. Structure the answer as multiple plain "
    "paragraphs separated by blank lines. Each paragraph develops one aspect of "
    "the answer. Do NOT use markdown section headers — start each new aspect "
    "with a normal sentence. Use plain hyphen bullets (- item) only when the "
    'question explicitly asks for an enumerated list (e.g. "list all items", '
    '"what are the steps"). When using bullets, place the citation at the end '
    "of each bullet."
)


_PARTIAL_ANSWER_RULE = (
    "If part of the requested information is missing from the context, mention "
    "what is missing in your own words in a short final paragraph. Do NOT use "
    'the exact phrase "I could not find that information in the uploaded '
    'document" as a closing disclaimer when the answer above already contains '
    "real content."
)


_BASE_ANSWER_PROMPT_TEMPLATE = """
Context:
{context}

Question:
{question}

Instructions:
- Use the context to answer the question. Extract whatever is relevant; do not refuse just because the wording differs from the question.
- __CITATION_RULE__
- __FORMAT_RULE__
- __NO_SOURCE_NARRATION_RULE__
- __LENGTH_RULE__
- __PARTIAL_ANSWER_RULE__
- Do not invent facts or use outside knowledge.
- ONLY when the context contains nothing related to the question at all, respond with EXACTLY this single sentence and nothing else:
  I could not find that information in the uploaded document.
  Never append that sentence after a paragraph that already answered (even partially).
""".strip()


def _build_answer_prompt(citation_rule: str, length_rule: str) -> str:
    """Inject the mode-specific citation and length rules into the shared base."""
    return (
        _BASE_ANSWER_PROMPT_TEMPLATE
        .replace("__CITATION_RULE__", citation_rule)
        .replace("__FORMAT_RULE__", _FORMAT_RULE)
        .replace("__NO_SOURCE_NARRATION_RULE__", _NO_SOURCE_NARRATION_RULE)
        .replace("__LENGTH_RULE__", length_rule)
        .replace("__PARTIAL_ANSWER_RULE__", _PARTIAL_ANSWER_RULE)
    )


ANSWER_PROMPT_TEMPLATE = _build_answer_prompt(
    _STANDARD_CITATION_RULE, _STANDARD_LENGTH_RULE
)

EXHAUSTIVE_ANSWER_PROMPT_TEMPLATE = _build_answer_prompt(
    _EXHAUSTIVE_CITATION_RULE, _EXHAUSTIVE_LENGTH_RULE
)


STANDARD_RERANK_CRITERIA = (
    "Score for PRECISION. Prefer chunks that directly and concisely answer the "
    "question. A 10 chunk contains the exact answer; a 7 chunk contains most of "
    "it; a 5 chunk is on-topic but does not actually answer; a 1 chunk is "
    "off-topic. Penalize chunks that only mention the topic in passing."
)

EXHAUSTIVE_RERANK_CRITERIA = (
    "Score for BREADTH and CITABILITY. Prefer chunks that cover any aspect of "
    "the topic and that contain concrete, citable facts (numbers, names, "
    "definitions, claims that can be quoted). A 10 chunk adds a distinct, "
    "citable piece of evidence; a 7 chunk adds partial new evidence; a 5 chunk "
    "is topical but largely repeats what other chunks already say; a 1 chunk is "
    "off-topic. A chunk that is on-topic but redundant should score lower than "
    "one that adds a new citable fact."
)


RERANK_PROMPT_TEMPLATE = """
You are ranking retrieved document chunks for a document question-answering system.

Question:
{question}

Chunk:
{chunk}

Scoring criteria:
{criteria}

Give only a relevance score from 1 to 10.
""".strip()


SUMMARY_PROMPT_TEMPLATE = """
You are summarizing an uploaded document for a student demo.
Use only the provided context; do not invent facts or use outside knowledge.
Write a short summary in 4 to 6 bullet points based on whatever is present in the context, even if the material is partial or rough.
Mention page numbers and the source file when possible.

Context:
{context}
""".strip()


REWRITE_QUESTION_PROMPT_TEMPLATE = """
You are rewriting a user question for document retrieval.

Use the conversation history only when the latest question depends on it.
If the latest question is already clear and standalone, return it unchanged.
Do not answer the question.
Do not add facts that are not implied by the conversation.
Return only one standalone question on a single line.
Do not include explanations, definitions, or any extra sentences.

Conversation history:
{chat_history}

Latest user question:
{question}
""".strip()
