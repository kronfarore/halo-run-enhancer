r"""What has to be imported into each Halo 3 map to make everything the Run Enhancer
can offer actually usable there -- the shopping list for a prepare_map rebuild.

FOUR SECTIONS, because the games carry them four different ways:

  WEAPONS    `weap` tags. Checked for residency AND for geometry (below).
  TURRETS    also `weap` tags, so identical checks -- but they are the detachable
             emplacements rather than things you spawn holding, and halo.json tracks
             them in a separate per-mission `turret` list. Machine Gun, Plasma Cannon,
             the Flamethrower (a turret in Halo 3, not a carried weapon) and the
             Missile Pod, which only 040_voi stocks.
  EQUIPMENT  `eqip` tags, residency only: equipment is placed, not held, so the
             first-person geometry gate does not apply.
  GRENADES   an `eqip` tag like the rest of the equipment --
             objects\weapons\grenade\<name>\<name> -- AND a slot in `matg` ->
             Grenades holding a Maximum Count plus Equipment and Projectile tagRefs
             (slot 0 frag, 1 plasma, 2 claymore, 3 firebomb). Both are checked: the
             tag can be missing from the map, or present while the slot fails to point
             at it. Measured: all four are wired on every Halo 3 campaign map, so
             grenades are a halo.json OFFER question rather than an import one --
             which is why this also reports the mismatch.

THE TWO CHECKS, in the order they gate:

  1. RESIDENT   is the tag in this map at all? If not, `_weap_ref_id` / `_resolve_pi`
                return None and the pick is silently skipped.
  2. GEOMETRY   does the weapon's family own render-model and first-person-animation
                chunks in this map's zone? prepare_map's own gate for ODST -- a tag
                marked resident with no geometry black-screens the game.

IMPORTANT -- Halo 3 is NOT ODST. `prepare_map` hardcodes ODST offsets and the weap
First Person block moved: **Halo 3 0x3FC, ODST 0x40C**. Reading ODST's on an H3 map
lands 16 bytes past it and reports jmad=0 for every weapon, i.e. "everything is
broken". This module overrides that one constant.

ALSO IMPORTANT -- the READY verdict is not predictive on SHIPPED maps. The Shotgun on
010_jungle passed every check here and still would not appear in game; rebuilding the
level through H3EK's tool.exe fixed it, and its scenario weapon palette never changed.
Treat this as the list of what to ADD to a rebuild, not as a promise about a stock map.

    python h3_import_list.py                  # every level
    python h3_import_list.py 010_jungle       # one level
    python h3_import_list.py --json           # machine-readable, to drive a rebuild
    python h3_import_list.py --offers         # also cross-check halo.json's own lists
"""
import argparse
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import halo_patch as HP                                          # noqa: E402
import prepare_map as PM                                         # noqa: E402

GAME = 'Halo 3'
MAPS = (r"C:\Program Files (x86)\Steam\steamapps\common"
        r"\Halo The Master Chief Collection\halo3\maps")
LEVELS = ["010_jungle", "020_base", "030_outskirts", "040_voi", "050_floodvoi",
          "070_waste", "100_citadel", "110_hc", "120_halo"]
MISSION_OF = {l: l.split('_')[0] for l in LEVELS}

# See the module docstring: the one ODST constant that is wrong for Halo 3.
PM.WEAP_FIRST_PERSON = 0x3FC

# `weap` tags that are emplacements rather than carried weapons. The Flamethrower sits
# here because Halo 3 mounts it: 110_hc and 120_halo list it under `turret`, never
# under `weapons`.
TURRETS = ('Machine Gun', 'Plasma Cannon', 'Flamethrower', 'Missile Pod')

# matg -> Grenades slot per type, mirroring the `index` halo.json already uses on each
# grenade's Maximum Count target.
GRENADE_SLOT = {'Frag Grenade': 0, 'Plasma Grenade': 1,
                'Claymore Grenade': 2, 'Firebomb Grenade': 3}
GREN_EQUIP_AT, GREN_PROJ_AT = 0x14 + 0xC, 0x24 + 0xC     # tagRef ident offsets

