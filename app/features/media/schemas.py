from pydantic import BaseModel

class ImageOut(BaseModel):
    id: int
    key: str
    bytes: int
    mime: str

class AudioOut(BaseModel):
    id: int
    key: str
    bytes: int
    mime: str

class VideoOut(BaseModel):
    id: int
    key: str
    bytes: int
    mime: str

class SignedUrlOut(BaseModel):
    id: str
    url: str
    expires_in: int
