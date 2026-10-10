#!/usr/bin/env python3
"""Generic CCEL plain-text -> RAG markdown converter.

Handles the shared CCEL ThML-rendered format: ___ separators, [N] footnote
clusters at page bottoms, "Indexes"/"References" tails, wrapped paragraphs,
hyphen line-breaks. Heading structure is detected from marker lines
(CHAPTER/BOOK/PART/SECTION/LECTURE/SERMON/...) plus optional following title
blocks. Per-file tweaks live in OVERRIDES below.

Usage:
    python3 tools/convert_ccel.py                  # all unconverted sources
    python3 tools/convert_ccel.py FILE [FILE...]   # specific sources
    python3 tools/convert_ccel.py --report         # heading map only
"""
import argparse
import re
import sys
import unicodedata
from html import unescape
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC_DIR = REPO / 'sources'
DOC_DIR = REPO / 'docs'

SEP = re.compile(r'^\s*_{10,}\s*$')
END_MARKERS = ('Indexes', 'Index of Scripture References', 'INDEXES',
               'INDEX.', 'INDEX', 'Acknowledgements', 'Acknowledgments',
               'This document is from the Christian Classics')

# ---- structural vocabulary --------------------------------------------------
# (keyword -> level) for "MARKER N[. Title]" lines; '#' handled specially
LEVEL2 = {'PART': 2, 'BOOK': 2, 'SECTION': 2, 'TREATISE': 2, 'TRACTATE': 2,
          'DIVISION': 2, 'VOLUME': 2}
LEVEL3 = {'CHAPTER': 3, 'LECTURE': 3, 'SERMON': 3, 'DISCOURSE': 3,
          'QUESTION': 3, 'LETTER': 3, 'HOMILY': 3, 'ORATION': 3,
          'DISSERTATION': 3, 'REPLY': 3, 'PSALM': 3}
LEVEL4 = {'ARTICLE': 4, 'POINT': 4, 'OBJECTION': 4}
MARKERS = dict(LEVEL2, **LEVEL3, **LEVEL4)

# standalone one-word (or short) structural blocks -> level-2 headings
LONE = {'PREFACE', 'INTRODUCTION', 'APPENDIX', 'DEDICATION', 'CONCLUSION',
        'PROLOGUE', 'EPILOGUE', 'ADVERTISEMENT', 'POSTSCRIPT', 'MEMOIR',
        'GENERAL PREFACE', 'EDITOR\'S PREFACE', 'PUBLISHER\'S PREFACE',
        'PREFATORY NOTE', 'PREFATORY REMARKS', 'PREFACE TO THE READER',
        'TO THE READER', 'INTRODUCTORY NOTE', 'INTRODUCTORY ESSAY',
        'THE INTRODUCTION', 'THE CONCLUSION'}

# paragraph-leading markers -> bolded
BOLD_MARK = re.compile(
    r'^((?:X|IX|IV|V?I{0,3}|XI{0,3})\.'
    r'|(?:First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth'
    r'|Firstly|Secondly|Thirdly|Fourthly|Fifthly|Sixthly|Seventhly|Eighthly'
    r'|Ninthly|Tenthly|Lastly|Finally)\.'
    r'|(?:Use|Quest|Object|Ans|Case|Inference|Observ|Obs|Doct|Note|Remark'
    r'|Argument|Proof|Corollary|Rule|Direction|Exhortation|Application'
    r'|Question|Answer|Caution|Instance)\.?(?:\s*\d+\.)?'
    r'|\(\d{1,3}\)'
    r'|\d{1,3}\.)'
    r'\s+(.*)$')

# scholastic apparatus labels (Aquinas et al.)
SCHOL = re.compile(
    r'^\s*((?:Objection|Reply to Objection|Answer to Objection|Answer|Question'
    r'|Reply)\s+\d+[:.]?'
    r'|(?:On the contrary|I answer that|Sed contra|Respondeo dicendum'
    r'|Reply to the [A-Za-z]+|To the [A-Za-z]+,)[:,.]?)\s*')

SMALL = {'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'in', 'nor', 'of',
         'on', 'or', 'the', 'to', 'up', 'with', 'from', 'into', 'unto', 'upon'}

