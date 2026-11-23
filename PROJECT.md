# PROJECT.md — Chess Pattern Analyzer

Dokumen ini adalah **spesifikasi kerja** untuk project yang akan dibangun.
Agent diharapkan membaca ini lebih dulu, lalu mengimplementasikan sesuai
kontrak di bawah. Fokusnya **satu model saja**: analisis pola/motif taktis
dari posisi catur. Tidak ada klasifikasi fase, tidak ada engine eksternal.

> **Konvensi penamaan:** BE / backend = folder `server/`; FE / frontend =
> folder `client/`. Kata "backend" dan "frontend" di dokumen ini selalu
> merujuk ke peran, bukan ke nama folder. Semua path yang tertulis sudah
> memakai nama folder asli di repo.

---

## 1. Tujuan & scope

Bangun aplikasi yang menerima **FEN catur** dan memprediksi **motif serangan
hitam** yang mungkin muncul dari posisi tersebut. Model bersifat
**multi-label**: satu posisi bisa memiliki beberapa motif sekaligus.

Alur utama:

```
[papan catur di frontend] --FEN--> POST /api/analyze-pattern
        --> [validasi + ekstraksi fitur] --> [model multi-label]
        --> [{label, probability}, ...] --> [panel hasil analisis]
```

### Yang harus ada

- Sumber FEN: papan catur yang bisa dimainkan (minimal: gerakan legal,
  giliran, skak/skakmat, undo/reset) agar pengguna bisa menghasilkan posisi.
- Model ML multi-label untuk 23 motif taktis.
- Endpoint HTTP untuk prediksi, plus health check.
- Panel frontend yang menampilkan hasil prediksi.
- Pipeline training yang menghasilkan artifact model + metrik.
- Test untuk data/label, fitur, training, dan API.

### Non-goals (jangan dibangun)

- Klasifikasi fase permainan (`opening` / `middlegame` / `endgame`).
- Label berbasis nomor langkah/putaran (ply, fullmove, halfmove) sebagai
  target maupun fitur.
- Analisis kualitas langkah, centipawn loss, atau langkah terbaik/bot.
- Stockfish atau engine UCI lain.
- Autentikasi, riwayat analisis, queue/async, training dari dalam server.

---

## 2. Prinsip desain

- **FEN = posisi (state), bukan langkah (action).** Model hanya melihat satu
  posisi. Ia memprediksi *potensi* motif, bukan memastikan langkah
  berikutnya.
- **Multi-label, bukan multi-class.** Tiap motif punya probabilitas sendiri,
  tidak di-softmax dan tidak dijumlahkan menjadi 100%.
- **Ekstraksi fitur hidup di dalam pipeline** yang diserialisasi bersama
  model. Training dan serving memakai kode yang sama → tidak ada drift.
- **Gagal dengan anggun.** Tanpa artifact model, server tetap hidup dan
  endpoint prediksi mengembalikan `503`. FEN invalid → `422`.
- **Pisahkan data, fitur, training, dan serving** ke modul berbeda supaya
  perubahan salah satu tidak merusak yang lain.

---

## 3. Struktur direktori target

