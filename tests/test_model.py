import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from model import aslt_check, evaluate, gab, load_inputs, moisture_integral, p_sat, scenario  # noqa: E402
from montecarlo import run  # noqa: E402

B = scenario(load_inputs())


def test_inputs_complete_and_ordered():
    for k, v in load_inputs().items():
        assert v["low"] <= v["base"] <= v["high"], k
        assert v["source"], k


def test_buck_matches_steam_tables():
    # saturation pressure of water: 4.246 kPa at 30 C, 7.384 kPa at 40 C
    assert p_sat(30) == pytest.approx(4.246, rel=2e-3)
    assert p_sat(40) == pytest.approx(7.384, rel=2e-3)


def test_gab_rises_with_aw():
    m = gab(np.linspace(0.05, 0.8, 50), B["m0"], B["C"], B["K"])
    assert np.all(np.diff(m) > 0)


def test_integral_converges():
    a = moisture_integral(B["aw_i"], B["aw_c"], 0.75, B["m0"], B["C"], B["K"], n=400)
    b = moisture_integral(B["aw_i"], B["aw_c"], 0.75, B["m0"], B["C"], B["K"], n=4000)
    assert a == pytest.approx(b, rel=1e-4)


def test_no_failure_when_storage_rh_below_critical_aw():
    assert np.isinf(moisture_integral(0.2, 0.5, 0.45, B["m0"], B["C"], B["K"]))


def test_ranking_and_scaling():
    ev = evaluate(B)
    order = [ev[p]["ivb"] for p in ("foil", "alox", "met", "bopp")]
    assert order == sorted(order, reverse=True)
    # shelf life is inversely proportional to WVTR
    p2 = dict(B, wvtr_alox=2 * B["wvtr_alox"])
    assert evaluate(p2)["alox"]["ivb"] == pytest.approx(ev["alox"]["ivb"] / 2, rel=1e-9)
    # higher humidity shortens shelf life
    assert ev["alox"]["ivb"] < ev["alox"]["iva"]


def test_aslt_factors():
    a = aslt_check(B)
    assert a["af_vitamin_c"] == pytest.approx(2.90, abs=0.01)
    assert a["af_moisture"] == pytest.approx(p_sat(40) / p_sat(30))


def test_monte_carlo_reproducible():
    inp = load_inputs()
    assert run(inp, n=2000, seed=3) == run(inp, n=2000, seed=3)
