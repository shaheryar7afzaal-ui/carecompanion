"""
Phase 2: Query
Embed the question, retrieve the closest chunks, and have the LLM answer using only those.
Try it in the terminal:  python rag.py
"""

import chromadb
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DB_DIR = "chroma_db"
COLLECTION = "care_guides"
EMBED_MODEL = "text-embedding-3-small"   # MUST match ingest.py
CHAT_MODEL = "gpt-4o-mini"
TOP_K = 5

# Below this cosine similarity, we treat retrieval as "not grounded" and refuse.
# text-embedding-3 scores run lowish; relevant chunks are usually 0.35-0.65.
# Tune this by printing scores for good and bad questions.
MIN_SIMILARITY = 0.30

EMERGENCY_TERMS = [
    "chest pain", "can't breathe", "cannot breathe", "not breathing", "trouble breathing",
    "unconscious", "unresponsive", "won't wake", "stroke", "face drooping", "slurred speech",
    "seizure", "choking", "overdose", "took too many", "bleeding a lot", "hit her head",
    "hit his head", "hit their head", "suicid", "kill myself", "end my life",
]

EMERGENCY_MESSAGE = (
    "This sounds like it could be an emergency. Call 911 now, or your local emergency number. "
    "Stay with the person until help arrives."
)

NOT_GROUNDED_MESSAGE = (
    "I don't have reliable information on that in my caregiving guides. "
    "Please check with their doctor, nurse, or pharmacist."
)

SYSTEM_PROMPT = """You are CareCompanion, an assistant for family caregivers of older adults.

Rules:
- Answer ONLY using the numbered context provided. Do not use outside knowledge.
- If the context does not answer the question, say you don't know and suggest asking their doctor or pharmacist.
- Write in plain, warm language at a grade 6 reading level. Short sentences. Use a short bulleted list for steps.
- Never diagnose, and never tell someone to start, stop, or change a medication.
- If anything sounds urgent, tell them to call 911 first.
- Cite the context you used inline like [1] or [2]."""

client = OpenAI()
collection = chromadb.PersistentClient(path=DB_DIR).get_collection(COLLECTION)


def is_emergency(question: str) -> bool:
    q = question.lower()
    return any(term in q for term in EMERGENCY_TERMS)


def retrieve(question: str, k: int = TOP_K):
    """Embed the question with the SAME model as ingest, return the k nearest chunks."""
    q_vec = client.embeddings.create(model=EMBED_MODEL, input=[question]).data[0].embedding
    res = collection.query(
        query_embeddings=[q_vec],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    chunks = []
    for text, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        chunks.append({
            "text": text,
            "source": meta["source"],
            "page": meta["page"],
            "similarity": round(1 - dist, 3),   # cosine distance -> similarity
        })
    return chunks


def build_context(chunks):
    return "\n\n".join(
        f"[{i}] ({c['source']}, p.{c['page']})\n{c['text']}" for i, c in enumerate(chunks, start=1)
    )


def answer(question: str, history=None):
    """Returns {'answer': str, 'sources': list, 'status': 'ok'|'emergency'|'not_grounded'}."""
    # Guard 1: emergencies skip the LLM entirely
    if is_emergency(question):
        return {"answer": EMERGENCY_MESSAGE, "sources": [], "status": "emergency"}

    chunks = retrieve(question)

    # Guard 2: if nothing relevant was found, refuse instead of letting the model guess
    if not chunks or chunks[0]["similarity"] < MIN_SIMILARITY:
        return {"answer": NOT_GROUNDED_MESSAGE, "sources": chunks, "status": "not_grounded"}

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in (history or [])[-4:]:          # a little conversation memory
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({
        "role": "user",
        "content": f"CONTEXT:\n{build_context(chunks)}\n\nQUESTION: {question}",
    })

    resp = client.chat.completions.create(model=CHAT_MODEL, messages=messages, temperature=0.2)
    return {"answer": resp.choices[0].message.content, "sources": chunks, "status": "ok"}


if __name__ == "__main__":
    print("CareCompanion (type 'quit' to exit)\n")
    while True:
        q = input("You: ").strip()
        if q.lower() in {"quit", "exit"}:
            break
        result = answer(q)
        print("\n--- retrieved chunks ---")
        for c in result["sources"]:
            print(f"  {c['similarity']:.3f}  {c['source']} p.{c['page']}: {c['text'][:80]}...")
        print(f"\nCareCompanion [{result['status']}]:\n{result['answer']}\n")
