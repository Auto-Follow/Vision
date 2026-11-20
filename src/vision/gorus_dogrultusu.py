"""Piksel (u, v) -> govde FRD birim gorus dogrultusu (line-of-sight).

Zincir: piksel (u, v) -> distorsiyon giderme (``cv2.undistortPoints``) -> normalize
goruntu koordinati (x_n, y_n) -> optik frame dogrultusu (x_n, y_n, 1) -> optik -> govde
FRD rotasyonu (``KameraMontaji.optikten_govdeye``) -> birim vektor.

Frame tanimlari (varsayim; ortak spec madde 3/5 yazilinca guncellenecek):

- Piksel: OpenCV kurali; orijin sol ust, u saga, v asagi, tam sayi degerli koordinat
  piksel merkezi. Gecerli aralik -0.5 <= u <= w - 0.5, -0.5 <= v <= h - 0.5.
- Kamera (optik) frame: OpenCV optik frame; x saga, y asagi, z ileri (optik eksen).
- Govde (body) frame: PX4 FRD; x ileri (burun), y saga, z asagi. Dogrultunun orijini
  govde orijini kabul edilir; kamera ile govde orijini arasindaki oteleme ihmal edilir.

Birimler: piksel [piksel]; cikti vektoru birimsizdir, normu 1'dir.

Attitude kullanimi (secenek a): cikti, aracin attitude'undan bagimsiz, saf govde FRD
dogrultusudur; yataylastirma veya yerel NED'e cevirme yapilmaz. Gerekce: Pi'de attitude
kullanmak icin PX4'ten MAVLink ile okuma ve kare zamaniyla eslestirme gerekir; bu ek
gecikme ve zaman eslesme hatasi getirir. Yataylastirma gerekirse attitude'a dogrudan sahip
olan PX4 tarafinda yapilabilir. Bu kesin bir mimari karar degildir; kontrol (madde 13) ve
PX4 entegrasyonu maddelerinde yeniden degerlendirilir.

``None`` (cozum yok) veya ``ValueError`` (gecersiz girdi) sonucunun ICD'deki "hedef yok"
karsiligi burada tanimlanmaz (madde 5, 11).

Fonksiyonlar saf ve durumsuzdur; yalnizca NumPy ve OpenCV kullanilir. Dosya okuma,
loglama, donanim, Gazebo veya MAVLink bagimliligi yoktur.
"""

import math
from collections.abc import Sequence
from numbers import Real

import cv2
import numpy as np

from vision.kamera_modeli import KameraModeli

# cv2.undistortPoints yakinsama kriteri: (tip, en fazla yineleme, epsilon [piksel]).
# OpenCV'nin varsayilani yalnizca 5 yinelemedir (COUNT, 5); guclu distorsiyonda kenar
# piksellerde bu yetmez. EPS, OpenCV'de o anki tahminin yeniden distorsiyonlu pikselinin
# girdiye uzakligidir [piksel]. 1e-6 piksel, fx ~ 1774 piksel icin ~6e-10 rad demektir;
# piksel nicemlemesinin (0.5 piksel) ve gidis-donus testinin (1e-4 rad) cok altindadir.
# 100 yineleme, tek nokta icin mikrosaniyeler mertebesinde bir ust sinirdir; yakinsayan
# makul katsayilar bu siniri bulmadan EPS'e ulasir.
DISTORSIYON_GIDERME_KRITERI: tuple[int, int, float] = (
    cv2.TERM_CRITERIA_COUNT | cv2.TERM_CRITERIA_EPS,
    100,
    1e-6,
)

# Geri yansitma toleransi [piksel]. Girdi pikselinin kendisi +-0.5 piksel nicemlenmistir;
# yakinsamis bir cozum DISTORSIYON_GIDERME_KRITERI'nin epsilon'u (1e-6 piksel) mertebesinde
# geri yansir. Yarim pikselden uzak bir geri yansitma, distorsiyon gidermenin gercek bir
# cozum bulmadigini gosterir (ornek: OpenCV'nin yakinsamayip distorsiyonlu koordinati
# dondurdugu durum). Yarim piksellik bir artik hata fx ~ 1774 piksel icin ~3e-4 rad
# (~0.016 derece) dogrultu hatasi demektir.
GERI_YANSITMA_TOLERANSI_PIKSEL: float = 0.5


