#!/usr/bin/env bash
# Rebuild every Airlume PDF from its Markdown source.
# Usage:  bash docs/build.sh        (run from the repository root)
set -euo pipefail
cd "$(dirname "$0")"

# If the lmodern LaTeX package is missing (some minimal TeX installs), use the
# stub in tex-fallback/. It is unused because fonts come from fontspec.
if ! kpsewhich lmodern.sty >/dev/null 2>&1; then
  export TEXINPUTS="$(pwd)/tex-fallback//:${TEXINPUTS:-}"
fi

COMMON=(--pdf-engine=xelatex
  -V mainfont="Bitstream Charter" -V sansfont="DejaVu Sans" -V monofont="DejaVu Sans Mono"
  -V fontsize=11pt -V linkcolor=accent -V urlcolor=accent -V colorlinks=true)

echo "Building the complete project plan..."
(cd plan && pandoc plan.md -o ../pdf/Airlume_Complete_Project_Plan.pdf \
  --include-in-header=header.tex --toc --toc-depth=2 --number-sections \
  -V geometry:"a4paper,margin=2.2cm,top=2.5cm,bottom=2.3cm" "${COMMON[@]}")

echo "Building the v1 proposal (archived)..."
(cd proposal-v1 && pandoc proposal.md -o ../pdf/Airlume_Project_Proposal_v1.pdf \
  --include-in-header=header.tex --toc --toc-depth=2 --number-sections \
  -V geometry:"a4paper,margin=2.4cm,top=2.6cm,bottom=2.4cm" "${COMMON[@]}")

echo "Done:"; ls -la pdf/
