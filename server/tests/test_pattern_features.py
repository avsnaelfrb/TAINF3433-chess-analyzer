import chess
import numpy as np

from app.pattern_features import (
    FEATURE_NAMES,
    PatternFeatureExtractor,
    extract_pattern_features,
    pattern_vector,
)

TACTICAL_FEN = "r1bq1rk1/ppp2ppp/2n5/3np3/2B1P3/2N2N2/PPP2PPP/R1BQ1RK1 w - - 0 9"


def test_feature_names_are_unique_and_complete():
    assert len(FEATURE_NAMES) == 46
    assert len(set(FEATURE_NAMES)) == 46


def test_extract_returns_all_features_as_floats():
    features = extract_pattern_features(chess.STARTING_FEN)
    assert set(features) == set(FEATURE_NAMES)
    assert all(isinstance(value, float) and np.isfinite(value) for value in features.values())


def test_vector_shape_for_multiple_positions():
    for fen in (chess.STARTING_FEN, TACTICAL_FEN):
        vector = pattern_vector(fen)
        assert vector.shape == (46,)
        assert np.isfinite(vector).all()


def test_clock_fields_do_not_leak_into_features():
    shifted = chess.STARTING_FEN.replace(" 0 1", " 33 77")
    np.testing.assert_array_equal(pattern_vector(shifted), pattern_vector(chess.STARTING_FEN))


def test_material_is_from_black_perspective():
    black_up = extract_pattern_features("3qk3/8/8/8/8/8/8/4K3 w - - 0 1")
    white_up = extract_pattern_features("3Qk3/8/8/8/8/8/8/4K3 w - - 0 1")
    assert black_up["material_diff_black"] > 0
    assert white_up["material_diff_black"] < 0
    assert black_up["black_queen_count"] == 1
    assert white_up["white_queen_count"] == 1


def test_pawn_and_king_features():
    features = extract_pattern_features("4k3/3p4/8/8/8/8/8/4K3 w - - 0 1")
    assert features["black_passed_pawns"] == 1
    assert features["black_promotion_distance"] == 6
    assert features["white_king_exposed"] == 1


def test_extractor_transform_and_input_board_untouched():
    fen = TACTICAL_FEN
    board = chess.Board(fen)
    matrix = PatternFeatureExtractor().fit_transform([fen, chess.STARTING_FEN])
    assert matrix.shape == (2, 46)
    assert board.fen() == fen
    assert board.turn == chess.WHITE
