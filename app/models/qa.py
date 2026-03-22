import uuid
from datetime import datetime
from sqlalchemy import String, Text, Float, Integer, DateTime, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Question(Base):
    __tablename__ = 'questions'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    answers: Mapped[list['Answer']] = relationship('Answer', back_populates='question', cascade='all, delete-orphan')
    relevant_chunks: Mapped[list['RelevantChunk']] = relationship('RelevantChunk', back_populates='question', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Question {self.text[:50]}>"


class Answer(Base):
    __tablename__ = 'answers'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id: Mapped[str] = mapped_column(String(36), ForeignKey('questions.id', ondelete='CASCADE'))
    text: Mapped[str] = mapped_column(Text)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    question: Mapped['Question'] = relationship('Question', back_populates='answers')

    def __repr__(self):
        return f"<Answer {self.text[:50]}>"


class RelevantChunk(Base):
    __tablename__ = 'relevant_chunks'
    __table_args__ = (UniqueConstraint('question_id', 'chunk_id'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id: Mapped[str] = mapped_column(String(36), ForeignKey('questions.id', ondelete='CASCADE'))
    chunk_id: Mapped[str] = mapped_column(String(36), ForeignKey('document_chunks.id', ondelete='CASCADE'))
    similarity_score: Mapped[float] = mapped_column(Float)
    rank: Mapped[int] = mapped_column(Integer)

    question: Mapped['Question'] = relationship('Question', back_populates='relevant_chunks')
    chunk: Mapped['DocumentChunk'] = relationship('DocumentChunk')

    def __repr__(self):
        return f"<RelevantChunk score={self.similarity_score:.2f}>"
