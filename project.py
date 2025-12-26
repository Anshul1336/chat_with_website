from flask import Flask, request, jsonify
import json
import MySQLdb
from langchain_community.document_loaders import ScrapingAntLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from uuid import uuid4
import google.generativeai as genai
from langchain_community.document_loaders import RecursiveUrlLoader
import time

model = SentenceTransformer("all-MiniLM-L6-v2")
pc = Pinecone(api_key="Enter your pinecone API key")

app = Flask(__name__)

db = MySQLdb.connect(
    host="localhost",
    user="root",
    password="MySQL@1336",
    database="chat"
)

@app.route('/data', methods=['POST'])
def data():
    cur = db.cursor(MySQLdb.cursors.DictCursor)
    data = request.json
    url = str(data.get('url')).strip()
    if not url:
        return jsonify({"error": "URL is required"}), 400

    #checking if the url is already processed
    cur.execute("SELECT vd_index, id FROM data_URL WHERE url = %s", (url,))
    result = cur.fetchone()
    
    if result:
        index_name = result['vd_index']
        return jsonify({
            "message": "Data already processed for this URL",
            "index_name": index_name,
            "data_id": result['id']
        }), 200

    #extraction
    scrapingant_loader = ScrapingAntLoader(
    [url],
    api_key="Enter your scrapingant API key",
    continue_on_failure=True,
    )
    documents = scrapingant_loader.load()
    if not documents:
        return jsonify({"error": "No content extracted from URL"}), 400

    # Generate a new index name using uuid4
    index_name = f"index-{uuid4().hex[:8]}"

    # counting number of rows
    cur.execute("""
    SELECT id, vd_index 
    FROM data_url 
    ORDER BY id ASC 
    LIMIT 1
    """)
    rows = cur.fetchall()
    cur.execute("SELECT COUNT(*) AS c FROM data_url")
    db_count = cur.fetchone()["c"]

    if db_count >= 5:
        if not rows:
            return jsonify({
                "error": "Index limit reached but no DB records to delete. Clear Pinecone manually."
            }), 500

        old = rows[0]
        old_index = old["vd_index"]

        if old_index in pc.list_indexes():
            pc.delete_index(old_index)

        # ⏳ WAIT until Pinecone confirms deletion
        for _ in range(30):
            time.sleep(1)
            if old_index not in pc.list_indexes():
                break
        else:
            return jsonify({"error": "Pinecone index deletion timeout"}), 500

        cur.execute("DELETE FROM messages WHERE data_id = %s", (old["id"],))
        cur.execute("DELETE FROM data_url WHERE id = %s", (old["id"],))
        db.commit()

    indexes = pc.list_indexes()

    # stop if index is filled
    # continue if not by creating an index
    if index_name not in indexes:
        if db_count >= 5:
            return jsonify({"error": "Index limit reached. Cleanup failed."}), 500
        else:
            try:
                pc.create_index(
                    name=index_name,
                    dimension=384,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                )
            except Exception:
                return jsonify({
                    "error": "Pinecone index limit reached (max 5). Delete old data or use namespaces."
                }), 403

    index = pc.Index(index_name)
        
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(documents)
    
    texts= [doc.page_content for doc in chunks]
    if not texts:
        return jsonify({"error": "No text chunks generated"}), 400

    # adding vector embeddings
    embeddings = model.encode(texts).tolist()
    uuids = [str(uuid4()) for _ in range(len(chunks))]
    metadata = [{"text": t.page_content} for t in chunks]

    # upserting the vectors to the index
    index.upsert(vectors= [(uuids[i], embeddings[i], metadata[i]) for i in range(len(chunks))])

    # inserting into db
    cur.execute(
        "INSERT INTO data_url (url, vd_index) VALUES (%s, %s)",
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
      # 🔥 MUST be passed now
    if not query or not url:
        return jsonify({"error": "Both query and url are required"}), 400

    # vector embeddings of query
    vector_query = model.encode(query).tolist()
    cur = db.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("SELECT vd_index, id FROM data_url WHERE url = %s", (url,))
    result = cur.fetchone()
    if not result:
        return jsonify({"error": "URL not found"}), 400

    index_name = result['vd_index']
    data_id = result['id']

    index = pc.Index(index_name)

    results = index.query(
        vector=vector_query,
        top_k=5,
        include_metadata=True
    )

    # comparison
    context = ''
    for result in results.matches:
        context += result['metadata']['text'] + '\n'

    prompt = f"{context} Now according to the above context answer some questions : {query}"

    genai.configure(api_key="Enter your gemini API key")
    response = genai.GenerativeModel("gemini-flash-latest").generate_content(prompt)

    cur.execute("SELECT id FROM data_url WHERE url = %s", (url,))
    result = cur.fetchone()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
        id INT AUTO_INCREMENT PRIMARY KEY,
        prompt TEXT,
        response TEXT,
        data_id INT,
        tim TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (data_id) REFERENCES data_URL(id)
        )""")
    db.commit()

    if not result:
        return jsonify({"error": "data_id not found for given URL"}), 404

    data_id = result['id']
    cur.execute(
        "INSERT INTO messages(prompt, response, data_id) VALUES (%s, %s, %s)",
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
    cur = db.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT 
          m.id AS message_id,
          m.prompt,
          m.response,
          m.tim,
          d.url,
          d.vd_index
        FROM messages m
        JOIN data_URL d ON m.data_id = d.id
        ORDER BY m.tim DESC
    """)
    messages = cur.fetchall()
    return jsonify(messages)

if __name__ == '__main__':
    # app.run(debug=False, use_reloader=False)
    app.run(debug=True)
