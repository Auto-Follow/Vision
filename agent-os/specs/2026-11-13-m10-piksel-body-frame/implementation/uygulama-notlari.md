# m10 — Uygulama notları (Görev Grubu 1–4 ve 7)

> Tarih: 2026-11-20 · Branch: `ozellik/m10-piksel-body-frame` (Vision) · Spec: `../spec.md` · Görevler: `../tasks.md`
>
> **Durum:** Dönüşüm, config ve birim testleri bitti (Görev Grubu 1–4). SITL doğrulaması (Görev Grubu 5–6) kullanıcı kararıyla **ertelendi** (2026-11-20). Bu yüzden roadmap'teki "SITL'de hata ölçülür" doğrulaması henüz yapılmadı; sim bağlanınca 5–6 yapılır ve bu not güncellenir.

## 1. Eklenen dosyalar ve adlar

Spec'in önerdiği adların hepsi değiştirilmeden kullanıldı.

| Dosya | İçerik |
|---|---|
| `src/vision/kamera_modeli.py` | `KameraIcParametreleri`, `KameraMontaji`, `KameraModeli` (frozen dataclass'lar), `kamera_modeli_yukle(yol)`, `OPTIKTEN_KAMERA_FRD`, `IZINLI_DISTORSIYON_UZUNLUKLARI` |
| `src/vision/gorus_dogrultusu.py` | `pikselden_govde_dogrultusu(model, u, v, geri_yansitma_toleransi=0.5)`, `bbox_merkezi(kutu)`, `DISTORSIYON_GIDERME_KRITERI`, `GERI_YANSITMA_TOLERANSI_PIKSEL` |
| `config/kamera/sitl.yaml` | m06 `x500_tez` değerleri (`yer_tutucu: false`) |
| `config/kamera/pi.yaml` | CM3 Standard nominal değerleri + m06 montaj önerisi (iki bölüm de `yer_tutucu: true`) |
| `tests/test_kamera_modeli.py` | veri sınıfları, doğrulama, rotasyon, roll/ZYX sırası |
| `tests/test_kamera_profili.py` | YAML profilleri ve yükleyici |
| `tests/test_gorus_dogrultusu.py` | dönüşüm, geçersiz girdi, distorsiyon, OpenCV API, bbox, saflık |
| `planning/visuals/01-donusum-zinciri.mmd` | dönüşüm zinciri akış şeması (Mermaid) |
| `planning/visuals/02-eksenler.svg` | piksel / optik / body FRD eksenleri |
| `planning/visuals/03-montaj-yan-gorunum.svg` | 35° montajın yandan görünümü, FOV |

Kod ve yorumlar mevcut repo üslubuna uyar: Türkçe ve ASCII karakterlerle yazıldı (ş/ğ/ı yok). `requirements/`, `pyproject.toml` ve `.github/` değişmedi; yeni paket yok.

## 2. Kullanım

```python
from vision.kamera_modeli import kamera_modeli_yukle
from vision.gorus_dogrultusu import bbox_merkezi, pikselden_govde_dogrultusu

model = kamera_modeli_yukle("config/kamera/sitl.yaml")  # Pi'de: config/kamera/pi.yaml
u, v = bbox_merkezi((x_min, y_min, x_max, y_max))  # [piksel]
d = pikselden_govde_dogrultusu(model, u, v)  # body FRD birim vektör veya None
```

- `ValueError`: u/v sayı değilse, NaN/Inf ise veya geçerli aralığın dışındaysa (−0.5 ≤ u ≤ w − 0.5, −0.5 ≤ v ≤ h − 0.5). Mesajda değer ve sınırlar yazar.
- `None`: geometrik çözüm yok (distorsiyon giderme sonlu değil ya da geri yansıtma 0.5 px'ten uzak). ICD'deki "hedef yok" karşılığı burada tanımlanmadı (madde 5, 11).
- Sim ile Pi arasındaki tek fark seçilen profil dosyasıdır; kodda `if simulation:` yok.

## 3. Kararlar ve gerekçeler

**Rotasyon ve işaret kuralı (varsayım):**
- `R = Rz(yaw) · Ry(pitch) · Rx(roll) · P`, `v_govde = R · v_optik`.
- P sabit eksen eşlemesidir: optik z → x, optik x → y, optik y → z.
- Matrisler standart sağ el FRD Euler matrisleridir. `Ry(θ)·(1,0,0) = (cos θ, 0, −sin θ)` olduğundan pozitif pitch optik ekseni yukarı kaldırır, ek bir işaret çevirmesi gerekmez. m06'nın "35° aşağı" değeri pitch = −0.610865 rad demektir.
- **Roll:** pozitif roll, FRD'de +Rx'tir. Kameranın arkasından optik eksen boyunca bakınca saat yönünde döner. Örnek, roll = +90°: görüntü sağı → body (0, 0, 1) (aşağı), görüntü aşağısı → (0, −1, 0) (sol), optik eksen değişmez. Testle sabitlendi.
- Rotasyonun ortonormal olduğu ve det = +1 olduğu her çağrıda kontrol edilir (tolerans 1e-9). Tutmazsa `RuntimeError` verilir; bu bir iç hata göstergesidir.

**Distorsiyon giderme (OpenCV 5.0.0.93):**
- Kriter: `(COUNT | EPS, 100, 1e-6)`.
  - OpenCV'nin varsayılanı yalnızca 5 iterasyondur. Güçlü distorsiyonda kenarda yetmiyor; k1 = 0.3 ile köşede yaklaşık 0.02 px hata kalıyor.
  - 1e-6 px, fx ≈ 1774 için yaklaşık 6e-10 rad demektir; ihmal edilebilir.
- Geri yansıtma toleransı: 0.5 px (varsayılan argüman).
  - Girdi pikseli zaten ±0.5 px nicemlidir; yakınsamış bir çözüm yaklaşık 1e-6 px içinde geri yansır.
  - Yarım piksellik artık hata yaklaşık 0.016° doğrultu hatası demektir.

**Config:**
- Bilinmeyen anahtarlar reddedilir. Böylece yanlış yazılmış bir anahtar (ör. `distortion`) sessizce atlanmaz.
- `distorsiyon` alanı zorunludur. "Distorsiyon yok" demek için açıkça `[]` yazılır.
- Yer tutucu bir profil yüklendiğinde her yüklemede bir kez uyarı loglanır (logger `vision.kamera_modeli`). Global bir "zaten uyarıldı" durumu tutulmaz.
- SITL değerleri m06'dan **değer olarak** kopyalandı. Kaynak: Autopilot `ozellik/m06-sim-ortami`, commit `65e5bf793be5eda84fe7b9c38338ec15d968ee85`, dosyalar `tez/sim/kamera_montaji.yaml` ve `tez/sim/models/x500_tez/model.sdf`. Kod bu dosyaları okumaz (kural 7). m06'da değerler değişirse `config/kamera/sitl.yaml` elle güncellenir.
- fx değeri 1773.925033 olarak yazıldı. Tam değer 1773.925033120075; fark yaklaşık 1.2e-7 px.

**Attitude (seçenek a):** Çıktı attitude'dan bağımsız body FRD doğrultusudur. Gerekçe modül docstring'inde ve spec'te aynıdır. Kesin bir mimari karar olarak sunulmadı; madde 13 ve PX4 entegrasyonunda yeniden değerlendirilecek.

## 4. OpenCV 5.0.0.93 API bulguları (Görev 3.1)

`cv2.__version__` değeri `"5.0.0"`.

- **Yer:** `cv2.undistortPoints` ve `cv2.projectPoints` üst düzeydedir. `cv2.calib3d` alt modülü yok.
- **`undistortPoints` imzası:** `undistortPoints(src, cameraMatrix, distCoeffs[, dst[, R[, P[, criteria]]]]) -> dst`.
  - `criteria` anahtar kelimeyle `(type, maxCount, epsilon)` demeti olarak verilebilir.
  - P verilmezse çıktı normalize koordinattır.
  - float64 `(1,1,2)` girdi için float64 `(1,1,2)` döner.
- **EPS'nin anlamı:** o anki tahminin yeniden distorsiyonlu pikselinin girdiye uzaklığıdır [px].
- **`projectPoints` imzası:** `projectPoints(objectPoints, rvec, tvec, cameraMatrix, distCoeffs[, ...]) -> (imagePoints, jacobian)`.
- **Boş distorsiyon:** `(0,)` şekilli dizi iki fonksiyonda da kabul edilir ve "distorsiyon yok" anlamına gelir.
- **Önemli:** `undistortPoints` yakınsamadığında hata vermez, sonlu ama yanlış bir değer döndürür. Bu yüzden geri yansıtma kontrolü zorunludur. Örnek: k1 = −1 ile köşe pikseline giden bir nokta yoktur; OpenCV yine de bir değer döndürür ve geri yansıtma hatası yaklaşık 733 px çıkar, fonksiyon da `None` döndürür.
- Bu davranış `test_opencv_undistort_ve_project_points_api_si_dogrulandigi_gibi` testiyle sabitlendi. Test sürümün "5.0." ile başladığını da kontrol eder. OpenCV sürümü bilinçli olarak değiştirilirse test kasıtlı olarak kırılır ve API'nin yeniden doğrulanması gerektiğini gösterir.

## 5. Test sonuçları

- Yerel olarak (laptop, Python 3.12.3) toplam **99 test** var: bu spec'in 94 testi ve mevcut `test_ortam.py`.
- Son çalıştırma: `ruff format` temiz, `ruff check` "All checks passed!", `pytest -q` → `99 passed`.
- Python 3.13 sonucu PR açılınca `ci (3.13)` işinde görülecek.
- Spec'in "Birim testleri" listesinin her maddesi en az bir testle karşılanıyor. Eşleştirme Görev Grubu 4'te yapıldı.
  - **Principal point:** montajsız ve SITL profili (pitch −35° → (0.819, 0, 0.574)).
  - **Bilinen açılar:** kenar pikseli ≈ HFOV/2 = 33.0°.
  - **Montaj:** pitch/yaw/roll ve ZYX sırası.
  - **Distorsiyon gidiş-dönüş:** hata < 1e-4 rad.
  - **Geçersiz girdi:** aralık sınırları ve `None` durumu.
  - **Diğer:** bbox, saflık, ızgarada norm = 1, config.

**m06 ile bağımsız karşılaştırma (CI dışı, bir kez):**
- SITL profilinin sonucu, m06'nın kendi zinciriyle (`tez/sim/araclar/kamera.py`: `Camera.pixel_to_los`, `camera_to_body(35°)`) görüntünün köşe ve kenarları dahil 63 noktasında karşılaştırıldı.
- En büyük fark **1.4e-5°**. Bu fark 35°'nin config'te 0.610865 rad olarak yuvarlanmasından gelir.
- Karşılaştırma repo dışında bir komutla yapıldı; Vision kodu m06'yı import etmez ve Autopilot'ta dosya değişmedi.
- Bu ölçüm SITL doğrulamasının (Görev Grubu 5–6, Ölçüm A) yerine geçmez. Yalnızca iki uygulamanın aynı eksen kurallarını kullandığını gösterir.

## 6. Karşılaşılan sorunlar

- **`.venv` yoktu:** Laptopta Vision'ın `.venv`'i kurulmamıştı. README'deki adımlarla, sabit sürümlü paketlerle kuruldu. Sonuç: OpenCV 5.0.0, NumPy 2.4.6, PyYAML 6.0.3, ruff 0.16.9.
- **PyYAML'da bilimsel gösterim:** PyYAML (YAML 1.1) `1e-3` gibi noktasız bilimsel gösterimi metin olarak okuyor; yükleyici bunu `kamera.distorsiyon[0] bir sayi olmali` hatasıyla reddediyor. Madde 9'un kalibrasyon katsayıları girilirken `1.0e-3` biçimi kullanılmalı; `pi.yaml`'da bununla ilgili bir not var.
- **`yer_tutucu` ve YAML 1.1:** `yes`/`no`/`on`/`off` değerleri boolean olarak kabul ediliyor. Tırnaklı metinler reddediliyor.
- **`bbox_merkezi`'nin hata tipi:** Dizi olmayan bir girdi (ör. `5`) `TypeError` veriyor, `ValueError` değil. İmza `Sequence[float]` olduğu için bu Python kuralına uyuyor; spec ile çelişmiyor, test edilmedi.

## 7. Diğer işlere notlar

- **m15 (Autopilot `ozellik/m15-takip-kodu`):** `grup-0-on-kosullar.md`'deki 5. soru "yön body FRD mi, montaj açısı Pi'de mi uygulanıyor, birim vektör mü?" diye soruyor. Bu spec'e göre üçünün de cevabı **evet**. Diğer sorular (hız, yaş, mesaj yerleşimi, "hedef yok", sıra no, hedef seçimi, bağlantı) m10'un kapsamı dışında.
- **Mesaj biçimi:** m06 `TEZ_LOS` (`DEBUG_VECT`), m15 ise `AF_LOS` (`DEBUG_FLOAT_ARRAY`) varsayıyor. İkisi de bu spec'in çıktısıyla aynı içeriği bekliyor. Hangisinin kullanılacağı ortak spec m05'te kararlaştırılmalı.
- **Ertelenenler:** Görev Grubu 5 (m06 koşu değerlendirme script'i) ve 6 (SITL ölçümü). Sim bağlanınca `tasks.md`'deki adımlarla yapılır; kurulum gereksinimleri 6.1'de.
- **`tez-*` tag'i:** Kural 6'daki tag SITL ölçümünden sonra ekip tarafından açılır.