def pikselden_govde_dogrultusu(
    model: KameraModeli,
    u: float,
    v: float,
    geri_yansitma_toleransi: float = GERI_YANSITMA_TOLERANSI_PIKSEL,
) -> np.ndarray | None:
    """Bir pikseli govde FRD'de birim gorus dogrultusuna cevirir.

    Distorsiyon ``cv2.undistortPoints`` ile ``DISTORSIYON_GIDERME_KRITERI`` (COUNT | EPS,
    100 yineleme, 1e-6 piksel) kullanilarak giderilir; distorsiyon yoksa (bos katsayi
    dizisi) ayni kod yolu calisir. Sonuc ``cv2.projectPoints`` ile ayni ic parametre ve
    katsayilarla geri yansitilir; geri yansitilmis piksel girdiden
    ``geri_yansitma_toleransi``'ndan fazla uzaksa geometrik cozum yok sayilir. Oteleme
    kullanilmaz; mesafe veya 3B konum uretilmez. Attitude kullanilmaz (secenek a).

    Frame tanimlari varsayimdir (ortak spec madde 3 yazilinca guncellenecek); modul
    docstring'ine bakiniz.

    Args:
        model: Ic parametreler ve montaj; ``kamera_modeli_yukle`` ile yuklenir.
        u: Yatay piksel koordinati [piksel], OpenCV kurali, -0.5 <= u <= w - 0.5.
        v: Dikey piksel koordinati [piksel], OpenCV kurali, -0.5 <= v <= h - 0.5.
        geri_yansitma_toleransi: Geri yansitma hatasinin ust siniri [piksel], > 0.
            Varsayilan 0.5 piksel: girdi pikselinin nicemleme yarim genisligi; gerekcesi
            ``GERI_YANSITMA_TOLERANSI_PIKSEL`` yorumundadir.

    Returns:
        Govde FRD birim dogrultu, float64, sekil (3,), normu 1 [birimsiz]; geometrik
        cozum yoksa (distorsiyon giderme sonlu degil veya geri yansitma toleransi
        asildi) ``None``.

    Raises:
        ValueError: u veya v sayi degil, NaN/Inf ya da gecerli araligin disindaysa
            (mesaj degeri ve sinirlari icerir); tolerans sonlu ve > 0 degilse.
    """
    ic = model.ic
    u = _piksel_koordinati("u", u, ic.genislik)
    v = _piksel_koordinati("v", v, ic.yukseklik)
    if not _sonlu_mu(geri_yansitma_toleransi) or geri_yansitma_toleransi <= 0.0:
        raise ValueError(
            f"geri_yansitma_toleransi sonlu ve sifirdan buyuk olmali, "
            f"verilen: {geri_yansitma_toleransi!r}"
        )

    kamera_matrisi = ic.kamera_matrisi()
    katsayilar = ic.distorsiyon_katsayilari()
    piksel = np.array([[[u, v]]], dtype=np.float64)

    normalize = cv2.undistortPoints(
        piksel, kamera_matrisi, katsayilar, criteria=DISTORSIYON_GIDERME_KRITERI
    ).reshape(2)
    if not np.all(np.isfinite(normalize)):
        return None

    optik = np.array([normalize[0], normalize[1], 1.0], dtype=np.float64)
    geri_yansitilan, _ = cv2.projectPoints(
        optik.reshape(1, 3),
        np.zeros(3, dtype=np.float64),
        np.zeros(3, dtype=np.float64),
        kamera_matrisi,
        katsayilar,
    )
    hata = float(np.linalg.norm(geri_yansitilan.reshape(2) - piksel.reshape(2)))
    if not math.isfinite(hata) or hata > geri_yansitma_toleransi:
        return None

    govde = model.montaj.optikten_govdeye() @ optik
    return govde / np.linalg.norm(govde)


def bbox_merkezi(kutu: Sequence[float]) -> tuple[float, float]:
    """Bir sinirlayici kutunun (bbox) merkez pikselini dondurur.

    bbox formati varsayimdir (algilama ciktisi ve ICD madde 5, 7 yazilinca
    guncellenecek): (x_min, y_min, x_max, y_max) [piksel], OpenCV piksel kurali. Merkez
    koselerin aritmetik ortalamasidir; ayak noktasi veya baska ozel nokta secilmez.

    Args:
        kutu: (x_min, y_min, x_max, y_max) [piksel]; x_min <= x_max, y_min <= y_max.

    Returns:
        (u, v) [piksel]; ``pikselden_govde_dogrultusu``'na verilebilir.

    Raises:
        ValueError: Kutu 4 sonlu sayidan olusmuyorsa veya min > max ise.
    """
    if isinstance(kutu, (str, bytes)) or len(kutu) != 4:
        raise ValueError(f"kutu (x_min, y_min, x_max, y_max) olmali, verilen: {kutu!r}")
    adlar = ("x_min", "y_min", "x_max", "y_max")
    x_min, y_min, x_max, y_max = (
        _sonlu_sayi(ad, deger) for ad, deger in zip(adlar, kutu, strict=True)
    )
    if x_min > x_max or y_min > y_max:
        raise ValueError(f"kutu min degerleri max'tan buyuk olamaz, verilen: {kutu!r}")
    return (x_min + x_max) / 2.0, (y_min + y_max) / 2.0


def _sonlu_mu(deger: object) -> bool:
    """Deger sonlu bir gercek sayiysa (bool haric) True."""
    return not isinstance(deger, bool) and isinstance(deger, Real) and math.isfinite(deger)


def _sonlu_sayi(ad: str, deger: object) -> float:
    """Sonlu bir gercek sayiyi float'a cevirir; degilse adiyla ValueError verir."""
    if not _sonlu_mu(deger):
        raise ValueError(f"{ad} sonlu bir sayi olmali, verilen: {deger!r}")
    return float(deger)


def _piksel_koordinati(ad: str, deger: object, boyut: int) -> float:
    """Piksel koordinatini dogrular: sonlu ve [-0.5, boyut - 0.5] icinde; degilse ValueError.

    NaN karsilastirmada her zaman yanlis oldugu icin sonluluk ayrica kontrol edilir.
    """
    alt, ust = -0.5, boyut - 0.5
    if not _sonlu_mu(deger) or not alt <= float(deger) <= ust:
        raise ValueError(
            f"{ad} = {deger!r} gecersiz; sonlu olmali ve gecerli aralik [{alt}, {ust}] "
            f"icinde olmali [piksel]"
        )
    return float(deger)
