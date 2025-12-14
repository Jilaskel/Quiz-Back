# app/features/images/schemas.py
from pydantic import BaseModel

class ImageOut(BaseModel):
    id: int
    key: str
    bytes: int
    mime: str

class SignedUrlOut(BaseModel):
    id: str
    url: str
    expires_in: int