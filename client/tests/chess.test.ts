import { describe, expect, it } from 'vitest'
import type {
  Board,
  CastlingRights,
  Color,
  GameSnapshot,
  PieceType,
  PromotionType,
} from '../src/types/chess'
import {
  createEmptyBoard,
  createInitialBoard,
  initialCastlingRights,
} from '../src/lib/chess/board'
import {
  applyMove,
  createInitialGame,
  gameStatus,
  legalMoves,
  withStatus,
} from '../src/lib/chess/engine'
import { INITIAL_FEN, toFen } from '../src/lib/chess/fen'
import { parseSquare } from '../src/lib/chess/notation'

function square(name: string) {
  const result = parseSquare(name)
  if (!result) throw new Error(`Invalid square: ${name}`)
  return result
}

function move(
  state: GameSnapshot,
  from: string,
  to: string,
  promotion?: PromotionType,
): GameSnapshot {
  return applyMove(state, { from: square(from), to: square(to), promotion })
}

function put(board: Board, name: string, color: Color, type: PieceType): void {
  const at = square(name)
  board[at.rank][at.file] = { color, type }
}

function noCastling(): CastlingRights {
  return { whiteKing: false, whiteQueen: false, blackKing: false, blackQueen: false }
}

function position(board: Board, turn: Color): GameSnapshot {
  return { board, turn, castling: noCastling(), enPassant: null, ply: 0 }
}

describe('FEN', () => {
  it('membuat FEN awal', () => {
    expect(toFen(createInitialGame())).toBe(INITIAL_FEN)
  })

  it('mencatat en passant dan menaikkan fullmove setelah giliran hitam', () => {
    const afterE4 = move(createInitialGame(), 'e2', 'e4')
    expect(toFen(afterE4)).toBe(
      'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1',
    )

    const afterE5 = move(afterE4, 'e7', 'e5')
    expect(toFen(afterE5)).toBe(
      'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2',
    )
  })

  it('menghapus hak castling saat rook bergerak', () => {
    const state = move(move(createInitialGame(), 'g1', 'f3'), 'h1', 'g1')
    expect(toFen(state).split(' ')[2]).toBe('Qkq')
  })
})

describe('engine catur', () => {
  it('menghasilkan 20 langkah legal di posisi awal', () => {
    expect(legalMoves(createInitialGame())).toHaveLength(20)
  })

  it('tidak mengubah state lama saat applyMove', () => {
    const initial = createInitialGame()
    const snapshot = initial.board[1][4]
    move(initial, 'e2', 'e4')
    expect(initial.board[1][4]).toEqual(snapshot)
    expect(initial.turn).toBe('white')
  })

  it('melaksanakan castling dan menghapus hak castling', () => {
    const board = createEmptyBoard()
    put(board, 'e1', 'white', 'king')
    put(board, 'h1', 'white', 'rook')
    put(board, 'e8', 'black', 'king')
    const state = position(board, 'white')
    state.castling = { ...state.castling, whiteKing: true }

    const castle = legalMoves(state, square('e1')).find((item) => item.castle === 'king')
    expect(castle).toBeDefined()
    const after = applyMove(state, castle!)
    expect(after.board[0][6]).toEqual({ color: 'white', type: 'king' })
    expect(after.board[0][5]).toEqual({ color: 'white', type: 'rook' })
    expect(after.castling.whiteKing).toBe(false)
  })

  it('menangkap en passant tanpa mengubah papan asal', () => {
    const afterE4 = move(createInitialGame(), 'e2', 'e4')
    const afterA6 = move(afterE4, 'a7', 'a6')
    const afterE5 = move(afterA6, 'e4', 'e5')
    const afterD5 = move(afterE5, 'd7', 'd5')

    const capture = legalMoves(afterD5, square('e5')).find((item) => item.enPassant)
    expect(capture).toBeDefined()
    const afterCapture = applyMove(afterD5, capture!)
    expect(afterCapture.board[4][3]).toBeNull()
    expect(afterCapture.board[5][3]).toEqual({ color: 'white', type: 'pawn' })
    expect(afterD5.board[4][3]).toEqual({ color: 'black', type: 'pawn' })
  })

  it('mempromosikan pawn', () => {
    const board = createEmptyBoard()
    put(board, 'a7', 'white', 'pawn')
    put(board, 'h1', 'white', 'king')
    put(board, 'h8', 'black', 'king')
    const state = position(board, 'white')

    const promotion = legalMoves(state, square('a7')).find(
      (item) => item.promotion === 'queen',
    )
    expect(promotion).toBeDefined()
    expect(applyMove(state, promotion!).board[7][0]).toEqual({
      color: 'white',
      type: 'queen',
    })
  })

  it('mendeteksi skakmat dan stalemate', () => {
    const mate = withStatus(
      move(move(move(move(createInitialGame(), 'f2', 'f3'), 'e7', 'e5'), 'g2', 'g4'), 'd8', 'h4'),
    )
    expect(mate.status).toBe('checkmate')

    const board = createEmptyBoard()
    put(board, 'a8', 'black', 'king')
    put(board, 'c6', 'white', 'king')
    put(board, 'c7', 'white', 'queen')
    expect(gameStatus(position(board, 'black'))).toBe('stalemate')
  })
})

describe('utilitas', () => {
  it('membaca dan menulis nama kotak', () => {
    expect(square('e4')).toEqual({ file: 4, rank: 3 })
    expect(parseSquare('z9')).toBeNull()
  })

  it('papan awal memiliki 32 bidak', () => {
    expect(createInitialBoard().flat().filter(Boolean)).toHaveLength(32)
  })
})
