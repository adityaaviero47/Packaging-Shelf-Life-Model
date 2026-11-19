"""Moisture-limited shelf life of a milk-protein nutrition powder in four flexible packs,
plus an accelerated shelf-life (ASLT) check for vitamin C.

Physics: water vapour permeates the pack film at a rate set by the film's permeance and the
vapour-pressure gap between the room and the product's headspace (its water activity).
The product takes up that water along its GAB sorption isotherm until it reaches a critical
water activity (caking / lactose crystallisation). Shelf life = time to reach it.

    t = mass * solids / (P * A * p_sat(T)) * integral[ dm / (RH - aw) ]   from aw_i to aw_c

P (permeance) comes from the film's WVTR at 38 C/90% RH (ASTM F1249, dry side 0% RH).
Every input is a (low, base, high) triple in data/inputs.csv with its source.
All results are model outputs, not measured shelf lives.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
R = 8.314  # J/(mol K)
DAYS_PER_MONTH = 30.44
PACKS = ["foil", "alox", "met", "bopp"]
PACK_LABELS = {
    "foil": "PET/Al foil/PE",
    "alox": "AlOx-PET/PE",
    "met": "Metallised film",
    "bopp": "BOPP/PE (clear)",
}
ZONES = {"iva": "Zone IVa 30 C/65% RH", "ivb": "Zone IVb 30 C/75% RH", "acc": "Accelerated 40 C/75% RH"}
TEST_T, TEST_RH = 37.8, 0.90  # ASTM F1249 WVTR condition


def load_inputs(path: Path | None = None) -> dict[str, dict]:
    path = path or ROOT / "data" / "inputs.csv"
    rows = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            for k in ("low", "base", "high"):
                r[k] = float(r[k])
            if not r["low"] <= r["base"] <= r["high"]:
                raise ValueError(f"{r['id']}: need low <= base <= high")
            rows[r["id"]] = r
    return rows


def scenario(inputs, which="base"):
    return {k: v[which] for k, v in inputs.items()}


def p_sat(t_c):
    """Saturation vapour pressure of water in kPa (Buck equation)."""
    t_c = np.asarray(t_c, dtype=float)
    return 0.61121 * np.exp((18.678 - t_c / 234.5) * (t_c / (257.14 + t_c)))


def gab(aw, m0, c, k):
    """Equilibrium moisture (kg water per kg dry matter) at water activity aw."""
    u = k * aw
    return m0 * c * u / ((1 - u) * (1 - u + c * u))


def moisture_integral(aw_i, aw_c, rh, m0, c, k, n=400):
    """integral of dm/(RH - aw) from aw_i to aw_c, by the midpoint rule on n steps (vectorised)."""
    aw_i, aw_c, rh = np.broadcast_arrays(np.asarray(aw_i, float), np.asarray(aw_c, float), np.asarray(rh, float))
    s = np.linspace(0.0, 1.0, n + 1)
    grid = aw_i[..., None] + (aw_c - aw_i)[..., None] * s
    m0, c, k = (np.asarray(x, float)[..., None] if np.ndim(x) else x for x in (m0, c, k))
    m = gab(grid, m0, c, k)
    dm = np.diff(m, axis=-1)
    mid = 0.5 * (grid[..., 1:] + grid[..., :-1])
    with np.errstate(divide="ignore", invalid="ignore"):
        val = np.sum(dm / (rh[..., None] - mid), axis=-1)
    return np.where(aw_c < rh, val, np.inf)


def permeance(wvtr):
    """g per (m2 day kPa) from WVTR measured at 38 C/90% RH against 0% RH."""
    return np.asarray(wvtr, float) / (TEST_RH * p_sat(TEST_T))


def shelf_life_days(p, pack, zone):
    T, RH = p[f"T_{zone}"], p[f"RH_{zone}"]
    I = moisture_integral(p["aw_i"], p["aw_c"], RH, p["m0"], p["C"], p["K"])
    P = permeance(p[f"wvtr_{pack}"])
    return p["mass"] * p["solids"] / (P * p["area"] * p_sat(T)) * I


def evaluate(p):
    out = {}
    for pk in PACKS:
        out[pk] = {z: shelf_life_days(p, pk, z) / DAYS_PER_MONTH for z in ZONES}
        out[pk]["water_g_to_fail"] = p["mass"] * p["solids"] * (gab(p["aw_c"], p["m0"], p["C"], p["K"]) - gab(p["aw_i"], p["m0"], p["C"], p["K"]))
    return out


def arrhenius_factor(ea_kj, t_hot_c, t_cold_c):
    """How many times faster a reaction runs at t_hot than at t_cold."""
    return float(np.exp(ea_kj * 1000 / R * (1 / (t_cold_c + 273.15) - 1 / (t_hot_c + 273.15))))


def aslt_check(p):
    """Equivalent months at Zone IVb of a 6-month 40 C/75% RH test, for two failure modes."""
    af_vit = arrhenius_factor(p["Ea_vitc"], p["T_acc"], p["T_ivb"])
    # moisture route: same RH (75%) in both, so the ratio is the vapour-pressure ratio
    af_moist = float(p_sat(p["T_acc"]) / p_sat(p["T_ivb"]))
    return dict(af_vitamin_c=af_vit, af_moisture=af_moist,
                months_equiv_vitamin_c=6 * af_vit, months_equiv_moisture=6 * af_moist,
                af_vitamin_c_30_to_25=arrhenius_factor(p["Ea_vitc"], 30, 25))


if __name__ == "__main__":
    import json
    b = scenario(load_inputs())
    print(json.dumps({k: {z: float(v) for z, v in d.items()} for k, d in evaluate(b).items()}, indent=1))
    print(json.dumps(aslt_check(b), indent=1))
    print("psat", float(p_sat(37.8)), float(p_sat(30)), float(p_sat(40)))
