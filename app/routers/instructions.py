from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.instruction import SystemInstruction
from app.models.user import User
from app.schemas.instruction import InstructionCreate, InstructionUpdate, InstructionResponse

router = APIRouter(prefix='/api/instructions', tags=['System Instructions'])


@router.get('/', response_model=list[InstructionResponse])
def list_instructions(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Daftar semua instruksi sistem (aktif dan nonaktif)."""
    return db.query(SystemInstruction).order_by(SystemInstruction.order, SystemInstruction.category).all()


@router.post('/', response_model=InstructionResponse, status_code=201)
def create_instruction(
    body: InstructionCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Buat instruksi sistem baru."""
    if db.query(SystemInstruction).filter(SystemInstruction.name == body.name).first():
        raise HTTPException(400, f"Instruksi dengan nama '{body.name}' sudah ada.")

    instruction = SystemInstruction(**body.model_dump())
    db.add(instruction)
    db.commit()
    db.refresh(instruction)
    return instruction


@router.put('/{instruction_id}', response_model=InstructionResponse)
def update_instruction(
    instruction_id: str,
    body: InstructionUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Update isi atau status instruksi."""
    instruction = db.query(SystemInstruction).filter(SystemInstruction.id == instruction_id).first()
    if not instruction:
        raise HTTPException(404, "Instruksi tidak ditemukan.")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(instruction, field, value)

    db.commit()
    db.refresh(instruction)
    return instruction


@router.delete('/{instruction_id}')
def delete_instruction(
    instruction_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Hapus instruksi."""
    instruction = db.query(SystemInstruction).filter(SystemInstruction.id == instruction_id).first()
    if not instruction:
        raise HTTPException(404, "Instruksi tidak ditemukan.")
    db.delete(instruction)
    db.commit()
    return {'message': f"Instruksi '{instruction.name}' berhasil dihapus."}


@router.post('/{instruction_id}/toggle', response_model=InstructionResponse)
def toggle_instruction(
    instruction_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Aktifkan / nonaktifkan instruksi tanpa menghapusnya."""
    instruction = db.query(SystemInstruction).filter(SystemInstruction.id == instruction_id).first()
    if not instruction:
        raise HTTPException(404, "Instruksi tidak ditemukan.")
    instruction.is_active = not instruction.is_active
    db.commit()
    db.refresh(instruction)
    status = "diaktifkan" if instruction.is_active else "dinonaktifkan"
    return instruction
