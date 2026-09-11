r"""h4_scope_test.py -- give ONE Halo 4 weapon a zoom and a scope HUD, for an in-game
check of the scope graft (halo_patch._apply_h4_scope).

What it writes, on the live map:
  * the weapon's Magnification Levels 1 and Magnification Range 2x -- what a Zoom card
    does, so the weapon can zoom at all
  * the scope grafted into the weapon's HUD screen (cusc) from a scoped weapon's
    screen on the same map -- battle_rifle by default, --donor picks another

The live map is copied aside FIRST, to sprint_toolkit/_scope_test_backup/, and
--restore copies that back. The vault baseline is never used, so a map you have edited
in Sapien comes back exactly as it was before this ran.

    python sprint_toolkit/h4_scope_test.py --map m020                      # dry run
    python sprint_toolkit/h4_scope_test.py --map m020 --apply
    python sprint_toolkit/h4_scope_test.py --map m020 --weapon storm_lmg --donor dmr --apply
    python sprint_toolkit/h4_scope_test.py --map m020 --restore

Donors (HUD screen names): battle_rifle, dmr, carbine, forerunner_rifle, magnum,
sniper_rifle, beam_rifle, rocket_launcher, fuel_rod -- whichever the map carries.
"""
import argparse
import os
import shutil
import sys

TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import assembly_plugins                                           # noqa: E402
import halo_patch as hp                                           # noqa: E402
import h4_census as hc                                            # noqa: E402

G = 'Halo 4'
S = chr(92)
BACKUP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_scope_test_backup')


def _weapon(m, leaf):
    hits = [(n, b) for n, b in m.find_tags('weap', '*') if n.rsplit(S, 1)[-1] == leaf]
    return hits[0] if hits else (None, None)


def _hud_state(m, wname):
    b = _weapon(m, wname.rsplit(S, 1)[-1])[1]
    hud = hp._h4_tag_at(m, b + hp._H4_HUD_REF)
    comps = hp._h4_rows(m, hud[1], *hp._H4_CUSC['components'])
    temps = hp._h4_rows(m, hud[1], *hp._H4_CUSC['templates'])
    return hud[0], len(comps), len(temps)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--map', required=True, help='campaign map basename, e.g. m020')
    ap.add_argument('--weapon', default='storm_assault_rifle', help='weap tag leaf name')
    ap.add_argument('--donor', default=None, help='donor HUD screen, e.g. battle_rifle')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--restore', action='store_true')
    a = ap.parse_args()
    live = os.path.join(hc.MAPS, a.map + '.map')
    bak = os.path.join(BACKUP, a.map + '.map')
    print('live   %s' % live)
    print('backup %s  (exists: %s)' % (bak, os.path.exists(bak)))
    if a.restore:
        if not os.path.exists(bak):
            raise SystemExit('no backup to restore from')
        shutil.copyfile(bak, live)
        os.remove(bak)
        print('restored %s from the side backup (backup removed)' % a.map)
        return
    m = hp.open_map(live, G)
    wname, wb = _weapon(m, a.weapon)
    if wname is None:
        raise SystemExit('%s is not in %s' % (a.weapon, a.map))
    hud, nc, nt = _hud_state(m, wname)
    print('weapon %s\n   HUD %s: %d components, %d template(s)' % (wname, hud, nc, nt))
    reg = hp.PluginRegistry(assembly_plugins.plugins_dir(), ['Halo4MCC', 'Halo4'])
    wp = reg.get('weap')
    print('   Magnification Levels %s, Range %s-%s' % (
        m.read_tag_field(wb, 'Magnification Levels', wp),
        m.read_tag_field(wb, 'Magnification Range', wp),
        m.read_tag_field(wb, 'Magnification Range Max', wp)))
    if not a.apply:
        huds = {}
        for n, b in m.find_tags('weap', '*'):
            r = hp._h4_tag_at(m, b + hp._H4_HUD_REF)
            if r:
                huds.setdefault(r[0].rsplit(S, 1)[-1], r)
        donors = [d for d in ((a.donor,) if a.donor else hp._H4_SCOPE_DONORS) if d in huds]
        print('   donor HUDs on this map: %s' % donors)
        for d in donors[:1]:
            plan = hp._h4_scope_plan(m, hp._h4_tag_at(m, wb + hp._H4_HUD_REF)[1],
                                     huds[d][1])
            if isinstance(plan, str):
                print('   plan from %s: NOT POSSIBLE -- %s' % (d, plan))
            else:
                print('   plan from %s: +%d components, +%d binding(s), +%d comparison(s), '
                      'overlay adds %s' % (d, plan['added'], len(plan['binds']),
                                           len(plan['cmps']),
                                           [(ti, len(oc), len(an)) for ti, oc, an in plan['ov']]))
        print('(dry run -- pass --apply)')
        return
    del m
    os.makedirs(BACKUP, exist_ok=True)
    if not os.path.exists(bak):
        shutil.copyfile(live, bak)
        print('backup CREATED first')
    m = hp.open_map(live, G)
    wname, wb = _weapon(m, a.weapon)
    for f, v in (('Magnification Levels', 1), ('Magnification Range', 2.0),
                 ('Magnification Range Max', 2.0)):
        m.write_tag_field(wb, f, v, wp)
    rows = hp._apply_h4_scope(m, ['weap ' + wname],
                              donor_huds=(a.donor,) if a.donor else None)
    for r in rows:
        print('   %s' % r)
    if not any(r.get('ok') and not r.get('skip') for r in rows):
        print('nothing grafted -- map NOT saved')
        return
    m.save()
    del m
    m2 = hp.open_map(live, G)
    hud, nc, nt = _hud_state(m2, wname)
    print('after save: HUD %s has %d components, %d template(s); checksum reproduces: %s'
          % (hud, nc, nt, m2.u32(m2.CHECKSUM_OFF) == m2.update_checksum()))


if __name__ == '__main__':
    main()
