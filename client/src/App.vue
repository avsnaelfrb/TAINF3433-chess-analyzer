<script setup lang="ts">
import { computed } from 'vue'
import ChessBoard from './components/ChessBoard.vue'
import GameControls from './components/GameControls.vue'
import PatternPanel from './components/PatternPanel.vue'
import { useChess } from './composables/useChess'

const {
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
} = useChess()

const statusText = computed(() => {
  switch (status.value) {
    case 'check':
      return 'Skak'
    case 'checkmate':
      return 'Skakmat'
    case 'stalemate':
      return 'Stalemate'
    default:
      return 'Permainan berjalan'
  }
})

const turnText = computed(() => (turn.value === 'white' ? 'Putih' : 'Hitam'))
</script>

<template>
  <main class="app-shell">
    <header class="app-header">
      <h1>Chess Pattern Analyzer</h1>
      <p>Pilih langkah di papan, lalu minta prediksi motif dari posisi saat ini.</p>
    </header>

    <div class="game-layout">
      <section class="board-column">
        <div class="game-meta">
          <span>Giliran: <strong>{{ turnText }}</strong></span>
          <span>Status: <strong>{{ statusText }}</strong></span>
        </div>

        <ChessBoard
          :board="board"
          :turn="turn"
          :legal-moves="legalMoves"
          :last-move="lastMove"
          :in-check="inCheck"
          @play="play"
        />

        <GameControls :can-undo="canUndo" @undo="undo" @reset="reset" />

        <div class="move-log">
          <h2>Riwayat langkah</h2>
          <ol v-if="moveLog.length > 0">
            <li v-for="(notation, index) in moveLog" :key="index">{{ notation }}</li>
          </ol>
          <p v-else class="muted">Belum ada langkah.</p>
        </div>

        <details class="fen-details">
          <summary>FEN saat ini</summary>
          <code>{{ fen }}</code>
        </details>
      </section>

      <PatternPanel :fen="fen" :turn="turn" />
    </div>
  </main>
</template>
