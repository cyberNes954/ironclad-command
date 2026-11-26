import streamlit as st
from brain.agent import IroncladBrain
from brain.ingestion import ingest_pdf, ingest_youtube, ingest_url, list_knowledge
from voice_agent.cold_caller import ColdCallAgent

st.set_page_config(page_title="Ironclad Command", page_icon="🧠", layout="wide")

# Initialize session state
if "brain" not in st.session_state:
    st.session_state.brain = IroncladBrain()
if "caller" not in st.session_state:
    st.session_state.caller = ColdCallAgent()
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar
st.sidebar.title("🧠 IRONCLAD COMMAND")
st.sidebar.markdown("**Master Operations Brain**")
st.sidebar.markdown("Ironclad Logistic™")

kb = list_knowledge()
total = sum(len(v) for v in kb.values())
st.sidebar.metric("Knowledge Files", total)
st.sidebar.metric("Categories", len(kb))

# Tabs
tab_chat, tab_learn, tab_calls, tab_kb = st.tabs(["💬 Brain", "📚 Teach Me", "📞 Cold Calls", "🗂️ Knowledge"])

# --- BRAIN CHAT ---
with tab_chat:
    st.header("Talk to Ironclad Command")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("sources"):
                st.caption(f"📖 Sources: {', '.join(msg['sources'])}")
    
    if prompt := st.chat_input("Ask about operations, SOPs, rates..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = st.session_state.brain.ask(prompt)
                st.markdown(result["answer"])
                if result["sources"]:
                    st.caption(f"📖 Sources: {', '.join(result['sources'])}")
                st.session_state.messages.append({"role": "assistant", "content": result["answer"], "sources": result["sources"]})

# --- TEACH ME ---
with tab_learn:
    st.header("Teach the Brain")
    st.markdown("Upload documents, paste YouTube links, or drop blog URLs.")
    col1, col2 = st.columns(2)
    
    DEFAULT_CATS = ["01_acquisition", "02_onboarding", "03_equipment", "04_financial", "05_broker_relations", "06_vetting", "07_execution", "08_new"]
    categories = sorted(kb.keys()) if kb else DEFAULT_CATS
    
    with col1:
        st.subheader("📄 Upload PDFs")
        uploaded = st.file_uploader("Drag & drop", type=["pdf", "txt", "md"], accept_multiple_files=True)
        category = st.selectbox("Category", categories)
        if uploaded and st.button("Ingest", type="primary"):
            for f in uploaded:
                path = ingest_pdf(f.read(), f.name, category)
                st.success(f"✅ {f.name} → {path}")
            st.session_state.brain.rebuild_index()
            st.rerun()
            
    with col2:
        st.subheader("🔗 Learn from URL")
        url = st.text_input("YouTube or blog URL")
        if url and st.button("Learn", type="primary"):
            try:
                if "youtube" in url:
                    path = ingest_youtube(url, category)
                else:
                    path = ingest_url(url, category)
                st.success(f"✅ Learned → {path}")
                st.session_state.brain.rebuild_index()
                st.rerun()
            except Exception as e:
                st.error(f"❌ {e}")

# --- COLD CALLS ---
with tab_calls:
    st.header("📞 Cold Call Agent")
    st.info("This agent makes REAL phone calls using your 80/20 script.")
    action = st.radio("What do you want to do?", ["Create/Update Assistant", "Make a Call", "View Call History"])

    if action == "Create/Update Assistant":
        if st.button("Create Voice Assistant", type="primary"):
            try:
                result = st.session_state.caller.create_assistant()
                st.session_state.assistant_id = result["id"]
                st.success(f"✅ Assistant created: {result['id']}")
                st.code(result["id"])
            except Exception as e:
                st.error(f"❌ {e}")
    elif action == "Make a Call":
        assistant_id = st.text_input("Assistant ID", value=st.session_state.get("assistant_id", ""))
        phone = st.text_input("Carrier Phone (+1XXXXXXXXXX)")
        name = st.text_input("Carrier Name (optional)")
        if st.button("📞 MAKE CALL", type="primary"):
            try:
                result = st.session_state.caller.make_call(assistant_id, phone, name)
                st.success(f"✅ Call started! ID: {result['id']}")
            except Exception as e:
                st.error(f"❌ {e}")
    elif action == "View Call History":
        try:
            calls = st.session_state.caller.list_calls()
            for call in calls[:10]:
                with st.expander(f"{call.get('name', 'Call')} — {call.get('status', '?')}"):
                    st.json(call)
        except Exception as e:
            st.error(f"❌ {e}")

# --- KNOWLEDGE BASE ---
with tab_kb:
    st.header("Knowledge Base")
    for cat, files in kb.items():
        with st.expander(f"**{cat}** ({len(files)} files)"):
            for f in files:
                st.write(f"• {f}")
    if st.button("🔄 Rebuild Index"):
        st.session_state.brain.rebuild_index()
        st.success("Done.")