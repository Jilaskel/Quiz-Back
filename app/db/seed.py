import io
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from sqlmodel import Session, select
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from app.db.models.users import User
from app.db.models.colors import Color
from app.db.models.categories import Category
from app.db.models.themes import Theme
from app.security.password import hash_password
from app.features.media.services import ImageService


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


# -----------------------------
# Seed Themes (+ upload image)
# -----------------------------
async def seed_themes(session: Session, img_svc: ImageService, data: Dict[str, Any]) -> None:
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

        # --- Étape 1-2 : upload MinIO + insert Image DB (via img_svc.upload) ---
        try:
            upload_file = _uploadfile_from_path(img_path)
            img_data = await img_svc.upload(upload_file, owner_id=owner_id)
            image_id = img_data.get("id")
            if not image_id:
                skipped_upload += 1
                print(f"⚠️ Upload OK mais image_id manquant → thème ignoré: '{theme_name}'.")
                # pas de theme sans image
                continue
        except HTTPException as e:
            skipped_upload += 1
            print(f"⚠️ Upload MinIO échoué → thème ignoré: '{theme_name}'. Détail: {e.detail}")
            continue
        except Exception as e:
            skipped_upload += 1
            print(f"⚠️ Upload MinIO échoué → thème ignoré: '{theme_name}'. Erreur: {e}")
            continue

        # --- Étape 3 : insert Theme DB ---
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

            # --- Étape 4 : commit par thème ---
            session.commit()
            inserted += 1

        except Exception as e:
            # Important : on annule l'ajout du thème si la DB plante après upload image
            session.rollback()
            skipped_db += 1
            print(f"⚠️ Insertion DB échouée → thème ignoré: '{theme_name}'. Erreur: {e}")
            # NB: ici l'image est déjà uploadée + enregistrée en DB (via img_svc.upload).
            # Si tu veux éviter les orphelins, il faudra implémenter un delete image.
            continue

    print(
        f"✅ Thèmes insérés : {inserted} | "
        f"ignorés (déjà présents) : {skipped_existing} | "
        f"ignorés (upload KO) : {skipped_upload} | "
        f"ignorés (DB KO après upload) : {skipped_db}."
    )


# -----------------------------
# Main entrypoint
# -----------------------------
async def seed_all(
    session: Session,
    seed_path: str,
    img_svc: ImageService,
):
    data = load_seed_yaml(seed_path)

    seed_colors(session, data)
    seed_categories(session, data)
    seed_users(session, data)
    await seed_themes(session, img_svc, data)