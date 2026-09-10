r"""h4_hero_assist_icon_test.py -- is the ability meter's icon picked per ability TYPE?

The sprint meter shows but draws no icon, and nothing on the sprint eqip selects one:
after the restore it matches a working ability on every presentation surface it has.
So the icon is chosen in the HUD layer, and the one experiment that settles how:

    point Chief's `Hero Assist Equipment` at storm_forerunner_vision_pve,
    an ability whose meter icon is known to work.

  * the Promethean Vision icon appears  -> the meter picks its icon per ability TYPE
                                            and sprint simply has no art; that ends it.
  * no icon either                      -> the meter itself is misconfigured when fed
                                            through this slot, worth more digging.

Written IN PLACE on the live Dawn, touching one tagRef, so whatever else is on that map
stays exactly as it is -- a restore from the baseline would throw that away. The value
it replaces is recorded, and --undo writes it back.

    python sprint_toolkit/h4_hero_assist_icon_test.py            # dry run
    python sprint_toolkit/h4_hero_assist_icon_test.py --apply
    python sprint_toolkit/h4_hero_assist_icon_test.py --undo
"""
import argparse
import json
import os
import struct
import sys

TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import assembly_plugins                                           # noqa: E402
import halo_patch as hp                                           # noqa: E402
import h4_census as hc                                            # noqa: E402

S = chr(92)
MAP = 'm10_crash'
PROBE = ('objects' + S + 'equipment' + S + 'storm_forerunner_vision'
         + S + 'storm_forerunner_vision_pve')
UNDO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out',
                    'h4_hero_assist_icon_test.undo.json')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--undo', action='store_true')
    a = ap.parse_args()
    live = os.path.join(hc.MAPS, MAP + '.map')
    reg = hp.PluginRegistry(assembly_plugins.plugins_dir(), ['Halo4MCC', 'Halo4'])
    off = hp._h4_ref_offsets(reg, 'bipd', (hp._H4_HERO_ASSIST_FIELD,)).get(
        hp._H4_HERO_ASSIST_FIELD)
    m = hp.open_map(live, 'Halo 4')
    chief = m.find_tags('bipd', hp._H4_CHIEF_BIPD)
    if not chief or off is None:
        raise SystemExit('no Chief biped / no Hero Assist Equipment field')
    base = chief[0][1]
    ro = base + off
    cur = bytes(m.data[ro:ro + 16])
    rid = struct.unpack_from('<I', cur, 0xC)[0]
    now = next((t.get('name') for t in m.tags if t.get('ident') == rid), None)
    print('Dawn: Hero Assist Equipment = %s' % (now or 'null'))

    if a.undo:
        if not os.path.exists(UNDO):
            raise SystemExit('nothing recorded to undo')
        rec = json.load(open(UNDO, encoding='utf-8'))
        m.data[ro:ro + 16] = bytes.fromhex(rec['bytes'])
        m.save()
        os.remove(UNDO)
        print('restored to %s' % rec['was'])
        return

    ident = hp._h4_tag_ident(m, 'eqip', PROBE)
    print('probe    = %s (%s)' % (PROBE.rsplit(S, 1)[-1],
                                  'resident' if ident is not None else 'NOT on this map'))
    if ident is None:
        raise SystemExit('the Promethean Vision tag is not resident on Dawn')
    if not a.apply:
        print('(dry run -- pass --apply)')
        return
    os.makedirs(os.path.dirname(UNDO), exist_ok=True)
    json.dump({'map': MAP, 'was': now, 'bytes': cur.hex()},
              open(UNDO, 'w', encoding='utf-8'), indent=1)
    struct.pack_into('<I', m.data, ro, hp._EQIP_MAGIC)
    for b in range(4, 12):
        m.data[ro + b] = hp._H4_REF_FILL
    struct.pack_into('<I', m.data, ro + 0xC, ident & 0xFFFFFFFF)
    m.save()
    del m
    m2 = hp.open_map(live, 'Halo 4')
    rid2 = struct.unpack_from('<I', m2.data,
                              m2.find_tags('bipd', hp._H4_CHIEF_BIPD)[0][1] + off + 0xC)[0]
    got = next((t.get('name') for t in m2.tags if t.get('ident') == rid2), None)
    print('after save: Hero Assist Equipment = %s ; tags=%d ; checksum reproduces: %s'
          % ((got or 'null').rsplit(S, 1)[-1], len(m2.tags),
             m2.u32(m2.CHECKSUM_OFF) == m2.update_checksum()))
    print('undo record: %s' % UNDO)


if __name__ == '__main__':
    main()
