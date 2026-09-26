# How to interpret Bangladesh Fuel Observatory numbers

## International benchmark equivalent

This is the selected international refined-product benchmark converted from USD/barrel into Tk/litre:

\[
\text{Benchmark} \times \text{USD/BDT} \div 158.9873
\]

It answers:

> **What does the international benchmark correspond to in Bangladesh taka per litre?**

It does **not** mean that a Bangladesh filling station should necessarily sell the fuel at that amount.

## Market-window signal

This is the average of available converted benchmark values during the previous 30 calendar days before the relevant event/cutoff.

It is meant to represent a smoothed market signal rather than a single-day market print.

## Domestic calibration

This is an empirical residual:

> official retail price − prior market-window signal

It is a model component, not a government cost ledger.

## Model-implied retail estimate

This is the primary model's estimate:

> prior market-window signal + expanding domestic calibration

It is an independent analytical nowcast. It is not an official Bangladesh price and is not presented as a universal “fair price”.

## Scenario Lab

Scenario Lab is a hypothetical experiment. A user changes the benchmark and exchange rate and the site recalculates:

1. international benchmark equivalent;
2. domestic calibration component;
3. model-implied retail estimate;
4. comparison with the official reference at the model cutoff.

The Scenario Lab is **not** a government recommendation or a future-price guarantee.

## Why an official event may be shown as “not used”

A market series can end before a later official event. RON95 is currently an example: its latest public benchmark observation can precede a later official price event. The model uses the latest available benchmark date as its cutoff and does not allow later official information to leak into that nowcast.
