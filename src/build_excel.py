"""Builds model/Packaging_Shelf_Life_Model.xlsx: a live Excel model on named input cells.

The moisture integral is laid out row by row (400 midpoint steps, as in src/model.py), so
the workbook recalculates when any input is overridden. Monte Carlo results are values.
"""
from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName

from model import PACK_LABELS, PACKS, ROOT, ZONES, load_inputs

F = "Arial"
BLUE, NORM, BOLD = Font(name=F, color="0000FF"), Font(name=F), Font(name=F, bold=True)
HEAD, HFILL, YFILL = Font(name=F, bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1F3A5F"), PatternFill("solid", fgColor="FFFF00")
N = 400


def header(ws, row, vals, widths):
    for j, v in enumerate(vals, 1):
        c = ws.cell(row=row, column=j, value=v)
        c.font, c.fill = HEAD, HFILL
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for j, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(j)].width = w


def name(wb, nm, ref):
    wb.defined_names[nm] = DefinedName(nm, attr_text=ref)


def build(out: Path):
    inp = load_inputs()
    wb = Workbook()
    ws = wb.active
    ws.title = "Read Me"
    for i, (t, f) in enumerate([
        ("Packaging Shelf-Life Model: moisture barrier and accelerated testing for a nutrition powder", BOLD),
        ("Time for a milk-protein powder in a 500 g pouch to reach its critical water activity, for 4 pack films and 3 storage conditions.", NORM),
        ("", NORM),
        ("Inputs: blue = sourced or assumed value (low / base / high). Type in the yellow Override column to test a scenario.", NORM),
        ("Moisture Uptake: the moisture integral, 400 midpoint steps along the GAB isotherm from packing aw to critical aw.", NORM),
        ("Shelf Life: months to failure per pack and condition. ASLT: what a 6-month 40 C/75% RH test is worth at 30 C.", NORM),
        ("Uncertainty: Monte Carlo results computed in Python (src/montecarlo.py); these do not recalculate.", NORM),
        ("", NORM),
        ("All results are model outputs on published data and stated assumptions, not measured shelf lives.", NORM),
        ("Film permeance is held constant with temperature, which overstates water uptake at 30 C (a conservative choice).", NORM),
    ], 1):
        ws.cell(row=i, column=1, value=t).font = f
    ws.column_dimensions["A"].width = 120

    ws = wb.create_sheet("Inputs")
    header(ws, 1, ["ID", "Group", "Input", "Unit", "Low", "Base", "High", "Override", "Active", "Basis", "Source"],
           [11, 10, 52, 26, 9, 9, 9, 10, 10, 11, 100])
    ws.freeze_panes = "A2"
    for i, (k, v) in enumerate(inp.items(), 2):
        for j, val in enumerate([k, v["group"], v["parameter"], v["unit"]], 1):
            ws.cell(row=i, column=j, value=val).font = NORM
        for j, s in zip((5, 6, 7), ("low", "base", "high")):
            ws.cell(row=i, column=j, value=v[s]).font = BLUE
        ws.cell(row=i, column=8).fill = YFILL
        ws.cell(row=i, column=9, value=f"=IF(ISBLANK(H{i}),F{i},H{i})").font = NORM
        ws.cell(row=i, column=10, value=v["basis"]).font = NORM
        ws.cell(row=i, column=11, value=v["source"] + (f" | {v['url']}" if v["url"] else "")).font = NORM
        fmt = "0.0%" if v["unit"] == "fraction" else ("0.0000" if k == "m0" else "#,##0.00")
        for j in (5, 6, 7, 8, 9):
            ws.cell(row=i, column=j).number_format = fmt
        name(wb, f"in_{k}", f"Inputs!$I${i}")

    # ---- vapour pressures and permeances
    ws = wb.create_sheet("Films")
    header(ws, 1, ["Item", "Value", "Unit", "Formula logic"], [44, 14, 26, 70])
    buck = lambda t: f"0.61121*EXP((18.678-({t})/234.5)*(({t})/(257.14+({t}))))"
    rows = [("Saturation vapour pressure at 37.8 C (WVTR test)", "=" + buck("37.8"), "kPa", "Buck equation"),
            ("Saturation vapour pressure, Zone IVa", "=" + buck("in_T_iva"), "kPa", "Buck equation"),
            ("Saturation vapour pressure, Zone IVb", "=" + buck("in_T_ivb"), "kPa", "Buck equation"),
            ("Saturation vapour pressure, accelerated", "=" + buck("in_T_acc"), "kPa", "Buck equation")]
    for pk in PACKS:
        rows.append((f"Permeance, {PACK_LABELS[pk]}", f"=in_wvtr_{pk}/(0.9*B2)", "g per m2 per day per kPa", "WVTR / (0.90 x p_sat at 37.8 C); dry side at 0% RH"))
    for i, (a, f, u, l) in enumerate(rows, 2):
        ws.cell(row=i, column=1, value=a).font = NORM
        c = ws.cell(row=i, column=2, value=f); c.font = NORM; c.number_format = "0.0000"
        ws.cell(row=i, column=3, value=u).font = NORM
        ws.cell(row=i, column=4, value=l).font = NORM
    names = {"ps_test": "B2", "ps_iva": "B3", "ps_ivb": "B4", "ps_acc": "B5"}
    for j, pk in enumerate(PACKS):
        names[f"perm_{pk}"] = f"B{6 + j}"
    for nm, ref in names.items():
        name(wb, nm, f"Films!${ref[0]}${ref[1:]}")

    # ---- moisture integral
    ws = wb.create_sheet("Moisture Uptake")
    header(ws, 1, ["Step", "aw", "Moisture (kg/kg dm)", "Step dm", "aw midpoint", "Zone IVa term", "Zone IVb term", "Accelerated term"],
           [8, 10, 18, 14, 12, 14, 14, 16])
    gabf = lambda a: f"in_m0*in_C*in_K*({a})/((1-in_K*({a}))*(1-in_K*({a})+in_C*in_K*({a})))"
    for s in range(N + 1):
        r = s + 2
        ws.cell(row=r, column=1, value=s)
        ws.cell(row=r, column=2, value=f"=in_aw_i+(in_aw_c-in_aw_i)*A{r}/{N}").number_format = "0.0000"
        ws.cell(row=r, column=3, value="=" + gabf(f"B{r}")).number_format = "0.00000"
        if s > 0:
            ws.cell(row=r, column=4, value=f"=C{r}-C{r-1}").number_format = "0.000000"
            ws.cell(row=r, column=5, value=f"=(B{r}+B{r-1})/2").number_format = "0.0000"
            for col, z in zip((6, 7, 8), ("iva", "ivb", "acc")):
                ws.cell(row=r, column=col, value=f"=D{r}/(in_RH_{z}-E{r})").number_format = "0.000000"
    last = N + 2
    ws.cell(row=last + 2, column=5, value="Integral").font = BOLD
    for col, z in zip((6, 7, 8), ("iva", "ivb", "acc")):
        L = get_column_letter(col)
        c = ws.cell(row=last + 2, column=col, value=f"=SUM({L}3:{L}{last})"); c.number_format = "0.0000"; c.font = BOLD
        name(wb, f"I_{z}", f"'Moisture Uptake'!${L}${last + 2}")
    ws.freeze_panes = "A2"

    # ---- shelf life
    ws = wb.create_sheet("Shelf Life")
    header(ws, 1, ["Pack film", "Zone IVa (months)", "Zone IVb (months)", "Accelerated (months)", "Meets target at IVb?", "Water to failure (g)"],
           [24, 18, 18, 20, 20, 20])
    for i, pk in enumerate(PACKS, 2):
        ws.cell(row=i, column=1, value=PACK_LABELS[pk]).font = NORM
        for col, z in zip((2, 3, 4), ("iva", "ivb", "acc")):
            c = ws.cell(row=i, column=col, value=f"=in_mass*in_solids/(perm_{pk}*in_area*ps_{z})*I_{z}/30.44")
            c.number_format = "#,##0.0"
        ws.cell(row=i, column=5, value=f'=IF(C{i}>=in_target,"Yes","No")')
        ws.cell(row=i, column=6, value="=in_mass*in_solids*(" + gabf("in_aw_c") + "-" + gabf("in_aw_i") + ")").number_format = "0.0"
    ws.cell(row=7, column=1, value="Target (months)").font = BOLD
    ws.cell(row=7, column=2, value="=in_target").number_format = "0"

    # ---- ASLT
    ws = wb.create_sheet("ASLT")
    header(ws, 1, ["Item", "Value", "Formula logic"], [62, 12, 80])
    aslt = [("Vitamin C acceleration factor, 40 C vs 30 C", "=EXP(in_Ea_vitc*1000/8.314*(1/(in_T_ivb+273.15)-1/(in_T_acc+273.15)))", "Arrhenius, first-order loss"),
            ("Moisture acceleration factor, 40 C/75% vs 30 C/75%", "=ps_acc/ps_ivb", "Same RH both sides, constant permeance"),
            ("6 months at 40 C/75% RH equals, for vitamin C (months at 30 C)", "=6*B2", ""),
            ("6 months at 40 C/75% RH equals, for moisture uptake (months at 30 C/75%)", "=6*B3", ""),
            ("Vitamin C acceleration factor, 30 C vs 25 C", "=EXP(in_Ea_vitc*1000/8.314*(1/(25+273.15)-1/(30+273.15)))", "Arrhenius")]
    for i, (a, f, l) in enumerate(aslt, 2):
        ws.cell(row=i, column=1, value=a).font = NORM
        ws.cell(row=i, column=2, value=f).number_format = "0.00"
        ws.cell(row=i, column=3, value=l).font = NORM

    # ---- Monte Carlo (values)
    ws = wb.create_sheet("Uncertainty")
    mc = json.loads((ROOT / "results" / "summary.json").read_text())["monte_carlo"]
    ws.cell(row=1, column=1, value="Monte Carlo: 20,000 draws, independent triangular (low, base, high), seed 11. Values from Python; they do not recalculate.").font = BOLD
    header(ws, 3, ["Pack film", "Zone", "P(meets target)", "P10 (months)", "P50", "P90"], [24, 26, 16, 14, 12, 12])
    r = 4
    for pk in PACKS:
        for z in ("iva", "ivb"):
            s = mc[pk][z]
            for j, v in enumerate([PACK_LABELS[pk], ZONES[z], s["p_meets_target"], *s["p10_p50_p90"]], 1):
                c = ws.cell(row=r, column=j, value=v); c.font = NORM
                c.number_format = "0.0%" if j == 3 else "#,##0.0"
            r += 1

    ws = wb.create_sheet("Sources")
    header(ws, 1, ["Input", "Source"], [52, 140])
    for i, (k, v) in enumerate(inp.items(), 2):
        ws.cell(row=i, column=1, value=v["parameter"]).font = NORM
        ws.cell(row=i, column=2, value=v["source"] + (f" | {v['url']}" if v["url"] else " | assumption")).font = NORM

    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    print("wrote", out)


if __name__ == "__main__":
    build(ROOT / "model" / "Packaging_Shelf_Life_Model.xlsx")
