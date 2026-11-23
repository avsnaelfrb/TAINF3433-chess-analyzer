<script setup lang="ts">
defineProps<{ canUndo: boolean }>()

const emit = defineEmits<{
  undo: []
  reset: []
}>()
</script>

<template>
  <div class="controls">
    <button type="button" :disabled="!canUndo" @click="emit('undo')">Undo</button>
    <button type="button" @click="emit('reset')">Reset</button>
  </div>
</template>
