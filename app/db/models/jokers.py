
from sqlmodel import Field

from app.db.models.base import BaseModelDB

class Joker(BaseModelDB, table=True):

    name: str = Field(nullable=False, unique=True, index=True)
    description: str = Field(nullable=False)