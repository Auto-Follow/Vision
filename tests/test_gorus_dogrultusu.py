"""Piksel -> govde FRD birim gorus dogrultusu: bilinen geometriler, distorsiyon, gecersiz girdi."""

import copy
import math
from pathlib import Path

import cv2
import numpy as np
import pytest

from vision.gorus_dogrultusu import (
    DISTORSIYON_GIDERME_KRITERI,
    bbox_merkezi,
    pikselden_govde_dogrultusu,
)
from vision.kamera_modeli import (
    KameraIcParametreleri,
    KameraModeli,
    KameraMontaji,
    kamera_modeli_yukle,
)

SITL_PROFILI = Path(__file__).resolve().parents[1] / "config" / "kamera" / "sitl.yaml"

# SITL ic parametreleri (config/kamera/sitl.yaml ile ayni degerler, burada deger olarak).
GENISLIK = 2304
YUKSEKLIK = 1296
FX = 1773.925033
CX = 1152.0
CY = 648.0
YATAY_FOV_RAD = 1.151917

# Gidis-donus testinde yakinsadigi dogrulanmis, sifir olmayan 5 katsayili distorsiyon.
ILIMLI_DISTORSIYON = (-0.12, 0.08, 0.0008, -0.0006, -0.02)


def model_olustur(
    roll: float = 0.0,
    pitch: float = 0.0,
    yaw: float = 0.0,
    distorsiyon: tuple[float, ...] = (),
) -> KameraModeli:
    ic = KameraIcParametreleri(
        genislik=GENISLIK,
        yukseklik=YUKSEKLIK,
        fx=FX,
        fy=FX,
        cx=CX,
        cy=CY,
        distorsiyon=distorsiyon,
    )
    return KameraModeli(ic=ic, montaj=KameraMontaji(roll=roll, pitch=pitch, yaw=yaw))


def aci_farki(a: np.ndarray, b: np.ndarray) -> float:
    """Iki birim vektor arasindaki aci [rad]; kucuk acilarda da hassas (atan2)."""
    return math.atan2(np.linalg.norm(np.cross(a, b)), float(np.dot(a, b)))


@pytest.mark.parametrize(
    ("model", "beklenen"),
    [
        (model_olustur(), [1.0, 0.0, 0.0]),
        (model_olustur(pitch=-math.pi / 2), [0.0, 0.0, 1.0]),
        (model_olustur(yaw=math.pi / 2), [0.0, 1.0, 0.0]),
        (
            kamera_modeli_yukle(SITL_PROFILI),
            [math.cos(math.radians(35.0)), 0.0, math.sin(math.radians(35.0))],
        ),
    ],
    ids=["montajsiz", "pitch_eksi_90", "yaw_arti_90", "sitl_profili_pitch_eksi_35"],
)
def test_principal_point_montaja_gore_bilinen_dogrultuyu_verir(model, beklenen):
    dogrultu = pikselden_govde_dogrultusu(model, model.ic.cx, model.ic.cy)

    assert isinstance(dogrultu, np.ndarray)
    assert dogrultu.dtype == np.float64
    assert dogrultu.shape == (3,)
    assert np.linalg.norm(dogrultu) == pytest.approx(1.0, abs=1e-12)
    np.testing.assert_allclose(dogrultu, beklenen, atol=1e-6)


@pytest.mark.parametrize("aci_derece", [-30.0, -10.0, 5.0, 20.0, 32.0])
def test_bilinen_aci_pikseli_o_aci_kadar_saga_ve_asagi_doner(aci_derece):
    model = model_olustur()
    aci = math.radians(aci_derece)
    # Dikey aci gorus alaninda kalsin diye yatay acinin yarisi kullanilir.
    dikey_aci = aci / 2.0

    yatay = pikselden_govde_dogrultusu(model, CX + FX * math.tan(aci), CY)
    dikey = pikselden_govde_dogrultusu(model, CX, CY + FX * math.tan(dikey_aci))

    assert math.atan2(yatay[1], yatay[0]) == pytest.approx(aci, abs=1e-9)
    assert yatay[2] == pytest.approx(0.0, abs=1e-12)
    assert math.copysign(1.0, yatay[1]) == math.copysign(1.0, aci)  # saga = +y
    assert math.atan2(dikey[2], dikey[0]) == pytest.approx(dikey_aci, abs=1e-9)
    assert math.copysign(1.0, dikey[2]) == math.copysign(1.0, dikey_aci)  # v > cy -> z > 0


