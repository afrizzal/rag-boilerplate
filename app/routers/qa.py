from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.database import get_db
from app.db_mis import test_mis_connection
from app.models.qa import Question
from app.models.user import User
from app.schemas.qa import AskRequest, AskResponse, QuestionHistory
from app.services.rag import ask

router = APIRouter(prefix='/api/qa', tags=['QA'])


@router.post('/ask', response_model=AskResponse)
def ask_question(
    body: AskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Hybrid RAG — Ajukan pertanyaan ke chatbot.

    Sistem secara otomatis:
    1. Mencari konteks dari dokumen yang sudah diupload
    2. Memuat instruksi sistem (schema, rules, formulas)
    3. Jika MIS_DB_ENABLED=True: generate SQL → query MIS DB → ambil data real
    4. Menggabungkan semua konteks dan menjawab via Gemini Flash
    """
    try:
        result = ask(body.question, db)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Gagal memproses pertanyaan: {e}")

    return result


@router.get('/history', response_model=list[QuestionHistory])
def get_history(
    limit: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Riwayat pertanyaan dan jawaban (default 20 terakhir)."""
    questions = (
        db.query(Question)
        .options(joinedload(Question.answers))
        .order_by(Question.created_at.desc())
        .limit(limit)
        .all()
    )
    return questions


@router.get('/mis-status')
def mis_connection_status(_: User = Depends(get_current_user)):
    """Cek status koneksi ke database MIS."""
    ok, message = test_mis_connection()
    return {'connected': ok, 'message': message}
