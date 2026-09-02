r"""Arm both metagame experiments at once, with values chosen to be unmistakable.

Two things need proving in game, and they can be proven in the same sitting because
they touch different code paths:

  A. PLAYER DEATH. `death_penalty.py` repoints the death site at its own float. The
     open question is not whether the write lands -- that is already verified by
     readback -- but whether the WRAPPER is the authority in every game. Halo 3, ODST
     and Reach also carry `Player Death Point Count` in matg (25/25/0), and if the game
     dll wins there, this only ever moves Halo 1 and Halo 2.

  B. BETRAYAL. The wrapper only honours a ScoreDB row when it is NEGATIVE, falling back
     to a hardcoded -50 otherwise -- which is why setting Marines to 0 or positive
     changed nothing. NOPping the sign guard should make a POSITIVE row pay out,
     because ApplyPenalty ADDs its argument.

Both are armed at values no difficulty multiplier could disguise: a 500-point death and
a +200 Marine. If a reading comes back as 25 or -50, the patch did not take; if it
comes back scaled but large, it did.

    python sprint_toolkit/metagame_test.py --arm        # set both up
    python sprint_toolkit/metagame_test.py --status     # what is armed right now
    python sprint_toolkit/metagame_test.py --restore    # put everything back

--restore also puts scoredb.xml back from its .bak and re-pushes it, so the file and
the running game agree again afterwards.
"""
import argparse
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_TOOL = os.path.dirname(_HERE)
os.chdir(_TOOL)
sys.path.insert(0, _TOOL)
sys.path.insert(0, _HERE)

import death_penalty as dp                                          # noqa: E402
import score_live                                                   # noqa: E402
import scoredb_patch                                                # noqa: E402

DEATH_TEST = 500.0
MARINE_TEST = 200.0


def scoredb():
    import json
    cfg = json.load(open(os.path.join(_TOOL, 'settings.json'), encoding='utf-8'))
    root = cfg.get('mcc_root') or (r'C:\Program Files (x86)\Steam\steamapps\common'
                                   r'\Halo The Master Chief Collection')
    return os.path.join(root, scoredb_patch.SCOREDB_REL)


# A snapshot of scoredb.xml as it was when the test was armed. NOT the .bak the score
# scaler keeps: that one is the pristine shipped file, and restoring from it would throw
# away whatever scaling the current run had already applied. This file exists only for
# the duration of the experiment.
SNAPSHOT_SUFFIX = '.mgtest'


def set_marines(path, score):
    """Rewrite every Marine row to `score`, leaving every other row alone.

    Edited from the CURRENT file, not the baseline, so a run's existing score scaling
    survives the experiment. Setting an absolute value cannot compound, so there is no
    reason to reach for the baseline here."""
    snap = path + SNAPSHOT_SUFFIX
    if not os.path.exists(snap):
        import shutil
        shutil.copy2(path, snap)
    with open(path, encoding='utf-8') as f:
        cur = f.read()
    n = [0]

    def sub(m):
        n[0] += 1
        return '%sscore="%g"' % (m.group(1), score)

    out = re.sub(r'(type="_campaign_metagame_bucket_type_marine"[^/]*?)score="[^"]*"',
                 sub, cur)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(out)
    return n[0]


def unset_marines(path):
    """Put scoredb.xml back exactly as the test found it."""
    snap = path + SNAPSHOT_SUFFIX
    if not os.path.exists(snap):
        return False
    import shutil
    shutil.copy2(snap, path)
    os.remove(snap)
    return True


