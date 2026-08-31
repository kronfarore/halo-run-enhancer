r"""Compare two patches of the same level — the co-op desync tool.

WHAT LEVEL TO COMPARE AT
------------------------
Three levels exist and they answer different questions. This reports all three,
because a desync narrows down by which of them disagrees:

  1. IDENTITY   same level, same difficulty, same tool version?
                A different tool version can compute a different value from the same
                typed operator, and that is invisible at every other level.

  2. INTENT     did both machines PLAN the same edits — same tag, same field, same
                operator? A difference here is a run-state problem: different cards
                drafted, a card blacklisted on one side, options set differently.

  3. OUTCOME    did the same edits LAND on the same values? This is the one that
                actually desyncs a session, because it is the bytes in the .map.
                Two machines can plan identically and still land differently: a map
                patched from a dirty baseline rather than its .bak compounds, and an
                effect skipped on one side because a tag was absent leaves that
                field vanilla there and modified here.

The patch code in each file is a summary of level 3 only. When the codes match, the
maps agree and the desync is NOT the patch — look at loading, at the dll patches, or
at the run itself. When they differ, this says exactly where.

WHAT IS NOT COMPARED
--------------------
Timestamps, absolute paths and the backup path: those differ between two machines by
definition and say nothing. Ordering is ignored too — the plan is a set, not a
sequence.

USAGE
    python sprint_toolkit/patch_diff.py mine.json theirs.json
    python sprint_toolkit/patch_diff.py --mission l300        # the latest two locally
    python sprint_toolkit/patch_diff.py a.json b.json --all   # include matching rows
"""
import argparse
import glob
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


def landed(r):
    """The value this row actually left in the map, or None when it wrote nothing."""
    if not r.get('ok') or r.get('skip'):
        return None
    return r.get('new')


def plan_ops(patch):
    """{(tag, field, difficulty-flavour): operator} for every planned edit."""
    out = {}
    for cls, items in (patch.get('groups') or {}).items():
        for item in items:
            for op in item.get('ops') or []:
                key = (item.get('tag'), op.get('field'), op.get('block'))
                out[key] = op.get('op_str', '')
    return out


def _fmt(v, width=34):
    s = '—' if v is None else str(v)
    return s if len(s) <= width else s[:width - 1] + '…'


