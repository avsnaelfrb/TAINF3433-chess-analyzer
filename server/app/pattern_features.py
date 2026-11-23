"""46 FEN-derived features, all computed from black's point of view.

No clock, ply or fullmove fields are read: the model sees a position, not a
move history. All values are plain floats so the pipeline survives joblib.
"""

from __future__ import annotations

from collections.abc import Iterable

import chess
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin

FEATURE_NAMES: tuple[str, ...] = (
    # material and piece counts
    "material_diff_black",
    "black_pawn_count",
    "black_knight_count",
    "black_bishop_count",
    "black_rook_count",
    "black_queen_count",
    "white_pawn_count",
    "white_rook_count",
    "white_queen_count",
    "piece_count_diff",
    # white king position and shelter
    "white_king_file",
    "white_king_rank",
    "white_king_castled",
    "white_king_shield",
    "white_king_open_files",
    "white_king_exposed",
    "black_heavy_near_white_king",
    "black_attackers_king_zone",
    "white_king_center_distance",
    "white_king_back_rank",
    # black pressure
    "white_pieces_attacked",
    "white_hanging_pieces",
    "white_defended_pieces",
    "fork_targets",
    "capturable_defenders",
    "black_attacks_total",
    "black_attacks_king_zone",
    "white_pinned_pieces",
    "black_pinned_pieces",
    # tactical geometry
    "skewer_lines",
    "discovered_attack_blockers",
    "discovered_check_blockers",
    "double_check_squares",
    "xray_lines",
    "back_rank_gap",
    "white_king_diagonal_exposure",
    # black pawns and promotion
    "black_advanced_pawns",
    "black_passed_pawns",
    "black_pawn_advancement",
    "black_promotion_distance",
    "black_pawns_on_7th",
    "white_pawns_on_7th",
    # black mobility proxy
    "black_legal_moves",
    "black_checks",
    "black_captures",
    "black_capture_value",
)

PIECE_VALUES = {
    chess.PAWN: 1.0,
    chess.KNIGHT: 3.2,
    chess.BISHOP: 3.3,
    chess.ROOK: 5.0,
    chess.QUEEN: 9.0,
    chess.KING: 0.0,
}
ORTHOGONAL = ((1, 0), (-1, 0), (0, 1), (0, -1))
DIAGONAL = ((1, 1), (1, -1), (-1, 1), (-1, -1))
SLIDER_DIRS = {
    chess.ROOK: ORTHOGONAL,
    chess.BISHOP: DIAGONAL,
    chess.QUEEN: ORTHOGONAL + DIAGONAL,
}


def _chebyshev(a: chess.Square, b: chess.Square) -> int:
    return max(
        abs(chess.square_file(a) - chess.square_file(b)),
        abs(chess.square_rank(a) - chess.square_rank(b)),
    )


def _piece_squares(board: chess.Board, piece_type: chess.PieceType, color: chess.Color):
    return board.pieces(piece_type, color)


def _color_squares(board: chess.Board, color: chess.Color):
    for piece_type in (
        chess.PAWN,
        chess.KNIGHT,
        chess.BISHOP,
        chess.ROOK,
        chess.QUEEN,
        chess.KING,
    ):
        yield from _piece_squares(board, piece_type, color)


def _slider_chains(board: chess.Board):
    """Yield (slider square, occupied squares along each legal slider ray)."""
    for square in board.pieces(chess.QUEEN, chess.BLACK):
        yield from _chains_from(board, square, SLIDER_DIRS[chess.QUEEN])
    for square in board.pieces(chess.ROOK, chess.BLACK):
        yield from _chains_from(board, square, SLIDER_DIRS[chess.ROOK])
    for square in board.pieces(chess.BISHOP, chess.BLACK):
        yield from _chains_from(board, square, SLIDER_DIRS[chess.BISHOP])


def _chains_from(board: chess.Board, square: chess.Square, directions):
    origin_file, origin_rank = chess.square_file(square), chess.square_rank(square)
    for df, dr in directions:
        file_index, rank_index = origin_file + df, origin_rank + dr
        chain: list[tuple[chess.Square, chess.Piece]] = []
        while 0 <= file_index < 8 and 0 <= rank_index < 8:
            target = chess.square(file_index, rank_index)
            piece = board.piece_at(target)
            if piece is not None:
                chain.append((target, piece))
            file_index += df
            rank_index += dr
        if chain:
            yield square, chain


def _black_attack_counts(board: chess.Board) -> dict[chess.Square, int]:
    counts: dict[chess.Square, int] = {}
    for square in _color_squares(board, chess.BLACK):
        for target in board.attacks(square):
            counts[target] = counts.get(target, 0) + 1
    return counts


