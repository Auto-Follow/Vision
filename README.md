# Vision

Auto-Follow tezi: **Raspberry Pi 5** üzerinde çalışan görüntü işleme ve Pixhawk 6C ile iletişim yazılımı.

PX4 tarafı ayrı repodadır: [`Auto-Follow/Autopilot`](https://github.com/Auto-Follow/Autopilot) (PX4 v1.17.0, kilitli).

> **Durum:** İskelet. Görüntü işleme yöntemi ve Pi ↔ Pixhawk arayüzü (ICD) **henüz kesinleşmedi**. Özellikler Agent OS spec'leriyle eklenecek.

## Hedef ortamlar
| Ortam | Python | Not |
|---|---|---|
| Laptop (Ubuntu 24.04) | 3.12 | Geliştirme + Gazebo Harmonic simülasyonu |
| Raspberry Pi 5 | 3.13 | Raspberry Pi OS (64-bit) masaüstlü, Debian 13 Trixie — imaj `2026-09-15-raspios-trixie-arm64.img.xz` |

Kod **Python 3.12 ve 3.13**'te çalışacak şekilde yazılır (3.13'e özgü söz dizimi kullanılmaz); CI iki sürümü de test eder.

## Kurulum
### Laptop
Klasör yapısı herkeste aynıdır: `~/Desktop/Projects/Auto-Follow/{Autopilot,Vision}` (Autopilot kurulumu: [`TEZ_README.md`](https://github.com/Auto-Follow/Autopilot/blob/main/TEZ_README.md)).
```bash
mkdir -p ~/Desktop/Projects/Auto-Follow && cd ~/Desktop/Projects/Auto-Follow
git clone https://github.com/Auto-Follow/Vision.git && cd Vision
python3 -m venv --system-site-packages .venv      # Gazebo Python bağları (apt) görünsün diye
.venv/bin/pip install -r requirements/laptop.txt
.venv/bin/pip install -e . --no-deps
.venv/bin/pytest -q
```
Gazebo kamera erişimi için (bir kere): `sudo apt install python3-gz-transport13 python3-gz-msgs10`

### Raspberry Pi 5
İşletim sistemi: **Raspberry Pi OS (64-bit), masaüstlü** — `2026-09-15-raspios-trixie-arm64.img.xz`
(sha256 `61d95799550aac32788bb3cacc3d471dcc860f8053ce989dec4aecc388b799dd`). Raspberry Pi Imager'da listeden değil **"Use custom"** ile bu dosya yazılır.
```bash
sudo apt install -y python3-picamera2 git     # Pi kamera kütüphanesi apt'den (pip ile değil)
mkdir -p ~/Desktop/Projects/Auto-Follow && cd ~/Desktop/Projects/Auto-Follow   # laptopla aynı yol
git clone https://github.com/Auto-Follow/Vision.git && cd Vision
python3 -m venv --system-site-packages .venv   # picamera2 (apt) görünsün diye
.venv/bin/pip install -r requirements/pi.txt
.venv/bin/pip install -e . --no-deps
```

## Bağımlılıklar (sabit sürümler)
| Dosya | Nerede |
|---|---|
| `requirements/common.txt` | Her yerde: NumPy 2.4.6, pymavlink, pyserial, PyYAML |
| `requirements/laptop.txt` | Laptop: + OpenCV (GUI), pytest, ruff, MAVProxy |
| `requirements/pi.txt` | Pi: + OpenCV (headless) |
| `requirements/ci.txt` | GitHub Actions |

Yeni paket: sabit sürümle eklenir; hem **Python 3.12/x86_64** (laptop) hem **Python 3.13/aarch64** (Pi) için hazır paketi olmalı.

## Kurallar
- `main`'e doğrudan push yok: branch → PR → en az 1 onay → squash merge.
- CI (ruff + pytest, Python 3.12 ve 3.13) yeşil olmadan birleştirilmez.
- Commit öncesi: `.venv/bin/ruff format . && .venv/bin/ruff check . && .venv/bin/pytest -q`
- Video, log, veri seti, model ağırlığı repoya girmez.

## Agent OS v2.1.1
Kurulu: `agent-os/` + `.claude/` — `auto-follow` profili (PX4 reposundaki `tez/agent-os/profiles/auto-follow/`).
Komutlar: `/plan-product`, `/shape-spec`, `/write-spec`, `/create-tasks`, `/implement-tasks`, `/orchestrate-tasks`.

Yeniden derlemek için (Vision klasöründe; `Autopilot` reposu yan klasörde klonlu olmalı):
```bash
../Autopilot/tez/env/install-agent-os.sh
echo y | ~/agent-os/scripts/project-install.sh --re-install --profile auto-follow
```
`agent-os/product/roadmap.md`'yi sadece proje lideri günceller.
