# Specification: m10 — Piksel koordinatından body frame hedef vektörüne dönüşüm

## Goal
Görüntüdeki bir piksel (u, v) koordinatını, kamera iç parametreleri ve montajı kullanarak İHA body frame'inde birim görüş doğrultusuna (line-of-sight) çeviren saf, donanımsız ve test edilebilir Python fonksiyonları eklemek. Doğruluğu bilinen geometrilerle birim testlerinde ve SITL'de Gazebo ground truth'a karşı açısal hata (derece) olarak ölçmek.

## User Stories
- Hedef seçimi, gönderim ve kontrol maddelerinde (11, 12, 13) çalışan bir ekip üyesi olarak, algılanan kişinin body frame'deki birim doğrultusunu tek bir fonksiyondan almak istiyorum. Böylece kamera geometrisiyle uğraşmadan kendi işime odaklanabilirim.
- Vision geliştiricisi olarak dönüşümü kamera, Gazebo ve Pixhawk olmadan CI'da (3.12 ve 3.13) test edebilmek istiyorum. Böylece eksen veya işaret hataları uçuştan önce yakalanır.
- Tez yazarı olarak dönüşümün SITL'de ölçülmüş açısal hatasını tablo halinde istiyorum. Böylece yöntemin doğruluğunu sayısal olarak raporlayabilirim.

## Specific Requirements

**Piksel → body frame birim doğrultu dönüşümü (çekirdek)**
- Zincir: piksel (u, v) → distorsiyon giderme → normalize görüntü koordinatı (x_n, y_n) → camera (optik) frame doğrultusu (x_n, y_n, 1) → camera → body rotasyonu → normalize edilmiş body FRD vektörü.
- Çıktı: `float64` NumPy dizisi, şekli (3,), normu 1 (birimsiz). Geometrik çözüm yoksa `None` döner (bkz. geçersiz girdi maddesi).
- Fonksiyon saf ve durumsuzdur: kamera modeli nesnesini argüman olarak alır. Global durum, dosya okuma, loglama veya donanım erişimi yapmaz.
- Öteleme (lever arm) çıktıda kullanılmaz; doğrultunun orijini body orijini kabul edilir (bkz. Varsayımlar). Mesafe ve 3B konum üretilmez.
- Algılama modeline, Gazebo'ya, picamera2'ye ve pymavlink'e import bağımlılığı yoktur. Yalnızca NumPy ve OpenCV kullanılır.
- Önerilen yer `src/vision/` altında iki modül: kamera modeli ve config için bir modül (öneri `kamera_modeli.py`), dönüşüm için bir modül (öneri `gorus_dogrultusu.py`). Adlar bu spec'in önerisidir; işi yapan kişi değiştirebilir, ön ek yoktur.
- Herkese açık fonksiyonlarda tip ipuçları ve docstring zorunludur. Docstring'de frame (OpenCV optik / FRD) ve birimler yazılır.

**Girdi: piksel ve bbox merkezi**
- Ana girdi: float (u, v) pikseli, OpenCV kuralıyla (orijin sol üst, u sağa, v aşağı, tam sayı değer piksel merkezi).
- Geçerli aralık −0.5 ≤ u ≤ w − 0.5 ve −0.5 ≤ v ≤ h − 0.5'tir (w, h: config'teki çözünürlük).
- Küçük bir yardımcı fonksiyon bbox'ı (x_min, y_min, x_max, y_max; piksel) alıp merkezini verir. Tipik kullanım bbox merkezidir; bbox formatı da bir varsayımdır.
- Herhangi bir (u, v) kabul edilir; ayak noktası veya başka bir özel nokta seçimi bu spec'te yoktur.

**Kamera iç parametreleri ve distorsiyon**
- Parametreler: çözünürlük (w, h), fx, fy, cx, cy (piksel) ve OpenCV distorsiyon katsayıları (uzunluk 0, 4, 5, 8, 12 veya 14; boş liste distorsiyon yok demektir).
- Distorsiyon giderme `cv2.undistortPoints` ile yapılır. Yakınsama kriteri açıkça verilir. OpenCV 5.0.0.93'teki imza ve modül yeri uygulamada doğrulanır ve bir testle sabitlenir.
- Distorsiyon sıfır olsa da aynı kod yolu kullanılır. Madde 9'un katsayıları yalnızca config değiştirilerek eklenebilmelidir.
- Değerler değişmez (frozen) bir veri sınıfında tutulur. Oluşturulurken doğrulanır: w, h > 0; fx, fy > 0; tüm değerler sonlu; katsayı sayısı izin verilen bir değer. Aksi halde `ValueError`.

