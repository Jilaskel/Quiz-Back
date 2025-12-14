from app.db.session import engine, Session, init_db
from app.db.seed import seed_users, seed_colors, seed_categories

def main():
    init_db()
    with Session(engine) as session:
        seed_users(session)
        seed_colors(session)
        seed_categories(session)
    print("🌱 Base peuplée avec succès !")

if __name__ == "__main__":
    main()