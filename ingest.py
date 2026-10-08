"""
Phase 1: Ingest
Load PDFs from docs/, split into overlapping chunks, embed them, store in Chroma.
Run once (or again whenever you add new documents):  python ingest.py
"""

from pathlib import Path

import chromadb
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader

load_dotenv()

DOCS_DIR = Path("docs")
DB_DIR = "chroma_db"
COLLECTION = "care_guides"
EMBED_MODEL = "text-embedding-3-small"   # 1536-dim vectors

CHUNK_WORDS = 350      # ~500 tokens
OVERLAP_WORDS = 50     # so ideas cut at a boundary still appear whole somewhere
BATCH_SIZE = 100       # chunks per embedding API call

client = OpenAI()


def load_pdfs(folder: Path):
    """Yield (text, metadata) for every page of every PDF."""
    for pdf_path in sorted(folder.glob("*.pdf")):
        reader = PdfReader(pdf_path)
        for page_num, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                yield text, {"source": pdf_path.stem, "page": page_num}


def chunk_text(text: str, size: int = CHUNK_WORDS, overlap: int = OVERLAP_WORDS):
    """Sliding window over words. Simple, predictable, easy to explain."""
    words = text.split()
    if len(words) <= size:
        return [" ".join(words)]
    chunks, start = [], 0
    while start < len(words):
        chunks.append(" ".join(words[start:start + size]))
        start += size - overlap
    return chunks


def embed(texts):
    """Turn a list of strings into a list of vectors."""
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [item.embedding for item in resp.data]


def main():
    if not DOCS_DIR.exists() or not any(DOCS_DIR.glob("*.pdf")):
        raise SystemExit("Put some PDFs in the docs/ folder first.")

    # 1 + 2: load and chunk
    ids, documents, metadatas = [], [], []
    for page_text, meta in load_pdfs(DOCS_DIR):
        for i, chunk in enumerate(chunk_text(page_text)):
            ids.append(f"{meta['source']}-p{meta['page']}-c{i}")
            documents.append(chunk)
            metadatas.append(meta)
    print(f"Created {len(documents)} chunks from {len(list(DOCS_DIR.glob('*.pdf')))} PDFs")

    # Fresh collection each run so re-ingesting doesn't duplicate chunks.
    # cosine = compare vectors by angle (meaning), not raw distance
    db = chromadb.PersistentClient(path=DB_DIR)
    try:
        db.delete_collection(COLLECTION)
    except Exception:
        pass
    collection = db.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})

    # 3 + 4: embed in batches and store
    for start in range(0, len(documents), BATCH_SIZE):
        end = start + BATCH_SIZE
        vectors = embed(documents[start:end])
        collection.add(
            ids=ids[start:end],
            documents=documents[start:end],
            metadatas=metadatas[start:end],
            embeddings=vectors,
        )
        print(f"  embedded {min(end, len(documents))}/{len(documents)}")

    print(f"Done. {collection.count()} chunks stored in ./{DB_DIR}")


if __name__ == "__main__":
    main()
