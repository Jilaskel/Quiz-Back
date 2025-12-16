from app.db.session import engine, Session, init_db
from app.db.repositories.images import ImageRepository
from app.features.media.services import ImageService
from app.db.seed import seed_all
import asyncio

async def run_seed():
    init_db()
    with Session(engine) as session:
        image_repo = ImageRepository(session)
        image_service = ImageService(repo=image_repo)

        # 3️⃣ lancer le seed
        await seed_all(
            session=session,
            seed_path="app/db/seed_data.yaml",
            img_svc=image_service,
        )
        session.close()

asyncio.run(run_seed())