def test_yatay_kenar_pikseli_yarim_yatay_gorus_alanini_verir():
    dogrultu = pikselden_govde_dogrultusu(model_olustur(), GENISLIK - 0.5, CY)

    # Kenar pikselinin merkezi gorus alani sinirindan yarim piksel (0.5 / fx * cos^2,
    # ~2e-4 rad) iceridedir; tolerans 5e-4 rad (~0.03 derece) bunu kapsar.
    yatay_aci = math.atan2(dogrultu[1], dogrultu[0])
    assert yatay_aci == pytest.approx(YATAY_FOV_RAD / 2.0, abs=5e-4)
    assert math.degrees(yatay_aci) == pytest.approx(33.0, abs=0.03)


@pytest.mark.parametrize(
    "distorsiyon",
    [
        (-0.12, 0.08, 0.0008, -0.0006, -0.02),
        (0.3, -0.1, 0.001, 0.002, 0.01, 0.35, -0.08, 0.02),
    ],
    ids=["5_katsayi", "8_katsayi_rasyonel"],
)
def test_distorsiyon_gidis_donus_acisal_farki_cok_kucuk(distorsiyon):
    model = model_olustur(pitch=-0.610865, distorsiyon=distorsiyon)
    optikten_govdeye = model.montaj.optikten_govdeye()
    # Bilinen govde dogrultulari: burnun 20..50 derece asagisi, -25..25 derece yatayda.
    for asagi_derece in (20.0, 35.0, 50.0):
        for yatay_derece in (-25.0, 0.0, 25.0):
            asagi, yatay = math.radians(asagi_derece), math.radians(yatay_derece)
            govde = np.array(
                [
                    math.cos(asagi) * math.cos(yatay),
                    math.cos(asagi) * math.sin(yatay),
                    math.sin(asagi),
                ]
            )
            optik = optikten_govdeye.T @ govde
            piksel, _ = cv2.projectPoints(
                optik.reshape(1, 3),
                np.zeros(3),
                np.zeros(3),
                model.ic.kamera_matrisi(),
                model.ic.distorsiyon_katsayilari(),
            )
            u, v = piksel.reshape(2)
            assert -0.5 <= u <= GENISLIK - 0.5 and -0.5 <= v <= YUKSEKLIK - 0.5

            sonuc = pikselden_govde_dogrultusu(model, u, v)

            assert sonuc is not None
            assert aci_farki(sonuc, govde) < 1e-4


@pytest.mark.parametrize(
    ("u", "v", "alan"),
    [
        (math.nan, CY, "u"),
        (CX, math.inf, "v"),
        (-math.inf, CY, "u"),
        (-0.51, CY, "u"),
        (GENISLIK - 0.49, CY, "u"),
        (CX, -1.0, "v"),
        (CX, YUKSEKLIK, "v"),
    ],
)
def test_gecersiz_piksel_deger_ve_sinirla_deger_hatasi_verir(u, v, alan):
    with pytest.raises(ValueError, match=rf"^{alan} = .*\[-0\.5, \d+\.5\]"):
        pikselden_govde_dogrultusu(model_olustur(), u, v)


def test_yakinsamayan_asiri_distorsiyonda_none_doner():
    # k1 = -1 ile ileri model r_d = r (1 - r^2) en fazla 2 / (3 sqrt 3) ~ 0.385'e ulasir;
    # kose pikselinin normalize yaricapi ~0.745 oldugu icin hicbir distorsiyonsuz nokta bu
    # piksele yansimaz (geometrik cozum yok). OpenCV 5.0 bu durumda yakinsamadan sonlu bir
    # deger dondurur; geri yansitma kontrolu onu yakalar (hata ~730 piksel >> 0.5).
    model = model_olustur(distorsiyon=(-1.0, 0.0, 0.0, 0.0))

    assert pikselden_govde_dogrultusu(model, GENISLIK - 0.5, YUKSEKLIK - 0.5) is None
    # Ayni model principal point'te cozulur: None yalnizca cozumsuz piksellerde gelir.
    np.testing.assert_allclose(pikselden_govde_dogrultusu(model, CX, CY), [1.0, 0.0, 0.0])


