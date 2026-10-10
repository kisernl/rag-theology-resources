#!/usr/bin/env python3
"""Regenerate CATALOG.md — a human-readable index of docs/ by genre.

Reads each doc's frontmatter and emits a table per genre with
Title | Author | Tradition | Covers (commentaries). Lives at the repo
root, outside docs/, so it is never ingested as corpus content.

Usage: python3 tools/build_catalog.py
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOC = REPO / 'docs'
OUT = REPO / 'CATALOG.md'

# display order for genre sections
GENRES = ['commentary', 'sermon', 'systematic', 'treatise', 'catechism',
          'apologetics', 'devotional', 'biography', 'history', 'reference']

TITLES = {
    'commentary': 'Commentaries',
    'sermon': 'Sermons & Sermon Collections',
    'systematic': 'Systematic Theologies',
    'treatise': 'Treatises',
    'catechism': 'Catechisms',
    'apologetics': 'Apologetics',
    'devotional': 'Devotional Works',
    'biography': 'Biographies & Confessions',
    'history': 'Histories',
    'reference': 'Reference Works',
}


def frontmatter(path):
    fm = {}
    text = path.read_text()
    if not text.startswith('---'):
        return fm
    block = text.split('---', 2)[1]
    for line in block.splitlines():
        m = re.match(r'^(\w+):\s*(.*)$', line)
        if m:
            fm[m.group(1)] = m.group(2).strip().strip('"')
    return fm


def main():
    rows = {g: [] for g in GENRES}
    for p in sorted(DOC.glob('*.md')):
        fm = frontmatter(p)
        g = fm.get('genre', 'other')
        rows.setdefault(g, []).append((fm, p.name))

    out = ['# Corpus Catalog',
           '',
           'All works in `docs/`, grouped by `genre`. Regenerate with',
           '`python3 tools/build_catalog.py`.',
           '',
           f'**{sum(len(v) for v in rows.values())} works.**', '']
    for g in GENRES:
        if not rows.get(g):
            continue
        out += [f'## {TITLES.get(g, g.title())} ({len(rows[g])})', '']
        has_covers = any('covers' in fm for fm, _ in rows[g])
        if has_covers:
            out.append('| Title | Author | Tradition | Covers |')
            out.append('|---|---|---|---|')
        else:
            out.append('| Title | Author | Tradition |')
            out.append('|---|---|---|')
        for fm, name in sorted(rows[g], key=lambda r: (r[0].get('author', ''),
                                                     r[0].get('title', ''))):
            t = f"[{fm.get('title', '?')}](docs/{name})"
            a = fm.get('author', '?')
            tr = fm.get('tradition', '')
            if has_covers:
                cov = fm.get('covers', '')
                cov = cov.replace('", "', ', ').strip('[]"')
                out.append(f'| {t} | {a} | {tr} | {cov} |')
            else:
                out.append(f'| {t} | {a} | {tr} |')
        out.append('')
    other = [(fm, n) for g, v in rows.items() if g not in GENRES
             for fm, n in v]
    if other:
        out += ['## Other', '', '| Title | Author | Tradition |',
                '|---|---|---|']
        for fm, name in sorted(other, key=lambda r: r[0].get('author', '')):
            out.append(f"| [{fm.get('title','?')}](docs/{name})"
                       f" | {fm.get('author','?')}"
                       f" | {fm.get('tradition','')} |")
        out.append('')
    OUT.write_text('\n'.join(out))
    print(f'{OUT.name}: {sum(len(v) for v in rows.values())} works, '
          + ', '.join(f'{g} {len(rows[g])}' for g in GENRES
                      if rows.get(g)))


if __name__ == '__main__':
    main()
