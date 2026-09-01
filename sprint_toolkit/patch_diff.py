r"""Compare two patches of the same level — the co-op desync tool.

The patch code already tells you THAT two machines disagree. It is printed on both
screens and comparing two short strings needs no tool. What it cannot tell you is
what actually differs, which is the only thing you can act on. So this leads with
the differences themselves, named and explained, and keeps the raw tables behind
--detail for when you want to read every row yourself.

Each finding says what differs, on which side, and — where the data supports it —
why, because the same visible symptom has several causes that need different fixes:

  a different LEVEL, DIFFICULTY or TOOL VERSION invalidates everything below it.
        Two patches of different levels have nothing meaningful to compare, and a
        different tool version can compute a different value from the same typed
        operator, which shows up as a value difference with no visible cause.

  a card DRAFTED ON ONE SIDE ONLY is a run-state problem, not a patch problem:
        different cards drawn, a card blacklisted on one machine, options set
        differently. Fix it in the run, not in the map.

  the SAME EDIT LANDING ON DIFFERENT VALUES splits by whether the ORIGINAL values
        agree. If the two maps started from different numbers, one of them was
        patched over an already-patched map instead of from its .bak, and every
        multiplier on it has compounded. If they started from the same number and
        ended somewhere else, the operator or the magnitude differed.

  an edit that FAILED or was SKIPPED on one side leaves that field vanilla there
        and modified here — the tag was missing from that map, so the two maps
        disagree even though both machines planned the same thing.

WHAT IS NOT COMPARED
    Timestamps, absolute paths and the backup path: those differ between two
    machines by definition. Ordering is ignored too — a plan is a set, not a
    sequence.

USAGE
    python sprint_toolkit/patch_diff.py mine.json theirs.json
    python sprint_toolkit/patch_diff.py --mission l300     # the latest two locally
    python sprint_toolkit/patch_diff.py a.json b.json --detail   # full tables too
"""
import argparse
import glob
import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_TOOL = os.path.dirname(_HERE)
sys.path.insert(0, _TOOL)

PATCH_DIR = os.path.join(_TOOL, 'patches')


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def result_key(r):
    """What identifies a written value across two machines.

    The tag matters as much as the field: one effect can write the same field on
    several tags, and 'which tag' is exactly the kind of difference that desyncs."""
    return (str(r.get('effect', '')), str(r.get('tag', '')), str(r.get('field', '')))


def plan_ops(patch):
    """{(tag, field, block): operator} for every planned edit."""
    out = {}
    for _cls, items in (patch.get('groups') or {}).items():
        for item in items:
            for op in item.get('ops') or []:
                out[(item.get('tag'), op.get('field'), op.get('block'))] = \
                    op.get('op_str', '')
    return out


def state(r):
    """'wrote' / 'failed' / 'skipped' / 'missing' for one result row."""
    if r is None:
        return 'missing'
    if not r.get('ok'):
        return 'failed'
    if r.get('skip'):
        return 'skipped'
    return 'wrote'


def why(r):
    return str(r.get('reason') or '?') if r is not None else ''


def _n(v):
    """Numbers compare loosely — a value round-tripped through JSON on one machine
    and through a float on the other must not read as a difference."""
    try:
        return round(float(v), 6)
    except (TypeError, ValueError):
        return v


def _s(v):
    return '(none)' if v is None else str(v)


class Findings(object):
    """Differences in the order they should be READ, not the order they are found.

    A level mismatch makes every value difference below it meaningless, so severity
    ordering is not cosmetic here — it stops you chasing a hundred value rows that
    are all explained by the first line."""

    ORDER = ('BLOCKING', 'PLAN', 'VALUE', 'MISSED')

    def __init__(self):
        self.items = []

    def add(self, sev, headline, detail=None, cause=None):
        self.items.append((sev, headline, detail, cause))

    def by_severity(self):
        for sev in self.ORDER:
            rows = [i for i in self.items if i[0] == sev]
            if rows:
                yield sev, rows

    def __len__(self):
        return len(self.items)