def test_opencv_undistort_ve_project_points_api_si_dogrulandigi_gibi():
    # OpenCV 5.0.0 (opencv-python 5.0.0.93) uzerinde dogrulandi; surum degisirse bu test
    # API'nin yeniden incelenmesi gerektigini gosterir.
    assert cv2.__version__.startswith("5.0.")
    kamera_matrisi = model_olustur().ic.kamera_matrisi()
    piksel = np.array([[[CX + FX * 0.25, CY - FX * 0.125]]], dtype=np.float64)

    # Ust duzey cv2.undistortPoints; bos (0,) katsayi dizisi distorsiyon yok demektir;
    # criteria anahtar kelimeyle (tip, en fazla yineleme, epsilon) demeti olarak verilir.
    # P verilmeyince cikti normalize koordinattir, sekil (1, 1, 2), float64.
    normalize = cv2.undistortPoints(
        piksel, kamera_matrisi, np.zeros(0), criteria=DISTORSIYON_GIDERME_KRITERI
    )
    assert normalize.shape == (1, 1, 2)
    assert normalize.dtype == np.float64
    np.testing.assert_allclose(normalize.reshape(2), [0.25, -0.125], atol=1e-12)

    # cv2.projectPoints(objectPoints, rvec, tvec, cameraMatrix, distCoeffs) ->
    # (imagePoints (N, 1, 2), jacobian); rvec = tvec = 0 optik frame'de yansitir.
    geri, jakobiyen = cv2.projectPoints(
        np.array([[0.25, -0.125, 1.0]]), np.zeros(3), np.zeros(3), kamera_matrisi, np.zeros(0)
    )
    assert geri.shape == (1, 1, 2)
    assert jakobiyen.shape[0] == 2
    np.testing.assert_allclose(geri, piksel, atol=1e-9)


ROLL_TEST_ACISI = math.radians(20.0)
C20 = math.cos(ROLL_TEST_ACISI)
S20 = math.sin(ROLL_TEST_ACISI)


@pytest.mark.parametrize(
    ("roll", "saga_beklenen", "asagi_beklenen"),
    [
        # roll = +90: goruntu sagi -> govde asagisi (+z), goruntu asagisi -> sol (-y).
        (math.pi / 2, [C20, 0.0, S20], [C20, -S20, 0.0]),
        (-math.pi / 2, [C20, 0.0, -S20], [C20, S20, 0.0]),
        (math.pi, [C20, -S20, 0.0], [C20, 0.0, -S20]),
    ],
    ids=["roll_arti_90", "roll_eksi_90", "roll_180"],
)
def test_roll_goruntu_eksenlerini_bilinen_govde_yonune_cevirir(roll, saga_beklenen, asagi_beklenen):
    # Principal point'in 20 derece sagindaki ve 20 derece asagisindaki pikseller.
    model = model_olustur(roll=roll)
    kayma = FX * math.tan(ROLL_TEST_ACISI)

    saga = pikselden_govde_dogrultusu(model, CX + kayma, CY)
    asagi = pikselden_govde_dogrultusu(model, CX, CY + kayma)

    np.testing.assert_allclose(saga, saga_beklenen, atol=1e-9)
    np.testing.assert_allclose(asagi, asagi_beklenen, atol=1e-9)
    # Optik eksen roll'den etkilenmez.
    np.testing.assert_allclose(pikselden_govde_dogrultusu(model, CX, CY), [1, 0, 0], atol=1e-12)


@pytest.mark.parametrize(
    ("eksen", "sinir", "disari_yon"),
    [
        ("u", -0.5, -math.inf),
        ("u", GENISLIK - 0.5, math.inf),
        ("v", -0.5, -math.inf),
        ("v", YUKSEKLIK - 0.5, math.inf),
    ],
    ids=["u_alt", "u_ust", "v_alt", "v_ust"],
)
def test_gecerli_aralik_sinirlari_kabul_edilir_hemen_disi_reddedilir(eksen, sinir, disari_yon):
    model = model_olustur()
    hemen_disi = float(np.nextafter(sinir, disari_yon))

    def cagir(deger: float) -> np.ndarray | None:
        if eksen == "u":
            return pikselden_govde_dogrultusu(model, deger, CY)
        return pikselden_govde_dogrultusu(model, CX, deger)

    dogrultu = cagir(sinir)
    assert dogrultu is not None
    assert np.linalg.norm(dogrultu) == pytest.approx(1.0, abs=1e-12)
    with pytest.raises(ValueError, match=rf"^{eksen} = "):
        cagir(hemen_disi)


@pytest.mark.parametrize(
    "model",
    [
        kamera_modeli_yukle(SITL_PROFILI),
        model_olustur(roll=0.3, pitch=-0.6, yaw=0.2, distorsiyon=ILIMLI_DISTORSIYON),
    ],
    ids=["sitl_profili", "distorsiyonlu_egik_montaj"],
)
def test_goruntu_izgarasinda_sonuc_her_zaman_birim_vektor(model):
    # Izgara kenarlari ve koseleri de kapsar: -0.5 ve w - 0.5 / h - 0.5 dahil.
    for u in np.linspace(-0.5, GENISLIK - 0.5, 13):
        for v in np.linspace(-0.5, YUKSEKLIK - 0.5, 9):
            dogrultu = pikselden_govde_dogrultusu(model, float(u), float(v))

            assert dogrultu is not None
            assert dogrultu.dtype == np.float64
            assert dogrultu.shape == (3,)
            assert np.all(np.isfinite(dogrultu))
            assert np.linalg.norm(dogrultu) == pytest.approx(1.0, abs=1e-12)


