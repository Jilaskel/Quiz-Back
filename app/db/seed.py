import io
import json
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from sqlmodel import Session, select
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from app.db.models.users import User
from app.db.models.colors import Color
from app.db.models.categories import Category
from app.db.models.themes import Theme
from app.db.models.questions import Question
from app.db.models.jokers import Joker
from app.db.models.bonus import Bonus
from app.security.password import hash_password

from app.features.media.services import ImageService, AudioService, VideoService


# -----------------------------
# YAML loader
# -----------------------------
def load_seed_yaml(seed_path: str | Path) -> Dict[str, Any]:
    path = Path(seed_path)
    if not path.exists():
        raise FileNotFoundError(f"Seed YAML introuvable: {path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Le YAML de seed doit contenir un objet racine (mapping).")
    return data


# -----------------------------
# Helpers
# -----------------------------
def _uploadfile_from_path(path: Path) -> UploadFile:
    content_type, _ = mimetypes.guess_type(str(path))
    content_type = content_type or "application/octet-stream"
    fileobj = io.BytesIO(path.read_bytes())
    return UploadFile(filename=path.name, file=fileobj, headers={"content-type": content_type})


def _build_color_key_maps(data: Dict[str, Any]) -> Dict[str, str]:
    """color_key -> Color.name (car Color.key n'existe pas en DB)."""
    colors_yaml: List[Dict[str, Any]] = data.get("colors", [])
    return {c["key"]: c["name"] for c in colors_yaml}


def _build_category_key_maps(data: Dict[str, Any]) -> Dict[str, str]:
    """category_key -> Category.name (car Category.key n'existe pas en DB)."""
    categories_yaml: List[Dict[str, Any]] = data.get("categories", [])
    return {c["key"]: c["name"] for c in categories_yaml}


def _build_user_key_maps(data: Dict[str, Any]) -> Dict[str, str]:
    """owner_key -> User.username (car User.key n'existe pas en DB)."""
    users_yaml: List[Dict[str, Any]] = data.get("users", [])
    return {u["key"]: u["username"] for u in users_yaml}


def _build_theme_key_maps(data: Dict[str, Any]) -> Dict[str, str]:
    """theme_key -> Theme.name (pour retrouver un thème via YAML)."""
    themes_yaml: List[Dict[str, Any]] = data.get("themes", [])
    return {t["key"]: t["name"] for t in themes_yaml if "key" in t and "name" in t}


def _resolve_rel_path(base_json_path: Path, rel_path: str) -> Path:
    """
    Les paths dans le JSON sont relatifs au fichier questions.json.
    """
    p = Path(rel_path)
    if p.is_absolute():
        return p
    return (base_json_path.parent / p).resolve()


def _load_questions_json(json_path: Path) -> List[Dict[str, Any]]:
    if not json_path.exists():
        raise FileNotFoundError(f"questions.json introuvable: {json_path}")
    raw = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"Format invalide: {json_path} doit contenir une liste JSON.")
    # sécurise types
    out: List[Dict[str, Any]] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"Entrée JSON invalide à l'index {i} dans {json_path} (objet attendu).")
        out.append(item)
    return out


async def _upload_optional_image(
    img_svc: ImageService,
    *,
    file_path: Optional[Path],
    owner_id: int,
) -> Optional[int]:
    if not file_path:
        return None
    if not file_path.exists():
        print(f"⚠️ Image introuvable (ignorée): {file_path}")
        return None
    try:
        uf = _uploadfile_from_path(file_path)
        data = await img_svc.upload(uf, owner_id=owner_id)
        return data.get("id")
    except Exception as e:
        print(f"⚠️ Upload image échoué (ignorée): {file_path} — {e}")
        return None


async def _upload_optional_audio(
    audio_svc: AudioService,
    *,
    file_path: Optional[Path],
    owner_id: int,
) -> Optional[int]:
    if not file_path:
        return None
    if not file_path.exists():
        print(f"⚠️ Audio introuvable (ignoré): {file_path}")
        return None
    try:
        uf = _uploadfile_from_path(file_path)
        data = await audio_svc.upload(uf, owner_id=owner_id)
        return data.get("id")
    except Exception as e:
        print(f"⚠️ Upload audio échoué (ignoré): {file_path} — {e}")
        return None


async def _upload_optional_video(
    video_svc: VideoService,
    *,
    file_path: Optional[Path],
    owner_id: int,
) -> Optional[int]:
    if not file_path:
        return None
    if not file_path.exists():
        print(f"⚠️ Vidéo introuvable (ignorée): {file_path}")
        return None
    try:
        uf = _uploadfile_from_path(file_path)
        data = await video_svc.upload(uf, owner_id=owner_id)
        return data.get("id")
    except Exception as e:
        print(f"⚠️ Upload vidéo échoué (ignorée): {file_path} — {e}")
        return None


