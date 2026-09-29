#!/usr/bin/env bash
export PATH="$HOME/.TinyTeX/bin/x86_64-linux:$PATH"
cd /home/hermes/projects/democragpt-experiments/report
echo "=== errors / warnings in log ==="
grep -nE "^! |Extra alignment|Undefined control|Citation .* undefined|not found|not loadable|Overfull \\\\hbox \([0-9]{2,}" report.log | head -20
echo
echo "=== pdf info ==="
pdfinfo report.pdf | grep -E "Pages|Page size|Title"
echo
echo "=== embedded images (expect 11) ==="
pdfimages -list report.pdf | tail -n +3 | wc -l
echo
echo "=== citations resolved? (expect no 'undefined') ==="
grep -c "Citation.*undefined" report.log || true
echo
echo "=== text sample ==="
pdftotext report.pdf - | sed -n '1,40p'