"""
Pipeline pemrosesan dokumen:
1. Ekstrak teks dari file (PDF / DOCX / TXT)
2. Potong teks menjadi chunk-chunk kecil
3. Generate embedding untuk setiap chunk
4. Simpan ke MySQL
"""
import io
from datetime import datetime
from sqlalchemy.orm import Session
from app.config import settings
from app.models.document import Document, DocumentChunk
from .embedding import embed


# ── Ekstraksi Teks ─────────────────────────────────────────────────────────────

def extract_text(file_bytes: bytes, file_type: str) -> str:
    file_type = file_type.lower()

    if file_type == 'txt':
        return file_bytes.decode('utf-8', errors='replace')

    elif file_type == 'pdf':
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        return '\n'.join(page.extract_text() or '' for page in reader.pages)

    elif file_type in ('docx', 'doc'):
        from docx import Document as DocxDoc
        doc = DocxDoc(io.BytesIO(file_bytes))
        return '\n'.join(para.text for para in doc.paragraphs)

    raise ValueError(f"Format '{file_type}' tidak didukung. Gunakan: pdf, docx, txt")


# ── Chunking ───────────────────────────────────────────────────────────────────

def chunk_text(text: str) -> list[str]:
    size = settings.chunk_size
    overlap = settings.chunk_overlap
    words = text.split()
    chunks, start = [], 0

    while start < len(words):
        chunk = ' '.join(words[start: start + size])
        if chunk.strip():
            chunks.append(chunk)
        start += size - overlap

    return chunks


# ── Pipeline Utama ─────────────────────────────────────────────────────────────

def process_document(document: Document, file_bytes: bytes, db: Session) -> Document:
    """Extract → chunk → embed → save chunks → update document status."""

    # 1. Ekstrak teks
    text = extract_text(file_bytes, document.file_type)
    if not text.strip():
        raise ValueError("Dokumen kosong atau tidak bisa dibaca.")
    document.content = text

    # 2. Chunk
    chunks_text = chunk_text(text)
    if not chunks_text:
        raise ValueError("Tidak ada konten yang bisa di-chunk.")

    # 3. Embed semua chunk sekaligus (batch — lebih efisien)
    vectors = embed(chunks_text)

    # 4. Hapus chunk lama jika ada, lalu simpan yang baru
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()

    db.bulk_save_objects([
        DocumentChunk(
            document_id=document.id,
            content=chunks_text[i],
            chunk_index=i,
            embedding=vectors[i],
        )
        for i in range(len(chunks_text))
    ])

    # 5. Update status
    document.is_processed = True
    document.processed_at = datetime.utcnow()
    db.commit()
    db.refresh(document)

    return document
