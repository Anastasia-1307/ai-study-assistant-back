from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import User, Note, Course, Assignment, Schedule, Material, Log
from models.schemas import (
    NoteCreate,
    NoteUpdate,
    NoteResponse,
    CourseCreate,
    CourseUpdate,
    CourseResponse,
    AssignmentCreate,
    AssignmentUpdate,
    AssignmentResponse,
    ScheduleCreate,
    ScheduleUpdate,
    ScheduleResponse,
    MaterialResponse
)
from auth.auth import get_current_user
from typing import List
import os
import uuid
from datetime import datetime

router = APIRouter(prefix="/materials", tags=["materials"])

# Allowed file types
ALLOWED_EXTENSIONS = {
    'doc', 'docx', 'xlsx', 'ppt', 'pptx', 'pdf', 'png', 'jpg', 'jpeg', 'txt', 'zip'
}

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# Notes
@router.post("/notes", response_model=NoteResponse)
async def create_note(
    note: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new note"""
    new_note = Note(
        user_id=current_user.id,
        title=note.title,
        content=note.content
    )
    db.add(new_note)
    db.commit()
    db.refresh(new_note)

    # Log action
    log = Log(
        user_id=current_user.id,
        action="NOTE_CREATED",
        details=f"Note '{note.title}' created"
    )
    db.add(log)
    db.commit()

    return new_note


@router.get("/notes", response_model=List[NoteResponse])
async def get_notes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all notes for current user"""
    notes = db.query(Note).filter(Note.user_id == current_user.id).all()
    return notes


@router.get("/notes/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific note"""
    note = db.query(Note).filter(
        Note.id == note_id,
        Note.user_id == current_user.id
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Notă negăsită")
    return note


@router.put("/notes/{note_id}", response_model=NoteResponse)
@router.patch("/notes/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: int,
    note_update: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a note"""
    note = db.query(Note).filter(
        Note.id == note_id,
        Note.user_id == current_user.id
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Notă negăsită")

    if note_update.title is not None:
        note.title = note_update.title
    if note_update.content is not None:
        note.content = note_update.content
    note.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(note)

    # Log action
    log = Log(
        user_id=current_user.id,
        action="NOTE_UPDATED",
        details=f"Note '{note.title}' updated"
    )
    db.add(log)
    db.commit()

    return note


@router.delete("/notes/{note_id}")
async def delete_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a note"""
    note = db.query(Note).filter(
        Note.id == note_id,
        Note.user_id == current_user.id
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Notă negăsită")

    db.delete(note)
    db.commit()

    # Log action
    log = Log(
        user_id=current_user.id,
        action="NOTE_DELETED",
        details=f"Note '{note.title}' deleted"
    )
    db.add(log)
    db.commit()

    return {"message": "Notă ștearsă cu succes"}


# Courses
@router.post("/courses", response_model=CourseResponse)
async def create_course(
    course: CourseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new course"""
    new_course = Course(
        user_id=current_user.id,
        name=course.name,
        description=course.description
    )
    db.add(new_course)
    db.commit()
    db.refresh(new_course)

    # Log action
    log = Log(
        user_id=current_user.id,
        action="COURSE_CREATED",
        details=f"Course '{course.name}' created"
    )
    db.add(log)
    db.commit()

    return new_course


@router.get("/courses", response_model=List[CourseResponse])
async def get_courses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all courses for current user"""
    courses = db.query(Course).filter(Course.user_id == current_user.id).all()
    return courses


@router.get("/courses/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific course"""
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.user_id == current_user.id
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Curs negăsit")
    return course


@router.put("/courses/{course_id}", response_model=CourseResponse)
@router.patch("/courses/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: int,
    course_update: CourseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a course"""
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.user_id == current_user.id
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Curs negăsit")

    if course_update.name is not None:
        course.name = course_update.name
    if course_update.description is not None:
        course.description = course_update.description

    db.commit()
    db.refresh(course)

    # Log action
    log = Log(
        user_id=current_user.id,
        action="COURSE_UPDATED",
        details=f"Course '{course.name}' updated"
    )
    db.add(log)
    db.commit()

    return course


@router.delete("/courses/{course_id}")
async def delete_course(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a course"""
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.user_id == current_user.id
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Curs negăsit")

    db.delete(course)
    db.commit()

    # Log action
    log = Log(
        user_id=current_user.id,
        action="COURSE_DELETED",
        details=f"Course '{course.name}' deleted"
    )
    db.add(log)
    db.commit()

    return {"message": "Curs șters cu succes"}


# Assignments
@router.post("/assignments", response_model=AssignmentResponse)
async def create_assignment(
    assignment: AssignmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new assignment"""
    # Verify course belongs to user if course_id is provided
    if assignment.course_id:
        course = db.query(Course).filter(
            Course.id == assignment.course_id,
            Course.user_id == current_user.id
        ).first()
        if not course:
            raise HTTPException(status_code=404, detail="Curs negăsit")

    new_assignment = Assignment(
        user_id=current_user.id,
        course_id=assignment.course_id,
        title=assignment.title,
        description=assignment.description,
        due_date=assignment.due_date,
        status="pending"
    )
    db.add(new_assignment)
    db.commit()
    db.refresh(new_assignment)

    # Log action
    log = Log(
        user_id=current_user.id,
        action="ASSIGNMENT_CREATED",
        details=f"Assignment '{assignment.title}' created"
    )
    db.add(log)
    db.commit()

    return new_assignment


@router.get("/assignments", response_model=List[AssignmentResponse])
async def get_assignments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all assignments for current user"""
    assignments = db.query(Assignment).filter(Assignment.user_id == current_user.id).all()
    return assignments


@router.put("/assignments/{assignment_id}", response_model=AssignmentResponse)
async def update_assignment(
    assignment_id: int,
    assignment_update: AssignmentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an assignment"""
    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id,
        Assignment.user_id == current_user.id
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Tema negăsită")

    if assignment_update.title is not None:
        assignment.title = assignment_update.title
    if assignment_update.description is not None:
        assignment.description = assignment_update.description
    if assignment_update.due_date is not None:
        assignment.due_date = assignment_update.due_date
    if assignment_update.status is not None:
        assignment.status = assignment_update.status

    db.commit()
    db.refresh(assignment)

    # Log action
    log = Log(
        user_id=current_user.id,
        action="ASSIGNMENT_UPDATED",
        details=f"Assignment '{assignment.title}' updated"
    )
    db.add(log)
    db.commit()

    return assignment


@router.delete("/assignments/{assignment_id}")
async def delete_assignment(
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an assignment"""
    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id,
        Assignment.user_id == current_user.id
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Tema negăsită")

    db.delete(assignment)
    db.commit()

    # Log action
    log = Log(
        user_id=current_user.id,
        action="ASSIGNMENT_DELETED",
        details=f"Assignment '{assignment.title}' deleted"
    )
    db.add(log)
    db.commit()

    return {"message": "Tema ștearsă cu succes"}


# Schedule
@router.post("/schedule", response_model=ScheduleResponse)
async def create_schedule_item(
    schedule: ScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new schedule item"""
    new_schedule = Schedule(
        user_id=current_user.id,
        day_of_week=schedule.day_of_week,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        subject=schedule.subject,
        location=schedule.location
    )
    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)

    # Log action
    log = Log(
        user_id=current_user.id,
        action="SCHEDULE_CREATED",
        details=f"Schedule item for {schedule.day_of_week} created"
    )
    db.add(log)
    db.commit()

    return new_schedule


@router.get("/schedule", response_model=List[ScheduleResponse])
async def get_schedule(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all schedule items for current user"""
    schedule = db.query(Schedule).filter(Schedule.user_id == current_user.id).all()
    return schedule


@router.get("/schedule/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule_item(
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific schedule item"""
    schedule = db.query(Schedule).filter(
        Schedule.id == schedule_id,
        Schedule.user_id == current_user.id
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Programare negăsită")
    return schedule


@router.put("/schedule/{schedule_id}", response_model=ScheduleResponse)
@router.patch("/schedule/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule_item(
    schedule_id: int,
    schedule_update: ScheduleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update one schedule item."""
    schedule = db.query(Schedule).filter(
        Schedule.id == schedule_id,
        Schedule.user_id == current_user.id
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Programare negăsită")

    for field, value in schedule_update.model_dump(exclude_unset=True).items():
        setattr(schedule, field, value)

    db.commit()
    db.refresh(schedule)
    db.add(Log(
        user_id=current_user.id,
        action="SCHEDULE_UPDATED",
        details=f"Schedule item for {schedule.day_of_week} updated"
    ))
    db.commit()
    return schedule


@router.delete("/schedule/{schedule_id}")
async def delete_schedule_item(
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a schedule item"""
    schedule = db.query(Schedule).filter(
        Schedule.id == schedule_id,
        Schedule.user_id == current_user.id
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Programare negăsită")

    db.delete(schedule)
    db.commit()

    # Log action
    log = Log(
        user_id=current_user.id,
        action="SCHEDULE_DELETED",
        details=f"Schedule item for {schedule.day_of_week} deleted"
    )
    db.add(log)
    db.commit()

    return {"message": "Programare ștearsă cu succes"}


# File Upload
@router.post("/upload", response_model=MaterialResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a file"""
    # Check file extension
    file_ext = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Tip de fișier nepermis. Formate permise: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Check file size (max 10MB)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Fișierul nu poate depăși 10 MB")

    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # Save file
    with open(file_path, "wb") as f:
        f.write(content)

    # Save to database
    new_material = Material(
        user_id=current_user.id,
        filename=file.filename,
        file_type=file_ext,
        file_path=file_path,
        file_size=len(content)
    )
    db.add(new_material)
    db.commit()
    db.refresh(new_material)

    # Log action
    log = Log(
        user_id=current_user.id,
        action="FILE_UPLOADED",
        details=f"File '{file.filename}' uploaded"
    )
    db.add(log)
    db.commit()

    return new_material


@router.get("/files", response_model=List[MaterialResponse])
async def get_files(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all uploaded files for current user"""
    files = db.query(Material).filter(Material.user_id == current_user.id).all()
    return files


@router.get("/files/{file_id}", response_model=MaterialResponse)
async def get_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    material = db.query(Material).filter(
        Material.id == file_id,
        Material.user_id == current_user.id
    ).first()
    if not material:
        raise HTTPException(status_code=404, detail="Fișier negăsit")
    return material


@router.put("/files/{file_id}", response_model=MaterialResponse)
@router.patch("/files/{file_id}", response_model=MaterialResponse)
async def update_file(
    file_id: int,
    filename: str | None = Form(None),
    file: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rename a file and/or replace its contents using multipart/form-data."""
    material = db.query(Material).filter(
        Material.id == file_id,
        Material.user_id == current_user.id
    ).first()
    if not material:
        raise HTTPException(status_code=404, detail="Fișier negăsit")

    old_path = material.file_path
    if file is not None:
        file_ext = file.filename.rsplit('.', 1)[-1].lower() if file.filename and '.' in file.filename else ''
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Tip de fișier nepermis")
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Fișierul nu poate depăși 10 MB")
        stored_name = f"{uuid.uuid4()}_{file.filename}"
        new_path = os.path.join(UPLOAD_DIR, stored_name)
        with open(new_path, "wb") as output_file:
            output_file.write(content)
        material.file_path = new_path
        material.file_type = file_ext
        material.file_size = len(content)
        material.filename = file.filename

    if filename is not None:
        if not filename.strip():
            raise HTTPException(status_code=422, detail="Numele fișierului nu poate fi gol")
        material.filename = filename.strip()

    db.commit()
    db.refresh(material)
    if file is not None and os.path.exists(old_path):
        os.remove(old_path)
    db.add(Log(
        user_id=current_user.id,
        action="FILE_UPDATED",
        details=f"File '{material.filename}' updated"
    ))
    db.commit()
    return material


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a file"""
    file = db.query(Material).filter(
        Material.id == file_id,
        Material.user_id == current_user.id
    ).first()
    if not file:
        raise HTTPException(status_code=404, detail="Fișier negăsit")

    # Delete from filesystem
    if os.path.exists(file.file_path):
        os.remove(file.file_path)

    # Delete from database
    db.delete(file)
    db.commit()

    # Log action
    log = Log(
        user_id=current_user.id,
        action="FILE_DELETED",
        details=f"File '{file.filename}' deleted"
    )
    db.add(log)
    db.commit()

    return {"message": "Fișier șters cu succes"}
