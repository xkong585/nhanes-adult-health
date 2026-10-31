import json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from ml import regression_metrics,FEATURES

def test_weighted_errors_are_independently_known():
    m=regression_metrics(np.array([0.,2.]),np.array([1.,2.]),np.array([3.,1.]))
    assert m['weighted_MAE']==.75
    assert np.isclose(m['weighted_RMSE'],np.sqrt(.75))
    assert m['MAE']==.5

def test_no_target_or_design_variables_in_features():
    assert FEATURES==['RIDAGEYR','RIAGENDR','BMXBMI']

def test_outer_psu_validation_and_complete_oof():
    r=json.loads((ROOT/'evidence/ml_results.json').read_text())
    assert sum(f['test_n'] for f in r['folds'])==r['n']==4940
    assert all(f['PSU_overlap']==0 for f in r['folds'])
    assert len(r['scores'])==4
    assert all(np.isfinite(s['weighted_RMSE']) for s in r['scores'])