# A grenade IS an equipment tag -- objects\weapons\grenade\<name>\<name> -- so its
# residency is checked directly by path like any other eqip, as well as through the
# matg slot that references it. Checking both catches the two ways it can go wrong:
# the tag missing from the map, and the slot not pointing at it.
GRENADE_EQIP = {
    'Frag Grenade': r"objects\weapons\grenade\frag_grenade\frag_grenade",
    'Plasma Grenade': r"objects\weapons\grenade\plasma_grenade\plasma_grenade",
    'Claymore Grenade': r"objects\weapons\grenade\claymore_grenade\claymore_grenade",
    'Firebomb Grenade': r"objects\weapons\grenade\firebomb_grenade\firebomb_grenade",
}

# Mirrors CONFIG['weapon_aliases'] in halo_enhancer. Kept as a literal rather than
# imported, so this stays runnable without PySide6.
ALIASES = {'Magnum': 'Pistol'}


def _tool_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _h3(tag):
    if isinstance(tag, dict):
        tag = tag.get('Halo 3')
    return tag if isinstance(tag, str) else None


def catalogue():
    """Everything the enhancer can offer on Halo 3, split by how the map carries it."""
    with open(os.path.join(_tool_dir(), 'halo.json'), encoding='utf-8') as f:
        d = json.load(f)
    weapons, turrets = {}, {}
    for w, wd in d['Player Modifiers']['Specific Weapon Modifier'].items():
        for _cn, c in wd.items():
            if not isinstance(c, dict):
                continue
            t = _h3(c.get('tag'))
            if t and t.startswith('weap '):
                path = t.split(' & ')[0].split(' ', 1)[1]
                (turrets if w in TURRETS else weapons)[w] = path
                break
    equipment = {}
    for e, ed in (d.get('Equipment') or {}).items():
        if not isinstance(ed, dict):
            continue
        for _cn, c in ed.items():
            if not isinstance(c, dict):
                continue
            t = _h3(c.get('tag'))
            if t and t.startswith('eqip '):
                equipment[e] = t.split(' & ')[0].split(' ', 1)[1]
                break
    return {'weapons': weapons, 'turrets': turrets, 'equipment': equipment,
            'grenades': dict(GRENADE_SLOT), 'missions': d['Missions']['Halo 3']}


def zone_base(m):
    for t in m.tags:
        if t.get('class') == 'zone':
            return t.get('base')
    return None


def _weap_state(m, zb, path):
    if not m.find_tags('weap', path):
        return {'resident': False, 'mode': 0, 'jmad': 0, 'need': 'import'}
    mode = jmad = None
    if zb is not None:
        try:
            mode, jmad = PM.geometry(m, zb, path.rsplit('\\', 1)[-1])
        except Exception:
            mode = jmad = None
    need = 'geometry' if (mode == 0 and jmad == 0) else 'ok'
    return {'resident': True, 'mode': mode, 'jmad': jmad, 'need': need}


def _grenades(m, registry):
    """Per grenade type: does its matg slot resolve an Equipment and a Projectile?"""
    pl = registry.get('matg')
    tags = [t for t in m.tags if t.get('class') == 'matg']
    out = {}
    if pl is None or not tags:
        return {n: {'need': 'unknown', 'reason': 'matg unavailable'} for n in GRENADE_SLOT}
    f = pl.find('Maximum Count', 'Grenades')
    if not f:
        return {n: {'need': 'unknown', 'reason': 'Grenades block not in plugin'}
                for n in GRENADE_SLOT}
    base = tags[0]['base']
    boff, esize = f['block_offsets'][-1], f['block_sizes'][-1]
    n = m.i32(base + boff)
    blk = HP._block_base(m, base + boff)
    for name, slot in GRENADE_SLOT.items():
        # the equipment tag itself, by path, exactly as for any other eqip
        tag_here = bool(m.find_tags('eqip', GRENADE_EQIP[name]))
        if blk is None or slot >= max(0, n):
            out[name] = {'need': 'import', 'eqip': tag_here,
                         'reason': 'no matg slot %d (block has %d)' % (slot, n)}
            continue
        off = blk + slot * esize
        eq = struct.unpack_from('<I', m.data, off + GREN_EQUIP_AT)[0]
        pr = struct.unpack_from('<I', m.data, off + GREN_PROJ_AT)[0]
        en = HP._tag_name_by_id(m, eq) if eq != 0xFFFFFFFF else None
        pn = HP._tag_name_by_id(m, pr) if pr != 0xFFFFFFFF else None
        need = 'ok' if (tag_here and en and pn) else 'import'
        why = None
        if not tag_here:
            why = 'eqip tag not in this map'
        elif not en or not pn:
            why = 'matg slot %d has no %s' % (slot, 'equipment' if not en else 'projectile')
        out[name] = {'need': need, 'eqip': tag_here,
                     'max': struct.unpack_from('<h', m.data, off)[0],
                     'equipment': en, 'projectile': pn, 'reason': why}
    return out


