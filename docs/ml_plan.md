# ML protocol

Frozen before first model execution. NHANES: 5-fold GroupKFold by nested stratum/PSU. Weighted mean, ridge alpha=10 (age/sex and age/sex/BMI), and HGB 100 iterations, 7 leaves, min leaf40, L2=10, early stopping off. Training weights normalized to mean one; weighted MAE/RMSE and unweighted MAE/RMSE on OOF predictions. No tuning or selection on outer folds.

Participant-level inputs and predictions remain ignored under data/processed. Published metrics are aggregates only. Results are exploratory portfolio benchmarks; they do not replace the original analysis.
