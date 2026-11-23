import type {
  Board,
  CastlingRights,
  Piece,
  PieceType,
  Square,
} from '../../types/chess'

const BACK_RANK: PieceType[] = [
  'rook',
  'knight',
  'bishop',
  'queen',
  'king',
  'bishop',
  'knight',
  'rook',
]

export function createEmptyBoard(): Board {
  return Array.from({ length: 8 }, () => Array<Piece | null>(8).fill(null))
}

export function createInitialBoard(): Board {
  const board = createEmptyBoard()
  for (let file = 0; file < 8; file++) {
    board[0][file] = { color: 'white', type: BACK_RANK[file] }
    board[1][file] = { color: 'white', type: 'pawn' }
    board[6][file] = { color: 'black', type: 'pawn' }
    board[7][file] = { color: 'black', type: BACK_RANK[file] }
  }
  return board
}

export function cloneBoard(board: Board): Board {
  return board.map((row) => row.map((piece) => (piece ? { ...piece } : null)))
}

export function initialCastlingRights(): CastlingRights {
  return { whiteKing: true, whiteQueen: true, blackKing: true, blackQueen: true }
}

export function isInside(square: Square): boolean {
  return (
    Number.isInteger(square.file) &&
    Number.isInteger(square.rank) &&
    square.file >= 0 &&
    square.file < 8 &&
    square.rank >= 0 &&
    square.rank < 8
  )
}

export function sameSquare(a: Square, b: Square): boolean {
  return a.file === b.file && a.rank === b.rank
}

export function pieceAt(board: Board, square: Square): Piece | null {
  return board[square.rank]?.[square.file] ?? null
}