def survey(level, cat, registry):
    p = os.path.join(MAPS, level + ".map")
    if not os.path.exists(p):
        return None
    m = HP.open_map(p, GAME)
    zb = zone_base(m)
    out = {'weapons': {}, 'turrets': {}, 'equipment': {}, 'grenades': {}}
    for kind in ('weapons', 'turrets'):
        for name, path in sorted(cat[kind].items()):
            out[kind][name] = _weap_state(m, zb, path)
    for name, path in sorted(cat['equipment'].items()):
        here = bool(m.find_tags('eqip', path))
        out['equipment'][name] = {'resident': here, 'need': 'ok' if here else 'import'}
    out['grenades'] = _grenades(m, registry)
    return out


def _section(title, rows, mission_list=None):
    imp = [n for n, v in rows.items() if v['need'] == 'import']
    geo = [n for n, v in rows.items() if v['need'] == 'geometry']
    print("   %-10s %2d/%d ready" % (title, len(rows) - len(imp) - len(geo), len(rows)))
    if imp:
        print("      IMPORT               : %s" % ", ".join(sorted(imp)))
    if geo:
        print("      resident, NO geometry: %s" % ", ".join(sorted(geo)))
    if mission_list is not None:
        # halo.json's mission lists use the ALIAS names (CONFIG['weapon_aliases'] maps
        # Magnum -> Pistol), so compare canonically or every level reports a phantom
        # "offers Magnum but cannot deliver" beside a phantom "delivers Pistol".
        offered = {ALIASES.get(n, n) for n in mission_list}
        deliverable = {n for n, v in rows.items() if v['need'] == 'ok'}
        gone = sorted(offered - deliverable)
        spare = sorted(deliverable - offered)
        if gone:
            print("      halo.json OFFERS but map cannot deliver: %s" % ", ".join(gone))
        if spare:
            print("      map delivers but halo.json does not offer: %s" % ", ".join(spare))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('levels', nargs='*', default=[])
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--offers', action='store_true',
                    help="cross-check halo.json's per-mission lists against the map")
    a = ap.parse_args()

    cat = catalogue()
    registry = HP.PluginRegistry(_plugins_dir(), ["Halo3MCC", "Halo3"])
    levels = a.levels or LEVELS
    everything = {}
    for lvl in levels:
        r = survey(lvl, cat, registry)
        if r is not None:
            everything[lvl] = r

    if a.json:
        print(json.dumps(everything, indent=1))
        return 0

    print("catalogue: %d weapon(s), %d turret(s), %d equipment, %d grenade(s)\n"
          % (len(cat['weapons']), len(cat['turrets']),
             len(cat['equipment']), len(cat['grenades'])))
    for lvl, r in everything.items():
        mid = MISSION_OF.get(lvl)
        mission = cat['missions'].get(mid, {}) if a.offers else {}
        print("#### %s  (%s)" % (lvl, mid))
        _section("weapons", r['weapons'], mission.get('weapons') if a.offers else None)
        _section("turrets", r['turrets'], mission.get('turret') if a.offers else None)
        _section("equipment", r['equipment'],
                 mission.get('equipment') if a.offers else None)
        _section("grenades", r['grenades'],
                 mission.get('grenades') if a.offers else None)
        print()

    print("=== union across the surveyed levels ===")
    for kind in ('weapons', 'turrets', 'equipment', 'grenades'):
        need = sorted({n for r in everything.values()
                       for n, v in r[kind].items() if v['need'] != 'ok'})
        print("%-10s needing work somewhere (%d): %s"
              % (kind, len(need), ", ".join(need) or "none"))
    return 0


def _plugins_dir():
    """The Assembly plugins folder the enhancer is configured with, without importing
    the GUI: settings.json sits next to halo.json."""
    try:
        with open(os.path.join(_tool_dir(), 'settings.json'), encoding='utf-8') as f:
            return json.load(f).get('assembly_plugins_dir')
    except Exception:
        return None


if __name__ == '__main__':
    raise SystemExit(main())
