"""Checks the recalculated workbook against the Python model (run after Excel/LibreOffice recalc)."""
import sys
from openpyxl import load_workbook
from model import PACKS, ROOT, ZONES, aslt_check, evaluate, load_inputs, scenario

wb = load_workbook(ROOT / "model" / "Packaging_Shelf_Life_Model.xlsx", data_only=True)
p = scenario(load_inputs()); ev = evaluate(p); a = aslt_check(p)
ws = wb["Shelf Life"]; bad = 0
for i, pk in enumerate(PACKS, 2):
    for col, z in zip("BCD", ZONES):
        x, y = ws[f"{col}{i}"].value, float(ev[pk][z])
        if x is None or abs(x - y) > 1e-6 * max(1, y):
            print("MISMATCH", pk, z, x, y); bad += 1
    if abs(ws[f"F{i}"].value - float(ev[pk]["water_g_to_fail"])) > 1e-6:
        bad += 1; print("water", pk)
wa = wb["ASLT"]
for r, k in {2: "af_vitamin_c", 3: "af_moisture", 4: "months_equiv_vitamin_c", 5: "months_equiv_moisture", 6: "af_vitamin_c_30_to_25"}.items():
    if abs(wa[f"B{r}"].value - a[k]) > 1e-6:
        bad += 1; print("aslt", k, wa[f"B{r}"].value, a[k])
print("Excel matches Python" if not bad else f"{bad} mismatches"); sys.exit(bad > 0)
