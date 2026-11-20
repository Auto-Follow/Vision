# Görev Listesi: m10 — Piksel koordinatından body frame hedef vektörüne dönüşüm

## Genel Bakış

- Spec: `spec.md` · Gereksinimler: `planning/requirements.md` · Görsel yok (`planning/visuals/` boş).
- Repo: `Vision` (branch `ozellik/m10-piksel-body-frame`). Kod yalnızca bu repoya yazılır; `Autopilot/` ve çatı repoda dosya değişmez.
- Toplam: 7 görev grubu.
- 2026-11-20 güncellemesi: SITL doğrulaması m06 simülasyonuna (Autopilot `ozellik/m06-sim-ortami`, `x500_tez`) taşındı. Görev Grubu 2'nin değerleri ile Görev Grubu 5 ve 6 buna göre yeniden yazıldı (bkz. `spec.md` "Değişiklik kaydı").
- **2026-11-20 kullanıcı kararı: Görev Grubu 5 ve 6 (SITL) ertelendi.** Şimdi yalnızca 1–4 (dönüşüm, config, birim testleri) ve 7 (1–4 için doküman) uygulanır. 5–6 silinmedi; sim bağlanınca yapılır, 7 o zaman güncellenir. Stok Follow Me koşusu çıkarıldı; kapalı çevrim takip m15 koduyla ayrı bir işte yapılacak.

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