def _delete_questions_for_theme(session: Session, theme_id: int) -> int:
    rows = session.exec(select(Question).where(Question.theme_id == theme_id)).all()
    for r in rows:
        session.delete(r)
    session.commit()
    return len(rows)


# -----------------------------
# Seed Colors
# -----------------------------
def seed_colors(session: Session, data: Dict[str, Any]) -> None:
    if session.exec(select(Color)).first():
        print("ℹ️ Les couleurs existent déjà, aucune insertion effectuée.")
        return

    colors: List[Dict[str, Any]] = data.get("colors", [])
    if not colors:
        print("⚠️ Aucune couleur dans le YAML (clé 'colors').")
        return

    session.add_all([
        Color(
            name=c["name"],
            hex_code=c["hex_code"],
            description=c.get("description"),
        )
        for c in colors
    ])
    session.commit()
    print(f"✅ Palette de {len(colors)} couleurs insérée.")


# -----------------------------
# Seed Categories
# -----------------------------
def seed_categories(session: Session, data: Dict[str, Any]) -> None:
    if session.exec(select(Category)).first():
        print("ℹ️ Les catégories existent déjà, aucune insertion effectuée.")
        return

    categories: List[Dict[str, Any]] = data.get("categories", [])
    if not categories:
        print("⚠️ Aucune catégorie dans le YAML (clé 'categories').")
        return

    color_key_to_name = _build_color_key_maps(data)
    color_name_to_id = {c.name: c.id for c in session.exec(select(Color)).all()}

    objs: List[Category] = []
    for cat in categories:
        color_key = cat["color_key"]
        color_name = color_key_to_name.get(color_key)
        if not color_name:
            raise ValueError(f"color_key '{color_key}' inconnu pour category '{cat.get('name')}'.")

        color_id = color_name_to_id.get(color_name)
        if not color_id:
            raise ValueError(
                f"Couleur '{color_name}' introuvable en DB. "
                "As-tu bien seed les couleurs avant les catégories ?"
            )

        objs.append(Category(name=cat["name"], color_id=color_id))

    session.add_all(objs)
    session.commit()
    print(f"✅ {len(objs)} catégories insérées.")


# -----------------------------
# Seed Users
# -----------------------------
def seed_users(session: Session, data: Dict[str, Any]) -> None:
    if session.exec(select(User)).first():
        print("ℹ️ Les utilisateurs existent déjà, aucune insertion effectuée.")
        return

    users: List[Dict[str, Any]] = data.get("users", [])
    if not users:
        print("⚠️ Aucun utilisateur dans le YAML (clé 'users').")
        return

    session.add_all([
        User(
            username=u["username"],
            hashed_password=hash_password(u["password"]),
            admin=bool(u.get("admin", False)),
        )
        for u in users
    ])
    session.commit()
    print(f"✅ {len(users)} utilisateurs insérés.")

# ------------------------------------------------------------
# Seed Jokers
# ------------------------------------------------------------
def seed_jokers(session: Session, data: Dict[str, Any]) -> None:
    """
    Seed idempotent des jokers.
    - Si au moins un Joker existe déjà, on ne réinsère rien (comportement cohérent avec les autres seeds).
    - Utilise la clé YAML `jokers:`
    """
    if session.exec(select(Joker)).first():
        print("ℹ️ Les jokers existent déjà, aucune insertion effectuée.")
        return

    jokers: List[Dict[str, Any]] = data.get("jokers", [])
    if not jokers:
        print("⚠️ Aucun joker dans le YAML (clé 'jokers').")
        return

    session.add_all([
        Joker(
            name=j["name"],
            description=j["description"],
        )
        for j in jokers
    ])
    session.commit()
    print(f"✅ {len(jokers)} jokers insérés.")


# ------------------------------------------------------------
# Seed Bonus
# ------------------------------------------------------------
def seed_bonus(session: Session, data: Dict[str, Any]) -> None:
    """
    Seed idempotent des bonus.
    - Utilise la clé YAML `bonus:`
    """
    if session.exec(select(Bonus)).first():
        print("ℹ️ Les bonus existent déjà, aucune insertion effectuée.")
        return

    bonus: List[Dict[str, Any]] = data.get("bonus", [])
    if not bonus:
        print("⚠️ Aucun bonus dans le YAML (clé 'bonus').")
        return

    session.add_all([
        Bonus(
            name=b["name"],
            description=b["description"],
        )
        for b in bonus
    ])
    session.commit()
    print(f"✅ {len(bonus)} bonus insérés.")

