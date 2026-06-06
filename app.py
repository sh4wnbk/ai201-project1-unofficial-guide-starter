import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
import gradio as gr

from embed import retrieve

load_dotenv()

MODEL = "gemini-2.5-flash-lite"
TOP_K = 7
TEMPERATURE = 0.2
PREVIEW_CHARS = 200

REFUSAL = "I don't have enough information on that"

SYSTEM_PROMPT = f"""You are a financial-aid assistant for Lehman College (CUNY) students.

Answer using ONLY the information in the Context block provided for the CURRENT turn.
The context is labeled [Source N: filename] for each chunk. Do not use any prior
knowledge, general knowledge, training data, or plausible-sounding inference. Do not
fabricate dates, amounts, deadlines, URLs, eligibility rules, or procedures that are
not explicitly stated in the current context.

You may receive a conversation history of prior questions and answers in this chat.
Use that history ONLY to resolve references like "it," "that," "my appeal," or "what
about late?" — i.e., to understand what the user is asking. Do NOT carry forward
facts from prior turns' context that are not also present in the current turn's
Context block. If a follow-up question requires information from a prior turn's
context that is not in the current turn's context, treat it as not enough information.

If the current context does not contain enough information to answer the question,
respond with EXACTLY this sentence and nothing else: "{REFUSAL}".

When the current context is sufficient, write a direct, plain-prose answer. Do not
include inline citations or "[Source N]" markers — the UI shows sources in a
separate panel.
"""

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set. Add it to .env.")
        _client = genai.Client(api_key=api_key)
    return _client


def format_context(chunks: list[dict]) -> str:
    blocks = []
    for i, c in enumerate(chunks, 1):
        blocks.append(f"[Source {i}: {c['source']}]\n{c['text']}")
    return "\n\n".join(blocks)


def format_sources(chunks: list[dict]) -> str:
    lines = [f"**Sources (top {len(chunks)})**", ""]
    for i, c in enumerate(chunks, 1):
        preview = c["text"].strip().replace("\n", " ")
        if len(preview) > PREVIEW_CHARS:
            preview = preview[:PREVIEW_CHARS].rstrip() + "..."
        lines.append(f"{i}. `{c['source']}` (dist {c['distance']:.3f})")
        lines.append(f"   > {preview}")
        lines.append("")
    return "\n".join(lines)


def _content_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, dict) and "text" in p:
                parts.append(p["text"] if isinstance(p["text"], str) else str(p["text"]))
            elif isinstance(p, str):
                parts.append(p)
        return " ".join(parts).strip()
    return str(content)


def answer(query: str, history: list[dict] | None = None) -> tuple[str, str]:
    if not query or not query.strip():
        return "", ""
    history = history or []

    prior_user_msgs = [_content_text(t["content"]) for t in history if t["role"] == "user"]
    last_prior = prior_user_msgs[-1] if prior_user_msgs else ""
    retrieval_query = f"{last_prior} {query}".strip() if last_prior else query

    chunks = retrieve(retrieval_query, k=TOP_K)

    contents = []
    for turn in history:
        role = "user" if turn["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": _content_text(turn["content"])}]})
    user_msg = f"Context:\n{format_context(chunks)}\n\nQuestion: {query}"
    contents.append({"role": "user", "parts": [{"text": user_msg}]})

    response = _get_client().models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=TEMPERATURE,
        ),
    )
    if not response.candidates or not response.candidates[0].content or not response.candidates[0].content.parts:
        finish_reason = (
            response.candidates[0].finish_reason if response.candidates else "no candidates"
        )
        return f"(Model returned no content. Finish reason: {finish_reason})", format_sources(chunks)
    return response.text.strip(), format_sources(chunks)


SOURCES_PLACEHOLDER = "*Ask a question above to see retrieved sources here.*"


def respond(message: str, history: list[dict]) -> tuple[str, list[dict], str]:
    if not message.strip():
        return "", history, SOURCES_PLACEHOLDER
    try:
        answer_text, sources_md = answer(message, history)
    except Exception as e:
        import traceback
        traceback.print_exc()
        err_text = f"**Error from backend** (`{type(e).__name__}`): {e}"
        new_history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": err_text},
        ]
        return "", new_history, SOURCES_PLACEHOLDER
    new_history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": answer_text},
    ]
    return "", new_history, sources_md


def clear_chat() -> tuple[list, str]:
    return [], SOURCES_PLACEHOLDER


EVAL_QUERY_CARDS = [
    ["How many credits do I need to complete for my 5th TAP payment?"],
    ["What happens to my financial aid if I withdraw from all my classes?"],
    ["How do I appeal a SAP suspension at Lehman?"],
    ["What is the income limit to qualify for the Excelsior Scholarship?"],
    ["How do I check my financial aid status in CUNYfirst?"],
]
REFUSAL_QUERY_CARDS = [["How do I apply for a parking permit at Lehman?"]]
MULTITURN_QUERY_CARDS = [
    ["How do I appeal a SAP suspension at Lehman?"],
    ["What happens if my appeal is granted?"],
]


with gr.Blocks(title="Lehman Financial Aid Assistant") as demo:
    gr.Markdown("# Lehman Financial Aid Assistant")
    gr.Markdown(
        "Ask about FAFSA, TAP, SAP, Excelsior, withdrawals, and CUNYfirst at Lehman College. "
        "Answers are grounded only in the indexed documents. Follow-up questions are supported "
        "— prior turns are used to resolve references like *it* or *my appeal*."
    )

    chatbot = gr.Chatbot(height=400, label="Conversation")
    msg = gr.Textbox(
        label="Your question",
        lines=2,
        placeholder="e.g. What is the income limit for the Excelsior Scholarship?",
    )
    with gr.Row():
        ask_btn = gr.Button("Ask", variant="primary")
        clear_btn = gr.Button("Clear conversation")

    gr.Markdown("### Sources (latest turn)")
    sources_out = gr.Markdown(value=SOURCES_PLACEHOLDER)

    gr.Markdown("---")
    gr.Markdown("### Demo Prompts — click any card to load it into the input above")

    with gr.Accordion("Evaluation Queries (5 from planning.md)", open=True):
        gr.Examples(examples=EVAL_QUERY_CARDS, inputs=[msg], label="")

    with gr.Accordion("Out-of-Scope Refusal Test", open=False):
        gr.Examples(examples=REFUSAL_QUERY_CARDS, inputs=[msg], label="")

    with gr.Accordion("Multi-Turn Follow-up Demo", open=False):
        gr.Markdown(
            "Click the first card and submit. Then click the second card and submit. "
            "The follow-up uses conversation history to resolve *my appeal* and "
            "concat-retrieval to surface the FINANCIAL AID PROBATION chunk."
        )
        gr.Examples(examples=MULTITURN_QUERY_CARDS, inputs=[msg], label="")

    ask_btn.click(respond, inputs=[msg, chatbot], outputs=[msg, chatbot, sources_out])
    msg.submit(respond, inputs=[msg, chatbot], outputs=[msg, chatbot, sources_out])
    clear_btn.click(clear_chat, outputs=[chatbot, sources_out])


if __name__ == "__main__":
    demo.launch()
