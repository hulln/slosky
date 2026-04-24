# Paper Directory

This directory contains the JTDH manuscript sources and local paper material.

Top level:

- `jtdh-manuscript-english.tex`: main non-anonymous entry file
- `jtdh-manuscript-english-anonymous.tex`: anonymous entry file
- `jtdh.sty`: active local style file used by the manuscript

Source folders:

- `sections/front/`: abstract and front matter inputs
- `sections/body/`: main section inputs
- `bibliography/`: bibliography source
- `img/figures/`: paper figures
- `img/assets/`: template assets such as ORCID, ROR, and licence graphics
- `records/`: submission notes and records
- `submitted/`: tracked copies of the submitted PDFs

Supporting files:

- `jtdh-template-*.tex`: reference template files

Local-only material:

- `build/`: LaTeX build output, ignored by Git
- `local/`: local reading copies and other non-source paper material, ignored by Git

Compile with `latexmk` from this directory.
