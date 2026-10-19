from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime


class StudyRequest(BaseModel):
    text: str = Field(min_length=20, max_length=15000)
    document_id: str | None = None


# Auth Schemas
class UserRegister(BaseModel):
    fname: str = Field(..., min_length=2, max_length=100)
    lname: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=64)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    fname: str
    lname: str
    email: str

    class Config:
        from_attributes = True


# Material Schemas
class MaterialCreate(BaseModel):
    filename: str
    file_type: str
    file_path: str
    file_size: int


class MaterialResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    file_size: int
    uploaded_at: datetime

    class Config:
        from_attributes = True


# Note Schemas
class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = Field(None, min_length=1)


class NoteResponse(BaseModel):
    id: int
    title: str
    content: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Course Schemas
class CourseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class CourseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class CourseResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Assignment Schemas
class AssignmentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    course_id: Optional[int] = None


class AssignmentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None


class AssignmentResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    due_date: Optional[datetime]
    status: str
    course_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# Schedule Schemas
class ScheduleCreate(BaseModel):
    day_of_week: str = Field(..., min_length=1, max_length=20)
    start_time: str = Field(..., pattern=r'^\d{2}:\d{2}$')
    end_time: str = Field(..., pattern=r'^\d{2}:\d{2}$')
    subject: str = Field(..., min_length=1, max_length=255)
    location: Optional[str] = None


class ScheduleUpdate(BaseModel):
    day_of_week: Optional[str] = Field(None, min_length=1, max_length=20)
    start_time: Optional[str] = Field(None, pattern=r'^\d{2}:\d{2}$')
    end_time: Optional[str] = Field(None, pattern=r'^\d{2}:\d{2}$')
    subject: Optional[str] = Field(None, min_length=1, max_length=255)
    location: Optional[str] = None


class ScheduleResponse(BaseModel):
    id: int
    day_of_week: str
    start_time: str
    end_time: str
    subject: str
    location: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Achievement Schemas
class AchievementCreate(BaseModel):
    subject: str = Field(..., min_length=1, max_length=255)
    grade: int = Field(..., ge=1, le=10)
    date: Optional[datetime] = None
    notes: Optional[str] = None


class AchievementResponse(BaseModel):
    id: int
    subject: str
    grade: float
    date: datetime
    notes: Optional[str]

    class Config:
        from_attributes = True


# Study Session Schemas
class StudySessionCreate(BaseModel):
    date: Optional[datetime] = None
    duration_minutes: int = Field(..., gt=0)
    subject: Optional[str] = None
    notes: Optional[str] = None


class StudySessionResponse(BaseModel):
    id: int
    date: datetime
    duration_minutes: int
    subject: Optional[str]
    notes: Optional[str]

    class Config:
        from_attributes = True


# Improvement Area Schemas
class ImprovementAreaCreate(BaseModel):
    area: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class ImprovementAreaUpdate(BaseModel):
    area: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None


class ImprovementAreaResponse(BaseModel):
    id: int
    area: str
    description: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
    
