# Chat with Any URL

A small RAG project — drop in any public webpage and ask it questions. It scrapes the page, embeds the text, stores the vectors in Pinecone, and answers you with Gemini using whatever's actually relevant on that page.

Built this mostly to understand how a full RAG pipeline fits together end to end, not just the "call an LLM" part.

## What it actually does

- Paste a URL, it gets scraped and indexed
- Ask questions, get answers grounded in that page's content (not the model just guessing)
- Ask about the same URL again later and it skips re-processing, just chats
- Keeps a running history of everything you've asked, across every URL

## The catch: Pinecone's free tier

Free tier caps you at 5 indexes. Once you're at the limit, processing a 6th URL automatically deletes the oldest one — its vectors and its chat history both go. So this isn't a permanent archive, it's more like a rolling window of your last 5 pages. If you need URL #1 again after that, it'll just get re-scraped from scratch.

## Stack

- **Backend:** Flask
- **Frontend:** Streamlit
- **Vectors:** Pinecone (free tier)
- **LLM:** Gemini
- **Embeddings:** sentence-transformers (`all-MiniLM-L6-v2`, runs locally, no API cost)
- **Scraping:** ScrapingAnt
- **Storage:** SQLite — just a local file, nothing to install or configure

## Running it locally

```
pip install -r requirements.txt
python project.py                  # backend → localhost:5000
streamlit run streamlit_ui.py      # frontend → localhost:8501
```

You need a `.env` file with:

```
PINECONE_API_KEY=
SCRAPINGANT_API_KEY=
GEMINI_API_KEY=
```

No database setup required — SQLite creates `chat.db` and both tables automatically the first time you run the backend.

## Worth knowing before you use it

- Some sites just block scraping outright, nothing the app can do about that
- Big pages take a while to process — the scraping step is the slow part, not the AI
- If Pinecone's at its cap and cleanup hits a snag mid-eviction, you get a real error back instead of the app silently corrupting its own state
- This was originally built against a local MySQL setup — moved to SQLite since there was no real reason to run a separate database server for something this small

## Deploying

Backend and frontend deploy separately:

- **Backend** → any host that'll run a Flask app (Railway, Render, etc). Set the three API keys above as environment variables there.
- **Frontend** → Streamlit Community Cloud is the easiest option, point it at `streamlit_ui.py` and set `BACKEND_URL` in its secrets to wherever the backend ends up living.
