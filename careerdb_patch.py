"""Scale a mission's par time in MCC's <mcc_root>\\data\\careerdb\\careerdb.xml.

Every game's campaign par times live in this one file -- one <Chapter> per mission, with
par_time / average_time / max_time in seconds (Halo 1's Pillar of Autumn: 900 / 1800 /
2400). Halo 1 and Halo 2 have no scenario-side metagame at all, so for them this file is
the whole definition. From Halo 3 on the scenario ALSO carries Time Bonuses, which
halo_patch._scale_par_time scales in the map; careerdb's par_time equals the first of
those thresholds (ONI Sword Base 600 s = its 10-minute bonus).

MCC reads the file ONCE at startup (CareerDB::init), exactly like scoredb.xml, so a
change takes effect at the next MCC start.

The same baseline model as scoredb_patch: the pristine file is kept as <file>.bak and
every apply scales FROM it, so re-patching never compounds and a scale of 1 puts the
shipped values back -- byte for byte: the file is read with its line endings kept and
written atomically (mcc_textfile; MCC reads it once at startup, so a half-written file
would be the par times of a whole session).

The stock copy is not trusted forever (review U4 C1): mcc_textfile.guard() compares the live
file with the .bak and with this tool's last write (<file>.bak.meta); a file that is neither
-- an MCC update shipped a new careerdb.xml, a Steam verify put one back -- is taken as the
new stock copy (the .bak is refreshed from it, the caller's row says so) instead of being
rewritten from the old one on every patch. There is no pristine test for this file: its
structure (every attribute but the three times) is the test.
"""
import os
import re
import shutil

import mcc_textfile          # atomic writes, line endings kept (review U4 B9 / N7)

CAREERDB_REL = os.path.join('data', 'careerdb', 'careerdb.xml')
TIME_ATTRS = ('par_time', 'average_time', 'max_time')
# careerdb's per-game element names
XML_GAME = {'Halo 1': 'Halo1', 'Halo 2': 'Halo2', 'Halo 3': 'Halo3',
            'Halo 3: ODST': 'Halo3ODST', 'Halo Reach': 'HaloReach', 'Halo 4': 'Halo4'}


def backup_path(path):
    return path + '.bak'


_TIME_VAL = re.compile(r'(\b(?:par_time|average_time|max_time)\s*=\s*")[^"]*(")')


def _skeleton(text):
    """The file with the three times blanked and whitespace folded: what this tool's own
    writes never change (mcc_textfile.guard)."""
    return re.sub(r'\s+', ' ', _TIME_VAL.sub(r'\1\2', text)).strip()


def read_baseline(path, notes=None):
    bak = backup_path(path)
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
        mcc_textfile.record_bak(bak)
    else:
        mcc_textfile.guard(path, bak, _skeleton, None, 'careerdb.xml', notes)
    return mcc_textfile.read_text(bak)


def history_path(path):
    """Every chapter state this module has written -- sprint_toolkit/careerdb_live needs
    them all, because MCC holds whatever the file said when it last STARTED."""
    return path + '.history.json'


def chapter_times(text):
    """{title: (par, average, max)} for every chapter carrying all three times."""
    out = {}
    for tag in re.finditer(r'<Chapter\b([^>]*)>', text, re.S):
        a = dict(re.findall(r'(\w+)="([^"]*)"', tag.group(1)))
        if a.get('title') and all(a.get(k) for k in TIME_ATTRS) \
                and float(a['par_time']) > 0:
            out[a['title']] = tuple(float(a[k]) for k in TIME_ATTRS)
    return out


def _remember(path, title, times):
    import json
    hp = history_path(path)
    try:
        with open(hp, encoding='utf-8') as f:
            hist = json.load(f)
    except Exception:
        hist = {}
    rows = hist.setdefault(title, [])
    if list(times) not in rows:
        rows.append(list(times))
        mcc_textfile.write_text_atomic(hp, json.dumps(hist))


