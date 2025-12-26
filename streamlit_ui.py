import streamlit as st
import requests

st.set_page_config(page_title="Chat with URL", layout="wide")

# --- SESSION STATE DEFAULTS ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "url" not in st.session_state:
    st.session_state.url = ""
if "data_id" not in st.session_state:
    st.session_state.data_id = None
if "url_input" not in st.session_state:
    st.session_state.url_input = ""
if "new_chat_trigger" not in st.session_state:
    st.session_state.new_chat_trigger = False

if "processed_urls" not in st.session_state:
    st.session_state.processed_urls = set()

# --- Handle New Chat Reset ---
if st.session_state.new_chat_trigger:
    st.session_state.chat_history = []
    st.session_state.url = ""
    st.session_state.data_id = None
    st.session_state.url_input = ""
    st.session_state.new_chat_trigger = False
    st.rerun()

# --- UI HEADER ---
st.title("🧠 Chat with Any URL")
st.subheader("Enter a URL to Begin")

# --- URL INPUT ---
url_input = st.text_input("Website URL", key="url_input")

# --- Start New Chat Button ---
if st.button("🔄 Start New Chat"):
    st.session_state.new_chat_trigger = True
    st.rerun()

# --- Process URL ---
if url_input:
    if url_input in st.session_state.processed_urls:
        st.info("This URL is already processed. You can start chatting.")
        st.session_state.url = url_input

    else:
        with st.spinner("🔍 Processing URL..."):
            response = requests.post(
                "http://localhost:5000/data",
                json={"url": url_input}
            )

            if response.status_code == 200:
                data = response.json()
                st.session_state.processed_urls.add(url_input)
                st.session_state.url = url_input
                st.session_state.data_id = data.get("data_id")
                st.success(data.get("message"))
            else:
                try:
                    st.error(response.json().get("error", "Failed"))
                except:
                    st.error("Backend error. Check Flask terminal.")

# --- CHAT UI ---
if st.session_state.url:
    st.subheader("💬 Ask a Question")
    user_query = st.text_input("Type your question", key="query_input")
    if st.button("Send"):

    # if user_query:
        chat_res = requests.post("http://localhost:5000/data/chat", json={
            "url": st.session_state.url,
            "query": user_query
        })

        if chat_res.status_code == 200:
            data = chat_res.json()
            answer = data.get("response", "No response.")
            st.session_state.chat_history.append({"role": "user", "content": user_query})
            st.session_state.chat_history.append({"role": "bot", "content": answer})
        else:
            st.error(chat_res.json().get("error", "Something went wrong."))

    # --- Chat History Section ---
    with st.expander("📜 Full Chat History", expanded=True):
        for msg in st.session_state.chat_history[::-1]:  # Newest at bottom
            if msg["role"] == "user":
                st.markdown(f"🧑 **You:** {msg['content']}")
            elif msg["role"] == "bot":
                st.markdown(f"🤖 **Bot:** {msg['content']}")

    # --- Latest Answer Highlight ---
    if st.session_state.chat_history:
        latest = st.session_state.chat_history[-1]
        if latest["role"] == "bot":
            st.success(f"**Latest Answer:** {latest['content']}")

else:
    st.info("🔗 Enter a URL above to begin chatting.")
