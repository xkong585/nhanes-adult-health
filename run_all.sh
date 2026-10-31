#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3}"
export MPLCONFIGDIR="$PWD/.mplconfig"
mkdir -p evidence data/processed
"$PYTHON" src/run_pipeline.py
