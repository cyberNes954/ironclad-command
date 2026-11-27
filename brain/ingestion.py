import re
from pathlib import Path
import fitz
from youtube_transcript_api import YouTubeTranscriptApi
import trafilatura

KB_ROOT = Path("knowledge_base")
KB_ROOT.mkdir(parents=True, exist_ok=True)


def slugify(t):
    t = re.sub(r"[^\w\s-]", "", t.lower())
    return re.sub(r"[-\s]+", "-", t).strip("-")[:80] or "doc"


def ingest_pdf(file_bytes, filename, category="08_new"):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = "\n\n".join(p.get_text() for p in doc)
    doc.close()
    d = KB_ROOT / category
    d.mkdir(parents=True, exist_ok=True)
    p = d / (slugify(Path(filename).stem) + ".md")
    p.write_text("# " + filename + "\n\n" + text, encoding="utf-8")
    return str(p)


def ingest_youtube(url, category="08_new"):
    vid = _extract_yt_id(url)
    tr = YouTubeTranscriptApi.get_transcript(vid, languages=["en"])
    text = " ".join(e["text"] for e in tr)
    d = KB_ROOT / category
    d.mkdir(parents=True, exist_ok=True)
    p = d / ("yt-" + vid + ".md")
    p.write_text("Source: " + url + "\n\n" + text, encoding="utf-8")
    return str(p)


def ingest_url(url, category="08_new"):
    text = trafilatura.extract(trafilatura.fetch_url(url), include_comments=False)
    if not text:
        raise ValueError("Could not extract: " + url)
    d = KB_ROOT / category
    d.mkdir(parents=True, exist_ok=True)
    p = d / ("web-" + slugify(url.split("//")[-1][:40]) + ".md")
    p.write_text("Source: " + url + "\n\n" + text, encoding="utf-8")
    return str(p)


def _extract_yt_id(url):
    for pat in [r"v=([a-zA-Z0-9_-]{11})", r"youtu\.be/([a-zA-Z0-9_-]{11})"]:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    raise ValueError("Invalid YouTube URL")


def list_knowledge():
    out = {}
    for cat in sorted(KB_ROOT.iterdir()):
        if cat.is_dir():
            out[cat.name] = [f.name for f in cat.glob("*.md")]
    return out