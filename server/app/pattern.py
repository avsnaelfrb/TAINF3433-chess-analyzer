"""Dataset filtering, 23-label encoding and split per GameId."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
from datasets import Dataset, load_dataset
from sklearn.model_selection import GroupShuffleSplit

# Fixed order: the label vector columns and the model output follow this tuple.
ATTACK_CLASSES: tuple[str, ...] = (
    "fork",
    "pin",
    "skewer",
    "discoveredAttack",
    "xRayAttack",
    "deflection",
    "attraction",
    "clearance",
    "interference",
    "sacrifice",
    "discoveredCheck",
    "doubleCheck",
    "kingsideAttack",
    "queensideAttack",
    "attackingF2F7",
    "backRankMate",
    "exposedKing",
    "hangingPiece",
    "trappedPiece",
    "capturingDefender",
    "advancedPawn",
    "promotion",
    "mate",
)
ATTACK_THEMES: frozenset[str] = frozenset(ATTACK_CLASSES)


def _theme_set(themes: str | Iterable[str] | None) -> set[str]:
    if isinstance(themes, str):
        return set(themes.split())
    return set(themes or ())


def fen_white_to_move(fen: str) -> bool:
    parts = fen.split()
    return len(parts) >= 2 and parts[1] == "w"


def attack_theme_labels(themes: str | Iterable[str] | None) -> list[str]:
    found = _theme_set(themes)
    return [theme for theme in ATTACK_CLASSES if theme in found]


def attack_label_vector(themes: str | Iterable[str] | None) -> list[int]:
    found = _theme_set(themes)
    return [int(theme in found) for theme in ATTACK_CLASSES]


def attack_label_matrix(themes_iterable: Iterable[str | Iterable[str]]) -> np.ndarray:
    return np.asarray([attack_label_vector(themes) for themes in themes_iterable], dtype=np.int8)


def is_pattern_row(row: dict) -> bool:
    if not fen_white_to_move(row.get("FEN", "")):
        return False
    try:
        popularity = float(row.get("Popularity") or 0)
    except (TypeError, ValueError):
        return False
    return popularity >= 50 and bool(attack_theme_labels(row.get("Themes")))


def load_pattern_dataset(limit: int = 0) -> Dataset:
    """Lichess/chess-puzzles rows filtered to white-to-move attack puzzles."""
    dataset = load_dataset("Lichess/chess-puzzles", split="train")
    dataset = dataset.filter(is_pattern_row, desc="filter attack puzzles")
    if limit > 0:
        dataset = dataset.select(range(min(limit, len(dataset))))
    return dataset.map(
        lambda row: {"label_vector": attack_label_vector(row["Themes"])},
        desc="encode labels",
    )


def split_by_game_id(
    dataset: Dataset, test_size: float = 0.2, random_state: int = 42
) -> tuple[Dataset, Dataset]:
    """Keep every GameId entirely on one side of the split."""
    groups = dataset["GameId"]
    splitter = GroupShuffleSplit(
        n_splits=1, test_size=test_size, random_state=random_state
    )
    train_idx, test_idx = next(
        splitter.split(np.zeros(len(groups)), groups=groups)
    )
    return dataset.select(train_idx), dataset.select(test_idx)
