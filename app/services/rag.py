"""
Hybrid RAG Pipeline:

1. Embed pertanyaan → retrieve chunk dokumen relevan
2. Load system instructions dari DB
3. [Jika MIS aktif] Generate SQL → eksekusi ke MIS DB → ambil data real
4. Gabungkan dokumen + data real + instruksi → Gemini → jawaban final
5. Simpan ke DB
"""
import numpy as np
import google.generativeai as genai
from sqlalchemy.orm import Session

from app.config import settings
from app.models.document import Document, DocumentChunk
from app.models.instruction import SystemInstruction
from app.models.qa import Question, Answer, RelevantChunk
from .embedding import embed
from .text_to_sql import run_text_to_sql


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
    chunks = (
        db.query(DocumentChunk.id, DocumentChunk.content, DocumentChunk.embedding, DocumentChunk.document_id)
        .join(DocumentChunk.document)
        .filter(DocumentChunk.embedding.isnot(None))
        .all()
    )
    if not chunks:
        return []

    scored = [
        {'chunk_id': c.id, 'content': c.content, 'score': cosine_similarity(question_vector, c.embedding)}
        for c in chunks
    ]
    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored[: settings.top_k_chunks]


# ── System Instructions ────────────────────────────────────────────────────────

def load_instructions(db: Session) -> dict[str, str]:
    """
    Load instruksi aktif dari DB, dikelompokkan per kategori.
    Return dict: {'schema': '...', 'rule': '...', 'all': '...'}
    """
    instructions = (
        db.query(SystemInstruction)
        .filter(SystemInstruction.is_active == True)
        .order_by(SystemInstruction.order, SystemInstruction.category)
        .all()
    )

    category_labels = {
        'schema':  'DATABASE SCHEMA & TABLE MAPPING',
        'rule':    'BUSINESS RULES',
        'formula': 'CALCULATION FORMULAS',
        'context': 'BUSINESS CONTEXT',
        'general': 'GENERAL INSTRUCTIONS',
    }

    groups: dict[str, list[str]] = {}
    for inst in instructions:
        groups.setdefault(inst.category, []).append(inst.content)

    # Teks per kategori (untuk Text-to-SQL: hanya butuh schema + formula)
    schema_parts = []
    all_parts = []

    for category, items in groups.items():
        label = category_labels.get(category, category.upper())
        block = f"[{label}]\n" + '\n'.join(f"- {i}" for i in items)
        all_parts.append(block)
        if category in ('schema', 'formula', 'rule'):
            schema_parts.append(block)

    return {
        'schema': '\n\n'.join(schema_parts),   # untuk generate SQL
        'all': '\n\n'.join(all_parts),          # untuk prompt jawaban
    }


# ── Prompt Builder ─────────────────────────────────────────────────────────────

def build_final_prompt(
    question: str,
    chunks: list[dict],
    doc_titles: dict,
    instructions_all: str,
    data_result: str | None,
    sql_query: str | None,
) -> str:

    # Blok instruksi
    instr_block = f"\n=== SYSTEM INSTRUCTIONS ===\n{instructions_all}\n===========================\n" \
        if instructions_all else ''

    # Blok dokumen
    if chunks:
        context = '\n\n'.join(
            f"[Sumber {i+1}: {doc_titles.get(c['chunk_id'], 'Dokumen')}]\n{c['content']}"
            for i, c in enumerate(chunks)
        )
        doc_block = f"\n=== KONTEKS DOKUMEN ===\n{context}\n=======================\n"
    else:
        doc_block = ''

    # Blok data real dari MIS
    if data_result:
        data_block = (
            f"\n=== DATA DARI DATABASE MIS ===\n"
            f"Query: {sql_query}\n\n"
            f"Hasil:\n{data_result}\n"
            f"==============================\n"
        )
    else:
        data_block = ''

    return (
        f"Kamu adalah asisten AI internal yang membantu menjawab pertanyaan bisnis.\n"
        f"Gunakan semua informasi yang tersedia di bawah ini untuk menjawab dengan akurat.\n"
        f"Jika data tidak tersedia, katakan dengan jujur.\n"
        f"{instr_block}"
        f"{doc_block}"
        f"{data_block}"
        f"\nPertanyaan: {question}\n"
        f"Jawaban:"
    )


# ── Generation ─────────────────────────────────────────────────────────────────

def generate_answer(prompt: str) -> str:
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY belum diisi di file .env")
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)
    return model.generate_content(prompt).text


# ── Pipeline Utama ─────────────────────────────────────────────────────────────

def ask(question_text: str, db: Session) -> dict:
    # 1. Embed pertanyaan
    q_vector = embed([question_text])[0]

    # 2. Retrieve chunk dokumen
    top_chunks = retrieve(q_vector, db)

    # 3. Load instruksi sistem
    instructions = load_instructions(db)

    # 4. Text-to-SQL (jika MIS DB aktif)
    sql_result = {'sql': None, 'formatted_result': None, 'row_count': 0, 'error': None}
    if settings.mis_db_enabled and instructions['schema']:
        sql_result = run_text_to_sql(question_text, instructions['schema'])

    # 5. Jika tidak ada data sama sekali
    has_context = top_chunks or sql_result['formatted_result'] or instructions['all']
    if not has_context:
        return {
            'question_id': '', 'answer_id': '',
            'question': question_text,
            'answer': 'Belum ada dokumen, instruksi, atau koneksi database yang tersedia.',
            'confidence_score': 0.0,
            'sources': [],
            'sql_query': None, 'query_result_count': 0, 'data_error': None,
        }

    # 6. Buat peta judul dokumen
    chunk_doc_map = {}
    if top_chunks:
        chunk_ids = [c['chunk_id'] for c in top_chunks]
        rows = db.query(DocumentChunk.id, DocumentChunk.document_id).filter(DocumentChunk.id.in_(chunk_ids)).all()
        doc_ids = list({r.document_id for r in rows})
        docs = db.query(Document.id, Document.title).filter(Document.id.in_(doc_ids)).all()
        doc_title_map = {d.id: d.title for d in docs}
        chunk_doc_map = {r.id: doc_title_map.get(r.document_id, 'Dokumen') for r in rows}

    # 7. Build prompt dan generate jawaban
    prompt = build_final_prompt(
        question=question_text,
        chunks=top_chunks,
        doc_titles=chunk_doc_map,
        instructions_all=instructions['all'],
        data_result=sql_result['formatted_result'],
        sql_query=sql_result['sql'],
    )
    answer_text = generate_answer(prompt)

    # 8. Hitung confidence
    confidence = (
        sum(c['score'] for c in top_chunks) / len(top_chunks) if top_chunks else 0.0
    )

    # 9. Simpan ke DB
    question_obj = Question(text=question_text, embedding=q_vector)
    db.add(question_obj)
    db.flush()

    answer_obj = Answer(question_id=question_obj.id, text=answer_text, confidence_score=confidence)
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
        'sql_query': sql_result['sql'],
        'query_result_count': sql_result['row_count'],
        'data_error': sql_result['error'],
    }
