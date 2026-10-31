"""Generate aggregate-only report, responsive evidence explorer and two-page PDF."""
from pathlib import Path
import html
import json
import os
os.environ.setdefault('MPLCONFIGDIR', str(Path(__file__).resolve().parents[1]/'.mplconfig'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from prepare import ROOT

INK='#163c3c'; TEAL='#007e78'; GOLD='#cf8b31'
LIMITATIONS = ('Cross-sectional association; no temporal or causal inference. Complete-case selection may bias estimates. '
               'MEC weights address the sample design, not all item missingness. Age is top-coded at 80; linear age adjustment '
               'may leave residual confounding. Treatment, lifestyle and other unmeasured factors are not adjusted. '
               'Sparse BMI bands have wider intervals. Results describe the 2017-2018 cycle, not current health status. '
               'The analysis is an independent public-data portfolio project, unaffiliated with Kaiser Permanente; no clinical recommendations.')

def records(name):
    return pd.read_csv(ROOT/'evidence'/name).to_dict('records')

def make_charts():
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'axes.labelcolor':INK,'text.color':INK,'axes.titleweight':'bold','figure.facecolor':'white'})
    b=pd.read_csv(ROOT/'evidence/bmi_band_means.csv')
    fig,ax=plt.subplots(figsize=(8,3.8),layout='constrained')
    x=np.arange(len(b));ax.errorbar(x,b.estimate,yerr=[b.estimate-b.lower,b.upper-b.estimate],fmt='o-',color=TEAL,capsize=5,lw=1.7)
    ax.set_xticks(x,[f'{r.group}\nn={r.n:,}' for r in b.itertuples()]);ax.set_xlabel('Measured BMI band (kg/m²)');ax.set_ylabel('Mean HbA1c (%)')
    ax.set_title('Higher BMI bands have higher mean HbA1c',loc='left',pad=16)
    ax.grid(axis='y',alpha=.15);fig.savefig(ROOT/'reports/fig_bmi_hba1c.png',dpi=180);plt.close(fig)
    f=pd.read_csv(ROOT/'evidence/cohort_flow.csv')
    labels=['Interviewed','Age 20+','Positive MEC weight','BMI available','HbA1c + covariates']
    ns=[int(f.n.sum())]
    for reason in ['under_20','no_MEC_weight','BMI_missing','HbA1c_missing']:
        ns.append(ns[-1]-int(f.loc[f.stage==reason,'n'].iloc[0]))
    fig,ax=plt.subplots(figsize=(8,3.1),layout='constrained')
    ax.barh(labels[::-1],ns[::-1],color=[TEAL]*4+['#b8d5d1'])
    for i,n in enumerate(ns[::-1]):ax.text(n+60,i,f'{n:,}',va='center')
    ax.set_xlim(0,max(ns)*1.15);ax.set_xlabel('Observed participants (unweighted)');ax.set_title('From source population to analysis domain',loc='left')
    fig.savefig(ROOT/'reports/fig_cohort_flow.png',dpi=180);plt.close(fig)
    r=pd.read_csv(ROOT/'evidence/residual_band_means.csv')
    fig,ax=plt.subplots(figsize=(8,3),layout='constrained');ax.axhline(0,color='#8b9e9b',lw=1)
    ax.errorbar(np.arange(len(r)),r.estimate,yerr=[r.estimate-r.lower,r.upper-r.estimate],fmt='o',color=TEAL,capsize=4)
    ax.set_xticks(np.arange(len(r)),r.group);ax.set_xlabel('BMI band (kg/m²)');ax.set_ylabel('Mean residual (pp)')
    ax.set_title('Aggregate residuals: inspect linearity',loc='left');fig.savefig(ROOT/'reports/fig_residuals.png',dpi=180);plt.close(fig)

