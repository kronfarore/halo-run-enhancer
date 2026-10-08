r"""The shieldless Jackal as KIT tags, resident in all ten Halo 1 scenarios (2026-10-08).

User rule: a Jackal given a two-handed or heavy weapon (Armed cards) loses its arm shield.
The enhancer decides that at patch time (h1_enemy_weapons.jackal_shield_rule points the
armed slot at '<jackal biped> shieldless'), but the tags themselves must be BUILT into the
maps: adding tags to a built Halo 1 map is a fatal error on load (2026-10-02, and again on
b30 2026-10-08 with these very tags).

What makes a Jackal shieldless, measured on b30 (probe 2, 2026-10-08, user: no shield, the
body takes the hits; an energy shield of 0 alone did nothing):
  * gbxmodel region 'shield': every normal look (base00) uses ~shield_off's geometry;
  * collision: the 'shield' region's node uses ~shield_off's BSP for every normal
    permutation, and the shield vitality is 0.

Tags written (beside the stock ones, which are never touched):
  characters\jackal\jackal shieldless.gbxmodel
  characters\jackal\jackal shieldless.model_collision_geometry
  characters\jackal\jackal shieldless.biped        (copy of jackal.biped)
  characters\jackal\jackal major shieldless.biped  (copy of jackal major.biped: the major
      keeps its own colour rows, ping interrupt 0.3 s / 9 ticks and unit flags)
Each level scenario gets both bipeds APPENDED to its bipeds palette (no index moves) and one
placement each with `not placed: automatically` -- it never spawns, it only makes tool
build the tags in (the weapon ports' recipe, h1-weapon-into-map). A '.before_shieldless'
copy of each scenario is kept beside it the first time.

    python h1_shieldless_jackal.py            (dry run: what would change)
    python h1_shieldless_jackal.py --write
"""
import argparse
import copy
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401

KIT = r'F:\SteamLibrary\steamapps\common\HCEEK\tags'
JACKAL = r'characters\jackal\jackal'
SHIELDLESS = ' shieldless'                       # = h1_enemy_weapons.SHIELDLESS
BIPEDS = (JACKAL, JACKAL + ' major')
LEVELS = ('a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40')
REGION, OFF = 'shield', '~shield_off'
LODS = ('superlow_geometry_block', 'low_geometry_block', 'medium_geometry_block',
        'high_geometry_block', 'superhigh_geometry_block')
BACKUP = '.before_shieldless'


def path(rel, ext):
    return os.path.join(KIT, rel + ext)


def save(tag, p, write):
    if write:
        if os.path.exists(p) and p.endswith('.scenario') and not os.path.exists(p + BACKUP):
            shutil.copy2(p, p + BACKUP)
        tag.serialize(filepath=p, temp=False, backup=False)


def make_model(write):
    from reclaimer.hek.defs.mod2 import mod2_def
    t = mod2_def.build(filepath=path(JACKAL, '.gbxmodel'))
    region = next(r for r in t.data.tagdata.regions.STEPTREE if r.name == REGION)
    perms = region.permutations.STEPTREE
    off = next(p for p in perms if p.name == OFF)
    for p in perms:
        if not p.name.startswith('~'):
            for k in LODS:
                setattr(p, k, getattr(off, k))
            print('   model: shield look %r -> %s' % (p.name, [getattr(p, k) for k in LODS]))
    save(t, path(JACKAL + SHIELDLESS, '.gbxmodel'), write)


def make_collision(write):
    from reclaimer.hek.defs.coll import coll_def
    t = coll_def.build(filepath=path(JACKAL, '.model_collision_geometry'))
    d = t.data.tagdata
    regions = d.regions.STEPTREE
    ri = next(i for i, r in enumerate(regions) if r.name == REGION)
    names = [p.name for p in regions[ri].permutations.STEPTREE]
    off = names.index(OFF)
    for n in d.nodes.STEPTREE:
        if n.region != ri:
            continue
        bsps = n.bsps.STEPTREE
        for i, nm in enumerate(names):
            if not nm.startswith('~') and i < len(bsps) and off < len(bsps):
                bsps[i] = copy.deepcopy(bsps[off])
                print('   collision: node %r permutation %r -> %s\'s BSP' % (n.name, nm, OFF))
    d.shield.maximum_shield_vitality = 0.0
    print('   collision: shield vitality -> 0')
    save(t, path(JACKAL + SHIELDLESS, '.model_collision_geometry'), write)


def make_bipeds(write):
    from reclaimer.hek.defs.bipd import bipd_def
    for src in BIPEDS:
        t = bipd_def.build(filepath=path(src, '.biped'))
        o = t.data.tagdata.obje_attrs
        o.model.filepath = JACKAL + SHIELDLESS
        o.collision_model.filepath = JACKAL + SHIELDLESS
        print('   biped %s -> model + collision %s' % ((src + SHIELDLESS).rsplit('\\', 1)[-1],
                                                     (JACKAL + SHIELDLESS).rsplit('\\', 1)[-1]))
        save(t, path(src + SHIELDLESS, '.biped'), write)


def make_resident(write):
    from reclaimer.hek.defs.scnr import scnr_def
    for lvl in LEVELS:
        p = path(r'levels\%s\%s' % (lvl, lvl), '.scenario')
        t = scnr_def.build(filepath=p)
        d = t.data.tagdata
        pal, places = d.bipeds_palette.STEPTREE, d.bipeds.STEPTREE
        changed = []
        for b in BIPEDS:
            name = b + SHIELDLESS
            names = [e.name.filepath.lower() for e in pal]
            if name.lower() in names:
                idx = names.index(name.lower())
            else:
                pal.append()
                pal[-1].name.filepath = name
                idx = len(pal) - 1
                changed.append('palette #%d' % idx)
            if any(x.type == idx for x in places):
                continue
            if len(places):
                places.append(copy.deepcopy(places[0]))
            else:
                places.append()
            x = places[len(places) - 1]
            x.type = idx
            x.name = -1
            x.not_placed.automatically = True
            changed.append('resident-only placement of #%d' % idx)
        print('   %s: %s' % (lvl, ', '.join(changed) or 'already resident'))
        if changed:
            t.filepath = p
            save(t, p, write)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    print('tags%s:' % ('' if a.write else ' (dry run)'))
    make_model(a.write)
    make_collision(a.write)
    make_bipeds(a.write)
    print('scenarios%s:' % ('' if a.write else ' (dry run)'))
    make_resident(a.write)
    if a.write:
        print('written. The ten-map rebuild builds them in (batched with the ports).')


if __name__ == '__main__':
    main()
