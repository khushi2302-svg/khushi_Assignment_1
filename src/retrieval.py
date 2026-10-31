import re
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "knowledge_base" / "student_handbook.md"

def load_chunks():
    raw = POLICY_PATH.read_text(encoding="utf-8")
    chunks = []
    current_heading = "General"
    buffer = []
    for line in raw.splitlines():
        if line.startswith("#"):
            if buffer:
                body = " ".join(buffer).strip()
                if body:
                    chunks.append({"id": f"POL-{len(chunks)+1:02d}", "heading": current_heading, "text": body})
                buffer = []
            current_heading = line.lstrip("#").strip()
        elif line.strip():
            buffer.append(line.strip())
    if buffer:
        chunks.append({"id": f"POL-{len(chunks)+1:02d}", "heading": current_heading, "text": " ".join(buffer).strip()})
    return chunks

def search_policy(query, top_k=2):
    chunks = load_chunks()
    if not chunks:
        return []
    corpus = [c["heading"] + " " + c["text"] for c in chunks]
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1,2))
    matrix = vectorizer.fit_transform(corpus + [query])
    scores = cosine_similarity(matrix[-1], matrix[:-1]).ravel()
    ranked = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
    return [
        {"chunk_id": c["id"], "heading": c["heading"], "text": c["text"], "score": round(float(score), 3)}
        for score, c in ranked[:top_k] if score > 0
    ]
