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

    def create(self, *, commit: bool = True, **fields) -> ModelT:
        """
        Crée et persiste un nouvel enregistrement.
        commit=False permet d'orchestrer une transaction globale au niveau service.
        """
        entity = self.model(**fields)
        self.session.add(entity)
        if commit:
            self.session.commit()
            self.session.refresh(entity)
        else:
            # flush pour obtenir l'ID sans commit (utile pour FKs)
            self.session.flush()
        return entity

    # ---------- UPDATE ----------

    def update(self, entity: ModelT, *, commit: bool = True, **changes) -> ModelT:
        """
        Met à jour un enregistrement existant.
        commit=False permet d'orchestrer une transaction globale au niveau service.
        """
        for key, value in changes.items():
            setattr(entity, key, value)
        self.session.add(entity)
        if commit:
            self.session.commit()
            self.session.refresh(entity)
        else:
            self.session.flush()
        return entity

    # ---------- DELETE ----------

    def delete(self, entity: ModelT, *, commit: bool = True) -> None:
        """
        Supprime un enregistrement.
        commit=False permet d'orchestrer une transaction globale au niveau service.
        """
        self.session.delete(entity)
        if commit:
            self.session.commit()
        else:
            self.session.flush()
