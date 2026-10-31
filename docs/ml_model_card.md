# ML model card

Added PSU-grouped five-fold held-out HbA1c benchmarks on 4,940 adults. Weighted MAE: mean baseline 0.5460, age/sex ridge 0.4987, age/sex/BMI ridge 0.4867, gradient boosting 0.5003 percentage points. BMI ridge reduced MAE by 10.9% versus the mean baseline. The nonlinear model did not outperform ridge. These are concurrent measurements, not future diabetes prediction.

4,940 complete-case adults, NHANES 2017-2018. Predict concurrent HbA1c (%) using age, sex and BMI. Original survey association analysis remains the primary analysis.

Five outer folds hold out entire nested stratum/PSU groups. All transformations and weighted fits use training folds only. Hyperparameters were fixed in advance; no outer-fold model selection. Every adult receives one held-out prediction. Weighted metrics use MEC weights; these are predictive scores, not survey-design confidence intervals.

## Predictors

RIDAGEYR, RIAGENDR, BMXBMI

## Intended use and limits

Cross-sectional prediction does not establish causality or predict future diabetes. Complete cases are a selected population; no external validation. Fold differences and sex/age errors are diagnostics, not proof of fairness. Race, diagnosis and outcome-derived features are excluded.

Permutation importance measures the score decrease after independently permuting a feature. Correlated predictors can share information; the measure is not causal. It is not used for selecting features or hyperparameters. No model was selected by the held-out test score. Settings are deliberately fixed in docs/ml_plan.md, rather than tuned on evaluation folds. The scorecard is a benchmark, not a deployed medical tool.

## Reproducibility and privacy

Pinned packages, deterministic seeds, official source hashes, full pipeline tests, and empty-cache rerun evidence are included. No individual rows or serialized estimator are committed. The original descriptive/association analysis retains its separate assumptions and results.
