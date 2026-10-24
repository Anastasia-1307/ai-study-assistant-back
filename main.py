
import os
import certifi

os.environ["SSL_CERT_FILE"] = certifi.where()

import ollama
from fastapi import FastAPI, Depends, Response, Request
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from dotenv import load_dotenv

from datetime import datetime
from uuid import uuid4
from io import BytesIO
from pypdf import PdfReader

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")


from fastapi import UploadFile, File, HTTPException
from models.schemas import (
    StudyRequest,
    UserRegister,
    UserLogin,
    UserResponse
)
from fastapi.middleware.cors import CORSMiddleware
from database.chroma import collection
from database.database import init_db, get_db
from database.models import User, Log
from services.ai_service import split_text, generate_material
from auth.auth import (
    validate_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    hash_token,
    verify_token_hash,
    authenticate_user,
    get_current_user,
    set_auth_cookies,
    clear_auth_cookies,
    get_client_ip,
    check_ip_blocked,
    record_failed_login,
    reset_login_attempts
)
from routes import materials, progress, conversations


app = FastAPI(title="AI Study Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(materials.router)
app.include_router(progress.router)
app.include_router(conversations.router)

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    init_db()



@app.get("/")
def home():
    return {"message": "AI Study Assistant functioneaza!"}



@app.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Încarcă un fișier PDF."
        )

    content = await file.read()

    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Fișierul nu poate depăși 10 MB."
        )

    try:
        reader = PdfReader(BytesIO(content))

        if reader.is_encrypted:
            raise HTTPException(
                status_code=400,
                detail="PDF-ul este protejat prin parolă."
            )

        # Extragem textul din fiecare pagină.
        pages_text = [
            page.extract_text() or ""
            for page in reader.pages
        ]

        text = "\n".join(pages_text).strip()

        if not text:
            raise HTTPException(
                status_code=400,
                detail="Nu am putut extrage textul din PDF."
            )

        # Generăm ID-ul înainte de a crea metadatele.
        document_id = str(uuid4())

        # Împărțim textul în fragmente și păstrăm metadatele.
        chunks = []
        metadatas = []

        for page_number, page_text in enumerate(
            pages_text, start=1
        ):
            for chunk in split_text(page_text):
                chunks.append(chunk)
                metadatas.append({
            "document_id": document_id,
            "filename": file.filename or "document.pdf",
            "page": page_number
        })

        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="PDF-ul nu conține fragmente de text valide."
            )


        ids = [
            f"{document_id}_{i}"
            for i in range(len(chunks))
        ]

        # ChromaDB generează embeddings și salvează datele.
        collection.add(
            ids=ids,
            documents=chunks,
            metadatas=metadatas
        )

        return {
            "message": "PDF-ul a fost procesat și salvat în ChromaDB.",
            "document_id": document_id,
            "filename": file.filename,
            "pages": len(reader.pages),
            "characters": len(text),
            "chunks_saved": len(chunks)
        }

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="PDF-ul nu a putut fi procesat sau salvat."
        )
    finally:
        await file.close()


@app.post("/search-document")
async def search_document(
    question: str,
    current_user: User = Depends(get_current_user)
):
    if not question.strip():
        raise HTTPException(
            status_code=400,
            detail="Introdu o întrebare."
        )

    results = collection.query(
        query_texts=[question],
        n_results=3,
        include=["documents", "metadatas", "distances"]
    )

    documents = results["documents"][0]

    if not documents:
        return {
            "question": question,
            "results": []
        }

    return {
        "question": question,
        "results": [
            {
                "text": document,
                "filename": metadata["filename"],
                "page": metadata["page"],
                "distance": distance
            }
            for document, metadata, distance in zip(
                documents,
                results["metadatas"][0],
                results["distances"][0]
            )
        ]
    }


