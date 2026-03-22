from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import engine, Base
import app.models  # noqa: F401 — pastikan semua model ter-register sebelum create_all
from app.routers import documents, qa


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Buat semua tabel di MySQL saat server start (jika belum ada)
    Base.metadata.create_all(bind=engine)
    print("[DB] Tabel siap.")
    yield
    # Cleanup saat server stop (opsional)


app = FastAPI(
    title='RAG Chatbot API',
    description='Chatbot yang menjawab berdasarkan dokumen menggunakan Gemini Flash + Sentence Transformers',
    version='1.0.0',
    lifespan=lifespan,
)

app.include_router(documents.router)
app.include_router(qa.router)


@app.get('/')
def root():
    return {
        'message': 'RAG Chatbot API aktif',
        'docs': '/docs',
        'endpoints': {
            'upload_dokumen': 'POST /api/documents/upload',
            'list_dokumen': 'GET /api/documents',
            'tanya': 'POST /api/qa/ask',
            'riwayat': 'GET /api/qa/history',
        }
    }
