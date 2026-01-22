"""
Authentication routes for BAR Community Map Sharing Portal.
Handles user registration, login, and token management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import UserCreate, UserLogin, UserResponse, Token
from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    authenticate_user,
    get_user_by_username,
    get_user_by_email,
    get_current_user
)


# =============================================================================
# Router Setup
# =============================================================================

router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
)


# =============================================================================
# Registration Endpoint
# =============================================================================

@router.post(
    "/register",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with username, email, and password. Returns JWT access token.",
    responses={
        201: {"description": "User successfully registered"},
        400: {"description": "Username or email already exists"},
        422: {"description": "Validation error"}
    }
)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
) -> Token:
    """
    Register a new user account.

    Args:
        user_data: User registration data (username, email, password)
        db: Database session

    Returns:
        Token response with access_token, token_type, and user info

    Raises:
        HTTPException 400: If username or email already exists
        HTTPException 422: If validation fails
    """
    # Check if username already exists
    existing_user = get_user_by_username(db, username=user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Check if email already exists
    existing_email = get_user_by_email(db, email=user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        is_active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Generate access token
    access_token = create_access_token(
        data={
            "sub": new_user.username,
            "user_id": new_user.id
        }
    )

    # Return token and user info
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(new_user)
    )


# =============================================================================
# Login Endpoint
# =============================================================================

@router.post(
    "/login",
    response_model=Token,
    summary="Login with username and password",
    description="Authenticate user and return JWT access token.",
    responses={
        200: {"description": "Login successful"},
        401: {"description": "Invalid credentials"}
    }
)
async def login(
    user_data: UserLogin,
    db: Session = Depends(get_db)
) -> Token:
    """
    Login user with username and password.

    Args:
        user_data: User login data (username, password)
        db: Database session

    Returns:
        Token response with access_token, token_type, and user info

    Raises:
        HTTPException 401: If credentials are invalid
    """
    # Authenticate user
    user = authenticate_user(db, username=user_data.username, password=user_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate access token
    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.id
        }
    )

    # Return token and user info
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


# =============================================================================
# OAuth2 Compatible Login (for Swagger UI)
# =============================================================================

@router.post(
    "/token",
    response_model=Token,
    summary="OAuth2 token endpoint (for Swagger UI)",
    description="OAuth2-compatible token endpoint. Use this endpoint from Swagger UI's 'Authorize' button.",
    include_in_schema=False  # Hide from default docs, but still available for Swagger
)
async def login_oauth2(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Token:
    """
    OAuth2-compatible login endpoint for Swagger UI.

    This endpoint accepts form data (username, password) and returns a JWT token.
    It's used by FastAPI's built-in OAuth2 authentication in the Swagger UI.

    Args:
        form_data: OAuth2 form data (username, password)
        db: Database session

    Returns:
        Token response with access_token, token_type, and user info

    Raises:
        HTTPException 401: If credentials are invalid
    """
    # Authenticate user
    user = authenticate_user(db, username=form_data.username, password=form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate access token
    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.id
        }
    )

    # Return token and user info
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


# =============================================================================
# Current User Endpoint
# =============================================================================

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user",
    description="Returns information about the currently authenticated user.",
    responses={
        200: {"description": "User information returned successfully"},
        401: {"description": "Not authenticated"}
    }
)
async def get_me(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """
    Get the current authenticated user's information.

    This endpoint requires a valid JWT token in the Authorization header.
    Returns the user's profile information if authenticated.

    Args:
        current_user: The authenticated user (injected by get_current_user dependency)

    Returns:
        UserResponse with the user's information

    Raises:
        HTTPException 401: If no valid token is provided
    """
    return UserResponse.model_validate(current_user)
