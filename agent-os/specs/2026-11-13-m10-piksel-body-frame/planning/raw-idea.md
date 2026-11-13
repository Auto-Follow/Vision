# Ham Fikir

Yol haritası madde 10 — Piksel koordinatından body frame hedef vektörüne dönüşüm. Pixel coordinates → görüş doğrultusu → camera frame → body frame dönüşümü uygulanır; attitude bilgisinin kullanımı değerlendirilir ve gerekçesiyle belgelenir (Vision). Doğrulama: bilinen geometrilerle birim testleri geçer ve SITL'de hesaplanan vektör Gazebo'daki gerçek (ground truth) hedef konumuyla karşılaştırılıp hata ölçülür. Boyut: L.

Not: Ortak spec'ler (madde 3 frame tanımları, 4 haberleşme, 5 ICD) henüz yazılmadı; frame, eksen, birim, mesaj konuları bu spec'te 'Varsayımlar' başlığı altında açıkça yazılacak.
