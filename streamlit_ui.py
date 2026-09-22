import streamlit as st
import requests
import os

try:
    BACKEND_URL = st.secrets["BACKEND_URL"]
except Exception:
    BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:5000")

st.set_page_config(page_title="Chat with URL")

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
                f"{BACKEND_URL}/data",
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
                except Exception:
                    st.error("Backend error. Check Flask terminal.")

# --- CHAT UI ---
if st.session_state.url:
    st.subheader("💬 Ask a Question")

    # --- Latest Answer, shown above the history ---
    if st.session_state.chat_history:
        latest = st.session_state.chat_history[-1]
        if latest["role"] == "assistant":
            st.success(f"**Latest Answer:** {latest['content']}")

    # --- Chat History Section ---
    with st.expander("📜 Full Chat History", expanded=True):
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    user_query = st.chat_input("Type your question")
    if user_query:
        with st.spinner("🤔 Thinking..."):
            chat_res = requests.post(f"{BACKEND_URL}/data/chat", json={
                "url": st.session_state.url,
                "query": user_query
            })

            if chat_res.status_code == 200:
                data = chat_res.json()
                answer = data.get("response", "No response.")
                st.session_state.chat_history.append({"role": "user", "content": user_query})
                st.session_state.chat_history.append({"role": "assistant", "content": answer})
                st.rerun()
            else:
                try:
                    st.error(chat_res.json().get("error", "Something went wrong."))
                except Exception:
                    st.error("Backend error. Check Flask terminal.")

else:
    st.info("🔗 Enter a URL above to begin chatting.")

# --- All-time history across every URL, pulled straight from the backend ---
with st.expander("🗂️ All-Time History (every URL ever processed)"):
    if st.button("Load Full History"):
        resp = requests.get(f"{BACKEND_URL}/data/messages")
        if resp.status_code == 200:
            all_messages = resp.json()
            if not all_messages:
                st.info("No messages recorded yet.")
            for m in all_messages:
                st.markdown(f"**{m['url']}** — {m['tim']}")
                st.markdown(f"🧑 {m['prompt']}")
                st.markdown(f"🤖 {m['response']}")
                st.divider()
        else:
            st.error("Failed to load history.")