def known_triplets(path):
    """{title: {(par, avg, max)}} -- every value MCC could be holding right now: the
    pristine file, the current file, and each state written since."""
    import json
    out = {}
    for src in (backup_path(path), path):
        if os.path.exists(src):
            with open(src, encoding='utf-8') as f:
                for title, t in chapter_times(f.read()).items():
                    out.setdefault(title, set()).add(t)
    try:
        with open(history_path(path), encoding='utf-8') as f:
            for title, rows in json.load(f).items():
                out.setdefault(title, set()).update(tuple(r) for r in rows)
    except Exception:
        pass
    return out


def _norm(s):
    s = re.sub(r'[^a-z0-9]', '', (s or '').lower())
    return s[3:] if s.startswith('the') else s


def _game_span(text, game):
    """(start, end) of this game's element in the file."""
    tag = XML_GAME.get(str(game).strip())
    if not tag:
        return None
    m = re.search(r'<%s>(.*?)</%s>' % (tag, tag), text, re.S)
    return (m.start(1), m.end(1)) if m else None


def chapter_span(text, game, mission_name):
    """(start, end) of the <Chapter .../> carrying par times for this mission, matched by
    name against its builtInMapId (_map_id_halo2_the_oracle <- "Oracle")."""
    span = _game_span(text, game)
    if not span:
        return None
    want = _norm(mission_name)
    hits = []
    # The START tag only: Halo 1 and 2 write <Chapter .../>, but from Halo 3 on a
    # chapter has child elements, so a self-closing pattern skipped every one of them.
    for m in re.finditer(r'<Chapter\b[^>]*>', text[span[0]:span[1]], re.S):
        body = m.group(0)
        mid = re.search(r'builtInMapId="_map_id_[a-z0-9]+?_([^"]+)"', body)
        if mid and 'par_time=' in body:
            n = _norm(mid.group(1))
            if n == want:
                return span[0] + m.start(), span[0] + m.end()
            if want and want in n:
                hits.append((span[0] + m.start(), span[0] + m.end()))
    return hits[0] if len(hits) == 1 else None


def apply(path, game, mission_name, factor, dry_run=False, notes=None):
    """Scale one mission's three times by `factor`, from the pristine baseline.

    Returns {'old': {...}, 'new': {...}} or None when the mission has no par time (the
    ODST hub, Halo 4's Spartan Ops entries). `notes` (a list) receives a line when the
    stock copy had to be refreshed first."""
    base = read_baseline(path, notes)
    span = chapter_span(base, game, mission_name)
    if span is None:
        if not dry_run:
            mcc_textfile.write_text_atomic(path, base)   # any earlier mission's edit goes away
            mcc_textfile.record_write(path, backup_path(path))
        return None
    chunk = base[span[0]:span[1]]
    old, new = {}, {}

    def scale(m):
        v = float(m.group(2))
        old[m.group(1)] = int(v)
        new[m.group(1)] = int(round(v * factor))
        return '%s="%d"' % (m.group(1), new[m.group(1)])
    chunk = re.sub(r'\b(%s)="(\d+(?:\.\d+)?)"' % '|'.join(TIME_ATTRS), scale, chunk)
    if not dry_run:
        mcc_textfile.write_text_atomic(path, base[:span[0]] + chunk + base[span[1]:])
        mcc_textfile.record_write(path, backup_path(path))
        title = re.search(r'\btitle="([^"]+)"', chunk)
        if title and all(k in new for k in TIME_ATTRS):
            _remember(path, title.group(1), tuple(float(new[k]) for k in TIME_ATTRS))
    return {'old': old, 'new': new}


def restore(path):
    """The stock copy back into place: 'restored', or 'refreshed' when the live file turned
    out to be a NEWER stock file (it then IS the stock copy; nothing to put back), or False
    with no .bak."""
    bak = backup_path(path)
    if not os.path.exists(bak):
        return False
    if mcc_textfile.guard(path, bak, _skeleton, None, 'careerdb.xml') == 'refreshed':
        return 'refreshed'
    mcc_textfile.copy_atomic(bak, path)
    mcc_textfile.record_write(path, bak)
    return 'restored'