def status():
    # The file half is reported even with MCC closed: checking what is armed before
    # launching the game is exactly when you want to look.
    h, base, pid, err = dp.attach()
    if err:
        print('  %s — the process half cannot be read' % err)
    else:
        try:
            val, at, _ = dp.state(h, base)
            origin = ('stock' if at == dp.STOCK_LITERAL
                      else 'OUR SLOT' if at == dp.SLOT else '?')
            guard, raw = dp.betrayal_state(h, base)
            print('  pid %d, base 0x%X' % (pid, base))
            print('  A  player death penalty   %-8s  (%s)' % (val, origin))
            print('  B  betrayal sign guard    %-8s  (%s)'
                  % (guard, raw.hex() if raw else '?'))
        finally:
            dp.k32.CloseHandle(h)
    p = scoredb()
    rows = re.findall(r'type="_campaign_metagame_bucket_type_marine"[^/]*?score="([^"]*)"',
                      open(p, encoding='utf-8').read())
    print('  B  Marine rows in scoredb.xml  %s' % (', '.join(rows) or 'none'))
    return 0


def arm():
    p = scoredb()
    n = set_marines(p, MARINE_TEST)
    print('  scoredb.xml: %d Marine row(s) set to +%g' % (n, MARINE_TEST))
    pushed = score_live.push_from_xml(p)
    print('  live push: %s' % ('%d record(s)' % pushed['written'] if pushed.get('ok')
                               else 'FAILED — %s' % pushed.get('reason')))
    h, base, pid, err = dp.attach()
    if err:
        print('  %s' % err)
        return 1
    try:
        ok, e = dp.apply(h, base, DEATH_TEST)
        print('  A  death penalty -> %g : %s' % (DEATH_TEST, 'ok' if ok else 'FAILED %s' % e))
        ok2, e2 = dp.betrayal_open(h, base)
        print('  B  betrayal guard -> open : %s' % ('ok' if ok2 else 'FAILED %s' % e2))
    finally:
        dp.k32.CloseHandle(h)
    print()
    print(PROTOCOL)
    return 0


def unarm():
    h, base, pid, err = dp.attach()
    if err:
        print('  %s (skipping the process half)' % err)
    else:
        try:
            print('  A  death penalty restored: %s' % dp.restore(h, base)[0])
            print('  B  betrayal guard restored: %s' % dp.betrayal_restore(h, base)[0])
        finally:
            dp.k32.CloseHandle(h)
    p = scoredb()
    done = unset_marines(p)
    print('  scoredb.xml restored from the test snapshot: %s'
          % (done or 'nothing to restore (was it armed?)'))
    pushed = score_live.push_from_xml(p)
    print('  live push: %s' % ('%d record(s)' % pushed['written'] if pushed.get('ok')
                               else pushed.get('reason')))
    return 0


PROTOCOL = """
WHAT TO DO
  Campaign scoring must be ON for any of this to be visible. Both tests read the score
  counter on the HUD, so run them somewhere the number is easy to watch.

  A. DEATH PENALTY. Note the score, die, note it again.
       ~500 lost (x difficulty/skull)  the wrapper is the authority in THIS game
       exactly 25 lost                 the write did not reach this game -- for Halo 3,
                                       ODST or Reach that means the matg field wins and
                                       those three need the map patch instead
       nothing lost                    scoring is off, or deaths are not scored here

     Worth running TWICE: once in Halo 1 or Halo 2, where the wrapper is the only
     scoring engine there is, and once in Halo 3 or ODST, where matg also has an
     opinion. The pair is what answers "does one live write cover every game".

  B. BETRAYAL. Kill a friendly Marine and watch the score.
       ~+200 gained                    both halves work: the guard NOP lets a positive
                                       ScoreDB row through, and ApplyPenalty adds it
       -50 lost                        the guard is still closed, or betrayal took a
                                       different path than +0x00437F44
       -200 lost                       the row is being read but its sign is inverted
                                       somewhere after the guard
       nothing                         Marines are not classed as a betrayal here --
                                       try the Marine variant the level actually uses

  Then: python sprint_toolkit/metagame_test.py --restore
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--arm', action='store_true')
    g.add_argument('--status', action='store_true')
    g.add_argument('--restore', action='store_true')
    a = ap.parse_args()
    if a.status:
        return status()
    if a.arm:
        return arm()
    return unarm()


if __name__ == '__main__':
    sys.exit(main())
