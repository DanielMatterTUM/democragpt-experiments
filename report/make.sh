#!/usr/bin/env bash
# Build the LaTeX report: xelatex -> biber -> xelatex -> xelatex.
#
# TinyTeX lives in $HOME/.TinyTeX and is NOT on PATH by default. The OpenType
# fonts shipped with TeX Live are also not visible to fontconfig, so fontspec
# cannot load them by name until ~/.config/fontconfig/fonts.conf points at
# $HOME/.TinyTeX/texmf-dist/fonts/{opentype,truetype} and fc-cache has run.
# Without that, xelatex reports "Font ... not loadable: Metric (TFM) file or
# installed font not found" and writes a BLANK one-page PDF that still exits 0.
set -euo pipefail

export PATH="$HOME/.TinyTeX/bin/x86_64-linux:$PATH"

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEXDIR="$REPO/report"
MAIN="${1:-report}"

cd "$TEXDIR"

echo "== 1/4 xelatex =="
xelatex -interaction=nonstopmode -halt-on-error "$MAIN.tex" >/dev/null

echo "== 2/4 biber =="
if [ -f "$MAIN.bcf" ]; then
  biber "$MAIN" >/dev/null
else
  echo "   no .bcf -- skipping biber"
fi

echo "== 3/4 xelatex =="
xelatex -interaction=nonstopmode -halt-on-error "$MAIN.tex" >/dev/null

echo "== 4/4 xelatex =="
xelatex -interaction=nonstopmode "$MAIN.tex" >/dev/null

PDF="$TEXDIR/$MAIN.pdf"
if [ ! -s "$PDF" ]; then
  echo "FAIL: $PDF missing or empty" >&2
  exit 1
fi

pages=$(pdfinfo "$PDF" | awk '/^Pages:/ {print $2}')
size=$(stat -c%s "$PDF")
echo "OK  $PDF  pages=$pages  bytes=$size"

# A one-page PDF of a few hundred bytes means the content did not render
# (usually a font failure). Guard against silently shipping a blank report.
if [ "$pages" = "1" ] && [ "$size" -lt 20000 ]; then
  echo "WARN: 1 page and only ${size} bytes -- suspiciously empty, check the log" >&2
  grep -c "not loadable" "$MAIN.log" >/dev/null 2>&1 &&
    echo "      font errors found in $MAIN.log" >&2
  exit 2
fi

echo "log: $TEXDIR/$MAIN.log"