def _mobility(board: chess.Board, features: dict[str, float]) -> None:
    probe = board.copy(stack=False)
    probe.turn = chess.BLACK
    moves = list(probe.legal_moves)
    features["black_legal_moves"] = float(len(moves))
    features["black_checks"] = float(sum(probe.gives_check(move) for move in moves))
    captures = [move for move in moves if probe.is_capture(move)]
    features["black_captures"] = float(len(captures))
    features["black_capture_value"] = float(
        sum(
            PIECE_VALUES.get(probe.piece_type_at(move.to_square), 1.0)
            for move in captures
        )
    )


def extract_pattern_features(fen: str) -> dict[str, float]:
    """Return a mapping of all 46 features for a single FEN."""
    board = chess.Board(fen)
    features: dict[str, float] = dict.fromkeys(FEATURE_NAMES, 0.0)

    white = {pt: _piece_squares(board, pt, chess.WHITE) for pt in PIECE_VALUES}
    black = {pt: _piece_squares(board, pt, chess.BLACK) for pt in PIECE_VALUES}

    for color, pieces in ((chess.BLACK, black), (chess.WHITE, white)):
        sign = 1 if color == chess.BLACK else -1
        for piece_type, squares in pieces.items():
            features["material_diff_black"] += sign * PIECE_VALUES[piece_type] * len(squares)

    features["black_pawn_count"] = float(len(black[chess.PAWN]))
    features["black_knight_count"] = float(len(black[chess.KNIGHT]))
    features["black_bishop_count"] = float(len(black[chess.BISHOP]))
    features["black_rook_count"] = float(len(black[chess.ROOK]))
    features["black_queen_count"] = float(len(black[chess.QUEEN]))
    features["white_pawn_count"] = float(len(white[chess.PAWN]))
    features["white_rook_count"] = float(len(white[chess.ROOK]))
    features["white_queen_count"] = float(len(white[chess.QUEEN]))
    features["piece_count_diff"] = float(
        sum(len(squares) for squares in black.values())
        - sum(len(squares) for squares in white.values())
    )

    white_king_square = board.king(chess.WHITE)
    if white_king_square is None:
        _pawns(board, features)
        _mobility(board, features)
        return features

    king_file = chess.square_file(white_king_square)
    king_rank = chess.square_rank(white_king_square)
    features["white_king_file"] = float(king_file)
    features["white_king_rank"] = float(king_rank)
    features["white_king_castled"] = float(white_king_square in (chess.G1, chess.C1))
    features["white_king_back_rank"] = float(king_rank == 0)
    features["white_king_center_distance"] = max(
        abs(king_file - 3.5), abs(king_rank - 3.5)
    )

    king_zone = set(board.attacks(white_king_square)) | {white_king_square}
    shield = sum(
        1
        for square in king_zone
        if (piece := board.piece_at(square)) is not None
        and piece.color == chess.WHITE
        and piece.piece_type == chess.PAWN
    )
    features["white_king_shield"] = float(shield)
    features["white_king_exposed"] = float(shield == 0)

    open_files = 0
    for file_index in range(max(0, king_file - 1), min(7, king_file + 1) + 1):
        file_mask = chess.BB_FILES[file_index]
        if not (board.pawns & board.occupied_co[chess.WHITE] & file_mask):
            open_files += 1
    features["white_king_open_files"] = float(open_files)

    features["black_heavy_near_white_king"] = float(
        sum(
            1
            for piece_type in (chess.QUEEN, chess.ROOK)
            for square in black[piece_type]
            if _chebyshev(square, white_king_square) <= 3
        )
    )

    attack_counts = _black_attack_counts(board)
    features["black_attacks_total"] = float(len(attack_counts))
    features["black_attackers_king_zone"] = float(
        sum(1 for square in king_zone if board.is_attacked_by(chess.BLACK, square))
    )
    features["black_attacks_king_zone"] = float(
        sum(1 for square in king_zone if attack_counts.get(square, 0))
    )
    features["double_check_squares"] = float(
        sum(
            1
            for square in king_zone
            if square != white_king_square
            and board.piece_at(square) is None
            and attack_counts.get(square, 0) >= 2
        )
    )

    white_pieces = [
        square
        for piece_type in (
            chess.PAWN,
            chess.KNIGHT,
            chess.BISHOP,
            chess.ROOK,
            chess.QUEEN,
        )
        for square in white[piece_type]
    ]
    attacked = [sq for sq in white_pieces if board.is_attacked_by(chess.BLACK, sq)]
    defended = {sq for sq in white_pieces if board.is_attacked_by(chess.WHITE, sq)}
    features["white_pieces_attacked"] = float(len(attacked))
    features["white_hanging_pieces"] = float(sum(sq not in defended for sq in attacked))
    features["white_defended_pieces"] = float(len(defended))

    features["fork_targets"] = float(
        sum(
            1
            for square in _color_squares(board, chess.BLACK)
            if sum(
                1
                for target in board.attacks(square)
                if (piece := board.piece_at(target)) is not None
                and piece.color == chess.WHITE
                and piece.piece_type != chess.KING
            )
            >= 2
        )
    )
    features["capturable_defenders"] = float(
        sum(
            1
            for square in attacked
            if any(
                (piece := board.piece_at(target)) is not None
                and piece.color == chess.WHITE
                for target in board.attacks(square)
            )
        )
    )

    features["white_pinned_pieces"] = float(
        sum(1 for square in white_pieces if board.is_pinned(chess.WHITE, square))
    )
    features["black_pinned_pieces"] = float(
        sum(
            1
            for piece_type in (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)
            for square in black[piece_type]
            if board.is_pinned(chess.BLACK, square)
        )
    )

    skewer = xray = discovered_attack = discovered_check = 0
    for _, chain in _slider_chains(board):
        first_piece = chain[0][1]
        if first_piece.color == chess.WHITE:
            if first_piece.piece_type != chess.KING:
                xray += 1
                if len(chain) > 1 and chain[1][1].color == chess.WHITE:
                    skewer += 1
        elif len(chain) > 1 and chain[1][1].color == chess.WHITE:
            if chain[1][1].piece_type == chess.KING:
                discovered_check += 1
            else:
                discovered_attack += 1
    features["skewer_lines"] = float(skewer)
    features["xray_lines"] = float(xray)
    features["discovered_attack_blockers"] = float(discovered_attack)
    features["discovered_check_blockers"] = float(discovered_check)

    back_rank_gap = 0
    for file_index in range(8):
        if board.piece_at(chess.square(file_index, 0)) is not None:
            continue
        pawn = board.piece_at(chess.square(file_index, 1))
        if pawn is None or pawn.color != chess.WHITE or pawn.piece_type != chess.PAWN:
            back_rank_gap += 1
    features["back_rank_gap"] = float(back_rank_gap)

    diagonal_exposure = 0
    for df, dr in DIAGONAL:
        file_index, rank_index = king_file + df, king_rank + dr
        while 0 <= file_index < 8 and 0 <= rank_index < 8:
            piece = board.piece_at(chess.square(file_index, rank_index))
            if piece is not None:
                if piece.color == chess.BLACK and piece.piece_type in (
                    chess.QUEEN,
                    chess.BISHOP,
                ):
                    diagonal_exposure += 1
                break
            file_index += df
            rank_index += dr
    features["white_king_diagonal_exposure"] = float(diagonal_exposure)

    _pawns(board, features)
    _mobility(board, features)
    return features


