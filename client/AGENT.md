# AGENT.md — Frontend (client/)

Kamu adalah **agent FE**. Tanggung jawabmu hanya isi folder `client/`.

## Sebelum mulai

Baca `../PROJECT.md` dulu — itu sumber kebenaran spesifikasi. Dokumen itu
memakai nama folder asli: **`client/`** = frontend / FE (folder kamu), dan
`server/` = backend / BE. Semua path di sana sudah bisa dipakai langsung.

## Milikmu

- `src/lib/chess/*` — aturan catur murni (pseudo/legal move, skak, undo,
  castling, promosi) dan pembuatan FEN. Tanpa Vue, tanpa import API.
- `src/types/chess.ts`, `src/composables/useChess.ts` — state reaktif, aksi,
  `fen` computed (`halfmove_clock = 0`, `fullmove_number = floor(ply/2)+1`).
- `src/api/pattern.ts` — `classifyPattern(fen, signal?)`, base URL `/api`
  (override `VITE_API_BASE`), timeout 15 detik, `AbortSignal`, `ApiError`
  dengan `status` (`0` = gagal jaringan).
- `src/components/*`, `src/App.vue`, `src/style.css` — papan yang bisa
  dimainkan (gerakan legal, giliran, skak/skakmat, undo/reset) dan panel hasil.
- `src/main.ts`, `index.html`, `vite.config.ts` (plugin Vue + proxy `/api` ke
  `http://localhost:8000`).
- `deno.json` (task `dev`/`test`/`build`/`preview`), `deno.lock`, `tests/`.
  `package.json` dan `node_modules/` yang ada sekarang adalah bawaan template;
  jangan pakai npm/yarn untuk menambah dependency.

## Kontrak dengan BE — jangan diubah sendiri

- Kirim `POST /api/analyze-pattern` dengan `{"fen": "..."}`, FEN posisi
  **saat ini apa adanya**, giliran putih. Tidak boleh dimodifikasi.
- Request hanya aktif saat `turn === 'white'` (distribusi training BE).
- BE balas 23 label, sudah terurut probabilitas turun. FE cukup tampilkan
  **2 teratas** dengan catatan "eksperimental" — ini batasan tampilan, bukan
  alasan untuk meminta BE mengirim lebih sedikit.
- `422` (FEN/body invalid), `503` (artifact model belum ada), dan gagal
  jaringan ditampilkan sebagai pesan biasa; aplikasi tidak boleh crash.
- Hasil direset setiap posisi berubah; request lama dibatalkan.

## Dilarang

- Menyentuh `../server/`, `../PROJECT.md`, atau kontrak HTTP di atas. Kalau
  kontrak perlu berubah, laporkan ke agent orchestra, jangan diam-diam
  menyesuaikan salah satu sisi.
- Menambah fitur di luar spec: klasifikasi fase, engine/Stockfish, bot,
  autentikasi, riwayat analisis, atau menilai kualitas langkah.

## Perintah

```bash
deno install
deno task dev      # http://localhost:5173
deno task test
deno task build
```

## Selesai bila

`deno task test` dan `deno task build` hijau; test mencakup pembuatan FEN,
client API (payload/respons/error/abort), dan gating giliran putih; alur manual
dari papan sampai panel berfungsi dengan backend di `localhost:8000`, termasuk
saat backend mati.
