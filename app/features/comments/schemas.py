from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field as PydField


class ThemeCommentCreateIn(BaseModel):
    game_id: int
    theme_id: int
    score: int = PydField(..., ge=0, le=5)
    comment: Optional[str] = None


class ThemeCommentUpdateIn(BaseModel):
    score: Optional[int] = PydField(None, ge=0, le=5)
    comment: Optional[str] = None


class ThemeCommentOut(BaseModel):
    id: int
    game_id: int
    theme_id: int
    score: int
    comment: Optional[str]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    game_owner_id: int
    game_owner_username: Optional[str]


class ThemeCommentListOut(BaseModel):
    items: List[ThemeCommentOut]
    total: int
