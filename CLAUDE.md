# Vision (Raspberry Pi 5 — Python)

Ortak kurallar ve Agent OS düzeni: üst klasördeki çatı repo `../CLAUDE.md` (Claude onu da otomatik okur). Ürün planı: `../agent-os/product/`.

## Bu repoya özel

- Kod **Python 3.12 (laptop) ve 3.13 (Pi, Raspberry Pi OS Trixie)** ikisinde de çalışmalı; 3.13'e özgü söz dizimi kullanma.
- Repo içi ortam: `.venv/` (`--system-site-packages`; Gazebo ve picamera2 apt'den gelir).
- Commit/PR öncesi: `.venv/bin/ruff format . && .venv/bin/ruff check . && .venv/bin/pytest -q`
- Bağımlılıklar `requirements/` altında **sabit sürümlüdür**. Yeni paket sabit sürümle eklenir ve hem cp312/x86_64 hem cp313/aarch64 hazır paketi olmalıdır.
- Raspberry Pi'ye **sadece bu repo** klonlanır: `src/` asla `../` (çatı repo, `Autopilot`) yoluna başvurmaz.
- Zorunlu CI: `ci (3.12)`, `ci (3.13)`. Kurulum: `README.md`.
