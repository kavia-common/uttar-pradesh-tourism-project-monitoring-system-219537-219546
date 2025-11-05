from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from src.api.config import get_settings
from src.api.db.mongo import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# PUBLIC_INTERFACE
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plaintext password against hashed value."""
    return pwd_context.verify(plain_password, hashed_password)


# PUBLIC_INTERFACE
def get_password_hash(password: str) -> str:
    """Hash password using bcrypt."""
    return pwd_context.hash(password)


# PUBLIC_INTERFACE
def create_token(subject: str, expires_delta: timedelta, extra_claims: Optional[Dict[str, Any]] = None) -> str:
    """Create JWT token for subject with expiration and optional extra claims."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


# PUBLIC_INTERFACE
def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate JWT token; raises HTTPException on error."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from e


# PUBLIC_INTERFACE
async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Retrieve current user from token and database."""
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token subject")
    db = get_db()
    user = await db.users.find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# PUBLIC_INTERFACE
def rbac_required(required_roles: Optional[List[str]] = None, required_permissions: Optional[List[str]] = None):
    """Dependency factory to enforce RBAC based on roles/permissions stored in Mongo.

    - required_roles: user must have at least one role from this list
    - required_permissions: user must have at least one permission from this list
    """

    async def _checker(current_user=Depends(get_current_user)):
        if not required_roles and not required_permissions:
            return current_user

        user_roles: List[str] = current_user.get("roles", [])
        if required_roles:
            if not any(r in user_roles for r in required_roles):
                raise HTTPException(status_code=403, detail="Insufficient role")

        if required_permissions:
            db = get_db()
            roles_docs = await db.roles.find({"name": {"$in": user_roles}}).to_list(length=100)
            permissions = set()
            for r in roles_docs:
                for p in r.get("permissions", []):
                    permissions.add(p)
            if not any(p in permissions for p in required_permissions):
                raise HTTPException(status_code=403, detail="Insufficient permissions")

        return current_user

    return _checker
