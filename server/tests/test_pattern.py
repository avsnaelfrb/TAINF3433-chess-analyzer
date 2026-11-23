import chess
from datasets import Dataset

from app.pattern import (
    ATTACK_CLASSES,
    ATTACK_THEMES,
    attack_label_matrix,
    attack_label_vector,
    attack_theme_labels,
    fen_white_to_move,
    is_pattern_row,
    split_by_game_id,
)


def test_theme_constants_are_consistent():
    assert len(ATTACK_CLASSES) == 23
    assert len(set(ATTACK_CLASSES)) == 23
    assert len(ATTACK_THEMES) == 23


def test_fen_white_to_move():
    assert fen_white_to_move(chess.STARTING_FEN)
    assert not fen_white_to_move(chess.STARTING_FEN.replace(" w ", " b "))
    assert not fen_white_to_move("garbage")


def test_attack_label_vector_and_labels():
    assert attack_theme_labels("mate fork opening quietMove") == ["fork", "mate"]
    assert attack_theme_labels(["mate", "unknown"]) == ["mate"]
    vector = attack_label_vector("mate fork opening")
    assert len(vector) == 23
    assert sum(vector) == 2
    assert vector[ATTACK_CLASSES.index("fork")] == 1
    assert vector[ATTACK_CLASSES.index("mate")] == 1
    assert vector[ATTACK_CLASSES.index("sacrifice")] == 0
    matrix = attack_label_matrix(["mate fork", "pin"])
    assert matrix.shape == (2, 23)
    assert matrix[0].sum() == 2 and matrix[1].sum() == 1


def test_is_pattern_row_filters_white_popularity_and_theme():
    base = {"FEN": chess.STARTING_FEN, "Popularity": 50, "Themes": "fork mate"}
    assert is_pattern_row(base)
    assert not is_pattern_row({**base, "FEN": base["FEN"].replace(" w ", " b ")})
    assert not is_pattern_row({**base, "Popularity": 49})
    assert not is_pattern_row({**base, "Themes": "opening quietMove"})
    assert not is_pattern_row({**base, "Popularity": "not-a-number"})


def test_split_by_game_id_has_no_group_leakage():
    dataset = Dataset.from_dict(
        {
            "GameId": ["g1", "g1", "g2", "g2", "g3", "g3", "g4", "g4"],
            "FEN": [chess.STARTING_FEN] * 8,
        }
    )
    train, test = split_by_game_id(dataset)
    assert len(train) + len(test) == len(dataset)
    assert set(train["GameId"]).isdisjoint(test["GameId"])
