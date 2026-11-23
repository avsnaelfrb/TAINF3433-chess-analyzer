import { describe, expect, it } from 'vitest'
import { useChess } from '../src/composables/useChess'
import { INITIAL_FEN } from '../src/lib/chess/fen'
import { parseSquare } from '../src/lib/chess/notation'

function from(name: string) {
  const square = parseSquare(name)
  if (!square) throw new Error(`Invalid square: ${name}`)
  return square
}

describe('useChess', () => {
  it('memainkan langkah, undo, lalu reset', () => {
    const game = useChess()
    expect(game.fen.value).toBe(INITIAL_FEN)
    expect(game.canUndo.value).toBe(false)

    expect(game.play({ from: from('e2'), to: from('e4') })).toBe(true)
    expect(game.turn.value).toBe('black')
    expect(game.moveLog.value).toEqual(['e2-e4'])
    expect(game.canUndo.value).toBe(true)

    game.undo()
    expect(game.fen.value).toBe(INITIAL_FEN)
    expect(game.moveLog.value).toEqual([])

    game.play({ from: from('e7'), to: from('e5') })
    game.reset()
    expect(game.fen.value).toBe(INITIAL_FEN)
    expect(game.turn.value).toBe('white')
  })

  it('menolak langkah ilegal', () => {
    const game = useChess()
    expect(game.play({ from: from('e2'), to: from('e5') })).toBe(false)
    expect(game.fen.value).toBe(INITIAL_FEN)
  })
})
