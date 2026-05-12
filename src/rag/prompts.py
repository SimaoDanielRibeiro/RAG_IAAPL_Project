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


ANSWER_PROMPT_TEMPLATE = """
Context:
{context}

Question:
{question}

Instructions:
- Use the context to answer the question. Extract whatever is relevant; do not refuse just because the wording differs from the question.
- If only part of the answer is present, give that part and note what is missing.
- Do not invent facts or use outside knowledge.
- Mention the relevant page number(s) and source file name(s) when possible.
- Keep the answer clear and concise.
- Only when the context contains nothing related to the question at all, respond exactly with:
  I could not find that information in the uploaded document.
""".strip()


EXHAUSTIVE_ANSWER_PROMPT_TEMPLATE = """
Context:
{context}

Question:
{question}

Instructions:
- Extract as much relevant information as possible from the context.
- Do not give only a short summary if the user asks for all items, all comparisons, all mentions, or everything relevant.
- Organize the answer into clear sections or bullet points when helpful.
- Include the relevant file name and page number when possible.
- If part of the requested information is missing from the context, say so clearly.
- If nothing relevant is found, respond exactly with:
  I could not find that information in the uploaded document.
- Do not use outside knowledge.
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
