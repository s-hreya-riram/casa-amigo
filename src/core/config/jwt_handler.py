from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

# 1. Prioritize os.getenv
SECRET_KEY = os.getenv("SECRET_KEY")

# 2. Check if the key was found, and raise an error if not
if not SECRET_KEY:
    raise ValueError(
        "SECRET_KEY environment variable not set. "
        "Ensure it is configured in your Render service environment variables."
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()


def create_access_token(user_id: UUID, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token for a user."""
    to_encode = {"sub": str(user_id)}
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        raise ValueError(f"Failed to create token: {str(e)}")


def verify_token(token: str) -> Optional[UUID]:
    """Verify JWT token and return user_id if valid."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return UUID(user_id)
    except JWTError:
        return None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UUID:
    """
    Dependency to extract and verify user from JWT token.
    Use this on protected endpoints.
    """
    token = credentials.credentials
    user_id = verify_token(token)
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_id