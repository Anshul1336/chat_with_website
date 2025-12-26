Chat with Any URL (RAG-based)

This is a local Retrieval-Augmented Generation (RAG) project that allows users to paste a website URL and ask questions based on the content of that page.
The system scrapes the webpage, generates embeddings, stores them in Pinecone, and answers questions using contextual retrieval with Google Gemini.

FEATURES

⦁	Chat with any public webpage

⦁	Context-aware answers (RAG)

⦁	Already processed URLs are reused

⦁	Automatic cleanup when Pinecone index limit is reached

⦁	Streamlit-based UI

⦁	Local MySQL database

TECH STACK

⦁	Backend: Flask

⦁	Frontend: Streamlit

⦁	Vector Database: Pinecone (Free tier)

⦁	LLM: Google Gemini

⦁	Embeddings: Sentence Transformers

⦁	Scraping: ScrapingAnt

⦁	Database: MySQL (local)

PROJECT FILES

⦁	project.py -> Flask backend (API + Pinecone logic)

⦁	streamlit_ui.py -> Streamlit frontend

⦁	README.md -> Instructions

PREREQUISITES

⦁	Python 3.9 or above

⦁	MySQL installed locally

⦁	Pinecone account (Free plan)

⦁	ScrapingAnt API key

⦁	Google Gemini API key

IMPORTANT PINECONE LIMITATION

⦁	Pinecone Free plan allows a maximum of 5 indexes

⦁	This project automatically:

  Deletes the oldest Pinecone index
 	
  Deletes related rows from the database

⦁	If Pinecone deletion fails, new URLs will NOT be processed

DATABASE SETUP

⦁	Create database:

  CREATE DATABASE chat;

⦁	Create table:

 	CREATE TABLE data_url (
 	id INT AUTO_INCREMENT PRIMARY KEY,
 	url TEXT,
 	vd_index TEXT
 	);

The messages table is created automatically by the backend.

HOW TO RUN

⦁	requirements file:		pip install -r requirements.txt

⦁	Start backend:		python project.py

⦁	Backend runs at:		http://localhost:5000

⦁	Start frontend:		streamlit run streamlit_ui.py

HOW TO USE

⦁	Paste a website URL

⦁	Wait for processing

⦁	Ask questions related to that webpage

⦁	Chat using retrieved context

BEHAVIOR NOTES

⦁	Same URL is not processed again

⦁	Works locally only

⦁	Internet connection required

⦁	Some websites may block scraping

COMMON ERRORS

⦁	403 Pinecone error → Index limit reached

⦁	500 error → Scraping failed or Pinecone sync delay

⦁	JSONDecodeError → Backend crashed before response



⚠️ This project is designed to be run locally.
Live deployment is not included due to API cost and index limits.
