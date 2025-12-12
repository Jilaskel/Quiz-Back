from app.db.session import engine, Session, init_db
from app.db.seed import seed_db

def main():
    init_db()
    with Session(engine) as session:
        seed_db(session)
    print("🌱 Base peuplée avec succès !")

if __name__ == "__main__":
    main()