# ---- per-file overrides -----------------------------------------------------
# 'level': {keyword: level} added/overriding MARKERS
# 'lone': extra standalone heading words; 'title_max': max chars of a title
# block that follows a bare marker line (default 150)
# 'head_res': [(regex, level)] — evaluated on the block's first line before
#             the generic caps/marker rules
OVERRIDES = {
    'aquinas-summa-theologica.txt': {
        'drop_markers': ['OBJECTION'],
        'head_res': [
            (r'^\s*(FIRST|SECOND|THIRD|SUPPLEMENT|APPENDIX)\b.*\bPART\b', 2),
            (r'^\s*TREATISE ON\b', 3),
            (r'^\s*.+\((?:ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN'
             r'|ELEVEN|TWELVE|THIRTEEN|FOURTEEN|FIFTEEN|\d+)\s+ARTICLES?\)', 4),
            (r'^\s{4,}(?:Whether|Of|How|Concerning)\b.*\?\s*$', 5),
        ],
        'title_max': 200,
    },
    'watson-body-of-divinity.txt': {
        'head_res': [(r'^\s*Q-[0-9IVXLCivxlc]+\s*:', 2)],
        'bracket_enum': True,
    },
    'watson-lord-s-prayer.txt': {
        'head_res': [(r'^The (Preface to|(?:First|Second|Third|Fourth|Fifth'
                      r'|Sixth) Petition in) the Lord\'s Prayer\b', 2)],
        'bracket_enum': True,
    },
    'watson-ten-commandments.txt': {
        'head_res': [(r'^\d+\.\s+[A-Z]', 2),
                     (r'^\s{0,3}\d+\.\d+\s+', 3)],
        'bracket_enum': True,
    },
    'watson-beatitudes-an-exposition-of-matthew-5-1-12.txt': {
        'head_res': [(r'^\d+\.\s+[A-Z]', 2)],
        'bracket_enum': True,
    },
    'chesterton-heretics.txt': {
        'head_res': [(r'^\s{0,4}(?:[IVX]{1,6})\.\s+\S', 2)],
    },
    'forsyth-work-of-christ.txt': {
        'head_res': [(r'^(?:[IVX]{1,6})\.\s+\S', 2)],
    },
    'harnack-monasticism-its-ideals-and-history-and-the-confessions-of-st-augustine.txt': {
        'head_res': [(r'^\s*[IVX]+\.\s*$', 2)],
    },
    'bushnell-christ-and-his-salvation-in-sermons-variously-related-thereto.txt': {
        'head_res': [(r'^\s*[IVX]+\.\s*$', 2)],
    },
    'upham-felon-s-maxims-of-the-saints.txt': {
        'head_res': [(r'^\s*ARTICLE\s+[A-Z][A-Z0-9\- ]*$', 2)],
    },
    'owen-eshcol-a-cluster-of-the-fruit-of-canaan.txt': {
        'head_res': [(r'^\s*Rules?\s+(?:of walking|to be observed)\b', 2),
                     (r'^\s*Rule\s+[0-9IVXLCivxlc]+\.', 3)],
    },
    'owen-gospel-grounds-and-evidences-of-the-faith-of-god-s-elect.txt': {
        'head_res': [(r'^\s*[IVX]+\.\s*$', 2)],
    },
    'owen-truth-and-innocence-vindicated.txt': {
        'head_res': [(r'^Review of\b', 2)],
    },
    'owen-review-of-the-annotations-of-hugo-grotius.txt': {
        'head_res': [(r'^\s*A (?:review|second consideration)\b', 2)],
    },
    'flavel-christ-altogether-lovely.txt': {
        'head_res': [(r'^\s*DOCTRINE\b', 3)],
    },
    'bullinger-commentary-on-revelation.txt': {
        'caps_level': 3,
        'lone': ['INTRODUCTORY'],
    },
    'calvin-commentary-on-matthew-mark-luke-volume-1.txt': {
        'caps_level': 2,
        'body_sep': 3,
        'head_res': [(r'^\s*(?i:matthew|mark|luke|john)\s+\d+:\d+'
                      r'(?:\s*-\s*\d+)?\s*\.?\s*$', 3)],
    },
    'calvin-commentary-on-matthew-mark-luke-volume-2.txt': {
        'caps_level': 2,
        'body_sep': 3,
        'head_res': [(r'^\s*(Matthew|Mark|Luke|John)\s+\d+:\d+'
                      r'(?:\s*-\s*\d+)?\s*\.?\s*$', 3)],
    },
    'calvin-commentary-on-matthew-mark-luke-volume-3.txt': {
        'caps_level': 2,
        'body_sep': 3,
        'head_res': [(r'^\s*(?i:matthew|mark|luke|john)\s+\d+:\d+'
                      r'(?:\s*-\s*\d+)?\s*\.?\s*$', 3)],
    },
    'calvin-harmony-of-the-law-volume-1.txt': {
        'caps_level': 3,
        'body_sep': 2,
        'head_res': [(r'^\s*(?:EXODUS|LEVITICUS|NUMBERS|DEUTERONOMY|GENESIS)'
                      r'\s+\d+\s*$', 2)],
    },
    'calvin-harmony-of-the-law-volume-2.txt': {
        'caps_level': 3,
        'body_sep': 2,
        'head_res': [(r'^\s*(?i:exodus|leviticus|numbers|deuteronomy'
                      r'|genesis)\s+\d+:\d+(?:[-,]\s*\d+)*\s*$', 3),
                     (r'^\s*(?i:exodus|leviticus|numbers|deuteronomy'
                      r'|genesis)\s+\d+\s*$', 2)],
    },
    'calvin-harmony-of-the-law-volume-3.txt': {
        'caps_level': 3,
        'body_sep': 2,
        'head_res': [(r'^\s*(?:EXODUS|LEVITICUS|NUMBERS|DEUTERONOMY|GENESIS)'
                      r'\s+\d+\s*$', 2)],
    },
    'calvin-harmony-of-the-law-volume-4.txt': {
        'caps_level': 3,
        'body_sep': 2,
        'head_res': [(r'^\s*(?i:exodus|leviticus|numbers|deuteronomy'
                      r'|genesis)\s+\d+:\d+(?:[-,]\s*\d+)*\s*$', 3),
                     (r'^\s*(?i:exodus|leviticus|numbers|deuteronomy'
                      r'|genesis)\s+\d+\s*$', 2)],
    },
    'ryle-expository-thoughts-on-matthew.txt': {
        'head_res': [(r'^\s*Matthew\s+\d+:\d+(?:\s*-\s*\d+)?\s*$', 3),
                     (r'^\s*Matthew\s+\d+\s*$', 2)],
    },
    'schmid-doctrinal-theology.txt': {
        'loose_defs': True,
        'sec_res': r'^\s*§\s*\d+',
        'level': {'CHAPTER': 2},
        'head_res': [(r'^\s*§\s*\d+', 3)],
    },
    'edwards-works-of-jonathan-edwards-volume-one.txt': {
        'bracket_enum': True,
    },
    'edwards-works-of-jonathan-edwards-volume-two.txt': {
        'bracket_enum': True,
    },
    'edwards-select-sermons.txt': {
        'bracket_enum': True,
    },
    # gen-COM batch: Expositor's Bible vols and others whose sections are
    # marked by a bare roman numeral line (title block follows)
    'dods-expositor-s-bible-the-book-of-genesis.txt': {
        'head_res': [(r'^\s*[IVXL]+\.\s*$', 2)],
    },
    'dods-expositor-s-bible-the-gospel-of-st-john-volume-ii.txt': {
        'head_res': [(r'^\s*[IVXL]+\.\s*$', 2)],
    },
    'ball-expositor-s-bible-the-prophecies-of-jeremiah-volume-i.txt': {
        'head_res': [(r'^\s*[IVXL]+\.\s*$', 2)],
    },
    'bennett-expositor-s-bible-the-book-of-jeremiah-volume-ii.txt': {
        # INDEX sits between preface and body — skip it, don't end on it
        'front_index': True,
        'head_res': [(r'^\s*[IVXL]+\.\s*$', 2)],
    },
    'gibson-expositor-s-bible-the-gospel-of-st-matthew.txt': {
        'head_res': [(r'^\s*[IVXL]+\.\s*$', 2)],
    },
    'jowett-epistles-of-st-peter.txt': {
        'head_res': [(r'^\s*[IVXL]+\.\s*[\d,.\s\u2013-]+\.?\s*$', 3)],
    },
    'watson_ra-expositor-s-bible-judges-and-ruth.txt': {
        'head_res': [(r'^\s*[IVXL]+\.\s*$', 2)],
    },
    'watson_ra-expositor-s-bible-the-book-of-numbers.txt': {
        # bare roman numeral section markers (II, III, …) without a period
        'head_res': [(r'^\s*[IVXL]+\.?\s*$', 2)],
    },
    'mcgarvey-commentary-on-acts-of-the-apostles.txt': {
        # section markers are centered "Acts I", "Acts II", … lines
        'head_res': [(r'^\s*Acts\s+[IVXLC]+\s*$', 3)],
    },
    'maclaren-expositor-s-bible-colossians-and-philemon.txt': {
        'head_res': [(r'^\s*[IVXL]+\.\s*$', 2)],
    },
    'tischendorf-origin-of-the-four-gospels.txt': {
        'head_res': [(r'^\s*[IVXL]+\.\s*$', 2)],
    },
    # Maclaren Expositions: sermon titles are standalone caps lines
    'maclaren-expositions-of-holy-scripture-deuteronomy-joshua-judges-ruth-and-first-book-of-samuel-second-samuel-first-kings-and-second-kings-chapters.txt': {
        'caps_level': 2,
    },
    'maclaren-expositions-of-holy-scripture-ezekiel-daniel-and-the-minor-prophets-and-matthew-chaps-i-to-viii.txt': {
        'caps_level': 2,
    },
    'maclaren-expositions-of-holy-scripture-genesis-exodus-leviticus-and-numbers.txt': {
        'caps_level': 2,
    },
    'maclaren-expositions-of-holy-scripture-isaiah-and-jeremiah.txt': {
        'caps_level': 2,
    },
    'maclaren-expositions-of-holy-scripture-mark.txt': {
        'caps_level': 2,
    },
    'maclaren-expositions-of-holy-scripture-matthew-ix-to-xviii.txt': {
        'caps_level': 2,
    },
    'maclaren-expositions-of-holy-scripture-st-john-ch-i-to-xiv.txt': {
        'caps_level': 2,
    },
    'maclaren-expositions-of-holy-scripture-st-john-chs-xv-to-xxi.txt': {
        'caps_level': 2,
    },
    'maclaren-expositions-of-holy-scripture-the-acts.txt': {
        'caps_level': 2,
    },
    'maclaren-expositions-of-the-holy-scriptures-second-kings-from-chap-viii-and-chronicles-ezra-and-nehemiah-esther-job-proverbs-and-ecclesiastes.txt': {
        'caps_level': 2,
    },
}


