export type Color = 'white' | 'black'
export type PieceType =
  | 'pawn'
  | 'knight'
  | 'bishop'
  | 'rook'
  | 'queen'
  | 'king'
export type PromotionType = Exclude<PieceType, 'pawn' | 'king'>

export interface Piece {
  color: Color
  type: PieceType
}

export interface Square {
  file: number
  rank: number
}

export type Board = (Piece | null)[][]

export interface Move {
  from: Square
  to: Square
  promotion?: PromotionType
  castle?: 'king' | 'queen'
  enPassant?: boolean
}

export interface CastlingRights {
  whiteKing: boolean
  whiteQueen: boolean
  blackKing: boolean
  blackQueen: boolean
}

export interface GameSnapshot {
  board: Board
  turn: Color
  castling: CastlingRights
  enPassant: Square | null
  ply: number
}

export type GameStatus = 'playing' | 'check' | 'checkmate' | 'stalemate'

export interface GameState extends GameSnapshot {
  status: GameStatus
}
