# Analysis plan | frozen before estimation, 2026-10-31

Question: among U.S. civilian noninstitutionalized adults aged >=20 in NHANES
2017-2018, what is the association between measured BMI and continuous HbA1c?
This is a cross-sectional statistical analysis, not a diagnostic or causal study.

Inputs: DEMO_J, GHB_J, BMX_J, DIQ_J from CDC. DEMO is the left-join spine.
Every SEQN must be nonmissing and unique; orphan component keys or inflated joins
stop publication. Never remove duplicates to force a pass.

Primary model: survey::svyglm(LBXGH ~ bmi5 + RIDAGEYR + sex), Gaussian identity,
where bmi5=BMXBMI/5 and sex is the original two-level RIAGENDR category.
Use MEC 2-year WTMEC2YR, strata SDMVSTRA, nested PSU SDMVPSU. First construct
the full positive-weight MEC design, then subset adults and complete cases.
Report regression t intervals with the model residual design df. Descriptive
means use t intervals with the domain design df. Fail on lonely PSU.

Exclusion order (mutually exclusive): age missing; age <20; no positive MEC
weight; missing BMI; missing HbA1c; missing adjustment variables; retained.
Missing design identifiers among positive-weight participants are fatal.
No imputation and no data-dependent outlier deletion. Retain all positive
measured BMI/HbA1c, flag BMI >60 or HbA1c >14 for review. Height/weight audit
checks agreement within 0.2 kg/m²; discrepancies are warnings, not deletions.
DIQ010=1 yes, 2 no, 3 borderline, 7 refused, 9 don't know, dot missing.
Only valid DIQ010=2 enters the prespecified no-reported-diabetes domain.
Never treat HbA1c values 7 or 9 as missing.

Table 1: complete-case weighted means (BMI, HbA1c, age and female proportion)
for all adults and age groups 20-39, 40-59, 60+. Show unweighted n and 95% CIs.
Figures: mutually exclusive cohort flow; HbA1c domain means for fixed BMI bands
<18.5, 18.5-<25, 25-<30, 30-<35, 35-<40, >=40, with n and intervals.

Sensitivity: (1) weighted vs unweighted means for the same complete cases;
(2) primary model in DIQ010=2 domain; (3) additional RIDRETH3 adjustment;
(4) quadratic BMI term as a prespecified shape check. No model selection based
on significance. Plot aggregate residual means by BMI band and summarize
leverage, without publishing participant-level records.

Independent reconciliation: Python weighted means, weighted normal-equation
coefficients, and stratum/PSU Taylor variances against R survey. Means contribute
zero outside their domain while retaining all MEC PSUs. Integration tests cover
corrupt keys, missing fields, unknown codes, flow conservation and nonzero
out-of-domain PSU contributions. Report retained/excluded adult demographics.

Limitations: complete-case selection, top-coded age (80), linear age adjustment,
treatment and unmeasured confounding, sparse domains, nonresponse, historic
single-cycle estimates. No causal claim, disease prediction, prevalence claim,
or 2026 population estimate. All outputs are generated from actual data.