HEADINGS = {
    'BLOCKING': 'These two patches are not comparable',
    'PLAN': 'Planned on one machine only',
    'VALUE': 'Same edit, different value in the map',
    'MISSED': 'Edit did not land on one machine',
}


def collect(a, b, na, nb):
    f = Findings()

    # ---- identity: a mismatch here explains everything under it ------------
    for key, label in (('map', 'level'), ('target_difficulty', 'difficulty'),
                       ('tool_version', 'tool version')):
        va, vb = a.get(key), b.get(key)
        if key == 'map':
            va, vb = os.path.basename(str(va)), os.path.basename(str(vb))
        if va == vb:
            continue
        cause = None
        if key == 'map':
            cause = ('Different levels. Nothing below this line means anything until '
                     'you compare two patches of the same map.')
        elif key == 'target_difficulty':
            cause = ('Every difficulty-flavoured field writes a different slot, so '
                     'most value differences below are just this.')
        else:
            cause = ('Different tool versions can compute different values from the '
                     'same typed operator. Update the older side and re-patch.')
        f.add('BLOCKING', '%s: %s = %s, %s = %s' % (label, na, _s(va), nb, _s(vb)),
              cause=cause)

    # ---- plan: which edits each machine intended ---------------------------
    pa, pb = plan_ops(a), plan_ops(b)
    if pa and pb:
        for k in sorted(set(pa) - set(pb)):
            f.add('PLAN', '%s only: %s  %s  %s' % (na, k[1], pa[k], k[0]))
        for k in sorted(set(pb) - set(pa)):
            f.add('PLAN', '%s only: %s  %s  %s' % (nb, k[1], pb[k], k[0]))
        for k in sorted(k for k in set(pa) & set(pb) if pa[k] != pb[k]):
            f.add('PLAN', 'different operator on %s' % k[1],
                  detail='%s = %s     %s = %s   (%s)' % (na, pa[k], nb, pb[k], k[0]),
                  cause='Same field, different magnitude — a card at a different '
                        'level, or a hand-edited value.')

    # ---- outcome: what is actually in the two maps -------------------------
    ra = {result_key(r): r for r in (a.get('results') or [])}
    rb = {result_key(r): r for r in (b.get('results') or [])}
    agree = 0
    for k in sorted(set(ra) | set(rb)):
        x, y = ra.get(k), rb.get(k)
        sx, sy = state(x), state(y)
        eff, tag, fld = k
        name = '%s / %s' % (eff, fld) if eff else fld

        if sx == 'wrote' and sy == 'wrote':
            if _n(x.get('new')) == _n(y.get('new')):
                agree += 1
                continue
            same_start = _n(x.get('old')) == _n(y.get('old'))
            f.add('VALUE', name,
                  detail=['%s: %s -> %s' % (na, _s(x.get('old')), _s(x.get('new'))),
                          '%s: %s -> %s' % (nb, _s(y.get('old')), _s(y.get('new')))],
                  cause=None if same_start else
                        'The two maps started from DIFFERENT original values — one of '
                        'them was patched over an already-patched map instead of from '
                        'its .bak. Restore that side and re-patch.')
            continue

        if sx == 'wrote' or sy == 'wrote':
            good, bad, gn, bn = ((x, y, na, nb) if sx == 'wrote' else (y, x, nb, na))
            bs = state(bad)
            f.add('MISSED', name,
                  detail='%s wrote %s;  %s %s'
                         % (gn, _s(good.get('new')), bn,
                            'has no such row' if bs == 'missing'
                            else '%s (%s)' % (bs, why(bad))),
                  cause='That field is still vanilla on %s and modified on %s — the '
                        'two maps genuinely disagree.' % (bn, gn))
            continue
        agree += 1                       # both failed or both skipped: consistent

    return f, (len(ra), len(rb), agree), (pa, pb)


