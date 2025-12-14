from typing import Optional, Dict

from sqlmodel import Session, select
from app.db.models.users import User
from app.db.models.colors import Color
from app.db.models.categories import Category 

from app.security.password import hash_password

# Associe chaque catégorie à une couleur (par NOM de couleur déjà seedée)
CATEGORY_TO_COLOR_NAME: Dict[str, str] = {
    "Films/Séries": "Orange",
    "Musique": "Pink",
    "Littérature/BDs": "Brown",
    "Manga/Animés": "Violet",
    "Jeux vidéo": "Lime",
    "Sport": "Red",
    "Histoire": "Yellow",
    "Géographie": "Blue",
    "Science": "Green",
    "Arts plastiques": "Indigo",
    "Technologie": "Teal",
    "Divers": "Gray",
}

def seed_users(session: Session):
    if not session.exec(select(User)).first():
        session.add_all([
            User(username="Thomas", hashed_password=hash_password("Thomas123"), admin=True),
            User(username="Martin", hashed_password=hash_password("Martin123"), admin=True),
            User(username="Maxime", hashed_password=hash_password("Maxime123"), admin=False),
        ])
        session.commit()
        print("✅ Utilisateurs insérés.")
    else:
        print("ℹ️ Les utilisateurs existent déjà, aucune insertion effectuée.")

def seed_colors(session: Session):
    """Insère une palette de 12 couleurs contrastées si la table est vide."""

    if not session.exec(select(Color)).first():
        session.add_all([
            Color(name="Red", hex_code="#E63946", description="Rouge vif, couleur d'alerte ou d'action."),
            Color(name="Orange", hex_code="#F77F00", description="Orange énergique, pour attirer l'attention."),
            Color(name="Yellow", hex_code="#FFBE0B", description="Jaune lumineux, utilisé pour les avertissements."),
            Color(name="Lime", hex_code="#9EF01A", description="Vert citron éclatant, symbole de fraîcheur."),
            Color(name="Green", hex_code="#2A9D8F", description="Vert apaisant, associé à la stabilité."),
            Color(name="Teal", hex_code="#00B4D8", description="Bleu sarcelle lumineux, couleur technologique."),
            Color(name="Blue", hex_code="#1D4ED8", description="Bleu profond, couleur de confiance."),
            Color(name="Indigo", hex_code="#5E60CE", description="Indigo soutenu, élégant et professionnel."),
            Color(name="Violet", hex_code="#9B5DE5", description="Violet doux, évoquant la créativité."),
            Color(name="Pink", hex_code="#FF006E", description="Rose fuchsia, pour une touche vibrante."),
            Color(name="Brown", hex_code="#8D5524", description="Brun terreux, pour des éléments naturels."),
            Color(name="Gray", hex_code="#6B7280", description="Gris neutre, parfait pour les fonds ou textes secondaires."),
        ])
        session.commit()
        print("✅ Palette de 12 couleurs contrastées insérée.")
    else:
        print("ℹ️ Les couleurs existent déjà, aucune insertion effectuée.")

def seed_categories(session: Session):
    """Insère les catégories de quizz classiques, liées aux couleurs déjà seedées."""
    if not session.exec(select(Category)).first():
        categories = []
        for cat_name, color_name in CATEGORY_TO_COLOR_NAME.items():
            color = session.exec(select(Color).where(Color.name == color_name)).first()
            categories.append(Category(name=cat_name, color_id=color.id))
        session.add_all(categories)
        session.commit()
        print("✅ Catégories de quizz insérées.")
    else:
        print("ℹ️ Les catégories existent déjà, aucune insertion effectuée.")