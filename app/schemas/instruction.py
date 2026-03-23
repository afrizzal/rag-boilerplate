from datetime import datetime
from pydantic import BaseModel
from typing import Literal


Category = Literal['schema', 'rule', 'formula', 'context', 'general']


class InstructionCreate(BaseModel):
    name: str
    category: Category = 'general'
    content: str
    order: int = 0
    is_active: bool = True


class InstructionUpdate(BaseModel):
    name: str | None = None
    category: Category | None = None
    content: str | None = None
    order: int | None = None
    is_active: bool | None = None


class InstructionResponse(BaseModel):
    id: str
    name: str
    category: str
    content: str
    is_active: bool
    order: int
    created_at: datetime
    updated_at: datetime

    model_config = {'from_attributes': True}
