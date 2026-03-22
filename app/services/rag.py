"""
RAG Pipeline:
1. Embed pertanyaan
2. Cosine similarity vs semua chunk di MySQL
3. Ambil Top-K chunk paling relevan
4. Kirim ke Gemini Flash → jawaban
5. Simpan hasil ke DB
"""
import numpy as np
import google.generativeai as genai
from sqlalchemy.orm import Session

from app.config import settings
from app.models.document import DocumentChunk
from app.models.qa import Question, Answer, RelevantChunk
from .embedding import embed


# ── Similarity ─────────────────────────────────────────────────────────────────

def cosine_similarity(a: list, b: list) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


# ── Retrieval ──────────────────────────────────────────────────────────────────

def retrieve(question_vector: list, db: Session) -> list[dict]:
    """Ambil Top-K chunk paling relevan dari MySQL."""
    chunks = (
        db.query(
            DocumentChunk.id,
            DocumentChunk.content,
            DocumentChunk.embedding,
            DocumentChunk.document_id,
        )
        .join(DocumentChunk.document)
        .filter(DocumentChunk.embedding.isnot(None))
        .all()
    )

    if not chunks:
        return []

    # Hitung similarity untuk setiap chunk
    scored = []
    for chunk in chunks:
        score = cosine_similarity(question_vector, chunk.embedding)
        scored.append({
            'chunk_id': chunk.id,
            'content': chunk.content,
            'score': score,
        })

    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored[: settings.top_k_chunks]


# ── Generation ─────────────────────────────────────────────────────────────────

def build_prompt(question: str, chunks: list[dict], doc_titles: dict) -> str:
    context = '\n\n'.join(
        f"[Sumber {i+1}: {doc_titles.get(c['chunk_id'], 'Dokumen')}]\n{c['content']}"
        for i, c in enumerate(chunks)
    )
    return f"""Kamu adalah asisten AI yang menjawab pertanyaan berdasarkan dokumen yang tersedia.
Jawablah hanya berdasarkan konteks berikut. Jika informasi tidak ada, katakan dengan jujur.

=== KONTEKS ===
{context}
===============

Pertanyaan: {question}
Jawaban:"""


def generate(question: str, chunks: list[dict], doc_titles: dict) -> str:
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY belum diisi di file .env")

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)
    prompt = build_prompt(question, chunks, doc_titles)
    response = model.generate_content(prompt)
    return response.text


# ── Pipeline Utama ─────────────────────────────────────────────────────────────

def ask(question_text: str, db: Session) -> dict:
    # 1. Embed pertanyaan
    q_vector = embed([question_text])[0]

    # 2. Retrieve chunk relevan
    top_chunks = retrieve(q_vector, db)

    if not top_chunks:
        return {
            'question_id': '',
            'answer_id': '',
            'question': question_text,
            'answer': 'Belum ada dokumen yang diupload. Silakan upload dokumen terlebih dahulu.',
            'confidence_score': 0.0,
            'sources': [],
        }

    # 3. Ambil judul dokumen untuk setiap chunk
    chunk_ids = [c['chunk_id'] for c in top_chunks]
    rows = (
        db.query(DocumentChunk.id, DocumentChunk.document_id)
        .filter(DocumentChunk.id.in_(chunk_ids))
        .all()
    )
    from app.models.document import Document
    doc_ids = list({r.document_id for r in rows})
    docs = db.query(Document.id, Document.title).filter(Document.id.in_(doc_ids)).all()
    doc_title_map = {d.id: d.title for d in docs}
    chunk_doc_map = {r.id: doc_title_map.get(r.document_id, 'Dokumen') for r in rows}

    # 4. Generate jawaban
    answer_text = generate(question_text, top_chunks, chunk_doc_map)

    # 5. Hitung confidence
    confidence = sum(c['score'] for c in top_chunks) / len(top_chunks)

    # 6. Simpan ke DB
    question_obj = Question(text=question_text, embedding=q_vector)
    db.add(question_obj)
    db.flush()

    answer_obj = Answer(
        question_id=question_obj.id,
        text=answer_text,
        confidence_score=confidence,
    )
    db.add(answer_obj)
    db.flush()

    for rank, chunk_data in enumerate(top_chunks):
        db.add(RelevantChunk(
            question_id=question_obj.id,
            chunk_id=chunk_data['chunk_id'],
            similarity_score=chunk_data['score'],
            rank=rank,
        ))

    db.commit()

    return {
        'question_id': question_obj.id,
        'answer_id': answer_obj.id,
        'question': question_text,
        'answer': answer_text,
        'confidence_score': round(confidence, 4),
        'sources': [
            {
                'document': chunk_doc_map.get(c['chunk_id'], 'Dokumen'),
                'similarity_score': round(c['score'], 4),
                'excerpt': c['content'][:200] + '...' if len(c['content']) > 200 else c['content'],
            }
            for c in top_chunks
        ],
    }
