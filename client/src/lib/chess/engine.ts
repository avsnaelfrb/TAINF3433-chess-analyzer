import type {
  Board,
  CastlingRights,
  Color,
  GameSnapshot,
  GameState,
  GameStatus,
  Move,
  Piece,
  PieceType,
  PromotionType,
  Square,
} from '../../types/chess'
import {
  cloneBoard,
  createInitialBoard,
  initialCastlingRights,
  isInside,
  pieceAt,
  sameSquare,
} from './board'

const KNIGHT_OFFSETS: readonly Square[] = [
  { file: 1, rank: 2 },
  { file: 2, rank: 1 },
  { file: 2, rank: -1 },
  { file: 1, rank: -2 },
  { file: -1, rank: -2 },
  { file: -2, rank: -1 },
  { file: -2, rank: 1 },
  { file: -1, rank: 2 },
]

const KING_OFFSETS: readonly Square[] = [
  { file: 1, rank: 1 },
  { file: 1, rank: 0 },
  { file: 1, rank: -1 },
  { file: 0, rank: -1 },
  { file: -1, rank: -1 },
  { file: -1, rank: 0 },
  { file: -1, rank: 1 },
  { file: 0, rank: 1 },
]

const DIAGONAL_DIRECTIONS: readonly Square[] = [
  { file: 1, rank: 1 },
  { file: 1, rank: -1 },
  { file: -1, rank: -1 },
  { file: -1, rank: 1 },
]

const ORTHOGONAL_DIRECTIONS: readonly Square[] = [
  { file: 1, rank: 0 },
  { file: -1, rank: 0 },
  { file: 0, rank: 1 },
  { file: 0, rank: -1 },
]

const PROMOTION_TYPES: readonly PromotionType[] = ['queen', 'rook', 'bishop', 'knight']

function opposite(color: Color): Color {
  return color === 'white' ? 'black' : 'white'
}

function pawnDirection(color: Color): number {
  return color === 'white' ? 1 : -1
}

function pawnStartRank(color: Color): number {
  return color === 'white' ? 1 : 6
}

function promotionRank(color: Color): number {
  return color === 'white' ? 7 : 0
}

function isEnemy(piece: Piece | null, color: Color): boolean {
  return piece !== null && piece.color !== color
}

function canLandOn(piece: Piece | null, color: Color): boolean {
  return piece === null || piece.color !== color
}

function attacksAlong(
  board: Board,
  square: Square,
  by: Color,
  directions: readonly Square[],
  types: readonly PieceType[],
): boolean {
  for (const direction of directions) {
    let file = square.file + direction.file
    let rank = square.rank + direction.rank
    while (isInside({ file, rank })) {
      const piece = pieceAt(board, { file, rank })
      if (piece) {
        if (piece.color === by && types.includes(piece.type)) return true
        break
      }
      file += direction.file
      rank += direction.rank
    }
  }
  return false
}

export function isSquareAttacked(board: Board, square: Square, by: Color): boolean {
  if (!isInside(square)) return false

  const pawnOriginRank = square.rank - pawnDirection(by)
  for (const fileOffset of [-1, 1]) {
    const pawn = pieceAt(board, { file: square.file + fileOffset, rank: pawnOriginRank })
    if (pawn?.color === by && pawn.type === 'pawn') return true
  }

  for (const offset of KNIGHT_OFFSETS) {
    const piece = pieceAt(board, {
      file: square.file + offset.file,
      rank: square.rank + offset.rank,
    })
    if (piece?.color === by && piece.type === 'knight') return true
  }

  for (const offset of KING_OFFSETS) {
    const piece = pieceAt(board, {
      file: square.file + offset.file,
      rank: square.rank + offset.rank,
    })
    if (piece?.color === by && piece.type === 'king') return true
  }

  if (attacksAlong(board, square, by, DIAGONAL_DIRECTIONS, ['bishop', 'queen'])) {
    return true
  }
  return attacksAlong(board, square, by, ORTHOGONAL_DIRECTIONS, ['rook', 'queen'])
}

export function kingSquare(board: Board, color: Color): Square | null {
  for (let rank = 0; rank < 8; rank++) {
    for (let file = 0; file < 8; file++) {
      const piece = board[rank][file]
      if (piece?.color === color && piece.type === 'king') return { file, rank }
    }
  }
  return null
}

