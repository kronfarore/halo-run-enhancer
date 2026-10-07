r"""Halo 1 TEST map: which species can ride a Covenant dropship (2026-10-07).

Question (user): what can spawn from a dropship? The species replacement cards leave
every squad the scripts seat in a vehicle alone; if other species ride, the cards (and
the faction skulls) could convert dropship waves too.

a30 opens with one: mission_lz_dropship places platoon lz_search/cship_toon (squads
grunt, far_grunt, elite), loads all of it into lz_cship's passenger seats with
(vehicle_load_magic lz_cship "passenger" (ai_actors lz_search/cship_toon)), flies in and
unloads the 8 cd-passenger seats one by one in random order.

The test, on a COPY of the E: baseline:
  * squad `grunt` gets count 8 (Normal and Insane) -- it has exactly 8 starting
    locations -- and every location its own species through the location's actor-type
    override, so each of the 8 seats holds a different species;
  * `far_grunt` and `elite` drop to 0, so nothing else competes for the seats;
  * lz_search's team is set to Covenant (3) so no species in it decides the side;
  * the player gets h1_enemy_test_map's god shield, to watch the unload in peace.
Seat 1 is a stock Grunt: the CONTROL. If it does not ride, the test says nothing.

    python h1_dropship_test.py            -> halo1\maps\a30_dropship_test.map
    h1_dropship_test.cmd deploy|restore   (live kept as a30.map.pre_dropship)
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
sys.path.insert(0, TOOL)
sys.path.insert(0, HERE)
import halo_patch as hp            # noqa: E402
import h1_species_swap as sw       # noqa: E402
import h1_enemy_weapons as ew      # noqa: E402
import h1_enemy_test_map as etm    # noqa: E402

BS = chr(92)
LEVEL = 'a30'
BASE = 'E:/HaloBaselines/halo1/maps/%s.map' % LEVEL
OUT = os.path.join(os.path.dirname(TOOL), 'halo1', 'maps', LEVEL + '_dropship_test.map')
ENCOUNTER, SQUAD, EMPTY = 'lz_search', 'grunt', ('far_grunt', 'elite')
SEATS = [                                    # one per starting location, in order
    sw.C('grunt', 'grunt minor plasma pistol'),                       # control
    sw.C('hunter', 'hunter'),
    sw.C('jackal', 'jackal minor plasma pistol'),
    sw.C('floodcombat elite', 'floodcombat elite assault rifle'),
    sw.C('floodcombat_human', 'floodcombat_human shotgun'),
    sw.C('flood_infection', 'flood_infection'),
    sw.C('floodcarrier', 'floodcarrier'),
    sw.C('sentinel', 'sentinel'),
]


def main():
    m = hp.open_map(BASE, 'Halo 1')
    lv = ew.Level(m, hp)
    swp = sw.Swapper(m, lv, lambda: [])
    idx = []
    for name in SEATS:
        got = swp.entry(swp.resolve(name))
        if got is None:
            raise SystemExit('no palette entry for %s' % name)
        idx.append(got)
    enc = None
    for e in m.follow_all(lv.s, [0x42C], [0xB0], 'all'):
        if m.data[e:e + 0x20].split(b'\0')[0].decode('latin-1') == ENCOUNTER:
            enc = e
    if enc is None:
        raise SystemExit('no encounter %s' % ENCOUNTER)
    struct.pack_into('<h', m.data, enc + sw.ENC_TEAM, sw.TEAM['covenant'])
    done = []
    for sq in m.follow_all(enc, [0x80], [0xE8], 'all'):
        name = m.data[sq:sq + 0x20].split(b'\0')[0].decode('latin-1')
        if name in EMPTY:
            struct.pack_into('<hh', m.data, sq + 0x7C, 0, 0)
            done.append('%s -> 0' % name)
        elif name == SQUAD:
            locs = m.follow_all(sq, [0xD0], [0x1C], 'all')
            if len(locs) != len(SEATS):
                raise SystemExit('%s has %d starting locations, expected %d'
                                 % (SQUAD, len(locs), len(SEATS)))
            struct.pack_into('<hh', m.data, sq + 0x7C, len(SEATS), len(SEATS))
            for loc, i, nm in zip(locs, idx, SEATS):
                struct.pack_into('<h', m.data, loc + 0x18, i)
            done.append('%s -> %d: %s' % (SQUAD, len(SEATS),
                                         ', '.join(n.rsplit(BS, 1)[-1] for n in SEATS)))
    coll = m.tags[('coll', etm.COLL)]
    for off, v in ((etm.MAX_BODY, 1e6), (etm.MAX_SHIELD, 1e6), (etm.LEAK, 0.0),
                   (etm.STUN, 0.0), (etm.RECHARGE, 0.1)):
        struct.pack_into('<f', m.data, coll + off, v)
    m.save(OUT)
    for n in swp.notes:
        print('  ' + n)
    for d in done:
        print('  ' + d)
    print('wrote %s' % OUT)


if __name__ == '__main__':
    main()
