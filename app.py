import os
import re
import json
import urllib.request
import urllib.error
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Ironclad Command", page_icon="🧠", layout="wide")


def key(n):
    try:
        if n in st.secrets:
            return str(st.secrets[n])
    except Exception:
        pass
    return os.environ.get(n, "")


GROQ = key("GROQ_API_KEY")
KB = Path("knowledge_base")
KB.mkdir(parents=True, exist_ok=True)
CATS = ["01_acquisition", "02_onboarding", "03_equipment", "04_financial",
        "05_broker_relations", "06_vetting", "07_execution", "08_new"]

SYSTEM = """You are IRONCLAD COMMAND - master operations brain of Ironclad Logistic,
a truck dispatch service in Fort Lauderdale, Florida (954) 634-2388.

Answer ONLY from the knowledge base below. Never guess. If the answer is not there, say:
"That is not in my knowledge base yet - upload the source."

BUSINESS RULES:
- No forced dispatch, ever. The carrier approves every load.
- Rates must be backed by CPM math (break-even plus 15-25 percent profit).
- No Rate Confirmation = No Dispatch.
- Notify the broker within 15 minutes when detention starts.
- Send POD to the broker within 2 hours of delivery.
- Vet carriers on SAFER before onboarding. Unsatisfactory rating = do not use.
- Dispatch fee = percent of gross line-haul, invoiced weekly on Friday.

STYLE: Direct, professional, no fluff. Name the document you used. Flag risks.

KNOWLEDGE BASE:
{context}"""


def docs():
    out = []
    for p in sorted(KB.rglob("*.md")):
        try:
            out.append((p.name, p.read_text(encoding="utf-8", errors="ignore")))
        except Exception:
            pass
    return out


def slug(t):
    t = re.sub(r"[^\w\s-]", "", t.lower())
    return re.sub(r"[-\s]+", "-", t).strip("-")[:80] or "doc"


def save(title, body, cat):
    d = KB / cat
    d.mkdir(parents=True, exist_ok=True)
    p = d / (slug(title) + ".md")
    p.write_text("# " + title + "\n\n" + body, encoding="utf-8")
    return str(p)


def ask(q):
    if not GROQ:
        return "GROQ_API_KEY missing. Add it in Streamlit Cloud, Settings, Secrets."
    ds = docs()
    if not ds:
        return "Knowledge base is empty. Upload your PDFs in the Teach Me tab."
    ctx = "\n\n".join("=== %s ===\n%s" % (n, t) for n, t in ds)[:280000]
    body = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": SYSTEM.format(context=ctx)},
            {"role": "user", "content": q},
        ],
        "temperature": 0.2,
        "max_tokens": 1024,
    }
    r = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": "Bearer " + GROQ,
                 "Content-Type": "application/json",
                 "User-Agent": "IroncladCommand/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(r, timeout=90) as resp:
            return json.loads(resp.read().decode("utf-8"))["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        return "Groq error %s: %s" % (e.code, e.read().decode("utf-8", "ignore")[:300])
    except Exception as e:
        return "Failed: %s" % e


D = docs()
st.sidebar.title("🧠 IRONCLAD COMMAND")
st.sidebar.caption("Ironclad Logistic")
st.sidebar.metric("Knowledge Files", len(D))
st.sidebar.write("Groq key:", "✅" if GROQ else "❌")

t1, t2, t3, t4 = st.tabs(["💬 Brain", "📚 Teach Me", "🗂️ Knowledge", "🔧 System"])

with t1:
    st.header("Talk to Ironclad Command")
    if "msgs" not in st.session_state:
        st.session_state.msgs = []
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
    if q := st.chat_input("Ask about SOPs, rates, compliance..."):
        st.session_state.msgs.append({"role": "user", "content": q})
        with st.chat_message("user"):
            st.markdown(q)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                a = ask(q)
            st.markdown(a)
        st.session_state.msgs.append({"role": "assistant", "content": a})

with t2:
    st.header("Teach the Brain")
    cat = st.selectbox("Category", CATS)
    ups = st.file_uploader("Upload PDFs", type=["pdf", "txt", "md"], accept_multiple_files=True)
    if ups and st.button("Ingest", type="primary"):
        import fitz
        for f in ups:
            raw = f.read()
            if f.name.lower().endswith(".pdf"):
                d = fitz.open(stream=raw, filetype="pdf")
                text = "\n\n".join(p.get_text() for p in d)
                d.close()
            else:
                text = raw.decode("utf-8", "ignore")
            st.success(save(f.name, text, cat))
        st.rerun()

    url = st.text_input("YouTube or blog URL")
    if url and st.button("Learn from link", type="primary"):
        try:
            if "youtu" in url:
                from youtube_transcript_api import YouTubeTranscriptApi
                vid = None
                for pat in [r"v=([a-zA-Z0-9_-]{11})", r"youtu\.be/([a-zA-Z0-9_-]{11})"]:
                    m = re.search(pat, url)
                    if m:
                        vid = m.group(1)
                if not vid:
                    st.error("Could not read that YouTube link.")
                else:
                    tr = YouTubeTranscriptApi.get_transcript(vid, languages=["en"])
                    st.success(save("yt-" + vid, "Source: " + url + "\n\n" + " ".join(e["text"] for e in tr), cat))
                    st.rerun()
            else:
                import trafilatura
                text = trafilatura.extract(trafilatura.fetch_url(url), include_comments=False)
                if not text:
                    st.error("Could not extract that page.")
                else:
                    st.success(save("web-" + url.split("//")[-1][:40], "Source: " + url + "\n\n" + text, cat))
                    st.rerun()
        except Exception as e:
            st.error(str(e))

with t3:
    st.header("Knowledge Base")
    if not D:
        st.info("Nothing uploaded yet. Go to Teach Me.")
    for n, t in D:
        with st.expander("%s (%d chars)" % (n, len(t))):
            st.text(t[:3000])

with t4:
    st.header("🔧 System")
    st.write("Groq key detected:", bool(GROQ))
    st.write("Knowledge files:", len(D))
    st.write("Repo root:", sorted(os.listdir(".")))