@app.post("/generate-material")
async def generate_study_material(
    request: StudyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    result = generate_material(request)

    # If conversation_id is provided, save messages to the conversation
    if request.conversation_id:
        from database.models import Conversation, Message
        from models.schemas import MessageCreate

        # Verify conversation belongs to user
        conversation = db.query(Conversation).filter(
            Conversation.id == request.conversation_id,
            Conversation.user_id == current_user.id
        ).first()

        if conversation:
            # Save user message
            user_message = Message(
                conversation_id=request.conversation_id,
                role="user",
                content=request.text
            )
            db.add(user_message)

            # Save assistant response
            assistant_message = Message(
                conversation_id=request.conversation_id,
                role="assistant",
                content=result.get("result", "")
            )
            db.add(assistant_message)

            # Update conversation timestamp
            conversation.updated_at = datetime.utcnow()

            # Auto-generate title from first user message
            existing_messages = db.query(Message).filter(
                Message.conversation_id == request.conversation_id
            ).count()
            if existing_messages == 0:
                title = request.text[:50] + "..." if len(request.text) > 50 else request.text
                conversation.title = title

            db.commit()

    return result

@app.get("/documents")
async def get_documents(
    current_user: User = Depends(get_current_user)
):
    results = collection.get(
        include=["metadatas"]
    )

    metadatas = results.get("metadatas") or []
    ids = results.get("ids") or []

    documents = {}

    for metadata in metadatas:
        if not metadata:
            continue

        document_id = metadata.get("document_id")

        if document_id:
            documents[document_id] = {
                "document_id": document_id,
                "filename": metadata.get("filename"),
            }

    return {
        "total_chunks": len(ids),
        "total_documents": len(documents),
        "documents": list(documents.values()),
    }


# Auth Endpoints
@app.post("/auth/register", response_model=UserResponse)
async def register(user: UserRegister, db: Session = Depends(get_db)):
    """Register a new user"""
    # Validate password
    is_valid, error_msg = validate_password(user.password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email-ul este deja înregistrat")

    # Create new user
    hashed_password = get_password_hash(user.password)
    new_user = User(
        fname=user.fname,
        lname=user.lname,
        email=user.email,
        password=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Log registration
    log = Log(
        user_id=new_user.id,
        action="USER_REGISTERED",
        details=f"User {new_user.email} registered successfully"
    )
    db.add(log)
    db.commit()

    return new_user


@app.post("/auth/login")
async def login(
    user_credentials: UserLogin,
    response: Response,
    request: Request,
    db: Session = Depends(get_db)
):
    """Login user and set httpOnly cookies with access and refresh tokens"""
    # Get client IP address
    ip_address = get_client_ip(request)
    print(f"Login attempt from IP: {ip_address}")
    print(f"Current server time: {datetime.utcnow()}")

    # Check if IP is blocked
    is_blocked, blocked_until, remaining_seconds = check_ip_blocked(db, ip_address)
    print(f"IP blocked: {is_blocked}, blocked_until: {blocked_until}, remaining: {remaining_seconds}")

    if is_blocked:
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Prea multe încercări nereușite",
                "blocked_until": blocked_until.isoformat() + "Z",
                "remaining_seconds": remaining_seconds
            }
        )

    
    user = authenticate_user(
        db,
        user_credentials.email,
        user_credentials.password
    )

    if not user:
        # Înregistrăm încercarea nereușită.
        record_failed_login(db, ip_address)

        # Verificăm dacă această încercare a declanșat blocarea.
        is_blocked, blocked_until, remaining_seconds = check_ip_blocked(
            db, ip_address
        )

        if is_blocked:
            raise HTTPException(
                status_code=429,
                detail={
                    "message": "Prea multe încercări nereușite. "
                               "Autentificarea este blocată temporar.",
                    "blocked_until": blocked_until.isoformat() + "Z",
                    "remaining_seconds": remaining_seconds
                }
            )

        # Dacă pragul de blocare nu a fost atins.
        raise HTTPException(
            status_code=401,
            detail="Email sau parolă incorectă"
        )


    # Reset login attempts on successful login
    reset_login_attempts(db, ip_address)

    # Create access token and refresh token
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    # Hash and store refresh token in database
    refresh_token_hash = hash_token(refresh_token)
    user.refresh_token_hash = refresh_token_hash
    db.commit()

    # Log login
    log = Log(
        user_id=user.id,
        action="USER_LOGGED_IN",
        details=f"User {user.email} logged in from IP: {ip_address}"
    )
    db.add(log)
    db.commit()

    # Set httpOnly cookies with hashed tokens
    set_auth_cookies(response, access_token, refresh_token)

    return {"message": "Autentificare reușită"}


@app.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return current_user


@app.post("/auth/logout")
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logout user (invalidate refresh token and clear cookies)"""
    # Clear refresh token hash from database
    current_user.refresh_token_hash = None
    db.commit()

    # Log logout
    log = Log(
        user_id=current_user.id,
        action="USER_LOGGED_OUT",
        details=f"User {current_user.email} logged out"
    )
    db.add(log)
    db.commit()

    # Clear httpOnly cookies
    clear_auth_cookies(response)

    return {"message": "Deconectare reușită"}


@app.post("/auth/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token from cookie"""
    from auth.auth import get_refresh_token_from_cookie

    refresh_token = get_refresh_token_from_cookie(request)
    if not refresh_token:
        raise HTTPException(
            status_code=401,
            detail="Token de refresh lipsă"
        )

    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        token_type: str = payload.get("type")

        if user_id is None or token_type != "refresh":
            raise HTTPException(
                status_code=401,
                detail="Token de refresh invalid"
            )
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Token de refresh invalid"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Utilizator negăsit"
        )

    # Verify refresh token hash
    if not user.refresh_token_hash or not verify_token_hash(refresh_token, user.refresh_token_hash):
        raise HTTPException(
            status_code=401,
            detail="Token de refresh invalid sau expirat"
        )

    # Create new tokens
    new_access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

    # Update refresh token hash in database
    new_refresh_token_hash = hash_token(new_refresh_token)
    user.refresh_token_hash = new_refresh_token_hash
    db.commit()

    # Log token refresh
    log = Log(
        user_id=user.id,
        action="TOKEN_REFRESHED",
        details=f"Refresh token for user {user.email}"
    )
    db.add(log)
    db.commit()

    # Set new cookies
    set_auth_cookies(response, new_access_token, new_refresh_token)

    return {"message": "Token reîmprospătat cu succes"}