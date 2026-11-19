# Test protocol: replacing the model's assumptions with measurements

The tornado shows 3 inputs drive almost all the uncertainty. These are the tests that pin them down, in order of value.

| # | Test | What it measures | Replaces | Why it matters |
|---|---|---|---|---|
| 1 | Sorption isotherm of the finished formulation (dynamic vapour sorption or saturated salt jars, 25 °C, aw 0.1 to 0.8) | GAB m0, C, K | MPC80 literature isotherm | Sugar, cocoa and premix change water uptake |
| 2 | Critical aw: hold samples at 5 aw levels for 4 weeks; check caking, flowability and lactose crystallisation (DSC or XRD) | aw_c | Assumed 0.40 | Largest single driver (13.8 to 52.4 months) |
| 3 | WVTR of the actual laminate, flat film and finished pouch, ASTM F1249 at 38 °C/90% RH | Film WVTR | Supplier datasheet | Second driver; pouches with folds and seals beat datasheets |
| 4 | Water activity at packing, 3 batches | aw_i | Assumed 0.20 | Sets the starting point |
| 5 | Stability study: 40 °C/75% RH for 6 months and 30 °C/75% RH real time; pull at 0, 1, 2, 3, 6 months for aw, moisture, vitamin C, sensory | Validates model | Model alone | Checks moisture and vitamin C separately |

## Decision rule

Pick the lightest film whose P10 shelf life at Zone IVb, rerun with measured inputs, clears the target. Do not read a 6-month accelerated pass as 18 months for moisture: the moisture acceleration factor is about 1.7, not 3.
