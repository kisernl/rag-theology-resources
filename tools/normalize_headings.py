#!/usr/bin/env python3
"""Normalize markdown headings to the corpus OSIS convention.

Two kinds of transforms:

1. Generic (applied to every doc):
   - full book names in headings -> OSIS codes ("Matthew 5" -> "Matt 5")
   - spaced-caps book headings ("G E N E S I S") -> OSIS code
   - "Psalm N" -> "Ps N"; "Book Chapter N" -> "Book N"
   - JFB abbreviations in heading refs ("Ge 1:1" -> "Gen 1:1")
   - "St. X" -> OSIS; roman numerals after a book name -> arabic
   - digit ranges -> en dash
   - book-context tracking via explicit book headings (used below)

2. Chapter-context mapping (only for files in CHAPTER_CTX — works whose
   "Chapter N" headings are literally Bible chapters):
   - "Chapter N[ — title]" / "Chap. N" -> "{Book} N[ — title]"
   - "Chapter N — <abbr> c:v. title" -> "{Book} c:v — title"
   - "Chapter N — 1-11" (pure verse range) -> "{Book} N:1–11"
   - "Remarks on Chapter N" -> "{Book} N — Remarks"
   - "Analysis of the Chapter" -> "{Book} {cur_ch} — Analysis"
   Book for a bare "Chapter N": for N>1 the running context is used.
   For N==1 (a chapter-number restart = new book), the book advances to
   the next entry in frontmatter `covers:` — UNLESS no chapter heading
   has yet been emitted under the current book (an explicit "## Lev"
   divider already moved context, so Chapter 1 belongs to it). If no
   context exists yet, the first covers entry seeds it; failing that,
   the nearest explicit-book heading wins.
   Covers entries may carry refs ("Rev 2–3") — only the book is used.

Usage:
    python3 tools/normalize_headings.py            # all docs
    python3 tools/normalize_headings.py FILE ...   # specific docs
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOC = REPO / 'docs'

BOOKS = {
    "Genesis": "Gen", "Exodus": "Exod", "Leviticus": "Lev",
    "Numbers": "Num", "Deuteronomy": "Deut", "Joshua": "Josh",
    "Judges": "Judg", "Ruth": "Ruth", "1 Samuel": "1Sam",
    "2 Samuel": "2Sam", "1 Kings": "1Kgs", "2 Kings": "2Kgs",
    "1 Chronicles": "1Chr", "2 Chronicles": "2Chr", "Ezra": "Ezra",
    "Nehemiah": "Neh", "Esther": "Esth", "Job": "Job", "Psalms": "Ps",
    "Psalm": "Ps", "Proverbs": "Prov", "Ecclesiastes": "Eccl",
    "Song of Solomon": "Song", "Song of Songs": "Song", "Isaiah": "Isa",
    "Jeremiah": "Jer", "Lamentations": "Lam", "Ezekiel": "Ezek",
    "Daniel": "Dan", "Hosea": "Hos", "Joel": "Joel", "Amos": "Amos",
    "Obadiah": "Obad", "Jonah": "Jonah", "Micah": "Mic", "Nahum": "Nah",
    "Habakkuk": "Hab", "Zephaniah": "Zeph", "Haggai": "Hag",
    "Zechariah": "Zech", "Malachi": "Mal", "Matthew": "Matt",
    "Mark": "Mark", "Luke": "Luke", "John": "John", "Acts": "Acts",
    "Romans": "Rom", "1 Corinthians": "1Cor", "2 Corinthians": "2Cor",
    "Galatians": "Gal", "Ephesians": "Eph", "Philippians": "Phil",
    "Colossians": "Col", "1 Thessalonians": "1Thess",
    "2 Thessalonians": "2Thess", "1 Timothy": "1Tim", "2 Timothy": "2Tim",
    "Titus": "Titus", "Philemon": "Phlm", "Hebrews": "Heb",
    "James": "Jas", "1 Peter": "1Pet", "2 Peter": "2Pet",
    "1 John": "1John", "2 John": "2John", "3 John": "3John",
    "Jude": "Jude", "Revelation": "Rev",
}
OSIS = set(BOOKS.values())
BOOK_ALT = '|'.join(sorted(BOOKS, key=len, reverse=True)).replace(
    ' ', r'\s+')
BOOK_RE = re.compile(r'\b(' + BOOK_ALT + r')\b')
OSIS_RE = '|'.join(sorted(OSIS, key=len, reverse=True))

# Jamieson-Fausset-Brown abbreviations (and a few common variants)
JFB = {
    'Ge': 'Gen', 'Ex': 'Exod', 'Le': 'Lev', 'Nu': 'Num', 'De': 'Deut',
    'Jos': 'Josh', 'Jg': 'Judg', 'Jud': 'Judg', 'Ru': 'Ruth',
    '1Sa': '1Sam', '2Sa': '2Sam', '1Ki': '1Kgs', '2Ki': '2Kgs',
    '1Ch': '1Chr', '2Ch': '2Chr', 'Ezr': 'Ezra', 'Ne': 'Neh',
    'Es': 'Esth', 'Job': 'Job', 'Ps': 'Ps', 'Pr': 'Prov', 'Ec': 'Eccl',
    'So': 'Song', 'Ca': 'Song', 'Isa': 'Isa', 'Jer': 'Jer', 'La': 'Lam',
    'Eze': 'Ezek', 'Ezk': 'Ezek', 'Da': 'Dan', 'Ho': 'Hos', 'Joe': 'Joel',
    'Am': 'Amos', 'Ob': 'Obad', 'Jon': 'Jonah', 'Mic': 'Mic',
    'Na': 'Nah', 'Hab': 'Hab', 'Zep': 'Zeph', 'Hag': 'Hag',
    'Zec': 'Zech', 'Mal': 'Mal', 'Mt': 'Matt', 'Mr': 'Mark', 'Mk': 'Mark',
    'Lu': 'Luke', 'Lk': 'Luke', 'Joh': 'John', 'Jn': 'John', 'Ac': 'Acts',
    'Ro': 'Rom', '1Co': '1Cor', '2Co': '2Cor', 'Ga': 'Gal', 'Eph': 'Eph',
    'Php': 'Phil', 'Col': 'Col', '1Th': '1Thess', '2Th': '2Thess',
    '1Ti': '1Tim', '2Ti': '2Tim', 'Tit': 'Titus', 'Phm': 'Phlm',
    'Heb': 'Heb', 'Jas': 'Jas', '1Pe': '1Pet', '2Pe': '2Pet',
    '1Jo': '1John', '2Jo': '2John', '3Jo': '3John', 'Jude': 'Jude',
    'Re': 'Rev',
}
JFB_RE = '|'.join(sorted(JFB, key=len, reverse=True))
ANYBOOK = f'(?:{JFB_RE}|{OSIS_RE})'

# files whose "Chapter N" headings are Bible chapters (chapter-by-chapter
# commentaries). Files with literary/thematic chapter numbering
# (bennett, johnson_bw-pnt, augustine, owen, …) must NOT be listed here —
# nor files without reliable book-divider headings (gray_jm-cwc has no
# Gen/Exod dividers; henry-concise's dividers go unrecognized), since
# wrong-book labels are worse than honest bare "Chapter N" markers.
CHAPTER_CTX = {
    'jamieson-commentary-critical-and-explanatory-on-the-whole-bible.md',
    'barnes-barnes-new-testament-notes.md',
    'henry-commentary-on-the-whole-bible-volume-i-genesis-to-deuteronomy.md',
    'henry-commentary-on-the-whole-bible-volume-ii-joshua-to-esther.md',
    'henry-commentary-on-the-whole-bible-volume-iii-job-to-song-of-solomon.md',
    'henry-commentary-on-the-whole-bible-volume-iv-isaiah-to-malachi.md',
    'henry-commentary-on-the-whole-bible-volume-v-matthew-to-john.md',
    'henry-commentary-on-the-whole-bible-volume-vi-acts-to-revelation.md',
    'leupold-exposition-of-genesis-volumes-1-and-2.md',
}

ROMAN = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
ORD = {'First': '1', 'Second': '2', 'Third': '3', 'Fiest': '1'}


def roman_to_int(s):
    s = s.upper()
    if not re.fullmatch(r'[IVXLCDM]+', s):
        return None
    total, prev = 0, 0
    for ch in reversed(s):
        v = ROMAN[ch]
        total += -v if v < prev else v
        prev = max(prev, v)
    return total


def norm_ref(ref):
    """'1:1, 2' -> '1:1–2'; '1:1-5' -> '1:1–5'."""
    ref = re.sub(r'(?<=\d)-(?=\d)', '–', ref.strip())
    return re.sub(r'(\d)\s*,\s*(\d)', r'\1–\2', ref)


def jfb_sub(m):
    return JFB[m.group(1)] + ' ' + norm_ref(m.group(2))


# tail words of spaced-caps epistle headings; ordinals apply only to
# books that have numbered forms
EPISTLE_TAIL = {
    'corinthians': 'Cor', 'thessalonians': 'Thess', 'timothy': 'Tim',
    'peter': 'Pet', 'john': 'John',
    'james': 'Jas', 'jude': 'Jude', 'galatians': 'Gal',
    'ephesians': 'Eph', 'philippians': 'Phil', 'colossians': 'Col',
    'titus': 'Titus', 'philemon': 'Phlm', 'hebrews': 'Heb',
    'romans': 'Rom',
}
ORDW = {'first': '1', 'second': '2', 'third': '3', 'fiest': '1'}


def spaced_book(t):
    """'G E N E S I S' / 'M a T T H E W' -> 'Gen'/'Matt' (or None).

    Also resolves spaced-caps phrase forms like
    'A C T S O F T H E a P O S T L E S' -> Acts and
    'T H E F I R S T E P I S T L E ... J O H N' -> 1John."""
    if not re.match(r'^([A-Za-z]\.? )+[A-Za-z]\.?\s*$', t):
        return None
    joined = re.sub(r'[^a-z]', '', t.lower())
    for pfx in ('st', 'the'):
        if joined.startswith(pfx):
            joined = joined[len(pfx):]
    for full, code in BOOKS.items():
        if full.replace(' ', '').lower() == joined:
            return code
    j = joined[3:] if joined.startswith('the') else joined
    if 'actsoftheapostles' in j or j == 'acts':
        return 'Acts'
    if 'revelation' in j:
        return 'Rev'
    m = re.match(r'(?:the)?(first|second|third|fiest)?'
                 r'(?:general|catholic)?(?:epistles?|epistlesof)?'
                 r'(?:of|to)?(?:paul|st)?(?:the)?(?:apostle)?(.+)$', j)
    if m and ('epistle' in j or m.group(1)):
        ordn = ORDW.get(m.group(1) or '', '')
        tail = m.group(2)
        for name, code in EPISTLE_TAIL.items():
            if tail.endswith(name):
                if code[0].isdigit() or (
                        ordn and code in {'Cor', 'Thess', 'Tim',
                                          'Pet', 'John'}):
                    return ordn + code
                return code
    return None


def epistle_map(t):
    """'The Second Epistle of Paul to Timothy' -> '2Tim' (or None)."""
    m = re.match(r'(?:The\s+)?(?:(First|Second|Third|Fiest)\s+)?'
                 r'(?:General\s+)?Epistle\s+'
                 r'(?:of\s+(?:St\.?\s+)?|of\s+Paul\s+to\s+(?:the\s+)?'
                 r'|to\s+(?:the\s+)?)(\w+)', t)
    if not m:
        return None
    n = ORD.get(m.group(1) or '', '')
    name = m.group(2)
    cands = [(full, code) for full, code in BOOKS.items()
             if full.lstrip('123 ').lower().startswith(name.lower())]
    if not cands:
        return None
    if n:
        want = f'{n} {name}'
        for full, code in cands:
            if full.lower() == want.lower():
                return code
    for full, code in cands:
        if full.lower() == name.lower():
            return code
    return None if n else cands[0][1]


def explicit_book(t):
    """OSIS code if the heading names a book/ref, else None."""
    t = re.sub(r'^(?:The\s+|Book of\s+|The Book of\s+)', '', t)
    m = re.match(rf'^(?:{OSIS_RE})\b', t)
    if m:
        return m.group(0)
    sb = spaced_book(t)
    if sb:
        return sb
    # book name must head the title AND be followed by a ref/Chapter/end —
    # "Genesis of the Catholic ..." is a concept, not a book divider
    m = re.match(rf'^({BOOK_ALT})\b'
                 r'(?=\s*(?:\d|:|—|-|$|Chapter\b))', t)
    if m:
        return BOOKS[re.sub(r'\s+', ' ', m.group(1))]
    m = re.match(rf'\b({JFB_RE})\s+\d', t)
    if m:
        return JFB[m.group(1)]
    m = re.search(r'Gospel (?:According to|of)\s+(?:St\.?\s+)?'
                  r'(Matthew|Mark|Luke|John)', t)
    if m:
        return BOOKS[m.group(1)]
    if re.search(r'Acts of the Apostles|^The Acts\b', t):
        return 'Acts'
    if re.match(r'(?:The\s+)?Book of Revelation|^Revelation\b', t):
        return 'Rev'
    m = re.match(r'^St\.?\s+(Matthew|Mark|Luke|John)$', t)
    if m:
        return BOOKS[m.group(1)]
    return None


def transform(path):
    ctx = path.name in CHAPTER_CTX
    lines = path.read_text().splitlines()
    heads = [(i, re.match(r'^(#{2,4}) (.*)$', l))
             for i, l in enumerate(lines)]
    explic = []
    for i, h in heads:
        if h:
            b = explicit_book(h.group(2)) or epistle_map(h.group(2))
            if b:
                explic.append((i, b))

    def near_book(at):
        best, bd = None, None
        for i, b in explic:
            d = abs(i - at)
            if bd is None or d < bd:
                best, bd = b, d
        return best

    # frontmatter covers -> ordered book queue for restart resolution
    covers = []
    fm = re.search(r'^covers: \[(.*)\]', '\n'.join(lines[:20]), re.M)
    if fm:
        for tok in re.findall(r'"([^"]+)"', fm.group(1)):
            bk = re.match(rf'^({OSIS_RE})\b', tok)
            if bk:
                covers.append(bk.group(1))

    def next_book(b):
        if b in covers:
            i = covers.index(b)
            if i + 1 < len(covers):
                return covers[i + 1]
        return None

    cur, cur_ch, chap_since, changed = None, None, 0, 0
    pend_ord = None  # ordinal carried from '... First Epistle ... to the'
    for i, h in heads:
        if not h:
            continue
        lvl, t = h.group(1), h.group(2).strip()
        orig = t

        sb = spaced_book(t)
        if sb:
            t = sb
            pend_ord = None
        elif re.match(r'^([A-Za-z]\.? )+[A-Za-z]\.?\s*$', t):
            # spaced tail word after an 'Epistle ... to the' heading:
            # 'C O R I N T H I a N S' -> '1Cor' via pending ordinal
            j2 = re.sub(r'[^a-z]', '', t.lower())
            for name, code in EPISTLE_TAIL.items():
                if j2.endswith(name):
                    if name in {'corinthians', 'thessalonians', 'timothy',
                                'peter', 'john'}:
                        cand = (pend_ord or (
                            cur[0] if cur and cur[0].isdigit()
                            and cur[1:] == code else '')) + code
                        if cand in OSIS:
                            t = cand
                    elif not pend_ord or code in OSIS:
                        t = code
                    break
            pend_ord = None
        else:
            # JFB abbrev refs inside heading text
            t = re.sub(rf'\b({JFB_RE})\s+(\d[\d:,\s\-–]*)', jfb_sub, t)
            # full book names -> OSIS, but only when clearly a scripture
            # reference: the whole heading is (decorated) book name, or the
            # name is followed by a chapter/verse number or 'Chapter'.
            # ("The Genesis of Dogma" / "James Orr, D.D." must NOT map.)
            t = re.sub(rf'^(?:The\s+|Book\s+of\s+|The\s+Book\s+of\s+)?'
                       rf'({BOOK_ALT})\.?$',
                       lambda m: BOOKS[re.sub(r'\s+', ' ', m.group(1))], t)
            t = re.sub(rf'\b({BOOK_ALT})'
                       rf'(?=\s+(?:\d|Chapter\b))',
                       lambda m: BOOKS[re.sub(r'\s+', ' ', m.group(1))], t)
            t = re.sub(r'Gospel\s+(?:According\s+to|of)\s+'
                       r'(?:St\.?\s+)?(Matthew|Mark|Luke|John)',
                       lambda m: 'Gospel of ' + BOOKS[m.group(1)], t)
            t = re.sub(r'\bSt\.?\s+(Matt|Mark|Luke|John)\b', r'\1', t)
            t = re.sub(r'\bPs\s+(\d+)\s*—\s*(\d)', r'Ps \1:\2', t)
            t = re.sub(rf'^({OSIS_RE}) Chapter\s+([0-9IVXLC]+)\.?$',
                       lambda m: f'{m.group(1)} '
                       f'{roman_to_int(m.group(2)) or m.group(2)}', t)
            t = re.sub(rf'^({OSIS_RE})\s+([IVXLC]+)\.?$',
                       lambda m: f'{m.group(1)} '
                       f'{roman_to_int(m.group(2)) or m.group(2)}', t)

        # remember '... First Epistle ... to the' so a following spaced
        # tail word ('C O R I N T H I a N S') can resolve to 1Cor
        pm = re.search(r'\b(First|Second|Third|Fiest)\s+'
                       r'(?:General\s+)?Epistle\b.*(?:to|of)\s+the\s*$',
                       orig)
        if pm:
            pend_ord = ORD[pm.group(1)]
        elif not re.match(r'^([A-Za-z]\.? )+[A-Za-z]\.?\s*$', orig):
            pend_ord = None

        b = explicit_book(t) or epistle_map(orig)
        if b:
            cur = b
        m = re.match(rf'^({OSIS_RE})\s+(\d+)', t)
        if m:
            cur, cur_ch, chap_since = m.group(1), m.group(2), 1
        elif b and not re.match(r'^Chapter\b', t):
            chap_since = 0

        if ctx:
            done = False

            def restart_book(n):
                """Book for a bare 'Chapter N' marker."""
                if n != 1:
                    return cur or near_book(i)
                if cur is None:
                    return covers[0] if covers else near_book(i)
                if chap_since == 0:
                    return cur            # fresh explicit divider owns it
                return next_book(cur) or cur
            m = re.match(r'^Chapter \(elegy\) (\d+)', t)
            if m and cur:
                t = f'{cur} {m.group(1)}'
                cur_ch = m.group(1)
                chap_since += 1
                done = True
            if not done:
                m = re.match(r'^Chap\.?\s+([IVXLCivxlc]+)\.?\s*$', t)
                if m and cur:
                    n = roman_to_int(m.group(1))
                    if n:
                        t, cur_ch = f'{cur} {n}', str(n)
                        chap_since += 1
                        done = True
            if not done:
                m = re.match(rf'^Chapter ([0-9IVXLC]+)\.?\s*—\s*'
                             rf'({ANYBOOK})\s+([\d:,\s\-–]+)'
                             rf'\.?\s*(.*)$', t)
                if m:
                    n = roman_to_int(m.group(1)) or m.group(1)
                    bk = JFB.get(m.group(2), m.group(2))
                    ref = norm_ref(m.group(3))
                    title = m.group(4).strip()
                    t = f'{bk} {ref}' + (f' — {title}' if title else '')
                    cur, cur_ch = bk, str(n)
                    chap_since += 1
                    done = True
            if not done:
                m = re.match(r'^Chapter ([0-9IVXLC]+)\.?\s*'
                             r'(?:—\s*(.*))?$', t)
                if m:
                    n = roman_to_int(m.group(1)) or (
                        int(m.group(1)) if m.group(1).isdigit() else None)
                    bk = restart_book(n)
                    if bk and n:
                        rest = (m.group(2) or '').strip()
                        t = f'{bk} {n}'
                        # pure verse-range tail: "— 1–11" -> "20:1–11"
                        vm = re.fullmatch(r'(\d+(?:[–-]\d+)?)', rest)
                        if vm:
                            t = f'{bk} {n}:{norm_ref(vm.group(1))}'
                        elif rest:
                            t += f' — {rest}'
                        cur, cur_ch = bk, str(n)
                        chap_since += 1
                        done = True
            if not done:
                m = re.match(r'^Remarks on '
                             r'(?:Chapter\s+([0-9IVXLC]+)'
                             rf'|({OSIS_RE})\s+(\d+))', t)
                if m:
                    bk = m.group(2) or cur
                    n = m.group(3) or roman_to_int(m.group(1) or '')
                    if bk and n:
                        t = f'{bk} {n} — Remarks'
                        done = True
            if not done:
                if re.match(r'^Remarks\.?$', t) and cur and cur_ch:
                    t = f'{cur} {cur_ch} — Remarks'
                elif re.match(r'^Analysis of (?:the )?Chapter', t) \
                        and cur and cur_ch:
                    t = f'{cur} {cur_ch} — Analysis'

        t = re.sub(r'(?<=\d)-(?=\d)', '–', t)
        if t != orig:
            lines[i] = f'{lvl} {t}'
            changed += 1
    if changed:
        path.write_text('\n'.join(lines) + '\n')
    return changed


def main():
    files = [DOC / f for f in sys.argv[1:]] \
        if len(sys.argv) > 1 else sorted(DOC.glob('*.md'))
    total = 0
    for p in files:
        n = transform(p)
        if n:
            print(f'{p.name}: {n} headings normalized')
        total += n
    print(f'total: {total} headings normalized across {len(files)} docs')


if __name__ == '__main__':
    main()
