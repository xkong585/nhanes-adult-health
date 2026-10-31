import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
import pytest
from prepare import validate_component,recode_diq,cohort_flags,ROOT
from reconcile import taylor_domain_mean

def test_duplicate_key_blocks_merge():
    with pytest.raises(ValueError,match='SEQN'):
        validate_component(pd.DataFrame({'SEQN':[1,1],'LBXGH':[5,6]}),'GHB_J')

def test_missing_schema_blocks_merge():
    with pytest.raises(ValueError,match='missing required'):
        validate_component(pd.DataFrame({'SEQN':[1]}),'GHB_J')

def test_diq_borderline_and_missing_distinct():
    clean,reason=recode_diq(pd.Series([1,2,3,7,9,np.nan]))
    assert clean[:3].tolist()==['yes','no','borderline']
    assert clean[3:].isna().all()
    assert reason[3:].tolist()==['refused','dont_know','source_missing']

def test_unknown_diq_stops_pipeline():
    with pytest.raises(ValueError): recode_diq(pd.Series([4]))

def test_mutually_exclusive_exclusions_and_zero_weight():
    d=pd.DataFrame({'SEQN':[1,2,3,4],'RIDAGEYR':[19,30,40,50], 'WTMEC2YR':[1,0,2,3],
       'SDMVSTRA':[1]*4,'SDMVPSU':[1,2,1,2],'BMXBMI':[np.nan,np.nan,np.nan,27],
       'LBXGH':[np.nan,np.nan,np.nan,7],'RIAGENDR':[1,2,1,2],'DIQ010':[2,2,2,3]})
    r=cohort_flags(d)
    assert r.exclusion_reason.tolist()==['under_20','no_MEC_weight','BMI_missing','retained']
    assert r.loc[3,'LBXGH']==7 # HbA1c 7% is not a questionnaire missing code.

def test_full_design_includes_zero_score_psu():
    mec=pd.DataFrame({'WTMEC2YR':[1.,1.,1.,1.],'x':[1.,3.,100.,100.],
                      'SDMVSTRA':[1,1,1,1],'SDMVPSU':[1,1,2,2]})
    mean,se=taylor_domain_mean(mec,'x',[True,True,False,False])
    assert mean==2 and se==0 # Both within-PSU deviations cancel.
    mean,se=taylor_domain_mean(mec,'x',[True,False,True,False])
    assert mean==50.5 and se==49.5

def test_singleton_psu_fails():
    mec=pd.DataFrame({'WTMEC2YR':[1.],'x':[2.],'SDMVSTRA':[1],'SDMVPSU':[1]})
    with pytest.raises(ValueError,match='Singleton'):taylor_domain_mean(mec,'x',[True])

@pytest.mark.skipif(not (ROOT/'data/processed/DEMO_J.csv').exists(),reason='downloaded-data integration check')
def test_official_zero_weight_decoder_regression():
    d=pd.read_csv(ROOT/'data/processed/DEMO_J.csv')
    assert d.WTMEC2YR.eq(0).sum()==550
    assert d.WTMEC2YR.gt(0).sum()==8704
    assert not d.WTMEC2YR.between(0,1e-50,inclusive='neither').any()

@pytest.mark.skipif(not (ROOT/'evidence/reconciliation_checks.csv').exists(),reason='integration evidence absent')
def test_generated_evidence_conserves_and_reconciles():
    flow=pd.read_csv(ROOT/'evidence/cohort_flow.csv')
    assert flow.n.sum()==9254
    assert flow.loc[flow.stage=='retained','n'].iloc[0]==4940
    assert pd.read_csv(ROOT/'evidence/reconciliation_checks.csv')['pass'].all()
    joins=pd.read_csv(ROOT/'evidence/join_audit.csv')
    assert joins.left_rows.eq(joins.output_rows).all()

def test_failed_rerun_invalidates_published_reports(tmp_path,monkeypatch):
    import run_pipeline
    (tmp_path/'reports').mkdir();(tmp_path/'evidence').mkdir()
    for name in ['report.html','index.html','brief.pdf','summary.json','model_diagnostics.html']:
        (tmp_path/'reports'/name).write_text('stale report')
    def broken_download():raise ValueError('intentional corrupt source')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(run_pipeline,'ROOT',tmp_path)
    monkeypatch.setattr(run_pipeline,'download',broken_download)
    with pytest.raises(ValueError,match='intentional'):
        run_pipeline.run()
    assert not (tmp_path/'reports/report.html').exists()
    assert not (tmp_path/'reports/brief.pdf').exists()
    import json
    assert json.loads((tmp_path/'evidence/run_log.json').read_text())['status']=='failed'