export function isInCheck(board: Board, color: Color): boolean {
  const king = kingSquare(board, color)
  return king !== null && isSquareAttacked(board, king, opposite(color))
}

function addPawnMoves(
  state: GameSnapshot,
  from: Square,
  color: Color,
  moves: Move[],
): void {
  const direction = pawnDirection(color)
  const oneStep = { file: from.file, rank: from.rank + direction }

  if (isInside(oneStep) && pieceAt(state.board, oneStep) === null) {
    if (oneStep.rank === promotionRank(color)) {
      for (const promotion of PROMOTION_TYPES) moves.push({ from, to: oneStep, promotion })
    } else {
      moves.push({ from, to: oneStep })
      const twoStep = { file: from.file, rank: from.rank + 2 * direction }
      if (
        from.rank === pawnStartRank(color) &&
        pieceAt(state.board, twoStep) === null
      ) {
        moves.push({ from, to: twoStep })
      }
    }
  }

  for (const fileOffset of [-1, 1]) {
    const to = { file: from.file + fileOffset, rank: from.rank + direction }
    if (!isInside(to)) continue
    const target = pieceAt(state.board, to)
    if (isEnemy(target, color)) {
      if (to.rank === promotionRank(color)) {
        for (const promotion of PROMOTION_TYPES) {
          moves.push({ from, to, promotion })
        }
      } else {
        moves.push({ from, to })
      }
    } else if (state.enPassant && sameSquare(to, state.enPassant)) {
      moves.push({ from, to, enPassant: true })
    }
  }
}

function addCastlingMoves(
  state: GameSnapshot,
  from: Square,
  color: Color,
  moves: Move[],
): void {
  const rank = color === 'white' ? 0 : 7
  const enemy = opposite(color)
  if (!sameSquare(from, { file: 4, rank })) return
  if (isSquareAttacked(state.board, from, enemy)) return

  const rights: CastlingRights = state.castling
  const kingSide = color === 'white' ? rights.whiteKing : rights.blackKing
  const queenSide = color === 'white' ? rights.whiteQueen : rights.blackQueen
  const rook: Piece = { color, type: 'rook' }

  const rookOn = (file: number): boolean => {
    const piece = pieceAt(state.board, { file, rank })
    return piece?.color === rook.color && piece.type === rook.type
  }

  if (kingSide) {
    const first = { file: 5, rank }
    const second = { file: 6, rank }
    if (
      pieceAt(state.board, first) === null &&
      pieceAt(state.board, second) === null &&
      rookOn(7) &&
      !isSquareAttacked(state.board, first, enemy) &&
      !isSquareAttacked(state.board, second, enemy)
    ) {
      moves.push({ from, to: second, castle: 'king' })
    }
  }

  if (queenSide) {
    const first = { file: 3, rank }
    const second = { file: 2, rank }
    const third = { file: 1, rank }
    if (
      pieceAt(state.board, first) === null &&
      pieceAt(state.board, second) === null &&
      pieceAt(state.board, third) === null &&
      rookOn(0) &&
      !isSquareAttacked(state.board, first, enemy) &&
      !isSquareAttacked(state.board, second, enemy)
    ) {
      moves.push({ from, to: second, castle: 'queen' })
    }
  }
}

export function pseudoMoves(state: GameSnapshot, from?: Square): Move[] {
  const moves: Move[] = []
  const origins: Square[] = []

  if (from) {
    if (isInside(from)) origins.push(from)
  } else {
    for (let rank = 0; rank < 8; rank++) {
      for (let file = 0; file < 8; file++) origins.push({ file, rank })
    }
  }

  for (const origin of origins) {
    const piece = pieceAt(state.board, origin)
    if (!piece || piece.color !== state.turn) continue

    switch (piece.type) {
      case 'pawn':
        addPawnMoves(state, origin, piece.color, moves)
        break
      case 'knight':
        for (const offset of KNIGHT_OFFSETS) {
          const to = { file: origin.file + offset.file, rank: origin.rank + offset.rank }
          if (isInside(to) && canLandOn(pieceAt(state.board, to), piece.color)) {
            moves.push({ from: origin, to })
          }
        }
        break
      case 'king':
        for (const offset of KING_OFFSETS) {
          const to = { file: origin.file + offset.file, rank: origin.rank + offset.rank }
          if (isInside(to) && canLandOn(pieceAt(state.board, to), piece.color)) {
            moves.push({ from: origin, to })
          }
        }
        addCastlingMoves(state, origin, piece.color, moves)
        break
      case 'bishop':
      case 'rook':
      case 'queen': {
        const directions =
          piece.type === 'bishop'
            ? DIAGONAL_DIRECTIONS
            : piece.type === 'rook'
              ? ORTHOGONAL_DIRECTIONS
              : [...DIAGONAL_DIRECTIONS, ...ORTHOGONAL_DIRECTIONS]
        for (const direction of directions) {
          let file = origin.file + direction.file
          let rank = origin.rank + direction.rank
          while (isInside({ file, rank })) {
            const to = { file, rank }
            const target = pieceAt(state.board, to)
            if (target?.color === piece.color) break
            moves.push({ from: origin, to })
            if (target) break
            file += direction.file
            rank += direction.rank
          }
        }
        break
      }
    }
  }

  return moves
}

