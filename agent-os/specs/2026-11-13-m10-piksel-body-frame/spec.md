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
- SITL profili, m06 simülasyonundaki `x500_tez` modelinin değerlerinden elle kopyalanır (kaynak: Autopilot `ozellik/m06-sim-ortami`, `tez/sim/kamera_montaji.yaml` ve `tez/sim/models/x500_tez/model.sdf`): 2304×1296, HFOV 1.151917 rad (66.0°), fx = fy = 1152 / tan(1.151917 / 2) ≈ 1773.9 px, cx = 1152, cy = 648, distorsiyon yok. Montaj: roll 0, pitch −0.610865 rad (35° aşağı), yaw 0; öteleme FRD'de (0.151, 0, 0.035) m. `yer_tutucu: false`. Türetme, kaynak dosya yolları ve m06 commit'i yorumda **yalnızca metin olarak** yazılır.
- Pi profili Raspberry Pi Camera Module 3 standart (Wide değil) içindir. Kamera bölümü simle aynı nominal değerleri taşır (2304×1296, datasheet HFOV ≈ 66°, distorsiyon boş). Bunlar karar değildir; `yer_tutucu: true` ve "kalibre edilmemiş, madde 9'da ölçülecek; çözünürlük belli değil" notu yazılır.
- Gerçek araç montajı henüz yapılmadı. m06'nın önerisi (35° aşağı, öteleme FRD (0.151, 0, 0.035) m) girilir; `yer_tutucu: true` ve "önerilen değer; montaj takılınca açı araçta ±0.5° ölçülüp girilecek" notu yazılır.
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
- Bilinen açılar: u = cx + fx·tan(θ) → doğrultu yatayda θ kadar sağdadır (y > 0). v > cy → z > 0 (aşağı). Montajsız (açılar 0) SITL iç parametreleriyle yatay kenar pikseli (u = w − 0.5) ≈ HFOV/2 ≈ 33.0° verir (yarım piksel farkı toleransa dahildir).
- Montaj: pitch = −90° iken principal point → (0, 0, 1). Yaw = +90° iken principal point → (0, 1, 0). SITL profilinde (pitch −35°) principal point → (cos 35°, 0, sin 35°) ≈ (0.819, 0, 0.574). Roll'ün görüntü eksenlerine etkisi de bilinen bir vektörle sınanır.
- Distorsiyon gidiş-dönüş: sıfır olmayan katsayılarla bilinen body doğrultuları `cv2.projectPoints` ile piksele, oradan fonksiyonla geri çevrilir. Açısal fark çok küçük bir toleransın (ör. 1e-4 rad) altında kalmalıdır.
- Geçersiz girdi: NaN, Inf ve aralık dışı piksel → `ValueError`. Yakınsamayan aşırı distorsiyonlu bir durum → `None`.
- Config: SITL profilinin değerleri HFOV 1.151917 rad ve 2304×1296 formülüyle, montajı 35° aşağı ve FRD (0.151, 0, 0.035) m ile tutarlıdır (sabitler testte değer olarak yazılır; Autopilot'taki YAML/SDF okunmaz). Pi profili yüklenir ve `yer_tutucu` bayrağı doğrudur. Eksik veya hatalı alanlar `ValueError` üretir. Uyarı `caplog` ile doğrulanır.
- Testler donanım, Gazebo ve ağ olmadan çalışır. Mevcut `tests/` düzenine uyar (öneri: `tests/test_kamera_modeli.py`, `tests/test_gorus_dogrultusu.py`).

**SITL doğrulaması: ortam ve veri kaynağı (m06 simülasyonu)**
- Ortam: laptop, Autopilot'taki m06 simülasyonu (`tez/sim`, Gazebo Harmonic + PX4 SITL v1.17.0, araç `x500_tez`). m06 main'e girene kadar `ozellik/m06-sim-ortami` branch'indedir; ölçümde kullanılan Autopilot commit'i sonuçlara yazılır. Kurulum ve çalıştırma m06'nın kendi belgesine göre yapılır (`tez/sim/README.md` "A. Kurulum", `EKIP_ICIN_OZET.md` bölüm 6–7). Autopilot'ta hiçbir dosya değişmez.
- Koşular m06'nın senaryo yöneticisiyle (`tez/sim/araclar/senaryo.py`, `toplu.py`) üretilir. Her koşu `tez/sim/sonuclar/<klasör>/` altına (git'e girmez) `dogru_cevap.csv`, `ozet.json` ve model açıksa `algilama.csv`, `kutular.csv` yazar.
- Vision tarafında yalnızca bir **değerlendirme script'i** olur (öneri: `scripts/` altında, `src/` dışında). Elle çalıştırılır, CI'da çalışmaz, `ruff format` / `ruff check` kurallarına uyar. Koşu klasörünü **argüman olarak** alır ve yalnızca CSV/JSON dosyalarını okur. Autopilot'un kodunu import etmez, sabit bir Autopilot yolu içermez (kural 7'nin ruhu: veri bağımlılığı var, kod bağımlılığı yok). Çekirdek fonksiyonlar `vision` paketinden import edilir; geometri yeniden yazılmaz.
- Script Gazebo'ya bağlanmaz, gz import etmez, MAVLink göndermez. Yeni pip paketi eklenmez; CSV okuma için standart kütüphane (`csv`, `json`) ve NumPy yeterlidir (pandas `requirements/`'ta olmadığı için kullanılmaz).
- Script, koşunun `ozet.json`'undaki kamera kalibrasyonunu (camera_info iç parametreleri) ve montajını (ofset, C_cb) Vision SITL profiliyle karşılaştırır. Fark varsa raporlar ve sonuçlara not düşer. Alan adları uygulamada gerçek bir koşu dosyasından doğrulanır.

