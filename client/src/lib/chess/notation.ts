import type { Move, PromotionType, Square } from '../../types/chess'
import { FILES } from './constants'

const PROMOTION_NOTATION: Record<PromotionType, string> = {
  queen: 'Q',
  rook: 'R',
  bishop: 'B',
  knight: 'N',
}

export function squareName(square: Square): string {
  return `${FILES[square.file]}${square.rank + 1}`
}

export function parseSquare(name: string): Square | null {
  const match = /^([a-h])([1-8])$/.exec(name)
  if (!match) return null
  return {
    file: FILES.indexOf(match[1] as (typeof FILES)[number]),
    rank: Number(match[2]) - 1,
  }
}

export function moveNotation(move: Move, captured = false): string {
  if (move.castle === 'king') return 'O-O'
  if (move.castle === 'queen') return 'O-O-O'
  const separator = captured || move.enPassant ? 'x' : '-'
  const promotion = move.promotion ? `=${PROMOTION_NOTATION[move.promotion]}` : ''
  return `${squareName(move.from)}${separator}${squareName(move.to)}${promotion}`
}
