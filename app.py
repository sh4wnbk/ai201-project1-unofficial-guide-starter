import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
import gradio as gr

from embed import retrieve

load_dotenv()

MODEL = "gemini-2.5-flash"
TOP_K = 5
TEMPERATURE = 0.2
PREVIEW_CHARS = 200

REFUSAL = "I don't have enough information on that"

SYSTEM_PROMPT = f"""You are a financial-aid assistant for Lehman College (CUNY) students.

Answer using ONLY the information in the Context block below. The context is labeled
[Source N: filename] for each chunk. Do not use any prior knowledge, general knowledge,
training data, or plausible-sounding inference. Do not fabricate dates, amounts,
deadlines, URLs, eligibility rules, or procedures that are not explicitly stated in
the context.

If the context does not contain enough information to answer the question, respond
with EXACTLY this sentence and nothing else: "{REFUSAL}".

When the context is sufficient, write a direct, plain-prose answer. Do not include
inline citations or "[Source N]" markers — the UI shows sources in a separate panel.
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


def answer(query: str) -> tuple[str, str]:
    if not query or not query.strip():
        return "", ""
    chunks = retrieve(query, k=TOP_K)
    user_msg = f"Context:\n{format_context(chunks)}\n\nQuestion: {query}"
    response = _get_client().models.generate_content(
        model=MODEL,
        contents=user_msg,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=TEMPERATURE,
        ),
    )
    return response.text.strip(), format_sources(chunks)


with gr.Blocks(title="Lehman Financial Aid Assistant") as demo:
    gr.Markdown("# Lehman Financial Aid Assistant")
    gr.Markdown(
        "Ask about FAFSA, TAP, SAP, Excelsior, withdrawals, and CUNYfirst at Lehman College. "
        "Answers are grounded only in the indexed documents."
    )
    query_in = gr.Textbox(label="Your question", lines=2, placeholder="e.g. What is the income limit for the Excelsior Scholarship?")
    ask_btn = gr.Button("Ask", variant="primary")
    answer_out = gr.Textbox(label="Answer", lines=8, interactive=False)
    gr.Markdown("### Sources")
    sources_out = gr.Markdown(value="*Ask a question above to see retrieved sources here.*")

    ask_btn.click(answer, inputs=query_in, outputs=[answer_out, sources_out])
    query_in.submit(answer, inputs=query_in, outputs=[answer_out, sources_out])


if __name__ == "__main__":
    demo.launch()
