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


_CITATION_RULE = (
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


ANSWER_PROMPT_TEMPLATE = f"""
Context:
{{context}}

Question:
{{question}}

Instructions:
- Use the context to answer the question. Extract whatever is relevant; do not refuse just because the wording differs from the question.
- Do NOT add any inline citations in the answer text. No "[filename, p.N]", no "(filename)", no parenthetical sources. The user already sees the supporting sources separately in the Evidence panel.
- {_FORMAT_RULE}
- {_NO_SOURCE_NARRATION_RULE}
- Keep the answer direct and concise — typically 2 to 4 sentences in plain prose. Synthesize the relevant facts smoothly.
- If only part of the answer is present, give that part and briefly mention what is missing in your own words. Do NOT use the exact phrase "I could not find that information in the uploaded document" as a closing disclaimer when the rest of the answer has real content.
- Do not invent facts or use outside knowledge.
- ONLY when the context contains nothing related to the question at all, respond with EXACTLY this single sentence and nothing else:
  I could not find that information in the uploaded document.
  Never append that sentence after a paragraph that already answered (even partially).
""".strip()


EXHAUSTIVE_ANSWER_PROMPT_TEMPLATE = f"""
Context:
{{context}}

Question:
{{question}}

Instructions:
- Give a thorough, complete answer that extracts as much relevant information from the context as possible.
- {_CITATION_RULE}
- CITATION PLACEMENT: every paragraph MUST contain at least one inline citation in the [filename, p.N] format. Place the citation at the very END of the paragraph it supports — never inside a sentence and never narrated as part of the prose. If a paragraph combines facts from two or more sources, put ALL the citations together at the end of that paragraph. A paragraph with no citation is not acceptable.
- {_FORMAT_RULE}
- {_NO_SOURCE_NARRATION_RULE}
- Structure the answer as multiple plain paragraphs separated by blank lines. Each paragraph develops one aspect of the answer. Do NOT use markdown section headers — start each new aspect with a normal sentence.
- Use plain hyphen bullets (- item) only when the question explicitly asks for an enumerated list (e.g. "list all items", "what are the steps"). When using bullets, place the citation at the end of each bullet.
- If part of the requested information is missing from the context, mention what is missing in your own words in a short final paragraph. Do NOT use the exact phrase "I could not find that information in the uploaded document" as a closing disclaimer when the answer above already contains real content.
- Do not invent facts or use outside knowledge.
- ONLY when the context contains nothing related to the question at all, respond with EXACTLY this single sentence and nothing else:
  I could not find that information in the uploaded document.
  Never append that sentence after a paragraph that already answered (even partially).
""".strip()


RERANK_PROMPT_TEMPLATE = """
You are ranking retrieved document chunks for a document question-answering system.

Question:
{question}

Chunk:
{chunk}

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
