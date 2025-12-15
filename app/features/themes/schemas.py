from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field as PydField


# ---------- IN / UPDATE ----------

class ThemeCreateIn(BaseModel):
    name: str = PydField(..., description="Nom du thème")
    description: Optional[str] = None
    image_id: Optional[int] = None
    category_id: Optional[int] = None
    is_public: bool = False
    is_ready: bool = False
    # admin uniquement
    valid_admin: Optional[bool] = None
    # admin uniquement : créer pour un autre owner
    owner_id: Optional[int] = None


class ThemeUpdateIn(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image_id: Optional[int] = None
    category_id: Optional[int] = None
    is_public: Optional[bool] = None
    is_ready: Optional[bool] = None
    # admin uniquement
    valid_admin: Optional[bool] = None
    # admin uniquement
    owner_id: Optional[int] = None


# ---------- OUT ----------

class ThemeOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    image_id: Optional[int]
    category_id: Optional[int]
    owner_id: int
    is_public: bool
    is_ready: bool
    valid_admin: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ThemeWithSignedUrlOut(ThemeOut):
    image_signed_url: Optional[str] = None
    image_signed_expires_in: Optional[int] = None