def _pawns(board: chess.Board, features: dict[str, float]) -> None:
    black_pawns = list(board.pieces(chess.PAWN, chess.BLACK))
    white_pawns = list(board.pieces(chess.PAWN, chess.WHITE))
    white_pawn_squares = {
        (chess.square_file(sq), chess.square_rank(sq)) for sq in white_pawns
    }

    advanced = passed = advancement = 0
    promotion_distance = 8
    on_seventh = 0
    for square in black_pawns:
        file_index, rank_index = chess.square_file(square), chess.square_rank(square)
        if rank_index <= 4:
            advanced += 1
        if rank_index == 1:
            on_seventh += 1
        advancement += max(0, 6 - rank_index)
        promotion_distance = min(promotion_distance, rank_index)
        if not any(
            other_file in (file_index - 1, file_index, file_index + 1)
            and other_rank < rank_index
            for other_file, other_rank in white_pawn_squares
        ):
            passed += 1

    features["black_advanced_pawns"] = float(advanced)
    features["black_passed_pawns"] = float(passed)
    features["black_pawn_advancement"] = float(advancement)
    features["black_promotion_distance"] = float(promotion_distance)
    features["black_pawns_on_7th"] = float(on_seventh)
    features["white_pawns_on_7th"] = float(
        sum(1 for sq in white_pawns if chess.square_rank(sq) == 6)
    )


def pattern_vector(fen: str) -> np.ndarray:
    features = extract_pattern_features(fen)
    return np.asarray([features[name] for name in FEATURE_NAMES])


class PatternFeatureExtractor(BaseEstimator, TransformerMixin):
    """Stateless sklearn transformer around :func:`pattern_vector`."""

    def fit(self, X, y=None):
        return self

    def transform(self, X: Iterable[str]) -> np.ndarray:
        return np.vstack([pattern_vector(fen) for fen in X])
