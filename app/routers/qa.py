from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.qa import Question
from app.schemas.qa import AskRequest, AskResponse, QuestionHistory
from app.services.rag import ask

router = APIRouter(prefix='/api/qa', tags=['QA'])


@router.post('/ask', response_model=AskResponse)
def ask_question(body: AskRequest, db: Session = Depends(get_db)):
    """
    Ajukan pertanyaan ke chatbot RAG.
    Sistem akan mencari konteks dari dokumen yang sudah diupload,
    lalu menjawab menggunakan Gemini Flash.
    """
    try:
        result = ask(body.question, db)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Gagal memproses pertanyaan: {e}")

    return result


@router.get('/history', response_model=list[QuestionHistory])
def get_history(limit: int = 20, db: Session = Depends(get_db)):
    """Riwayat pertanyaan dan jawaban (default 20 terakhir)."""
    questions = (
        db.query(Question)
        .options(joinedload(Question.answers))
        .order_by(Question.created_at.desc())
        .limit(limit)
        .all()
    )
    return questions
