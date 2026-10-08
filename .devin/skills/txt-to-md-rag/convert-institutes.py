#!/usr/bin/env python3
"""Convert Project Gutenberg calvins-institutes.txt to Markdown.

RAG-oriented conventions:
- YAML front matter with work metadata
- Markdown heading hierarchy (## books/major divisions, ### chapters,
  #### sub-headings) using the book's own TOC titles
- Hard-wrapped lines joined into single-line paragraphs; hyphen-split
  words rejoined without a space
- Footnotes inlined at the point of reference as ` [fn. N: text]`
  (no trailing footnotes section)
- Translator's `_italics_` preserved (native markdown emphasis)
- Verse blocks keep line-per-line layout with hard breaks
- Section numerals (I., II., ...) bolded
- Gutenberg boilerplate/license stripped; source attribution added
"""
import re

SRC = "/Users/noahkiser/workspace/github/kisernl/theology-resources-reformed/calvins-institutes.txt"
OUT = "/Users/noahkiser/workspace/github/kisernl/theology-resources-reformed/calvins-institutes.md"

raw = open(SRC, encoding="utf-8").read().split("\n")

START = next(i for i, l in enumerate(raw) if l.startswith("*** START"))
END = next(i for i, l in enumerate(raw) if l.startswith("*** END"))
FN = next(i for i, l in enumerate(raw) if l.strip() == "FOOTNOTES")

# ---------- locate content regions ----------
def find_line(text, lo, hi):
    return next(i for i in range(lo, hi) if raw[i].strip() == text)

i_contents = find_line("CONTENTS", START, START + 60)
i_advert = find_line("ADVERTISEMENT.", i_contents, i_contents + 250)

# ---------- parse footnote definitions first ----------
defs = {}
num, buf = None, ""
for l in raw[FN + 1 : END]:
    m = re.match(r"^ {1,5}(\d{1,4}) ", l)
    if m:
        if num is not None:
            defs[num] = buf.strip()
        num, buf = m.group(1), l[m.end():]
    elif l.strip():
        buf += " " + l.strip()
if num is not None:
    defs[num] = buf.strip()

# ---------- parse CONTENTS into (indent_level, text) entries ----------
STARTER = re.compile(
    r"^(Advertisement|The Translator|The Author|Dedication|General Syllabus|"
    r"Book |Chapter |Argument\.|The (First|Second|Third|Fourth|Fifth|Sixth|"
    r"Seventh|Eighth|Ninth|Tenth) |Footnotes)"
)
toc = []  # (level, text)
for l in raw[i_contents + 1 : i_advert]:
    if not l.strip():
        continue
    indent = len(l) - len(l.lstrip())
    level = 0 if indent == 0 else (1 if indent <= 3 else 2)
    if STARTER.match(l.strip()):
        toc.append([level, l.strip()])
        if l.strip().startswith("Footnotes"):
            break  # last TOC entry; cover-art notes follow
    else:  # wrapped continuation of previous entry
        toc[-1][1] += " " + l.strip()

toc_iter = iter(toc)

def next_toc():
    return next(toc_iter)[1].rstrip(".")

# ---------- helpers ----------
def join_lines(block_lines):
    """Join hard-wrapped lines; no space after a trailing hyphen."""
    out = ""
    for l in block_lines:
        s = l.strip()
        if out.endswith("‐") or out.endswith("-"):
            out += s
        elif out:
            out += " " + s
        else:
            out = s
    return out

def fnrefs(text):
    """Inline footnotes: (N) -> ' [fn. N: text]'."""
    def repl(m):
        body = defs.get(m.group(1), "")
        return f" [fn. {m.group(1)}: {body}]"
    return re.sub(r"\((\d{1,4})\)", repl, text)

def bold_section(text):
    return re.sub(r"^([IVXLC]{1,6})\. ", r"**\1.** ", text)

# ---------- output ----------
out = []
out += [
    "---",
    'title: "Institutes of the Christian Religion"',
    'author: "John Calvin"',
    'translator: "John Allen"',
    'edition: "Sixth American Edition, Revised and Corrected"',
    "volume: 1",
    'source: "https://www.gutenberg.org/ebooks/45001"',
    "---",
    "",
    "# Institutes of the Christian Religion (Vol. 1 of 2)",
    "",
    "**by John Calvin**",
    "",
    "*Translated from the original Latin, and collated with the author's",
    "last edition in French, by John Allen*",
    "",
    "*Sixth American Edition, Revised and Corrected. In Two Volumes. — Vol. I.*",
    "",
    "*Philadelphia: Presbyterian Board of Publication, 1813*",
    "",
    "> Source text: [Project Gutenberg eBook #45001]"
    "(https://www.gutenberg.org/ebooks/45001) (public domain).",
    "",
    "---",
    "",
    "## Contents",
    "",
]
for level, text in toc:
    if text == "Footnotes":
        continue  # footnotes are inlined; no such section exists
    out.append("  " * level + "- " + text)
out += ["", "---", ""]

# ---------- body ----------
body = raw[i_advert:FN]
blocks, cur = [], []
for l in body:
    if l.strip():
        cur.append(l)
    else:
        if cur:
            blocks.append(cur)
            cur = []
if cur:
    blocks.append(cur)

BOOK_RE = re.compile(r"^BOOK [IVXLC]+\.")
CHAP_RE = re.compile(r"^Chapter [IVXLC]+\.")
CMD_RE = re.compile(r"^The (First|Second|Third|Fourth|Fifth|Sixth|Seventh|"
                    r"Eighth|Ninth|Tenth) Commandment\.")
FRONT = {"ADVERTISEMENT.", "THE TRANSLATOR’S PREFACE.", "DEDICATION.",
         "GENERAL SYLLABUS."}
AUTHOR_PREFACE = "THE AUTHOR’S PREFACE"

for blk in blocks:
    joined = join_lines(blk)
    indented = blk[0][0] in (" ", "\t")

    if not indented and (joined in FRONT or joined.startswith(AUTHOR_PREFACE)):
        out += ["## " + next_toc(), ""]
    elif not indented and BOOK_RE.match(joined):
        out += ["## " + next_toc(), ""]
    elif not indented and joined == "Argument.":
        out += ["### " + next_toc(), ""]
    elif not indented and CHAP_RE.match(joined):
        out += ["### " + next_toc(), ""]
    elif not indented and CMD_RE.match(joined):
        out += ["#### " + next_toc(), ""]
    elif indented:
        if joined.startswith("_"):  # prose quotation / salutation: join
            out += [fnrefs(joined), ""]
        else:  # verse: keep line breaks
            verse = [l.strip() for l in blk]
            for j, v in enumerate(verse):
                out.append(fnrefs(v) + ("  " if j < len(verse) - 1 else ""))
            out.append("")
    else:
        out += [fnrefs(bold_section(joined)), ""]

open(OUT, "w", encoding="utf-8").write("\n".join(out).rstrip() + "\n")
print(f"wrote {OUT}: {len(out)} lines, {len(defs)} footnotes inlined, "
      f"{len(toc)} toc entries")