def compare(a, b, names, show_all=False):
    na, nb = names
    problems = 0

    # ---- 1. identity -------------------------------------------------------
    print('=' * 78)
    print('IDENTITY')
    for key, label in (('map', 'level'), ('target_difficulty', 'difficulty'),
                       ('tool_version', 'tool version')):
        va, vb = a.get(key), b.get(key)
        if key == 'map':
            va, vb = os.path.basename(str(va)), os.path.basename(str(vb))
        same = va == vb
        problems += 0 if same else 1
        print('  %-14s %-28s %-28s %s'
              % (label, _fmt(va, 28), _fmt(vb, 28), 'ok' if same else '<-- DIFFERS'))
    ca, cb = a.get('patch_code'), b.get('patch_code')
    print('  %-14s %-28s %-28s %s'
          % ('patch code', ca, cb, 'MATCH' if ca == cb else '<-- DIFFERS'))
    if ca == cb and ca:
        print()
        print('  The codes match: both maps were written with the same values. If you '
              'still desynced,')
        print('  the cause is not the patch — check the dll patches, the map files '
              'actually loaded,')
        print('  and whether one side was still on an older .map when the session '
              'started.')

    # ---- 2. intent ---------------------------------------------------------
    pa, pb = plan_ops(a), plan_ops(b)
    only_a = sorted(set(pa) - set(pb))
    only_b = sorted(set(pb) - set(pa))
    diff = sorted(k for k in set(pa) & set(pb) if pa[k] != pb[k])
    print()
    print('=' * 78)
    print('INTENT   %d planned edit(s) here, %d there' % (len(pa), len(pb)))
    if not pa or not pb:
        # Patches written before the plan was recorded carry an empty `groups`. Listing
        # every edit as one-sided would read as "the other machine planned nothing",
        # which is the opposite of what an empty groups block means.
        side = na if not pa else nb
        print('  %s recorded no plan (older tool version) — nothing to compare at this'
              % side)
        print('  level. The OUTCOME section below is unaffected and is the one that')
        print('  matters for a desync.')
    elif not (only_a or only_b or diff):
        print('  identical — both machines planned the same edits')
    else:
        for k in only_a:
            print('  only %s: %s  %s  %s' % (na, k[0], k[1], pa[k]))
        for k in only_b:
            print('  only %s: %s  %s  %s' % (nb, k[0], k[1], pb[k]))
        for k in diff:
            print('  operator differs: %s  %s' % (k[0], k[1]))
            print('        %-10s %-14s %-10s %s' % (na, pa[k], nb, pb[k]))
        problems += len(only_a) + len(only_b) + len(diff)

    # ---- 3. outcome --------------------------------------------------------
    ra = {result_key(r): r for r in (a.get('results') or [])}
    rb = {result_key(r): r for r in (b.get('results') or [])}
    keys = sorted(set(ra) | set(rb))
    rows, same_rows = [], 0
    for k in keys:
        x, y = ra.get(k), rb.get(k)
        lx, ly = (landed(x) if x else None), (landed(y) if y else None)
        if x and y and lx == ly:
            same_rows += 1
            if not show_all:
                continue
            rows.append((k, x, y, 'same'))
            continue
        if x is None:
            rows.append((k, None, y, 'only ' + nb))
        elif y is None:
            rows.append((k, x, None, 'only ' + na))
        else:
            rows.append((k, x, y, 'VALUE'))
    print()
    print('=' * 78)
    print('OUTCOME  %d written row(s) here, %d there, %d agree'
          % (len(ra), len(rb), same_rows))
    if not rows:
        print('  every row agrees — the two maps carry the same values')
    else:
        print('  %-9s %-30s %-34s %s' % ('', 'effect / field', na, nb))
        for k, x, y, why in rows:
            if why == 'same':
                continue
            problems += 1
            eff, tag, fld = k
            print('  %-9s %-30s %-34s %s'
                  % (why, _fmt('%s: %s' % (eff, fld), 30),
                     _fmt(_row_text(x)), _fmt(_row_text(y))))
            if tag:
                print('            %s' % tag)
    print()
    print('=' * 78)
    print('%d difference(s)' % problems if problems else 'No differences.')
    return problems


def _row_text(r):
    if r is None:
        return None
    if not r.get('ok'):
        return 'FAILED: %s' % r.get('reason', '?')
    if r.get('skip'):
        return 'skipped: %s' % (r.get('reason') or r.get('new') or '')
    old, new = r.get('old'), r.get('new')
    return '%s -> %s' % (old, new) if old is not None else str(new)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('files', nargs='*', help='two patch .json files')
    ap.add_argument('--mission', help='compare the two most recent local patches of a level')
    ap.add_argument('--all', dest='show_all', action='store_true',
                    help='also count the rows that agree')
    args = ap.parse_args()

    if args.mission:
        found = sorted(glob.glob(os.path.join(PATCH_DIR, 'patch_%s_*.json' % args.mission)))
        if len(found) < 2:
            print('need two local patches of %s; found %d in %s'
                  % (args.mission, len(found), PATCH_DIR))
            return 1
        files = found[-2:]
        print('comparing the two most recent local patches of %s:' % args.mission)
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
    names = [os.path.basename(f).replace('patch_', '')[:18] for f in files]
    print('  A = %s' % files[0])
    print('  B = %s' % files[1])
    print()
    return 1 if compare(a, b, ('A', 'B'), args.show_all) else 0


if __name__ == '__main__':
    sys.exit(main())