def test_geri_yansitma_toleransi_cozum_yok_sinirini_belirler():
    asiri = model_olustur(distorsiyon=(-1.0, 0.0, 0.0, 0.0))
    ilimli = model_olustur(distorsiyon=ILIMLI_DISTORSIYON)
    kose = (GENISLIK - 0.5, YUKSEKLIK - 0.5)

    # Cozumsuz kose pikseli (geri yansitma hatasi ~730 piksel) varsayilan 0.5 piksel
    # toleransla reddedilir; tolerans hatanin uzerine cikarilirsa kabul edilir.
    assert pikselden_govde_dogrultusu(asiri, *kose) is None
    assert pikselden_govde_dogrultusu(asiri, *kose, geri_yansitma_toleransi=1e4) is not None
    # Yakinsamis cozumun geri yansitma hatasi ~1e-7 pikseldir; cok siki tolerans da gecer.
    assert pikselden_govde_dogrultusu(ilimli, *kose, geri_yansitma_toleransi=1e-3) is not None


@pytest.mark.parametrize("tolerans", [0.0, -0.1, math.nan, math.inf, True])
def test_gecersiz_geri_yansitma_toleransi_deger_hatasi_verir(tolerans):
    with pytest.raises(ValueError, match="geri_yansitma_toleransi"):
        pikselden_govde_dogrultusu(model_olustur(), CX, CY, geri_yansitma_toleransi=tolerans)


def test_donusum_saf_girdiyi_degistirmez_ve_ayni_sonucu_verir():
    model = model_olustur(roll=0.1, pitch=-0.610865, yaw=-0.2, distorsiyon=ILIMLI_DISTORSIYON)
    onceki = copy.deepcopy(model)
    kutu = [400.0, 300.0, 600.0, 900.0]

    u, v = bbox_merkezi(kutu)
    ilk = pikselden_govde_dogrultusu(model, u, v)
    ilk_kopya = ilk.copy()
    ilk[:] = 0.0  # Donen dizi cagirana aittir; sonraki cagrilari etkilememeli.
    ikinci = pikselden_govde_dogrultusu(model, u, v)

    np.testing.assert_array_equal(ikinci, ilk_kopya)
    assert model == onceki
    np.testing.assert_array_equal(model.ic.kamera_matrisi(), onceki.ic.kamera_matrisi())
    assert kutu == [400.0, 300.0, 600.0, 900.0]


@pytest.mark.parametrize(
    ("kutu", "beklenen"),
    [
        ((0.0, 0.0, 10.0, 20.0), (5.0, 10.0)),
        ([100.5, 200.25, 300.5, 400.75], (200.5, 300.5)),
        (np.array([-0.5, -0.5, GENISLIK - 0.5, YUKSEKLIK - 0.5]), (1151.5, 647.5)),
        ((7, 9, 7, 9), (7.0, 9.0)),
    ],
    ids=["demet", "liste", "numpy_tum_goruntu", "tam_sayi_dejenere"],
)
def test_bbox_merkezi_kose_ortalamasini_verir(kutu, beklenen):
    merkez = bbox_merkezi(kutu)

    assert merkez == pytest.approx(beklenen, abs=1e-12)
    assert all(type(deger) is float for deger in merkez)


@pytest.mark.parametrize(
    "kutu",
    [
        (1.0, 2.0, 3.0),
        (1.0, 2.0, 3.0, 4.0, 5.0),
        "1234",
        (math.nan, 0.0, 10.0, 10.0),
        (0.0, 0.0, math.inf, 10.0),
        (0.0, None, 10.0, 10.0),
        (True, 0.0, 10.0, 10.0),
        (10.0, 0.0, 5.0, 10.0),
        (0.0, 10.0, 10.0, 5.0),
    ],
    ids=[
        "3_eleman",
        "5_eleman",
        "metin",
        "nan",
        "inf",
        "none",
        "bool",
        "x_min_buyuk",
        "y_min_buyuk",
    ],
)
def test_gecersiz_bbox_deger_hatasi_verir(kutu):
    with pytest.raises(ValueError, match="kutu|x_min|y_min|x_max|y_max"):
        bbox_merkezi(kutu)
