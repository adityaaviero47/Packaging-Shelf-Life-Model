"""Monte Carlo over the (low, base, high) ranges and one-way tornado swings."""
from __future__ import annotations

import numpy as np

from model import PACKS, evaluate, scenario


def draw(inputs, n, seed):
    rng = np.random.default_rng(seed)
    return {k: (np.full(n, v["base"]) if v["low"] == v["high"] else rng.triangular(v["low"], v["base"], v["high"], n))
            for k, v in inputs.items()}


def run(inputs, n=20_000, seed=11):
    d = draw(inputs, n, seed)
    ev = evaluate(d)
    target = float(scenario(inputs)["target"])
    out = {}
    for pk in PACKS:
        out[pk] = {}
        for z in ("iva", "ivb"):
            x = ev[pk][z]
            out[pk][z] = dict(p_meets_target=float(np.mean(x >= target)),
                              p10_p50_p90=[float(v) for v in np.percentile(x, [10, 50, 90])])
    return out


def tornado(inputs, pack="alox", zone="ivb"):
    base = scenario(inputs)
    b0 = float(evaluate(base)[pack][zone])
    rows = []
    for k, v in inputs.items():
        if v["low"] == v["high"]:
            continue
        vals = []
        for w in ("low", "high"):
            p = dict(base); p[k] = v[w]
            vals.append(float(evaluate(p)[pack][zone]))
        if abs(vals[1] - vals[0]) > 1e-9:
            rows.append(dict(input=k, label=v["parameter"], low=vals[0], high=vals[1], swing=abs(vals[1] - vals[0]), base=b0))
    return sorted(rows, key=lambda r: -r["swing"])
