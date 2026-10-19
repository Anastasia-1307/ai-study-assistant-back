from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import User, Achievement, StudySession, ImprovementArea, Log
from models.schemas import (
    AchievementCreate,
    AchievementResponse,
    StudySessionCreate,
    StudySessionResponse,
    ImprovementAreaCreate,
    ImprovementAreaUpdate,
    ImprovementAreaResponse
)
from auth.auth import get_current_user
from typing import List
from datetime import datetime, timedelta

router = APIRouter(prefix="/progress", tags=["progress"])


# Achievements (Grades)
@router.post("/achievements", response_model=AchievementResponse)
async def create_achievement(
    achievement: AchievementCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new achievement (grade)"""
    new_achievement = Achievement(
        user_id=current_user.id,
        subject=achievement.subject,
        grade=achievement.grade,
        date=achievement.date or datetime.utcnow(),
        notes=achievement.notes
    )
    db.add(new_achievement)
    db.commit()
    db.refresh(new_achievement)

    # Log action
    log = Log(
        user_id=current_user.id,
        action="ACHIEVEMENT_CREATED",
        details=f"Achievement for {achievement.subject} with grade {achievement.grade} created"
    )
    db.add(log)
    db.commit()

    return new_achievement


@router.get("/achievements", response_model=List[AchievementResponse])
async def get_achievements(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all achievements for current user"""
    achievements = db.query(Achievement).filter(
        Achievement.user_id == current_user.id
    ).order_by(Achievement.date.desc()).all()
    return achievements


@router.get("/achievements/stats")
async def get_achievement_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get statistics about achievements"""
    achievements = db.query(Achievement).filter(
        Achievement.user_id == current_user.id
    ).all()

    if not achievements:
        return {
            "total": 0,
            "average": 0,
            "by_subject": {},
            "recent": []
        }

    # Calculate average
    total = len(achievements)
    average = sum(a.grade for a in achievements) / total

    # Group by subject
    by_subject = {}
    for a in achievements:
        if a.subject not in by_subject:
            by_subject[a.subject] = []
        by_subject[a.subject].append(a.grade)

    by_subject_avg = {
        subject: sum(grades) / len(grades)
        for subject, grades in by_subject.items()
    }

    # Get recent achievements (last 5)
    recent = achievements[:5]

    return {
        "total": total,
        "average": round(average, 2),
        "by_subject": by_subject_avg,
        "recent": [
            {
                "subject": a.subject,
                "grade": a.grade,
                "date": a.date
            }
            for a in recent
        ]
    }


@router.delete("/achievements/{achievement_id}")
async def delete_achievement(
    achievement_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an achievement"""
    achievement = db.query(Achievement).filter(
        Achievement.id == achievement_id,
        Achievement.user_id == current_user.id
    ).first()
    if not achievement:
        raise HTTPException(status_code=404, detail="Reușită negăsită")

    db.delete(achievement)
    db.commit()

    # Log action
    log = Log(
        user_id=current_user.id,
        action="ACHIEVEMENT_DELETED",
        details=f"Achievement for {achievement.subject} deleted"
    )
    db.add(log)
    db.commit()

    return {"message": "Reușită ștearsă cu succes"}


# Study Sessions
@router.post("/study-sessions", response_model=StudySessionResponse)
async def create_study_session(
    session: StudySessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new study session"""
    new_session = StudySession(
        user_id=current_user.id,
        date=session.date or datetime.utcnow(),
        duration_minutes=session.duration_minutes,
        subject=session.subject,
        notes=session.notes
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    # Log action
    log = Log(
        user_id=current_user.id,
        action="STUDY_SESSION_CREATED",
        details=f"Study session of {session.duration_minutes} minutes created"
    )
    db.add(log)
    db.commit()

    return new_session


@router.get("/study-sessions", response_model=List[StudySessionResponse])
async def get_study_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all study sessions for current user"""
    sessions = db.query(StudySession).filter(
        StudySession.user_id == current_user.id
    ).order_by(StudySession.date.desc()).all()
    return sessions


@router.get("/study-sessions/stats")
async def get_study_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get statistics about study sessions"""
    sessions = db.query(StudySession).filter(
        StudySession.user_id == current_user.id
    ).all()

    if not sessions:
        return {
            "total_sessions": 0,
            "total_minutes": 0,
            "total_hours": 0,
            "average_session_minutes": 0,
            "by_subject": {},
            "last_7_days_minutes": 0,
            "last_7_days_hours": 0,
            "last_30_days_minutes": 0,
            "last_30_days_hours": 0
        }

    # Calculate totals
    total_sessions = len(sessions)
    total_minutes = sum(s.duration_minutes for s in sessions)
    total_hours = total_minutes / 60
    average_session = total_minutes / total_sessions

    # Group by subject
    by_subject = {}
    for s in sessions:
        if s.subject:
            if s.subject not in by_subject:
                by_subject[s.subject] = 0
            by_subject[s.subject] += s.duration_minutes

    # Calculate last 7 and 30 days
    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    last_7_days = sum(
        s.duration_minutes for s in sessions
        if s.date >= seven_days_ago
    )
    last_30_days = sum(
        s.duration_minutes for s in sessions
        if s.date >= thirty_days_ago
    )

    return {
        "total_sessions": total_sessions,
        "total_minutes": total_minutes,
        "total_hours": round(total_hours, 2),
        "average_session_minutes": round(average_session, 2),
        "by_subject": by_subject,
        "last_7_days_minutes": last_7_days,
        "last_7_days_hours": round(last_7_days / 60, 2),
        "last_30_days_minutes": last_30_days,
        "last_30_days_hours": round(last_30_days / 60, 2)
    }


@router.delete("/study-sessions/{session_id}")
async def delete_study_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a study session"""
    session = db.query(StudySession).filter(
        StudySession.id == session_id,
        StudySession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesiune de studiu negăsită")

    db.delete(session)
    db.commit()

    # Log action
    log = Log(
        user_id=current_user.id,
        action="STUDY_SESSION_DELETED",
        details=f"Study session deleted"
    )
    db.add(log)
    db.commit()

    return {"message": "Sesiune de studiu ștearsă cu succes"}


# Improvement Areas
@router.post("/improvement-areas", response_model=ImprovementAreaResponse)
async def create_improvement_area(
    area: ImprovementAreaCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new improvement area"""
    new_area = ImprovementArea(
        user_id=current_user.id,
        area=area.area,
        description=area.description,
        status="active"
    )
    db.add(new_area)
    db.commit()
    db.refresh(new_area)

    # Log action
    log = Log(
        user_id=current_user.id,
        action="IMPROVEMENT_AREA_CREATED",
        details=f"Improvement area '{area.area}' created"
    )
    db.add(log)
    db.commit()

    return new_area


@router.get("/improvement-areas", response_model=List[ImprovementAreaResponse])
async def get_improvement_areas(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all improvement areas for current user"""
    areas = db.query(ImprovementArea).filter(
        ImprovementArea.user_id == current_user.id
    ).order_by(ImprovementArea.created_at.desc()).all()
    return areas


@router.put("/improvement-areas/{area_id}", response_model=ImprovementAreaResponse)
async def update_improvement_area(
    area_id: int,
    area_update: ImprovementAreaUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an improvement area"""
    area = db.query(ImprovementArea).filter(
        ImprovementArea.id == area_id,
        ImprovementArea.user_id == current_user.id
    ).first()
    if not area:
        raise HTTPException(status_code=404, detail="Aspect de îmbunătățit negăsit")

    if area_update.area is not None:
        area.area = area_update.area
    if area_update.description is not None:
        area.description = area_update.description
    if area_update.status is not None:
        area.status = area_update.status

    db.commit()
    db.refresh(area)

    # Log action
    log = Log(
        user_id=current_user.id,
        action="IMPROVEMENT_AREA_UPDATED",
        details=f"Improvement area '{area.area}' updated"
    )
    db.add(log)
    db.commit()

    return area


@router.delete("/improvement-areas/{area_id}")
async def delete_improvement_area(
    area_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an improvement area"""
    area = db.query(ImprovementArea).filter(
        ImprovementArea.id == area_id,
        ImprovementArea.user_id == current_user.id
    ).first()
    if not area:
        raise HTTPException(status_code=404, detail="Aspect de îmbunătățit negăsit")

    db.delete(area)
    db.commit()

    # Log action
    log = Log(
        user_id=current_user.id,
        action="IMPROVEMENT_AREA_DELETED",
        details=f"Improvement area '{area.area}' deleted"
    )
    db.add(log)
    db.commit()

    return {"message": "Aspect de îmbunătățit șters cu succes"}
