#!/usr/bin/env bash
# Compile le rapport en PDF (XeLaTeX) et en Word (.docx) à partir de la même source Markdown.
# Usage : ./build.sh [fichier.md]   (par défaut rapport.md)
# Prérequis : pandoc, XeLaTeX (texlive-xetex, texlive-latex-extra, texlive-lang-french), polices IBM Plex.
set -euo pipefail
cd "$(dirname "$0")"
SRC="${1:-rapport.md}"
OUT="${SRC%.md}"

pandoc "$SRC" -o "$OUT.pdf" \
  --pdf-engine=xelatex --listings \
  -H latex/preamble.tex -B latex/cover.tex \
  -V documentclass=report -V classoption=11pt -V papersize=a4 \
  -V geometry:"top=2.6cm,bottom=2.6cm,left=2.6cm,right=2.6cm" \
  --top-level-division=chapter --number-sections

echo "PDF : $OUT.pdf"
