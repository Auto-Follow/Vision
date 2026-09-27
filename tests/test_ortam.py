"""Ortam dogrulama: sabit bagimliliklar dogru surumlerle yukleniyor mu."""

import sys
from importlib.metadata import version

import vision


def test_python_surumu():
    assert sys.version_info >= (3, 11)


def test_paket_surumu():
    assert vision.__version__ == "0.1.0"


def test_numpy_sabit_surum():
    assert version("numpy") == "2.4.6"


def test_opencv_numpy_ile_calisiyor():
    import cv2
    import numpy as np

    kare = np.zeros((48, 64, 3), dtype=np.uint8)
    gri = cv2.cvtColor(kare, cv2.COLOR_BGR2GRAY)
    assert gri.shape == (48, 64)


def test_pymavlink_yukleniyor():
    from pymavlink.dialects.v20 import common

    assert common.MAVLINK_MSG_ID_HEARTBEAT == 0
