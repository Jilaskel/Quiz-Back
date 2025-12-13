from sqlmodel import Session, select
from app.models.users import User

from app.security.password import hash_password

def seed_db(session: Session):
    if not session.exec(select(User)).first():
        session.add_all([
            User(username="Thomas", hashed_password=hash_password("Thomas")),
            User(username="Martin", hashed_password=hash_password("Martin")),
        ])
        session.commit()