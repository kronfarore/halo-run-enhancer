r"""Kit edit for the 'Tartarus: killable' option (tartarus.py): give 08b's boss loop a
way to end when Tartarus actually dies.

The fight is one (sleep_until (cond ...) 1) in tartarus_boss_fight. Stock, only the
last pinned phase returns TRUE -- the script kills him itself. A Tartarus that can die
(ai_cannot_die flipped at patch time) is never pinned, and once dead his object is
`none`, so the 'not on the platform or the ledge' clause teleports nothing and sleeps
90 ticks, forever: the mission would hang. This adds, as the FIRST clause,

    ((<= (ai_living_count boss_tartarus) 0)  TRUE)

Inert in a stock fight (he cannot die, so he is always living until the script's own
ai_kill, which returns TRUE in the same pass). When it fires, the stock outro runs:
nav point off, ai_kill (a no-op), 'NICE JOB!', fade, erase, cinematic.

    python h2_tartarus_kit.py            # dry run: show the edit
    python h2_tartarus_kit.py --apply    # edit the kit .hsc (backup .tartarus.bak)
    python h2_tartarus_kit.py --revert   # restore the backup
    python h2_tartarus_kit.py --status   # source edited? built map carries it?
Then rebuild + ship:  python h2_rebuild_all.py --maps 08b
"""
import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import h2_tagfield  # noqa: E402

HSC = os.path.join(h2_tagfield.H2EK, 'data', 'scenarios', 'solo', '08b_deltacontrol',
                   'scripts', '08b_deltacontrol_boss.hsc')
BAK = HSC + '.tartarus.bak'
MARK = ';[tartarus] killable Tartarus: his death ends the fight'
# The cond's first stock clause; the new one goes right above it.
ANCHOR = '((volume_test_objects kill_e13_0 (ai_get_object boss_miranda))'
CLAUSE = '((<= (ai_living_count boss_tartarus) 0)\t\t\t\t\t\t\t\t\t\tTRUE)'


def transform(text):
    if MARK in text:
        return text, False
    i = text.find(ANCHOR)
    if i < 0 or text.find(ANCHOR, i + 1) >= 0:
        raise SystemExit('anchor clause not found exactly once in %s' % HSC)
    ls = text.rfind('\n', 0, i) + 1
    indent = text[ls:i]
    nl = '\r\n' if '\r\n' in text else '\n'
    return text[:ls] + indent + MARK + nl + indent + CLAUSE + nl + text[ls:], True


def _read(p):
    with open(p, 'rb') as f:
        return f.read().decode('latin-1')


def _write(p, s):
    with open(p, 'wb') as f:
        f.write(s.encode('latin-1'))


def built_state():
    import halo_patch as HP
    import tartarus as T
    from h2_rebuild_all import LIVE, SUBDIR, baseline_root
    live = os.path.join(LIVE, '08b_deltacontrol.map')
    out = {}
    for label, path in (('live', live),
                        ('baseline', HP.baseline_path(live, baseline_root() or None, SUBDIR))):
        if not path or not os.path.isfile(path):
            out[label] = 'missing  ' + str(path)
            continue
        m = HP.open_map(path, 'Halo 2')
        t = T._tree(m, HP._scnr_base(m), HP._block_base)
        out[label] = ('carries the branch' if t and T.fight_end_branch(t)
                      else 'stock (no branch)') + '  ' + path
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--revert', action='store_true')
    ap.add_argument('--status', action='store_true')
    a = ap.parse_args(argv)
    text = _read(HSC)
    if a.status:
        print('source  :', 'edited' if MARK in text else 'stock', HSC)
        for k, v in built_state().items():
            print('%-8s:' % k, v)
        return 0
    if a.revert:
        if not os.path.isfile(BAK):
            raise SystemExit('no backup at %s' % BAK)
        shutil.copy2(BAK, HSC)
        print('restored', HSC)
        return 0
    new, changed = transform(text)
    if not changed:
        print('already edited:', HSC)
        return 0
    if not a.apply:
        i = new.find(MARK)
        print(new[new.rfind('\n', 0, i - 200):new.find('\n', i + len(MARK) + 200)])
        print('\n(dry run -- --apply to write)')
        return 0
    if not os.path.isfile(BAK):
        shutil.copy2(HSC, BAK)
    _write(HSC, new)
    print('edited %s (backup %s)' % (HSC, BAK))
    print('next: python h2_rebuild_all.py --maps 08b')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
