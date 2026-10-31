"""Single fail-closed entry point; invalidate old public outputs before every run."""
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import time
from datetime import datetime,timezone
from importlib.metadata import version
from download_data import download,sha256
from prepare import prepare,ROOT
from reconcile import reconcile

def run():
    os.chdir(ROOT)
    start=time.perf_counter(); started=datetime.now(timezone.utc).isoformat()
    # An interrupted/failed rerun must not leave a publishable stale report.
    for name in ['report.html','index.html','brief.pdf','ml_report.html','ml_brief.pdf','summary.json','model_diagnostics.html']:
        (ROOT/'reports'/name).unlink(missing_ok=True)
    log={'started_at_utc':started,'status':'running','steps':[]}
    target=ROOT/'evidence/run_log.json'
    try:
        for name,operation in [
            ('download_and_verify',download),
            ('decode_official_XPT',lambda:subprocess.run(['Rscript','src/read_xpt.R'],check=True)),
            ('prepare_and_QC',prepare),
            ('survey_analysis',lambda:subprocess.run(['Rscript','src/survey_design.R'],check=True)),
            ('independent_reconciliation',reconcile),
            ('ML_benchmarks',lambda:__import__('ml').run_ml()),
            ('tests',lambda:subprocess.run([os.sys.executable,'-m','pytest','-q','tests','--junitxml=evidence/tests.xml'],check=True)),
        ]:
            t=time.perf_counter();operation();log['steps'].append({'name':name,'seconds':round(time.perf_counter()-t,3)})
        from report import build
        build()
        from ml_report import link_main
        link_main(ROOT)
        log['ml_plan_sha256']=__import__('hashlib').sha256((ROOT/'docs/ml_plan.md').read_bytes()).hexdigest()
        log.update(status='passed',elapsed_seconds=round(time.perf_counter()-start,3),
                   environment={'python':platform.python_version(),'platform':platform.platform(),
                                'packages':{p:version(p) for p in ['pandas','numpy','scipy','pyarrow','matplotlib','reportlab','pytest','scikit-learn','joblib','threadpoolctl']}},
                   source_lock_sha256=sha256(ROOT/'docs/source_lock.json'),
                   analysis_plan_sha256=sha256(ROOT/'docs/analysis_plan.md'))
    except Exception as exc:
        for name in ['report.html','index.html','brief.pdf','ml_report.html','ml_brief.pdf','summary.json','model_diagnostics.html']:
            (ROOT/'reports'/name).unlink(missing_ok=True)
        (ROOT/'evidence/ml_results.json').unlink(missing_ok=True)
        log.update(status='failed',error=str(exc),elapsed_seconds=round(time.perf_counter()-start,3))
        raise
    finally:
        target.write_text(json.dumps(log,indent=2)+'\n')

if __name__=='__main__':run()
