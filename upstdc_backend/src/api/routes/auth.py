from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from src.api.schemas import TokenPair, UserPublic
from src.api.security import (
    create_token,
    verify_password,
    get_current_user,
)
from src.api.db.mongo import get_db
from src.api.config import get_settings

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", summary="Login and get JWT tokens", response_model=TokenPair)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate with email and password to get access and refresh tokens.
    """
    try:
        db = get_db()
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")
    user = await db.users.find_one({"email": form_data.username})
    if not user or not verify_password(form_data.password, user.get("password_hash", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    settings = get_settings()
    access_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)

    access_token = create_token(str(user["_id"]), access_expires, {"type": "access"})
    refresh_token = create_token(str(user["_id"]), refresh_expires, {"type": "refresh"})

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(access_expires.total_seconds()),
    )


@router.post("/refresh", summary="Refresh access token", response_model=TokenPair)
async def refresh_token(current_user=Depends(get_current_user)):
    """
    Use refresh token to obtain new access token. For simplicity, this endpoint expects
    'Authorization: Bearer <refresh_token>' header even for refresh.
    """
    settings = get_settings()
    access_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    access_token = create_token(str(current_user["_id"]), access_expires, {"type": "access"})
    refresh_token = create_token(str(current_user["_id"]), refresh_expires, {"type": "refresh"})
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(access_expires.total_seconds()),
    )


@router.post("/logout", summary="Logout", status_code=204)
async def logout():
    """
    Stateless JWT logout; clients should discard tokens. If token blacklisting is needed,
    implement a denylist store.
    """
    return


@router.get("/me", summary="Get current user profile", response_model=UserPublic)
async def me(current_user=Depends(get_current_user)):
    """
    Return currently authenticated user details.
    """
    # Project a minimal public view
    return {
        "_id": str(current_user["_id"]),
        "email": current_user["email"],
        "full_name": current_user.get("full_name", ""),
        "roles": current_user.get("roles", []),
    }
