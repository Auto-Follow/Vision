"""Kamera modeli: ic parametreler, govdeye montaj ve optik -> govde FRD rotasyonu.

Frame tanimlari (varsayim; ortak spec madde 3 yazilinca guncellenecek):

- Kamera (optik) frame: OpenCV optik frame; x goruntude saga, y goruntude asagi,
  z ileri (optik eksen). Piksel kurali OpenCV'ninkidir: orijin sol ust, tam sayi
  degerli koordinat piksel merkezi.
- Govde (body) frame: PX4 FRD; x ileri (burun), y saga, z asagi. Orijin base_link.

Birimler (varsayim): aci [rad], uzunluk [m], ic parametreler [piksel].

Kamera modeli bir YAML profilinden ``kamera_modeli_yukle`` ile yuklenir; SITL ile Pi
arasindaki fark yalnizca secilen profil dosyasidir. Profil semasi ``kamera_modeli_yukle``
docstring'indedir.

Modul yalnizca NumPy ve PyYAML kullanir; donanim, Gazebo veya MAVLink bagimliligi yoktur.
"""

import logging
import math
import os
from dataclasses import dataclass
from numbers import Integral, Real
from pathlib import Path

import numpy as np
import yaml

_logger = logging.getLogger(__name__)

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


@dataclass(frozen=True)
class KameraModeli:
    """Donusum fonksiyonlarina verilecek kamera modeli: ic parametreler ve montaj.

    Her bolumun kendi ``yer_tutucu`` bayragi vardir: True ise degerler olculmus veya
    kalibre edilmis degildir (ornek: Pi profili, madde 9 kalibrasyonundan ve gercek
    montajdan once). Bayraklar hesaplamayi degistirmez; yalnizca bilgi icindir.

    Attributes:
        ic: Kamera ic parametreleri [piksel].
        montaj: Kameranin govde FRD'ye montaji [rad, m].
        ic_yer_tutucu: ``ic`` degerleri yer tutucu ise True.
        montaj_yer_tutucu: ``montaj`` degerleri yer tutucu ise True.

    Raises:
        ValueError: Bir alan beklenen tipte degilse; mesaj hatali alanin adini icerir.
    """

    ic: KameraIcParametreleri
    montaj: KameraMontaji
    ic_yer_tutucu: bool = False
    montaj_yer_tutucu: bool = False

    def __post_init__(self) -> None:
        """Alan tiplerini dogrular (ic ve montaj kendi dogrulamasini olusturulurken yapar)."""
        if not isinstance(self.ic, KameraIcParametreleri):
            raise ValueError(f"ic KameraIcParametreleri olmali, verilen: {self.ic!r}")
        if not isinstance(self.montaj, KameraMontaji):
            raise ValueError(f"montaj KameraMontaji olmali, verilen: {self.montaj!r}")
        if not isinstance(self.ic_yer_tutucu, bool):
            raise ValueError(f"ic_yer_tutucu bool olmali, verilen: {self.ic_yer_tutucu!r}")
        if not isinstance(self.montaj_yer_tutucu, bool):
            raise ValueError(f"montaj_yer_tutucu bool olmali, verilen: {self.montaj_yer_tutucu!r}")

    @property
    def yer_tutucu(self) -> bool:
        """Bolumlerden en az biri yer tutucu ise True."""
        return self.ic_yer_tutucu or self.montaj_yer_tutucu


# Profil semasi: her bolumde zorunlu anahtarlar (veri sinifi alanlari + yer_tutucu) ve
# secimlik "not" (yer tutucu uyarisinda gosterilen kisa aciklama). Bunlarin disindaki
# anahtarlar reddedilir: yazim hatasi olan bir anahtar (ornek "distortion") sessizce
# yok sayilsaydi varsayilan deger kullanilirdi.
_KAMERA_ANAHTARLARI: tuple[str, ...] = (
    "genislik",
    "yukseklik",
    "fx",
    "fy",
    "cx",
    "cy",
    "distorsiyon",
)
_MONTAJ_ANAHTARLARI: tuple[str, ...] = ("roll", "pitch", "yaw", "oteleme")
_BAYRAK_ANAHTARI: str = "yer_tutucu"
_NOT_ANAHTARI: str = "not"
_KOK_ANAHTARLARI: tuple[str, ...] = ("kamera", "montaj")