def titlecase(s):
    out, first = [], True
    for w in s.split():
        if not any(c.isalpha() for c in w):
            out.append(w)
            continue
        lw = w.lower()
        out.append(lw if (not first and lw in small())
                    else lw[:1].upper() + lw[1:])
        first = False
    return ' '.join(out)


def small():
    return SMALL


def fix_mojibake(s):
    # repair UTF-8-as-Latin1 artifacts when there are few of them
    if 'Ã' not in s:
        return s
    try:
        fixed = s.encode('latin-1', 'strict').decode('utf-8', 'strict')
        return fixed if fixed.count('') == 0 else s
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def parse_header(raw):
    meta = {}
    for l in raw[:40]:
        m = re.match(r'^\s*(Title|Creator\(s\)|Print Basis|Rights|LC Call no)'
                     r'\s*:\s*(.*)$', l)
        if m:
            meta[m.group(1)] = m.group(2).strip()
    return meta


def clean_author(creator, fname):
    if creator:
        c = re.sub(r'\(.*?\)', '', creator).strip()
        c = c.split(';')[0].split(',')[::-1]
        c = ' '.join(x.strip() for x in c if x.strip())
        if c:
            return re.sub(r'\bD\.?D\.?\b', '', c).strip(' ,.')
    return fname.split('-', 1)[0].title()