# -----------------------------
# Seed Themes (+ upload image)
# -----------------------------
async def seed_themes(
    session: Session,
    img_svc: ImageService,
    data: Dict[str, Any]
) -> None:
    themes: List[Dict[str, Any]] = data.get("themes", [])

    if session.exec(select(Theme)).first():
        print("ℹ️ Les thèmes existent déjà, aucune insertion effectuée.")
        return

    if not themes:
        print("ℹ️ Aucun thème dans le YAML (clé 'themes'), aucune insertion effectuée.")
        return

    category_key_to_name = _build_category_key_maps(data)
    user_key_to_username = _build_user_key_maps(data)

    category_name_to_id = {c.name: c.id for c in session.exec(select(Category)).all()}
    username_to_id = {u.username: u.id for u in session.exec(select(User)).all()}

    inserted = 0
    skipped_existing = 0
    skipped_upload = 0
    skipped_db = 0

    for t in themes:
        theme_name = t["name"]

        # --- Owner ---
        owner_key = t["owner_key"]
        username = user_key_to_username.get(owner_key)
        if not username:
            raise ValueError(f"owner_key inconnu '{owner_key}' pour theme '{theme_name}'")

        owner_id = username_to_id.get(username)
        if not owner_id:
            raise ValueError(f"Utilisateur '{username}' introuvable en DB (theme '{theme_name}')")

        # --- Category ---
        cat_key = t["category_key"]
        cat_name = category_key_to_name.get(cat_key)
        if not cat_name:
            raise ValueError(f"category_key inconnu '{cat_key}' pour theme '{theme_name}'")

        category_id = category_name_to_id.get(cat_name)
        if not category_id:
            raise ValueError(
                f"Catégorie introuvable en DB pour theme '{theme_name}' "
                f"(category_key='{cat_key}' -> category_name='{cat_name}')."
            )

        # --- Idempotence: (name + owner_id) ---
        existing = session.exec(
            select(Theme).where(Theme.name == theme_name, Theme.owner_id == owner_id)
        ).first()
        if existing:
            skipped_existing += 1
            continue

        # --- Image path obligatoire ---
        image_path = t.get("image_path")
        if not image_path:
            raise ValueError(f"image_path manquant pour theme '{theme_name}' (seed exige une image).")

        img_path = Path(image_path)
        if not img_path.exists():
            raise FileNotFoundError(f"Image introuvable pour theme '{theme_name}': {img_path}")

        # --- Upload image + insert Image DB ---
        try:
            upload_file = _uploadfile_from_path(img_path)
            img_data = await img_svc.upload(upload_file, owner_id=owner_id)
            image_id = img_data.get("id")
            if not image_id:
                skipped_upload += 1
                print(f"⚠️ Upload OK mais image_id manquant → thème ignoré: '{theme_name}'.")
                continue
        except HTTPException as e:
            skipped_upload += 1
            print(f"⚠️ Upload MinIO échoué → thème ignoré: '{theme_name}'. Détail: {e.detail}")
            continue
        except Exception as e:
            skipped_upload += 1
            print(f"⚠️ Upload MinIO échoué → thème ignoré: '{theme_name}'. Erreur: {e}")
            continue

        # --- Insert Theme DB ---
        try:
            theme = Theme(
                name=theme_name,
                description=t.get("description"),
                is_public=bool(t.get("is_public", True)),
                is_ready=bool(t.get("is_ready", True)),
                valid_admin=bool(t.get("valid_admin", True)),
                image_id=image_id,
                category_id=category_id,
                owner_id=owner_id,
            )
            session.add(theme)
            session.commit()
            inserted += 1

        except Exception as e:
            session.rollback()
            skipped_db += 1
            print(f"⚠️ Insertion DB échouée → thème ignoré: '{theme_name}'. Erreur: {e}")
            continue

    print(
        f"✅ Thèmes insérés : {inserted} | "
        f"ignorés (déjà présents) : {skipped_existing} | "
        f"ignorés (upload KO) : {skipped_upload} | "
        f"ignorés (DB KO après upload) : {skipped_db}."
    )