def kamera_modeli_yukle(yol: str | os.PathLike[str]) -> KameraModeli:
    """Bir YAML kamera profilini okur, dogrular ve ``KameraModeli`` dondurur.

    Profil semasi (birimler; frame tanimlari varsayimdir, ortak spec madde 3)::

        kamera:
          genislik: int [piksel]       yukseklik: int [piksel]
          fx, fy: float [piksel] (> 0) cx, cy: float [piksel]
          distorsiyon: [float, ...]    OpenCV katsayilari; [] = distorsiyon yok
          yer_tutucu: bool             not: str (secimlik)
        montaj:
          roll, pitch, yaw: float [rad] (govde FRD'ye gore, ZYX)
          oteleme: [x, y, z] [m] (govde FRD)
          yer_tutucu: bool             not: str (secimlik)

    Tum anahtarlar (``not`` haric) zorunludur; ``distorsiyon`` da acikca yazilir.
    Bilinmeyen anahtarlar reddedilir. Deger dogrulamasi ``KameraIcParametreleri`` ve
    ``KameraMontaji`` tarafindan yapilir. Bolumlerden biri yer tutucu ise her yuklemede
    modul logger'i ile bir kez uyari yazilir.

    Args:
        yol: Profil dosyasinin yolu. Goreli yol cagiranin calisma klasorune goredir;
            fonksiyon kendi bildigi bir yol kullanmaz.

    Returns:
        Ic parametreler, montaj ve iki ``yer_tutucu`` bayragini tasiyan kamera modeli.

    Raises:
        ValueError: Dosya gecerli YAML degilse, bir anahtar eksik/bilinmeyen ya da bir
            deger yanlis tipte/gecersizse. Mesaj dosya yolunu ve hatali alani
            (ornek ``kamera.fx``) icerir.
        OSError: Dosya okunamazsa (ornek: dosya yok).
    """
    dosya_yolu = Path(yol)
    try:
        with dosya_yolu.open(encoding="utf-8") as dosya:
            veri = yaml.safe_load(dosya)
    except yaml.YAMLError as hata:
        raise ValueError(f"{dosya_yolu}: gecerli YAML degil: {hata}") from hata

    kok = _bolum_al(dosya_yolu, "profil", veri, _KOK_ANAHTARLARI, ())
    kamera = _bolum_al(
        dosya_yolu,
        "kamera",
        kok["kamera"],
        (*_KAMERA_ANAHTARLARI, _BAYRAK_ANAHTARI),
        (_NOT_ANAHTARI,),
    )
    montaj = _bolum_al(
        dosya_yolu,
        "montaj",
        kok["montaj"],
        (*_MONTAJ_ANAHTARLARI, _BAYRAK_ANAHTARI),
        (_NOT_ANAHTARI,),
    )

    try:
        ic = KameraIcParametreleri(**{anahtar: kamera[anahtar] for anahtar in _KAMERA_ANAHTARLARI})
    except ValueError as hata:
        # Veri sinifi mesajlari alan adiyla baslar; bolum adi on ek olarak eklenir.
        raise ValueError(f"{dosya_yolu}: kamera.{hata}") from hata
    try:
        montaj_nesnesi = KameraMontaji(
            **{anahtar: montaj[anahtar] for anahtar in _MONTAJ_ANAHTARLARI}
        )
    except ValueError as hata:
        raise ValueError(f"{dosya_yolu}: montaj.{hata}") from hata

    model = KameraModeli(
        ic=ic,
        montaj=montaj_nesnesi,
        ic_yer_tutucu=_bayrak_al(dosya_yolu, "kamera", kamera),
        montaj_yer_tutucu=_bayrak_al(dosya_yolu, "montaj", montaj),
    )
    kamera_notu = _not_al(dosya_yolu, "kamera", kamera)
    montaj_notu = _not_al(dosya_yolu, "montaj", montaj)

    yer_tutucular = []
    if model.ic_yer_tutucu:
        yer_tutucular.append(f"kamera ({kamera_notu})" if kamera_notu else "kamera")
    if model.montaj_yer_tutucu:
        yer_tutucular.append(f"montaj ({montaj_notu})" if montaj_notu else "montaj")
    if yer_tutucular:
        _logger.warning(
            "%s: yer tutucu kamera profili yuklendi, degerler olculmus degil: %s",
            dosya_yolu,
            "; ".join(yer_tutucular),
        )
    return model


def _bolum_al(
    dosya_yolu: Path,
    ad: str,
    veri: object,
    zorunlu: tuple[str, ...],
    secimlik: tuple[str, ...],
) -> dict[str, object]:
    """Bir YAML eslemini dogrular: eksik veya bilinmeyen anahtar varsa ValueError verir."""
    if not isinstance(veri, dict):
        raise ValueError(
            f"{dosya_yolu}: {ad} anahtar: deger eslemi olmali, verilen: {type(veri).__name__}"
        )
    on_ek = "" if ad == "profil" else f"{ad}."
    for anahtar in zorunlu:
        if anahtar not in veri:
            raise ValueError(f"{dosya_yolu}: {on_ek}{anahtar} eksik")
    izinli = (*zorunlu, *secimlik)
    for anahtar in veri:
        if anahtar not in izinli:
            raise ValueError(
                f"{dosya_yolu}: {on_ek}{anahtar} bilinmeyen anahtar; izinli: {list(izinli)}"
            )
    return veri


def _bayrak_al(dosya_yolu: Path, ad: str, bolum: dict[str, object]) -> bool:
    """Bolumun yer_tutucu bayragini dondurur; true/false degilse ValueError verir."""
    deger = bolum[_BAYRAK_ANAHTARI]
    if not isinstance(deger, bool):
        raise ValueError(
            f"{dosya_yolu}: {ad}.{_BAYRAK_ANAHTARI} true veya false olmali, verilen: {deger!r}"
        )
    return deger


def _not_al(dosya_yolu: Path, ad: str, bolum: dict[str, object]) -> str:
    """Bolumun secimlik notunu dondurur (yoksa bos metin); metin degilse ValueError verir."""
    deger = bolum.get(_NOT_ANAHTARI, "")
    if not isinstance(deger, str):
        raise ValueError(f"{dosya_yolu}: {ad}.{_NOT_ANAHTARI} metin olmali, verilen: {deger!r}")
    return deger.strip()