def blocks_of(raw):
    elems, cur = [], []
    for l in raw:
        if SEP.match(l):
            if cur:
                elems.append(('block', cur))
                cur = []
            elems.append(('sep',))
            continue
        if not l.strip():
            if cur:
                elems.append(('block', cur))
                cur = []
            continue
        cur.append(l)
    if cur:
        elems.append(('block', cur))
    return elems


def joined(lines):
    out = ''
    for l in lines:
        s = l.strip()
        if out and out.endswith('-') and not out.endswith(' -') \
                and out[-2:-1].isalpha():
            out = out[:-1] + s
        else:
            out = (out + ' ' + s).strip()
    return re.sub(r'\s+', ' ', out)


def parse_footnotes(elems, upto, loose=False):
    """Blocks that lead with [N] and follow a ___ or another def block.

    defs maps n -> deque of (elem_index, text) in file order. Numbering may
    restart per chapter, so refs bind to the nearest *following* def.
    loose=True treats every [N]-leading block as a def (works like Schmid's
    where notes are interleaved paragraphs, not page-bottom clusters)."""
    from collections import deque
    defs, def_blocks = {}, set()
    leads = [None] * len(elems)
    for i, (k, *rest) in enumerate(elems):
        if k == 'block':
            m = re.match(r'^\s*\[(\d+)\]\s+\S', rest[0][0])
            if m:
                leads[i] = int(m.group(1))

    def next_block(idx):
        j = idx + 1
        while j < len(elems) and elems[j][0] == 'sep':
            j += 1
        return j

    prev_i, cluster_open = None, False
    for i, (k, *rest) in enumerate(elems):
        if i >= upto:
            break
        if k == 'sep':
            cluster_open = True
            continue
        if leads[i] is None:
            cluster_open = False
            prev_i = i
            continue
        nb = next_block(i)
        is_def = loose or cluster_open or prev_i in def_blocks \
            or (nb < upto and leads[nb] is not None)
        if is_def:
            def_blocks.add(i)
            defs.setdefault(leads[i], deque()).append(
                (i, re.sub(r'^\s*\[\d+\]\s*', '', joined(rest[0]))))
        else:
            cluster_open = False
        prev_i = i
    return defs, def_blocks


