import uuid
from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class SystemInstruction(Base):
    __tablename__ = 'system_instructions'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), unique=True)  # contoh: "schema_customer"
    category: Mapped[str] = mapped_column(String(100), default='general')  # schema, rule, formula, context
    content: Mapped[str] = mapped_column(Text)  # isi instruksinya
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    order: Mapped[int] = mapped_column(Integer, default=0)  # urutan tampil di prompt
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<SystemInstruction {self.name}>"
