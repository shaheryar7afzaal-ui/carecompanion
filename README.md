# CareCompanion

A retrieval-augmented (RAG) assistant that answers family caregivers' questions using only trusted caregiving guides, with citations.

## How it works

**Ingest (once):** PDFs → split into ~500-token overlapping chunks → embedded with `text-embedding-3-small` (1536-dim) → stored in Chroma with source + page metadata.

**Query (every question):** emergency check → embed question → retrieve top 5 chunks by cosine similarity → refuse if best match is too weak → `gpt-4o-mini` answers using only those chunks, at a grade 6 reading level, with citations.

## Safety and accessibility

- Emergency phrases trigger a "call 911" message before any AI call
- Low retrieval similarity → "I don't know, ask their doctor" instead of guessing
- System prompt forbids diagnosis or medication changes
- Adjustable large text, read-aloud button, sources visible under every answer

## Run it

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
echo "OPENAI_API_KEY=sk-..." > .env
mkdir docs   # add caregiving PDFs here
python ingest.py
python rag.py          # terminal mode, shows retrieved chunks + scores
streamlit run app.py   # chat UI
python eval.py         # 10-question test set
```

## Next steps

- Hybrid search (vector + BM25) so exact drug names match reliably
- Reranking retrieved chunks
- Voice input for users who struggle to type
- Deploy on Azure (Blob Storage → AI Search → Azure OpenAI → App Service)
