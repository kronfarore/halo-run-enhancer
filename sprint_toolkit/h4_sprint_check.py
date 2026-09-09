r"""h4_sprint_check.py -- prove out the four Halo 4 sprint paths, offer side and map side.

Halo 4 is the one game that already sprints, so its sprint cards are not like anyone
else's. Sprint is INNATE -- matg `Default Player Traits / Movement Traits / Sprint
Usage` ships as True -- and the sprint equipment tag that survives in the cache grants
that same trait and reads the same `Player Information / Momentum and Sprinting`
numbers, owning nothing but the energy meter itself. So a Halo 4 sprint card always
moves both players; what `h4_sprint_mode` picks is who may be OFFERED one, and whether
the equipment comes back.

    off      vanilla -- no sprint card can appear
    holder   only a player carrying Sprint from Reach (or the Halo 1 ability)
    all      both players
    restore  innate sprint off and the sprint equipment given the HUD it never
             shipped with, which also unlocks the three energy-meter cards. PLACING
             the pickup is level work (Sapien) and is deliberately not done here.

This checks both halves:
  OFFER  the card set each mode produces, for a player who holds Sprint and one who
         does not, in Halo 4 AND in Reach (Reach must be untouched by all of this).
  MAP    --apply-map copies a map, runs the restore, reopens it and reads back the
         trait plus the HUD references the sprint equipment ships without.

    python sprint_toolkit/h4_sprint_check.py
    python sprint_toolkit/h4_sprint_check.py --apply-map
"""
import argparse
import os
import shutil
import struct
import sys
import tempfile

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import assembly_plugins                                           # noqa: E402
import halo_enhancer as he                                        # noqa: E402
import halo_patch as hp                                           # noqa: E402
import h4_census as hc                                            # noqa: E402

S = chr(92)
SPRINT_ITEM = 'Sprint'
# Dawn carries the sprint tag; Shutdown does not, and is here to prove the pass still
# does the matg half and reports the equipment half as skipped rather than failing.
MAPS = ('m10_crash', 'm70_liftoff')


def offer_check(db):
    print('=== OFFER SIDE')
    print('%-9s %-12s %-34s %s' % ('mode', 'game', 'holding', 'sprint cards offered'))
    for mode in he.H4_SPRINT_MODES:
        he.CONFIG['h4_sprint_mode'] = mode
        for game in ('Halo 4', 'Halo Reach'):
            for holding in ([], [SPRINT_ITEM], [he.SPRINT_ITEM]):
                mods = db.get_player_modifiers_filtered(holding, set(), game)
                names = sorted({m['name'] for m in mods
                                if m.get('equipment') == 'Sprint'})
                label = ', '.join(holding) or '(nothing)'
                print('%-9s %-12s %-34s %s' % (mode, game, label,
                                               ', '.join(names) or '-'))
    he.CONFIG['h4_sprint_mode'] = 'off'


def map_check(apply_map):
    print()
    print('=== MAP SIDE (restore)')
    reg = hp.PluginRegistry(assembly_plugins.plugins_dir(), ['Halo4MCC', 'Halo4'])
    matg_plug = reg.get('matg')
    for name in MAPS:
        src = os.path.join(hc.MAPS, name + '.map')
        if not os.path.exists(src):
            print('%-14s MISSING' % name)
            continue
        m = hp.open_map(src, 'Halo 4')
        base = m.find_tags('matg', 'globals' + S + 'globals')[0][1]
        print('%-14s before: Sprint Usage=%s ; sprint eqip resident=%s'
              % (name, m.read_tag_field(base, 'Sprint Usage', matg_plug,
                                        'Movement Traits', 0),
                 bool(m.find_tags('eqip', hp._H4_SPRINT_EQIP))))
        if not apply_map:
            continue
        tmp = os.path.join(tempfile.gettempdir(), 'h4sprint_' + name + '.map')
        shutil.copyfile(src, tmp)
        res, _bak = hp.apply_run(tmp, [], reg, 'Normal', backup=False, game='Halo 4',
                                 from_baseline=False, h4_sprint={'mode': 'restore'})
        for r in res:
            print('    %-22s %-22s %s -> %s%s'
                  % (r.get('effect'), r.get('field'), r.get('old'), r.get('new'),
                     '' if r.get('ok') else '  FAILED: %s' % r.get('reason')))
        m2 = hp.open_map(tmp, 'Halo 4')
        b2 = m2.find_tags('matg', 'globals' + S + 'globals')[0][1]
        idx = {t['index']: t for t in m2.tags}
        offs = hp._h4_ref_offsets(reg, 'eqip', hp._H4_HUD_FIELDS)
        got = []
        for tp, base in m2.find_tags('eqip', hp._H4_SPRINT_EQIP):
            for fname, off in offs.items():
                rid = struct.unpack_from('<I', m2.data, base + off + 0xC)[0]
                t = idx.get(rid & 0xFFFF) if rid not in (0, 0xFFFFFFFF) else None
                got.append('%s=%s' % (fname.split()[0],
                                      (t or {}).get('name', 'null').rsplit(S, 1)[-1]))
        chief = m2.find_tags('bipd', hp._H4_CHIEF_BIPD)
        boff = hp._h4_ref_offsets(reg, 'bipd', (hp._H4_HERO_ASSIST_FIELD,)).get(
            hp._H4_HERO_ASSIST_FIELD)
        if chief and boff is not None:
            rid = struct.unpack_from('<I', m2.data, chief[0][1] + boff + 0xC)[0]
            t = idx.get(rid & 0xFFFF) if rid not in (0, 0xFFFFFFFF) else None
            print('    chief:  Hero Assist Equipment = %s'
                  % ((t or {}).get('name', 'null').rsplit(S, 1)[-1]))
        print('    after:  Sprint Usage=%s ; sprint eqip %s'
              % (m2.read_tag_field(b2, 'Sprint Usage', matg_plug, 'Movement Traits', 0),
                 ', '.join(got) or '(not resident on this map)'))
        print('    tags=%d ; checksum reproduces: %s'
              % (len(m2.tags), m2.u32(m2.CHECKSUM_OFF) == m2.update_checksum()))
        del m2
        os.remove(tmp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply-map', action='store_true',
                    help='also write the restore onto a COPY of each map and read back')
    a = ap.parse_args()
    db = he.ModifierDatabase(os.path.join(TOOL, 'halo.json'))
    offer_check(db)
    map_check(a.apply_map)


if __name__ == '__main__':
    main()
