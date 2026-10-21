from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import User, LoginAttempt
import re
from uuid import uuid4

import os
from dotenv import load_dotenv

load_dotenv()  # înainte de os.getenv

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY nu este setat în .env")

ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Use argon2id for password hashing (more secure than bcrypt)
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__time_cost=3,
    argon2__memory_cost=65536,
    argon2__parallelism=4,
    argon2__hash_len=32,
    argon2__salt_len=16
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def get_token_from_cookie(request: Request) -> Optional[str]:
    """Get access token from httpOnly cookie"""
    return request.cookies.get("access_token")


def get_refresh_token_from_cookie(request: Request) -> Optional[str]:
    """Get refresh token from httpOnly cookie"""
    return request.cookies.get("refresh_token")


# Password validation regex
# 8-64 characters, at least one uppercase, one lowercase, one digit, one special character
# Allowed special characters: # @ & * - _ $ % ! ?
PASSWORD_REGEX = re.compile(
    r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[#@&*\-_$%!?])[A-Za-z\d#@&*\-_$%!?]{8,64}$'
)


def validate_password(password: str) -> tuple[bool, str]:
    """Validate password against requirements"""
    if not PASSWORD_REGEX.match(password):
        return False, (
            "Parola trebuie să aibă între 8 și 64 caractere, "
            "și să includă cel puțin o majusculă, o minusculă, o cifră "
            "și un simbol special (#, @, &, *, -, _, $, %, !, ?)"
        )
    return True, ""


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT refresh token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS) 
    # jti makes every issued refresh token unique, including tokens created
    # for the same user within the same second.
    to_encode.update({"exp": expire, "type": "refresh", "jti": uuid4().hex})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def hash_token(token: str) -> str:
    """Hash a token (refresh token) using argon2id for secure storage"""
    return pwd_context.hash(token)


def verify_token_hash(token: str, token_hash: str) -> bool:
    """Verify a token against its hash"""
    return pwd_context.verify(token, token_hash)


def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    """Set httpOnly, secure cookies for access and refresh tokens"""
    access_max_age = ACCESS_TOKEN_EXPIRE_MINUTES * 60
    refresh_max_age = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=access_max_age,
        expires=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        path="/",
        domain=None,
        secure=True,
        httponly=True,
        samesite="lax"
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=refresh_max_age,
        expires=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        path="/",
        domain=None,
        secure=True,
        httponly=True,
        samesite="lax"
    )


def clear_auth_cookies(response: Response):
    """Clear auth cookies"""
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")


def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """Get the current authenticated user from JWT token in cookie"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Nu s-a putut valida credențialele",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Try to get token from cookie first, then from Authorization header
    token = get_token_from_cookie(request)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user by email and password"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user


def get_client_ip(request: Request) -> str:
    """Get client IP address from request, handling proxies"""
    # Check for forwarded headers (reverse proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fallback to direct connection
    if request.client:
        return request.client.host

    return "unknown"


def get_block_duration(attempt_count: int) -> Optional[timedelta]:
    """Calculate block duration based on attempt count"""
    if attempt_count == 5:
        return timedelta(minutes=1)
    elif attempt_count == 6:
        return timedelta(minutes=2)
    elif attempt_count == 7:
        return timedelta(minutes=5)
    elif attempt_count == 8:
        return timedelta(minutes=15)
    elif attempt_count == 9:
        return timedelta(minutes=30)
    elif attempt_count >= 10:
        return timedelta(hours=1)
    return None


def check_ip_blocked(db: Session, ip_address: str):
    """Returnează (is_blocked, blocked_until, remaining_seconds)."""

    attempt = (
        db.query(LoginAttempt)
        .filter(LoginAttempt.ip_address == ip_address)
        .first()
    )

    if not attempt or not attempt.blocked_until:
        return False, None, None

    now = datetime.utcnow()
    blocked_until = attempt.blocked_until

    if blocked_until > now:
        remaining_seconds = max(
            1,
            int((blocked_until - now).total_seconds() + 0.999)
        )
        return True, blocked_until, remaining_seconds

    # Blocarea a expirat, dar păstrăm attempt_count
    # pentru a aplica o blocare progresivă la următorul eșec.
    attempt.blocked_until = None
    db.commit()

    return False, None, None


def record_failed_login(db: Session, ip_address: str):
    """Înregistrează eșecul și aplică blocarea dacă este necesar."""

    attempt = (
        db.query(LoginAttempt)
        .filter(LoginAttempt.ip_address == ip_address)
        .first()
    )

    now = datetime.utcnow()

    if not attempt:
        attempt = LoginAttempt(
            ip_address=ip_address,
            attempt_count=0,
            last_attempt_at=now,
        )
        db.add(attempt)
        db.flush()

    # Nu resetăm contorul doar pentru că blocarea a expirat.
    attempt.attempt_count += 1
    attempt.last_attempt_at = now

    block_duration = get_block_duration(attempt.attempt_count)

    if block_duration:
        attempt.blocked_until = now + block_duration
        print(
            f"IP blocked: {ip_address}; "
            f"attempts={attempt.attempt_count}; "
            f"duration={block_duration}"
        )
    else:
        attempt.blocked_until = None
        print(
            f"Failed login: {ip_address}; "
            f"attempts={attempt.attempt_count}"
        )

    db.commit()

def reset_login_attempts(db: Session, ip_address: str):
    """Reset login attempts for IP after successful login"""
    attempt = db.query(LoginAttempt).filter(LoginAttempt.ip_address == ip_address).first()
    if attempt:
        attempt.attempt_count = 0
        attempt.blocked_until = None
        db.commit()
