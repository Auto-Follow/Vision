"""Kamera profili (YAML): SITL ve Pi profillerinin yuklenmesi, sema dogrulamasi ve uyari."""

import copy
import logging
import math
import re
from pathlib import Path

import pytest
import yaml

from vision.kamera_modeli import (
    KameraIcParametreleri,
    KameraModeli,
    KameraMontaji,
    kamera_modeli_yukle,
)

# Profil klasoru test dosyasina gore bulunur (Vision reposu icinde kalir).
PROFIL_KLASORU = Path(__file__).resolve().parents[1] / "config" / "kamera"
SITL_PROFILI = PROFIL_KLASORU / "sitl.yaml"
PI_PROFILI = PROFIL_KLASORU / "pi.yaml"

LOGGER_ADI = "vision.kamera_modeli"

# m06 x500_tez degerleri (Autopilot ozellik/m06-sim-ortami, 65e5bf793b); dosya okunmaz.
GENISLIK = 2304
YUKSEKLIK = 1296
YATAY_FOV_RAD = 1.151917
EGIM_ASAGI_RAD = 0.610865
OTELEME_FRD_M = (0.151, 0.0, 0.035)

GECERLI_PROFIL = {
    "kamera": {
        "genislik": 2304,
        "yukseklik": 1296,
        "fx": 1773.925033,
        "fy": 1773.925033,
        "cx": 1152.0,
        "cy": 648.0,
        "distorsiyon": [],
        "yer_tutucu": False,
    },
    "montaj": {
        "roll": 0.0,
        "pitch": -0.610865,
        "yaw": 0.0,
        "oteleme": [0.151, 0.0, 0.035],
        "yer_tutucu": False,
    },
}

SIL = object()


def uyari_kayitlari(caplog):
    return [
        kayit
        for kayit in caplog.records
        if kayit.name == LOGGER_ADI and kayit.levelno == logging.WARNING
    ]


def test_sitl_profili_m06_degerleriyle_tutarli():
    model = kamera_modeli_yukle(SITL_PROFILI)

    beklenen_f = (GENISLIK / 2) / math.tan(YATAY_FOV_RAD / 2)
    assert isinstance(model, KameraModeli)
    assert isinstance(model.ic, KameraIcParametreleri)
    assert isinstance(model.montaj, KameraMontaji)
    assert (model.ic.genislik, model.ic.yukseklik) == (GENISLIK, YUKSEKLIK)
    assert model.ic.fx == pytest.approx(beklenen_f, abs=1e-6)
    assert model.ic.fy == pytest.approx(beklenen_f, abs=1e-6)
    assert model.ic.fx == pytest.approx(1773.9, abs=0.05)
    assert (model.ic.cx, model.ic.cy) == (GENISLIK / 2, YUKSEKLIK / 2)
    assert model.ic.distorsiyon == ()
    assert model.montaj.roll == 0.0
    assert model.montaj.pitch == pytest.approx(-EGIM_ASAGI_RAD, abs=1e-12)
    assert math.degrees(model.montaj.pitch) == pytest.approx(-35.0, abs=1e-4)
    assert model.montaj.yaw == 0.0
    assert model.montaj.oteleme == pytest.approx(OTELEME_FRD_M, abs=1e-12)
    assert model.ic_yer_tutucu is False
    assert model.montaj_yer_tutucu is False
    assert model.yer_tutucu is False


def test_sitl_profili_uyari_vermez(caplog):
    caplog.set_level(logging.WARNING, logger=LOGGER_ADI)

    kamera_modeli_yukle(SITL_PROFILI)

    assert uyari_kayitlari(caplog) == []


def test_pi_profili_yer_tutucu_ve_bir_kez_uyari_verir(caplog):
    caplog.set_level(logging.WARNING, logger=LOGGER_ADI)

    model = kamera_modeli_yukle(PI_PROFILI)

    assert model.ic_yer_tutucu is True
    assert model.montaj_yer_tutucu is True
    assert (model.ic.genislik, model.ic.yukseklik) == (GENISLIK, YUKSEKLIK)
    assert model.montaj.pitch == pytest.approx(-EGIM_ASAGI_RAD, abs=1e-12)
    uyarilar = uyari_kayitlari(caplog)
    assert len(uyarilar) == 1
    mesaj = uyarilar[0].getMessage()
    assert "kamera" in mesaj
    assert "montaj" in mesaj
    assert "yer tutucu" in mesaj


@pytest.mark.parametrize(
    ("bolum", "anahtar", "deger", "beklenen_alan"),
    [
        ("kamera", "fx", SIL, "kamera.fx"),
        ("kamera", "distorsiyon", SIL, "kamera.distorsiyon"),
        ("montaj", "yer_tutucu", SIL, "montaj.yer_tutucu"),
        (None, "montaj", SIL, "montaj"),
        ("kamera", "genislik", "2304", "kamera.genislik"),
        ("kamera", "yer_tutucu", "hayir", "kamera.yer_tutucu"),
        ("montaj", "oteleme", "0.151 0 0.035", "montaj.oteleme"),
        (None, "kamera", [1, 2], "kamera"),
        ("kamera", "fy", 0.0, "kamera.fy"),
        ("kamera", "distorsiyon", [0.1, 0.0, 0.0], "kamera.distorsiyon"),
        ("montaj", "pitch", math.nan, "montaj.pitch"),
        ("montaj", "oteleme", [0.151, 0.0], "montaj.oteleme"),
        ("kamera", "hfov", 1.151917, "kamera.hfov"),
    ],
)
def test_hatali_profil_alan_adiyla_deger_hatasi_verir(
    tmp_path, bolum, anahtar, deger, beklenen_alan
):
    profil = copy.deepcopy(GECERLI_PROFIL)
    hedef = profil if bolum is None else profil[bolum]
    if deger is SIL:
        del hedef[anahtar]
    else:
        hedef[anahtar] = deger
    yol = tmp_path / "hatali.yaml"
    yol.write_text(yaml.safe_dump(profil), encoding="utf-8")

    with pytest.raises(ValueError, match=re.escape(beklenen_alan)):
        kamera_modeli_yukle(yol)


@pytest.mark.parametrize("icerik", ["", "- kamera\n- montaj\n", "kamera: [\n"])
def test_eslem_olmayan_veya_bozuk_yaml_deger_hatasi_verir(tmp_path, icerik):
    yol = tmp_path / "bozuk.yaml"
    yol.write_text(icerik, encoding="utf-8")

    with pytest.raises(ValueError, match=re.escape(str(yol))):
        kamera_modeli_yukle(yol)
