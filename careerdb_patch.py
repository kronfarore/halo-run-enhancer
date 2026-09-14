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
shipped values back.
"""
import os
import re
import shutil

CAREERDB_REL = os.path.join('data', 'careerdb', 'careerdb.xml')
TIME_ATTRS = ('par_time', 'average_time', 'max_time')
# careerdb's per-game element names
XML_GAME = {'Halo 1': 'Halo1', 'Halo 2': 'Halo2', 'Halo 3': 'Halo3',
            'Halo 3: ODST': 'Halo3ODST', 'Halo Reach': 'HaloReach', 'Halo 4': 'Halo4'}


def backup_path(path):
    return path + '.bak'


def read_baseline(path):
    bak = backup_path(path)
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
    with open(bak, encoding='utf-8') as f:
        return f.read()


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
        with open(hp, 'w', encoding='utf-8') as f:
            json.dump(hist, f)


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


def apply(path, game, mission_name, factor, dry_run=False):
    """Scale one mission's three times by `factor`, from the pristine baseline.

    Returns {'old': {...}, 'new': {...}} or None when the mission has no par time (the
    ODST hub, Halo 4's Spartan Ops entries)."""
    base = read_baseline(path)
    span = chapter_span(base, game, mission_name)
    if span is None:
        if not dry_run:
            with open(path, 'w', encoding='utf-8', newline='') as f:
                f.write(base)                     # any earlier mission's edit goes away
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
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(base[:span[0]] + chunk + base[span[1]:])
        title = re.search(r'\btitle="([^"]+)"', chunk)
        if title and all(k in new for k in TIME_ATTRS):
            _remember(path, title.group(1), tuple(float(new[k]) for k in TIME_ATTRS))
    return {'old': old, 'new': new}


def restore(path):
    bak = backup_path(path)
    if os.path.exists(bak):
        shutil.copy2(bak, path)
        return True
    return False
