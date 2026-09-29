#!/usr/bin/env bash
# Final state check. Everything is committed; only the push is outstanding.
cd /home/hermes/projects/democragpt-experiments

echo "=== git ==="
echo "HEAD        : $(git log --oneline -1)"
echo "uncommitted : $(git status --short | wc -l)"
echo "ahead       : $(git rev-list --count origin/main..HEAD 2>/dev/null || echo '?') commit(s) to push"

echo
echo "=== deliverable: report/report.pdf ==="
pdfinfo report/report.pdf | grep -E "Title|Pages|Page size"
echo "figures embedded: $(pdfimages -list report/report.pdf | tail -n +3 | wc -l)"
echo "citations undefined: $(grep -c 'Citation.*undefined' report/report.log || true)"
echo "overfull >20pt     : $(grep -cE 'Overfull \\hbox \([0-9]{2,}' report/report.log || true)"

echo
echo "=== pipeline scripts ($(ls src/*.py src/*.sh | wc -l)) ==="
ls src/*.py src/*.sh | sed 's|src/|  |'

echo
echo "=== figures ==="
ls results/figures/*.pdf | sed 's|results/figures/|  |'

echo
echo "=== samples + their predictions coverage ==="
python3 src/verify_samples.py