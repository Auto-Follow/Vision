"""Kamera modeli: ic parametreler, govdeye montaj ve optik -> govde FRD rotasyonu.

Frame tanimlari (varsayim; ortak spec madde 3 yazilinca guncellenecek):

- Kamera (optik) frame: OpenCV optik frame; x goruntude saga, y goruntude asagi,
  z ileri (optik eksen). Piksel kurali OpenCV'ninkidir: orijin sol ust, tam sayi
  degerli koordinat piksel merkezi.
- Govde (body) frame: PX4 FRD; x ileri (burun), y saga, z asagi. Orijin base_link.

Birimler (varsayim): aci [rad], uzunluk [m], ic parametreler [piksel].

Modul yalnizca NumPy kullanir; donanim, Gazebo veya MAVLink bagimliligi yoktur.
"""

import math
from dataclasses import dataclass
from numbers import Integral, Real

import numpy as np

# OpenCV'nin kabul ettigi distorsiyon katsayisi sayilari (k1 k2 p1 p2 [k3 [k4 k5 k6
# [s1 s2 s3 s4 [tx ty]]]]); bos dizi distorsiyon yok demektir.
IZINLI_DISTORSIYON_UZUNLUKLARI: frozenset[int] = frozenset({0, 4, 5, 8, 12, 14})

