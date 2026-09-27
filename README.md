# Vision

Auto-Follow tezi: **Raspberry Pi 5** üzerinde çalışan görüntü işleme ve Pixhawk 6C ile iletişim yazılımı.

PX4 tarafı ayrı repodadır: [`Auto-Follow/Autopilot`](https://github.com/Auto-Follow/Autopilot) (PX4 v1.17.0, kilitli).

> **Durum:** İskelet. Görüntü işleme yöntemi, Pi ↔ Pixhawk arayüzü (ICD) ve Pi işletim sistemi **henüz kesinleşmedi**. Özellikler Agent OS spec'leriyle eklenecek.

## Hedef ortamlar
| Ortam | Python | Not |
|---|---|---|
| Laptop (Ubuntu 24.04) | 3.12 | Geliştirme + Gazebo Harmonic simülasyonu |
| Raspberry Pi 5 | 3.11 (Raspberry Pi OS) veya 3.12 (Ubuntu 24.04) | OS henüz seçilmedi |

Kod **Python 3.11 ile uyumlu** yazılır; CI iki sürümü de test eder.

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
```bash
python3 -m venv --system-site-packages .venv
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

Yeni paket: sabit sürümle, **Python 3.11 uyumlu** olarak eklenir (NumPy 2.5+ 3.12 istediği için 2.4.6'da sabit).

## Kurallar
- `main`'e doğrudan push yok: branch → PR → en az 1 onay → squash merge.
- CI (ruff + pytest, Python 3.11 ve 3.12) yeşil olmadan birleştirilmez.
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