def report(f, counts, plans, na, nb, detail=False, a=None, b=None):
    nra, nrb, agree = counts
    print('=' * 78)
    if not len(f):
        print('NO DIFFERENCES.')
        print('  Same level, same plan, same values in both maps (%d written row(s)).'
              % nra)
        print('  If you still desynced, it is not the patch: check the dll patches, '
              'which .map')
        print('  files each machine actually loaded, and whether one side started on '
              'an old map.')
        return 0
    print('WHAT DIFFERS   %d finding(s)' % len(f))
    print('  %s = %s' % (na, os.path.basename(str((a or {}).get('map', '?')))))
    print('  %s = %s' % (nb, os.path.basename(str((b or {}).get('map', '?')))))
    for sev, rows in f.by_severity():
        print()
        print('%s  (%d)' % (HEADINGS[sev], len(rows)))
        print('-' * 78)
        for _sev, headline, det, cause in rows:
            print('  * %s' % headline)
            for line in ([det] if isinstance(det, str) else (det or [])):
                # a long value reads as two labelled lines rather than one that
                # runs off the terminal and hides the second machine entirely
                for part in _wrap(line, 70) or ['']:
                    print('      %s' % part)
            if cause:
                for line in _wrap(cause, 70):
                    print('      %s' % line)
    print()
    print('-' * 78)
    print('%d row(s) here, %d there, %d agree' % (nra, nrb, agree))
    if detail:
        _tables(plans, a, b, na, nb)
    return len(f)


def _wrap(text, width):
    out, line = [], ''
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            out.append(line)
            line = word
        else:
            line = (line + ' ' + word).strip()
    if line:
        out.append(line)
    return out


def _tables(plans, a, b, na, nb):
    pa, pb = plans
    print()
    print('=' * 78)
    print('FULL PLAN')
    for label, p in ((na, pa), (nb, pb)):
        print('  %s — %d planned edit(s)' % (label, len(p)))
        for k in sorted(p):
            print('     %-28s %-14s %s' % (str(k[1])[:28], p[k], k[0]))
    print()
    print('=' * 78)
    print('FULL OUTCOME')
    for label, patch in ((na, a), (nb, b)):
        rows = patch.get('results') or []
        print('  %s — %d row(s)' % (label, len(rows)))
        for r in rows:
            print('     %-9s %-30s %s -> %s   %s'
                  % (state(r), ('%s / %s' % (r.get('effect', ''),
                                             r.get('field', '')))[:30],
                     _s(r.get('old')), _s(r.get('new')), r.get('tag', '')))


def compare_text(a, b, na='A', nb='B', detail=False):
    """The whole report as a string, for callers with no terminal.

    The GUI needs exactly what the CLI prints, so it must not grow a second
    implementation that drifts -- both go through here."""
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        f, counts, plans = collect(a, b, na, nb)
        n = report(f, counts, plans, na, nb, detail, a, b)
    return buf.getvalue(), n


def compare_files(path_a, path_b, na=None, nb=None, detail=False):
    """Load two patch logs and compare them. Returns (text, difference count)."""
    a, b = load(path_a), load(path_b)
    return compare_text(a, b, na or 'A', nb or 'B', detail)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('files', nargs='*', help='two patch .json files')
    ap.add_argument('--mission',
                    help='compare the two most recent local patches of a level')
    ap.add_argument('--detail', action='store_true',
                    help='print the full plan and outcome tables as well')
    ap.add_argument('--all', dest='detail', action='store_true',
                    help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.mission:
        found = sorted(glob.glob(os.path.join(PATCH_DIR,
                                              'patch_%s_*.json' % args.mission)))
        if len(found) < 2:
            print('need two local patches of %s; found %d in %s'
                  % (args.mission, len(found), PATCH_DIR))
            return 1
        files = found[-2:]
    elif len(args.files) == 2:
        files = args.files
    else:
        ap.print_usage()
        return 2

    for fn in files:
        if not os.path.exists(fn):
            print('no such file: %s' % fn)
            return 1
    a, b = load(files[0]), load(files[1])
    print('  A = %s' % files[0])
    print('  B = %s' % files[1])
    ca, cb = a.get('patch_code'), b.get('patch_code')
    print('  patch code   A %s    B %s' % (ca, cb))
    print()
    f, counts, plans = collect(a, b, 'A', 'B')
    return 1 if report(f, counts, plans, 'A', 'B', args.detail, a, b) else 0


if __name__ == '__main__':
    sys.exit(main())
