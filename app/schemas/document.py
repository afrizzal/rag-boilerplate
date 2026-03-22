from datetime import datetime
from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: str
    title: str
    file_type: str
    file_size: int
    is_processed: bool
    uploaded_at: datetime
    processed_at: datetime | None
    chunk_count: int

    model_config = {'from_attributes': True}


class UploadResponse(BaseModel):
    message: str
    document: DocumentResponse
