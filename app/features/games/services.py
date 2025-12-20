from typing import Any, Dict, List, Optional, Tuple
from sqlmodel import Session

import secrets
import string

from app.db.repositories.games import GameRepository
from app.db.repositories.players import PlayerRepository
from app.db.repositories.rounds import RoundRepository
from app.db.repositories.grids import GridRepository
from app.db.repositories.jokers import JokerRepository
from app.db.repositories.bonus import BonusRepository
from app.db.repositories.jokers_in_games import JokerInGameRepository
from app.db.repositories.jokers_used_in_games import JokerUsedInGameRepository
from app.db.repositories.bonus_in_games import BonusInGameRepository
from app.db.repositories.colors import ColorRepository

from app.features.games.schemas import GameCreateIn, RoundCreateIn, AnswerCreateIn, JokerUseIn

class PermissionError(Exception):
    """Accès interdit (owner/admin)."""
    pass

class ConflictError(Exception):
    """Conflit métier (url déjà prise, case déjà répondue, joker déjà utilisé...)."""
    pass

class GameService:
    """
    Service métier Game : orchestre repos + règles.

    Conçu pour matcher les routes proposées :
    - state par game_url
    - use_joker séparé de answer_question
    - auto_next_round possible après answer_question
    """
    def __init__(
        self,
        session: Session,
        game_repo: GameRepository,
        player_repo: PlayerRepository,
        round_repo: RoundRepository,
        grid_repo: GridRepository,
        joker_repo: JokerRepository,
        joker_in_game_repo: JokerInGameRepository,
        joker_used_repo: JokerUsedInGameRepository,
        bonus_repo: BonusRepository,
        bonus_in_game_repo: BonusInGameRepository,
        color_repo: ColorRepository,
    ):
        self.session = session

        self.games = game_repo
        self.players = player_repo
        self.rounds = round_repo
        self.grids = grid_repo

        self.jokers = joker_repo
        self.jokers_in_game = joker_in_game_repo
        self.jokers_used = joker_used_repo

        self.bonus = bonus_repo
        self.bonus_in_game = bonus_in_game_repo

        self.colors = color_repo

    # -----------------------------------
    # Helpers: auth & ownership
    # -----------------------------------
    def _get_game_or_404(self, game_url: str):
        game = self.games.get_by_url(game_url)
        if not game:
            raise LookupError("GAME_NOT_FOUND")
        return game

    def _ensure_owner_or_admin(self, game, *, user_id: int, is_admin: bool) -> None:
        if (game.owner_id != user_id) and (not is_admin):
            raise PermissionError("FORBIDDEN")

    # -----------------------------------
    # Helpers: url games
    # -----------------------------------
    def _generate_game_url(self) -> str:
        """
        Génère une url/slug courte, safe pour URL.
        Exemple: g-8f3k1p9z
        """
        alphabet = string.ascii_lowercase + string.digits
        token = "".join(secrets.choice(alphabet) for _ in range(8))
        return f"g-{token}"

    # ---------------------------------------------------------------------
    # Catalogues jokers / bonus
    # ---------------------------------------------------------------------

    def list_all_jokers(self) -> List[Dict[str, Any]]:
        rows = self.jokers.list_name_description()
        return [{"id": r[0], "name": r[1], "description": r[2]} for r in rows]

    def list_all_bonus(self) -> List[Dict[str, Any]]:
        rows = self.bonus.list_name_description()
        return [{"id": r[0], "name": r[1], "description": r[2]} for r in rows]

    # ---------------------------------------------------------------------
    # Parties d'un user + joueurs + couleur(hex) + thème
    # ---------------------------------------------------------------------

    def list_user_games_with_players(self, owner_id: int) -> List[Dict[str, Any]]:
        flat = self.games.list_by_owner_with_players_color_theme(owner_id)

        # Remap plat -> hiérarchie
        by_game: Dict[int, Dict[str, Any]] = {}
        for r in flat:
            gid = r.game_id
            if gid not in by_game:
                by_game[gid] = {
                    "id": gid,
                    "url": r.game_url,
                    "seed": r.seed,
                    "rows_number": r.rows_number,
                    "columns_number": r.columns_number,
                    "finished": r.finished,
                    "players": [],
                }

            # si partie sans players encore
            if r.player_id is not None:
                by_game[gid]["players"].append(
                    {
                        "id": r.player_id,
                        "name": r.player_name,
                        "order": r.player_order,
                        "color": {"id": r.color_id, "hex_code": r.color_hex_code},
                        "theme": {"id": r.theme_id, "name": r.theme_name},
                    }
                )

        return list(by_game.values())

    # ---------------------------------------------------------------------
    # Create game
    # ---------------------------------------------------------------------

    def create_game(self, payload: GameCreateIn, *, owner_id: int) -> Any:
        # 1) génère une url unique avec retry
        url = self._generate_game_url()
        tries = 0
        while self.games.get_by_url(url):
            tries += 1
            if tries >= 10:
                raise ConflictError("GAME_URL_GENERATION_FAILED")
            url = self._generate_game_url()

        # Transaction globale
        game = self.games.create(
            commit=False,
            owner_id=owner_id,
            seed=payload.seed,
            url=url,
            rows_number=payload.rows_number,
            columns_number=payload.columns_number,
            finished=False,
        )

        # Players
        for p in payload.players:
            self.players.create(
                commit=False,
                game_id=game.id,
                color_id=p.color_id,
                theme_id=p.theme_id,
                name=p.name,
                order=p.order,
            )

        # Attach jokers/bonus (optionnel)
        if payload.joker_ids:
            for jid in payload.joker_ids:
                # unique constraint côté DB (joker_id, game_id)
                self.jokers_in_game.create(commit=False, joker_id=jid, game_id=game.id)

        if payload.bonus_ids:
            for bid in payload.bonus_ids:
                self.bonus_in_game.create(commit=False, bonus_id=bid, game_id=game.id)

        # TODO: init grille (cells + question_id) selon seed
        # -> volontairement laissé hors-scope ici

        # 6) créer le first round (round_number=1) pour le premier joueur
        first_player = self.players.get_next_player_in_game(game.id, current_order=0)
        if not first_player:
            raise ConflictError("GAME_HAS_NO_PLAYERS")

        first_round = self.rounds.create(
            commit=False,          # important: même transaction
            player_id=first_player.id,
            round_number=1,
        )

        self.session.commit()
        self.session.refresh(game)
        return game
    
    # ---------------------------------------------------------------------
    # Etat d'une partie
    # ---------------------------------------------------------------------

    def get_game_state(self, game_url: str, *, user_id: int, is_admin: bool) -> Dict[str, Any]:
        game = self._get_game_or_404(game_url)
        self._ensure_owner_or_admin(game, user_id=user_id, is_admin=is_admin)

        players = self.players.list_by_game(game.id)

        # 1) grille complète : cases + question(theme+points)
        grid_rows = self.grids.list_grid_questions_with_theme_and_points(game.id)
        grid = [
            {
                "grid_id": r.grid_id,
                "row": r.row,
                "column": r.column,
                "round_id": r.round_id,
                "correct_answer": r.correct_answer,
                "skip_answer": r.skip_answer,
                "question": {
                    "id": r.question_id,
                    "theme": {"id": r.question_theme_id, "name": r.question_theme_name},
                    "points": int(r.question_points or 0),
                },
            }
            for r in grid_rows
        ]

        # 2) dernier round à jouer (= dernier round ajouté à rounds pas encore dans la grille)
        last_pending_round = self.rounds.get_last_round_not_in_grid(game.id)

        current_turn = None
        if last_pending_round:
            current_turn = {
                "round_id": last_pending_round.round_id,
                "round_number": last_pending_round.round_number,
                "player": {
                    "id": last_pending_round.player_id,
                    "name": last_pending_round.player_name,
                    "order": last_pending_round.player_order,
                    "theme_id": last_pending_round.player_theme_id,
                },
            }

        # 3) jokers dispo pour le joueur du tour (disponible = pas utilisé avant ce round)
        available_jokers: List[Dict[str, Any]] = []
        if current_turn:
            all_jig = self.jokers_in_game.list_for_game(game.id)
            used_before = set(
                self.jokers_used.list_used_joker_in_game_ids_for_game_before_round(
                    game.id, current_turn["round_id"]
                )
            )
            available_jokers = [
                {
                    "joker_in_game_id": r.joker_in_game_id,
                    "joker": {"id": r.joker_id, "name": r.name, "description": r.description},
                    "available": (r.joker_in_game_id not in used_before),
                }
                for r in all_jig
            ]

        # 4) scores
        scores = self._compute_scores(game_id=game.id, players=players)

        # 5) bonus attachés au game
        bonus = [
            {
                "bonus_in_game_id": r.bonus_in_game_id,
                "bonus": {"id": r.bonus_id, "name": r.name, "description": r.description},
            }
            for r in self.bonus_in_game.list_for_game(game.id)
        ]

        return {
            "game": {
                "id": game.id,
                "url": game.url,
                "seed": game.seed,
                "rows_number": game.rows_number,
                "columns_number": game.columns_number,
                "finished": game.finished,
            },
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "order": p.order,
                    "theme_id": p.theme_id,
                    "color_id": p.color_id,
                }
                for p in players
            ],
            "grid": grid,
            "current_turn": current_turn,
            "available_jokers": available_jokers,
            "bonus": bonus,
            "scores": scores,
        }

    # ---------------------------------------------------------------------
    # Scoring
    # ---------------------------------------------------------------------

    def _compute_scores(self, game_id: int, players) -> Dict[int, int]:
        """
        Règle demandée :
        - On parcourt les questions déjà répondues (grid.round_id > 0)
        - Si skip -> 0
        - Si incorrect -> 0 (pour l’instant)
        - Si correct :
            - si le joueur répond à son propre thème : +points
            - si le joueur répond au thème d’un autre :
                - le joueur gagne +points
                - le joueur propriétaire du thème perd -points
        + Placeholders pour jokers.
        """
        scores: Dict[int, int] = {p.id: 0 for p in players}
        player_theme: Dict[int, int] = {p.id: p.theme_id for p in players}
        theme_owner: Dict[int, int] = {p.theme_id: p.id for p in players}

        answered = self.grids.list_answered_cells_for_scoring(game_id)

        # On a besoin de round_id -> player_id pour savoir qui a joué
        # (requête “pure” déjà possible, mais simple de la refaire en repo plus tard si besoin)
        rounds_flat = self.rounds.list_by_game(game_id)
        round_to_player: Dict[int, int] = {r.round_id: r.player_id for r in rounds_flat}

        for cell in answered:
            round_id = cell.round_id
            if round_id is None or round_id <= 0:
                continue

            player_id = round_to_player.get(round_id)
            if not player_id:
                continue

             # skip / incorrect => 0 (pour l’instant)
            if cell.skip_answer or (not cell.correct_answer):
                self._apply_joker_effects_on_scoring_placeholder(
                    game_id=game_id,
                    round_id=round_id,
                    player_id=player_id,
                    question_theme_id=cell.question_theme_id,
                    base_points=0,
                    is_correct=cell.correct_answer,
                    is_skip=cell.skip_answer,
                    scores=scores,
                )
                continue

            points = int(cell.question_points or 0)
            question_theme_id = cell.question_theme_id

            if player_theme.get(player_id) == question_theme_id:
                # répond à son propre thème
                scores[player_id] += points
            else:
                # répond à un autre thème
                scores[player_id] += points
                owner_id = theme_owner.get(question_theme_id)
                if owner_id:
                    scores[owner_id] -= points

            # Placeholder: jokers/bonus peuvent impacter le scoring
            self._apply_joker_effects_on_scoring_placeholder(
                game_id=game_id,
                round_id=round_id,
                player_id=player_id,
                question_theme_id=question_theme_id,
                base_points=points,
                is_correct=True,
                is_skip=False,
                scores=scores,
            )

        return scores

    def _apply_joker_effects_on_scoring_placeholder(
        self,
        *,
        game_id: int,
        round_id: int,
        player_id: int,
        question_theme_id: int,
        base_points: int,
        is_correct: bool,
        is_skip: bool,
        scores: Dict[int, int],
    ) -> None:
        """
        Placeholder : à implémenter.
        Exemple : double points, annuler perte de points, voler points, etc.
        Tu peux ici charger les jokers utilisés sur ce round et modifier `scores`.
        """
        return
    
    # ---------------------------------------------------------------------
    # Joker usage (process séparé)
    # ---------------------------------------------------------------------

    def use_joker(self, game_url: str, payload: JokerUseIn, *, user_id: int, is_admin: bool) -> Any:
        game = self._get_game_or_404(game_url)
        self._ensure_owner_or_admin(game, user_id=user_id, is_admin=is_admin)

        # JokerInGame doit appartenir à la partie
        jig = self.jokers_in_game.get(payload.joker_in_game_id)
        if not jig or jig.game_id != game.id:
            raise LookupError("JOKER_IN_GAME_NOT_FOUND")

        # Vérifier round appartient à la partie
        round_ctx = self.rounds.get_round_context(payload.round_id)
        if not round_ctx:
            raise LookupError("ROUND_NOT_FOUND")
        if round_ctx.game_id != game.id:
            raise LookupError("ROUND_NOT_IN_GAME")

        # dispo = pas utilisé avant ce round
        used_before = set(
            self.jokers_used.list_used_joker_in_game_ids_for_game_before_round(game.id, payload.round_id)
        )
        if payload.joker_in_game_id in used_before:
            raise ConflictError("JOKER_ALREADY_USED")

        usage = self.jokers_used.create(
            commit=True,
            joker_in_game_id=payload.joker_in_game_id,
            round_id=payload.round_id,
            target_player_id=payload.target_player_id,
            target_grid_id=payload.target_grid_id,
        )

        # Placeholder effets immédiats
        self._apply_joker_effects_after_use_placeholder(game_id=game.id, usage_id=usage.id)
        return usage

    def _apply_joker_effects_after_use_placeholder(self, game_id: int, usage_id: int) -> None:
        # Ici tu implémenteras des jokers qui modifient l'état dès l'usage
        # (ex: révéler question, bloquer une case, etc.)
        return

    # ---------------------------------------------------------------------
    # Answer (process séparé) + auto-next-round
    # ---------------------------------------------------------------------

    def answer_question(
        self,
        game_url: str,
        payload: AnswerCreateIn,
        *,
        user_id: int,
        is_admin: bool,
        auto_next_round: bool = True,
    ) -> Tuple[Any, Optional[Any]]:
        game = self._get_game_or_404(game_url)
        self._ensure_owner_or_admin(game, user_id=user_id, is_admin=is_admin)

        grid = self.grids.get(payload.grid_id)
        if not grid or grid.game_id != game.id:
            raise LookupError("GRID_NOT_FOUND")

        # empêcher double réponse
        if grid.round_id is not None:
            raise ConflictError("GRID_ALREADY_ANSWERED")

        # Vérifier round appartient à la partie + récupérer contexte
        round_ctx = self.rounds.get_round_context(payload.round_id)
        if not round_ctx:
            raise LookupError("ROUND_NOT_FOUND")
        if round_ctx.game_id != game.id:
            raise LookupError("ROUND_NOT_IN_GAME")

        updated = self.grids.update(
            grid,
            commit=True,
            round_id=payload.round_id,
            correct_answer=payload.correct_answer,
            skip_answer=payload.skip_answer,
        )

        next_round = None
        if auto_next_round:
            next_round = self._maybe_create_next_round_after_answer(game_id=game.id, just_played_round_id=payload.round_id)

        return updated, next_round

    def _maybe_create_next_round_after_answer(self, *, game_id: int, just_played_round_id: int) -> Optional[Any]:
        """
        Crée un next round (round_number+1) pour le prochain joueur (ordre circulaire).
        - Dépend de l'ordre des players dans la partie.
        - Empêche création si déjà existant.
        """
        ctx = self.rounds.get_round_context(just_played_round_id)
        if not ctx or ctx.game_id != game_id:
            return None

        current_round_number = ctx.round_number
        current_player_order = ctx.player_order

        # joueur suivant (ordre circulaire)
        next_player = self.players.get_next_player_in_game(game_id, current_player_order)
        if not next_player:
            return None

        next_round_number = current_round_number + 1

        # éviter doublon (player_id, round_number)
        if self.rounds.exists_for_player_round_number(next_player.id, next_round_number):
            return None

        created = self.rounds.create(
            commit=True,
            player_id=next_player.id,
            round_number=next_round_number,
        )
        return created
    
    # ---------------------------------------------------------------------
    # Public: colors
    # ---------------------------------------------------------------------
    def list_public_colors(self, *, offset: int = 0, limit: int = 500) -> List[Dict[str, Any]]:
        rows = self.colors.list_public(offset=offset, limit=limit)
        return [{"id": r[0], "name": r[1], "hex_code": r[2]} for r in rows]