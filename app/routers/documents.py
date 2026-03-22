from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.document import Document
from app.schemas.document import DocumentResponse, UploadResponse
from app.services.document_processor import process_document

router = APIRouter(prefix='/api/documents', tags=['Documents'])

ALLOWED_TYPES = {'pdf', 'txt', 'docx', 'doc'}


def _to_response(doc: Document) -> DocumentResponse:
    return DocumentResponse(
        id=doc.id,
        title=doc.title,
        file_type=doc.file_type,
        file_size=doc.file_size,
        is_processed=doc.is_processed,
        uploaded_at=doc.uploaded_at,
        processed_at=doc.processed_at,
        chunk_count=len(doc.chunks),
    )


@router.get('/', response_model=list[DocumentResponse])
def list_documents(db: Session = Depends(get_db)):
    """Daftar semua dokumen."""
    docs = db.query(Document).order_by(Document.uploaded_at.desc()).all()
    return [_to_response(d) for d in docs]


@router.post('/upload', response_model=UploadResponse, status_code=201)
def upload_document(
    file: UploadFile = File(...),
    title: str = Form(default=''),
    db: Session = Depends(get_db),
):
    """Upload dan proses dokumen baru (PDF / DOCX / TXT)."""
    ext = file.filename.split('.')[-1].lower() if file.filename else ''
    if ext not in ALLOWED_TYPES:
        raise HTTPException(400, f"Format tidak didukung. Gunakan: {', '.join(ALLOWED_TYPES)}")

    file_bytes = file.file.read()
    doc_title = title.strip() or file.filename

    document = Document(
        title=doc_title,
        file_type=ext,
        file_size=len(file_bytes),
    )
    db.add(document)
    db.flush()  # dapatkan id sebelum process

    try:
        process_document(document, file_bytes, db)
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Gagal memproses dokumen: {e}")

    return UploadResponse(
        message=f"Dokumen '{doc_title}' berhasil diupload dan diproses.",
        document=_to_response(document),
    )


@router.get('/{doc_id}', response_model=DocumentResponse)
def get_document(doc_id: str, db: Session = Depends(get_db)):
    """Detail satu dokumen."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Dokumen tidak ditemukan.")
    return _to_response(doc)


@router.delete('/{doc_id}')
def delete_document(doc_id: str, db: Session = Depends(get_db)):
    """Hapus dokumen beserta semua chunk-nya."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Dokumen tidak ditemukan.")
    db.delete(doc)
    db.commit()
    return {'message': f"Dokumen '{doc.title}' berhasil dihapus."}