MARKER_RE = re.compile(
    r'^\s*(' + '|'.join(MARKERS) + r')\s+'
    r'([0-9IVXLC]+(?:\s*[-–—]\s*[0-9IVXLC]+)?)\.?'
    r'(?:\s*[-–—:]+\s*|\s+)?(.*)$')


def convert(src_path, report_only=False):
    raw = open(src_path, encoding='utf-8').read().split('\n')
    meta = parse_header(raw)
    elems = blocks_of(raw)

    # 'front_index': a INDEX block placed before the body — drop the whole
    # run (INDEX block through the blocks up to the next ___ separator)
    # and don't let it trigger end-of-document detection
    idx_skip = set()
    if OVERRIDES.get(src_path.name, {}).get('front_index'):
        for i, (k, *rest) in enumerate(elems):
            if k == 'block' \
                    and joined(rest[0]).strip().rstrip(':') == 'INDEX':
                j = i
                while j < len(elems) and elems[j][0] != 'sep':
                    idx_skip.add(j)
                    j += 1
                break

    # find body end (Indexes / References / license line)
    end_i = len(elems)
    for i, (k, *rest) in enumerate(elems):
        if k != 'block' or i in idx_skip:
            continue
        t0 = joined(rest[0])
        if t0 in END_MARKERS or t0.startswith('This document is from the '
                                            'Christian Classics'):
            end_i = i
            break
    ov = OVERRIDES.get(src_path.name, {})
    defs, def_blocks = parse_footnotes(elems, end_i,
                                       loose=ov.get('loose_defs', False))
    markers = dict(MARKERS)
    markers.update(ov.get('level', {}))
    for dk in ov.get('drop_markers', ()):
        markers.pop(dk, None)
    lone = LONE | set(ov.get('lone', ()))
    title_max = ov.get('title_max', 150)
    marker_re = re.compile(
        r'^\s*(?i:(' + '|'.join(markers) + r'))\s+'
        r'([0-9IVXLC]+(?:\s*[-–—]\s*[0-9IVXLC]+)?)\.?'
        r'(?:\s*[-–—:]+\s*|\s+)?(.*)$')

    def esc(t):
        # square brackets in source text are literal — escape them so e.g.
        # Summa's "[54](A[1])" cross-refs can't render as markdown links
        return t.replace('[', '\\[').replace(']', '\\]')

    max_gap = ov.get('max_def_gap')          # elems; ref<->def distance cap

    # section boundaries for scoped footnote binding (numbering restarts
    # per section, e.g. Schmid's § divisions)
    sec_bounds = []
    if ov.get('sec_res'):
        for i, (k, *r) in enumerate(elems):
            if k == 'block' and re.match(ov['sec_res'], r[0][0]):
                sec_bounds.append(i)

    def sec_end(at_i):
        for b in sec_bounds:
            if b > at_i:
                return b
        return len(elems)

    def inline_notes(t, at_i):
        limit = min(sec_end(at_i), at_i + max_gap) if max_gap \
            else sec_end(at_i)

        def sub(m):
            n = int(m.group(1))
            q = defs.get(n)
            if not q:
                if ov.get('bracket_enum'):
                    return '**[%d]**' % n
                return m.group(0)
            # discard defs that precede this ref — they belong to earlier refs
            while q and q[0][0] < at_i:
                q.popleft()
            if q and q[0][0] < limit:
                return ' [fn. %d: %s]' % (n, esc(q.popleft()[1]))
            # unbound bracketed number: in works like Watson's it is an
            # inline enumeral — bold it rather than leaving a raw marker
            if ov.get('bracket_enum'):
                return '**[%d]**' % n
            return m.group(0)
        # [N.] is an enumeral style (Edwards et al.), not a footnote ref
        t = re.sub(r'\\\[(\d+)\.\\\]', r'**[\1.]**', t)
        return re.sub(r'\\\[(\d+)\\\]', sub, t)

    out, toc = [], []
    heads = []

    def h(level, text, indent):
        out.extend(['', '#' * level + ' ' + text, ''])
        if indent is not None:
            toc.append('  ' * indent + '- ' + text)
        heads.append((level, text))

    # body begins after the 2nd ___ separator (metadata box, then title page)
    seps = [i for i, e in enumerate(elems) if e[0] == 'sep']
    bsi = ov.get('body_sep', 1)
    body_start = seps[bsi] if len(seps) > bsi else 0

    # precompute marker-only blocks & TOC runs (>=2 consecutive marker blocks
    # are the source's own table of contents — skip them entirely)
    def marker_only(idx):
        e = elems[idx]
        if e[0] != 'block':
            return False
        f = e[1][0].strip()
        mm = marker_re.match(f)
        if not mm:
            return False
        rest_t = (mm.group(3) or '').strip()
        return bool(re.fullmatch(r'[\[\]\d\s.,;:\-–—]*', rest_t)) \
            and any(c.isdigit() for c in rest_t)

    toc_skip = set()
    j = 0
    while j < len(elems):
        if elems[j][0] == 'block' and marker_only(j):
            run = [j]
            k = j + 1
            while k < len(elems) and elems[k][0] == 'sep':
                k += 1
            while k < len(elems) and marker_only(k):
                run.append(k)
                k += 1
                while k < len(elems) and elems[k][0] == 'sep':
                    k += 1
            if len(run) >= 2:
                toc_skip.update(run)
            j = run[-1] + 1
        else:
            j += 1

    pending = None          # (level, label) awaiting a title block
    for i, (k, *rest) in enumerate(elems):
        if k == 'sep' or i in def_blocks or i <= body_start \
                or i in toc_skip or i in idx_skip:
            continue
        lines = rest[0]
        t = joined(lines)
        first = lines[0].strip()

        if t in END_MARKERS or (t.startswith('Index of') and 'Scripture' in t):
            break
        if t.startswith('This document is from the Christian Classics'):
            break

        head_hit = None
        for pat, lvl in ov.get('head_res', ()):
            if re.match(pat, lines[0]) and len(t) < 220:
                head_hit = (lvl, t)
                break
        if head_hit:
            lvl, tt = head_hit
            tt = re.sub(r'\s*\[[^\]]*\]', '', tt)      # crossref tags
            tt = re.sub(r'^(\d+)\.(?=[A-Za-z])', r'\1. ', tt)
            if re.fullmatch(r'[IVXLC]+\.?', tt):
                # bare numeral marker (I. / II. …) — next block may be its title
                if pending is not None:
                    pl, plab = pending
                    h(pl, plab, pl - 2)
                pending = (lvl, tt.rstrip('.'))
                continue
            if tt.upper() == tt and any(c.isalpha() for c in tt):
                tt = titlecase(tt)
            h(lvl, esc(tt).rstrip('.'), lvl - 2 if lvl <= 3 else None)
            pending = None
            continue

        m = marker_re.match(first)
        lone_hit = t.upper().rstrip('.') in lone

        if m and len(first) < 90:
            kw, num, rest_t = m.group(1).upper(), m.group(2), m.group(3).strip()
            lvl = markers.get(kw, markers.get(m.group(1), 3))
            label = kw.capitalize() + ' ' + num
            if kw == 'CHAPTER':
                label = 'Chapter ' + num
            if pending is not None:
                # stacked structural lines (PART I / QUESTION …) — emit the
                # pending head with no title before processing this marker
                pl, plab = pending
                h(pl, plab, pl - 2)
            if rest_t and not re.match(r'^[-–—.]*\s*$', rest_t):
                title = re.sub(r'\s*\[[^\]]*\]', '', rest_t).rstrip('.')
                if title.upper() == title and any(c.isalpha() for c in title):
                    title = titlecase(title)
                h(lvl, label + ' — ' + esc(title), lvl - 2)
                pending = None
            else:
                pending = (lvl, label)
            continue

        if lone_hit:
            if pending is not None:
                pl, plab = pending
                h(pl, plab, pl - 2)
            h(2, titlecase(t.rstrip('.')), 0)
            pending = None
            continue

        if pending is not None:
            lvl, label = pending
            if len(t) <= title_max and not t.endswith(';'):
                title = re.sub(r'\s*\[[^\]]*\]', '', t).rstrip('.')
                if title.upper() == title and any(c.isalpha() for c in title):
                    title = titlecase(title)
                h(lvl, label + ' — ' + esc(title), lvl - 2)
            else:
                h(lvl, label, lvl - 2)
                out.append(inline_notes(esc(t), i))
                out.append('')
            pending = None
            continue

        # ALL-CAPS standalone subheadings -> #### (level overridable);
        # require a prior heading unless the file opts in via caps_level,
        # so title-page caps don't leak as #### noise
        if len(t) < 130 and t.isupper() and sum(c.isalpha() for c in t) > 6 \
                and (heads or 'caps_level' in ov):
            tt = re.sub(r'\s*\[[^\]]*\]', '', t)
            tt = re.sub(r'^(\d+)\.(?=[A-Za-z])', r'\1. ', tt)
            clvl = ov.get('caps_level', 4)
            h(clvl, esc(titlecase(tt).rstrip('.')),
              clvl - 2 if clvl <= 3 else None)
            continue

        ms = SCHOL.match(t)
        m2 = BOLD_MARK.match(t) if not ms else None
        if ms:
            t = '**%s** %s' % (ms.group(1).rstrip(),
                               t[ms.end():].strip())
        elif m2:
            t = '**%s** %s' % (m2.group(1).rstrip(), m2.group(2))
        out.append(inline_notes(esc(t), i))
        out.append('')

    if pending is not None:
        pl, plab = pending
        h(pl, plab, pl - 2)

    if report_only:
        return heads, defs

    title = meta.get('Title', src_path.stem)
    author = clean_author(meta.get('Creator(s)'), src_path.stem)
    edition = meta.get('Print Basis', '')
    header = ['---', f'title: "{title}"', f'author: "{author}"']
    if edition:
        header.append(f'edition: "{edition}"')
    header += ['source: "Christian Classics Ethereal Library (CCEL)"',
               '---', '', f'# {title}', '', f'*{author}*', '',
               '> Source: Christian Classics Ethereal Library (CCEL). '
               'Public domain.', '', '## Contents', '']
    final = '\n'.join(header) + '\n'.join(toc) + '\n' + '\n'.join(out) + '\n'
    final = re.sub(r'\\\[\d+\\\]mp3', '', final)      # CCEL audio-link refs
    final = re.sub(r'(\n\*{5,})+\n*$', '\n', final)   # trailing rule marks
    final = fix_mojibake(final)
    out_path = DOC_DIR / (src_path.stem + '.md')
    out_path.write_text(final, encoding='utf-8')
    return heads, defs, out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='*')
    ap.add_argument('--report', action='store_true')
    args = ap.parse_args()

    files = [SRC_DIR / f for f in args.files] if args.files else sorted(
        p for p in SRC_DIR.glob('*.txt')
        if not (DOC_DIR / (p.stem + '.md')).exists())
    if not files:
        print('nothing to convert')
        return
    for p in files:
        try:
            if args.report:
                heads, defs = convert(p, report_only=True)
                print(f'=== {p.name}  ({len(heads)} headings, '
                      f'{len(defs)} footnotes)')
                for lvl, txt in heads:
                    print('   ' * (lvl - 2) + '#' * lvl + ' ' + txt)
            else:
                heads, defs, out_path = convert(p)
                raw_refs = re.findall(r'\\\[(\d+)\\\]', out_path.read_text())
                print(f'{p.name}: {len(heads)} headings, {len(defs)} notes, '
                      f'{len(raw_refs)} raw [N] left -> {out_path.name}')
        except Exception as e:
            print(f'{p.name}: FAILED {e}', file=sys.stderr)


if __name__ == '__main__':
    main()
