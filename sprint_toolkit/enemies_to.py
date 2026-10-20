r"""enemies_to.py -- a TEST RIG: turn a level's enemies into one character, Halo 2 to Halo 4.

The species writer is the patcher's own (halo_patch._apply_ladder, Thunderstorm / Downpour),
driven with a forced move "every eligible enemy -> TARGET": it handles weapons (a Hunter gets
-1 = its own arm gun; keeping the squads' weapons made swapped Hunters spawn with plasma
pistols in Reach and not at all in Halo 3), cell arrays shared between squads, allies, and
squads the scripts load into vehicles.

RESIDENCY DECIDES WHERE A SWAP CAN SPAWN (measured 2026-10-19/20): a character only spawns
where its tags are loaded. Hunters at the START: Reach m70_bonus, ODST sc100 / sc110 / sc120 /
sc140. Halo 3 and Halo 4 load Hunters only in the zones of their own fights, so swapping the
whole level leaves the rest EMPTY and can block progress -- use --squads to swap only the
squads of that part of the level (Halo 4 m70: sq_sp03_bot_; m80: sq_lab_). Writing pool bits
crashes Halo 4 (h4_pools.py), and switching the Hunter's designer zone on at the start did not
load it either (m80).

The map is built from the patcher BASELINE (+ any extra you name) and written over the live
map; the enhancer's next patch puts the run back.

    python sprint_toolkit/enemies_to.py "Halo Reach" m70_bonus hunter
    python sprint_toolkit/enemies_to.py "Halo 4" m70_liftoff storm_hunter --squads sq_sp03_bot_
    python sprint_toolkit/enemies_to.py "Halo 3: ODST" sc100 hunter --hunter-drop
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import halo_patch as HP       # noqa: E402
import map_vault as V         # noqa: E402

BS = chr(92)


def leaf(name):
    return (name or '').lower().rsplit(BS, 1)[-1]


def swap(m, game, target, squads=None):
    """Every eligible enemy (of the squads whose name contains one of `squads`, else all)
    -> the palette entry whose leaf name is `target`. Returns the writer's result rows."""
    lay = HP._BETRAYAL[game]
    soff = lay['squads'][0]
    scnr = HP._scnr_base(m)
    subs = [s.lower() for s in (squads or ())]
    mode = {'keep': None}
    orig_follow, orig_units = m.follow_all, HP._ts_units
    orig_moves, orig_gate = HP._ts_moves, HP._ts_resident_gate

    def follow(base, offs, sizes, how):
        out = orig_follow(base, offs, sizes, how)
        if subs and mode['keep'] is not None and base == scnr and list(offs) == [soff]:
            def name(sq):
                return bytes(m.data[sq:sq + 32]).split(b'\0')[0].decode('latin1').lower()
            out = [sq for sq in out if any(s in name(sq) for s in subs) == mode['keep']]
        return out

    def units(*a, **k):
        if not subs:
            return orig_units(*a, **k)
        mode['keep'] = False
        outside = orig_units(*a, **k)
        mode['keep'] = True
        inside = orig_units(*a, **k)
        mode['keep'] = None
        # an element an outside squad also reaches (shared cell arrays) stays as it is
        taken = set()
        for u in outside:
            taken.add(u['char_at'])
            taken.update(u['weap_at'])
            taken.update(u.get('weap2_at', ()))
        for u in inside:
            if u['char_at'] in taken or any(
                    x in taken for x in list(u['weap_at']) + list(u.get('weap2_at', ()))):
                u['protected'] = True
        return inside

    def moves(_game, entries, up, down, allowed=None, pools=None):
        t = next((i for i, (n, _sp, _ok) in enumerate(entries) if leaf(n) == target), None)
        if t is None:
            raise SystemExit('%s is not in the character palette' % target)
        return {i: t for i, (n, _sp, ok) in enumerate(entries)
                if ok and i != t and leaf(n) != target}

    m.follow_all, HP._ts_units = follow, units
    HP._ts_moves, HP._ts_resident_gate = moves, (lambda *a, **k: None)
    try:
        return HP._apply_ladder(m, game, None, set(), set())
    finally:
        m.follow_all, HP._ts_units = orig_follow, orig_units
        HP._ts_moves, HP._ts_resident_gate = orig_moves, orig_gate


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('game')
    ap.add_argument('map')
    ap.add_argument('target', help='character leaf name, e.g. hunter, storm_hunter')
    ap.add_argument('--squads', help='comma list of squad-name substrings to swap (default all)')
    ap.add_argument('--hunter-drop', action='store_true',
                    help="also apply the 'Hunters drop a Fuel Rod' option")
    a = ap.parse_args()
    live = V.resolve(a.game, a.map)
    if not live:
        raise SystemExit('map not found')
    m = HP.open_map(V.baseline_for(a.game, live), a.game)
    if a.hunter_drop:
        import hunter_drop
        for r in hunter_drop.apply(m, a.game, True):
            print('hunter drop:', r.get('field'), '->', r.get('new', r.get('reason')))
    for r in swap(m, a.game, a.target.lower(),
                  a.squads.split(',') if a.squads else None):
        print('swap:', r.get('new', r.get('reason')))
    m.save(live)
    print('wrote', live)


if __name__ == '__main__':
    main()
