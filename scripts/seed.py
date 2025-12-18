from app.db.session import engine, Session, init_db

from app.db.repositories.images import ImageRepository
from app.db.repositories.audios import AudioRepository
from app.db.repositories.videos import VideoRepository

from app.features.media.services import ImageService, AudioService, VideoService

from app.db.seed import seed_all
import asyncio

async def run_seed():
    init_db()
    with Session(engine) as session:
        image_repo = ImageRepository(session)
        audio_repo = AudioRepository(session)
        video_repo = VideoRepository(session)

        image_service = ImageService(repo=image_repo)
        audio_service = AudioService(repo=audio_repo)
        video_service = VideoService(repo=video_repo)

        # 3️⃣ lancer le seed
        await seed_all(
            session=session,
            seed_path="app/db/seed_data.yaml",
            img_svc=image_service,
            audio_svc=audio_service,
            video_svc=video_service,
        )
        session.close()

asyncio.run(run_seed())