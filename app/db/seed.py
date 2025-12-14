from sqlmodel import Session, select
from app.db.models.users import User

from app.security.password import hash_password

def seed_db(session: Session):
    if not session.exec(select(User)).first():
        session.add_all([
            User(username="Thomas", hashed_password=hash_password("Thomas123")),
            User(username="Martin", hashed_password=hash_password("Martin123")),
        ])
        session.commit()