**Kamera montajı (camera → body)**
- Montaj, kameranın body FRD'ye göre roll, pitch, yaw açılarıyla (radyan, ZYX sırası: önce yaw, sonra pitch, sonra roll) ve FRD ötelemesiyle (metre) tanımlanır.
- Açıların hepsi 0 iken optik eksen (z) body +x'e, görüntü sağı (optik x) body +y'ye, görüntü aşağısı (optik y) body +z'ye denk gelir. Toplam rotasyon, montaj rotasyonu ile bu sabit eksen eşlemesinin bileşkesidir.
- İşaret kuralı: pozitif pitch optik ekseni yukarı kaldırır, yani aşağı eğik bir kameranın pitch değeri negatiftir. Bu kural testle sabitlenir.
- Rotasyon NumPy ile hesaplanır, SciPy kullanılmaz. Elde edilen matrisin ortonormal ve determinantının +1 olduğu kontrol edilir.
- Öteleme config'te ve veri sınıfında saklanır, ama doğrultu hesabına girmez. SITL doğrulamasında ve ileride 3B konum hesabında kullanılabilir.
- Kamera gövdeye sabittir; gimbal desteği yoktur.

**Config profilleri (YAML)**
- Her profil tek bir YAML dosyasıdır. İçinde `kamera` (iç parametreler) ve `montaj` bölümleri vardır; her bölümün kendi `yer_tutucu` bayrağı olur. Dosyalar repo içinde `src/` dışında durur (öneri: `config/kamera/`).
- SITL profili, Gazebo `mono_cam` ve `x500_mono_cam` değerlerinden elle kopyalanır: 1280×960, fx = fy = 640 / tan(1.74 / 2) ≈ 539.9 px, cx = 640, cy = 480, distorsiyon yok. Montaj açıları 0, öteleme FRD'de (0.12, −0.03, −0.242) m. `yer_tutucu: false`. Türetme ve kaynak SDF yolu yorumda yazılır.
- Pi profili Raspberry Pi Camera Module 3 standart (Wide değil) içindir. Çözünürlük sensör modlarından biri olarak seçilir (ör. 2304×1296), intrinsics nominal datasheet HFOV'undan (yaklaşık 66°) hesaplanır, distorsiyon boş bırakılır. Bunlar karar değildir; `yer_tutucu: true` ve "kalibre edilmemiş, madde 9'da ölçülecek" notu yazılır.
- Gerçek araç montajı bilinmiyor. Açılar 0 ve öteleme 0 girilir, `yer_tutucu: true` ve "kameranın bakış yönü ve eğimi belli değil" notu yazılır.
- Yükleme fonksiyonu YAML yolunu argüman olarak alır. Hiçbir yol kodda sabit yazılmaz ve `../` kullanılmaz. PyYAML `safe_load` kullanılır.
- Eksik anahtar, yanlış tip veya geçersiz değer, hangi alanın hatalı olduğunu söyleyen bir `ValueError` üretir. Yer tutucu bir profil yüklenirse `logging` ile bir kez uyarı verilir.
- Simülasyon ile Pi arasındaki fark yalnızca hangi profilin seçildiğidir; kodda `if simulation:` dalı olmaz.

**Geçersiz girdi ve "çözüm yok" davranışı**
- u veya v NaN/Inf ise ya da geçerli aralığın dışındaysa `ValueError` fırlatılır; mesajda değer ve sınırlar yazar.
- Distorsiyon giderme sonlu bir sonuç vermezse ya da sonucun `cv2.projectPoints` ile geri yansıtılmış hali girdiden bir toleranstan fazla uzaksa `None` döner. Bu durum güçlü distorsiyonda kenar piksellerde yakınsamama olarak görülür.
- Geri yansıtma toleransı (piksel) fonksiyonun varsayılan bir argümanıdır. Değeri ve gerekçesi docstring'de yazar.
- `None` veya `ValueError` sonucunun ICD'deki "hedef yok" karşılığı burada tanımlanmaz (madde 5 ve 11).

