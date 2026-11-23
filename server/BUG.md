# BUG.md — Backend (server/)

Daftar perbaikan yang masih harus dikerjakan agent BE. Ini bukan spesifikasi;
rujukan tetap `../PROJECT.md` dan `AGENT.md`.

## Bug / perbaikan yang perlu dilakukan

- [ ] `app/config.py` — `FALLBACK_MODEL_VERSION` (env
      `CHESS_PATTERN_MODEL_VERSION`) didefinisikan tetapi tidak dipakai di
      mana pun. Putuskan: pakai sebagai fallback saat artifact tidak punya
      versi, atau hapus kalau versi memang selalu berasal dari artifact.
- [ ] `pyproject.toml` — `joblib` dipakai langsung di `app/api.py` dan
      `app/pattern_training.py`, tetapi tidak dideklarasikan sebagai dependency;
      saat ini hanya datang transitif dari scikit-learn. Tambahkan ke
      `dependencies` agar tidak rapuh saat dependency berubah.

## Catatan

_Belum ada catatan tambahan._
