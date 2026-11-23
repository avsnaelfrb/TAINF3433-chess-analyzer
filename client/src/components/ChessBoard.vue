<script setup lang="ts">
import { computed, ref } from 'vue'
import { sameSquare } from '../lib/chess/board'
import { PIECE_ICONS } from '../lib/chess/constants'
import { kingSquare } from '../lib/chess/engine'
import { squareName } from '../lib/chess/notation'
import type { Board, Color, Move, Piece, PromotionType, Square } from '../types/chess'
import PromotionModal from './PromotionModal.vue'

const props = defineProps<{
  board: Board
  turn: Color
  legalMoves: Move[]
  lastMove: Move | null
  inCheck: boolean
}>()

const emit = defineEmits<{ play: [move: Move] }>()

const selected = ref<Square | null>(null)
const pendingMove = ref<Move | null>(null)

const rows = computed(() =>
  Array.from({ length: 8 }, (_, index) => {
    const rank = 7 - index
    return Array.from({ length: 8 }, (_, file) => ({ file, rank }))
  }),
)
const targets = computed(() =>
  props.legalMoves.filter(
    (move) => selected.value !== null && sameSquare(move.from, selected.value),
  ),
)
const checkedKing = computed(() =>
  props.inCheck ? kingSquare(props.board, props.turn) : null,
)

function isLight(cell: Square): boolean {
  return (cell.file + cell.rank) % 2 === 1
}

function isTarget(cell: Square): boolean {
  return targets.value.some((move) => sameSquare(move.to, cell))
}

function pieceIn(cell: Square): Piece | null {
  return props.board[cell.rank][cell.file]
}

function iconIn(cell: Square): string | null {
  const piece = pieceIn(cell)
  return piece ? PIECE_ICONS[piece.color][piece.type] : null
}

function squareLabel(cell: Square): string {
  const piece = pieceIn(cell)
  return piece ? `${squareName(cell)}, ${piece.color} ${piece.type}` : squareName(cell)
}

function onSquareClick(cell: Square): void {
  if (pendingMove.value) return

  if (selected.value) {
    const matching = targets.value.filter((move) => sameSquare(move.to, cell))
    if (matching.length > 0) {
      const move = matching[0]
      if (matching.some((item) => item.promotion)) {
        pendingMove.value = move
      } else {
        emit('play', move)
        selected.value = null
      }
      return
    }
    if (sameSquare(selected.value, cell)) {
      selected.value = null
      return
    }
  }

  const piece = props.board[cell.rank][cell.file]
  selected.value = piece?.color === props.turn ? cell : null
}

function choosePromotion(piece: PromotionType): void {
  if (pendingMove.value) emit('play', { ...pendingMove.value, promotion: piece })
  pendingMove.value = null
  selected.value = null
}

function cancelPromotion(): void {
  pendingMove.value = null
}
</script>

<template>
  <div class="board-frame">
    <div v-for="(row, index) in rows" :key="index" class="board-row">
      <button
        v-for="cell in row"
        :key="squareName(cell)"
        type="button"
        class="square"
        :class="{
          light: isLight(cell),
          dark: !isLight(cell),
          selected: selected && sameSquare(selected, cell),
          target: isTarget(cell),
          'last-origin': lastMove && sameSquare(lastMove.from, cell),
          'last-target': lastMove && sameSquare(lastMove.to, cell),
          checked: checkedKing && sameSquare(checkedKing, cell),
        }"
        :aria-label="squareLabel(cell)"
        @click="onSquareClick(cell)"
      >
        <span v-if="pieceIn(cell)" class="piece" :class="pieceIn(cell)?.color">
          {{ iconIn(cell) }}
        </span>
        <span v-if="isTarget(cell)" class="target-dot" aria-hidden="true" />
      </button>
    </div>
  </div>

  <PromotionModal
    v-if="pendingMove"
    @select="choosePromotion"
    @cancel="cancelPromotion"
  />
</template>
