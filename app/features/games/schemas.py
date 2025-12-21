from typing import List, Optional, Dict
from pydantic import BaseModel, Field, model_validator


# -----------------------------
# Catalogues (Jokers / Bonus)
# -----------------------------

class JokerPublicOut(BaseModel):
    id: int
    name: str
    description: str


class BonusPublicOut(BaseModel):
    id: int
    name: str
    description: str


# -----------------------------
# Game creation
# -----------------------------

class PlayerCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    color_id: int = Field(ge=1)
    theme_id: int = Field(ge=1)


class GameCreateIn(BaseModel):
    seed: int
    rows_number: int = Field(ge=1, le=50)
    columns_number: int = Field(ge=1, le=50)

    players: List[PlayerCreateIn] = Field(min_length=1, max_length=20)
    number_of_questions_by_player: int = Field(ge=1, le=50)

    general_theme_ids: List[int] = Field(min_length=1)

    # optionnel : associer des jokers/bonus au setup
    joker_ids: Optional[List[int]] = None
    bonus_ids: Optional[List[int]] = None


class GameCreateOut(BaseModel):
    id: int
    url: str
    seed: int
    rows_number: int
    columns_number: int
    finished: bool


# -----------------------------
# "My games" list
# -----------------------------

class ColorOut(BaseModel):
    id: int
    hex_code: str


class ThemeOut(BaseModel):
    id: int
    name: str


class PlayerInGameOut(BaseModel):
    id: int
    name: str
    order: int
    color: ColorOut
    theme: ThemeOut


class GameWithPlayersOut(BaseModel):
    id: int
    url: str
    seed: int
    rows_number: int
    columns_number: int
    finished: bool
    players: List[PlayerInGameOut]


# -----------------------------
# Game state
# -----------------------------

class QuestionInGridOut(BaseModel):
    id: int
    points: int
    theme: ThemeOut


class GridCellOut(BaseModel):
    grid_id: int
    row: int
    column: int
    round_id: Optional[int] = None
    correct_answer: bool
    skip_answer: bool
    question: QuestionInGridOut


class CurrentTurnPlayerOut(BaseModel):
    id: int
    name: str
    order: int
    theme_id: int


class CurrentTurnOut(BaseModel):
    round_id: int
    round_number: int
    player: CurrentTurnPlayerOut


class JokerAvailabilityOut(BaseModel):
    joker_in_game_id: int
    joker: JokerPublicOut
    available: bool


class BonusInGameOut(BaseModel):
    bonus_in_game_id: int
    bonus: BonusPublicOut


class GameMetaOut(BaseModel):
    id: int
    url: str
    seed: int
    rows_number: int
    columns_number: int
    finished: bool
    owner_id: int


class GameStateOut(BaseModel):
    game: GameMetaOut
    players: List[Dict]  # volontairement “simple” (ou tu peux typer strict)
    grid: List[GridCellOut]
    current_turn: Optional[CurrentTurnOut] = None
    available_jokers: List[JokerAvailabilityOut] = []
    bonus: List[BonusInGameOut] = []
    scores: Dict[int, int]  # player_id -> points

# -----------------------------
# Rounds
# -----------------------------

class RoundCreateIn(BaseModel):
    player_id: Optional[int] = Field(default=None, ge=1)
    player_order: Optional[int] = Field(default=None, ge=1)
    round_number: int = Field(ge=1)


class RoundCreateOut(BaseModel):
    id: int
    player_id: int
    round_number: int


# -----------------------------
# Answers (sans jokers)
# -----------------------------

class AnswerCreateIn(BaseModel):
    """
    Enregistrer une réponse sur une case de grille.
    - round_id: le tour en cours
    - grid_id: la case ciblée
    """
    round_id: int = Field(ge=1)
    grid_id: int = Field(ge=1)
    correct_answer: bool = False
    skip_answer: bool = False


class AnswerCreateOut(BaseModel):
    grid_id: int
    round_id: int
    correct_answer: bool
    skip_answer: bool

    # si auto_next_round=true, on peut renvoyer le round créé
    next_round: Optional[RoundCreateOut] = None


# -----------------------------
# Joker usage (process séparé)
# -----------------------------

class JokerUseIn(BaseModel):
    """
    Utiliser un joker pendant un round.
    - joker_in_game_id: l’instance de joker attachée à la partie
    - round_id: le round pendant lequel on utilise le joker
    - targets: optionnels selon joker
    """
    joker_in_game_id: int = Field(ge=1)
    round_id: int = Field(ge=1)
    target_player_id: Optional[int] = Field(default=None, ge=1)
    target_grid_id: Optional[int] = Field(default=None, ge=1)


class JokerUseOut(BaseModel):
    id: int
    joker_in_game_id: int
    round_id: int
    target_player_id: Optional[int] = None
    target_grid_id: Optional[int] = None

class ColorPublicOut(BaseModel):
    id: int
    name: str
    hex_code: str

# -----------------------------
# Suggestion de setup
# -----------------------------
class PlayerSetupIn(BaseModel):
    theme_id: int

class GameSetupSuggestIn(BaseModel):
    players: List[PlayerSetupIn] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def themes_must_be_unique(self):
        theme_ids = [p.theme_id for p in self.players]
        if len(theme_ids) != len(set(theme_ids)):
            raise ValueError("Each player must have a unique theme_id")
        return self

class GameSetupSuggestOut(BaseModel):
    number_of_questions_by_player: int
    rows_number: int
    columns_number: int

    general_theme_ids: List[int]
    joker_ids: List[int]
    bonus_ids: List[int]