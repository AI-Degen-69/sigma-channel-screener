"""Acceptance tests for the channel decision in monthly_screener.py.

Run from the repo root: python -m pytest tests -q
"""
import math
import pathlib
import sys

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import monthly_screener as ms


def _row(**kw):
    base = dict(price=50.0, mid=80.0, std=10.0, low3=50.0, low4=40.0, slope_up=True, k=3)
    base.update(kw)
    return ms.classify_channel(**base)


def test_action_at_the_band():
    r = _row()
    assert r["signal"] == "action"
    assert r["note"].startswith("ACTION: at/below -3")
    assert r["pos"] == pytest.approx(-3.0)


def test_action_uses_low4_when_k_is_4():
    r = _row(price=40.0, k=4)
    assert r["signal"] == "action"
    assert r["note"].startswith("ACTION: at/below -4")
    assert "(standard)" in r["note"]


def test_action_keeps_s_tier_suffix():
    assert "(S-tier)" in _row()["note"]


def test_watch_zone_between_half_and_full_band():
    r = _row(price=52.0)
    assert r["signal"] == "watch"
    assert r["note"].startswith("WATCH: near -3")
    assert r["pos"] == pytest.approx(-2.8)


def test_hold_above_the_watch_zone():
    r = _row(price=79.0)
    assert r["signal"] == "hold"
    assert r["note"] == "hold/cash - no signal"


def test_flat_channel_wins_over_every_other_branch():
    r = _row(price=10.0, slope_up=False)
    assert r["signal"] == "skip_flat"
    assert r["note"].startswith("SKIP: channel flat/down")


def test_negative_low3_is_skipped():
    r = _row(low3=-1.0)
    assert r["signal"] == "skip_band"
    assert r["note"].startswith("SKIP: -3/-4 band below zero")


def test_negative_low4_only_skips_the_k4_row():
    r = _row(low3=5.0, low4=-2.0, k=4, price=60.0)
    assert r["signal"] == "skip_band"
    assert _row(low3=5.0, low4=-2.0, k=3, price=60.0)["signal"] != "skip_band"


def test_zero_std_gives_nan_position_instead_of_raising():
    r = _row(price=100.0, mid=100.0, std=0.0, low3=90.0, low4=85.0)
    assert math.isnan(r["pos"])
    assert r["signal"] == "hold"


def test_screen_attaches_signal_to_every_row(monkeypatch):
    n = ms.W + 100
    closes = np.linspace(100.0, 300.0, n) + np.sin(np.arange(n) / 10.0) * 2.0
    dates = np.array([f"d{i}" for i in range(n)])

    monkeypatch.setattr(ms, "live_mcaps", lambda tickers: {})
    monkeypatch.setattr(ms, "fetch", lambda ticker, force=False: (dates, closes, None))

    rows = ms.screen()
    assert rows, "screen() returned no rows"
    for r in rows:
        assert "signal" in r, f"{r.get('ticker')} has no signal"
        assert r["signal"] in {"skip_flat", "skip_band", "action", "watch", "hold"}
    assert any(r["signal"] == "hold" for r in rows)
