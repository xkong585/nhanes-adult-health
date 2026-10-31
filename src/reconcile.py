"""Independent normal equations and domain Taylor linearization, versus R survey."""
import numpy as np
import pandas as pd
from prepare import ROOT

def taylor_domain_mean(mec, column, domain):
    """Zero score outside domain, aggregate over ALL full-design nested PSUs."""
    w = mec.WTMEC2YR.to_numpy()
    x = mec[column].fillna(0).to_numpy()
    inside = np.asarray(domain,dtype=bool)
    total = w[inside].sum()
    mean = np.dot(w[inside],x[inside])/total
    scores = np.where(inside,w*(x-mean)/total,0.)
    frame = mec[['SDMVSTRA','SDMVPSU']].copy()
    frame['score'] = scores
    psu = frame.groupby(['SDMVSTRA','SDMVPSU']).score.sum()
    variance = 0.
    for _, values in psu.groupby(level=0):
        m=len(values)
        if m < 2:
            raise ValueError('Singleton PSU in full design')
        variance += m/(m-1)*np.square(values-values.mean()).sum()
    return float(mean), float(np.sqrt(variance))

def reconcile():
    d = pd.read_parquet(ROOT/'data/processed/cohort_flags.parquet')
    mec = d[d.mec_usable]
    domain = mec.main_model_complete.to_numpy()
    reference = pd.read_csv(ROOT/'evidence/table1.csv')
    rows=[]
    for col in ['BMXBMI','LBXGH']:
        mean,se=taylor_domain_mean(mec,col,domain)
        r=reference[(reference.group=='All adults') & (reference.variable==col)].iloc[0]
        for metric,py,rv in [('mean',mean,r.estimate),('Taylor_SE',se,r.se)]:
            rows.append({'check':f'{col}.{metric}','python':py,'R_survey':rv,'absolute_difference':abs(py-rv),'pass':bool(np.isclose(py,rv,atol=1e-9,rtol=1e-8))})
    a=mec[mec.main_model_complete]
    X=np.column_stack([np.ones(len(a)),a.bmi5,a.RIDAGEYR,a.RIAGENDR.eq(2).astype(float)])
    w=a.WTMEC2YR.to_numpy()
    beta=np.linalg.solve(np.einsum('ni,n,nj->ij',X,w,X),np.einsum('ni,n,n->i',X,w,a.LBXGH.to_numpy()))
    model=pd.read_csv(ROOT/'evidence/model_results.csv').query("model=='primary'").set_index('term')
    for term,value in zip(['(Intercept)','bmi5','RIDAGEYR','sexFemale'],beta):
        rv=model.loc[term,'estimate']
        rows.append({'check':f'primary.{term}','python':value,'R_survey':rv,'absolute_difference':abs(value-rv),'pass':bool(np.isclose(value,rv,atol=1e-9,rtol=1e-8))})
    results=pd.DataFrame(rows)
    results.to_csv(ROOT/'evidence/reconciliation_checks.csv',index=False)
    if not results['pass'].all():
        raise ValueError('Independent reconciliation failed; report blocked')
    return results

if __name__=='__main__':
    reconcile()
