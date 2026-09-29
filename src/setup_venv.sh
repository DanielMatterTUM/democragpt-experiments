#!/usr/bin/env bash
# Rebuild the analysis venv (matplotlib+numpy for figures, scipy for the
# extended stats). /tmp is wiped on gateway restarts, so this must be re-runnable.
set -euo pipefail
VENV=/tmp/venv-an
if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet numpy matplotlib scipy
"$VENV/bin/python" - <<'PY'
import matplotlib, numpy, scipy
print("mpl", matplotlib.__version__, "np", numpy.__version__, "scipy", scipy.__version__)
PY