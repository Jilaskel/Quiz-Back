from sqlmodel import Field
from typing import Optional
from datetime import datetime

from .base import BaseModelDB

class RefreshToken(BaseModelDB, table=True):
    jti: str = Field(index=True, unique=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    expires_at: datetime
    revoked_at: Optional[datetime] = Field(default=None)
    user_agent: Optional[str] = None
    ip: Optional[str] = None