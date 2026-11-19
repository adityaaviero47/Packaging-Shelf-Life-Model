"""Runs the full analysis: base case, Monte Carlo, tornado, ASLT check, charts, Excel model."""
from __future__ import annotations

import csv
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from model import PACK_LABELS, PACKS, ROOT, ZONES, aslt_check, evaluate, gab, load_inputs, scenario  # noqa: E402
from montecarlo import run, tornado  # noqa: E402

RES, CH = ROOT / "results", ROOT / "charts"


def main():
    RES.mkdir(exist_ok=True); CH.mkdir(exist_ok=True)
    inp = load_inputs(); b = scenario(inp)
    ev = evaluate(b)
    summary = {
        "base_case_months": {pk: {z: round(float(ev[pk][z]), 2) for z in ZONES} for pk in PACKS},
        "water_g_to_failure": round(float(ev["foil"]["water_g_to_fail"]), 2),
        "aslt": {k: round(v, 3) for k, v in aslt_check(b).items()},
        "monte_carlo": run(inp),
        "tornado_alox_ivb": tornado(inp)[:6],
    }
    (RES / "summary.json").write_text(json.dumps(summary, indent=2))
    with open(RES / "shelf_life_by_pack.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pack", "zone_iva_months", "zone_ivb_months", "accelerated_months", "p_meets_18m_ivb"])
        for pk in PACKS:
            w.writerow([PACK_LABELS[pk], *[round(float(ev[pk][z]), 1) for z in ZONES], summary["monte_carlo"][pk]["ivb"]["p_meets_target"]])

    # Chart 1: shelf life at Zone IVb with P10-P90 whiskers, log scale, 18-month line
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    mc = summary["monte_carlo"]
    for i, pk in enumerate(PACKS):
        p10, p50, p90 = mc[pk]["ivb"]["p10_p50_p90"]
        ax.errorbar(i, p50, yerr=[[p50 - p10], [p90 - p50]], fmt="o", color="#1F3A5F", capsize=6, ms=7)
        ax.text(i + 0.12, p50, f"{p50:.0f} mo\n{mc[pk]['ivb']['p_meets_target']:.0%} meet 18 mo", va="center", fontsize=8.5)
    ax.axhline(b["target"], color="#C0392B", ls="--", lw=1)
    ax.text(3.45, b["target"] * 1.08, "18-month target", color="#C0392B", fontsize=8.5, ha="right")
    ax.set_yscale("log"); ax.set_xlim(-0.4, 3.9)
    ax.set_xticks(range(4), [PACK_LABELS[p] for p in PACKS], fontsize=9)
    ax.set_ylabel("Months to critical aw (log scale)")
    ax.set_title("Moisture-limited shelf life at Zone IVb (30 C/75% RH): median and P10-P90", loc="left", fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(CH / "shelf_life_by_pack.png", dpi=160); plt.close(fig)

    # Chart 2: tornado for AlOx pack
    t = tornado(inp)[:5][::-1]
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    for i, r in enumerate(t):
        lo, hi = sorted((r["low"], r["high"]))
        ax.barh(i, hi - lo, left=lo, color="#1F3A5F")
    ax.axvline(t[0]["base"], color="#999", lw=1)
    ax.axvline(b["target"], color="#C0392B", ls="--", lw=1)
    short = {"aw_c": "Critical water activity", "wvtr_alox": "Film WVTR (AlOx-PET/PE)", "area": "Pouch area", "aw_i": "Water activity at packing"}
    ax.set_yticks(range(len(t)), [short.get(r["input"], r["label"]) for r in t], fontsize=9)
    ax.set_xlim(0, max(max(r["low"], r["high"]) for r in t) * 1.08)
    ax.set_xlabel("Months at Zone IVb, AlOx-PET/PE pouch (each input low to high)")
    ax.set_title("What moves shelf life most", loc="left", fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(CH / "tornado_alox.png", dpi=160); plt.close(fig)

    # Chart 3: isotherm with packing and critical aw
    aw = np.linspace(0.05, 0.8, 200)
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    ax.plot(aw, 100 * gab(aw, b["m0"], b["C"], b["K"]), color="#1F3A5F")
    for x, lab in ((b["aw_i"], "packed"), (b["aw_c"], "critical")):
        ax.axvline(x, color="#999", ls=":", lw=1); ax.text(x + 0.01, 2, lab, fontsize=8.5)
    ax.set_xlabel("Water activity"); ax.set_ylabel("Moisture (g per 100 g dry matter)")
    ax.set_title("GAB isotherm, milk protein concentrate MPC80 at 25 C", loc="left", fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(CH / "isotherm.png", dpi=160); plt.close(fig)

    from build_excel import build
    build(ROOT / "model" / "Packaging_Shelf_Life_Model.xlsx")
    print(json.dumps({k: summary[k] for k in ("base_case_months", "water_g_to_failure", "aslt")}, indent=1))


if __name__ == "__main__":
    main()
