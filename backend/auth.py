"""
Authentication utilities for BAR Community Map Sharing Portal.
Implements JWT token generation, validation, and password hashing.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import User


# =============================================================================
# Password Hashing
# =============================================================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password: The plain text password to verify
        hashed_password: The hashed password to compare against

    Returns:
        True if passwords match, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: The plain text password to hash

    Returns:
        The hashed password
    """
    return pwd_context.hash(password)


# =============================================================================
# JWT Token Operations
# =============================================================================

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: The payload data to encode in the token (e.g., {"sub": username, "user_id": 123})
        expires_delta: Optional custom expiration time. Defaults to ACCESS_TOKEN_EXPIRE_MINUTES

    Returns:
        The encoded JWT token as a string

    Example:
        >>> token = create_access_token({"sub": "user123", "user_id": 1})
        >>> print(token)
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    """
    to_encode = data.copy()

    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    # Encode JWT
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT token.

    Args:
        token: The JWT token to verify

    Returns:
        The decoded token payload

    Raises:
        HTTPException: If token is invalid or expired

    Example:
        >>> payload = verify_token("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
        >>> print(payload)
        {"sub": "user123", "user_id": 1, "exp": 1234567890}
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# =============================================================================
# User Authentication
# =============================================================================

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Authenticate a user by username and password.

    Args:
        db: Database session
        username: The username to authenticate
        password: The plain text password to verify

    Returns:
        The User object if authentication successful, None otherwise

    Example:
        >>> user = authenticate_user(db, "john_doe", "securepass123")
        >>> if user:
        ...     print(f"Authenticated: {user.username}")
    """
    user = db.query(User).filter(User.username == username).first()

    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    if not user.is_active:
        return None

    return user


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """
    Retrieve a user by username.

    Args:
        db: Database session
        username: The username to look up

    Returns:
        The User object if found, None otherwise
    """
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Retrieve a user by email address.

    Args:
        db: Database session
        email: The email address to look up

    Returns:
        The User object if found, None otherwise
    """
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """
    Retrieve a user by ID.

    Args:
        db: Database session
        user_id: The user ID to look up

    Returns:
        The User object if found, None otherwise
    """
    return db.query(User).filter(User.id == user_id).first()


# =============================================================================
# FastAPI Dependencies
# =============================================================================

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency to get the current authenticated user from JWT token.

    This function should be used in protected route endpoints:
        @app.get("/api/maps")
        async def get_maps(current_user: User = Depends(get_current_user)):
            ...

    Args:
        credentials: The HTTP Bearer credentials (extracted from Authorization header)
        db: Database session

    Returns:
        The authenticated User object

    Raises:
        HTTPException: If token is invalid, expired, or user not found

    Example:
        >>> @app.get("/api/me")
        ... async def get_me(current_user: User = Depends(get_current_user)):
        ...     return current_user
    """
    token = credentials.credentials

    # Verify and decode token
    payload = verify_token(token)

    username: str = payload.get("sub")
    user_id: int = payload.get("user_id")

    if username is None or user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user = get_user_by_id(db, user_id=user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    FastAPI dependency to get the current active user.

    This is an additional layer on top of get_current_user that explicitly
    checks for active status. Useful for endpoints that require active users.

    Args:
        current_user: The current user from get_current_user dependency

    Returns:
        The active User object

    Raises:
        HTTPException: If user is not active

    Example:
        >>> @app.post("/api/maps")
        ... async def upload_map(current_user: User = Depends(get_current_active_user)):
        ...     # User is guaranteed to be active here
        ...     pass
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    return current_user


# =============================================================================
# Optional Authentication (allows anonymous access)
# =============================================================================

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    FastAPI dependency to optionally get the current user.

    This allows endpoints to work both authenticated and unauthenticated.
    Returns None if no valid token is provided.

    Args:
        credentials: Optional HTTP Bearer credentials
        db: Database session

    Returns:
        The User object if authenticated and valid, None otherwise

    Example:
        >>> @app.get("/api/maps")
        ... async def get_maps(user: Optional[User] = Depends(get_optional_user)):
        ...     if user:
        ...         # Show personalized results
        ...     else:
        ...         # Show public results
    """
    if credentials is None:
        return None

    try:
        token = credentials.credentials
        payload = verify_token(token)

        user_id: int = payload.get("user_id")
        if user_id is None:
            return None

        user = get_user_by_id(db, user_id=user_id)
        return user if user and user.is_active else None

    except (JWTError, HTTPException):
        return None
