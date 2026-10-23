#!/usr/bin/env bash
# Compile le rapport en PDF (XeLaTeX) et en Word (.docx) à partir des mêmes chapitres Markdown.
# Usage : ./build.sh
# Prérequis : pandoc, XeLaTeX (texlive-xetex, texlive-latex-extra, texlive-lang-french), python-docx.
set -euo pipefail
cd "$(dirname "$0")"
SRC=(chapitres/*.md)
OUT=rapport

pandoc "${SRC[@]}" -o "$OUT.pdf" \
  --pdf-engine=xelatex --listings --lua-filter latex/crossref.lua \
  -H latex/preamble.tex -B latex/cover.tex \
  -V documentclass=report -V classoption=11pt -V papersize=a4 \
  -V geometry:"top=2.6cm,bottom=2.6cm,left=2.6cm,right=2.6cm" \
  --top-level-division=chapter --number-sections
echo "PDF  : $OUT.pdf"

python3 docx/docx_tools.py reference docx/reference.docx
pandoc "${SRC[@]}" -o "$OUT.docx" \
  --lua-filter latex/crossref.lua --reference-doc docx/reference.docx \
  --top-level-division=chapter --number-sections
python3 docx/docx_tools.py finish "$OUT.docx"
echo "Word : $OUT.docx"
