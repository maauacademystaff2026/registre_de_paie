"""Tests de core/utils.py."""

import pytest

from core.utils import detecter_periode, hhmm_to_minutes, minutes_to_hhmm


@pytest.mark.parametrize(
    "texte,minutes",
    [("00:00", 0), ("02:00", 120), ("00:45", 45), ("100:15", 6015)],
)
def test_hhmm_to_minutes(texte, minutes):
    assert hhmm_to_minutes(texte) == minutes


def test_hhmm_to_minutes_format_invalide_leve_value_error():
    with pytest.raises(ValueError):
        hhmm_to_minutes("pas une durée")


def test_minutes_to_hhmm_est_l_inverse_de_hhmm_to_minutes():
    assert minutes_to_hhmm(125) == "02:05"


def test_detecter_periode_prend_le_mois_majoritaire():
    dates = ["2026-07-01", "2026-07-15", "2026-07-31", "2026-08-01"]
    assert detecter_periode(dates) == (2026, 7)


def test_detecter_periode_liste_vide_renvoie_none():
    assert detecter_periode([]) is None
