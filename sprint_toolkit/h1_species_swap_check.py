r"""Offline checks for the Halo 1 species replacement cards (h1_species_swap.py), run on
the patcher's E: baselines -- nothing is written to a live map.

    python h1_species_swap_check.py eligible --levels a10,c40
        per encounter: eligible, or why not (non-enemy squads, seated by script, set piece
        and the script functions that made it one)
    python h1_species_swap_check.py dry --levels a10 --cards hunter,flood combat --share 0.3 [--together]
        the pass alone, in memory: what each card converts, palette entries reused /
        appended / slots, clones built
    python h1_species_swap_check.py e2e --level a10 --cards flood combat,human --skulls betrayal
        a full halo_patch.apply_run on a scratch COPY (with an Armed: Elite needler card),
        then the written map's encounter teams and species -- proves the patch order
        (ladder -> swap -> Betrayal / Schism -> Armed)
Card keys: grunt, jackal, elite, hunter, sentinel, flood infection, flood combat, human.
"""
import argparse
import json
import os
import shutil
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
sys.path.insert(0, TOOL)
import halo_patch as hp            # noqa: E402
import h1_species_swap as sw       # noqa: E402
import enemy_count as ec           # noqa: E402
import h1_enemy_weapons as ew      # noqa: E402

LEVELS = ('a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40')
BASE = 'E:/HaloBaselines/halo1/maps/%s.map'
NAMES = {'human': 'Friend Marines'}


def card_name(k):
    return NAMES.get(k, '%s Incursion' % k.title())


def show(rows):
    for r in rows:
        print('   %-26s %s' % (r.get('effect'), 'SKIP ' + str(r.get('reason')) if r.get('skip') else
              ('FAIL ' + str(r.get('reason'))) if not r.get('ok') else
              '%s -> %s' % (r.get('old', ''), r.get('new', ''))))


def eligible(levels):
    for lv in levels:
        m = hp.open_map(BASE % lv, 'Halo 1')
        level = ew.Level(m, hp)
        why = {}
        sets = sw.setpiece_names(m, why)
        print('=== %s' % lv)
        for e in sw._encounters(m, level, ec.h1_squads(m)):
            live = [s for s in e['squads'] if s['chars'] and s['placed']]
            foes = [s for s in live if s['enemy'] and not s['boss']]
            if not foes:
                continue
            reasons = []
            if len(foes) != len(live):
                reasons.append('non-enemy squads')
            if any(s['bound'] for s in e['squads']):
                reasons.append('seated by script')
            if e['name'] in sets:
                reasons.append('set piece (%s)' % ', '.join(sorted(why.get(e['name'], ()))))
            print('   %-24s %3d on Insane  %s' % (e['name'], sum(s['insane'] for s in foes),
                                                 '; '.join(reasons) or 'ELIGIBLE'))


def dry(levels, keys, share, together):
    for lv in levels:
        for group in ([keys] if together else [[k] for k in keys]):
            m = hp.open_map(BASE % lv, 'Halo 1')
            rows = sw.apply(m, hp, [{'name': card_name(k), 'species': k, 'share': share}
                                    for k in group], [BASE % x for x in LEVELS])
            print('=== %s %s' % (lv, ' + '.join(group)))
            show(rows)


def e2e(lv, keys, share, skulls):
    tmp = os.path.join(tempfile.gettempdir(), 'h1_swap_e2e_%s.map' % lv)
    shutil.copy2(BASE % lv, tmp)
    try:
        reg = hp.PluginRegistry(json.load(open(os.path.join(TOOL, 'settings.json')))
                                ['assembly_plugins_dir'], ['Halo1MCC', 'Halo1'])
        levels = [BASE % x for x in LEVELS]
        plan = [{'tag': 'actv characters\\*', 'name': card_name(k),
                 'ops': [{'field': 'Incursion', 'species_swap': k, 'op_str': '+%g' % share}]}
                for k in keys]
        armed = {'levels': levels, 'option1': False, 'first_weapons': [], 'enabled': {},
                 'fallback': {}, 'cards': {'Elite': {'weapons\\needler\\needler': 0.5}},
                 'donors': {}}
        results, _b = hp.apply_run(tmp, plan, reg, 'Normal', backup=False, game='Halo 1',
                                   from_baseline=False, skulls=skulls, h1_enemy_weapons=armed,
                                   h1_levels=levels)
        names = {p['name'] for p in plan} | {'species swap', 'Betrayal', 'Schism'}
        show([r for r in results if r.get('effect') in names
              or 'enemy weapons' in str(r.get('effect'))])
        m = hp.open_map(tmp, 'Halo 1')
        by_enc = {}
        for s in ec.h1_squads(m):
            by_enc.setdefault(s['name'].split('/')[0], set()).update(s['chars'])
        print('--- written map: encounters with an explicit team')
        for e in m.follow_all(hp._scnr_base(m), [0x42C], [0xB0], 'all'):
            n = m.data[e:e + 0x20].split(b'\0')[0].decode('latin-1').lower()
            t = struct.unpack_from('<h', m.data, e + 0x24)[0]
            if t:
                print('   %-24s %-9s %s' % (n, ec.TEAM_NAMES[t] if t < len(ec.TEAM_NAMES) else t,
                                            ', '.join(sorted(c.rsplit('\\', 1)[-1]
                                                             for c in by_enc.get(n, ())))[:140]))
    finally:
        os.remove(tmp)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('eligible')
    a.add_argument('--levels', default=','.join(LEVELS))
    d = sub.add_parser('dry')
    d.add_argument('--levels', default='a10')
    d.add_argument('--cards', default=','.join(sw.CARDS))
    d.add_argument('--share', type=float, default=0.3)
    d.add_argument('--together', action='store_true')
    e = sub.add_parser('e2e')
    e.add_argument('--level', default='a10')
    e.add_argument('--cards', default='flood combat,human')
    e.add_argument('--share', type=float, default=0.3)
    e.add_argument('--skulls', default='')
    x = ap.parse_args()
    if x.cmd == 'eligible':
        eligible(x.levels.split(','))
    elif x.cmd == 'dry':
        dry(x.levels.split(','), x.cards.split(','), x.share, x.together)
    else:
        e2e(x.level, x.cards.split(','), x.share, [s for s in x.skulls.split(',') if s])


if __name__ == '__main__':
    main()