- [x] 1.0 Kamera modeli veri sınıflarını ve montaj rotasyonunu tamamla
  - [x] 1.1 `tests/test_kamera_modeli.py` (öneri ad) içinde 2–8 odaklı test yaz
    - Mevcut `tests/test_ortam.py` üslubu: düz pytest fonksiyonları, Türkçe `snake_case` adlar, dosya başında docstring
    - Geçerli iç parametrelerle nesne oluşur; geçersiz değerler (w veya h ≤ 0, fx veya fy ≤ 0, NaN/Inf, izin verilmeyen distorsiyon katsayı sayısı ör. 3) `ValueError` verir (`pytest.mark.parametrize` ile tek test)
    - Montaj açıları 0 iken: optik z → body (1, 0, 0), optik x → (0, 1, 0), optik y → (0, 0, 1)
    - Pitch = −90° iken optik eksen → (0, 0, 1); yaw = +90° iken optik eksen → (0, 1, 0)
    - İşaret kuralı: pozitif pitch optik ekseni yukarı kaldırır (sonuç z < 0)
    - Birkaç rastgele açı için rotasyon matrisi ortonormal ve determinantı +1
    - Donanım, Gazebo ve ağ kullanılmaz
  - [x] 1.2 `src/vision/` altında kamera modeli modülünü oluştur (öneri `kamera_modeli.py`)
    - Mevcut `vision` paketine eklenir; `pyproject.toml` ve paket yapısı değişmez
  - [x] 1.3 İç parametreler için değişmez (frozen) veri sınıfı yaz
    - Alanlar: çözünürlük (w, h) [piksel], fx, fy, cx, cy [piksel], OpenCV distorsiyon katsayıları (uzunluk 0, 4, 5, 8, 12 veya 14; boş = distorsiyon yok)
    - Oluşturulurken doğrulama: w, h > 0; fx, fy > 0; tüm değerler sonlu; katsayı sayısı izinli. Aksi halde hangi alanın hatalı olduğunu söyleyen `ValueError`
    - OpenCV'ye verilecek kamera matrisi ve katsayı dizisi `float64` olarak türetilebilir
  - [x] 1.4 Montaj için değişmez veri sınıfı yaz
    - Alanlar: roll, pitch, yaw [rad] (kameranın body FRD'ye göre, ZYX sırası: önce yaw, sonra pitch, sonra roll) ve FRD öteleme [m]
    - Tüm değerler sonlu olmalı; değilse `ValueError`
    - Öteleme saklanır ama doğrultu hesabına girmez (docstring'de yazılır)
    - Gimbal desteği yoktur; kamera gövdeye sabittir
  - [x] 1.5 camera (optik) → body FRD rotasyonunu NumPy ile hesapla
    - Toplam rotasyon = ZYX montaj rotasyonu ∘ sabit eksen eşlemesi (optik z → x, optik x → y, optik y → z)
    - Elde edilen matrisin ortonormal ve det = +1 olduğu kontrol edilir; SciPy kullanılmaz
    - Roll'ün pozitif yönü aynı FRD Euler kuralından türetilir ve docstring'de bilinen bir vektörle örneklenir (roll testi Görev Grubu 4'te)
    - Frame tanımları docstring'de "varsayım" olarak işaretlenir
  - [x] 1.6 Yalnızca 1.1'deki testleri çalıştır: `.venv/bin/pytest -q tests/test_kamera_modeli.py`
  - [x] 1.7 Doğrula: `.venv/bin/ruff format . && .venv/bin/ruff check . && .venv/bin/pytest -q`
  - [x] 1.8 Commit: `2026-11-13-m10-piksel-body-frame: Görev grubu 1 — kamera modeli veri sınıfları ve montaj rotasyonu`
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

- [x] 2.0 SITL ve Pi config profillerini ve yükleme fonksiyonunu tamamla
  - [x] 2.1 Config için 2–8 odaklı test yaz (öneri: `tests/test_kamera_modeli.py` içine ya da ayrı bir dosyaya)
    - SITL profili yüklenir; değerler formülle tutarlıdır: 2304×1296, fx = fy = 1152 / tan(1.151917 / 2) ≈ 1773.9 px, cx = 1152, cy = 648, distorsiyon boş, montaj roll 0 / pitch −0.610865 rad (35° aşağı) / yaw 0, öteleme FRD (0.151, 0, 0.035) m, `yer_tutucu` her iki bölümde `false`. Sabitler testte **değer olarak** yazılır; Autopilot'taki YAML/SDF okunmaz
    - SITL profili yüklenince uyarı yoktur (`caplog`)
    - Pi profili yüklenir; `kamera` ve `montaj` bölümlerinde `yer_tutucu: true`; yer tutucu uyarısı `caplog` ile bir kez görülür
    - Eksik anahtar, yanlış tip ve geçersiz değer (`tmp_path` altında yazılan küçük YAML'larla, parametrize) hatalı alanın adını içeren `ValueError` verir
    - Testler profil dosyalarını test dosyasının konumuna göre repo içinden bulur (Vision dışına çıkmaz)
  - [x] 2.2 SITL profil YAML'ını yaz (öneri `config/kamera/` altında; `src/` dışında)
    - `kamera` bölümü: 2304×1296, fx = fy ≈ 1773.9, cx = 1152, cy = 648, distorsiyon yok, `yer_tutucu: false`
    - `montaj` bölümü: roll 0, pitch −0.610865, yaw 0 [rad]; FRD öteleme (0.151, 0, 0.035) [m]; `yer_tutucu: false`
    - Yorumda türetme (fx = (w/2) / tan(HFOV/2), HFOV = 1.151917 rad), "m06'nın 35° aşağı eğimi = bu kuralla pitch −35°" notu, FLU → FRD dönüşümü, kaynak dosyalar (Autopilot `ozellik/m06-sim-ortami`: `tez/sim/kamera_montaji.yaml`, `tez/sim/models/x500_tez/model.sdf`) ve kopyalanan m06 commit'i **yalnızca metin olarak** yazılır; kod bu dosyaları okumaz
    - Birimler her alanda yorumla belirtilir
  - [x] 2.3 Pi profil YAML'ını yaz (Raspberry Pi Camera Module 3 **standart**, Wide değil)
    - Kamera değerleri simle aynı nominal değerlerdir (2304×1296, datasheet HFOV ≈ 66°, distorsiyon boş)
    - `kamera.yer_tutucu: true` ve "kalibre edilmemiş, madde 9'da ölçülecek; Pi çözünürlüğü belli değil" notu
    - `montaj`: m06 önerisi (pitch −35°, FRD (0.151, 0, 0.035) m), `yer_tutucu: true` ve "önerilen değer; gerçek montaj yapılmadı, takılınca açı ±0.5° ölçülecek" notu
    - Bu değerler karar değildir; yorumda açıkça yazılır
  - [x] 2.4 Yükleme fonksiyonunu kamera modeli modülüne ekle
    - YAML yolunu argüman olarak alır; kodda sabit yol ve `../` yok; PyYAML `safe_load`
    - Şema doğrulaması: eksik anahtar, yanlış tip veya geçersiz değerde hatalı alanı söyleyen `ValueError` (Görev Grubu 1'deki veri sınıfı doğrulaması yeniden kullanılır, tekrar yazılmaz)
    - Dönüş değeri, dönüşüm fonksiyonuna argüman olarak verilecek kamera modeli nesnesidir (iç parametreler + montaj + `yer_tutucu` bayrakları)
    - Yer tutucu bir profil yüklenirse `logging` ile **bir kez** uyarı verilir
  - [x] 2.5 `src/` içinde `../`, sabit config yolu veya `if simulation:` dalı olmadığını kontrol et (ör. `grep`)
  - [x] 2.6 Yalnızca 2.1'deki testleri çalıştır
  - [x] 2.7 Doğrula: `.venv/bin/ruff format . && .venv/bin/ruff check . && .venv/bin/pytest -q`
  - [x] 2.8 Commit: `2026-11-13-m10-piksel-body-frame: Görev grubu 2 — SITL ve Pi config profilleri ve yükleyici`
    - Profil YAML'ları, değişen modül ve test dosyası adıyla eklenir

**Kabul Kriterleri:**
- 2.1'deki testler geçer
- SITL profili m06 `x500_tez` değerleriyle (`kamera_montaji.yaml`) tutarlıdır; Pi profili ve gerçek araç montajı açıkça yer tutucu olarak işaretlidir
- Hatalı config, alan adını söyleyen `ValueError` üretir; yer tutucu profil bir kez uyarı verir
- Simülasyon ile Pi farkı yalnızca seçilen profil dosyasıdır
- ruff ve tüm pytest yeşil, commit atılmış

### Çekirdek: Dönüşüm

#### Görev Grubu 3: Piksel → body frame birim görüş doğrultusu
**Bağımlılıklar:** Görev Grubu 1, Görev Grubu 2

- [x] 3.0 Piksel → body FRD birim doğrultu dönüşümünü tamamla
  - [x] 3.1 OpenCV 5.0.0.93'te `undistortPoints` ve `projectPoints`'in modül yerini ve imzasını `.venv` içinde incele
    - Bulgu (fonksiyon yeri, argümanlar, yakınsama kriteri nasıl verilir) Görev Grubu 7'de kaydedilmek üzere not alınır
  - [x] 3.2 `tests/test_gorus_dogrultusu.py` (öneri ad) içinde 2–8 odaklı test yaz
    - Principal point (cx, cy) → (1, 0, 0); sonuç `float64`, şekil (3,), normu 1
    - Bilinen açılar: u = cx + fx·tan(θ) → yatayda θ kadar sağ (y > 0); v > cy → z > 0 (parametrize)
    - SITL iç parametreleri, montaj açıları 0: yatay kenar pikseli (u = w − 0.5) ≈ HFOV/2 ≈ 33.0° (tolerans yarım piksel farkını kapsar)
    - Montajla: pitch = −90° → (0, 0, 1); yaw = +90° → (0, 1, 0); SITL profili (pitch −35°) principal point → (cos 35°, 0, sin 35°) ≈ (0.819, 0, 0.574)
    - Distorsiyon gidiş-dönüş: sıfır olmayan katsayılarla bilinen body doğrultuları `cv2.projectPoints` ile piksele, sonra fonksiyonla geri; açısal fark < 1e-4 rad
    - Geçersiz girdi: NaN, Inf ve aralık dışı u/v → `ValueError` (parametrize)
    - Yakınsamayan aşırı distorsiyonlu durum → `None`
    - 3.1'de doğrulanan OpenCV API'sini sabitleyen bir test
  - [x] 3.3 Dönüşüm modülünü oluştur (öneri `src/vision/gorus_dogrultusu.py`)
    - Modül docstring'i: çıktı attitude'dan bağımsız body FRD doğrultusudur (seçenek a); frame'ler ve birimler; frame tanımları varsayımdır
    - Yalnızca NumPy ve OpenCV import edilir; Gazebo, picamera2, pymavlink, algılama modeli yok
  - [x] 3.4 Girdi doğrulamasını yaz
    - u veya v NaN/Inf ise ya da −0.5 ≤ u ≤ w − 0.5, −0.5 ≤ v ≤ h − 0.5 aralığının dışındaysa `ValueError`; mesajda değer ve sınırlar yazar
  - [x] 3.5 Distorsiyon gidermeyi `cv2.undistortPoints` ile yaz
    - Yakınsama kriteri açıkça verilir (değer ve gerekçe docstring'de)
    - Distorsiyon sıfırken de aynı kod yolu kullanılır; madde 9 katsayıları yalnızca config ile eklenebilir
  - [x] 3.6 Geri yansıtma kontrolünü ekle
    - Sonuç sonlu değilse ya da `cv2.projectPoints` ile geri yansıtılmış piksel girdiden toleranstan fazla uzaksa `None` döner
    - Tolerans [piksel] varsayılan bir argümandır; değeri ve gerekçesi docstring'de
  - [x] 3.7 Normalize koordinatı (x_n, y_n, 1) doğrultusuna çevir, Görev Grubu 1'in rotasyonuyla body FRD'ye döndür ve normalize et
    - Öteleme kullanılmaz; mesafe ve 3B konum üretilmez
    - Fonksiyon saf ve durumsuzdur: kamera modeli nesnesini argüman alır; global durum, dosya okuma, loglama, donanım erişimi yok
    - Dönüş tipi `np.ndarray | None` (Python 3.12 ile uyumlu)
  - [x] 3.8 bbox merkezi yardımcı fonksiyonunu yaz
    - Girdi (x_min, y_min, x_max, y_max) [piksel], çıktı (u, v); bbox formatının varsayım olduğu docstring'de yazılır (madde 5, 7)
    - Ayak noktası veya başka özel nokta seçimi yoktur
  - [x] 3.9 Yalnızca 3.2'deki testleri çalıştır: `.venv/bin/pytest -q tests/test_gorus_dogrultusu.py`
  - [x] 3.10 Doğrula: `.venv/bin/ruff format . && .venv/bin/ruff check . && .venv/bin/pytest -q`
  - [x] 3.11 Commit: `2026-11-13-m10-piksel-body-frame: Görev grubu 3 — piksel → body frame görüş doğrultusu dönüşümü`

**Kabul Kriterleri:**
- 3.2'deki testler geçer
- Principal point, bilinen açılar, montaj, distorsiyon gidiş-dönüş ve geçersiz girdi davranışı spec'e uyar
- Çözüm yoksa `None`, geçersiz girdide `ValueError`; ICD "hedef yok" karşılığı tanımlanmamıştır (madde 5, 11)
- Modül yalnızca NumPy ve OpenCV'ye bağımlıdır; `src/` içinde Gazebo importu yoktur
- ruff ve tüm pytest yeşil, commit atılmış

### Test

#### Görev Grubu 4: Test gözden geçirme ve boşluk doldurma
**Bağımlılıklar:** Görev Grubu 1–3

- [x] 4.0 Birim testlerini gözden geçir ve yalnızca kritik boşlukları doldur
  - [x] 4.1 Görev Grubu 1–3'te yazılan testleri gözden geçir (yaklaşık 6–24 test)
  - [x] 4.2 Spec'in "Birim testleri" listesini yazılmış testlerle tek tek eşleştir; yalnızca bu spec'e ait eksikleri çıkar
    - Beklenen olası eksikler: roll'ün görüntü eksenlerine etkisi (bilinen vektörle), geçerli aralığın sınır değerlerinin (−0.5 ve w − 0.5) kabul edilmesi, bbox merkezi yardımcı fonksiyonu, görüntü ızgarasında normun her zaman 1 olması, geri yansıtma toleransı argümanının etkisi, fonksiyonun girdisini değiştirmemesi (saflık)
  - [x] 4.3 En fazla 10 ek test yaz
    - Davranışı test et, iç uygulama ayrıntısını değil; testler donanım, Gazebo ve ağ olmadan çalışır
  - [x] 4.4 Bu spec'in testlerini çalıştır: `.venv/bin/pytest -q tests/test_kamera_modeli.py tests/test_gorus_dogrultusu.py` (ve varsa ayrı config test dosyası)
  - [x] 4.5 Doğrula: `.venv/bin/ruff format . && .venv/bin/ruff check . && .venv/bin/pytest -q`
    - Laptop 3.12'de geçer; 3.13 (`ci (3.13)`) PR açıldığında CI'da görülür
  - [x] 4.6 Commit: `2026-11-13-m10-piksel-body-frame: Görev grubu 4 — birim testi boşlukları dolduruldu`

**Kabul Kriterleri:**
- Spec'teki birim testi listesinin her maddesi en az bir testle karşılanır
- En fazla 10 ek test eklenmiştir
- Bu spec'in tüm testleri ve mevcut `tests/test_ortam.py` geçer
- Commit atılmış

### SITL doğrulaması

#### Görev Grubu 5: m06 koşu klasörü değerlendirme script'i (ERTELENDİ)
**Bağımlılıklar:** Görev Grubu 2, Görev Grubu 3 (Görev Grubu 4 ile paralel yürüyebilir)

Not: Script CI'da çalışmaz; spec gereği bu grupta CI testi zorunlu değildir. Script Gazebo'ya bağlanmadığı için okuma ve metrik fonksiyonları, `tmp_path` altında elle yazılmış küçük sahte CSV'lerle pytest'te sınanabilir (isteğe bağlı, en fazla 4 test). Asıl doğrulama 5.8'deki gerçek koşu üzerindeki duman testidir.

- [ ] 5.0 m06 koşu klasörünü okuyup Ölçüm A/B/C metriklerini üreten script'i tamamla
  - [ ] 5.1 m06 çıktı biçimini doğrula (okuma, Autopilot'ta dosya değişmez)
    - Autopilot `ozellik/m06-sim-ortami`: `tez/sim/README.md` "Doğru cevap, görüş vektörü ve görünürlük" ve çıktı tablosu, `tez/sim/araclar/kayit.py` (`truth_row`), `algilama.py` (CSV sütunları), `rapor.py` (`ozet.json` kamera kalibrasyonu ve montaj alanları)
    - Kullanılacak sütunlar: `dogru_cevap.csv` → `t`, `merkez_u/v`, `kadrajda`, `los_govde_x/y/z`, `gorunur`, `hedef_kutu_u0/v0/u1/v1`, `dron_x/y/z`, `dron_qw/qx/qy/qz`, `hedef_x/y`; `algilama.csv` → `t_us`, `secilen_u0…v1`, `los_i_x/y/z`; `ozet.json` → kamera kalibrasyonu ve montaj (ofset, C_cb). Gerçek alan adları 6.2'deki ilk koşuda kesinleştirilir
    - Bulgular Görev Grubu 7'de kaydedilmek üzere not alınır
  - [ ] 5.2 Script iskeletini yaz (öneri `scripts/` altında; `src/` dışında)
    - `argparse`: bir veya birden çok koşu klasörü, config profil yolu, sonuç dosyası yolu (verilmezse stdout)
    - Yalnızca standart kütüphane (`csv`, `json`, `pathlib`, `math`) ve NumPy; pandas yok, gz yok, MAVLink yok; Autopilot kodu import edilmez, Autopilot yolu sabit yazılmaz
    - Çekirdek fonksiyonlar `vision` paketinden import edilir, geometri tekrar yazılmaz
    - Tip ipuçları ve docstring'ler; `ruff format` / `ruff check` (ANN dahil) kurallarına uyar
  - [ ] 5.3 Kamera ve montaj karşılaştırması
    - `ozet.json`'daki camera_info iç parametreleri ve montaj (ofset, C_cb) Vision SITL profiliyle karşılaştırılır; C_cb'den eğim açısı çıkarılıp −35° ile kıyaslanır
    - Fark varsa raporlanır ve sonuç dosyasına not düşülür (config'i değiştirmek kullanıcının kararıdır)
  - [ ] 5.4 Ölçüm A (geometrik, ana metrik)
    - `kadrajda` satırlarında `merkez_u/v` → Vision dönüşümü → `los_govde` ile açı farkı
    - Aralık dışı (`ValueError`) veya `None` sonuçları sayılır ve raporlanır, ölçüme katılmaz
  - [ ] 5.5 Ölçüm B (görüntüden) ve paralaks ek metriği
    - `gorunur` satırlarında segmentasyon kutusu merkezi (Vision bbox yardımcısıyla) → Vision dönüşümü → `los_govde` ile açı farkı
    - Paralaks: ground truth'u body orijininden de hesapla (İHA konumu ve quaternion'u, hedef konumu + 0.9 m; ENU/FLU → FRD). Hesaplanan doğrultuyla farkı ayrıca ver. Frame dönüşümü yorumda varsayım olarak işaretlenir
  - [ ] 5.6 Ölçüm C (model kutusu, `algilama.csv` varsa)
    - Seçilen kutunun merkezi → Vision dönüşümü; `t_us` ile `dogru_cevap.csv`'ye birleştirilip `los_govde` ile, ayrıca aynı satırdaki m06 `los_i_x/y/z` ile açı farkı (iki uygulama tutarlılığı, ≈ 0 beklenir)
  - [ ] 5.7 Metrikleri hesapla ve yaz
    - Her ölçüm için ortalama / RMS / maksimum açısal hata [°], satır sayısı; toplam ve piksel bölgesine göre (merkez / kenar / köşe; sınırlar adlandırılmış sabit)
    - Sonuç Markdown tablo olarak argümanla verilen yola veya stdout'a yazılır; koşu klasörüne veya repoya CSV/kare kopyalanmaz
    - Kesin başarı eşiği yoktur
  - [ ] 5.8 Duman testi (6.2'deki ilk koşu üzerinde)
    - Ölçüm A'nın hatası çok küçüktür; büyükse önce eksen/işaret (pitch −35° işareti, FLU/FRD) ve config kontrol edilir
    - Birkaç satırda elle işaret kontrolü: hedef görüntünün sağındayken y > 0, alt yarısındayken doğrultu burunun 35°'den daha aşağısında
    - Sonuç Görev Grubu 7'de not edilir
  - [ ] 5.9 (İsteğe bağlı) `tmp_path` altında sahte CSV'lerle okuma/metrik testleri (en fazla 4)
  - [ ] 5.10 Doğrula: `.venv/bin/ruff format . && .venv/bin/ruff check . && .venv/bin/pytest -q` (script pytest tarafından toplanmaz; `testpaths = ["tests"]`)
  - [ ] 5.11 Commit: `2026-11-13-m10-piksel-body-frame: Görev grubu 5 — m06 koşu değerlendirme script'i`

**Kabul Kriterleri:**
- Script `src/` dışında, gz/pandas/Autopilot importu yok, ruff kurallarına uyar, CI'ı etkilemez
- Kamera/montaj karşılaştırması ve atılan satır sayıları raporlanır
- Duman testinde Ölçüm A'nın hatası çok küçük ve eksen işaretleri doğrudur
- Commit atılmış

#### Görev Grubu 6: m06 simülasyonunda ölçüm ve sonuçların kaydı (ERTELENDİ)
**Bağımlılıklar:** Görev Grubu 5 (6.1 ve 6.2 ondan önce de yapılabilir)

- [ ] 6.0 m06 koşularını üret, değerlendir ve sonuç tablosunu spec klasörüne yaz
  - [ ] 6.1 m06 ortamını kur (bir kez, laptop; Autopilot'ta dosya değişmez)
    - Autopilot `ozellik/m06-sim-ortami` branch'inde (main'e girene kadar), `tez/sim/README.md` "A. Kurulum": submodule ve kilit kontrolü (`tez/pin/verify_pin.sh --worktree`), apt paketleri (A2), `.venv-tez` (A3), `tez/sim/derle.sh && tez/sim/kur.sh`
    - Model açık koşu (Ölçüm C) isteniyorsa A4: `person_detection_model_v0.2.pt` `~/auto-follow-modeller/` altına (Vision `model-training`, commit `ebff718`'den, sha256 kontrollü); repoya girmez
    - `sudo` ve internet gerektiren adımlar kullanıcıya sorularak yapılır
    - İsteğe bağlı: `tez/sim/araclar/f0_kabul.sh` ile simin çalıştığını doğrula
  - [ ] 6.2 Koşu 1: araç havada bekler (`takip: yok`, ör. `yuruyen_insan`; `--modelsiz` olabilir), `--ekransiz`
  - [ ] 6.3 Koşu 2: farklı irtifada veya farklı senaryoda (`takip: yok`) araç havada bekler. Stok Follow Me kullanılmaz; kapalı çevrim takip m15 koduyla ayrı bir işte yapılacak
  - [ ] 6.4 (İsteğe bağlı) Koşu 3: model açık bir koşu (ör. `kalabalik_park`), Ölçüm C için
  - [ ] 6.5 Ölçüm ortamını kaydet
    - Vision commit'i, Autopilot (m06 branch) commit'i, PX4 v1.17.0, Gazebo Harmonic, OpenCV/NumPy sürümleri, kullanılan config profili, senaryolar ve irtifaları, komut satırları, model dosyası ve sha256 (varsa)
  - [ ] 6.6 Script'i koşu klasörleri üzerinde çalıştır; koşu klasörleri `tez/sim/sonuclar/` altında kalır (git'e girmez)
  - [ ] 6.7 Sonuçları `implementation/sitl-dogrulama-sonuclari.md` dosyasına yaz (spec'in önerdiği yol)
    - Her koşu için tablo: Ölçüm A, B, C ve paralaks; ortalama / RMS / maksimum [°], satır sayısı; toplam ve bölgeye göre
    - Kamera/montaj karşılaştırması (5.3), atılan satır sayıları ve nedenleri
    - Kısa yorum: A'nın küçüklüğü, B'deki kutu merkezi ≠ gövde merkezi etkisi, C'deki iki uygulama tutarlılığı, paralaksın küçüklüğü, kenar/köşe kapsamı
    - Kesin başarı eşiği konmaz; ortam bilgisi (6.5)
    - Kural 6 notu: iki repo aynı `tez-*` tag'iyle işaretlenmeli; tag'i ekip açar (bu görevde tag açılmaz)
  - [ ] 6.8 Doğrula: `.venv/bin/ruff format . && .venv/bin/ruff check . && .venv/bin/pytest -q`
  - [ ] 6.9 Commit: `2026-11-13-m10-piksel-body-frame: Görev grubu 6 — SITL ölçüm sonuçları`
    - Yalnızca sonuç dosyası (ve ölçüm sırasında script'te yapılan küçük düzeltmeler varsa onlar) adıyla eklenir; CSV, kare, video, log eklenmez

**Kabul Kriterleri:**
- En az iki koşu (araç havada bekler, `takip: yok`) değerlendirilmiştir; Ölçüm A ve B ve paralaks raporlanmıştır, model koşusu varsa C de
- Sonuç tablosu ve yorum spec klasöründedir
- Repoya CSV, kare, video, log veya model girmemiştir; Autopilot'ta dosya değişmemiştir
- Commit atılmış

### Dokümantasyon

#### Görev Grubu 7: Kararlar, test sonuçları ve karşılaşılan sorunların kaydı
**Bağımlılıklar:** Görev Grubu 1–6

- [ ] 7.0 Spec klasöründeki dokümanı kodla eşitle
  - [ ] 7.1 `implementation/` altında bir uygulama notu yaz (ad işi yapanın seçimi)
    - Seçilen modül, fonksiyon, config ve script adları ve yerleri (spec önerilerinden farklıysa gerekçesiyle)
    - OpenCV 5.0.0.93 API bulguları (3.1), seçilen yakınsama kriteri ve geri yansıtma toleransı ile gerekçeleri
    - Roll işaret kuralı ve montaj rotasyonu bileşimi
    - Pi profilinde seçilen yer tutucu çözünürlük ve HFOV kaynağı; kopyalanan m06 commit'i
    - m06 çıktı biçimi bulguları (5.1), kamera/montaj karşılaştırması (5.3), duman testi sonucu (5.8), m06 kurulumunda karşılaşılan sorunlar (6.1)
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
4. Görev Grubu 4 — Test gözden geçirme ve boşluk doldurma (Görev Grubu 5 — m06 koşu değerlendirme script'i **ERTELENDİ**)
5. Görev Grubu 6 — m06'da ölçüm ve sonuçlar (Görev Grubu 5'e bağlı) — **ERTELENDİ**
6. Görev Grubu 7 — Uygulama notları ve doküman güncellemesi (hepsine bağlı)
