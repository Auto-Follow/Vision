"""Kamera modeli: ic parametre ve montaj dogrulamasi, optik -> govde FRD rotasyonu."""

import math

import numpy as np
import pytest

from vision.kamera_modeli import KameraIcParametreleri, KameraMontaji

GECERLI_IC = {
    "genislik": 2304,
    "yukseklik": 1296,
    "fx": 1773.9,
    "fy": 1773.9,
    "cx": 1152.0,
    "cy": 648.0,
}


def optik_eksen_govdede(roll: float, pitch: float, yaw: float) -> np.ndarray:
    rotasyon = KameraMontaji(roll=roll, pitch=pitch, yaw=yaw).optikten_govdeye()
    return rotasyon @ np.array([0.0, 0.0, 1.0])


def test_gecerli_ic_parametreler_nesne_olusturur():
    ic = KameraIcParametreleri(**GECERLI_IC, distorsiyon=[0.1, -0.05, 0.001, 0.002, 0.01])

    matris = ic.kamera_matrisi()
    katsayilar = ic.distorsiyon_katsayilari()
    assert matris.dtype == np.float64
    assert matris.shape == (3, 3)
    np.testing.assert_array_equal(
        matris, [[1773.9, 0.0, 1152.0], [0.0, 1773.9, 648.0], [0.0, 0.0, 1.0]]
    )
    assert katsayilar.dtype == np.float64
    assert katsayilar.shape == (5,)
    assert KameraIcParametreleri(**GECERLI_IC).distorsiyon_katsayilari().shape == (0,)
    with pytest.raises(AttributeError):
        ic.fx = 1.0  # frozen


@pytest.mark.parametrize(
    ("alan", "deger"),
    [
        ("genislik", 0),
        ("yukseklik", -1),
        ("genislik", 2304.5),
        ("fx", 0.0),
        ("fy", -1773.9),
        ("fx", math.nan),
        ("cx", math.inf),
        ("cy", "648"),
        ("distorsiyon", [0.1, 0.0, 0.0]),
        ("distorsiyon", [0.1, math.nan, 0.0, 0.0]),
    ],
)
def test_gecersiz_ic_parametre_alan_adiyla_deger_hatasi_verir(alan, deger):
    with pytest.raises(ValueError, match=alan):
        KameraIcParametreleri(**{**GECERLI_IC, alan: deger})


@pytest.mark.parametrize(
    ("alan", "deger"),
    [
        ("roll", math.nan),
        ("pitch", math.inf),
        ("yaw", -math.inf),
        ("oteleme", (0.151, 0.0, math.nan)),
        ("oteleme", (0.151, 0.0)),
    ],
)
def test_gecersiz_montaj_alan_adiyla_deger_hatasi_verir(alan, deger):
    montaj = {"roll": 0.0, "pitch": -0.610865, "yaw": 0.0, "oteleme": (0.151, 0.0, 0.035)}
    with pytest.raises(ValueError, match=alan):
        KameraMontaji(**{**montaj, alan: deger})


def test_sifir_acida_optik_eksenler_govde_eksenlerine_denk_gelir():
    rotasyon = KameraMontaji(roll=0.0, pitch=0.0, yaw=0.0).optikten_govdeye()

    np.testing.assert_allclose(rotasyon @ [0.0, 0.0, 1.0], [1.0, 0.0, 0.0], atol=1e-12)
    np.testing.assert_allclose(rotasyon @ [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], atol=1e-12)
    np.testing.assert_allclose(rotasyon @ [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], atol=1e-12)


@pytest.mark.parametrize(
    ("roll", "pitch", "yaw", "beklenen"),
    [
        (0.0, -math.pi / 2, 0.0, [0.0, 0.0, 1.0]),
        (0.0, 0.0, math.pi / 2, [0.0, 1.0, 0.0]),
        (
            0.0,
            -0.610865,
            0.0,
            [math.cos(math.radians(35.0)), 0.0, math.sin(math.radians(35.0))],
        ),
    ],
)
def test_pitch_ve_yaw_optik_ekseni_bilinen_yone_cevirir(roll, pitch, yaw, beklenen):
    np.testing.assert_allclose(optik_eksen_govdede(roll, pitch, yaw), beklenen, atol=1e-6)


def test_pozitif_pitch_optik_ekseni_yukari_kaldirir():
    eksen = optik_eksen_govdede(0.0, math.radians(10.0), 0.0)

    assert eksen[2] < 0.0
    assert eksen[0] > 0.0


def test_rastgele_acilarda_rotasyon_ortonormal_ve_determinanti_bir():
    uretec = np.random.default_rng(10)
    for roll, pitch, yaw in uretec.uniform(-math.pi, math.pi, size=(20, 3)):
        rotasyon = KameraMontaji(roll=roll, pitch=pitch, yaw=yaw).optikten_govdeye()

        assert rotasyon.dtype == np.float64
        np.testing.assert_allclose(rotasyon.T @ rotasyon, np.eye(3), atol=1e-12)
        assert np.linalg.det(rotasyon) == pytest.approx(1.0, abs=1e-12)


def test_pozitif_roll_goruntu_eksenlerini_optik_eksen_etrafinda_dondurur():
    rotasyon = KameraMontaji(roll=math.pi / 2, pitch=0.0, yaw=0.0).optikten_govdeye()

    # Sutunlar: goruntu sagi (optik x) -> asagi (+z), goruntu asagisi (optik y) -> sol
    # (-y), optik eksen (optik z) -> ileri (+x, degismez).
    np.testing.assert_allclose(
        rotasyon, [[0.0, 0.0, 1.0], [0.0, -1.0, 0.0], [1.0, 0.0, 0.0]], atol=1e-12
    )
    # Kucuk pozitif roll'de de goruntu sagi asagi egilir (isaret kurali).
    kucuk = KameraMontaji(roll=math.radians(5.0), pitch=0.0, yaw=0.0).optikten_govdeye()
    assert (kucuk @ [1.0, 0.0, 0.0])[2] > 0.0


SIN35 = math.sin(math.radians(35.0))
COS35 = math.cos(math.radians(35.0))


@pytest.mark.parametrize(
    ("roll", "optik_eksen", "goruntu_sagi"),
    [
        (0.0, [0.0, COS35, SIN35], [-1.0, 0.0, 0.0]),
        (math.pi / 2, [0.0, COS35, SIN35], [0.0, -SIN35, COS35]),
    ],
    ids=["roll_0", "roll_arti_90"],
)
def test_birlesik_acilar_zyx_sirasiyla_once_yaw_sonra_pitch_sonra_roll(
    roll, optik_eksen, goruntu_sagi
):
    # Yaw +90 derece (saga bakis) ve 35 derece asagi egim: ZYX sirasinda optik eksen
    # yaw ile saga donmus halde asagi egilir; baska bir sirada (ornek XYZ) (0, 1, 0) olurdu.
    rotasyon = KameraMontaji(
        roll=roll, pitch=-math.radians(35.0), yaw=math.pi / 2
    ).optikten_govdeye()

    np.testing.assert_allclose(rotasyon @ [0.0, 0.0, 1.0], optik_eksen, atol=1e-12)
    np.testing.assert_allclose(rotasyon @ [1.0, 0.0, 0.0], goruntu_sagi, atol=1e-12)
