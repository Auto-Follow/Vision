# Görev Listesi: m10 — Piksel koordinatından body frame hedef vektörüne dönüşüm

## Genel Bakış

- Spec: `spec.md` · Gereksinimler: `planning/requirements.md` · Görsel yok (`planning/visuals/` boş).
- Repo: `Vision` (branch `ozellik/m10-piksel-body-frame`). Kod yalnızca bu repoya yazılır; `Autopilot/` ve çatı repoda dosya değişmez.
- Toplam: 7 görev grubu, 61 alt görev.

### Tüm görev grupları için geçerli kurallar

- Kod Python 3.12 (laptop) ve 3.13 (Pi) ile çalışır; 3.13'e özgü söz dizimi kullanılmaz. Tip ipuçları zorunlu, herkese açık fonksiyonlarda docstring (frame ve birim yazılır).
- `src/` hiçbir yerde `../` yoluna, çatı repoya veya `Autopilot/`'a başvurmaz. `src/` içinde Gazebo, picamera2 veya pymavlink importu olmaz.
- `requirements/` ve `.github/workflows/ci.yml` değişmez; yeni pip paketi (SciPy vb.) eklenmez. NumPy 2.4.6, OpenCV 5.0.0.93, PyYAML 6.0.3 kullanılır.
- Kodda `if simulation:` dalı olmaz; SITL ile Pi farkı yalnızca seçilen YAML profilidir.
- Modül, dosya, config ve script adları spec'te **öneridir** (`kamera_modeli.py`, `gorus_dogrultusu.py`, `config/kamera/`, `scripts/`). İşi yapan kişi değiştirebilir; değiştirirse Görev Grubu 7'de kaydeder. Ön ek dayatılmaz.
- Spec'in "Varsayımlar" bölümündeki maddeler (OpenCV optik frame, PX4 FRD, birimler, Gazebo FLU/ENU ↔ FRD, Gazebo intrinsics kuralı, bbox formatı) **varsayım olarak kalır**. Kodda ve docstring'lerde "varsayım (ortak spec madde 3/5 yazılınca güncellenecek)" diye işaretlenir, kesinleşmiş gibi sunulmaz.
- Her görev grubu bir doğrulama adımıyla biter: `.venv/bin/ruff format . && .venv/bin/ruff check . && .venv/bin/pytest -q` (CI dışı SITL kısımlarında ayrıca spec'teki elle çalıştırma).
- Her görev grubu, kontroller geçince ayrı bir commit ile kapanır: `2026-11-13-m10-piksel-body-frame: Görev grubu <N> — <ne yapıldı>`. Dosyalar **adıyla** eklenir (`git add -A` / `git add .` yok). Push, amend, rebase yapılmaz; `main`'de commit atılmaz.
- Kare, video, log ve model ağırlığı repoya girmez (kural 9).

## Görev Listesi

### Çekirdek: Kamera modeli

#### Görev Grubu 1: Kamera iç parametreleri, montaj ve camera → body rotasyonu
**Bağımlılıklar:** Yok

- [ ] 1.0 Kamera modeli veri sınıflarını ve montaj rotasyonunu tamamla
  - [ ] 1.1 `tests/test_kamera_modeli.py` (öneri ad) içinde 2–8 odaklı test yaz
    - Mevcut `tests/test_ortam.py` üslubu: düz pytest fonksiyonları, Türkçe `snake_case` adlar, dosya başında docstring
    - Geçerli iç parametrelerle nesne oluşur; geçersiz değerler (w veya h ≤ 0, fx veya fy ≤ 0, NaN/Inf, izin verilmeyen distorsiyon katsayı sayısı ör. 3) `ValueError` verir (`pytest.mark.parametrize` ile tek test)
    - Montaj açıları 0 iken: optik z → body (1, 0, 0), optik x → (0, 1, 0), optik y → (0, 0, 1)
    - Pitch = −90° iken optik eksen → (0, 0, 1); yaw = +90° iken optik eksen → (0, 1, 0)
    - İşaret kuralı: pozitif pitch optik ekseni yukarı kaldırır (sonuç z < 0)
    - Birkaç rastgele açı için rotasyon matrisi ortonormal ve determinantı +1
    - Donanım, Gazebo ve ağ kullanılmaz
  - [ ] 1.2 `src/vision/` altında kamera modeli modülünü oluştur (öneri `kamera_modeli.py`)
    - Mevcut `vision` paketine eklenir; `pyproject.toml` ve paket yapısı değişmez
  - [ ] 1.3 İç parametreler için değişmez (frozen) veri sınıfı yaz
    - Alanlar: çözünürlük (w, h) [piksel], fx, fy, cx, cy [piksel], OpenCV distorsiyon katsayıları (uzunluk 0, 4, 5, 8, 12 veya 14; boş = distorsiyon yok)
    - Oluşturulurken doğrulama: w, h > 0; fx, fy > 0; tüm değerler sonlu; katsayı sayısı izinli. Aksi halde hangi alanın hatalı olduğunu söyleyen `ValueError`
    - OpenCV'ye verilecek kamera matrisi ve katsayı dizisi `float64` olarak türetilebilir
  - [ ] 1.4 Montaj için değişmez veri sınıfı yaz
    - Alanlar: roll, pitch, yaw [rad] (kameranın body FRD'ye göre, ZYX sırası: önce yaw, sonra pitch, sonra roll) ve FRD öteleme [m]
    - Tüm değerler sonlu olmalı; değilse `ValueError`
    - Öteleme saklanır ama doğrultu hesabına girmez (docstring'de yazılır)
    - Gimbal desteği yoktur; kamera gövdeye sabittir
  - [ ] 1.5 camera (optik) → body FRD rotasyonunu NumPy ile hesapla
    - Toplam rotasyon = ZYX montaj rotasyonu ∘ sabit eksen eşlemesi (optik z → x, optik x → y, optik y → z)
    - Elde edilen matrisin ortonormal ve det = +1 olduğu kontrol edilir; SciPy kullanılmaz
    - Roll'ün pozitif yönü aynı FRD Euler kuralından türetilir ve docstring'de bilinen bir vektörle örneklenir (roll testi Görev Grubu 4'te)
    - Frame tanımları docstring'de "varsayım" olarak işaretlenir
  - [ ] 1.6 Yalnızca 1.1'deki testleri çalıştır: `.venv/bin/pytest -q tests/test_kamera_modeli.py`
  - [ ] 1.7 Doğrula: `.venv/bin/ruff format . && .venv/bin/ruff check . && .venv/bin/pytest -q`
  - [ ] 1.8 Commit: `2026-11-13-m10-piksel-body-frame: Görev grubu 1 — kamera modeli veri sınıfları ve montaj rotasyonu`
    - Yalnızca bu gruptaki dosyalar adıyla eklenir (ör. `src/vision/kamera_modeli.py`, `tests/test_kamera_modeli.py`)

**Kabul Kriterleri:**
- 1.1'deki testler geçer
- Geçersiz iç parametre ve montaj değerleri alan adını belirten `ValueError` üretir
- Sıfır açıda eksen eşlemesi ve pitch/yaw işaret kuralı testlerle sabitlenmiştir
- Rotasyon yalnızca NumPy ile hesaplanır, ortonormal ve det = +1'dir
- ruff ve tüm pytest yeşil, commit atılmış

### Config

#### Görev Grubu 2: YAML config profilleri ve yükleyici
**Bağımlılıklar:** Görev Grubu 1

- [ ] 2.0 SITL ve Pi config profillerini ve yükleme fonksiyonunu tamamla
  - [ ] 2.1 Config için 2–8 odaklı test yaz (öneri: `tests/test_kamera_modeli.py` içine ya da ayrı bir dosyaya)
    - SITL profili yüklenir; değerler formülle tutarlıdır: 1280×960, fx = fy = 640 / tan(1.74 / 2) ≈ 539.9 px, cx = 640, cy = 480, distorsiyon boş, montaj açıları 0, öteleme (0.12, −0.03, −0.242) m, `yer_tutucu` her iki bölümde `false`. Sabitler testte **değer olarak** yazılır, SDF okunmaz
    - SITL profili yüklenince uyarı yoktur (`caplog`)
    - Pi profili yüklenir; `kamera` ve `montaj` bölümlerinde `yer_tutucu: true`; yer tutucu uyarısı `caplog` ile bir kez görülür
    - Eksik anahtar, yanlış tip ve geçersiz değer (`tmp_path` altında yazılan küçük YAML'larla, parametrize) hatalı alanın adını içeren `ValueError` verir
    - Testler profil dosyalarını test dosyasının konumuna göre repo içinden bulur (Vision dışına çıkmaz)
  - [ ] 2.2 SITL profil YAML'ını yaz (öneri `config/kamera/` altında; `src/` dışında)
    - `kamera` bölümü: 1280×960, fx = fy ≈ 539.9, cx = 640, cy = 480, distorsiyon yok, `yer_tutucu: false`
    - `montaj` bölümü: açılar 0 [rad], FRD öteleme (0.12, −0.03, −0.242) [m], `yer_tutucu: false`
    - Yorumda türetme (fx = (w/2) / tan(HFOV/2), HFOV = 1.74 rad), FLU → FRD dönüşümü ve kaynak SDF yolları (`Autopilot/Tools/simulation/gz/models/mono_cam/model.sdf`, `.../x500_mono_cam/model.sdf`) **yalnızca metin olarak** yazılır; kod bu dosyaları okumaz
    - Birimler her alanda yorumla belirtilir
  - [ ] 2.3 Pi profil YAML'ını yaz (Raspberry Pi Camera Module 3 **standart**, Wide değil)
    - Çözünürlük bir sensör modundan seçilir (ör. 2304×1296); intrinsics nominal datasheet HFOV'undan (yaklaşık 66°) hesaplanır; distorsiyon boş
    - `kamera.yer_tutucu: true` ve "kalibre edilmemiş, madde 9'da ölçülecek" notu
    - `montaj`: açılar 0, öteleme 0, `yer_tutucu: true` ve "kameranın bakış yönü ve eğimi belli değil" notu
    - Bu değerler karar değildir; yorumda açıkça yazılır
  - [ ] 2.4 Yükleme fonksiyonunu kamera modeli modülüne ekle
    - YAML yolunu argüman olarak alır; kodda sabit yol ve `../` yok; PyYAML `safe_load`
    - Şema doğrulaması: eksik anahtar, yanlış tip veya geçersiz değerde hatalı alanı söyleyen `ValueError` (Görev Grubu 1'deki veri sınıfı doğrulaması yeniden kullanılır, tekrar yazılmaz)
    - Dönüş değeri, dönüşüm fonksiyonuna argüman olarak verilecek kamera modeli nesnesidir (iç parametreler + montaj + `yer_tutucu` bayrakları)
    - Yer tutucu bir profil yüklenirse `logging` ile **bir kez** uyarı verilir
  - [ ] 2.5 `src/` içinde `../`, sabit config yolu veya `if simulation:` dalı olmadığını kontrol et (ör. `grep`)
  - [ ] 2.6 Yalnızca 2.1'deki testleri çalıştır
  - [ ] 2.7 Doğrula: `.venv/bin/ruff format . && .venv/bin/ruff check . && .venv/bin/pytest -q`
  - [ ] 2.8 Commit: `2026-11-13-m10-piksel-body-frame: Görev grubu 2 — SITL ve Pi config profilleri ve yükleyici`
    - Profil YAML'ları, değişen modül ve test dosyası adıyla eklenir

**Kabul Kriterleri:**
- 2.1'deki testler geçer
- SITL profili Gazebo `mono_cam` / `x500_mono_cam` değerleriyle tutarlıdır; Pi profili ve gerçek araç montajı açıkça yer tutucu olarak işaretlidir
- Hatalı config, alan adını söyleyen `ValueError` üretir; yer tutucu profil bir kez uyarı verir
- Simülasyon ile Pi farkı yalnızca seçilen profil dosyasıdır
- ruff ve tüm pytest yeşil, commit atılmış

### Çekirdek: Dönüşüm

#### Görev Grubu 3: Piksel → body frame birim görüş doğrultusu
**Bağımlılıklar:** Görev Grubu 1, Görev Grubu 2

- [ ] 3.0 Piksel → body FRD birim doğrultu dönüşümünü tamamla
  - [ ] 3.1 OpenCV 5.0.0.93'te `undistortPoints` ve `projectPoints`'in modül yerini ve imzasını `.venv` içinde incele
    - Bulgu (fonksiyon yeri, argümanlar, yakınsama kriteri nasıl verilir) Görev Grubu 7'de kaydedilmek üzere not alınır
  - [ ] 3.2 `tests/test_gorus_dogrultusu.py` (öneri ad) içinde 2–8 odaklı test yaz
    - Principal point (cx, cy) → (1, 0, 0); sonuç `float64`, şekil (3,), normu 1
    - Bilinen açılar: u = cx + fx·tan(θ) → yatayda θ kadar sağ (y > 0); v > cy → z > 0 (parametrize)
    - SITL profilinde yatay kenar pikseli ≈ HFOV/2 ≈ 49.85° (tolerans yarım piksel farkını kapsar)
    - Montajla: pitch = −90° → (0, 0, 1); yaw = +90° → (0, 1, 0)
    - Distorsiyon gidiş-dönüş: sıfır olmayan katsayılarla bilinen body doğrultuları `cv2.projectPoints` ile piksele, sonra fonksiyonla geri; açısal fark < 1e-4 rad
    - Geçersiz girdi: NaN, Inf ve aralık dışı u/v → `ValueError` (parametrize)
    - Yakınsamayan aşırı distorsiyonlu durum → `None`
    - 3.1'de doğrulanan OpenCV API'sini sabitleyen bir test
  - [ ] 3.3 Dönüşüm modülünü oluştur (öneri `src/vision/gorus_dogrultusu.py`)
    - Modül docstring'i: çıktı attitude'dan bağımsız body FRD doğrultusudur (seçenek a); frame'ler ve birimler; frame tanımları varsayımdır
    - Yalnızca NumPy ve OpenCV import edilir; Gazebo, picamera2, pymavlink, algılama modeli yok
  - [ ] 3.4 Girdi doğrulamasını yaz
    - u veya v NaN/Inf ise ya da −0.5 ≤ u ≤ w − 0.5, −0.5 ≤ v ≤ h − 0.5 aralığının dışındaysa `ValueError`; mesajda değer ve sınırlar yazar
  - [ ] 3.5 Distorsiyon gidermeyi `cv2.undistortPoints` ile yaz
    - Yakınsama kriteri açıkça verilir (değer ve gerekçe docstring'de)
    - Distorsiyon sıfırken de aynı kod yolu kullanılır; madde 9 katsayıları yalnızca config ile eklenebilir
  - [ ] 3.6 Geri yansıtma kontrolünü ekle
    - Sonuç sonlu değilse ya da `cv2.projectPoints` ile geri yansıtılmış piksel girdiden toleranstan fazla uzaksa `None` döner
    - Tolerans [piksel] varsayılan bir argümandır; değeri ve gerekçesi docstring'de
  - [ ] 3.7 Normalize koordinatı (x_n, y_n, 1) doğrultusuna çevir, Görev Grubu 1'in rotasyonuyla body FRD'ye döndür ve normalize et
    - Öteleme kullanılmaz; mesafe ve 3B konum üretilmez
    - Fonksiyon saf ve durumsuzdur: kamera modeli nesnesini argüman alır; global durum, dosya okuma, loglama, donanım erişimi yok
    - Dönüş tipi `np.ndarray | None` (Python 3.12 ile uyumlu)
  - [ ] 3.8 bbox merkezi yardımcı fonksiyonunu yaz
    - Girdi (x_min, y_min, x_max, y_max) [piksel], çıktı (u, v); bbox formatının varsayım olduğu docstring'de yazılır (madde 5, 7)
    - Ayak noktası veya başka özel nokta seçimi yoktur
  - [ ] 3.9 Yalnızca 3.2'deki testleri çalıştır: `.venv/bin/pytest -q tests/test_gorus_dogrultusu.py`
  - [ ] 3.10 Doğrula: `.venv/bin/ruff format . && .venv/bin/ruff check . && .venv/bin/pytest -q`
  - [ ] 3.11 Commit: `2026-11-13-m10-piksel-body-frame: Görev grubu 3 — piksel → body frame görüş doğrultusu dönüşümü`

**Kabul Kriterleri:**
- 3.2'deki testler geçer
- Principal point, bilinen açılar, montaj, distorsiyon gidiş-dönüş ve geçersiz girdi davranışı spec'e uyar
- Çözüm yoksa `None`, geçersiz girdide `ValueError`; ICD "hedef yok" karşılığı tanımlanmamıştır (madde 5, 11)
- Modül yalnızca NumPy ve OpenCV'ye bağımlıdır; `src/` içinde Gazebo importu yoktur
- ruff ve tüm pytest yeşil, commit atılmış

### Test

#### Görev Grubu 4: Test gözden geçirme ve boşluk doldurma
**Bağımlılıklar:** Görev Grubu 1–3

- [ ] 4.0 Birim testlerini gözden geçir ve yalnızca kritik boşlukları doldur
  - [ ] 4.1 Görev Grubu 1–3'te yazılan testleri gözden geçir (yaklaşık 6–24 test)
  - [ ] 4.2 Spec'in "Birim testleri" listesini yazılmış testlerle tek tek eşleştir; yalnızca bu spec'e ait eksikleri çıkar
    - Beklenen olası eksikler: roll'ün görüntü eksenlerine etkisi (bilinen vektörle), geçerli aralığın sınır değerlerinin (−0.5 ve w − 0.5) kabul edilmesi, bbox merkezi yardımcı fonksiyonu, görüntü ızgarasında normun her zaman 1 olması, geri yansıtma toleransı argümanının etkisi, fonksiyonun girdisini değiştirmemesi (saflık)
  - [ ] 4.3 En fazla 10 ek test yaz
    - Davranışı test et, iç uygulama ayrıntısını değil; testler donanım, Gazebo ve ağ olmadan çalışır
  - [ ] 4.4 Bu spec'in testlerini çalıştır: `.venv/bin/pytest -q tests/test_kamera_modeli.py tests/test_gorus_dogrultusu.py` (ve varsa ayrı config test dosyası)
  - [ ] 4.5 Doğrula: `.venv/bin/ruff format . && .venv/bin/ruff check . && .venv/bin/pytest -q`
    - Laptop 3.12'de geçer; 3.13 (`ci (3.13)`) PR açıldığında CI'da görülür
  - [ ] 4.6 Commit: `2026-11-13-m10-piksel-body-frame: Görev grubu 4 — birim testi boşlukları dolduruldu`

**Kabul Kriterleri:**
- Spec'teki birim testi listesinin her maddesi en az bir testle karşılanır
- En fazla 10 ek test eklenmiştir
- Bu spec'in tüm testleri ve mevcut `tests/test_ortam.py` geçer
- Commit atılmış

### SITL doğrulaması

#### Görev Grubu 5: SITL doğrulama script'i
**Bağımlılıklar:** Görev Grubu 2, Görev Grubu 3 (Görev Grubu 4 ile paralel yürüyebilir)

Not: Spec gereği script CI'da çalışmaz ve bu grupta pytest testi yazılmaz. Doğrulama ruff kuralları ve 5.11'deki elle SITL duman testidir.

- [ ] 5.0 Elle çalıştırılan SITL doğrulama script'ini tamamla
  - [ ] 5.1 Ortamı ve adları doğrula (elle, laptop)
    - `Autopilot/` içinde `make px4_sitl gz_x500_mono_cam` (dünya `default`; Gazebo NVIDIA'da) ile başlat; Autopilot'ta hiçbir dosya değişmez
    - `gz topic -l` ve `gz service -l` ile şunları doğrula: `/world/default/create`, `/world/default/set_pose`, `/world/default/remove`, kamera görüntüsü ve `camera_info` topic'leri (`.../x500_mono_cam_0/link/camera_link/sensor/imager/...`), poz topic'i (`/world/default/pose/info` veya `dynamic_pose/info`)
    - `camera_link` pozunun yayınlanıp yayınlanmadığını kontrol et
    - `.venv/bin/python` içinden apt'den gelen `gz.transport13` ve `gz.msgs10` importunu kontrol et
    - Bulgular Görev Grubu 7'de kaydedilmek üzere not alınır
  - [ ] 5.2 Script iskeletini yaz (öneri `scripts/` altında; `src/` dışında)
    - `argparse`: config profil yolu, dünya adı, topic ve servis adları (varsayılanlar 5.1'de doğrulananlar), sonuç dosyası yolu, senaryo parametreleri
    - Gazebo importları yalnızca bu script'te; çatı repoya veya Autopilot'a dosya yolu ile bağımlılık yok
    - Çekirdek fonksiyonlar `vision` paketinden import edilir, geometri tekrar yazılmaz
    - Tip ipuçları ve docstring'ler; `ruff format` / `ruff check` (ANN dahil) kurallarına uyar
    - Script MAVLink ile komut göndermez; araç PX4 konsolundan veya QGC'den elle kaldırılır
  - [ ] 5.3 Hedef nesneyi yönet
    - Dünyanın `create` servisiyle satır içi SDF olarak statik küçük küre (öneri yarıçap 0.25 m), doygun renk ve emissive malzeme
    - Yeri `set_pose` ile değiştirilir; iş bitince (hata ve Ctrl+C dahil) `remove` ile silinir
    - Hiçbir model veya dünya dosyası eklenmez
  - [ ] 5.4 Kamera görüntüsüne ve `camera_info`'ya abone ol
    - `camera_info`'daki iç parametreleri config'teki SITL değerleriyle karşılaştır; fark varsa raporla ve sonuçlara not düş
  - [ ] 5.5 Pozları oku
    - İHA (`x500_mono_cam_0` model/base_link) ve hedef pozu; kamera konumu `camera_link` pozu yayınlanıyorsa oradan, değilse config ötelemesinden. Hangisinin kullanıldığı sonuçlara yazılır
    - İHA pozu yalnızca değerlendirmede kullanılır, algoritmanın girdisi değildir
  - [ ] 5.6 Pikseli ölç
    - HSV renk eşiklemesi, en büyük blob, görüntü momentleriyle merkez
    - Blob görüntü kenarına değiyorsa veya alanı eşiğin altındaysa kare atılır; eşikler gerekçeli yorumlu adlandırılmış sabitlerdir
    - Ölçülen piksel `vision` dönüşüm fonksiyonuna verilir
  - [ ] 5.7 Ground truth doğrultuyu hesapla
    - Hedefin dünya (ENU) konumundan kamera konumu çıkarılır, base_link FLU'ya çevrilir, FRD'ye geçirilir (y → −y, z → −z), normalize edilir (ana metrik)
    - Ek metrik: aynı işlem body orijininden (ötelemeyi ihmal etmenin paralaks etkisi)
    - Gazebo ↔ PX4 frame ilişkisi varsayım olarak yorumda belirtilir
  - [ ] 5.8 Zaman eşleşmesi ve durağanlık
    - Görüntü ve poz mesajları sim time zaman damgalarına göre en yakın eşleşmeyle eşlenir
    - Ardışık pozlarda açı değişimi eşiği aşan kareler atılır; atılan kare sayıları sayılır
  - [ ] 5.9 Senaryo ızgarasını üret
    - Mesafeler (ör. 3, 8, 15 m) × görüntü merkezi, kenarları ve köşelerini kapsayan ızgara; her konuma bölge etiketi (merkez / kenar / köşe)
    - Hedef konumu SITL nominal pinhole modeliyle ve İHA'nın o anki pozuna göre nişanlanır; ölçülen piksel daima görüntüden gelir
    - Yerin altına düşen konumlar atlanır
    - İrtifa (yerde / hover) script'in argümanı veya o anki pozdan okunan bilgi olarak sonuçlara yazılır
  - [ ] 5.10 Metrikleri hesapla ve yaz
    - Hesaplanan doğrultu ile ground truth arasındaki açı [derece]: ortalama, RMS, maksimum; toplam ve bölgeye göre; ana (kamera konumundan) ve ek (body orijininden) ayrı
    - Sonuç tablosu argümanla verilen yola veya stdout'a Markdown olarak yazılır; kare/video/log repoya kaydedilmez (gerekirse repo dışına veya `.gitignore`'daki klasörlere)
    - Kesin başarı eşiği yoktur
  - [ ] 5.11 Elle duman testi (SITL, yerde)
    - Hedef tam önde: hata küçük ve doğrultu ≈ (1, 0, 0); hedef sağda: y > 0; hedef aşağıda/yukarıda: z işareti doğru
    - Bu test eksen/işaret hatalarını (ENU/FLU/FRD) ölçümden önce yakalamak içindir; sonuç Görev Grubu 7'de not edilir
  - [ ] 5.12 Doğrula: `.venv/bin/ruff format . && .venv/bin/ruff check . && .venv/bin/pytest -q` (script pytest tarafından toplanmaz; `testpaths = ["tests"]`)
  - [ ] 5.13 Commit: `2026-11-13-m10-piksel-body-frame: Görev grubu 5 — SITL doğrulama script'i`

**Kabul Kriterleri:**
- Script `src/` dışında, ruff kurallarına uyar, CI'ı etkilemez
- Hedef dosya eklenmeden spawn edilir ve iş bitince silinir
- `camera_info` karşılaştırması, kamera konumu kaynağı ve atılan kare sayıları raporlanır
- Duman testinde eksen işaretleri doğrudur
- Commit atılmış

#### Görev Grubu 6: SITL ölçümü ve sonuçların kaydı
**Bağımlılıklar:** Görev Grubu 5

- [ ] 6.0 SITL ölçümlerini yap ve sonuç tablosunu spec klasörüne yaz
  - [ ] 6.1 Ölçüm ortamını kaydet
    - Kullanılan Vision ve Autopilot commit'leri, PX4 v1.17.0, Gazebo Harmonic, OpenCV/NumPy sürümleri, kullanılan config profili
  - [ ] 6.2 Ölçüm 1: araç yerde, tüm mesafe ve ızgara senaryoları
  - [ ] 6.3 Ölçüm 2: araç elle kaldırılır (PX4 konsolu veya QGC), birinci hover irtifasında durağanken ölçüm
  - [ ] 6.4 Ölçüm 3: ikinci, farklı hover irtifasında ölçüm
    - Seçilen irtifa değerleri sonuçlara yazılır
  - [ ] 6.5 Test sonrası SITL parametre dosyasını sıfırla (`build/px4_sitl_default/rootfs/parameters*.bson`; test standardı)
  - [ ] 6.6 Sonuçları `implementation/sitl-dogrulama-sonuclari.md` dosyasına yaz (spec'in önerdiği yol)
    - Her irtifa için tablo: ortalama / RMS / maksimum açısal hata [°], toplam ve bölgeye göre; ana ve ek (body orijini) metrik
    - `camera_info` karşılaştırması, kamera konumunun kaynağı, atılan kare sayıları ve nedenleri
    - Kısa yorum: paralaks etkisi, kenar/köşe davranışı, olası hata kaynakları (blob merkezi ≠ küre merkezi, zaman eşleşmesi, yarım piksel kuralı)
    - Kesin başarı eşiği konmaz; ortam bilgisi (6.1)
    - Kural 6 notu: iki repo aynı `tez-*` tag'iyle işaretlenmeli; tag'i ekip açar (bu görevde tag açılmaz)
  - [ ] 6.7 Doğrula: `.venv/bin/ruff format . && .venv/bin/ruff check . && .venv/bin/pytest -q`
  - [ ] 6.8 Commit: `2026-11-13-m10-piksel-body-frame: Görev grubu 6 — SITL ölçüm sonuçları`
    - Yalnızca sonuç dosyası (ve ölçüm sırasında script'te yapılan küçük düzeltmeler varsa onlar) adıyla eklenir; kare/log eklenmez

**Kabul Kriterleri:**
- En az 3 irtifada (yerde + 2 hover) ve birkaç mesafede ölçüm yapılmıştır; merkez, kenar ve köşe bölgeleri ayrı raporlanır
- Sonuç tablosu ve yorum spec klasöründedir
- Repoya kare, video veya log girmemiştir
- Commit atılmış

### Dokümantasyon

#### Görev Grubu 7: Kararlar, test sonuçları ve karşılaşılan sorunların kaydı
**Bağımlılıklar:** Görev Grubu 1–6

- [ ] 7.0 Spec klasöründeki dokümanı kodla eşitle
  - [ ] 7.1 `implementation/` altında bir uygulama notu yaz (ad işi yapanın seçimi)
    - Seçilen modül, fonksiyon, config ve script adları ve yerleri (spec önerilerinden farklıysa gerekçesiyle)
    - OpenCV 5.0.0.93 API bulguları (3.1), seçilen yakınsama kriteri ve geri yansıtma toleransı ile gerekçeleri
    - Roll işaret kuralı ve montaj rotasyonu bileşimi
    - Pi profilinde seçilen yer tutucu çözünürlük ve HFOV kaynağı
    - SITL'de doğrulanan topic/servis adları, `camera_link` pozu durumu (5.1), duman testi sonucu (5.11)
    - Birim testi sonuçları (test sayısı, 3.12 yerel sonuç; 3.13 CI sonucu PR'da)
    - Karşılaşılan sorunlar ve çözümleri
  - [ ] 7.2 Attitude kararının (seçenek a) gerekçesinin kodda (modül docstring'i) ve spec'te tutarlı olduğunu kontrol et; kesin mimari karar gibi sunulmadığını doğrula
  - [ ] 7.3 "Varsayımlar" maddelerinin kodda ve config yorumlarında varsayım olarak işaretli kaldığını kontrol et
  - [ ] 7.4 Uygulama spec'ten saptıysa `spec.md`'yi güncelle (ad değişiklikleri, netleşen ayrıntılar)
  - [ ] 7.5 Son kontroller
    - `requirements/` ve `.github/workflows/ci.yml` değişmemiş; `Autopilot/` ve çatı repoda değişiklik yok
    - `src/` içinde `../`, Gazebo/picamera2/pymavlink importu ve `if simulation:` yok (`grep`)
    - Repoda kare, video, log, model ağırlığı yok
  - [ ] 7.6 Doğrula: `.venv/bin/ruff format . && .venv/bin/ruff check . && .venv/bin/pytest -q`
  - [ ] 7.7 Commit: `2026-11-13-m10-piksel-body-frame: Görev grubu 7 — uygulama notları ve doküman güncellemesi`

**Kabul Kriterleri:**
- Kararlar, gerekçeler, test sonuçları ve sorunlar spec klasöründe yazılıdır; doküman koddan geri kalmamıştır
- Varsayımlar ve öneri adlar kesinleşmiş gibi sunulmaz
- Son kontrollerin tümü geçer, commit atılmış

## Uygulama Sırası

1. Görev Grubu 1 — Kamera modeli veri sınıfları ve montaj rotasyonu
2. Görev Grubu 2 — YAML config profilleri ve yükleyici
3. Görev Grubu 3 — Piksel → body frame dönüşümü
4. Görev Grubu 4 — Test gözden geçirme ve boşluk doldurma ile Görev Grubu 5 — SITL doğrulama script'i (ikisi de 1–3'e bağlı; paralel yürüyebilir)
5. Görev Grubu 6 — SITL ölçümü ve sonuçlar (Görev Grubu 5'e bağlı)
6. Görev Grubu 7 — Uygulama notları ve doküman güncellemesi (hepsine bağlı)
