from pydantic import BaseModel, Field

class StudyRequest(BaseModel):
    text: str = Field(min_length=20, max_length=15000)
    document_id: str | None = None
    