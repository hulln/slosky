# Paper Workspace

This folder contains the manuscript workspace and the official JTDH template files.

## What to edit

For the actual paper draft, edit:

- `jtdh-manuscript-english.tex`
- files in `sections/`

Keep these original template files unchanged:

- `jtdh-template-english.tex`
- `jtdh-template-slovene.tex`
- `jtdh.sty`

## Structure

- `jtdh-manuscript-english.tex`: working English manuscript based on the official template
- `sections/`: manuscript section files
- `references.bib`: bibliography
- `img/`: template image assets

## Section levels

The JTDH template is article-based. Use:

- `\section`
- `\subsection`
- `\subsubsection`

Do not use `\chapter`.

## Compilation

The official template says it should be compiled with LuaLaTeX or XeLaTeX, with `biber` for the bibliography.

This environment currently does not have:

- `xelatex`
- `lualatex`
- `latexmk`
- `biber`

So the manuscript can be edited here, but it cannot currently be compiled here.

## Method claims to keep aligned

Keep the manuscript aligned with:

- `docs/methodology-section-draft.md`
- `docs/validation-results.md`
- `docs/quality-assurance.md`
- `docs/detector-choice.md`

Keep claims conservative:

- currently recoverable public posts
- discovered Slovene-linked accounts
- deleted posts excluded
