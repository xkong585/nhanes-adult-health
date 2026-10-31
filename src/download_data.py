"""Download official files; all cached/downloaded bytes must match the source lock."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import urllib.request
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def download():
    lock = json.loads((ROOT / 'docs/source_lock.json').read_text())
    out = ROOT / 'data/raw'
    out.mkdir(parents=True, exist_ok=True)
    old_path = ROOT / 'evidence/source_manifest.csv'
    old = pd.read_csv(old_path).set_index('file').to_dict('index') if old_path.exists() else {}
    rows = []
    for item in lock:
        path = out / item['file']
        if not path.exists():
            request = urllib.request.Request(item['url'], headers={'User-Agent': 'NHANESPortfolio/1.0'})
            with urllib.request.urlopen(request, timeout=120) as response:
                content = response.read()
            if hashlib.sha256(content).hexdigest() != item['sha256']:
                raise ValueError(f"Source changed for {path.name}; investigate before updating source_lock.json")
            temp = path.with_suffix(path.suffix + '.tmp')
            temp.write_bytes(content)
            os.replace(temp, path)
            obtained = datetime.now(timezone.utc).isoformat()
        else:
            obtained = old.get(item['file'], {}).get('downloaded_at_utc', item['first_obtained_utc'])
        if sha256(path) != item['sha256']:
            raise ValueError(f'Corrupt or changed cached source: {path.name}')
        if path.suffix == '.xpt' and not path.read_bytes().startswith(b'HEADER RECORD'):
            raise ValueError(f'Not SAS XPT: {path.name}')
        rows.append({**item, 'downloaded_at_utc': obtained, 'bytes': path.stat().st_size})
    pd.DataFrame(rows).to_csv(old_path, index=False)
    return rows

if __name__ == '__main__':
    download()