def pdf_brief(primary, table):
    c=canvas.Canvas(str(ROOT/'reports/brief.pdf'),pagesize=(612,792))
    c.setTitle('NHANES 2017-2018 | Adult BMI and HbA1c');c.setAuthor('Xiangyi (Sam) Kong')
    style=ParagraphStyle('p',fontName='Helvetica',fontSize=10,leading=15,textColor=HexColor(INK))
    def para(text,y,height=80):
        p=Paragraph(text,style);w,h=p.wrap(516,height);p.drawOn(c,48,y-h);return y-h
    def header(page,title):
        c.setFillColor(HexColor(TEAL));c.rect(0,744,612,48,fill=1,stroke=0);c.setFillColor(HexColor('#ffffff'));c.setFont('Helvetica-Bold',11)
        c.drawString(48,763,'PUBLIC HEALTH / REPRODUCIBLE RESEARCH');c.setFillColor(HexColor(INK));c.setFont('Helvetica-Bold',22);c.drawString(48,705,title)
        c.setFont('Helvetica',9);c.drawString(48,28,'Xiangyi (Sam) Kong | Independent portfolio study | 31 October 2026');c.drawRightString(564,28,f'{page} / 2')
    header(1,'BMI and HbA1c in U.S. adults')
    para('NHANES 2017-2018 | Adults aged 20+ | Four official CDC components',682)
    c.setFont('Helvetica-Bold',30);c.drawString(48,613,f'+{primary["estimate"]:.3f} pp')
    para(f'Adjusted HbA1c difference per 5 kg/m² higher BMI. 95% CI {primary["lower"]:.3f} to {primary["upper"]:.3f}; n={int(primary["n"]):,}.',594)
    para('A positive association persists after adjustment for age and recorded sex. This estimate does not show that changing BMI causes a change in HbA1c.',545)
    c.drawImage(ImageReader(str(ROOT/'reports/fig_cohort_flow.png')),48,295,width=516,height=200,mask='auto')
    para('<b>Question and methods.</b> DEMO_J is the participant spine; GHB_J supplies HbA1c, BMX_J supplies BMI, and DIQ_J supplies reported diabetes status. Keys and joins are validated before analysis. The full positive-weight MEC design is built before adult and complete-case domains.',270)
    para('<b>Inference.</b> R survey uses WTMEC2YR, SDMVSTRA and nested SDMVPSU, with Taylor linearization. Means use domain design t intervals; regression uses residual design degrees of freedom. Weighting does not correct all complete-case selection.',174)
    c.showPage();header(2,'Results, checks and limits')
    c.drawImage(ImageReader(str(ROOT/'reports/fig_bmi_hba1c.png')),48,416,width=516,height=245,mask='auto')
    para('Points are survey-weighted complete-case domain means; bars are 95% t intervals. Unweighted sample sizes are printed below each BMI band. These are descriptive means, not adjusted predictions.',405)
    sens=pd.read_csv(ROOT/'evidence/sensitivity_table.csv');no=sens.query("model=='no_reported_diabetes'").iloc[0]
    para(f'<b>Sensitivity.</b> In the prespecified DIQ010=2 domain (no reported diabetes), the BMI coefficient is {no.estimate:.3f} pp (95% CI {no.lower:.3f}-{no.upper:.3f}; n={int(no.n):,}). This domain excludes borderline and unknown answers and is not all adults.',343)
    para('<b>Verification.</b> Python normal equations reproduce the primary coefficients; an independent stratum/PSU Taylor calculation reproduces both mean standard errors. All eight reconciliation checks pass. Corrupt keys, schema failures, invalid categories and domain calculations have executable tests.',265)
    para('<b>Limitations.</b> '+LIMITATIONS,187)
    para('<b>Sources.</b> CDC/NCHS NHANES 2017-2018 DEMO_J, GHB_J, BMX_J, DIQ_J. Exact URLs, SHA256 hashes, codebooks, run logs and aggregate tables are included in the repository. Data use is limited to statistical analysis and reporting.',82)
    c.save()

def build():
    out=ROOT/'reports';out.mkdir(exist_ok=True)
    make_charts()
    primary=pd.read_csv(ROOT/'evidence/model_results.csv').query("model=='primary' and term=='bmi5'").iloc[0].to_dict()
    table=records('table1.csv')
    payload={'primary':primary,'table':table,'models':records('sensitivity_table.csv'),'bands':records('bmi_band_means.csv'),
             'flow':records('cohort_flow.csv'),'joins':records('join_audit.csv'),'checks':records('qc_checks.csv'),
             'reconcile':records('reconciliation_checks.csv'),'design':records('design_summary.csv'),
             'missing':records('complete_case_comparison.csv'),'diagnostics':records('diagnostics.csv'),
             'investigations':json.loads((ROOT/'evidence/investigation_items.json').read_text())}
    (out/'summary.json').write_text(json.dumps(payload,indent=2,allow_nan=False))
    template=(ROOT/'src/dashboard.html').read_text()
    page=template.replace('/*__DATA__*/',json.dumps(payload,allow_nan=False)).replace('__LIMITATIONS__',html.escape(LIMITATIONS))
    (out/'report.html').write_text(page)
    (out/'index.html').write_text(page)
    (ROOT/'docs/limitations.md').write_text('# Interpretation and limitations\n\n'+LIMITATIONS+'\n\n'+
        'The DIQ010=2 subgroup is based on reported diagnosis, not absence of diabetes. Pregnant adults are not excluded in this fixed minimal scope. '
        'The race-adjusted and quadratic specifications are sensitivity analyses, not chosen as a new primary model.\n')
    pdf_brief(primary,table)
    diagnostics='<!doctype html><html lang="en"><meta charset="utf-8"><title>Model diagnostics</title><body><h1>Primary-model diagnostics</h1><img width="800" src="fig_residuals.png" alt="Residual means by BMI band">'+pd.DataFrame(payload['diagnostics']).to_html(index=False)+'<p>The maximum leverage and residual pattern are descriptive checks. Real extremes remain in the primary model. See the prespecified quadratic model in model_results.csv; the quadratic linear coefficient alone is not a constant per-5-unit effect.</p></body></html>'
    (out/'model_diagnostics.html').write_text(diagnostics)
    (ROOT/'docs/resume_bullets.md').write_text(f'''# Verified project statements | completed 2026-10-31

- Integrated four official NHANES 2017-2018 components into a validated analysis dataset of {int(primary['n']):,} adult complete cases, with provenance hashes, one-to-one merge audits and mutually exclusive cohort exclusions.
- Applied R survey weights, strata and PSUs to estimate BMI-HbA1c associations with 95% confidence intervals; independently reconciled estimates and Taylor standard errors in Python and documented prespecified sensitivity analyses.
- Automated audited data preparation, aggregate reporting, two-page PDF generation and a responsive evidence dashboard; retained analysis limitations and executable failure-case tests.

Do not claim Kaiser employment, clinical practice, causality, current prevalence, or measured business savings.\n''')

if __name__=='__main__':
    build()