# Montaj acilari 0 iken optik -> govde FRD eksen eslemesi (varsayim, ortak spec madde 3):
# optik x (goruntu sagi) -> govde +y, optik y (goruntu asagisi) -> govde +z,
# optik z (optik eksen) -> govde +x. Sutunlar optik eksenlerin govdedeki karsiligidir.
OPTIKTEN_KAMERA_FRD: np.ndarray = np.array(
    [
        [0.0, 0.0, 1.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
    ],
    dtype=np.float64,
)
OPTIKTEN_KAMERA_FRD.setflags(write=False)

# Rotasyon matrisi kontrolu icin sayisal tolerans; float64 ile birkac carpimin
# yuvarlama hatasi 1e-15 mertebesindedir, 1e-9 bunun cok uzerinde ama gercek bir
# hatayi (ornegin yanlis eksen eslemesi) kesin yakalar.
_ROTASYON_TOLERANSI: float = 1e-9


def _gercek_sayi(alan: str, deger: object) -> float:
    """Sonlu bir gercek sayiyi float'a cevirir; degilse alan adiyla ValueError verir."""
    if isinstance(deger, bool) or not isinstance(deger, Real):
        raise ValueError(f"{alan} bir sayi olmali, verilen: {deger!r}")
    sonuc = float(deger)
    if not math.isfinite(sonuc):
        raise ValueError(f"{alan} sonlu olmali, verilen: {deger!r}")
    return sonuc


def _pozitif_sayi(alan: str, deger: object) -> float:
    """Sonlu ve sifirdan buyuk bir gercek sayiyi float'a cevirir; degilse ValueError."""
    sonuc = _gercek_sayi(alan, deger)
    if sonuc <= 0.0:
        raise ValueError(f"{alan} sifirdan buyuk olmali, verilen: {deger!r}")
    return sonuc


def _pozitif_tam_sayi(alan: str, deger: object) -> int:
    """Sifirdan buyuk bir tam sayiyi int'e cevirir; degilse alan adiyla ValueError verir."""
    if isinstance(deger, bool) or not isinstance(deger, Integral):
        raise ValueError(f"{alan} tam sayi olmali, verilen: {deger!r}")
    sonuc = int(deger)
    if sonuc <= 0:
        raise ValueError(f"{alan} sifirdan buyuk olmali, verilen: {deger!r}")
    return sonuc


def _sayi_dizisi(alan: str, degerler: object) -> tuple[float, ...]:
    """Sonlu sayilardan olusan bir diziyi float demetine cevirir; degilse ValueError."""
    if isinstance(degerler, (str, bytes)):
        raise ValueError(f"{alan} sayi dizisi olmali, verilen: {degerler!r}")
    try:
        elemanlar = list(degerler)
    except TypeError:
        raise ValueError(f"{alan} sayi dizisi olmali, verilen: {degerler!r}") from None
    return tuple(_gercek_sayi(f"{alan}[{i}]", eleman) for i, eleman in enumerate(elemanlar))


@dataclass(frozen=True)
class KameraIcParametreleri:
    """Pinhole kamera ic parametreleri ve OpenCV distorsiyon katsayilari.

    Koordinatlar OpenCV piksel kuralindadir (varsayim; ortak spec madde 3): orijin sol
    ust, u saga, v asagi, tam sayi degerli koordinat piksel merkezi.

    Attributes:
        genislik: Goruntu genisligi w [piksel], > 0 tam sayi.
        yukseklik: Goruntu yuksekligi h [piksel], > 0 tam sayi.
        fx: Yatay odak uzakligi [piksel], > 0.
        fy: Dikey odak uzakligi [piksel], > 0.
        cx: Principal point yatay koordinati [piksel].
        cy: Principal point dikey koordinati [piksel].
        distorsiyon: OpenCV distorsiyon katsayilari (k1, k2, p1, p2, k3, ...) [birimsiz];
            uzunluk 0, 4, 5, 8, 12 veya 14. Bos demet distorsiyon yok demektir.

    Raises:
        ValueError: Bir alan gecersizse; mesaj hatali alanin adini ve degerini icerir.
    """

    genislik: int
    yukseklik: int
    fx: float
    fy: float
    cx: float
    cy: float
    distorsiyon: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        """Alanlari dogrular ve tiplerini (int, float, float demeti) sabitler."""
        object.__setattr__(self, "genislik", _pozitif_tam_sayi("genislik", self.genislik))
        object.__setattr__(self, "yukseklik", _pozitif_tam_sayi("yukseklik", self.yukseklik))
        object.__setattr__(self, "fx", _pozitif_sayi("fx", self.fx))
        object.__setattr__(self, "fy", _pozitif_sayi("fy", self.fy))
        object.__setattr__(self, "cx", _gercek_sayi("cx", self.cx))
        object.__setattr__(self, "cy", _gercek_sayi("cy", self.cy))
        katsayilar = _sayi_dizisi("distorsiyon", self.distorsiyon)
        if len(katsayilar) not in IZINLI_DISTORSIYON_UZUNLUKLARI:
            izinli = sorted(IZINLI_DISTORSIYON_UZUNLUKLARI)
            raise ValueError(
                f"distorsiyon katsayi sayisi {izinli} degerlerinden biri olmali, "
                f"verilen: {len(katsayilar)}"
            )
        object.__setattr__(self, "distorsiyon", katsayilar)

    def kamera_matrisi(self) -> np.ndarray:
        """OpenCV kamera matrisi K'yi dondurur.

        Returns:
            float64, sekil (3, 3): [[fx, 0, cx], [0, fy, cy], [0, 0, 1]] [piksel].
            Her cagrida yeni bir dizi doner.
        """
        return np.array(
            [
                [self.fx, 0.0, self.cx],
                [0.0, self.fy, self.cy],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )

    def distorsiyon_katsayilari(self) -> np.ndarray:
        """OpenCV'ye verilecek distorsiyon katsayilarini dondurur.

        Returns:
            float64, sekil (n,) [birimsiz]; n = 0 distorsiyon yok demektir.
            Her cagrida yeni bir dizi doner.
        """
        return np.array(self.distorsiyon, dtype=np.float64)


@dataclass(frozen=True)
class KameraMontaji:
    """Kameranin govdeye sabit montaji (gimbal yok).

    Acilar kameranin govde FRD'ye gore yonelimidir; ZYX sirasi: once yaw, sonra pitch,
    sonra roll (PX4 FRD Euler kurali). Acilarin hepsi 0 iken optik eksen govde +x'e,
    goruntu sagi +y'ye, goruntu asagisi +z'ye bakar. Isaret kurali:

    - Pozitif pitch optik ekseni yukari kaldirir; asagi egik kameranin pitch'i negatiftir
      (ornek: 35 derece asagi egim = pitch -0.610865 rad).
    - Pozitif yaw optik ekseni saga (govde +y) cevirir.
    - Pozitif roll, kamerayi optik eksen etrafinda arkadan bakildiginda saat yonunde
      dondurur: roll = +90 derecede goruntu sagi (optik x) govde +z'ye (asagi),
      goruntu asagisi (optik y) govde -y'ye (sola) denk gelir.

    Frame tanimlari varsayimdir (ortak spec madde 3 yazilinca guncellenecek).

    Attributes:
        roll: Optik eksen etrafinda donme [rad].
        pitch: Yatay eksen etrafinda donme [rad]; pozitif yukari.
        yaw: Dusey eksen etrafinda donme [rad]; pozitif saga.
        oteleme: Kamera orijininin govde FRD'deki konumu (x, y, z) [m]. Saklanir ama
            gorus dogrultusu hesabina girmez; dogrultunun orijini govde orijini kabul
            edilir. SITL dogrulamasi ve ileride 3B konum hesabi icin tutulur.

    Raises:
        ValueError: Bir alan sonlu degilse veya oteleme 3 elemanli degilse; mesaj hatali
            alanin adini icerir.
    """

    roll: float
    pitch: float
    yaw: float
    oteleme: tuple[float, float, float] = (0.0, 0.0, 0.0)

    def __post_init__(self) -> None:
        """Alanlari dogrular ve tiplerini (float, float demeti) sabitler."""
        object.__setattr__(self, "roll", _gercek_sayi("roll", self.roll))
        object.__setattr__(self, "pitch", _gercek_sayi("pitch", self.pitch))
        object.__setattr__(self, "yaw", _gercek_sayi("yaw", self.yaw))
        oteleme = _sayi_dizisi("oteleme", self.oteleme)
        if len(oteleme) != 3:
            raise ValueError(f"oteleme 3 elemanli (x, y, z) olmali, verilen: {len(oteleme)}")
        object.__setattr__(self, "oteleme", oteleme)

    def montaj_rotasyonu(self) -> np.ndarray:
        """Kamera FRD -> govde FRD rotasyonunu (yalnizca montaj acilari) dondurur.

        "Kamera FRD", optik frame'in sabit eksen eslemesiyle FRD'ye cevrilmis halidir
        (x optik eksen, y goruntu sagi, z goruntu asagisi). Matris
        R = Rz(yaw) @ Ry(pitch) @ Rx(roll) seklindedir (ZYX, PX4 FRD Euler kurali).

        Returns:
            float64, sekil (3, 3); v_govde = R @ v_kamera_frd.
        """
        return _zyx_rotasyonu(self.roll, self.pitch, self.yaw)

    def optikten_govdeye(self) -> np.ndarray:
        """OpenCV optik frame -> govde FRD toplam rotasyonunu dondurur.

        Toplam rotasyon = montaj rotasyonu (ZYX) @ sabit eksen eslemesi
        (optik z -> x, optik x -> y, optik y -> z). Bir dogrultu v_optik icin
        v_govde = R @ v_optik. Oteleme kullanilmaz.

        Ornek (roll isareti): roll = +pi/2, pitch = yaw = 0 iken
        R @ (1, 0, 0) = (0, 0, 1) (goruntu sagi -> asagi) ve
        R @ (0, 1, 0) = (0, -1, 0) (goruntu asagisi -> sol); optik eksen
        R @ (0, 0, 1) = (1, 0, 0) degismez.

        Frame tanimlari varsayimdir (ortak spec madde 3 yazilinca guncellenecek).

        Returns:
            float64, sekil (3, 3); ortonormal, determinanti +1. Her cagrida yeni dizi.

        Raises:
            RuntimeError: Hesaplanan matris ortonormal degilse veya det != +1 ise
                (sonlu acilarla olmamasi gerekir; ic hata gostergesi).
        """
        rotasyon = self.montaj_rotasyonu() @ OPTIKTEN_KAMERA_FRD
        _rotasyonu_dogrula(rotasyon)
        return rotasyon


def _zyx_rotasyonu(roll: float, pitch: float, yaw: float) -> np.ndarray:
    """ZYX Euler acilarindan (FRD kurali) Rz(yaw) @ Ry(pitch) @ Rx(roll) matrisini kurar.

    Ry(pitch) @ (1, 0, 0) = (cos pitch, 0, -sin pitch): FRD'de z asagi oldugu icin
    pozitif pitch ileri ekseni yukari kaldirir. Acilar [rad].
    """
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    rx = np.array([[1.0, 0.0, 0.0], [0.0, cr, -sr], [0.0, sr, cr]], dtype=np.float64)
    ry = np.array([[cp, 0.0, sp], [0.0, 1.0, 0.0], [-sp, 0.0, cp]], dtype=np.float64)
    rz = np.array([[cy, -sy, 0.0], [sy, cy, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    return rz @ ry @ rx


def _rotasyonu_dogrula(rotasyon: np.ndarray) -> None:
    """Matrisin ortonormal ve determinantinin +1 oldugunu kontrol eder; degilse RuntimeError."""
    if not np.all(np.isfinite(rotasyon)):
        raise RuntimeError("rotasyon matrisi sonlu olmayan deger iceriyor")
    if not np.allclose(rotasyon.T @ rotasyon, np.eye(3), atol=_ROTASYON_TOLERANSI, rtol=0.0):
        raise RuntimeError("rotasyon matrisi ortonormal degil")
    determinant = float(np.linalg.det(rotasyon))
    if abs(determinant - 1.0) > _ROTASYON_TOLERANSI:
        raise RuntimeError(f"rotasyon matrisinin determinanti +1 degil: {determinant}")
