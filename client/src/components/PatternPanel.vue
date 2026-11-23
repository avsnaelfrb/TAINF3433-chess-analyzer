<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { ApiError, classifyPattern, type PatternLabel } from '../api/pattern'
import type { Color } from '../types/chess'

type PanelState = 'idle' | 'loading' | 'success' | 'error'

const props = defineProps<{ fen: string; turn: Color }>()

const state = ref<PanelState>('idle')
const labels = ref<PatternLabel[]>([])
const error = ref('')
let controller: AbortController | null = null
let requestId = 0

const isWhiteTurn = computed(() => props.turn === 'white')
const canAnalyze = computed(() => isWhiteTurn.value && state.value !== 'loading')

function reset(): void {
  requestId++
  controller?.abort()
  controller = null
  labels.value = []
  error.value = ''
  state.value = 'idle'
}

watch([() => props.fen, () => props.turn], reset)
onUnmounted(reset)

async function analyze(): Promise<void> {
  if (!canAnalyze.value) return
  reset()
  const id = ++requestId
  const active = new AbortController()
  controller = active
  state.value = 'loading'

  try {
    const result = await classifyPattern(props.fen, active.signal)
    if (id !== requestId) return
    labels.value = result.labels.slice(0, 2)
    state.value = 'success'
  } catch (cause) {
    if (id !== requestId || active.signal.aborted) return
    error.value = cause instanceof ApiError ? cause.message : 'Analisis gagal.'
    state.value = 'error'
  } finally {
    if (id === requestId) controller = null
  }
}

function readable(label: string): string {
  return label.replace(/([a-z])([A-Z])/g, '$1 $2')
}

function percent(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}
</script>

<template>
  <section class="panel">
    <div class="panel-heading">
      <h2>Analisis motif</h2>
      <span class="badge">eksperimental</span>
    </div>

    <p v-if="!isWhiteTurn" class="hint">
      Analisis hanya tersedia saat giliran putih.
    </p>

    <button type="button" class="primary" :disabled="!canAnalyze" @click="analyze">
      {{ state === 'loading' ? 'Menganalisis…' : 'Analisis posisi' }}
    </button>

    <p v-if="state === 'idle' && isWhiteTurn" class="muted">
      Siap menganalisis posisi ini.
    </p>
    <p v-if="state === 'loading'" class="muted" role="status">Menghubungi model…</p>

    <ol v-if="state === 'success'" class="result-list">
      <li v-for="item in labels" :key="item.label">
        <span>{{ readable(item.label) }}</span>
        <strong>{{ percent(item.probability) }}</strong>
      </li>
    </ol>
    <p v-if="state === 'success'" class="note">
      Dua motif teratas dari 23 label. Probabilitas belum terkalibrasi.
    </p>

    <p v-if="state === 'error'" class="error" role="alert">{{ error }}</p>
  </section>
</template>
