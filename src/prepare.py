"""Audited one-to-one integration and explicit analysis-domain flags."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    'DEMO_J': ['SEQN','RIDAGEYR','RIAGENDR','RIDRETH3','WTMEC2YR','SDMVSTRA','SDMVPSU'],
    'GHB_J': ['SEQN','LBXGH'],
    'BMX_J': ['SEQN','BMXBMI','BMXWT','BMXHT'],
    'DIQ_J': ['SEQN','DIQ010'],
}
DIQ = {1:'yes', 2:'no', 3:'borderline', 7:'refused', 9:'dont_know'}

def validate_component(df, name):
    absent = sorted(set(REQUIRED[name]) - set(df.columns))
    if absent:
        raise ValueError(f'{name}: missing required fields {absent}')
    if df.SEQN.isna().any() or df.SEQN.duplicated().any():
        raise ValueError(f'{name}: SEQN must be nonmissing and unique; merge stopped')

def recode_diq(series):
    if not series.dropna().isin(DIQ).all():
        raise ValueError('Unexpected DIQ010 category')
    reason = series.map(DIQ).fillna('source_missing')
    clean = reason.where(reason.isin(['yes','no','borderline']))
    return clean, reason

def cohort_flags(df):
    df = df.copy()
    positive = df.WTMEC2YR.notna() & np.isfinite(df.WTMEC2YR) & (df.WTMEC2YR > 0)
    if df.loc[positive, ['SDMVSTRA','SDMVPSU']].isna().any().any():
        raise ValueError('Positive-weight MEC participant missing design identifiers')
    df['mec_usable'] = positive
    df['adult'] = df.RIDAGEYR.ge(20)
    df['diabetes_status'], df['diq_reason'] = recode_diq(df.DIQ010)
    df['exclusion_reason'] = np.select([
        df.RIDAGEYR.isna(), df.RIDAGEYR.lt(20), ~positive,
        df.BMXBMI.isna(), df.LBXGH.isna(),
        df[['RIDAGEYR','RIAGENDR']].isna().any(axis=1)
    ], ['age_missing','under_20','no_MEC_weight','BMI_missing','HbA1c_missing','adjustment_missing'], default='retained')
    df['main_model_complete'] = df.exclusion_reason.eq('retained')
    df['bmi5'] = df.BMXBMI / 5
    return df

def prepare():
    evidence = ROOT / 'evidence'
    evidence.mkdir(exist_ok=True)
    checks, tables, profile = [], {}, []
    for name in REQUIRED:
        df = pd.read_csv(ROOT / f'data/processed/{name}.csv')
        try:
            validate_component(df, name)
        except ValueError:
            # Participant-level conflicts are local only, never report assets.
            df[df.SEQN.isna() | df.SEQN.duplicated(keep=False)].to_csv(ROOT / 'data/processed/key_conflicts.csv', index=False)
            raise
        checks.extend([{'check':f'{name}.required_fields','status':'pass'}, {'check':f'{name}.key_unique_nonnull','status':'pass'}])
        for col in REQUIRED[name]:
            s = df[col]
            profile.append({'component':name,'field':col,'rows':len(df),'columns_in_source':len(df.columns),
                            'missing':int(s.isna().sum()),'min':s.min(),'max':s.max()})
        tables[name] = df[REQUIRED[name]]
    # Independent decoder audit: pandas 2.3.3 maps source zeros to a tiny positive.
    pandas_demo = pd.read_sas(ROOT/'data/raw/DEMO_J.xpt',format='xport')
    r_demo = tables['DEMO_J']
    pd.DataFrame([{'decoder':'R foreign::read.xport','MEC_zero_weights':int(r_demo.WTMEC2YR.eq(0).sum()),
                   'MEC_positive_weights':int(r_demo.WTMEC2YR.gt(0).sum()),'used_for_analysis':True},
                  {'decoder':'pandas read_sas xport','MEC_zero_weights':int(pandas_demo.WTMEC2YR.eq(0).sum()),
                   'MEC_positive_weights':int(pandas_demo.WTMEC2YR.gt(0).sum()),'used_for_analysis':False}]).to_csv(evidence/'decoder_audit.csv',index=False)
    merged = tables['DEMO_J']
    audits = []
    for name in ['GHB_J','BMX_J','DIQ_J']:
        other = tables[name]
        orphans = set(other.SEQN) - set(merged.SEQN)
        if orphans:
            raise ValueError(f'{name}: {len(orphans)} orphan keys')
        before = len(merged)
        merged = merged.merge(other, on='SEQN', how='left', validate='one_to_one', indicator=True)
        matched = int(merged._merge.eq('both').sum())
        audits.append({'component':name,'left_rows':before,'right_rows':len(other),'matched':matched,
                       'unmatched':before-matched,'orphan_keys':len(orphans),'output_rows':len(merged),
                       'interpretation':{'GHB_J':'Age 12+ MEC lab component; unmatched include younger/non-examined participants',
                       'BMX_J':'Examined participants with body measurements; variable eligibility differs by age',
                       'DIQ_J':'Questionnaire age 1+; infants are not eligible'}[name]})
        merged = merged.drop(columns='_merge')
        if len(merged) != before:
            raise ValueError('Join inflated DEMO rows')
        checks.append({'check':f'{name}.one_to_one_left_join','status':'pass'})
    for col, allowed in [('RIAGENDR',[1,2]),('RIDRETH3',[1,2,3,4,6,7])]:
        if not merged[col].dropna().isin(allowed).all():
            raise ValueError(f'Unexpected {col} category')
        checks.append({'check':f'{col}.valid_categories','status':'pass'})
    for col in ['BMXBMI','LBXGH']:
        if not (merged[col].dropna().gt(0) & np.isfinite(merged[col].dropna())).all():
            raise ValueError(f'Nonpositive or nonfinite {col}')
        checks.append({'check':f'{col}.positive_finite','status':'pass'})
    if (merged.WTMEC2YR.dropna() < 0).any():
        raise ValueError('Negative MEC weight')
    merged.to_parquet(ROOT / 'data/processed/merged_all.parquet', index=False)
    flagged = cohort_flags(merged)
    flagged.to_parquet(ROOT / 'data/processed/cohort_flags.parquet', index=False)
    flagged.to_csv(ROOT / 'data/processed/merged.csv', index=False)
    reasons = ['age_missing','under_20','no_MEC_weight','BMI_missing','HbA1c_missing','adjustment_missing','retained']
    counts = flagged.exclusion_reason.value_counts().reindex(reasons,fill_value=0)
    if counts.sum() != len(flagged):
        raise ValueError('Cohort flow does not conserve participants')
    checks.extend([{'check':'cohort.flow_conservation','status':'pass'},
                   {'check':'MEC.design_identifiers','status':'pass'}, {'check':'DIQ010.variable_specific_recode','status':'pass'}])
    pd.DataFrame({'stage':counts.index,'n':counts.values}).to_csv(evidence / 'cohort_flow.csv',index=False)
    adult = flagged[flagged.adult & flagged.mec_usable]
    adult[['BMXBMI','LBXGH','RIAGENDR','RIDRETH3','DIQ010']].isna().sum().rename('missing').to_csv(evidence / 'missingness_summary.csv')
    comparison = []
    for retained, group in adult.groupby('main_model_complete'):
        comparison.append({'group':'retained' if retained else 'excluded','n':len(group),
                           'unweighted_mean_age':group.RIDAGEYR.mean(),
                           'unweighted_female_fraction':group.RIAGENDR.eq(2).mean(),
                           'denominator':'positive-MEC-weight adults; excludes interview-only adults'})
    pd.DataFrame(comparison).to_csv(evidence / 'complete_case_comparison.csv',index=False)
    bmi_recalc = flagged.BMXWT / (flagged.BMXHT / 100)**2
    unit_diff = (bmi_recalc - flagged.BMXBMI).abs()
    warnings = {'BMI_over_60':int(flagged.BMXBMI.gt(60).sum()), 'HbA1c_over_14':int(flagged.LBXGH.gt(14).sum()),
                'BMI_height_weight_disagreement_over_0_2':int(unit_diff.gt(.2).sum()),
                'height_weight_pairs_checked':int(unit_diff.notna().sum()),
                'interpretation':'Investigate; real measured extremes are retained. BMI uses rounded source height/weight.'}
    (evidence / 'investigation_items.json').write_text(json.dumps(warnings,indent=2))
    pd.DataFrame(profile).to_csv(evidence / 'raw_profile.csv',index=False)
    pd.DataFrame(audits).to_csv(evidence / 'join_audit.csv',index=False)
    pd.DataFrame(checks).to_csv(evidence / 'qc_checks.csv',index=False)
    flagged.diq_reason.value_counts().rename_axis('reason').rename('n').to_csv(evidence / 'diq_recode_audit.csv')
    return flagged

if __name__ == '__main__':
    prepare()
