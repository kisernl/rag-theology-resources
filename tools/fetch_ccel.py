#!/usr/bin/env python3
"""Fetch plain-text versions of all works listed in a CCEL genre index.

Downloads each work's full UTF-8 text into sources/, named per the repo
convention:  sources/<author-slug>-<title-slug>.txt

Usage:
    python3 tools/fetch_ccel.py                 # fetch gen-THE list
    python3 tools/fetch_ccel.py --genre gen-XXX # another genre
    python3 tools/fetch_ccel.py --dry-run       # list works, no download
"""
import argparse
import re
import sys
import time
import urllib.error
import urllib.request
from html import unescape
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOURCES = REPO / 'sources'
GENRE_URL = 'https://ccel.org/index/genre/{genre}'
TXT_URL = 'https://ccel.org/ccel/b/{author}/{work}/cache/{work}.txt'
UA = {'User-Agent': 'theology-resources-reformed fetch (personal use)'}
DELAY = 1.5          # seconds between requests
TRIES = 3

# author/work ids already present under sources/ (no re-download)
ALREADY = {
    ('allestree', 'government'):  'allestree-government-of-the-tongue.txt',
    ('anselm', 'basic_works'):    'anselm-basic-writings.txt',
    ('augustine', 'doctrine'):    'augustine-on-christian-doctrine.txt',
    ('baxter', 'unconverted'):    'baxter-call-to-the-unconverted.txt',
    ('baxter', 'causes'):         'baxter-slighting-christ.txt',
    ('baxter', 'pastor'):         'baxter-reformed-pastor.txt',
    ('boethius', 'tracts'):       'boethius-theological-tractates.txt',
    ('boettner', 'predest'):      'boettner-reformed-doctrine-of-predestination.txt',
    ('bonar', 'peace'):           'bonar-gods-way-of-peace.txt',
    ('bonar', 'rentveil'):        'bonar-the-rent-veil.txt',
    ('boston', 'crook'):          'boston-crook-in-the-lot.txt',
    ('calvin', 'institutes'):     'calvin-institutes.txt',
}
# listed works intentionally excluded (content duplicated elsewhere, or not
# useful for the RAG corpus)
DUPLICATES = {
    ('boethius', 'trinity'): 'duplicate of Tractate I in boethius-theological-tractates.txt',
    ('calvin', 'institutio1'): 'Latin, partial digitization (front matter only)',
    ('calvin', 'institutio2'): 'Latin, partial digitization (front matter only)',
    ('hodge', 'theology4'): 'standalone index volume — low RAG value',
    ('owen', 'poema'): 'single Latin poem',
    ('cranmer', 'necessarydoctrine'): 'partial digitization — only the '
        'justification excerpt (~950 words); removed from corpus',
}


def fetch(url):
    for attempt in range(TRIES):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode('utf-8', 'replace')
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt == TRIES - 1:
                raise
        except urllib.error.URLError:
            if attempt == TRIES - 1:
                raise
        time.sleep(DELAY * (attempt + 2))


def works_in_genre(genre):
    """Return [(author_dir, work_id, title, author_name)] from the index page."""
    html = fetch(GENRE_URL.format(genre=genre))
    if html is None:
        sys.exit('genre page not found: ' + genre)
    out = []
    pat = re.compile(
        r'<a href="/ccel/([a-z_0-9]+)/([a-z_0-9]+)\.html">(.*?)</a>'
        r'.*?authorName.*?<a href="/ccel/\1">(.*?)</a>',
        re.S)
    for m in pat.finditer(html):
        author_dir, work, title, author = m.groups()
        title = re.sub(r'\s+', ' ', unescape(title)).strip()
        author = re.sub(r'\s+', ' ', unescape(author)).strip()
        out.append((author_dir, work, title, author))
    return out


def slug(s):
    import unicodedata
    s = unescape(s).lower()
    s = s.replace('æ', 'ae').replace('œ', 'oe')
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return re.sub(r'-{2,}', '-', s)


def author_slug(author_dir, author_name):
    return re.sub(r'_[a-z]$', '', author_dir) or slug(author_name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--genre', default='gen-THE')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--delay', type=float, default=DELAY)
    args = ap.parse_args()

    SOURCES.mkdir(exist_ok=True)
    works = works_in_genre(args.genre)
    print(f'{len(works)} works listed in {args.genre}\n')

    ok, skipped, dup, failed = [], [], [], []
    seen_names = {p.name for p in SOURCES.glob('*.txt')}
    for author_dir, work, title, author in works:
        key = (author_dir, work)
        if key in ALREADY:
            skipped.append((title, ALREADY[key]))
            continue
        if key in DUPLICATES:
            dup.append((title, DUPLICATES[key]))
            continue

        name = f'{author_slug(author_dir, author)}-{slug(title)}.txt'
        if name in seen_names:
            name = f'{author_slug(author_dir, author)}-{slug(title)}-{work}.txt'
        dest = SOURCES / name

        if args.dry_run:
            print(f'  would fetch {author_dir}/{work} -> {name}')
            continue

        text = fetch(TXT_URL.format(author=author_dir, work=work))
        if text is None or '____' not in text[:2000]:
            failed.append((title, 'no plain-text edition'))
            continue
        dest.write_text(text, encoding='utf-8')
        seen_names.add(name)
        print(f'  {name}  ({len(text)//1024} KB)')
        time.sleep(args.delay)

    if not args.dry_run:
        print(f'\n{len(list(SOURCES.glob("*.txt")))} files in sources/')
    if skipped:
        print(f'\nskipped, already present ({len(skipped)}):')
        for t, f in skipped:
            print(f'  {t} -> {f}')
    if dup:
        print(f'\nskipped, duplicates ({len(dup)}):')
        for t, why in dup:
            print(f'  {t} — {why}')
    if failed:
        print(f'\nFAILED ({len(failed)}):')
        for t, why in failed:
            print(f'  {t} — {why}')
        sys.exit(1)


if __name__ == '__main__':
    main()
