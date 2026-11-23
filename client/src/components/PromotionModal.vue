<script setup lang="ts">
import type { PromotionType } from '../types/chess'

const emit = defineEmits<{
  select: [piece: PromotionType]
  cancel: []
}>()

const choices: PromotionType[] = ['queen', 'rook', 'bishop', 'knight']
const labels: Record<PromotionType, string> = {
  queen: 'Ratu',
  rook: 'Benteng',
  bishop: 'Gajah',
  knight: 'Kuda',
}
</script>

<template>
  <div class="modal-backdrop" role="presentation" @click.self="emit('cancel')">
    <div class="modal" role="dialog" aria-modal="true" aria-label="Pilih promosi bidak">
      <h3>Promosi bidak</h3>
      <div class="promotion-options">
        <button
          v-for="choice in choices"
          :key="choice"
          type="button"
          class="promotion-option"
          @click="emit('select', choice)"
        >
          {{ labels[choice] }}
        </button>
      </div>
      <button type="button" class="text-button" @click="emit('cancel')">Batal</button>
    </div>
  </div>
</template>