**SITL ölçümü, metrikler ve raporlama**
- Ground truth: `dogru_cevap.csv`'deki `los_govde_x/y/z`. m06 bunu her kamera karesinde Gazebo'nun İHA pozundan ve `camera_link` pozundan hesaplar; kameradan hedefin gövde merkezine (yerden 0.9 m) giden, gövde FRD'de birim vektördür. İHA pozu yalnızca değerlendirmede kullanılır; Vision algoritmasının girdisi değildir.
- Ölçüm A, geometrik (ana metrik): aynı satırdaki `merkez_u/v` (hedefin gövde merkezinin pikseli; yalnızca `kadrajda` olan satırlar) Vision fonksiyonuna verilir, sonuç `los_govde` ile karşılaştırılır. Bu ölçüm Vision'ın config'ini (iç parametreler + 35° montaj) ve dönüşüm zincirini m06'nın bağımsız zincirine (Gazebo'nun bildirdiği kamera pozu ve camera_info) karşı sınar. Beklenen hata çok küçüktür; büyük hata eksen, işaret veya config hatası demektir.
- Ölçüm B, görüntüden (ek metrik): segmentasyon kamerasından gelen hedef kutusunun (`hedef_kutu_u0/v0/u1/v1`, yalnızca `gorunur` satırlar) merkezi Vision fonksiyonuna verilir ve `los_govde` ile karşılaştırılır. Bu ölçüm render edilmiş görüntüye dayanır. Kutu merkezi ile gövde merkezi aynı nokta olmadığı için hatanın bir kısmı dönüşümden değil hedef noktası seçiminden gelir; bu yorumda ayrıca belirtilir.
- Ölçüm C, model kutusu (isteğe bağlı, model açık bir koşu varsa): `algilama.csv`'deki seçilen kutunun (`secilen_u0…v1`) merkezi Vision fonksiyonuna verilir. Sonuç iki şeyle karşılaştırılır: `t_us` ile birleştirilen `los_govde` ve m06'nın aynı kutu için hesapladığı `los_i_x/y/z`. İkinci fark iki uygulamanın tutarlılığını gösterir ve ≈ 0 olmalıdır. Vision kodu modeli çalıştırmaz; kutular yalnızca veri olarak okunur.
- Ek metrik (paralaks): ground truth ayrıca body orijininden hesaplanır (`dogru_cevap.csv`'deki İHA konumu ve quaternion'u, hedef konumu ve 0.9 m yükseklik; ENU/FLU → FRD). Böylece ötelemeyi ihmal etmenin etkisi görülür; `x500_tez`'de öteleme küçüktür (0.151 m ileri, 0.035 m aşağı).
- Metrikler: açısal hata (derece), ortalama, RMS ve maksimum. Her ölçüm (A, B, C) ayrı verilir; toplamda ve piksel bölgesine göre (merkez / kenar / köşe; sınırlar script'te adlandırılmış sabit) ayrıca raporlanır. Yürüyen insan görüntünün her bölgesini kapsamayabilir; her bölgedeki satır sayısı yazılır.
- Senaryolar: en az iki koşu. Birincisi araç havada sabitken (`takip: yok`, ör. `yuruyen_insan`; modelsiz olabilir). İkincisi araç takip ederken (ör. `takip_yuruyen`); bu koşuda attitude ve konum değişir, body frame doğrultusunun attitude'dan bağımsız olduğu görülür. Model açık bir koşu varsa Ölçüm C de yapılır. Kullanılan senaryolar, irtifalar, model dosyası ve sha256'sı sonuçlara yazılır.
- Zaman eşleşmesi gerekmez: piksel ve ground truth aynı `dogru_cevap.csv` satırından gelir. Ölçüm C'de `t_us` anahtarıyla birleştirilir.
- Kesin bir başarı eşiği konmaz. Sonuç tablosu ve kısa yorum spec klasörüne (öneri: `implementation/sitl-dogrulama-sonuclari.md`) yazılır. Kullanılan Autopilot (m06 branch commit'i) ve Vision commit'leri ile sürümler de oraya eklenir. Kural 6 gereği iki repo aynı `tez-*` tag'iyle işaretlenir; tag'i ekip açar. Koşu klasörleri, CSV'ler, kare, video ve log repoya girmez.

## Varsayımlar
Ortak spec'ler (madde 3: frame tanımları, madde 4: haberleşme, madde 5: ICD) yazılmadığı için aşağıdakiler bu spec'e özgü varsayımlardır, kesinleşmiş değildir. Ortak spec'ler yazılınca bu spec, config ve kod onlara göre güncellenir.
- **Camera frame:** OpenCV optik frame: x sağ, y aşağı, z ileri (optik eksen). Piksel kuralı OpenCV'ninkidir: orijin sol üst, tam sayı değer piksel merkezi.
- **Body frame:** PX4 FRD: x ileri, y sağ, z aşağı. Orijin base_link'tir. Doğrultu çıktısında kamera ile body orijini arasındaki öteleme ihmal edilir.
- **Yerel dünya frame'i (gerekirse):** NED. Bu spec'in çıktısında kullanılmaz.
- **Birimler:** uzunluk metre, açı radyan (config dahil); raporlarda derece kullanılır. Çıktı vektörü birimsizdir, normu 1'dir.
- **Attitude gösterimi (ileride gerekirse):** quaternion (w, x, y, z), NED → FRD. Bu adımda kullanılmaz.
- **Gazebo ↔ PX4:** Gazebo model frame'i FLU, dünya frame'i ENU'dur. FLU → FRD dönüşümü x ekseni etrafında 180°'dir (y → −y, z → −z). Gazebo kamerası link'in +x eksenine bakar. Model pozu base_link pozu kabul edilir ve Gazebo base_link orijininin PX4 body orijiniyle çakıştığı varsayılır (m06'nın `dogru_cevap.csv`'si de bu varsayımla üretilir).
- **m06 eksen kuralları:** m06'nın `EKIP_ICIN_OZET.md` bölüm 3'teki eksenleri (OpenCV optik, PX4 FRD, Gazebo ENU/FLU, eğim 0'da optik z → x, x → y, y → z) bu spec'tekilerle aynıdır. m06'nın "35° aşağı eğim" değeri, bu spec'in kuralıyla pitch = −35° demektir. İkisi de varsayımdır; ortak spec madde 3 yazılınca ikisi birlikte güncellenir.
- **Gazebo kamera iç parametreleri:** kare piksel (fy = fx), cx = w/2, cy = h/2. Gazebo kuralıyla OpenCV'nin piksel merkezi kuralı arasında olası yarım piksellik (≈0.02°) fark ihmal edilir; `ozet.json`'daki camera_info karşılaştırmasıyla kontrol edilir. Sim kamerasında distorsiyon yoktur, yalnızca görüntü gürültüsü vardır. Distorsiyon yolu SITL'de değil, birim testlerinde sınanır.
- **m06 mesajları:** m06'nın `TEZ_LOS` (`DEBUG_VECT`) ve m15'in `AF_LOS` (`DEBUG_FLOAT_ARRAY`) biçimleri farklı varsayımlardır. İkisi de "gövde FRD birim vektör, montaj açısı Pi'de uygulanmış" içeriğini bekler; bu spec'in çıktısı bu içerikle uyumludur. Mesaj biçimi bu spec'te seçilmez (madde 5, 12).
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
- Değerlendirme script'i Gazebo Python bağlarını kullanmaz; m06 simülasyonu kendi ortamında (`.venv-tez`) çalışır.

**CI iş akışı (`.github/workflows/ci.yml`)**
- `ci (3.12)` ve `ci (3.13)` işleri yeni testleri ve ruff kontrollerini değişiklik gerekmeden çalıştırır. Workflow dosyası değiştirilmez.

**m06 simülasyonu (Autopilot `ozellik/m06-sim-ortami`, salt okunur referans)**
- `tez/sim/kamera_montaji.yaml`: kamera ve montaj değerlerinin tek dosyası. Dosyanın kendi notu da Vision'ın değerleri kendi config'ine kopyalamasını, dosyayı çalışma zamanında okumamasını söyler.
- `tez/sim/models/x500_tez/model.sdf`: `camera_link` base_link'e göre `0.151 0 -0.035 0 0.610865 0` (FLU, 35° aşağı), HFOV 1.151917 rad, 2304×1296, 30 Hz, distorsiyon yok.
- `tez/sim/araclar/kamera.py`: m06'nın aynı zinciri bağımsız olarak uygulayan kodu (`Camera.pixel_to_los`, `camera_to_body`). Vision bu kodu import etmez ve kopyalamaz; sonuçları Ölçüm A ve C'de karşılaştırılır.
- `tez/sim/README.md` "Doğru cevap, görüş vektörü ve görünürlük": `dogru_cevap.csv`, `algilama.csv`, `kutular.csv` sütunlarının tanımı.
- Bu değerler SITL config'ine yalnızca değer olarak kopyalanır. Kural 7 gereği ne `src/` ne de script bu dosyalara yol ile başvurur. Autopilot'a dosya eklenmez.

## Out of Scope
- 3B hedef konumu, mesafe tahmini ve zemin kesişimi (seçenek b ve c); yalnızca attitude kararında karşılaştırılır.
- Attitude'un çıktıda kullanılması, kare–attitude zaman eşleşmesi ve gecikme telafisi (yalnızca not olarak kalır).
- İnsan algılama modeli ve Hailo'suz algılama (madde 7, 8). Vision kodu modeli çalıştırmaz; m06 koşusunda model açıksa onun kutuları yalnızca veri olarak okunur (Ölçüm C).
- Hedef seçimi ve ICD'deki "hedef yok" çıkışı (madde 11).
- Camera Module 3 kalibrasyonu ve gerçek araçta kamera montajının ölçülmesi (madde 9 ve sonrası).
- MAVLink ile gönderim, haberleşme yöntemi, ICD mesaj formatı (madde 4, 5, 12) ve PX4 MAVLink ATTITUDE ile ölçüm.
- Hedef vektörünün filtrelenmesi veya takibi (Kalman vb.) ve bir canlı işleme döngüsü (kamera okuma, zamanlama).
- Simülasyon ortamının kendisi (madde 6, m06): bu spec m06'yı olduğu gibi kullanır, değiştirmez. Senaryo, dünya veya model eklemek ve Autopilot'ta (PX4 ağacı ve `tez/sim` dahil) değişiklik yapmak kapsam dışıdır.
- Vision'da Gazebo'ya bağlanan bir script (gz-transport); önceki taslaktaki küre hedef ve `gz service` yaklaşımı m06 kullanıldığı için düşmüştür.
- Gimbal, birden fazla kamera ve yeni pip paketi (SciPy vb.) eklemek.

## Değişiklik kaydı
- 2026-11-20: SITL ortamı stok `gz_x500_mono_cam`'den m06 simülasyonuna (`x500_tez`, Autopilot `ozellik/m06-sim-ortami`) geçti (kullanıcı kararı). SITL profili `tez/sim/kamera_montaji.yaml` değerlerine göre değişti: 2304×1296, HFOV 66°, 35° aşağı, FRD (0.151, 0, 0.035) m. Pi montajına m06 önerisi yer tutucu olarak girildi. Vision'daki gz script'i, küre hedefi ve renk eşiklemesi kaldırıldı. Yerine m06 koşu klasörlerini (`dogru_cevap.csv`, `algilama.csv`, `ozet.json`) okuyan bir değerlendirme script'i geldi (Ölçüm A/B/C). Gerekçe: m06 aynı ground truth'u zaten üretiyor; 35° eğim, pitch işaret kuralını simde de sınıyor; kamera gerçek CM3'e benziyor.
