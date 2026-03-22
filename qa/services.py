"""
Services untuk RAG pipeline:
1. Retrieval — cari chunk paling relevan dari MySQL
2. Generation — generate jawaban pakai Claude API
"""
import numpy as np
import anthropic
from django.conf import settings

from documents.models import DocumentChunk
from documents.services import generate_embeddings
from .models import Question, Answer, RelevantChunk


def cosine_similarity(vec_a: list, vec_b: list) -> float:
    """Hitung cosine similarity antara dua vector."""
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def retrieve_relevant_chunks(question_embedding: list, top_k: int = None) -> list[dict]:
    """
    Cari chunk paling relevan dari MySQL berdasarkan cosine similarity.
    Karena MySQL standar tidak punya native vector search,
    kita load semua embedding dan hitung similarity di Python.
    """
    top_k = top_k or settings.TOP_K_CHUNKS

    chunks = DocumentChunk.objects.filter(
        embedding__isnull=False,
        document__is_processed=True,
    ).values('id', 'content', 'embedding', 'document__title')

    if not chunks:
        return []

    scored = []
    for chunk in chunks:
        score = cosine_similarity(question_embedding, chunk['embedding'])
        scored.append({
            'chunk_id': chunk['id'],
            'content': chunk['content'],
            'document_title': chunk['document__title'],
            'similarity_score': score,
        })

    scored.sort(key=lambda x: x['similarity_score'], reverse=True)
    return scored[:top_k]


def build_prompt(question: str, relevant_chunks: list[dict]) -> str:
    """Bangun prompt untuk Claude dengan konteks dari dokumen."""
    context_parts = []
    for i, chunk in enumerate(relevant_chunks, 1):
        context_parts.append(
            f"[Sumber {i}: {chunk['document_title']}]\n{chunk['content']}"
        )
    context = '\n\n'.join(context_parts)

    return f"""Kamu adalah asisten AI yang menjawab pertanyaan berdasarkan dokumen yang tersedia.
Jawablah hanya berdasarkan konteks yang diberikan. Jika informasi tidak ada dalam konteks, katakan dengan jujur.

=== KONTEKS DOKUMEN ===
{context}
======================

Pertanyaan: {question}

Jawaban:"""


def generate_answer(question_text: str, context_chunks: list[dict]) -> str:
    """Generate jawaban menggunakan Claude API."""
    if not settings.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY belum dikonfigurasi di file .env")

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    prompt = build_prompt(question_text, context_chunks)

    message = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=1024,
        messages=[{'role': 'user', 'content': prompt}],
    )

    return message.content[0].text


def ask_question(question_text: str) -> dict:
    """
    Pipeline RAG lengkap:
    1. Embed pertanyaan
    2. Retrieve chunk relevan dari MySQL
    3. Generate jawaban dengan Claude
    4. Simpan hasil ke DB
    """
    # 1. Embed pertanyaan
    question_embedding = generate_embeddings([question_text])[0]

    # 2. Retrieve chunk relevan
    relevant_chunks = retrieve_relevant_chunks(question_embedding)

    if not relevant_chunks:
        return {
            'question': question_text,
            'answer': 'Tidak ada dokumen yang tersedia sebagai sumber pengetahuan. Silakan upload dokumen terlebih dahulu.',
            'sources': [],
            'confidence_score': 0.0,
        }

    # 3. Generate jawaban
    answer_text = generate_answer(question_text, relevant_chunks)

    # 4. Hitung confidence dari rata-rata top similarity score
    confidence = sum(c['similarity_score'] for c in relevant_chunks) / len(relevant_chunks)

    # 5. Simpan ke database
    question_obj = Question.objects.create(
        text=question_text,
        embedding=question_embedding,
    )
    answer_obj = Answer.objects.create(
        question=question_obj,
        text=answer_text,
        confidence_score=confidence,
    )

    for rank, chunk_data in enumerate(relevant_chunks):
        chunk = DocumentChunk.objects.get(pk=chunk_data['chunk_id'])
        RelevantChunk.objects.create(
            question=question_obj,
            chunk=chunk,
            similarity_score=chunk_data['similarity_score'],
            rank=rank,
        )

    return {
        'question_id': str(question_obj.id),
        'answer_id': str(answer_obj.id),
        'question': question_text,
        'answer': answer_text,
        'confidence_score': round(confidence, 4),
        'sources': [
            {
                'document': c['document_title'],
                'similarity_score': round(c['similarity_score'], 4),
                'excerpt': c['content'][:200] + '...' if len(c['content']) > 200 else c['content'],
            }
            for c in relevant_chunks
        ],
    }
