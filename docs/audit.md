# Event-eligibility audit

The model does not assume that every official price event is usable for statistical evaluation.

An event is **eligible** when its previous 30 calendar days contain at least four valid market/FX-derived observations for the mapped fuel benchmark.

With the bundled source snapshot:

| Fuel | Official events | Eligible events | Walk-forward OLS predictions |
|---|---:|---:|---:|
| Diesel | 11 | 9 | 3 |
| Petrol | 11 | 9 | 3 |
| Octane | 11 | 9 | 3 |

The first January event has no prior market history in the bundled benchmark archive. The February event has only three prior market observations within the 30-day rule and is therefore excluded. The remaining 2026 events have sufficient market-window coverage.

This is why the dashboard should show explicit sample-size warnings rather than filling missing validation metrics with arbitrary numbers.

## Current cutoff caveat

The current benchmark series end on different dates. In particular, RON95 ends earlier than Gasoil/RON92 in the current public archive. Therefore the Octane nowcast cutoff can precede the latest official retail event. The model excludes later official events from current calibration and labels the situation on the website.
