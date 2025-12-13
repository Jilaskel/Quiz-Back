from typing import Any, Generic, Optional, Sequence, Type, TypeVar
from sqlmodel import SQLModel, Session, select, func

# Type générique pour le modèle (User, RefreshToken, etc.)
ModelT = TypeVar("ModelT", bound=SQLModel)

class BaseRepository(Generic[ModelT]):
    """
    Repository de base pour les opérations CRUD standards.

    👉 Ne contient aucune logique métier.
    👉 Gère la persistance générique : create, read, update, delete, count, list.
    👉 Les repositories concrets définissent `model = MaClasseSQLModel`.
    """

    model: Type[ModelT]

    def __init__(self, session: Session):
        self.session = session

    # ---------- READ ----------

    def list(self, offset: int = 0, limit: int = 100) -> Sequence[ModelT]:
        """Retourne une liste paginée des enregistrements."""
        statement = select(self.model).offset(offset).limit(limit)
        return self.session.exec(statement).all()

    def count(self) -> int:
        """Retourne le nombre total d’enregistrements."""
        return self.session.exec(select(func.count(self.model.id))).one()

    def get(self, id_: Any) -> Optional[ModelT]:
        """Retourne un enregistrement par son identifiant, ou None."""
        return self.session.get(self.model, id_)

    # ---------- CREATE ----------

    def create(self, **fields) -> ModelT:
        """Crée et persiste un nouvel enregistrement."""
        entity = self.model(**fields)
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity

    # ---------- UPDATE ----------

    def update(self, entity: ModelT, **changes) -> ModelT:
        """Met à jour un enregistrement existant."""
        for key, value in changes.items():
            setattr(entity, key, value)
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity

    # ---------- DELETE ----------

    def delete(self, entity: ModelT) -> None:
        """Supprime un enregistrement."""
        self.session.delete(entity)
        self.session.commit()
