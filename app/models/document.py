import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, Boolean, DateTime, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Document(Base):
    __tablename__ = 'documents'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text, default='')
    file_type: Mapped[str] = mapped_column(String(50))
    file_size: Mapped[int] = mapped_column(Integer)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)

    chunks: Mapped[list['DocumentChunk']] = relationship(
        'DocumentChunk', back_populates='document', cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f"<Document {self.title}>"


class DocumentChunk(Base):
    __tablename__ = 'document_chunks'
    __table_args__ = (UniqueConstraint('document_id', 'chunk_index'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey('documents.id', ondelete='CASCADE'))
    content: Mapped[str] = mapped_column(Text)
    chunk_index: Mapped[int] = mapped_column(Integer)
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    document: Mapped['Document'] = relationship('Document', back_populates='chunks')

    def __repr__(self):
        return f"<DocumentChunk {self.document_id} #{self.chunk_index}>"
