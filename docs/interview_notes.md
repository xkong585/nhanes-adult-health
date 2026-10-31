# 90-second project explanation

I built a reproducible analysis of adult BMI and continuous HbA1c using four
NHANES 2017-2018 components. The main deliverable is a reliable analysis dataset
and evidence trail, not a prediction leaderboard. I verified participant keys,
join cardinality, variable-specific missingness and mutually exclusive exclusions.

The final domain contains 4,940 adult complete cases. I built the full MEC
survey design before domain subsetting, using two-year exam weights, strata
and nested PSUs. The adjusted coefficient was about 0.125 HbA1c percentage
points per 5 BMI units, with a 95% interval of 0.103 to 0.146. It is an
association, not a causal effect or a diagnosis.

A real issue was that one XPT decoder turned zero weights into tiny positive
numbers. An independent R decoder revealed 550 incorrect apparent positive
weights. I fixed the decoding path, added a regression test, and independently
reconciled weighted means, Taylor standard errors and regression coefficients
in Python. The automated report only publishes after those checks pass.

The limits are historic cross-sectional data, item missingness and treatment
or unmeasured confounding. Survey weighting does not remove every source of
selection bias. I can show the complete-case comparison and sensitivity results.

## Questions to be ready for

- Why MEC rather than interview/fasting weights? BMI and HbA1c are MEC measures;
  no fasting subsample variable is used.
- Why subset the design? Preserve the original strata/PSU structure and the
  random domain sample size for Taylor variance estimation.
- Why t intervals? Public design has 30 PSUs minus 15 strata; regression
  residual df also subtract the non-intercept model degrees of freedom.
- Why no outlier deletion? Real extremes can be valid. They are flagged and
  diagnostics are shown; values are not removed to improve a result.

## ML interview discussion

Added PSU-grouped five-fold held-out HbA1c benchmarks on 4,940 adults. Weighted MAE: mean baseline 0.5460, age/sex ridge 0.4987, age/sex/BMI ridge 0.4867, gradient boosting 0.5003 percentage points. BMI ridge reduced MAE by 10.9% versus the mean baseline. The nonlinear model did not outperform ridge. These are concurrent measurements, not future diabetes prediction.

Explain: (1) why the split matches the data unit; (2) how future features are excluded; (3) why a baseline is mandatory; (4) why calibration can fail to improve performance; (5) why permutation importance is not a causal coefficient.