```text
project-chess-analyzer/
├── server/                         # backend / BE
│   ├── main.py                     # entrypoint ASGI: `from app.api import app`
│   ├── train_pattern.py            # CLI training model
│   ├── prepare_pattern_dataset.py  # inspeksi/ekspor subset dataset hasil filter
│   ├── pyproject.toml              # dependency + konfigurasi pytest
│   ├── uv.lock                     # lockfile (uv)
│   ├── .python-version             # Python 3.14
│   ├── .gitignore                  # .venv, datasets/, models/*.joblib, cache
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py               # path & setting lewat env CHESS_*
│   │   ├── api.py                  # Pydantic schema + PatternClassifier + endpoint + create_app()
│   │   ├── pattern.py              # dataset HF, 23 label, filter, split per GameId
│   │   ├── pattern_features.py     # 46 fitur dari FEN (sudut pandang hitam)
│   │   └── pattern_training.py     # pipeline + evaluasi AP/F1 + CLI main()
│   ├── datasets/                   # cache subset opsional (gitignored)
│   ├── models/                     # pattern.joblib + pattern_metrics.json (gitignored)
│   └── tests/
│       ├── test_pattern.py         # filter dataset, label, split
│       ├── test_pattern_features.py# 46 fitur dari FEN
│       ├── test_pattern_training.py# smoke test training + metrik
│       └── test_api.py             # health + endpoint prediksi + batas input
└── client/                         # frontend / FE
    ├── deno.json, deno.lock        # package manager Deno 2 (task dev/build/test/preview)
    ├── vite.config.ts              # plugin Vue + proxy /api -> localhost:8000
    ├── index.html, src/main.ts     # entry
    ├── src/
    │   ├── App.vue                 # shell: papan + panel analisis
    │   ├── style.css               # tema, layout, responsif
    │   ├── types/chess.ts          # tipe domain (Color, Piece, Move, Castling, Snapshot)
    │   ├── lib/chess/              # logika catur murni, tanpa Vue (mudah di-test)
    │   │   ├── engine.ts           # pseudoMoves, applyMove, skak, langkah legal
    │   │   ├── board.ts            # buat/klon papan, castling awal
    │   │   ├── fen.ts              # state papan -> FEN; INITIAL_FEN
    │   │   ├── notation.ts         # nama kotak & notasi langkah
    │   │   └── constants.ts        # file papan, ikon bidak Unicode
    │   ├── api/pattern.ts          # client fetch + tipe respons + ApiError
    │   ├── composables/useChess.ts # state reaktif + aksi + computed fen
    │   └── components/
    │       ├── ChessBoard.vue      # grid papan, bidak, sorotan
    │       ├── PatternPanel.vue    # panel prediksi motif
    │       ├── PlayerCard.vue
    │       ├── StatusPanel.vue
    │       ├── MoveHistory.vue
    │       ├── GameControls.vue    # undo / reset
    │       └── PromotionModal.vue
    └── tests/                      # Vitest: logika game, pembuatan FEN, client API
```

`dist/`, `node_modules/`, `.venv/`, `__pycache__/` adalah generated files.

---

## 4. Backend — folder `server/` (BE)

### 4.1 Modul & tanggung jawab

| Modul | Isi wajib |
|---|---|
| `config.py` | `BASE_DIR`, path artifact, `MODEL_VERSION`, `CORS_ORIGINS`, env `CHESS_PATTERN_*` |
| `pattern.py` | `ATTACK_THEMES` (23 motif), `ATTACK_CLASSES` (urutan deterministik), `fen_white_to_move`, `attack_theme_labels`, `attack_label_vector/matrix`, `split_by_game_id`, `is_pattern_row`, `load_pattern_dataset` |
| `pattern_features.py` | `FEATURE_NAMES` (46), `extract_pattern_features(fen)`, `pattern_vector(fen)`, `PatternFeatureExtractor` (sklearn transformer) |
| `pattern_training.py` | `build_pipeline()`, `evaluate_multilabel()`, `main()` dengan argumen `--sample` |
| `api.py` | Pydantic request/response, `PatternClassifier`, `create_app(pattern_classifier=...)`, health check, middleware log request/response |
| `main.py` | `app = create_app()` + logging INFO |

Ketergantungan: `config → pattern → pattern_features → pattern_training →
artifact → api`. Modul tidak boleh saling mengimpor secara melingkar.

### 4.2 Kontrak HTTP

Base URL dev: `http://localhost:8000`.

| Endpoint | Request | Respons sukses |
|---|---|---|
| `GET /api/health` | — | `200 {"status":"ok"}` |
| `POST /api/analyze-pattern` | `{"fen": "..."}` | `200 {"labels":[{"label":"fork","probability":0.61}, ...], "model_version":"0.1.0"}` |

Aturan:

- `labels` berisi **ke-23 motif**, diurutkan dari probabilitas tertinggi.
- `probability` float `0.0`–`1.0`, independen per motif (bukan softmax).
- `model_version` dibaca dari artifact model.
- FEN invalid / body salah → `422 {"detail": "..."}`.
- Artifact belum ada, korup, atau daftar fitur basi → `503 {"detail": "..."}`
  tanpa mematikan server.
- CORS mengizinkan `http://localhost:5173` dan `http://127.0.0.1:5173`.
- `create_app(pattern_classifier=...)` harus menerima classifier tiruan agar
  test API tidak bergantung pada artifact asli.

### 4.3 Dataset & pelabelan