**Attitude kullanım kararı (seçenek a) ve gerekçesi**
- (a) Attitude kullanılmaz; çıktı saf body frame doğrultusudur. **Bu adım için seçilen seçenek budur.**
- (b) Roll/pitch ile yataylaştırılmış doğrultu ve düz zemin kesişimiyle konum. İrtifa ve attitude gerektirir. Kapsam dışıdır.
- (c) Tam attitude ile yerel NED doğrultusu ve konumu. Yaw kestirimi ve zaman eşleşmesi gerektirir. Kapsam dışıdır.
- Gerekçe: Pi'de attitude kullanmak için PX4'ten MAVLink ile okuma ve kare zamanıyla eşleştirme gerekir. Bu, ek gecikme ve zaman eşleşme hatası getirir. Body frame doğrultusu ise attitude'dan bağımsızdır. Yataylaştırma gerekirse attitude'a doğrudan sahip olan PX4 tarafında yapılabilir.
- Bu kesin bir mimari karar değildir. Kontrol (madde 13) ve PX4 entegrasyonu maddelerinde yeniden değerlendirilir. Kare–attitude zaman eşleşmesi ve gecikme telafisi yalnızca not olarak kalır.
- Dönüşüm modülünün docstring'inde çıktının attitude'dan bağımsız body frame doğrultusu olduğu yazılır.

