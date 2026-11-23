import { computed, ref } from 'vue'
import { sameSquare } from '../lib/chess/board'
import {
  applyMove,
  createInitialGame,
  legalMoves as findLegalMoves,
  withStatus,
} from '../lib/chess/engine'
import { toFen } from '../lib/chess/fen'
import { moveNotation } from '../lib/chess/notation'
import type { GameSnapshot, GameState, Move } from '../types/chess'

interface HistoryEntry {
  snapshot: GameSnapshot
  notation: string
  lastMove: Move
}

function snapshot(state: GameState): GameSnapshot {
  return {
    board: state.board,
    turn: state.turn,
    castling: state.castling,
    enPassant: state.enPassant,
    ply: state.ply,
  }
}

export function useChess() {
  const game = ref<GameState>(createInitialGame())
  const history = ref<HistoryEntry[]>([])

  const board = computed(() => game.value.board)
  const turn = computed(() => game.value.turn)
  const status = computed(() => game.value.status)
  const fen = computed(() => toFen(game.value))
  const legalMoves = computed(() => findLegalMoves(game.value))
  const inCheck = computed(
    () => status.value === 'check' || status.value === 'checkmate',
  )
  const moveLog = computed(() => history.value.map((entry) => entry.notation))
  const lastMove = computed(
    () => history.value[history.value.length - 1]?.lastMove ?? null,
  )
  const canUndo = computed(() => history.value.length > 0)

  function play(move: Move): boolean {
    const chosen = legalMoves.value.find(
      (candidate) =>
        sameSquare(candidate.from, move.from) &&
        sameSquare(candidate.to, move.to) &&
        candidate.promotion === move.promotion &&
        candidate.castle === move.castle &&
        candidate.enPassant === move.enPassant,
    )
    if (!chosen) return false

    const target = game.value.board[chosen.to.rank][chosen.to.file]
    history.value.push({
      snapshot: snapshot(game.value),
      notation: moveNotation(chosen, chosen.enPassant || target !== null),
      lastMove: chosen,
    })
    game.value = withStatus(applyMove(game.value, chosen))
    return true
  }

  function undo(): void {
    const previous = history.value.pop()
    if (!previous) return
    game.value = withStatus(previous.snapshot)
  }

  function reset(): void {
    game.value = createInitialGame()
    history.value = []
  }

  return {
    board,
    turn,
    status,
    fen,
    legalMoves,
    inCheck,
    moveLog,
    lastMove,
    canUndo,
    play,
    undo,
    reset,
  }
}