Sumber: `Lichess/chess-puzzles` lewat `datasets.load_dataset(...)`, diunduh ke
cache HuggingFace saat training pertama (bukan disimpan di repo).

Kolom dipakai: `FEN`, `Moves`, `Themes`, `GameId`, `Popularity`.

Filter baris:

- `FEN.split()[1] == "w"` → giliran putih, berarti solver puzzle = **hitam**.
  Ini menyelaraskan input training dengan FEN yang dikirim frontend.
- `Popularity >= 50`.
- Memiliki minimal satu motif dalam daftar `ATTACK_THEMES`.

Label: irisan `Themes` dengan 23 motif serangan/taktik:

```
fork, pin, skewer, discoveredAttack, xRayAttack, deflection, attraction,
clearance, interference, sacrifice, discoveredCheck, doubleCheck,
kingsideAttack, queensideAttack, attackingF2F7, backRankMate, exposedKing,
hangingPiece, trappedPiece, capturingDefender, advancedPawn, promotion, mate
```

Tema fase (`opening`/`middlegame`/`endgame`), panjang puzzle, keunggulan
(`crushing`/`advantage`), sumber (`master`), `defensiveMove`, `quietMove`,
`zugzwang` sengaja dibuang.

Split: **per `GameId`**, bukan per baris, supaya posisi dari game yang sama
tidak muncul di train dan test sekaligus. Default sample 200.000 baris
(setelah filter) untuk iterasi cepat; `--sample 0` untuk semua data.

> Jangan menerapkan `Moves[0]` ke FEN. Field `FEN` dataset sudah merupakan
> posisi satu ply *sebelum* puzzle; `Moves[0]` adalah blunder lawan yang
> memulai taktik.

### 4.4 Fitur & model

Semua 46 fitur dihitung dari FEN, **dari sudut pandang hitam**:

- Material & jumlah bidak.
- Posisi raja putih: file/rank, status castled, shield pion, file terbuka,
  bidak berat hitam di sekitar raja.
- Tekanan hitam: bidak putih yang diserang, menggantung, target fork,
  defender yang bisa ditangkap.
- Pin putih; geometri skewer, discovered attack, discovered check.
- Pion hitam maju/passed/promosi; celah baris belakang.
- Proksi mobilitas hitam dari simulasi giliran hitam pada salinan papan
  (jumlah langkah, skak, tangkapan, nilai tangkapan). Papan asli tidak diubah.

Model:

```
PatternFeatureExtractor -> StandardScaler -> OneVsRestClassifier(LogisticRegression(solver="liblinear"))
```

Tanpa `class_weight="balanced"` — bobot seimbang membuat motif langka
terlalu percaya diri pada posisi di luar distribusi training.

Metrik: **average precision (AP) per kelas**, macro/micro-F1. Jangan pakai
accuracy sebagai metrik utama (`mate` sekitar 44% dari label). Evaluasi juga
perlu menampilkan dukungan (support) tiap motif.

### 4.5 Training & artifact

```bash
uv sync
uv run python train_pattern.py --sample 200000   # iterasi cepat
uv run python train_pattern.py --sample 0        # seluruh data
```

Artifact (gitignored, harus di-generate ulang setelah clone):

- `models/pattern.joblib` → dict `{pipeline, classes, feature_names, model_version}`.
- `models/pattern_metrics.json` → metrik per motif + ringkasan.

Sebelum training, `prepare_pattern_dataset.py --limit 200000` bisa dipakai
untuk melihat jumlah baris hasil filter, distribusi motif, dan contoh baris.

### 4.6 Konfigurasi

