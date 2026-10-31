"""Pre-specified, PSU-held-out continuous HbA1c benchmarks (not clinical prediction)."""
import json
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from threadpoolctl import threadpool_limits
from prepare import ROOT
from ml_report import publish
FEATURES=['RIDAGEYR','RIAGENDR','BMXBMI']

def regression_metrics(y,p,w):
    return {'weighted_MAE':float(np.average(abs(y-p),weights=w)),'weighted_RMSE':float(np.sqrt(np.average((y-p)**2,weights=w))),'MAE':float(np.mean(abs(y-p))),'RMSE':float(np.sqrt(np.mean((y-p)**2)))}

def run_ml():
    d=pd.read_parquet(ROOT/'data/processed/cohort_flags.parquet');d=d.loc[d.main_model_complete].copy().reset_index(drop=True)
    X=d[FEATURES].astype(float);y=d.LBXGH.to_numpy(float);w=d.WTMEC2YR.to_numpy(float)
    groups=d.SDMVSTRA.astype(str)+'_'+d.SDMVPSU.astype(str)
    names=['Weighted mean','Age + sex ridge','Age + sex + BMI ridge','Gradient boosting']
    importance=[]
    predictions={name:np.full(len(d),np.nan) for name in names};folds=[]
    with threadpool_limits(limits=1):
        for fold,(tr,te) in enumerate(GroupKFold(5).split(X,y,groups)):
            assert set(groups.iloc[tr]).isdisjoint(groups.iloc[te])
            weights=w[tr]/w[tr].mean();predictions[names[0]][te]=np.average(y[tr],weights=weights)
            for name,cols in [(names[1],FEATURES[:2]),(names[2],FEATURES)]:
                model=make_pipeline(StandardScaler(),Ridge(alpha=10.0));model.fit(X.iloc[tr][cols],y[tr],ridge__sample_weight=weights);predictions[name][te]=model.predict(X.iloc[te][cols])
            model=HistGradientBoostingRegressor(max_iter=100,max_leaf_nodes=7,min_samples_leaf=40,l2_regularization=10,early_stopping=False,random_state=20261031)
            model.fit(X.iloc[tr],y[tr],sample_weight=weights);predictions[names[3]][te]=model.predict(X.iloc[te])
            pi=permutation_importance(model,X.iloc[te],y[te],scoring='neg_mean_absolute_error',sample_weight=w[te],n_repeats=5,random_state=20261031)
            importance.append(dict(zip(FEATURES,pi.importances_mean.tolist())))
            folds.append({'fold':fold,'train_n':len(tr),'test_n':len(te),'train_groups':int(groups.iloc[tr].nunique()),'test_groups':int(groups.iloc[te].nunique()),'PSU_overlap':0,'scores':[{'model':n,**regression_metrics(y[te],p[te],w[te])} for n,p in predictions.items()]})
    assert all(np.isfinite(p).all() for p in predictions.values())
    subgroup=[]
    for variable,labels in [('sex',d.RIAGENDR.map({1:'Male',2:'Female'})),('age',pd.cut(d.RIDAGEYR,[19,39,59,100],labels=['20-39','40-59','60+']).astype(str))]:
        for label in sorted(labels.unique()):
            mask=(labels==label).to_numpy()
            for name,p in predictions.items():subgroup.append({'variable':variable,'group':label,'n':int(mask.sum()),'model':name,**regression_metrics(y[mask],p[mask],w[mask])})
    out=d[['SEQN','SDMVSTRA','SDMVPSU']].copy()
    for n,p in predictions.items():out[n]=p
    out.to_parquet(ROOT/'data/processed/ml_oof_predictions.parquet',index=False)
    result={'title':'NHANES | HbA1c ML benchmarks','scope':f'{len(d):,} complete-case adults, NHANES 2017-2018. Predict concurrent HbA1c (%) using age, sex and BMI. Original survey association analysis remains the primary analysis.','validation':'Five outer folds hold out entire nested stratum/PSU groups. All transformations and weighted fits use training folds only. Hyperparameters were fixed in advance; no outer-fold model selection. Every adult receives one held-out prediction. Weighted metrics use MEC weights; these are predictive scores, not survey-design confidence intervals.','limitations':'Cross-sectional prediction does not establish causality or predict future diabetes. Complete cases are a selected population; no external validation. Fold differences and sex/age errors are diagnostics, not proof of fairness. Race, diagnosis and outcome-derived features are excluded.','primary_metric':'weighted_MAE','n':len(d),'features':FEATURES,'scores':[{'model':n,**regression_metrics(y,p,w)} for n,p in predictions.items()],'folds':folds,'subgroups':subgroup,'permutation_importance':{'model':'Gradient boosting','metric':'increase in held-out weighted MAE','mean_by_feature':{k:float(np.mean([v[k] for v in importance])) for k in FEATURES},'repeats_per_fold':5,'used_for_selection':False},'seed':20261031}
    publish(ROOT,result);return result
if __name__=='__main__':run_ml()
