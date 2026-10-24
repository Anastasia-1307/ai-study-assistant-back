from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from database.database import get_db
from database.models import User, Conversation, Message, Log
from models.schemas import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationWithMessagesResponse,
    MessageCreate,
    MessageResponse
)
from auth.auth import get_current_user
from typing import List
from datetime import datetime
import ollama

router = APIRouter(prefix="/conversations", tags=["conversations"])


def generate_conversation_title(user_message: str) -> str:
    """Generează un titlu scurt pe baza primei cereri."""

    fallback_title = user_message.strip()[:50].strip()

    try:
        response = ollama.chat(
            model="gemma3:4b",
            messages=[
                {
                    "role": "system",
                    "content": """
Generezi titluri pentru conversații cu un asistent educațional.

Reguli:
1. Identifică subiectul principal al cererii.
2. Formulează un titlu scurt, de maximum 8 cuvinte.
3. Scrie în limba română.
4. Nu răspunde la întrebare și nu explica subiectul.
5. Nu folosi ghilimele și nu adăuga etichete precum
   „Titlu:” sau introduceri.
6. Păstrează termenii tehnici și sensul cererii.
7. Returnează doar titlul.
"""
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            stream=False,
            options={
                "temperature": 0.1,
                "num_predict": 40
            }
        )

        title = response.message.content.strip()
        title = title.strip('"\'“”‘’').strip()
        title = " ".join(title.split())

        if not title:
            return fallback_title

        # Evită titlurile exagerat de lungi.
        words = title.split()
        if len(words) > 8:
            title = " ".join(words[:8])

        return title

    except Exception as e:
        print("EROARE GENERARE TITLU:", repr(e))
        return fallback_title


# Conversations
@router.post("", response_model=ConversationResponse)
async def create_conversation(
    conversation: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new conversation"""
    new_conversation = Conversation(
        user_id=current_user.id,
        title=conversation.title if conversation.title else "Conversație nouă"
    )
    db.add(new_conversation)
    db.commit()
    db.refresh(new_conversation)

    # Log action
    log = Log(
        user_id=current_user.id,
        action="CONVERSATION_CREATED",
        details=f"Conversation '{new_conversation.title}' created"
    )
    db.add(log)
    db.commit()

    return new_conversation


@router.get("", response_model=List[ConversationResponse])
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all conversations for current user, sorted by pinned and updated_at"""
    conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id
    ).order_by(Conversation.is_pinned.desc(), Conversation.updated_at.desc()).all()
    return conversations


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific conversation with all its messages"""

    conversation = db.query(Conversation).options(
        joinedload(Conversation.messages)
    ).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversație negăsită"
        )

    messages_response = [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at
        }
        for msg in sorted(
            conversation.messages,
            key=lambda msg: (msg.created_at, msg.id)
        )
    ]

    return {
        "id": conversation.id,
        "title": conversation.title,
        "is_pinned": conversation.is_pinned,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
        "messages": messages_response
    }


@router.put("/{conversation_id}", response_model=ConversationResponse)
@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    conversation_update: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a conversation (title or pinned status)"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversație negăsită")

    if conversation_update.title is not None:
        conversation.title = conversation_update.title
    if conversation_update.is_pinned is not None:
        conversation.is_pinned = conversation_update.is_pinned
    conversation.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(conversation)

    # Log action
    log = Log(
        user_id=current_user.id,
        action="CONVERSATION_UPDATED",
        details=f"Conversation '{conversation.title}' updated"
    )
    db.add(log)
    db.commit()

    return conversation


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a conversation and all its messages"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversație negăsită")

    db.delete(conversation)
    db.commit()

    # Log action
    log = Log(
        user_id=current_user.id,
        action="CONVERSATION_DELETED",
        details=f"Conversation '{conversation.title}' deleted"
    )
    db.add(log)
    db.commit()

    return {"message": "Conversație ștearsă cu succes"}


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def create_message(
    conversation_id: int,
    message: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Verificăm dacă conversația există și aparține utilizatorului.
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversație negăsită"
        )

    # 2. Verificăm dacă există deja mesaje înainte de a adăuga unul nou.
    existing_messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).count()

    # 3. Generăm titlul doar pentru prima cerere a utilizatorului.
    if message.role == "user" and existing_messages == 0:
        conversation.title = generate_conversation_title(
            message.content
        )

    # 4. Salvăm mesajul.
    new_message = Message(
        conversation_id=conversation_id,
        role=message.role,
        content=message.content
    )

    db.add(new_message)

    # 5. Actualizăm data ultimei modificări a conversației.
    conversation.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(new_message)

    return new_message



@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all messages for a conversation"""
    # Verify conversation belongs to user
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversație negăsită")

    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at.asc()).all()
    return messages
