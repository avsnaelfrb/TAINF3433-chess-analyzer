# BUG.md — Frontend (client/)

Daftar perbaikan yang masih harus dikerjakan agent FE. Ini bukan spesifikasi;
rujukan tetap `../PROJECT.md` dan `AGENT.md`.

## Bug / perbaikan yang perlu dilakukan

<!-- Belum ada temuan. -->

## Catatan (bukan bug, belum perlu dikerjakan)

- `PROJECT.md` §3 mencantumkan `PlayerCard.vue`, `StatusPanel.vue`, dan
  `MoveHistory.vue`. Ketiganya saat ini di-inline di `App.vue`. Masih sesuai
  `AGENT.md` yang menyebut `src/components/*` secara umum — tidak perlu dipecah
  tanpa kebutuhan nyata.
- `package.json` masih bawaan template. Deno memakai `deno.json`; jangan pakai
  npm/yarn untuk menambah dependency.
