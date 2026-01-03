from typing import Any, Dict, List, Optional, Tuple, DefaultDict, Iterable
from collections import defaultdict
from sqlmodel import Session

import secrets
import string
import random
from collections import Counter

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
from app.db.repositories.questions import QuestionRepository

from app.features.games.schemas import GameCreateIn, RoundCreateIn, AnswerCreateIn, JokerUseIn, GameSetupSuggestIn, GameSetupSuggestOut

from app.core.config import settings

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
        question_repo: QuestionRepository,
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

        self.questions = question_repo
        self.QUESTIONS_PAGE_SIZE = 500

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
    
    # -----------------------------------
    # Helpers: question selection for new games
    # -----------------------------------
    def _load_all_question_ids_for_theme(self, theme_id: int) -> List[int]:
        """Charge tous les IDs de questions pour un thème via pagination."""
        ids: List[int] = []
        offset = 0
        while True:
            batch = self.questions.list_by_theme(
                theme_id,
                offset=offset,
                limit=self.QUESTIONS_PAGE_SIZE,
                newest_first=False,  # stable
            )
            if not batch:
                break
            ids.extend([q.id for q in batch])
            offset += len(batch)
            if len(batch) < self.QUESTIONS_PAGE_SIZE:
                break
        return ids

    # ---------------------------------------------------------------------
    # Catalogues jokers / bonus
    # ---------------------------------------------------------------------

    def list_all_jokers(self) -> List[Dict[str, Any]]:
        rows = self.jokers.list_name_description()
        return [{"id": r[0], "name": r[1], "description": r[2], "requires_target_player": r[3], "requires_target_grid": r[4]} for r in rows]

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
        # Fixed random
        rng = random.Random(payload.seed)

        # 1) génère une url unique avec retry
        url = self._generate_game_url()
        tries = 0
        while self.games.get_by_url(url):
            tries += 1
            if tries >= 10:
                raise ConflictError("GAME_URL_GENERATION_FAILED")
            url = self._generate_game_url()

        # thèmes joueurs uniques
        theme_ids = [p.theme_id for p in payload.players]
        if len(theme_ids) != len(set(theme_ids)):
            raise ConflictError("DUPLICATE_PLAYER_THEMES_NOT_ALLOWED")
    
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
        players_payload = list(payload.players)
        rng.shuffle(players_payload)

        created_players = []
        for idx, p in enumerate(players_payload, start=1):
            created_players.append(
                self.players.create(
                    commit=False,
                    game_id=game.id,
                    color_id=p.color_id,
                    theme_id=p.theme_id,
                    name=p.name,
                    order=idx,
                )
            )

        # Attach jokers/bonus (optionnel)
        if payload.joker_ids:
            for jid in payload.joker_ids:
                # unique constraint côté DB (joker_id, game_id)
                self.jokers_in_game.create(commit=False, joker_id=jid, game_id=game.id)

        if payload.bonus_ids:
            for bid in payload.bonus_ids:
                self.bonus_in_game.create(commit=False, bonus_id=bid, game_id=game.id)

        # init grille (cells + question_id) selon seed
        rows = payload.rows_number
        cols = payload.columns_number
        grid_size = rows * cols

        nb_players = len(payload.players)
        player_q_total = nb_players * payload.number_of_questions_by_player
        general_q_total = grid_size - player_q_total
        if general_q_total < 0:
            raise ConflictError("GRID_TOO_SMALL_FOR_REQUESTED_PLAYER_QUESTIONS")

        if not payload.general_theme_ids:
            raise ConflictError("GENERAL_THEMES_REQUIRED")


        player_theme_ids = [p.theme_id for p in created_players]
        general_theme_ids = list(payload.general_theme_ids)

        # Interdire qu'un thème joueur soit aussi culture G :
        general_theme_ids = [tid for tid in general_theme_ids if tid not in set(player_theme_ids)]
        if not general_theme_ids: raise ConflictError("GENERAL_THEMES_REQUIRED")

        theme_ids_needed = sorted(set(player_theme_ids) | set(general_theme_ids))

        # 1) pool d'IDs par thème
        pool: Dict[int, List[int]] = {}
        for tid in theme_ids_needed:
            qids = self._load_all_question_ids_for_theme(tid)
            rng.shuffle(qids)  # déterministe
            pool[tid] = qids

        # 2) tirer questions joueurs
        player_selected_qids: List[int] = []
        for tid in player_theme_ids:
            need = payload.number_of_questions_by_player
            if len(pool.get(tid, [])) < need:
                raise ConflictError("NOT_ENOUGH_QUESTIONS_FOR_PLAYER_THEME")
            for _ in range(need):
                player_selected_qids.append(pool[tid].pop())

        # 3) tirer questions culture G (répartition random sur themes)
        general_selected_qids: List[int] = []
        for _ in range(general_q_total):
            tid = rng.choice(general_theme_ids)
            if not pool.get(tid):
                # fallback: prendre un autre thème non vide
                non_empty = [x for x in general_theme_ids if pool.get(x)]
                if not non_empty:
                    raise ConflictError("NOT_ENOUGH_QUESTIONS_FOR_GENERAL_THEMES")
                tid = rng.choice(non_empty)
            general_selected_qids.append(pool[tid].pop())

        # 4) placement
        coords = [(r, c) for r in range(rows) for c in range(cols)]
        rng.shuffle(coords)

        # Mélange des questions pour éviter "bloc joueur puis bloc culture G"
        all_qids = player_selected_qids + general_selected_qids
        rng.shuffle(all_qids)

        if len(all_qids) != grid_size:
            raise ConflictError("GRID_FILL_COUNT_MISMATCH")

        grids_to_create = []
        for (r, c), qid in zip(coords, all_qids):
            grids_to_create.append(
                self.grids.create(
                    commit=False,
                    game_id=game.id,
                    round_id=None,
                    question_id=qid,
                    correct_answer=False,
                    skip_answer=False,
                    row=r,
                    column=c,
                )
            )

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

        # ✅ Mapping round_id -> player_id (pour savoir qui a répondu)
        rounds_flat = self.rounds.list_by_game(game.id)
        round_to_player_id: Dict[int, int] = {r.round_id: r.player_id for r in rounds_flat}

        # 1) grille complète : cases + question(theme+points)
        grid_rows = self.grids.list_grid_questions_with_theme_and_points(game.id)
        grid = [
            {
                "grid_id": r.grid_id,
                "row": r.row,
                "column": r.column,
                "round_id": r.round_id,
                "player_id": round_to_player_id.get(r.round_id) if r.round_id else None,
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
        all_jig = self.jokers_in_game.list_for_game(game.id)  # jokers au niveau partie
        used_by_player = self.jokers_used.list_used_joker_in_game_ids_grouped_by_player_for_game(game.id)

        available_jokers: Dict[int, List[Dict[str, Any]]] = {}
        for p in players:
            used_set = used_by_player.get(p.id, set())

            available_jokers[p.id] = [
                {
                    "joker_in_game_id": r.joker_in_game_id,
                    "joker": {
                        "id": r.joker_id,
                        "name": r.name,
                        "description": r.description,
                        "requires_target_player": bool(r.requires_target_player),
                        "requires_target_grid": bool(r.requires_target_grid),
                    },
                    "available": (r.joker_in_game_id not in used_set),
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
                "owner_id": game.owner_id
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
        Base :
        - skip => 0 et aucun effet joker
        - incorrect => 0 (règle actuelle)
        - correct :
            - propre thème : +points
            - thème adverse : joueur +points, owner -points

        Jokers :
        - x2 : double l'impact de la question jouée sur le round où il est joué (si correct)
        - all_in : sur cette question :
            - correct : tous les adversaires perdent points
            - incorrect : le joueur perd points
        - flash : aucun impact score
        - gamble : cible une case -> s'applique quand cette case est résolue (non skip)
            - correct : le parieur gagne points
            - incorrect : le parieur perd points
        - appel à un ami : sur cette question, si incorrect -> target perd points
        """
        JOKER_X2 = "x2"
        JOKER_ALL_IN = "All-In"
        JOKER_FLASH = "Flash"
        JOKER_GAMBLE = "Gamble"
        JOKER_APPEL = "Appel à un ami"

        scores: Dict[int, int] = {p.id: 0 for p in players}
        player_theme: Dict[int, int] = {p.id: p.theme_id for p in players}
        theme_owner: Dict[int, int] = {p.theme_id: p.id for p in players}
        all_player_ids = [p.id for p in players]

        answered = self.grids.list_answered_cells_for_scoring(game_id)

        rounds_flat = self.rounds.list_by_game(game_id)
        round_to_player: Dict[int, int] = {r.round_id: r.player_id for r in rounds_flat}

        # jokers used enrichis (round_id, using_player_id, joker_name, targets...)
        used_rows = self.jokers_used.list_used_for_game_for_scoring(game_id)

        jokers_by_round: DefaultDict[int, List[Any]] = defaultdict(list)
        gambles_by_grid: DefaultDict[int, List[Any]] = defaultdict(list)

        for u in used_rows:
            jokers_by_round[u.round_id].append(u)
            if u.joker_name == JOKER_GAMBLE and u.target_grid_id:
                gambles_by_grid[u.target_grid_id].append(u)

        def owner_of_theme(theme_id: int) -> Optional[int]:
            return theme_owner.get(theme_id)

        def iter_round_jokers(round_id: int, using_player_id: int, joker_name: str) -> Iterable[Any]:
            for u in jokers_by_round.get(round_id, []):
                if u.using_player_id == using_player_id and u.joker_name == joker_name:
                    yield u

        def has_round_joker(round_id: int, using_player_id: int, joker_name: str) -> bool:
            return any(True for _ in iter_round_jokers(round_id, using_player_id, joker_name))

        # ------------------------------------------------------------------
        # Joker functions (1 fonction / joker)
        # ------------------------------------------------------------------

        def _apply_x2(
            *,
            round_id: int,
            answering_player_id: int,
            is_correct: bool,
            points: int,
            question_theme_id: int,
            owner_penalty_blocked: bool,
        ) -> None:
            if not is_correct:
                return
            if not has_round_joker(round_id, answering_player_id, JOKER_X2):
                return

            # "double l'impact" => on ajoute un delta identique au delta normal
            scores[answering_player_id] += points

            # si thème adverse => owner perd aussi les points doublés
            if player_theme.get(answering_player_id) != question_theme_id:
                owner_id = owner_of_theme(question_theme_id)
                if owner_id and not owner_penalty_blocked:
                    scores[owner_id] -= points


        def _apply_all_in(
            *,
            round_id: int,
            answering_player_id: int,
            is_correct: bool,
            points: int,
        ) -> None:
            if not has_round_joker(round_id, answering_player_id, JOKER_ALL_IN):
                return

            if is_correct:
                for pid in all_player_ids:
                    if pid != answering_player_id:
                        scores[pid] -= points
            else:
                scores[answering_player_id] -= points

        def _apply_flash(*, round_id: int, answering_player_id: int) -> None:
            # Pas d'impact score
            _ = round_id
            _ = answering_player_id
            return

        def _apply_appel_a_un_ami(
            *,
            round_id: int,
            answering_player_id: int,
            is_correct: bool,
            points: int,
        ) -> None:
            for u in iter_round_jokers(round_id, answering_player_id, JOKER_APPEL):
                if not u.target_player_id:
                    continue

                if is_correct:
                    # règle (1) : correct => les deux gagnent
                    scores[u.target_player_id] += points
                else:
                    # règle (1) : incorrect => l'ami perd
                    scores[u.target_player_id] -= points

        def _apply_gamble(
            *,
            grid_id: int,
            is_correct: bool,
            points: int,
            answering_player_id: int,
        ) -> None:
            for u in gambles_by_grid.get(grid_id, []):
                gambler_id = u.using_player_id

                # ✅ Si le parieur répond lui-même à la question, pas d'effet Gamble
                if gambler_id == answering_player_id:
                    continue

                if is_correct:
                    scores[gambler_id] += points
                else:
                    scores[gambler_id] -= points


        # ------------------------------------------------------------------
        # Main loop
        # ------------------------------------------------------------------

        for cell in answered:
            # Skip => aucun effet (score + jokers)
            if bool(cell.skip_answer):
                continue

            round_id = cell.round_id
            if round_id is None or round_id <= 0:
                continue

            answering_player_id = round_to_player.get(round_id)
            if not answering_player_id:
                continue

            points = int(cell.question_points or 0)
            question_theme_id = cell.question_theme_id

            # ami(s) appelé(s) sur ce round (souvent 0 ou 1)
            called_player_ids = [
                u.target_player_id
                for u in iter_round_jokers(round_id, answering_player_id, JOKER_APPEL)
                if u.target_player_id
            ]

            # si la question est d'un thème adverse, l'owner qui devrait perdre des points
            # MAIS si cet owner est appelé, on annule cette pénalité
            owner_id = owner_of_theme(question_theme_id)
            owner_penalty_blocked = (owner_id is not None and owner_id in called_player_ids)

            is_correct = bool(cell.correct_answer)

            # 1) scoring normal
            if is_correct:
                if player_theme.get(answering_player_id) == question_theme_id:
                    scores[answering_player_id] += points
                else:
                    scores[answering_player_id] += points
                    if owner_id and not owner_penalty_blocked:
                        scores[owner_id] -= points
            else:
                # incorrect => 0 (règle actuelle)
                pass

            # 2) apply jokers (round-based)
            _apply_x2(
                round_id=round_id,
                answering_player_id=answering_player_id,
                is_correct=is_correct,
                points=points,
                question_theme_id=question_theme_id,
                owner_penalty_blocked=owner_penalty_blocked,
            )
            _apply_all_in(
                round_id=round_id,
                answering_player_id=answering_player_id,
                is_correct=is_correct,
                points=points,
            )
            _apply_flash(round_id=round_id, answering_player_id=answering_player_id)
            _apply_appel_a_un_ami(
                round_id=round_id,
                answering_player_id=answering_player_id,
                is_correct=is_correct,
                points=points,
            )

            # 3) gamble (grid-based)
            _apply_gamble(
                grid_id=cell.id,
                is_correct=is_correct,
                points=points,
                answering_player_id=answering_player_id,
            )


        return scores
    
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

        player_id = round_ctx.player_id

        used_before = set(
            self.jokers_used.list_used_joker_in_game_ids_for_player_before_round(
                game.id, player_id, payload.round_id
            )
        )
        if payload.joker_in_game_id in used_before:
            raise ConflictError("Joker already used by this player")

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
    
    # ---------------------------------------------------------------------
    # Suggestion de setup
    # ---------------------------------------------------------------------
    def suggest_setup(self, payload: GameSetupSuggestIn) -> GameSetupSuggestOut:
        theme_ids = [p.theme_id for p in payload.players]

        counts = Counter(theme_ids)
        duplicates = [tid for tid, c in counts.items() if c > 1]
        if duplicates:
            # tu peux aussi inclure duplicates dans le detail si tu veux
            raise ConflictError("DUPLICATE_PLAYER_THEMES_NOT_ALLOWED")

        # 1) compter questions dispo par thème joueur
        counts = [self.questions.count_by_theme(tid) for tid in theme_ids]

        # cas extrêmes
        if not counts:
            raise ConflictError("NO_PLAYERS")

        min_available = min(counts)
        if min_available <= 0:
            # pas jouable : au moins un thème n'a aucune question
            raise ConflictError("THEME_HAS_NO_QUESTIONS")

        # 2) conseillé = min_available capé à 10
        n_by_player = min(min_available, 10)

        # 3) taille de grille minimale
        needed_cells = len(theme_ids) * n_by_player

        # 4) choisir la plus petite grille autorisée qui fit
        chosen: Tuple[int, int] | None = None
        for (r, c) in settings.ALLOWED_GRIDS:
            if r * c >= needed_cells:
                chosen = (r, c)
                break

        if chosen is None:
            raise ConflictError("NO_ALLOWED_GRID_CAN_FIT_REQUEST")

        rows, cols = chosen

        return GameSetupSuggestOut(
            number_of_questions_by_player=n_by_player,
            rows_number=rows,
            columns_number=cols,
            general_theme_ids=settings.GENERAL_THEME_IDS,
            joker_ids=settings.DEFAULT_JOKER_IDS,
            bonus_ids=settings.DEFAULT_BONUS_IDS,
        )