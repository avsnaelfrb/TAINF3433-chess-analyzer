# AGENT.md — Backend (server/)

Kamu adalah **agent BE**. Tanggung jawabmu hanya isi folder `server/`.

## Sebelum mulai

Baca `../PROJECT.md` dulu — itu sumber kebenaran spesifikasi. Catatan: di
dokumen itu folder ini bernama `backend/` dan frontend bernama `frontend/`;
padahal di repo ini keduanya bernama **`server/`** dan **`client/`**. Semua
path relatif di dokumen dibaca dengan pemetaan itu.

## Milikmu

- `app/config.py` — path artifact, `MODEL_VERSION`, `CORS_ORIGINS`, env
  `CHESS_*`.
- `app/pattern.py` — 23 `ATTACK_THEMES`, urutan `ATTACK_CLASSES`, filter baris,
  vektor label, split per `GameId`, `load_pattern_dataset`.
- `app/pattern_features.py` — 46 fitur dari FEN (sudut pandang hitam),
  `PatternFeatureExtractor`.
- `app/pattern_training.py`, `train_pattern.py`, `prepare_pattern_dataset.py`
  — pipeline, metrik AP/F1, CLI `--sample`.
- `app/api.py`, `main.py` — Pydantic schema, `PatternClassifier`,
  `create_app(pattern_classifier=...)`, health check, CORS, logging.
- `tests/` — test dataset/label/split, fitur, training, API.
- `pyproject.toml`, `uv.lock` (generate dengan `uv`), `.python-version`,
  `.gitignore`. `models/` dan `datasets/` adalah hasil generate, gitignored.

Jangan menyentuh `.git/` di folder ini, `../client/`, atau `../PROJECT.md`.

## Kontrak dengan FE — jangan diubah sendiri

- `GET /api/health` → `200 {"status":"ok"}`.
- `POST /api/analyze-pattern` dengan `{"fen": "..."}` →
  `200 {"labels":[{"label":"fork","probability":0.61}, ...],
  "model_version":"0.1.0"}`.
- `labels` wajib berisi **ke-23 motif**, diurutkan probabilitas tertinggi
  duluan. Probabilitas independen per motif, bukan softmax. FE yang memilih
  menampilkan 2 teratas — jangan ikut memotong di server.
- FEN invalid / body salah → `422`; artifact hilang, korup, atau daftar fitur
  basi → `503`. Server tetap hidup, tidak crash.
- CORS: `http://localhost:5173` dan `http://127.0.0.1:5173`.
- `create_app` harus bisa menerima classifier tiruan agar test API tidak
  butuh artifact asli.
- Kalau kontrak perlu berubah, laporkan ke agent orchestra; jangan
  menyesuaikan BE saja.

## Batasan model

FEN = posisi, bukan langkah. Jangan pakai ply/fullmove/halfmove sebagai fitur
atau target, jangan softmax, jangan `class_weight="balanced"`, jangan
klasifikasi fase. Dataset `Lichess/chess-puzzles` filter `FEN.split()[1] == "w"`
+ `Popularity >= 50`, split per `GameId`. Jangan terapkan `Moves[0]` ke FEN.
Pakai AP per kelas + macro/micro-F1, bukan accuracy sebagai metrik utama.

## Perintah

```bash
uv sync
uv run python prepare_pattern_dataset.py --limit 200000  # opsional
uv run python train_pattern.py --sample 200000
uv run uvicorn main:app --reload  # http://localhost:8000
uv run pytest
```

## Selesai bila

`uv run pytest` hijau; training menghasilkan `models/pattern.joblib` dan
`models/pattern_metrics.json`; health, prediksi 23 label, `422`, dan `503`
(serta CORS) teruji; dan tanpa artifact endpoint balas `503` tanpa mematikan
server.
