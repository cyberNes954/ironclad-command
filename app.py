import os
import re
import json
import base64
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
VAPI = key("VAPI_API_KEY")
GH_TOKEN = key("GITHUB_TOKEN")
GH_REPO = key("GITHUB_REPO") or "cyberNes954/ironclad-command"

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
- Minimum rate must be GROSS of the dispatch fee so the fee never eats carrier profit.
- Evaluate every load on ALL miles including deadhead, never loaded miles only.
- No Rate Confirmation = No Dispatch.
- Notify the broker within 15 minutes when detention starts.
- Send POD to the broker within 2 hours of delivery.
- Vet carriers on SAFER before onboarding. Unsatisfactory rating = do not use.
- Unrated is NOT a red flag. Most carriers are unrated.
- Entity Type must read CARRIER. Broker-affiliated = double brokering risk.
- Dispatch fee = percent of gross line-haul, invoiced weekly on Friday.

STYLE: Direct, professional, no fluff. Name the document you used. Flag risks.

KNOWLEDGE BASE:
{context}"""

COLD_SCRIPT = """You are a professional dispatcher for Ironclad Logistic in Fort Lauderdale.
Follow the 80/20 rule: the carrier talks 80 percent, you talk 20. Diagnose before you pitch.
Ask equipment type, preferred lanes, how they get loads now, their cost per mile, target rate.
If they do not know their cost per mile, tell them that is where carriers get hurt.
Confirm their email, summarize their pain, then ask if it makes sense to take the next step.
Short natural sentences. Never monologue. Never sound desperate."""


def get_models():
    if "_models" in st.session_state:
        return st.session_state._models
    ids = []
    if GROQ:
        try:
            r = urllib.request.Request(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": "Bearer " + GROQ,
                         "User-Agent": "IroncladCommand/1.0"},
            )
            with urllib.request.urlopen(r, timeout=30) as resp:
                ids = sorted(m["id"] for m in json.loads(resp.read().decode("utf-8")).get("data", []))
        except Exception:
            ids = []
    st.session_state._models = ids
    return ids


def default_model(ids):
    prefer = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "meta-llama/llama-4-maverick-17b-128e-instruct",
        "qwen/qwen3-32b",
        "gemma2-9b-it",
    ]
    for p in prefer:
        if p in ids:
            return p
    skip = ("whisper", "guard", "embed", "tts", "playai", "distil")
    chat = [i for i in ids if not any(s in i.lower() for s in skip)]
    return chat[0] if chat else "llama-3.1-8b-instant"


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


def gh_save(path, text):
    if not GH_TOKEN:
        return False
    url = "https://api.github.com/repos/%s/contents/%s" % (GH_REPO, path)
    hdr = {"Authorization": "Bearer " + GH_TOKEN,
           "Accept": "application/vnd.github+json",
           "User-Agent": "IroncladCommand/1.0",
           "Content-Type": "application/json"}
    sha = None
    try:
        g = urllib.request.Request(url + "?ref=main", headers=hdr)
        with urllib.request.urlopen(g, timeout=30) as resp:
            sha = json.loads(resp.read().decode("utf-8")).get("sha")
    except Exception:
        sha = None
    body = {"message": "Knowledge update: " + path,
            "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
            "branch": "main"}
    if sha:
        body["sha"] = sha
    try:
        p = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                   headers=hdr, method="PUT")
        with urllib.request.urlopen(p, timeout=60):
            return True
    except Exception:
        return False


def save(title, body, cat):
    d = KB / cat
    d.mkdir(parents=True, exist_ok=True)
    rel = "%s/%s/%s.md" % ("knowledge_base", cat, slug(title))
    text = "# " + title + "\n\n" + body
    (KB / cat / (slug(title) + ".md")).write_text(text, encoding="utf-8")
    return rel, gh_save(rel, text)


def ask(q, model):
    if not GROQ:
        return "GROQ_API_KEY missing. Add it in Streamlit Cloud, Settings, Secrets."
    ds = docs()
    if not ds:
        return "Knowledge base is empty. Upload your PDFs in the Teach Me tab."
    ctx = "\n\n".join("=== %s ===\n%s" % (n, t) for n, t in ds)[:280000]
    body = {"model": model,
            "messages": [{"role": "system", "content": SYSTEM.format(context=ctx)},
                         {"role": "user", "content": q}],
            "temperature": 0.2,
            "max_tokens": 1024}
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
        detail = e.read().decode("utf-8", "ignore")[:300]
        return "Groq error %s on model '%s': %s\n\nModels available to your account: %s" % (
            e.code, model, detail, ", ".join(get_models()) or "none listed")
    except Exception as e:
        return "Failed: %s" % e


def vapi(method, path, body=None):
    import requests
    r = requests.request(method, "https://api.vapi.ai" + path,
                         headers={"Authorization": "Bearer " + VAPI,
                                  "Content-Type": "application/json"},
                         json=body, timeout=60)
    r.raise_for_status()
    return r.json()


MODELS = get_models()
DEF = default_model(MODELS)
D = docs()

st.sidebar.title("🧠 IRONCLAD COMMAND")
st.sidebar.caption("Ironclad Logistic")
st.sidebar.metric("Knowledge Files", len(D))
st.sidebar.write("Groq key:", "✅" if GROQ else "❌")
st.sidebar.write("Vapi key:", "✅" if VAPI else "❌")
st.sidebar.write("Permanent storage:", "✅" if GH_TOKEN else "⚠️ temporary")
if MODELS:
    idx = MODELS.index(DEF) if DEF in MODELS else 0
    MODEL = st.sidebar.selectbox("AI model", MODELS, index=idx)
else:
    MODEL = DEF
    st.sidebar.warning("Could not list models. Check Groq key.")
st.sidebar.caption("Using: " + MODEL)

t1, t2, t3, t4, t5 = st.tabs(["💬 Brain", "📚 Teach Me", "📞 Cold Calls", "🗂️ Knowledge", "🔧 System"])

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
                a = ask(q, MODEL)
            st.markdown(a)
        st.session_state.msgs.append({"role": "assistant", "content": a})

with t2:
    st.header("Teach the Brain")
    if not GH_TOKEN:
        st.warning("Uploads are temporary until you add GITHUB_TOKEN to Secrets. They will be lost on reboot.")
    cat = st.selectbox("Category", CATS)
    ups = st.file_uploader("Upload PDFs or text", type=["pdf", "txt", "md"], accept_multiple_files=True)
    if ups and st.button("Ingest", type="primary"):
        for f in ups:
            raw = f.read()
            if f.name.lower().endswith(".pdf"):
                try:
                    import fitz
                    d = fitz.open(stream=raw, filetype="pdf")
                    text = "\n\n".join(p.get_text() for p in d)
                    d.close()
                except Exception as e:
                    st.error("PDF read failed: %s" % e)
                    continue
            else:
                text = raw.decode("utf-8", "ignore")
            rel, saved = save(f.name, text, cat)
            st.success(("✅ permanent: " if saved else "⚠️ temporary: ") + rel)
        st.rerun()

    url = st.text_input("YouTube or blog URL")
    if url and st.button("Learn from link", type="primary"):
        try:
            if "youtu" in url:
                from youtube_transcript_api import YouTubeTranscriptApi
                vid = None
                for pat in [r"v=([a-zA-Z0-9_-]{11})", r"youtu\.be/([a-zA-Z0-9_-]{11})", r"shorts/([a-zA-Z0-9_-]{11})"]:
                    m = re.search(pat, url)
                    if m:
                        vid = m.group(1)
                if not vid:
                    st.error("Could not read that YouTube link.")
                else:
                    tr = YouTubeTranscriptApi.get_transcript(vid, languages=["en"])
                    body = "Source: " + url + "\n\n" + " ".join(e["text"] for e in tr)
                    rel, saved = save("yt-" + vid, body, cat)
                    st.success(("✅ permanent: " if saved else "⚠️ temporary: ") + rel)
                    st.rerun()
            else:
                import trafilatura
                text = trafilatura.extract(trafilatura.fetch_url(url), include_comments=False)
                if not text:
                    st.error("Could not extract that page.")
                else:
                    rel, saved = save("web-" + url.split("//")[-1][:40], "Source: " + url + "\n\n" + text, cat)
                    st.success(("✅ permanent: " if saved else "⚠️ temporary: ") + rel)
                    st.rerun()
        except Exception as e:
            st.error(str(e))

with t3:
    st.header("Cold Call Agent")
    if not VAPI:
        st.info