# -----------------------------
# Seed Questions (depuis JSON par thème)
# -----------------------------
async def seed_questions_from_json(
    session: Session,
    img_svc: ImageService,
    audio_svc: AudioService,
    video_svc: VideoService,
    data: Dict[str, Any],
    *,
    replace_existing: bool = True,
) -> None:
    """
    Pour chaque thème du YAML, lit questions_json_path et remplit la table Question.
    - replace_existing=True : supprime les questions existantes du thème puis réinsère (idempotent).
    - Upload des médias optionnels :
        - Image_question_path -> question_image_id
        - Image_answer_path   -> answer_image_id
        - Sound_path          -> question_audio_id (par défaut audio côté question)
        - (optionnel) Video_path si un jour présent -> question_video_id
    """
    themes_yaml: List[Dict[str, Any]] = data.get("themes", [])
    if not themes_yaml:
        print("ℹ️ Aucun thème dans le YAML, seed questions ignoré.")
        return

    user_key_to_username = _build_user_key_maps(data)
    username_to_id = {u.username: u.id for u in session.exec(select(User)).all()}

    inserted_total = 0
    replaced_total = 0
    skipped_no_json = 0

    for t in themes_yaml:
        theme_name = t.get("name")
        theme_key = t.get("key")

        # 1) retrouver theme en DB (par name + owner comme vous faites déjà)
        owner_key = t["owner_key"]
        username = user_key_to_username.get(owner_key)
        if not username:
            print(f"⚠️ owner_key inconnu '{owner_key}' (theme '{theme_name}') → questions ignorées.")
            continue
        owner_id = username_to_id.get(username)
        if not owner_id:
            print(f"⚠️ owner '{username}' introuvable (theme '{theme_name}') → questions ignorées.")
            continue

        theme = session.exec(
            select(Theme).where(Theme.name == theme_name, Theme.owner_id == owner_id)
        ).first()
        if not theme:
            print(f"⚠️ Thème introuvable en DB (theme '{theme_name}') → questions ignorées.")
            continue

        # 2) trouver le JSON associé
        questions_json_path = t.get("questions_json_path")
        if not questions_json_path:
            skipped_no_json += 1
            print(f"ℹ️ Pas de questions_json_path pour theme '{theme_name}' → ignoré.")
            continue

        json_path = Path(questions_json_path)
        if not json_path.exists():
            print(f"⚠️ questions.json introuvable pour theme '{theme_name}': {json_path} → ignoré.")
            continue

        # 3) replace / delete
        if replace_existing:
            deleted = _delete_questions_for_theme(session, theme.id)
            replaced_total += deleted

        # 4) load JSON + create questions
        rows = _load_questions_json(json_path)

        to_insert: List[Question] = []
        for item in rows:
            q_text = (item.get("Question_text") or "").strip()
            a_text = (item.get("Answer_text") or "").strip()
            points = int(item.get("Value") or 0)

            # media paths relatifs au json
            q_img_rel = item.get("Image_question_path")
            a_img_rel = item.get("Image_answer_path")
            sound_rel = item.get("Sound_path")
            video_rel = item.get("Video_path")  # optionnel futur

            q_img_path = _resolve_rel_path(json_path, q_img_rel) if q_img_rel else None
            a_img_path = _resolve_rel_path(json_path, a_img_rel) if a_img_rel else None
            sound_path = _resolve_rel_path(json_path, sound_rel) if sound_rel else None
            video_path = _resolve_rel_path(json_path, video_rel) if video_rel else None

            # uploads optionnels
            question_image_id = await _upload_optional_image(img_svc, file_path=q_img_path, owner_id=owner_id)
            answer_image_id = await _upload_optional_image(img_svc, file_path=a_img_path, owner_id=owner_id)
            question_audio_id = await _upload_optional_audio(audio_svc, file_path=sound_path, owner_id=owner_id)
            question_video_id = await _upload_optional_video(video_svc, file_path=video_path, owner_id=owner_id)

            to_insert.append(
                Question(
                    theme_id=theme.id,
                    question=q_text,
                    answer=a_text,
                    points=points,
                    question_image_id=question_image_id,
                    answer_image_id=answer_image_id,
                    question_audio_id=question_audio_id,
                    answer_audio_id=None,
                    question_video_id=question_video_id,
                    answer_video_id=None,
                )
            )

        if not to_insert:
            print(f"ℹ️ Aucune question à insérer pour theme '{theme_name}'.")
            continue

        try:
            session.add_all(to_insert)
            session.commit()
            inserted_total += len(to_insert)
            print(f"✅ Questions insérées pour '{theme_name}' : {len(to_insert)}")
        except Exception as e:
            session.rollback()
            print(f"⚠️ Insertion questions échouée pour '{theme_name}': {e}")

    print(
        f"✅ Total questions insérées : {inserted_total} | "
        f"questions supprimées (replace) : {replaced_total} | "
        f"thèmes sans JSON : {skipped_no_json}"
    )


# -----------------------------
# Main entrypoint
# -----------------------------
async def seed_all(
    session: Session,
    seed_path: str,
    img_svc: ImageService,
    audio_svc: AudioService,
    video_svc: VideoService,
):
    data = load_seed_yaml(seed_path)

    seed_colors(session, data)
    seed_categories(session, data)
    seed_users(session, data)

    seed_jokers(session, data)
    seed_bonus(session, data)
    
    await seed_themes(session, img_svc, data)

    await seed_questions_from_json(session, img_svc, audio_svc, video_svc, data, replace_existing=True)