export function applyMove(state: GameSnapshot, move: Move): GameSnapshot {
  const board = cloneBoard(state.board)
  const piece = pieceAt(board, move.from)
  if (!piece) throw new Error('No piece on the move origin')

  const captured = pieceAt(board, move.to)
  board[move.from.rank][move.from.file] = null

  if (move.enPassant) {
    board[move.from.rank][move.to.file] = null
  }

  const landed: Piece = move.promotion
    ? { color: piece.color, type: move.promotion }
    : piece
  board[move.to.rank][move.to.file] = landed

  const rank = piece.color === 'white' ? 0 : 7
  if (move.castle === 'king') {
    const rook = board[rank][7]
    board[rank][7] = null
    board[rank][5] = rook
  } else if (move.castle === 'queen') {
    const rook = board[rank][0]
    board[rank][0] = null
    board[rank][3] = rook
  }

  const castling: CastlingRights = { ...state.castling }
  if (piece.type === 'king') {
    if (piece.color === 'white') {
      castling.whiteKing = false
      castling.whiteQueen = false
    } else {
      castling.blackKing = false
      castling.blackQueen = false
    }
  }
  if (piece.type === 'rook') {
    if (sameSquare(move.from, { file: 0, rank: 0 })) castling.whiteQueen = false
    if (sameSquare(move.from, { file: 7, rank: 0 })) castling.whiteKing = false
    if (sameSquare(move.from, { file: 0, rank: 7 })) castling.blackQueen = false
    if (sameSquare(move.from, { file: 7, rank: 7 })) castling.blackKing = false
  }
  if (captured?.type === 'rook') {
    if (sameSquare(move.to, { file: 0, rank: 0 })) castling.whiteQueen = false
    if (sameSquare(move.to, { file: 7, rank: 0 })) castling.whiteKing = false
    if (sameSquare(move.to, { file: 0, rank: 7 })) castling.blackQueen = false
    if (sameSquare(move.to, { file: 7, rank: 7 })) castling.blackKing = false
  }

  let enPassant: Square | null = null
  if (piece.type === 'pawn' && Math.abs(move.to.rank - move.from.rank) === 2) {
    enPassant = { file: move.from.file, rank: (move.from.rank + move.to.rank) / 2 }
  }

  return {
    board,
    turn: opposite(state.turn),
    castling,
    enPassant,
    ply: state.ply + 1,
  }
}

export function legalMoves(state: GameSnapshot, from?: Square): Move[] {
  const mover = state.turn
  return pseudoMoves(state, from).filter((move) => {
    const next = applyMove(state, move)
    const king = kingSquare(next.board, mover)
    return king === null || !isSquareAttacked(next.board, king, opposite(mover))
  })
}

export function gameStatus(state: GameSnapshot): GameStatus {
  const inCheck = isInCheck(state.board, state.turn)
  if (legalMoves(state).length === 0) {
    return inCheck ? 'checkmate' : 'stalemate'
  }
  return inCheck ? 'check' : 'playing'
}

export function withStatus(snapshot: GameSnapshot): GameState {
  return {
    board: snapshot.board,
    turn: snapshot.turn,
    castling: snapshot.castling,
    enPassant: snapshot.enPassant,
    ply: snapshot.ply,
    status: gameStatus(snapshot),
  }
}

export function createInitialGame(): GameState {
  return withStatus({
    board: createInitialBoard(),
    turn: 'white',
    castling: initialCastlingRights(),
    enPassant: null,
    ply: 0,
  })
}
