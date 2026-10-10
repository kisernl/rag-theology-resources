#!/usr/bin/env python3
"""Apply the corpus metadata contract to docs missing frontmatter fields.

Inserts `tradition`, `genre`, and (for commentaries/sermon collections)
`covers` after the `author:` line for every doc in docs/ that lacks a
`tradition:` field. Maps are keyed by filename; run after convert_ccel.py
and before/with normalize_headings.py.

Usage:
    python3 tools/tag_frontmatter.py            # all untagged docs
    python3 tools/tag_frontmatter.py FILE ...   # specific docs
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOC = REPO / 'docs'

TRADITION = {
    'adeney':'congregationalist','alexander':'anglican','aquinas':'medieval',
    'ball':'anglican','barnes':'reformed','bennett':'congregationalist',
    'berkhof':'reformed','blaikie':'reformed','bruce':'reformed',
    'burgon':'anglican','burton':'baptist','calvin':'reformed',
    'chadwick':'anglican','cox':'baptist','daubney':'anglican',
    'denney':'reformed','dick':'reformed','dods':'reformed',
    'easton':'anglican','edwards_tc':'reformed','farrar':'anglican',
    'findlay':'methodist','gibson':'reformed','gill':'reformed-baptist',
    'gray_jm':'dispensationalist','guyon':'catholic',
    'harnack':'liberal-protestant','harper':'reformed','henry':'reformed',
    'hodge':'reformed','hort':'anglican','horton':'congregationalist',
    'jamieson':'reformed','johnson_bw':'restorationist',
    'jowett':'congregationalist','kellogg':'reformed','latimer':'anglican',
    'leupold':'lutheran','lightfoot':'anglican','lumby':'anglican',
    'luther':'lutheran','maclaren':'baptist','mcgarvey':'restorationist',
    'meyer':'baptist','milligan':'reformed','moffat':'reformed',
    'moule':'anglican','nave':'methodist','newell':'dispensationalist',
    'plummer':'anglican','rainy':'reformed','robertson_at':'baptist',
    'ryle':'anglican','schaff':'early-church','skinner':'reformed',
    'smith_ga':'reformed','south_robert':'anglican',
    'spurgeon':'reformed-baptist','stokes':'anglican','swete':'anglican',
    'taylor_jh':'evangelical','temple':'anglican','tischendorf':'lutheran',
    'torrey':'evangelical','trench':'anglican','watson':'reformed',
    'watson_ra':'evangelical','wesley':'methodist','white':'other',
}

GENRE_OVERRIDE = {
    'berkhof-introduction-to-the-new-testament.md': 'treatise',
    'bruce-training-of-the-twelve.md': 'treatise',
    'burgon-causes-of-the-corruption-of-the-traditional-text-of-the-holy-gospels.md': 'treatise',
    'burgon-inspiration-and-interpretation-seven-sermons-preached-before-the-university-of-oxford-with-preliminary-remarks-being-an-answer-to-a-volume-enti.md': 'sermon',
    'burgon-last-twelve-verses-of-the-gospel-according-to-s-mark-vindicated-against-recent-critical-objectors-and-established.md': 'treatise',
    'daubney-three-additions-to-daniel-a-study.md': 'treatise',
    'easton-easton-s-bible-dictionary.md': 'reference',
    'nave-nave-s-topical-bible.md': 'reference',
    'torrey-torrey-s-new-topical-textbook.md': 'reference',
    'gray_jm-synthetic-bible-studies.md': 'treatise',
    'guyon-song-of-songs-of-solomon-explanations-and-reflections-having-reference-to-the-interior-life.md': 'devotional',
    'harnack-origin-of-the-new-testament.md': 'history',
    'latimer-sermons-by-hugh-latimer.md': 'sermon',
    'south_robert-sermons-preached-upon-several-occasions-vol-v.md': 'sermon',
    'spurgeon-till-he-come.md': 'sermon',
    'watson-beatitudes-an-exposition-of-matthew-5-1-12.md': 'sermon',
    'lightfoot-from-the-talmud-and-hebraica.md': 'treatise',
    'meyer-our-daily-homily.md': 'devotional',
    'swete-introduction-to-the-old-testament-in-greek-additional-notes.md': 'treatise',
    'taylor_jh-union-and-communion.md': 'devotional',
    'temple-essays-and-reviews-the-education-of-the-world-bunsen-s-biblical-researches-on-the-study-of-the-evidences-of-christianity-seances-historiques.md': 'treatise',
    'tischendorf-origin-of-the-four-gospels.md': 'history',
    'tischendorf-when-were-our-gospels-written.md': 'history',
}

NT = ["Matt","Mark","Luke","John","Acts","Rom","1Cor","2Cor","Gal","Eph",
      "Phil","Col","1Thess","2Thess","1Tim","2Tim","Titus","Phlm","Heb",
      "Jas","1Pet","2Pet","1John","2John","3John","Jude","Rev"]
OT = ["Gen","Exod","Lev","Num","Deut","Josh","Judg","Ruth","1Sam","2Sam",
      "1Kgs","2Kgs","1Chr","2Chr","Ezra","Neh","Esth","Job","Ps","Prov",
      "Eccl","Song","Isa","Jer","Lam","Ezek","Dan","Hos","Joel","Amos",
      "Obad","Jonah","Mic","Nah","Hab","Zeph","Hag","Zech","Mal"]
ALL = OT + NT

COVERS = {
    'adeney-expositor-s-bible-the-song-of-solomon-and-the-lamentations-of-jeremiah.md': ["Song","Lam"],
    'alexander-expositor-s-bible-the-epistles-of-st-john.md': ["1John","2John","3John"],
    'aquinas-catena-aurea-gospel-of-matthew.md': ["Matt"],
    'aquinas-catena-aurea-gospel-of-mark.md': ["Mark"],
    'ball-expositor-s-bible-the-prophecies-of-jeremiah-volume-i.md': ["Jer"],
    'barnes-barnes-new-testament-notes.md': NT,
    'bennett-expositor-s-bible-the-book-of-jeremiah-volume-ii.md': ["Jer"],
    'bennett-expositor-s-bible-the-books-of-chronicles.md': ["1Chr","2Chr"],
    'blaikie-expositor-s-bible-the-book-of-joshua.md': ["Josh"],
    'blaikie-expositor-s-bible-the-first-book-of-samuel.md': ["1Sam"],
    'blaikie-expositor-s-bible-the-second-book-of-samuel.md': ["2Sam"],
    'burton-expositor-s-bible-the-gospel-according-to-st-luke.md': ["Luke"],
    'calvin-commentaries-on-the-catholic-epistles.md': ["Jas","1Pet","2Pet","1John","2John","3John","Jude"],
    'calvin-commentary-on-acts-volume-1.md': ["Acts"],
    'calvin-commentary-on-acts-volume-2.md': ["Acts"],
    'calvin-commentary-on-corinthians-volume-1.md': ["1Cor"],
    'calvin-commentary-on-corinthians-volume-2.md': ["2Cor"],
    'calvin-commentary-on-daniel-volume-1.md': ["Dan"],
    'calvin-commentary-on-daniel-volume-2.md': ["Dan"],
    'calvin-commentary-on-ezekiel-volume-1.md': ["Ezek"],
    'calvin-commentary-on-ezekiel-volume-2.md': ["Ezek"],
    'calvin-commentary-on-galatians-and-ephesians.md': ["Gal","Eph"],
    'calvin-commentary-on-genesis-volume-1.md': ["Gen"],
    'calvin-commentary-on-genesis-volume-2.md': ["Gen"],
    'calvin-commentary-on-habakkuk-zephaniah-haggai.md': ["Hab","Zeph","Hag"],
    'calvin-commentary-on-hebrews.md': ["Heb"],
    'calvin-commentary-on-hosea.md': ["Hos"],
    'calvin-commentary-on-isaiah-volume-1.md': ["Isa"],
    'calvin-commentary-on-isaiah-volume-2.md': ["Isa"],
    'calvin-commentary-on-isaiah-volume-3.md': ["Isa"],
    'calvin-commentary-on-isaiah-volume-4.md': ["Isa"],
    'calvin-commentary-on-jeremiah-and-lamentations-volume-1.md': ["Jer","Lam"],
    'calvin-commentary-on-jeremiah-and-lamentations-volume-2.md': ["Jer","Lam"],
    'calvin-commentary-on-jeremiah-and-lamentations-volume-3.md': ["Jer","Lam"],
    'calvin-commentary-on-jeremiah-and-lamentations-volume-4.md': ["Jer","Lam"],
    'calvin-commentary-on-jeremiah-and-lamentations-volume-5.md': ["Jer","Lam"],
    'calvin-commentary-on-joel-amos-obadiah.md': ["Joel","Amos","Obad"],
    'calvin-commentary-on-john-volume-1.md': ["John"],
    'calvin-commentary-on-john-volume-2.md': ["John"],
    'calvin-commentary-on-jonah-micah-nahum.md': ["Jonah","Mic","Nah"],
    'calvin-commentary-on-joshua.md': ["Josh"],
    'calvin-commentary-on-matthew-mark-luke-volume-1.md': ["Matt","Mark","Luke"],
    'calvin-commentary-on-matthew-mark-luke-volume-3.md': ["Matt","Mark","Luke"],
    'calvin-commentary-on-philippians-colossians-and-thessalonians.md': ["Phil","Col","1Thess","2Thess"],
    'calvin-commentary-on-psalms-volume-1.md': ["Ps"],
    'calvin-commentary-on-psalms-volume-2.md': ["Ps"],
    'calvin-commentary-on-psalms-volume-3.md': ["Ps"],
    'calvin-commentary-on-psalms-volume-4.md': ["Ps"],
    'calvin-commentary-on-psalms-volume-5.md': ["Ps"],
    'calvin-commentary-on-romans.md': ["Rom"],
    'calvin-commentary-on-timothy-titus-philemon.md': ["1Tim","2Tim","Titus","Phlm"],
    'calvin-commentary-on-zechariah-malachi.md': ["Zech","Mal"],
    'calvin-harmony-of-the-law-volume-2.md': ["Exod","Lev","Num","Deut"],
    'calvin-harmony-of-the-law-volume-4.md': ["Exod","Lev","Num","Deut"],
    'chadwick-expositor-s-bible-the-book-of-exodus.md': ["Exod"],
    'chadwick-expositor-s-bible-the-gospel-according-to-st-mark.md': ["Mark"],
    'cox-expositor-s-bible-the-book-of-ecclesiastes.md': ["Eccl"],
    'dick-lectures-on-the-acts-of-the-apostles.md': ["Acts"],
    'denney-expositor-s-bible-the-epistles-to-the-thessalonians.md': ["1Thess","2Thess"],
    'denney-expositor-s-bible-the-second-epistle-to-the-corinthians.md': ["2Cor"],
    'dods-expositor-s-bible-the-book-of-genesis.md': ["Gen"],
    'dods-expositor-s-bible-the-first-epistle-to-the-corinthians.md': ["1Cor"],
    'dods-expositor-s-bible-the-gospel-of-st-john-volume-i.md': ["John"],
    'dods-expositor-s-bible-the-gospel-of-st-john-volume-ii.md': ["John"],
    'edwards_tc-expositor-s-bible-the-epistle-to-the-hebrews.md': ["Heb"],
    'farrar-expositor-s-bible-the-book-of-daniel.md': ["Dan"],
    'farrar-expositor-s-bible-the-first-book-of-kings.md': ["1Kgs"],
    'farrar-expositor-s-bible-the-second-book-of-kings.md': ["2Kgs"],
    'findlay-expositor-s-bible-the-epistle-to-the-ephesians.md': ["Eph"],
    'findlay-expositor-s-bible-the-epistle-to-the-galatians.md': ["Gal"],
    'gibson-expositor-s-bible-the-gospel-of-st-matthew.md': ["Matt"],
    'gill-exposition-of-the-book-of-solomon-s-song.md': ["Song"],
    'gray_jm-christian-workers-commentary-on-the-old-and-new-testaments.md': ALL,
    'guyon-song-of-songs-of-solomon-explanations-and-reflections-having-reference-to-the-interior-life.md': ["Song"],
    'harper-expositor-s-bible-the-book-of-deuteronomy.md': ["Deut"],
    'henry-commentary-on-the-whole-bible-volume-i-genesis-to-deuteronomy.md': ["Gen","Exod","Lev","Num","Deut"],
    'henry-commentary-on-the-whole-bible-volume-ii-joshua-to-esther.md': ["Josh","Judg","Ruth","1Sam","2Sam","1Kgs","2Kgs","1Chr","2Chr","Ezra","Neh","Esth"],
    'henry-commentary-on-the-whole-bible-volume-iii-job-to-song-of-solomon.md': ["Job","Ps","Prov","Eccl","Song"],
    'henry-commentary-on-the-whole-bible-volume-iv-isaiah-to-malachi.md': ["Isa","Jer","Lam","Ezek","Dan","Hos","Joel","Amos","Obad","Jonah","Mic","Nah","Hab","Zeph","Hag","Zech","Mal"],
    'henry-commentary-on-the-whole-bible-volume-v-matthew-to-john.md': ["Matt","Mark","Luke","John"],
    'henry-commentary-on-the-whole-bible-volume-vi-acts-to-revelation.md': NT[4:],
    'henry-matthew-henry-s-concise-commentary-on-the-bible.md': ALL,
    'hodge-commentary-on-the-epistle-to-the-ephesians.md': ["Eph"],
    'hort-epistle-of-st-james-greek-text-with-introduction-commentary-as-far-as-chapter-iv-verse-7-and-additional-notes.md': ["Jas 1–4:7"],
    'horton-expositor-s-bible-the-book-of-proverbs.md': ["Prov"],
    'jamieson-commentary-critical-and-explanatory-on-the-whole-bible.md': ALL,
    'johnson_bw-new-testament-commentary-vol-iii-john.md': ["John"],
    'johnson_bw-people-s-new-testament.md': NT,
    'jowett-epistles-of-st-peter.md': ["1Pet","2Pet"],
    'kellogg-expositor-s-bible-the-book-of-leviticus.md': ["Lev"],
    'leupold-exposition-of-genesis-volumes-1-and-2.md': ["Gen"],
    'lumby-expositor-s-bible-the-epistles-of-st-peter.md': ["1Pet","2Pet"],
    'luther-commentary-on-st-paul-s-epistle-to-the-galatians.md': ["Gal"],
    'maclaren-expositor-s-bible-colossians-and-philemon.md': ["Col","Phlm"],
    'maclaren-expositor-s-bible-the-psalms-volume-i.md': ["Ps"],
    'maclaren-expositor-s-bible-the-psalms-volume-ii.md': ["Ps"],
    'maclaren-expositor-s-bible-the-psalms-volume-iii.md': ["Ps"],
    'mcgarvey-commentary-on-acts-of-the-apostles.md': ["Acts"],
    'mcgarvey-four-fold-gospel.md': ["Matt","Mark","Luke","John"],
    'meyer-way-into-the-holiest.md': ["Heb"],
    'milligan-expositor-s-bible-the-book-of-revelation.md': ["Rev"],
    'moffat-general-epistles-james-peter-and-judas.md': ["Jas","1Pet","2Pet","Jude"],
    'moule-expositor-s-bible-the-epistle-of-st-paul-to-the-romans.md': ["Rom"],
    'newell-romans-verse-by-verse.md': ["Rom"],
    'plummer-expositor-s-bible-the-general-epistles-of-st-james-and-st-jude.md': ["Jas","Jude"],
    'plummer-expositor-s-bible-the-pastoral-epistles.md': ["1Tim","2Tim","Titus"],
    'rainy-expositor-s-bible-the-epistle-to-the-philippians.md': ["Phil"],
    'robertson_at-word-pictures-in-the-new-testament.md': NT,
    'ryle-expository-thoughts-on-matthew.md': ["Matt"],
    'schaff-npnf1-08-st-augustine-exposition-on-the-book-of-psalms.md': ["Ps"],
    'skinner-expositor-s-bible-the-book-of-ezekiel.md': ["Ezek"],
    'smith_ga-expositor-s-bible-the-book-of-isaiah-volume-i.md': ["Isa"],
    'smith_ga-expositor-s-bible-the-book-of-isaiah-volume-ii.md': ["Isa"],
    'smith_ga-expositor-s-bible-the-book-of-the-twelve-prophets-volume-i.md': ["Hos","Joel","Amos","Obad","Jonah","Mic"],
    'stokes-expositor-s-bible-the-acts-of-the-apostles-volume-i.md': ["Acts"],
    'stokes-expositor-s-bible-the-acts-of-the-apostles-volume-ii.md': ["Acts"],
    'trench-epistles-to-the-seven-churches-in-asia.md': ["Rev 2–3"],
    'watson-beatitudes-an-exposition-of-matthew-5-1-12.md': ["Matt 5:1–12"],
    'watson_ra-expositor-s-bible-judges-and-ruth.md': ["Judg","Ruth"],
    'watson_ra-expositor-s-bible-the-book-of-job.md': ["Job"],
    'watson_ra-expositor-s-bible-the-book-of-numbers.md': ["Num"],
    'wesley-wesley-s-notes-on-the-bible.md': ALL,
    'white-acts-of-the-apostles.md': ["Acts"],
    # Maclaren Expositions (genre: sermon) — coverage by volume title
    'maclaren-expositions-of-holy-scripture-deuteronomy-joshua-judges-ruth-and-first-book-of-samuel-second-samuel-first-kings-and-second-kings-chapters.md': ["Deut","Josh","Judg","Ruth","1Sam","2Sam","1Kgs","2Kgs"],
    'maclaren-expositions-of-holy-scripture-ezekiel-daniel-and-the-minor-prophets-and-matthew-chaps-i-to-viii.md': ["Ezek","Dan","Hos","Joel","Amos","Obad","Jonah","Mic","Nah","Hab","Zeph","Hag","Zech","Mal","Matt"],
    'maclaren-expositions-of-holy-scripture-genesis-exodus-leviticus-and-numbers.md': ["Gen","Exod","Lev","Num"],
    'maclaren-expositions-of-holy-scripture-isaiah-and-jeremiah.md': ["Isa","Jer"],
    'maclaren-expositions-of-holy-scripture-luke.md': ["Luke"],
    'maclaren-expositions-of-holy-scripture-mark.md': ["Mark"],
    'maclaren-expositions-of-holy-scripture-matthew-ix-to-xviii.md': ["Matt"],
    'maclaren-expositions-of-holy-scripture-psalms.md': ["Ps"],
    'maclaren-expositions-of-holy-scripture-romans-and-corinthians.md': ["Rom","1Cor","2Cor"],
    'maclaren-expositions-of-holy-scripture-st-john-ch-i-to-xiv.md': ["John"],
    'maclaren-expositions-of-holy-scripture-st-john-chs-xv-to-xxi.md': ["John"],
    'maclaren-expositions-of-holy-scripture-the-acts.md': ["Acts"],
    'maclaren-expositions-of-the-holy-scriptures-second-kings-from-chap-viii-and-chronicles-ezra-and-nehemiah-esther-job-proverbs-and-ecclesiastes.md': ["2Kgs","1Chr","2Chr","Ezra","Neh","Esth","Job","Prov","Eccl"],
}
# Maclaren Expositions volumes are sermons, not commentaries
for n in list(COVERS):
    if n.startswith('maclaren-expositions-'):
        GENRE_OVERRIDE[n] = 'sermon'


def tag(path):
    text = path.read_text()
    prefix = path.name.split('-', 1)[0]
    trad = TRADITION.get(prefix)
    if not trad:
        return f'no tradition mapping for prefix {prefix}'
    genre = GENRE_OVERRIDE.get(path.name, 'commentary')
    add = f'tradition: "{trad}"\ngenre: "{genre}"'
    if path.name in COVERS:
        books = ', '.join('"%s"' % b for b in COVERS[path.name])
        add += f'\ncovers: [{books}]'
    new, n = re.subn(r'(?m)^(author:.*)$', rf'\1\n{add}', text, count=1)
    if n != 1:
        return 'no author line'
    path.write_text(new)
    return None


def main():
    if len(sys.argv) > 1:
        files = [DOC / f for f in sys.argv[1:]]
    else:
        files = [p for p in sorted(DOC.glob('*.md'))
                 if 'tradition:' not in
                 p.read_text().split('---', 2)[1]]
    problems = []
    for p in files:
        err = tag(p)
        if err:
            problems.append(f'{p.name}: {err}')
    print(f'tagged {len(files) - len(problems)}/{len(files)} docs')
    for x in problems:
        print('PROBLEM:', x)
    missing_cov = [p.name for p in files
                   if GENRE_OVERRIDE.get(p.name, 'commentary') == 'commentary'
                   and p.name not in COVERS]
    for x in missing_cov:
        print('commentary missing covers:', x)


if __name__ == '__main__':
    main()
