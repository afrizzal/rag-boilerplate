from datetime import datetime
from pydantic import BaseModel, field_validator


class AskRequest(BaseModel):
    question: str

    @field_validator('question')
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError('Pertanyaan minimal 3 karakter.')
        return v


class SourceChunk(BaseModel):
    document: str
    similarity_score: float
    excerpt: str


class AskResponse(BaseModel):
    question_id: str
    answer_id: str
    question: str
    answer: str
    confidence_score: float
    sources: list[SourceChunk]


class AnswerHistory(BaseModel):
    id: str
    text: str
    confidence_score: float
    created_at: datetime

    model_config = {'from_attributes': True}


class QuestionHistory(BaseModel):
    id: str
    text: str
    created_at: datetime
    answers: list[AnswerHistory]

    model_config = {'from_attributes': True}
