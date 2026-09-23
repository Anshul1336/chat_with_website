from flask import Flask, request, jsonify
import json
import sqlite3
from langchain_community.document_loaders import ScrapingAntLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
from uuid import uuid4
import google.generativeai as genai
import time
import threading

from dotenv import load_dotenv
import os

load_dotenv()

model = SentenceTransformer("all-MiniLM-L6-v2")
pc = Pinecone(
    api_key=os.getenv("PINECONE_API_KEY")
)
MAX_INDEXES = 5

app = Flask(__name__)

db = sqlite3.connect(os.getenv("DB_PATH", "chat.db"), check_same_thread=False)
db.row_factory = sqlite3.Row
db.execute("PRAGMA foreign_keys = ON")

db.execute("""
    CREATE TABLE IF NOT EXISTS data_url (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT,
    vd_index TEXT
    )""")
db.execute("""
    CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt TEXT,
    response TEXT,
    data_id INTEGER,
    tim TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (data_id) REFERENCES data_url(id)
    )""")
db.commit()

@app.route('/data', methods=['POST'])
def data():
    cur = db.cursor()
    data = request.json
    url = str(data.get('url')).strip()
    if not url:
        return jsonify({"error": "URL is required"}), 400

    #checking if the url is already processed
    cur.execute("SELECT vd_index, id FROM data_url WHERE url = ?", (url,))
    result = cur.fetchone()

    if result:
        index_name = result['vd_index']
        return jsonify({
            "message": "Data already processed for this URL",
            "index_name": index_name,
            "data_id": result['id']
        }), 200

    # Generate a new index name using uuid4
    index_name = f"index-{uuid4().hex[:8]}"

    # scrape in the background while we sort out eviction + index creation below
    scrape_result = {}
    def scrape():
        try:
            loader = ScrapingAntLoader(
                [url],
                api_key=os.getenv("SCRAPINGANT_API_KEY"),
                continue_on_failure=True,
            )
            scrape_result["documents"] = loader.load()
        except Exception as e:
            scrape_result["error"] = str(e)

    scrape_thread = threading.Thread(target=scrape)
    scrape_thread.start()

    # Pinecone itself is the source of truth for how many indexes exist
    existing_indexes = pc.list_indexes().names()

    if len(existing_indexes) >= MAX_INDEXES:
        cur.execute("SELECT id, vd_index FROM data_url ORDER BY id ASC LIMIT 1")
        oldest = cur.fetchone()
        if not oldest:
            scrape_thread.join()
            return jsonify({
                "error": "Index limit reached but no DB record to evict. Clear Pinecone manually."
            }), 500

        old_index = oldest["vd_index"]

        if old_index in existing_indexes:
            pc.delete_index(old_index)

            # wait until Pinecone confirms deletion (checked twice a second)
            for _ in range(60):
                time.sleep(0.5)
                if old_index not in pc.list_indexes().names():
                    break
            else:
                scrape_thread.join()
                return jsonify({"error": "Pinecone index deletion timeout"}), 500

        cur.execute("DELETE FROM messages WHERE data_id = ?", (oldest["id"],))
        cur.execute("DELETE FROM data_url WHERE id = ?", (oldest["id"],))
        db.commit()

        # re-check for real after the eviction, don't trust the old count
        existing_indexes = pc.list_indexes().names()
        if len(existing_indexes) >= MAX_INDEXES:
            scrape_thread.join()
            return jsonify({"error": "Index limit reached. Cleanup failed."}), 500

    try:
        pc.create_index(
            name=index_name,
            dimension=384,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
    except Exception:
        scrape_thread.join()
        return jsonify({
            "error": "Pinecone index limit reached (max 5). Delete old data or use namespaces."
        }), 403

    scrape_thread.join()
    documents = scrape_result.get("documents")
    if not documents:
        pc.delete_index(index_name)
        return jsonify({"error": "No content extracted from URL"}), 400

    index = pc.Index(index_name)

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(documents)

    texts = [doc.page_content for doc in chunks]
    if not texts:
        pc.delete_index(index_name)
        return jsonify({"error": "No text chunks generated"}), 400

    # adding vector embeddings
    embeddings = model.encode(texts).tolist()
    uuids = [str(uuid4()) for _ in range(len(chunks))]
    metadata = [{"text": t.page_content} for t in chunks]

    # upserting the vectors to the index
    index.upsert(vectors= [(uuids[i], embeddings[i], metadata[i]) for i in range(len(chunks))])

    # inserting into db
    cur.execute(
        "INSERT INTO data_url (url, vd_index) VALUES (?, ?)",
        (url, index_name)
    )

    # saving the db
    db.commit()
    return jsonify({
        "message" : f"Data processed and stored successfully in Index: {index_name}",
    })

@app.route('/data/chat', methods=['POST'])
def chat():
    data = request.json
    url = data.get('url')
    query = data.get('query')
    if not query or not url:
        return jsonify({"error": "Both query and url are required"}), 400

    # vector embeddings of query
    vector_query = model.encode(query).tolist()
    cur = db.cursor()

    cur.execute("SELECT vd_index, id FROM data_url WHERE url = ?", (url,))
    result = cur.fetchone()
    if not result:
        return jsonify({"error": "URL not found"}), 400

    index_name = result['vd_index']
    data_id = result['id']

    index = pc.Index(index_name)

    try:
        results = index.query(
            vector=vector_query,
            top_k=5,
            include_metadata=True
        )

        # comparison
        context = ''
        for match in results.matches:
            context += match['metadata']['text'] + '\n'

        prompt = f"{context} Now according to the above context answer some questions : {query}"

        genai.configure(
        api_key=os.getenv("GEMINI_API_KEY")
        )
        response = genai.GenerativeModel("gemini-flash-latest").generate_content(prompt)
    except Exception as e:
        return jsonify({"error": f"Failed to generate answer: {e}"}), 502

    cur.execute(
        "INSERT INTO messages(prompt, response, data_id) VALUES (?, ?, ?)",
        (query, response.text, data_id)
    )
    db.commit()

    return jsonify({
        "response": response.text,
        "data_id": data_id
    })

# history
@app.route('/data/messages', methods=['GET'])
def get_messages():
    cur = db.cursor()
    cur.execute("""
        SELECT
          m.id AS message_id,
          m.prompt,
          m.response,
          m.tim,
          d.url,
          d.vd_index
        FROM messages m
        JOIN data_url d ON m.data_id = d.id
        ORDER BY m.tim DESC
    """)
    messages = [dict(row) for row in cur.fetchall()]
    return jsonify(messages)

if __name__ == '__main__':
    app.run(debug=False, use_reloader=False, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
