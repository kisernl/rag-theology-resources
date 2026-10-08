---
name: txt-to-md-rag
description: Convert plain-text source works (e.g. Project Gutenberg .txt files) in this repo to RAG-optimized Markdown, using the conventions established for docs/calvin-institutes.md
argument-hint: "<source .txt file>"
allowed-tools:
  - read
  - write
  - edit
  - exec
  - grep
  - glob
---

# Text → Markdown conversion for the RAG pipeline

This repo is a content store for a RAG pipeline / vector DB. Whenever a
`.txt` file here (typically a Project Gutenberg export of a theological
work) needs a Markdown version, apply ALL of the following conventions so
that header-aware splitters and contextual chunking work well.

A working converter for the Gutenberg-45001 format (used for
`calvins-institutes.txt`) is saved next to this file as
`convert-institutes.py`. New sources will differ in structure — copy and
adapt it rather than converting by hand, and always verify the output
against the checklist at the bottom.

## Output conventions

1. **File**: `docs/<author>-<title-slug>.md` — author surname first, no
   possessives (`calvin-institutes`, `augustine-confessions`,
   `allestree-government-of-the-tongue`, `anselm-basic-writings`).
   Sources live in `sources/` under the same slug (`sources/<author>-
   <title-slug>.txt`); rename misplaced/misspelled source files to match.
   Keep the source file — it is needed for re-conversion and verification.

2. **YAML front matter** at the very top:

   ```yaml
   ---
   title: "..."
   author: "..."
   translator: "..."        # if applicable
   edition: "..."           # if applicable
   source: "<gutenberg URL or other origin>"
   ---
   ```

3. **Title block**: `#` title, author line, edition/imprint lines in
   italics, then a `>` blockquote source attribution. Gutenberg license
   boilerplate and `[Cover Art]`/transcriber notes are dropped.

4. **Contents**: reproduce the book's TOC as a nested bullet list under
   `## Contents`. Drop entries for sections that won't exist (e.g.
   "Footnotes" — see rule 8).

5. **Heading hierarchy** — use the book's own TOC wording (title case),
   stripping the trailing period:
   - `##` major divisions (books, prefaces, dedications, appendices)
   - `###` chapters / arguments
   - `####` numbered sub-sections (e.g. the Ten Commandments)

6. **Paragraphs**: join hard-wrapped lines into one line per paragraph.
   If a line ends with a hyphen (`-` or `‐` U+2010), join the next line
   WITHOUT a space (the word was split across the break). Otherwise join
   with a single space.

7. **Inline emphasis**: Gutenberg `_underscores_` are already valid
   markdown italics — preserve them.

8. **Footnotes — INLINE, never a trailing section**: replace each
   in-text marker `(N)` with ` [fn. N: <footnote text>]` at the point of
   reference. Parse the footnote list first, then substitute. This keeps
   citations inside the same chunk as the text they support. The `fn.`
   prefix distinguishes them from the author's/translator's own
   `[bracketed]` interpolations.

9. **Section numbers**: paragraph-leading enumerals (e.g. `II.`, `III.`,
   or `1.`/`2.` depending on the edition) are the book's section markers —
   bold them (`**II.**`). They map to standard citations
   (Book.Chapter.Section) and are the preferred chunk boundaries.

10. **Verse/poetry blocks** (indented lines that are NOT wrapped in
    `_..._`): keep line-per-line with two trailing spaces for hard breaks.
    Indented prose quotations ARE joined into a normal paragraph — never
    emit raw 4-space indents (they render as code blocks).

11. **Typography**: preserve Unicode as-is (curly quotes, `‐`, æ/œ,
    Greek). Do not silently "fix" apparent source typos — stay faithful.

## Verification checklist (always run)

- Every footnote marker got inlined: zero remaining `\(\d+\)` refs; count
  of `[fn. N:` equals count of parsed definitions; numbering sequential.
- No stray `](` that could form a link (excluding intentional links).
- Heading text matches TOC entries, in order, none skipped.
- Word count of converted body ≈ source body (± markup tokens) — no lost
  content.
- Spot-check: first paragraph of a chapter, a verse block, the longest
  footnote, hyphen-joined words.
