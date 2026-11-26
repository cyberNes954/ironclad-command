import os, re
from pathlib import Path
import fitz
from youtube_transcript_api import YouTubeTranscriptApi
import trafilatura

KB_ROOT = Path("knowledge_base")
NEW_ZONE = KB_ROOT / "08_new"
NEW_ZONE.mkdir(parents=True, exist_ok=True)

def slugify(text):
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "-", text).strip("-")[:80]

def ingest_pdf(file_bytes, filename, category="08_new"):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = "\n\n".join(page.get_text() for page in doc)
    doc.close()
    title = Path(filename).stem
    target = KB_ROOT / category
    target.mkdir(parents=True, exist_ok=True)
    out_path = target / f"{slugify(title)}.md"
    out_path.write_text(f"# {title}\n\n{text}", encoding="utf-8")
    return str(out_path)

def ingest_youtube(url, category="08_new"):
    video_id = _extract_yt_id(url)
    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
    text = " ".join(e["text"] for e in transcript)
    target = KB_ROOT / category
    target.mkdir(parents=True, exist_ok=True)
    out_path = target / f"yt-{video_id}.md"
    out_path.write_text(f"# YouTube: {video_id}\n\nSource: {url}\n\n{text}", encoding="utf-8")
    return str(out_path)

def ingest_url(url, category="08_new"):
    downloaded = trafilatura.fetch_url(url)
    text = trafilatura.extract(downloaded, include_comments=False)
    if not text:
        raise ValueError(f"Could not extract: {url}")
    slug = slugify(url.split("//")[-1].split("/")[0])
    target = KB_ROOT / category
    target.mkdir(parents=True, exist_ok=True)
    out_path = target / f"web-{slug}.md"
    out_path.write_text(f"# Web: {url}\n\n{text}", encoding="utf-8")
    return str(out_path)

def _extract_yt_id(url):
    for p in [r"v=([a-zA-Z0-9_-]{11})", r"youtu\.be/([a-zA-Z0-9_-]{11})"]:
        m = re.search(p, url)
        if m: return m.group(1)
    raise ValueError("Invalid YouTube URL")

def list_knowledge():
    result = {}
    for cat in sorted(KB_ROOT.iterdir()):
        if cat.is_dir():
            result[cat.name] = [f.name for f in cat.glob("*.md")]
    return result