from sqlmodel import Session, select
from app.models.users import User

def seed_db(session: Session):
    if not session.exec(select(User)).first():
        session.add_all([
            User(username="Thomas", hashed_password="Thomas"),
            User(username="Martin", hashed_password="Martin"),
        ])
        session.commit()