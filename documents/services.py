"""
Services untuk pemrosesan dokumen:
1. Ekstraksi teks dari PDF/DOCX/TXT
2. Chunking teks
3. Pembuatan embedding dengan Sentence Transformers
"""
import io
import numpy as np
from django.conf import settings
from django.utils import timezone
from sentence_transformers import SentenceTransformer

from .models import Document, DocumentChunk

_embedding_model = None


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _embedding_model


def extract_text(file, file_type: str) -> str:
    """Ekstrak teks dari file berdasarkan tipenya."""
    file_type = file_type.lower()

    if file_type == 'txt':
        content = file.read()
        return content.decode('utf-8', errors='replace')

    elif file_type == 'pdf':
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(io.BytesIO(file.read()))
            return '\n'.join(
                page.extract_text() or '' for page in reader.pages
            )
        except ImportError:
            raise ValueError("PyPDF2 tidak terinstall. Jalankan: pip install PyPDF2")

    elif file_type in ('docx', 'doc'):
        try:
            from docx import Document as DocxDocument
            doc = DocxDocument(io.BytesIO(file.read()))
            return '\n'.join(para.text for para in doc.paragraphs)
        except ImportError:
            raise ValueError("python-docx tidak terinstall. Jalankan: pip install python-docx")

    else:
        raise ValueError(f"Tipe file '{file_type}' tidak didukung. Gunakan: txt, pdf, docx")


def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> list[str]:
    """Bagi teks menjadi potongan-potongan dengan overlap."""
    chunk_size = chunk_size or settings.CHUNK_SIZE
    overlap = overlap or settings.CHUNK_OVERLAP

    if not text.strip():
        return []

    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = ' '.join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Buat embedding untuk list teks."""
    model = get_embedding_model()
    embeddings = model.encode(texts, convert_to_numpy=True)
    return embeddings.tolist()


def process_document(document: Document, file) -> Document:
    """
    Pipeline lengkap memproses dokumen:
    extract text → chunk → embed → simpan ke DB
    """
    # 1. Ekstrak teks
    text = extract_text(file, document.file_type)
    document.content = text
    document.save(update_fields=['content'])

    # 2. Buat chunks
    chunks_text = chunk_text(text)
    if not chunks_text:
        raise ValueError("Dokumen tidak memiliki konten yang bisa diproses.")

    # 3. Generate embeddings untuk semua chunk sekaligus (lebih efisien)
    embeddings = generate_embeddings(chunks_text)

    # 4. Simpan chunks ke database
    DocumentChunk.objects.filter(document=document).delete()  # hapus chunk lama jika ada

    chunk_objects = [
        DocumentChunk(
            document=document,
            content=chunks_text[i],
            chunk_index=i,
            embedding=embeddings[i],
        )
        for i in range(len(chunks_text))
    ]
    DocumentChunk.objects.bulk_create(chunk_objects)

    # 5. Update status dokumen
    document.is_processed = True
    document.processed_at = timezone.now()
    document.save(update_fields=['is_processed', 'processed_at'])

    return document
