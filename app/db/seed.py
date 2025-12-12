from sqlmodel import Session, select
from app.domain.models import Todo

def seed_db(session: Session):
    if not session.exec(select(Todo)).first():
        session.add_all([
            Todo(title="Faire les courses"),
            Todo(title="Arroser les plantes"),
            Todo(title="Nettoyer la voiture"),
        ])
        session.commit()