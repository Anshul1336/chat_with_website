# Chat with Any URL (RAG-based)

A local Retrieval-Augmented Generation (RAG) project that lets users paste a website URL and ask questions based on the content of that page. The system scrapes the webpage, generates embeddings, stores them in Pinecone, and answers questions using contextual retrieval with Google Gemini.

## Features

- Chat with any public webpage
- Context-aware answers (RAG)
- Already-processed URLs are reused
- Automatic cleanup when the Pinecone index limit is reached
- Streamlit-based UI
- Local MySQL database

## Tech stack

- **Backend:** Flask
- **Frontend:** Streamlit
- **Vector database:** Pinecone (free tier)
- **LLM:** Google Gemini
- **Embeddings:** Sentence Transformers
- **Scraping:** ScrapingAnt
- **Database:** MySQL (local)
## Project files

- `project.py` — Flask backend (API + Pinecone logic)
- `streamlit_ui.py` — Streamlit frontend
- `README.md` — Instructions

## Prerequisites

- Python 3.9 or above
- MySQL installed locally
- Pinecone account (free plan)
- ScrapingAnt API key
- Google Gemini API key

## Pinecone limitation

Pinecone's free plan allows a maximum of 5 indexes. This project automatically deletes the oldest Pinecone index and its related database rows once that limit is hit. If Pinecone deletion fails, new URLs will not be processed.
## Database setup

Create the database:

```sql
CREATE DATABASE chat;
```

Create the table:

```sql
CREATE TABLE data_url (
  id INT AUTO_INCREMENT PRIMARY KEY,
  url TEXT,
  vd_index TEXT
);
```

The `messages` table is created automatically by the backend.
## How to run

```bash
pip install -r requirements.txt

# Start backend (runs at http://localhost:5000)
python project.py

# Start frontend
streamlit run streamlit_ui.py
```

## How to use

1. Paste a website URL
2. Wait for processing
3. Ask questions related to that webpage
4. Chat using retrieved context

## Behavior notes

- Same URL is not processed again
- Works locally only
- Internet connection required
- Some websites may block scraping

## Common errors

| Error | Cause |
|---|---|
| 403 Pinecone error | Index limit reached |
| 500 error | Scraping failed or Pinecone sync delay |
| JSONDecodeError | Backend crashed before response |

> This project is designed to be run locally. Live deployment isn't included, due to API cost and index limits.