| Env | Default | Fungsi |
|---|---|---|
| `CHESS_PATTERN_MODEL` | `models/pattern.joblib` | lokasi artifact |
| `CHESS_PATTERN_METRICS` | `models/pattern_metrics.json` | lokasi metrik |
| `CHESS_PATTERN_MODEL_VERSION` | `0.1.0` | versi fallback |
| `CHESS_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | origin yang diizinkan |
| `HF_TOKEN` | — | opsional, untuk rate limit HuggingFace |

Dependency: Python 3.14, `uv`, `fastapi[standard]`, `datasets>=5.1.0`,
`python-chess>=1.999`, `scikit-learn>=1.9.1`, `pytest` (dev).

---

## 5. Frontend — folder `client/` (FE)

### 5.1 Lapisan

- `lib/chess/*` — aturan catur dan pembuatan FEN murni, tanpa Vue, diuji
  terpisah.
- `composables/useChess.ts` — state reaktif permainan, aksi (langkah, undo,
  reset), dan `fen` computed. setting `halfmove_clock = 0`,
  `fullmove_number = floor(ply / 2) + 1`.
- `api/pattern.ts` — `classifyPattern(fen, signal?)` dengan base URL relatif
  `/api` (proxy Vite saat dev), override lewat `VITE_API_BASE`. Sertakan
  timeout 15 detik, `AbortSignal`, dan `ApiError` dengan `status` (0 = gagal
  jaringan).
- `PatternPanel.vue` — satu panel tanpa tab: terima prop `fen` dan `turn`,
  state idle/loading/sukses/error, tampilkan **2 motif teratas** dengan
  catatan "eksperimental".

### 5.2 Perilaku panel

- Tombol/request hanya aktif saat `turn === 'white'` (distribusi training).
- FEN yang dikirim adalah posisi saat ini, tanpa modifikasi.
- Hasil direset saat posisi berubah; request lama dibatalkan.
- Error `422` / `503` / jaringan ditampilkan sebagai pesan biasa.

### 5.3 Perintah

```bash
deno install
deno task dev      # http://localhost:5173
deno task test     # vitest
deno task build    # vue-tsc + vite build
```

Backend harus berjalan di `http://localhost:8000`; Vite mem-proxy `/api`.

---

## 6. Test & definisi selesai

Test backend minimal:

- filter baris, konversi `Themes` → vektor 23 label, split per `GameId`;
- ekstraksi 46 fitur dari beberapa FEN (termasuk posisi awal);
- smoke test pipeline + bentuk metrik;
- `GET /api/health`, prediksi sukses, FEN invalid `422`, artifact hilang `503`.

Test frontend minimal:

- pembuatan FEN dari state papan;
- client API (payload, respons, error, abort/timeout);
- panel hanya aktif saat giliran putih.

Pekerjaan dianggap selesai bila:

1. `uv run pytest` hijau.
2. `deno task test` dan `deno task build` hijau.
3. Training menghasilkan kedua artifact, dan metrik per motif tercatat.
4. `POST /api/analyze-pattern` dengan satu FEN giliran putih mengembalikan
   23 label terurut dari frontend hingga tampil di panel.
5. Tanpa artifact, endpoint balas `503` dan server tidak crash.

---

## 7. Cara menjalankan

Backend / BE (dari `server/`):

```bash
uv sync
uv run python train_pattern.py --sample 200000
uv run uvicorn main:app --reload       # http://localhost:8000
uv run pytest
```

Frontend / FE (dari `client/`):

```bash
deno install
deno task dev                          # http://localhost:5173
```

Alur uji manual: buka papan → pastikan giliran putih → minta analisis →
muncul beberapa motif + persen → ubah posisi → hasil lama hilang → matikan
backend → pesan error tampil, aplikasi tidak crash.

---

## 8. Risiko & batasan yang harus diingat

- Probabilitas **belum terkalibrasi** dan masih membawa prior dataset
  (`mate` dominan). Jangan sajikan top-1 sebagai vonis; tampilkan sebagai
  perkiraan eksperimental.
- Motif langka (`interference`, `clearance`, `capturingDefender`,
  `xRayAttack`) sulit dipelajari. Beri ambang tinggi atau sembunyikan bila
  perlu.
- Model melihat posisi statis, bukan langkah. Motif baru muncul setelah
  langkah berikutnya, jadi hasilnya bersifat potensi.
- FEN giliran hitam secara teknis bisa dikirim, tetapi di luar distribusi
  training — frontend yang membatasi.
- Duplikasi FEN antar-game bisa membuat metrik terlihat terlalu bagus;
  tetap pakai split per `GameId` dan laporkan evaluasi pada FEN unik.
- Fitur waktu (ply/fullmove/halfmove) **dilarang** dipakai: bukan tugas model
  ini dan menimbulkan label leakage.
- Artifact dan dataset tidak di-commit. Pastikan langkah training tercantum
  jelas sebelum endpoint dipakai.
- Unduhan dataset HuggingFace awal butuh koneksi (~1,1 GB cache); `HF_TOKEN`
  opsional.
