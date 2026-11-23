import type { Board, CastlingRights, GameSnapshot, Piece } from '../../types/chess'
import { PIECE_LETTERS } from './constants'
import { squareName } from './notation'

export const INITIAL_FEN =
  'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'

function fenPiece(piece: Piece): string {
  const letter = PIECE_LETTERS[piece.type]
  return piece.color === 'white' ? letter.toUpperCase() : letter
}

function placement(board: Board): string {
  return board
    .map((row) => {
      let result = ''
      let empty = 0
      for (const piece of row) {
        if (!piece) {
          empty++
          continue
        }
        if (empty > 0) {
          result += empty
          empty = 0
        }
        result += fenPiece(piece)
      }
      if (empty > 0) result += empty
      return result
    })
    .reverse()
    .join('/')
}

function castlingField(rights: CastlingRights): string {
  let result = ''
  if (rights.whiteKing) result += 'K'
  if (rights.whiteQueen) result += 'Q'
  if (rights.blackKing) result += 'k'
  if (rights.blackQueen) result += 'q'
  return result || '-'
}

export function toFen(state: GameSnapshot): string {
  const fullmove = Math.floor(state.ply / 2) + 1
  return [
    placement(state.board),
    state.turn === 'white' ? 'w' : 'b',
    castlingField(state.castling),
    state.enPassant ? squareName(state.enPassant) : '-',
    0,
    fullmove,
  ].join(' ')
}