**Birim testleri (pytest, CI'da 3.12 ve 3.13)**
- Principal point (cx, cy) → (1, 0, 0). Sonuç her durumda normu 1 olan bir vektördür.
- Bilinen açılar: u = cx + fx·tan(θ) → doğrultu yatayda θ kadar sağdadır (y > 0). v > cy → z > 0 (aşağı). SITL profilinde yatay kenar pikseli ≈ HFOV/2 ≈ 49.85° verir.
- Montaj: pitch = −90° iken principal point → (0, 0, 1). Yaw = +90° iken principal point → (0, 1, 0). Roll'ün görüntü eksenlerine etkisi de bilinen bir vektörle sınanır.
- Distorsiyon gidiş-dönüş: sıfır olmayan katsayılarla bilinen body doğrultuları `cv2.projectPoints` ile piksele, oradan fonksiyonla geri çevrilir. Açısal fark çok küçük bir toleransın (ör. 1e-4 rad) altında kalmalıdır.
- Geçersiz girdi: NaN, Inf ve aralık dışı piksel → `ValueError`. Yakınsamayan aşırı distorsiyonlu bir durum → `None`.
- Config: SITL profilinin değerleri HFOV 1.74 rad ve 1280×960 formülüyle tutarlıdır (sabitler testte değer olarak yazılır, SDF okunmaz). Pi profili yüklenir ve `yer_tutucu` bayrağı doğrudur. Eksik veya hatalı alanlar `ValueError` üretir. Uyarı `caplog` ile doğrulanır.
- Testler donanım, Gazebo ve ağ olmadan çalışır. Mevcut `tests/` düzenine uyar (öneri: `tests/test_kamera_modeli.py`, `tests/test_gorus_dogrultusu.py`).

**SITL doğrulama script'i: kurulum ve hedef**
- Vision repoda `src/` dışında bir script olur (öneri: `scripts/` altında). Elle çalıştırılır, CI'da çalışmaz. Yine de `ruff format` ve `ruff check` kurallarına uyar. Çatı reposuna veya Autopilot'a hiçbir dosya yolu ile bağımlı değildir.
- Ortam: laptop, Gazebo Harmonic + PX4 SITL `make px4_sitl gz_x500_mono_cam` (varsayılan dünya `default`). Gazebo için apt paketleri `python3-gz-transport13` ve `python3-gz-msgs10` gerekir; bunlar yalnızca bu script'te import edilir. Yeni pip paketi eklenmez.
- Hedef nesne, SITL çalışırken dünyanın `create` servisiyle satır içi SDF olarak spawn edilir. Yeri `set_pose` servisiyle değiştirilir, iş bitince `remove` servisiyle silinir. Hiçbir model veya dünya dosyası eklenmez.
- Hedef statik, küçük bir küredir (öneri: yarıçap 0.25 m). Sahnede başka bir şeyle karışmayacak doygun bir renkte ve emissive malzemeyle tanımlanır. Böylece renk eşiklemesi ışıktan bağımsız olur ve blob merkezi kürenin merkezine yakın düşer.
- Topic ve servis adları uygulamada `gz topic -l` / `gz service -l` ile doğrulanıp script argümanı ya da sabiti olarak yazılır. Beklenenler: `/world/default/create`, `/world/default/set_pose`, `/world/default/remove`, kamera görüntüsü `.../x500_mono_cam_0/link/camera_link/sensor/imager/image`, kamera bilgisi `.../camera_info`, pozlar `/world/default/pose/info` veya `dynamic_pose/info`.
- Script, config'teki SITL intrinsics değerlerini Gazebo'nun yayınladığı `camera_info` ile karşılaştırır. Fark varsa raporlar ve ölçüm sonuçlarına not düşer.
- Araç, PX4 konsolundan veya QGC'den elle kaldırılır. Script MAVLink ile komut göndermez. PX4 MAVLink ATTITUDE ile ölçüm madde 4 kesinleşene kadar yapılmaz.

**SITL ölçümü, metrikler ve raporlama**
- Piksel: kamera karesinde HSV renk eşiklemesiyle bulunan en büyük blob'un merkezi (görüntü momentleri). Blob görüntü kenarına değiyorsa veya alanı bir eşiğin altındaysa o kare atılır.
- Ground truth: Gazebo'dan okunan İHA (`x500_mono_cam_0` model/base_link) pozu ve hedef pozu kullanılır. Hedefin dünya konumundan kamera konumu çıkarılır, sonuç base_link'in FLU frame'ine çevrilir, sonra FRD'ye geçirilir (y → −y, z → −z) ve normalize edilir. İHA pozu yalnızca değerlendirmede kullanılır; algoritmanın girdisi değildir.
- Kamera konumu, Gazebo `camera_link` pozu yayınlanıyorsa oradan, yayınlanmıyorsa config'teki ötelemeden alınır. Hangisinin kullanıldığı sonuçlara yazılır.
- Ana metrik, hesaplanan doğrultu ile ground truth arasındaki açıdır (derece): ortalama, RMS ve maksimum. Ground truth kamera konumundan hesaplanır. Ek metrik olarak ground truth body orijininden de hesaplanır; böylece ötelemeyi ihmal etmenin etkisi (paralaks, yakın mesafede birkaç derece olabilir) ayrıca görülür.
- Senaryolar: en az 3 irtifa (yerde ve 2 farklı hover irtifası) ve birkaç mesafe (ör. 3, 8, 15 m). Hedef konumları görüntü merkezini, kenarlarını ve köşelerini kapsayan bir ızgaraya dağıtılır; sonuçlar bölgeye göre (merkez / kenar / köşe) ayrıca verilir. Yerin altına düşen konumlar atlanır.
- Hedef konumu SITL nominal pinhole modeliyle hedeflenir. Bu yalnızca nişan almak içindir; ölçülen piksel daima görüntüden gelir.
- Zaman eşleşmesi: görüntü ve poz mesajlarının sim time zaman damgaları en yakın eşleşmeyle eşlenir. Ardışık pozlarda açı değişimi eşiği aşan (araç durağan değil) kareler atılır. Ölçüm yalnızca yerde veya hover'da yapılır.
- Kesin bir başarı eşiği konmaz. Sonuç tablosu ve kısa yorum spec klasörüne (öneri: `implementation/sitl-dogrulama-sonuclari.md`) yazılır. Kullanılan Autopilot ve Vision commit'leri ile sürümler de oraya eklenir. Kural 6 gereği iki repo aynı `tez-*` tag'iyle işaretlenir; tag'i ekip açar. Kare, video ve log repoya girmez.

## Varsayımlar
Ortak spec'ler (madde 3: frame tanımları, madde 4: haberleşme, madde 5: ICD) yazılmadığı için aşağıdakiler bu spec'e özgü varsayımlardır, kesinleşmiş değildir. Ortak spec'ler yazılınca bu spec, config ve kod onlara göre güncellenir.
- **Camera frame:** OpenCV optik frame: x sağ, y aşağı, z ileri (optik eksen). Piksel kuralı OpenCV'ninkidir: orijin sol üst, tam sayı değer piksel merkezi.
- **Body frame:** PX4 FRD: x ileri, y sağ, z aşağı. Orijin base_link'tir. Doğrultu çıktısında kamera ile body orijini arasındaki öteleme ihmal edilir.
- **Yerel dünya frame'i (gerekirse):** NED. Bu spec'in çıktısında kullanılmaz.
- **Birimler:** uzunluk metre, açı radyan (config dahil); raporlarda derece kullanılır. Çıktı vektörü birimsizdir, normu 1'dir.
- **Attitude gösterimi (ileride gerekirse):** quaternion (w, x, y, z), NED → FRD. Bu adımda kullanılmaz.
- **Gazebo ↔ PX4:** Gazebo model frame'i FLU, dünya frame'i ENU'dur. FLU → FRD dönüşümü x ekseni etrafında 180°'dir (y → −y, z → −z). Gazebo kamerası link'in +x eksenine bakar. `x500_base`'de base_link'e ayrı poz verilmediği için model pozu base_link pozu kabul edilir ve Gazebo base_link orijininin PX4 body orijiniyle çakıştığı varsayılır.
- **Gazebo kamera iç parametreleri:** kare piksel (fy = fx), cx = w/2, cy = h/2. Gazebo kuralıyla OpenCV'nin piksel merkezi kuralı arasında olası yarım piksellik (≈0.05°) fark ihmal edilir; `camera_info` karşılaştırmasıyla kontrol edilir.
- **Mesaj, frekans, zaman damgası, bbox formatı ve "hedef yok" gösterimi** bu spec'te tanımlanmaz (madde 5, 7, 11).

## Existing Code to Leverage

**Vision paket iskeleti ve araç ayarları (`src/vision/__init__.py`, `pyproject.toml`)**
- Yeni modüller mevcut `vision` paketine eklenir (setuptools `where = ["src"]`). Paket yapısında değişiklik gerekmez.
- Ruff ayarları geçerlidir: satır uzunluğu 100, hedef `py312`, `ANN` dahil kurallar (testlerde `ANN` muaf). Script de bu kurallara uyar.
- pytest `testpaths = ["tests"]` olduğundan script test olarak toplanmaz.

**Mevcut test düzeni (`tests/test_ortam.py`)**
- Düz pytest fonksiyonları, Türkçe ve `snake_case` test adları, dosya başında docstring. Yeni testler aynı üslupta yazılır.
- `test_opencv_numpy_ile_calisiyor` OpenCV'nin CI'da (headless) çalıştığını zaten gösteriyor; `cv2.undistortPoints` ve `cv2.projectPoints` testleri aynı ortamda çalışır.

**Sabit bağımlılıklar (`requirements/common.txt`, `ci.txt`, `laptop.txt`, `pi.txt`)**
- NumPy 2.4.6, PyYAML 6.0.3 ve OpenCV 5.0.0.93 (headless / GUI) zaten sabit; `requirements/` değişmez.
- Gazebo Python bağları `laptop.txt` notunda yazıldığı gibi apt'den gelir ve yalnızca doğrulama script'inde kullanılır.

**CI iş akışı (`.github/workflows/ci.yml`)**
- `ci (3.12)` ve `ci (3.13)` işleri yeni testleri ve ruff kontrollerini değişiklik gerekmeden çalıştırır. Workflow dosyası değiştirilmez.

**Gazebo kamera ve montaj değerleri (salt okunur referans)**
- `Autopilot/Tools/simulation/gz/models/mono_cam/model.sdf`: `horizontal_fov` 1.74 rad, 1280×960, 30 Hz; sensör adı `imager`, link `camera_link`.
- `Autopilot/Tools/simulation/gz/models/x500_mono_cam/model.sdf`: kamera base_link'e göre `.12 .03 .242`, açı `0 0 0` (sabit eklem).
- Bu değerler SITL config'ine yalnızca değer olarak kopyalanır. Kural 7 gereği ne `src/` ne de script bu dosyalara yol ile başvurur. Kilitli submodule'e dosya eklenmez.

## Out of Scope
- 3B hedef konumu, mesafe tahmini ve zemin kesişimi (seçenek b ve c); yalnızca attitude kararında karşılaştırılır.
- Attitude'un çıktıda kullanılması, kare–attitude zaman eşleşmesi ve gecikme telafisi (yalnızca not olarak kalır).
- İnsan algılama modeli ve Hailo'suz algılama (madde 7, 8); model indirmek veya `model-training` branch'indeki ağırlıkları kullanmak.
- Hedef seçimi ve ICD'deki "hedef yok" çıkışı (madde 11).
- Camera Module 3 kalibrasyonu ve gerçek araçta kamera montajının ölçülmesi (madde 9 ve sonrası).
- MAVLink ile gönderim, haberleşme yöntemi, ICD mesaj formatı (madde 4, 5, 12) ve PX4 MAVLink ATTITUDE ile ölçüm.
- Hedef vektörünün filtrelenmesi veya takibi (Kalman vb.) ve bir canlı işleme döngüsü (kamera okuma, zamanlama).
- Hareketli insan hedefi simülasyonu ve simülasyon kamerası kararı (madde 6); `gz_x500_mono_cam` bu spec'te yalnızca ölçüm için kullanılır.
- Gazebo model veya dünya dosyası eklemek ve PX4 ağacında (`Tools/simulation/gz` dahil) değişiklik yapmak.
- Gimbal, birden fazla kamera ve yeni pip paketi (SciPy vb.) eklemek.
