# Spec Requirements: m10 — Piksel koordinatından body frame hedef vektörüne dönüşüm

## Initial Description

Yol haritası madde 10 — Piksel koordinatından body frame hedef vektörüne dönüşüm. Pixel coordinates → görüş doğrultusu → camera frame → body frame dönüşümü uygulanır; attitude bilgisinin kullanımı değerlendirilir ve gerekçesiyle belgelenir (Vision). Doğrulama: bilinen geometrilerle birim testleri geçer ve SITL'de hesaplanan vektör Gazebo'daki gerçek (ground truth) hedef konumuyla karşılaştırılıp hata ölçülür. Boyut: L.

Not: Ortak spec'ler (madde 3 frame tanımları, 4 haberleşme, 5 ICD) henüz yazılmadı; frame, eksen, birim, mesaj konuları bu spec'te 'Varsayımlar' başlığı altında açıkça yazılacak.

## Requirements Discussion

### First Round Questions

**Q1:** Çıktının ne olduğu: fonksiyon her zaman body frame'de birim görüş doğrultusu (unit line-of-sight / bearing vektörü) üretsin; ek olarak isteğe bağlı bir adım, doğrultuyu düz zemin varsayımıyla zemin düzlemiyle kesiştirip (irtifa + attitude) hedefin 3B konumunu (metre) tahmin etsin. İkisi birden mi, yoksa sadece doğrultu mu (mesafe başka yolla, ör. bbox yüksekliği + varsayılan insan boyu)?
**Answer:** "evet" (Takip sorusu 1 ile netleşti: bu spec'te çıktı yalnızca body frame birim görüş doğrultusu; 3B konum / zemin kesişimi kapsam dışı.)

**Q2:** Girdi, algılama kutusundan (bbox) seçilen tek bir piksel (u, v) (float) olsun; doğrultu için kutu merkezi, zemin kesişimi için kutunun alt-ortası (ayak noktası). Fonksiyon kutuyu da kabul edebilsin. Algılama modeline (madde 7/8) bağımlılık olmasın; saf numpy fonksiyonları. Uygun mu?
**Answer:** "evet" (Takip sorusu 1 ile netleşti: ayak noktası düşer; fonksiyon herhangi bir (u, v) pikselini kabul eder, tipik kullanım bbox merkezidir.)

**Q3:** Frame/eksen varsayımları ("Varsayımlar" bölümüne): camera frame = OpenCV optik frame (x sağ, y aşağı, z ileri); body frame = PX4 FRD (x ileri, y sağ, z aşağı); gerekirse yerel dünya = NED; birimler metre ve radyan; attitude girdisi quaternion (w, x, y, z), NED → FRD. Uygun mu, yoksa farklı bir kural (ör. FLU/ENU)?
**Answer:** "evet"

**Q4:** Kamera montajı (extrinsics): kamera gövdeye sabit, gimbal yok; camera → body dönüşümü YAML config'den (rotasyon roll/pitch/yaw, öteleme metre). Öteleme doğrultu hesabında ihmal edilir, sadece 3B konum hesabında kullanılır. SITL için `x500_mono_cam` değerleri (öne bakan, pitch 0, öteleme (0.12, 0.03, 0.242) m; FLU → FRD dönüşümüyle). Gerçek araçta kameranın bakış yönü ve aşağı eğim açısı belli mi? Değilse config'te yer tutucu.
**Answer:** "Gerçek araçta kameranın bakış yönü ve aşağı eğim açısı henüz belli değil." (Gerçek araç montajı belli değil → config'te açıkça işaretlenmiş yer tutucu. SITL değerleri Takip sorusu 2 ile onaylandı.)

**Q5:** Intrinsics kaynağı: SITL'de fx, fy, cx, cy Gazebo modelindeki HFOV ve çözünürlükten hesaplanıp config'e yazılsın (fx = (w/2) / tan(HFOV/2); distorsiyon sıfır). Pi'de Camera Module 3 için "kalibre edilmemiş, yer tutucu" diye işaretli bir config profili. Distorsiyon için OpenCV modeli (`cv2.undistortPoints`), böylece madde 9 katsayıları kod değişmeden eklenebilir. Camera Module 3 varyantı (standart / Wide) ve Pi'de kullanılacak çözünürlük?
**Answer:** "Raspberry Pi Camera Module 3 standart (Wide değil) kullanılıyor, ancak hangi çözünürlükte çalışacak henüz belli değil." (Pi çözünürlüğü Takip sorusu 4 ile netleşti: belli değil, yer tutucu.)

**Q6:** Attitude kullanımı: (a) hiç kullanılmaz, saf body frame vektörü; (b) roll/pitch ile yataylaştırılmış vektör ve zemin kesişimi; (c) tam attitude ile NED konumu. Önerim: temel çıktı (a), (b) isteğe bağlı fonksiyon; kare–attitude zaman eşleşmesi (gecikme telafisi) bu spec'te sadece belgelenir. Uygun mu?
**Answer:** "çıktı olarak sadece bu adımda a yeterli, attitude verisinin px4'ten okunması ve işlenmesi de gecikme yaratacağı için şu anki adımda gerekli değil." (Gerekçe, Functional Requirements bölümünde ayrıntılı yazılmıştır.)

**Q7:** SITL doğrulamasında piksel ve ground truth: piksel, renkli basit bir hedefin (kutu/silindir) OpenCV renk eşiklemesiyle bulunan merkezi; ground truth İHA ve hedef pozları Gazebo'dan (gz-transport pose topic); algoritmanın attitude girdisi ilk ölçümde Gazebo ground truth'tan. PX4 MAVLink ATTITUDE ile ikinci ölçüm yapılsın mı, yoksa madde 4 kesinleşene kadar beklesin mi?
**Answer:** "Madde 4 kesinleşene kadar beklesin." (Renkli hedef + Gazebo pozları yaklaşımı Takip sorusu 2 ile onaylandı. Sorudaki "algoritmanın attitude girdisi" kısmı Q6'da (a) seçildiği için düşer: algoritmanın attitude girdisi yoktur; Gazebo'daki İHA pozu yalnızca ground truth doğrultuyu body frame'e çevirmek için değerlendirmede kullanılır.)

**Q8:** Test dünyası/modeli nereye konacak? (`Tools/simulation/gz` kilitli; Vision `src/` kodu `../` yoluna başvuramaz.) Doğrulama script'i Vision'da `src/` dışında, CI'da çalışmaz. Gazebo dünya/model dosyaları Vision'da mı, Autopilot'ta mı (`allowed-paths.txt` onayı) yoksa hedef SITL çalışırken `gz service` ile spawn edilip hiç dosya eklenmesin mi (önerim)?
**Answer:** "Algılama modeli ağırlıkları model-training branch'inde duruyor." (Takip sorusu 3 ile netleşti: kastedilen Gazebo dosyaları değil, algılama modeli ağırlıklarıdır; bkz. "Existing Code to Reference". Gazebo hedef nesnesinin dosya eklenmeden `gz service` ile spawn edilmesi kullanıcı tarafından onaylandı (2026-11-13).)

**Q9:** Hata metrikleri: doğrultu için açısal hata (derece) ortalama/RMS/maksimum; 3B konum için hata (metre); birkaç farklı hedef konumu ve irtifada, görüntü kenarı ve merkezi dahil. Spec'te kesin eşik konmasın, sonuçlar raporlanıp tablo spec klasörüne yazılsın. Yoksa geçici bir eşik mi (ör. < 1°)?
**Answer:** "evet" (3B konum hatası, 3B konum kapsam dışı kaldığı için düşer; yalnızca açısal hata ölçülür.)

**Q10:** Geçersiz girdi: piksel görüntü dışında veya NaN/Inf ise `ValueError`; geometrik çözüm yoksa (ör. ışın ufkun üstünde) açık bir "geçersiz" sonucu (`None` ya da geçerlilik bayrağı). ICD'deki "hedef yok" karşılığı madde 5 ve 11'e bırakılsın. Uygun mu?
**Answer:** "evet"

**Q11:** Yeni paket eklenmesin: rotasyonlar NumPy ile, distorsiyon OpenCV ile (SciPy vb. yok). Gazebo pose okuma sadece doğrulama script'inde (apt `python3-gz-transport13`); `src/` içinde Gazebo importu olmasın. Uygun mu?
**Answer:** "evet"

**Q12:** Kapsam dışı: algılama modeli (madde 7/8), hedef seçimi (madde 11), kalibrasyonun kendisi (madde 9), MAVLink gönderimi ve ICD mesaj formatı (madde 4, 5, 12), hedef vektörünün filtrelenmesi/takibi (Kalman vb.), gecikme telafisi, hareketli insan hedefi simülasyonu (madde 6). Eklenecek başka bir şey?
**Answer:** İlk turda yanıtlanmadı; Takip sorusu 4 ile onaylandı, 3B konum / zemin kesişimi de listeye eklendi.

Genel not (kullanıcı): "eksik kalan bir şey varsa tekrardan sor"

### Existing Code to Reference

**Similar Features Identified:**
- Vision reposunda (`main`) yeniden kullanılabilecek geometri, kamera veya config kodu yok; repo iskelet durumunda (`src/vision/__init__.py`, `tests/test_ortam.py`).
- Projeksiyon/dönüşüm benzeri mevcut bir çalışma yok (kullanıcı belirtmedi).
- Bilgi notu (m10'da KULLANILMAYACAK): Vision reposunun `model-training` branch'inde `models/` altında YOLO tabanlı insan algılama ağırlıkları var: `person_detection_model_v0.1.pt`, `person_detection_model_v0.2.pt`, `person_detection_model_v0.3(probably overfitted).pt` (her biri ~22 MB). Kullanıcı bunların yanlış yerde durduğunu ve ileride düzeltileceğini belirtti. Algılama modeli bu spec'in kapsamı dışında olduğu için kullanılmaz; model indirilmez (ör. yolov8n). Not: model ağırlıklarının repoda bulunması kural 9 ile çelişir; düzeltilmesi bu spec'in işi değildir.
- Referans (kilitli, sadece okunur): `Autopilot/Tools/simulation/gz/models/mono_cam/model.sdf` (`horizontal_fov` 1.74 rad ≈ 99.7°, 1280x960, 30 Hz) ve `Autopilot/Tools/simulation/gz/models/x500_mono_cam/model.sdf` (kamera base_link'e göre `.12 .03 .242`, açı 0 0 0, yani öne bakan ve yatay). `x500_mono_cam_down` ise 90° aşağı bakar (kullanılmaz).

### Follow-up Questions

**Follow-up 1:** 3B konum bu spec'te var mı? Önerim: çıktı yalnızca body frame birim görüş doğrultusu; 3B konum ve zemin kesişimi kapsam dışı, seçenek karşılaştırması sadece belgelenir, kod yazılmaz. Bu durumda ayak noktası düşer; dönüştürülen piksel bbox merkezi olur, fonksiyon her türlü (u, v) pikselini kabul eder. Uygun mu?
**Answer:** "Evet"

**Follow-up 2:** SITL doğrulaması: renkli basit hedef, piksel OpenCV renk eşiklemesiyle; ground truth doğrultu Gazebo'dan okunan İHA ve hedef pozlarından; kamera montajı `x500_mono_cam` değerleri (öne bakan, pitch 0, (0.12, 0.03, 0.242) m, FLU → FRD); hata = hesaplanan ve gerçek doğrultu arasındaki açı (derece); MAVLink ATTITUDE ölçümü madde 4 kesinleşene kadar yok; gerçek araç montajı config'te "belli değil, yer tutucu". Uygun mu?
**Answer:** "Evet"

**Follow-up 3:** "models" klasörü nerede, içinde ne var? Önerim: doğrulama script'i Vision'da `src/` dışında durur ve model yolunu komut satırı argümanı olarak alır; `src/` hiçbir şekilde `../` yoluna başvurmaz; "model dosyalarının çatıda durması geçicidir" notu yazılır.
**Answer:** "Algılama modeli ağırlıkları model-training branch'inde duruyor; m10'da kullanılmayacak." (Kastedilen algılama modeli ağırlıklarıdır, Gazebo dosyaları değil. m10'da kullanılmaz ve indirilmez; Gazebo hedef nesnesi dosya eklenmeden `gz service` ile spawn edilir.)

**Follow-up 4:** Camera Module 3 standart için Pi çözünürlüğü belli mi? Değilse çözünürlük ve intrinsics config'te yer tutucu (madde 9'da ölçülecek). Kapsam dışı listesi (3B konum / zemin kesişimi eklenerek) onaylanıyor mu?
**Answer:** "Camera Module 3 standard için Pi çözünürlüğü belli değil, onaylıyorum."

## Visual Assets

### Files Provided:
No visual assets provided. (`planning/visuals/` klasörü bash ile kontrol edildi; görsel dosya bulunamadı.)

### Visual Insights:
- Yok.

## Requirements Summary

### Functional Requirements
- Piksel koordinatını (u, v; float) body frame'de birim görüş doğrultusuna (unit line-of-sight vektörü, boyutsuz, normu 1) çeviren saf fonksiyon(lar). Zincir: piksel → (distorsiyon giderme) → normalize görüntü koordinatı → camera frame doğrultusu → camera → body rotasyonu → normalize edilmiş body frame vektörü.
- Herhangi bir (u, v) pikseli kabul edilir; tipik kullanım bbox merkezidir. Algılama modeline bağımlılık yoktur.
- Bu adımda attitude kullanılmaz (seçenek (a)). Çıktı yalnızca body frame doğrultusudur; mesafe ve 3B konum üretilmez.
- Attitude kullanım seçenekleri (a: kullanılmaz, b: roll/pitch ile yataylaştırma + zemin kesişimi, c: tam attitude ile NED konumu) spec'te karşılaştırılır; (a) seçimi gerekçesiyle belgelenir. Gerekçe (kullanıcı, Q6): Pi'de attitude kullanmak için PX4'ten MAVLink ile okumak ve kare zamanıyla eşleştirmek gerekir; bu ek gecikme ve zaman eşleşme hatası getirir. Body frame vektörü attitude'dan bağımsızdır; yataylaştırma gerekirse attitude'a doğrudan sahip olan PX4 tarafında yapılabilir. Bu bir karar değil, seçenektir; kontrol ve PX4 entegrasyonu maddelerinde değerlendirilir. Gecikme telafisi (kare–attitude zaman eşleşmesi) yalnızca belgelenir.
- Camera intrinsics (fx, fy, cx, cy, çözünürlük) ve distorsiyon katsayıları (OpenCV modeli) config'ten okunur.
  - SITL profili: Gazebo `mono_cam` HFOV (1.74 rad) ve çözünürlükten (1280x960) hesaplanır, fx = (w/2) / tan(HFOV/2) (≈ 540 px; fy, cx, cy kuralları spec'te netleşir), distorsiyon sıfır.
  - Pi profili: Raspberry Pi Camera Module 3 **standart** (Wide değil). Çözünürlük ve intrinsics "kalibre edilmemiş, yer tutucu" olarak açıkça işaretlenir; değerler madde 9'da ölçülecek. Madde 9'un katsayıları kod değişmeden eklenebilmelidir. Simülasyon ve gerçek kamera parametreleri ayrı tutulur.
- Kamera montajı (extrinsics; camera → body rotasyonu, gerekirse öteleme) config'ten okunur. Kamera gövdeye sabittir, gimbal yoktur.
  - SITL profili: `x500_mono_cam` (öne bakan, açı 0, öteleme (0.12, 0.03, 0.242) m, Gazebo FLU → PX4 FRD).
  - Gerçek araç profili: montaj "belli değil, yer tutucu" olarak açıkça işaretlenir.
  - Öteleme (lever arm) doğrultu çıktısında kullanılmaz.
- Geçersiz girdi: piksel görüntü dışında veya NaN/Inf ise `ValueError`. Geometrik olarak çözümü olmayan durumlar için açık bir "geçersiz" sonucu (`None` ya da geçerlilik bayrağı). Bu durumların ICD'deki "hedef yok" karşılığı madde 5 ve 11'e bırakılır.
- Birim testleri (pytest, CI'da 3.12 ve 3.13), bilinen geometrilerle: ör. principal point → body +x (ileri); bilinen açıdaki pikseller → beklenen açı; montaj rotasyonu ile birlikte bilinen sonuç; distorsiyonlu durumda `cv2.projectPoints` ile gidiş-dönüş; geçersiz girdi durumları.
- SITL doğrulaması (elle/script ile çalıştırılır, CI'da değil):
  - Gazebo Harmonic + PX4 SITL, `gz_x500_mono_cam`.
  - Renkli basit bir hedef nesne SITL çalışırken `gz service` ile spawn edilir; model/dünya dosyası eklenmez (kullanıcı onayladı; ayrıntısı spec'te netleşir).
  - Piksel, kamera görüntüsünde OpenCV renk eşiklemesiyle bulunan hedef merkezidir.
  - Ground truth doğrultu, Gazebo'dan okunan İHA ve hedef pozlarından hesaplanır ve body frame'e çevrilir. İHA pozu yalnızca değerlendirmede kullanılır, algoritmanın girdisi değildir.
  - Metrik: hesaplanan ve gerçek doğrultu arasındaki açısal hata (derece), ortalama / RMS / maksimum. Birkaç farklı hedef konumu ve irtifada, görüntü merkezi ve kenarları dahil ölçülür.
  - Kesin eşik konmaz (başarı kriterleri madde 1'de belirlenmedi); sonuç tablosu spec klasörüne yazılır.
  - PX4 MAVLink ATTITUDE ile ikinci ölçüm madde 4 kesinleşene kadar yapılmaz.

### Reusability Opportunities
- Vision'da yeniden kullanılacak mevcut kod yok; bu spec ilk geometri ve config kodunu ekler. Sonraki maddeler (11, 12, 20) bu fonksiyonları kullanacaktır.
- Gazebo kamera parametreleri ve montaj değerleri kilitli PX4 submodule'ündeki `mono_cam` / `x500_mono_cam` SDF dosyalarından okunarak Vision config'ine **değer olarak** kopyalanır. Kural 7 gereği `src/` bu dosyalara yol ile başvurmaz.
- OpenCV (`cv2.undistortPoints`, `cv2.projectPoints`) mevcut sabit sürümle (5.0.0.93) kullanılır; YAML okuma için mevcut PyYAML 6.0.3 kullanılır.
- `model-training` branch'indeki algılama ağırlıkları yalnızca bilgi notudur; bu spec'te kullanılmaz.

### Scope Boundaries
**In Scope:**
- Piksel → camera frame → body frame birim görüş doğrultusu dönüşümü (saf, donanımsız, test edilebilir fonksiyonlar).
- Intrinsics ve distorsiyon desteği; SITL ve Pi (yer tutucu) config profilleri.
- Extrinsics (camera → body) config'i; SITL profili `x500_mono_cam` değerleriyle, gerçek araç profili yer tutucu olarak.
- Attitude kullanım seçeneklerinin karşılaştırılması ve (a) kararının gerekçesiyle belgelenmesi.
- Geçersiz girdi davranışı.
- Bilinen geometrilerle birim testleri.
- SITL doğrulama script'i (Vision'da, `src/` dışında, CI'da çalışmaz) ve ölçülen açısal hata sonuçlarının spec klasörüne yazılması.

**Out of Scope:**
- 3B hedef konumu, mesafe tahmini ve zemin kesişimi (seçenek (b)/(c)); yalnızca karşılaştırmada belgelenir.
- Attitude'un çıktıda kullanılması; kare–attitude zaman eşleşmesi ve gecikme telafisi (yalnızca belgelenir).
- İnsan algılama modeli ve Hailo'suz algılama (madde 7, 8); model indirme veya `model-training` ağırlıklarını kullanma.
- Hedef seçimi ve "hedef yok" ICD çıkışı (madde 11).
- Camera Module 3 kalibrasyonunun kendisi (madde 9).
- MAVLink ile gönderim, haberleşme yöntemi ve ICD mesaj formatı (madde 4, 5, 12); PX4 MAVLink ATTITUDE ile ölçüm.
- Hedef vektörünün filtrelenmesi veya takibi (Kalman vb.).
- Hareketli insan hedefi simülasyonu ve simülasyon kamerası kararı (madde 6).
- Gazebo model/dünya dosyası eklemek (hedef `gz service` ile spawn edilir).
- Gerçek araç montaj değerlerinin ölçülmesi.

### Technical Considerations

#### Varsayımlar
Aşağıdakiler ortak spec'ler (madde 3: frame tanımları, madde 4: haberleşme, madde 5: ICD) yazılmadığı için bu spec'e özgü **varsayımlardır**, kesinleşmiş değildir. Ortak spec'ler yazılınca bu spec ve kod onlara göre güncellenir.
- **Camera frame:** OpenCV optik frame: x sağ, y aşağı, z ileri (optik eksen). Piksel orijini sol üst köşe, u sağa, v aşağı.
- **Body frame:** PX4 FRD: x ileri, y sağ, z aşağı. Orijin body (base_link) orijinidir. Doğrultu çıktısında kamera ile body orijini arasındaki öteleme ihmal edilir.
- **Yerel dünya frame'i (gerekirse):** NED. Bu spec'te çıktıda kullanılmaz.
- **Birimler:** uzunluk metre, açı radyan (raporlarda derece). Çıktı vektörü birimsiz ve normu 1.
- **Attitude gösterimi (ileride gerekirse):** quaternion (w, x, y, z), NED → FRD. Bu adımda çıktıda kullanılmaz.
- **Gazebo ↔ PX4 dönüşümü:** Gazebo model frame'i FLU, dünya frame'i ENU. FLU → FRD dönüşümü x ekseni etrafında 180° dönüşümdür (y → −y, z → −z). Gazebo kamera sensörü link'in +x eksenine bakar. Montaj açısı 0 iken optik frame ile FRD arasında şu ilişki vardır: optik z → body x, optik x → body y, optik y → body z.
- **SITL montajı:** `x500_mono_cam` öteleme FLU (0.12, 0.03, 0.242) m, yani FRD'de (0.12, −0.03, −0.242) m, açı 0. Gazebo `base_link` orijininin PX4 body orijiniyle aynı olduğu varsayılır.
- **Mesaj, frekans, zaman damgası ve "hedef yok" gösterimi:** bu spec'te tanımlanmaz (madde 5).

#### Diğer teknik notlar
- Python 3.12 (laptop) ve 3.13 (Pi) uyumlu kod; 3.13'e özgü söz dizimi yok. ruff (`py312` hedefi) ve pytest CI'da (`ci (3.12)`, `ci (3.13)`) geçmeli. Tip ipuçları zorunlu, herkese açık fonksiyonlarda docstring.
- Yeni paket eklenmez: rotasyonlar NumPy 2.4.6 ile, distorsiyon OpenCV 5.0.0.93 ile, config PyYAML 6.0.3 ile.
- Simülasyon ve Pi farkı yalnızca config'tedir (YAML veya komut satırı argümanı); kodda `if simulation:` dalları olmaz.
- `src/` içinde Gazebo importu yoktur. gz-transport (apt `python3-gz-transport13`, `python3-gz-msgs10`) sadece doğrulama script'inde kullanılır. Kural 7 gereği `src/` asla `../` yoluna (çatı, Autopilot) başvurmaz; doğrulama script'i de çatı veya Autopilot dosyalarına bağımlı olmaz.
- Simülatör Gazebo Harmonic (`gz_*`); Gazebo Classic kullanılmaz. PX4 `Tools/simulation/gz` kilitli olduğundan oraya dosya eklenmez.
- Hedef nesne `gz service` (ör. world `create` servisi, satır içi SDF) ile spawn edilir. Servis/topic adları, pose topic'i ve hedef rengi/şekli spec'te netleşir.
- SITL ölçümünde dikkat edilecekler (spec'te karara bağlanacak):
  - Ground truth doğrultu kamera konumundan mı body orijininden mi hesaplanacak (paralaks / lever arm etkisi).
  - Renkli blob merkezi ile hedefin pozunun (kütle merkezi) aynı nokta olmayabileceği.
  - Görüntü ile poz zaman damgalarının eşleşmesi. Ölçümlerin askıda (hover) veya durağan konumlarda yapılması önerilir.
- Modül, dosya, config ve script adlarını ve klasör yerlerini işi yapan kişi spec'te belirler; önceden belirlenmiş ad veya ön ek yoktur.
- Video, log, veri seti ve model ağırlığı repoya girmez (kural 9). SITL ölçüm sonuçları tablo/metin olarak spec klasörüne yazılır.
