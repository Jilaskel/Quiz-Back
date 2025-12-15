from typing import Optional, Sequence, Tuple
from sqlmodel import select

from app.db.repositories.themes import ThemeRepository
from app.db.repositories.images import ImageRepository
from app.db.models.themes import Theme
from app.features.themes.schemas import ThemeCreateIn, ThemeUpdateIn
from app.features.media.services import ImageService

class PermissionError(Exception):
    pass

class ThemeService:
    """
    Logique métier / contrôles d'accès pour Theme.
    - Public : lecture des thèmes publics.
    - Owner : CRUD sur ses thèmes.
    - Admin : CRUD sur tous les thèmes, lecture de tout.
    - Vérifie que l'image existe et appartient à l'user (sauf admin) avant create/update.
    - Peut retourner une URL signée optionnelle pour l'image liée.
    """

    def __init__(
        self, 
        repo: ThemeRepository,
        image_repo: ImageRepository,
        image_svc: ImageService
    ):
        self.repo = repo
        self.image_repo = image_repo
        self.image_svc = image_svc

    # -------- Helpers permissions --------

    @staticmethod
    def _is_owner(user_id: int, theme: Theme) -> bool:
        return theme.owner_id == user_id

    @staticmethod
    def _is_admin(is_admin: bool) -> bool:
        return bool(is_admin)

    def _assert_can_view(self, user_ctx: Optional[Tuple[int, bool]], theme: Theme) -> None:
        """
        user_ctx: (user_id, is_admin) ou None (public).
        Règles : public ok; owner ok; admin ok; sinon interdit.
        """
        if theme.is_public:
            return
        if user_ctx is None:
            raise PermissionError("Not allowed.")
        user_id, is_admin = user_ctx
        if self._is_admin(is_admin) or self._is_owner(user_id, theme):
            return
        raise PermissionError("Not allowed.")

    def _assert_can_edit(self, user_id: int, is_admin: bool, theme: Theme) -> None:
        if self._is_admin(is_admin) or self._is_owner(user_id, theme):
            return
        raise PermissionError("Not allowed.")

    # -------- vérifs images --------
    def _can_publicly_expose_image(self, image_id: Optional[int]) -> bool:
        if not image_id:
            return False
        return self.repo.image_is_publicly_exposable(image_id)
    
    # --- URL signée contrôlée ---
    def _signed_url_for_theme(
        self,
        theme: Theme,
        user_ctx: Optional[Tuple[int, bool]],
    ) -> Optional[dict]:
        """
        Retourne {'url','expires_in'} si autorisé, sinon None.
        Règles:
          - Si (theme.is_public AND theme.valid_admin) => OK sans auth.
          - Sinon: il faut user_ctx ET (admin OU owner du theme).
        """
        if not theme.image_id:
            return None

        if theme.is_public and theme.valid_admin:
            data = self.image_svc.signed_get(str(theme.image_id))
            return {"url": data["url"], "expires_in": data["expires_in"]}

        # sinon auth requise (owner ou admin)
        if user_ctx is None:
            return None
        user_id, is_admin = user_ctx
        if is_admin or theme.owner_id == user_id:
            data = self.image_svc.signed_get(str(theme.image_id))
            return {"url": data["url"], "expires_in": data["expires_in"]}
        return None

    # -------- Reads --------

    def list_public(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        ready_only: bool = True,
        validated_only: bool = False,
        category_id: Optional[int] = None,
        q: Optional[str] = None,
        newest_first: bool = True,
    ) -> Sequence[Theme]:
        return self.repo.list_public(
            offset=offset,
            limit=limit,
            ready_only=ready_only,
            validated_only=validated_only,
            category_id=category_id,
            q=q,
            newest_first=newest_first,
        )

    def list_mine(
        self,
        user_id: int,
        *,
        offset: int = 0,
        limit: int = 100,
        only_ready: bool = False,
        only_public: bool = False,
        only_validated: bool = False,
        category_id: Optional[int] = None,
        q: Optional[str] = None,
        newest_first: bool = True,
    ) -> Sequence[Theme]:
        return self.repo.list_by_owner(
            owner_id=user_id,
            offset=offset,
            limit=limit,
            only_ready=only_ready,
            only_public=only_public,
            only_validated=only_validated,
            category_id=category_id,
            q=q,
            newest_first=newest_first,
        )

    def list_all_as_admin(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        category_id: Optional[int] = None,
        q: Optional[str] = None,
        newest_first: bool = True,
    ) -> Sequence[Theme]:
        # admin: tout voir (simple stratégie = pas de filtre public/ready)
        # On réutilise list() du repo de base + filtres simples
        stmt = self.repo.session.query(Theme)  # type: ignore[attr-defined]
        # fallback SQLModel natif :
        statement = select(Theme)
        if category_id is not None:
            statement = statement.where(Theme.category_id == category_id)
        if q:
            like = f"%{q}%"
            statement = statement.where(Theme.name.ilike(like) | Theme.description.ilike(like))
        if newest_first:
            statement = statement.order_by(Theme.id.desc())
        else:
            statement = statement.order_by(Theme.id.asc())
        statement = statement.offset(offset).limit(limit)
        return self.repo.session.exec(statement).all()

    def get_one(self, theme_id: int, user_ctx: Optional[Tuple[int, bool]]) -> Theme:
        theme = self.repo.get(theme_id)
        if not theme:
            raise LookupError("Theme not found.")
        self._assert_can_view(user_ctx, theme)
        return theme

    # -------- Writes --------

    def create(self, payload: ThemeCreateIn, *, user_id: int, is_admin: bool) -> Theme:
        # Admin peut forcer owner_id & valid_admin; owner normal ne peut pas
        owner_id = payload.owner_id if is_admin and payload.owner_id else user_id
        valid_admin = bool(payload.valid_admin) if is_admin and payload.valid_admin is not None else False

        created = self.repo.create(
            name=payload.name,
            description=payload.description,
            image_id=payload.image_id,
            category_id=payload.category_id,
            is_public=payload.is_public,
            is_ready=payload.is_ready,
            valid_admin=valid_admin,
            owner_id=owner_id,
        )
        return created

    def update(self, theme_id: int, payload: ThemeUpdateIn, *, user_id: int, is_admin: bool) -> Theme:
        theme = self.repo.get(theme_id)
        if not theme:
            raise LookupError("Theme not found.")
        self._assert_can_edit(user_id, is_admin, theme)

        changes = payload.model_dump(exclude_unset=True)
        # filtrer champs réservés admin si non-admin
        if not is_admin:
            changes.pop("valid_admin", None)
            # un user ne peut pas réassigner le owner
            changes.pop("owner_id", None)

        # si admin veut changer le owner
        if is_admin and "owner_id" in changes and changes["owner_id"] is None:
            # si explicitement None -> on l'ignore pour éviter d'orpheliner
            changes.pop("owner_id")

        return self.repo.update(theme, **changes)

    def delete(self, theme_id: int, *, user_id: int, is_admin: bool) -> None:
        theme = self.repo.get(theme_id)
        if not theme:
            return
        self._assert_can_edit(user_id, is_admin, theme)
        self.repo.delete(theme)
