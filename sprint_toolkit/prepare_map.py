r"""Prepare an ODST map for the enhancer: rebuild it, then bake in everything the
restored weapons need. One command per level.

WHAT THIS BAKES, AND WHY IT IS ONE-TIME
`apply_run` patches FROM `<map>.bak` and saves the whole buffer, so anything written
into the baseline survives every future patch -- verified by round-tripping a prepared
map through the same open/save cycle. So none of this belongs in the patcher:

  1. rebuild with the Editing Kit      (brings the tags AND their resources in)
  2. residency for every weapon        (object_new silently refuses a tag whose bit is
                                        clear in the zone tag's Required Tag Pool)
  3. HUD repoint for weapons whose     (ODST never shipped ui\chud\magnum or \smg, so
     chud ODST never shipped            they come back with a NULL HUD Interface)
  4. optional palette slots            (placements index the palette; grants do not)

WHAT YOU MUST DO FIRST, ONCE PER LEVEL, IN GUERILLA
Open `tags\levels\atlas\<map>\<map>.scenario` and give each cut weapon a Player
Starting Profile whose Primary Weapon is that weapon. A placeholder row the level never
reads is fine, and adding new rows is fine. Without that, `tool` pulls the weapon's tags
in but NOT its geometry, and the map black-screens when the tag is marked resident --
which this script checks for and refuses to ship.

    python prepare_map.py sc150
    python prepare_map.py --all
    python prepare_map.py sc150 --verify-only
    python prepare_map.py sc150 --placeable battle_rifle

MCC MUST BE CLOSED: it holds the map files open and every write fails.
"""
import argparse
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import halo_patch as HP                                          # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h3_zone_pools as Z                                        # noqa: E402
import h3_raw_residency as R                                     # noqa: E402
import odst_ek_build as EK                                       # noqa: E402
import map_vault as V                                            # noqa: E402

GAME = 'Halo 3: ODST'
WEAP_HUD = 0x418                    # weap "HUD Interface" tagRef; datum at +0xC
WEAP_FIRST_PERSON = 0x40C           # block; a player weapon has an fp model here
WEAP_MAGNIFICATION = 0x32E          # int16 "Magnification Levels" -- 0 means no scope

# Preference order when a weapon needs a borrowed HUD. Only donors with the SAME
# magnification level count are eligible, so a weapon without a scope never inherits a
# scoped HUD: the magnum and the SMG have 0 levels, while ODST's automag and
# smg_silenced have 1, and borrowing from those promised a zoom the weapon does not
# have. assault_rifle is ODST's plain human HUD and comes first for that reason.
HUD_DONORS = ('assault_rifle', 'smg_silenced', 'automag', 'battle_rifle',
              'plasma_rifle', 'plasma_pistol', 'shotgun', 'spike_rifle',
              'needler', 'brute_shot', 'sniper_rifle', 'carbine')


def _weap(m, base):
    """The weap tag whose filename is exactly `base`."""
    return next((t for t in m.tags if t.get('class') == 'weap' and t.get('name')
                 and str(t['name']).rsplit('\\', 1)[-1].lower() == base.lower()), None)


def geometry(m, zone_base, base):
    """(mode chunks, jmad chunks) owned by this weapon's family.

    A weapon whose model and animation own no chunks has no geometry in the map: the
    scenario references it but `tool` never gathered it. Marking such a tag resident is
    what black-screens the game, so this is the gate everything else hangs off.
    """
    owned = Z.chunks_by_tag(m, zone_base)
    mode = 0
    # Match a whole path segment, not a substring: `smg` must not sweep in
    # `smg_silenced`, which is a different weapon that is always present.
    want = {base.lower(), 'fp_' + base.lower(), 'lod_' + base.lower()}
    for t in m.tags:
        nm = (t.get('name') or '').lower()
        if (want & set(nm.split('\\'))) and t['class'] == 'mode':
            mode += len(owned.get(t['index'], []))
    # Animations must be followed, not name-matched: a variant shares another weapon's
    # graph -- plasma_rifle_red animates from fp_plasma_rifle, sentinel_gun from
    # fp_sentinel_beam -- so counting jmad chunks under its own name reports zero and
    # looks broken when it is perfectly fine.
    jmad = 0
    wt = _weap(m, base)
    if wt:
        blk = HP._block_base(m, wt['base'] + WEAP_FIRST_PERSON)
        n = m.i32(wt['base'] + WEAP_FIRST_PERSON)
        for i in range(max(0, n)) if blk else []:
            aid = m.u32(blk + i * 0x20 + 0x10 + 0xC)     # First Person Animations
            if aid == 0xFFFFFFFF:
                continue
            jmad += len(owned.get(aid & 0xFFFF, []))
    return mode, jmad


def player_weapons(m):
    """Every weapon in the map a player can hold, by tag basename.

    The test is structural: a player weapon has a first-person model in its `First
    Person` block, which is exactly what separates the real weapons from turrets and
    vehicle guns. Deriving this per map matters because levels differ in what they
    carry -- a fixed list built from one level would silently miss whatever another
    level is short of.
    """
    out = []
    for t in m.tags:
        if t.get('class') != 'weap' or not t.get('name'):
            continue
        base = t['base']
        n = m.i32(base + WEAP_FIRST_PERSON)
        blk = HP._block_base(m, base + WEAP_FIRST_PERSON)
        if not blk or n <= 0:
            continue
        if m.u32(blk + 0xC) == 0xFFFFFFFF:              # no fp model = not holdable
            continue
        out.append(str(t['name']).rsplit('\\', 1)[-1])
    return sorted(set(out))


def ek_weapon_universe():
    """Player-weapon basenames the Editing Kit can supply, for reporting what a level
    is missing. `objects\\weapons\\<class>\\<name>\\<name>.weapon`."""
    root = os.path.join(EK.EK, 'tags', 'objects', 'weapons')
    found = set()
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if f.lower().endswith('.weapon') and f[:-7].lower() == os.path.basename(dirpath).lower():
                found.add(f[:-7])
    return sorted(found)


def present(m, zone_base):
    """Player weapons in this map, split by whether they actually have geometry."""
    ok, missing = [], []
    for w in player_weapons(m):
        mode, jmad = geometry(m, zone_base, w)
        (ok if (mode and jmad) else missing).append(w)
    return ok, missing


def magnification(m, base_weap):
    return struct.unpack_from('<h', m.data, base_weap + WEAP_MAGNIFICATION)[0]


def fix_huds(m, weapons, overrides=None):
    """Give a weapon with a NULL HUD Interface one from a weapon that scopes the same.

    ODST ships no `ui\\chud\\magnum` and no `ui\\chud\\smg`, so those come back from
    Halo 3 with no ammo counter or reticle. The first fix borrowed from their ODST
    counterparts -- but automag and smg_silenced have 1 magnification level where the
    magnum and SMG have 0, so the borrowed HUD advertised a scope the weapon does not
    have. Donors are therefore filtered to the same magnification count.
    """
    overrides = overrides or {}
    chuds = {str(t['name']).rsplit('\\', 1)[-1].lower(): t for t in m.tags
             if t.get('class') == 'chdt' and t.get('name')}
    done = []
    for w in weapons:
        wt = _weap(m, w)
        if not wt:
            continue
        want_mag = magnification(m, wt['base'])
        cur = m.u32(wt['base'] + WEAP_HUD + 0xC)
        if cur != 0xFFFFFFFF:
            # Repair a HUD that scopes differently, not just a missing one: an earlier
            # pass gave the magnum ui\chud\automag, which advertises a 1x scope the
            # magnum does not have.
            cur_name = HP._tag_name_by_id(m, cur)
            donor = _weap(m, str(cur_name).rsplit('\\', 1)[-1]) if cur_name else None
            if donor is None and cur_name and str(cur_name).endswith('carbine'):
                donor = _weap(m, 'covenant_carbine')
            if donor is None or magnification(m, donor['base']) == want_mag:
                continue                               # correct, or cannot judge
            print('    HUD  %-16s had %s (%dx), replacing'
                  % (w, str(cur_name).rsplit('\\', 1)[-1],
                     magnification(m, donor['base'])))
        pick = overrides.get(w)
        if not pick:
            for cand in HUD_DONORS:
                ct = chuds.get(cand)
                dt = _weap(m, cand)
                if not ct:
                    continue
                # carbine's chud is named for a weapon called covenant_carbine
                if dt is None and cand == 'carbine':
                    dt = _weap(m, 'covenant_carbine')
                if dt is None or magnification(m, dt['base']) != want_mag:
                    continue
                pick = cand
                break
        ct = chuds.get((pick or '').lower())
        if not ct:
            print('    !! no HUD donor with %d magnification level(s) for %s'
                  % (want_mag, w))
            continue
        datum = HP._h3_tag_datum(m, 'chdt', str(ct['name']))
        struct.pack_into('<I', m.data, wt['base'] + WEAP_HUD + 0xC, datum)
        print('    HUD  %-16s NULL -> ui\\chud\\%s   (%d magnification level(s))'
              % (w, pick, want_mag))
        done.append(w)
    return done


# Squads 0x3B8 elem 0x6C; each squad holds Designer Cells 0x54 and Templated Cells
# 0x60, both 0x84 elements. A cell's Initial Weapon / Initial Secondary are one-entry
# tagblocks holding an int16 palette INDEX at +0xC -- the SAME Weapon Palette the
# placements index.
_SQUADS = (0x3B8, 0x6C)
_CELL_BLOCKS = ((0x54, 0x84), (0x60, 0x84))
_CELL_WEAPON_FIELDS = (0x20, 0x2C)
_CELL_IDX_AT = 0xC


def palette_in_use(m):
    """Palette indices something already depends on: placements AND AI loadouts.

    Repurposing a slot an enemy squad references would silently rearm the enemies --
    the squad cells index this same palette, so "no placement uses it" is not enough
    to call a slot free.
    """
    lay = HP._MAP_WEAPONS[GAME]
    scnr = HP._scnr_base(m)
    used = set()
    woff, wes = lay['weapons']
    wn, wbase = m.i32(scnr + woff), HP._block_base(m, scnr + woff)
    for i in range(max(0, wn)) if wbase else []:
        used.add(struct.unpack_from('<h', m.data, wbase + i * wes)[0])
    soff, ses = _SQUADS
    sn, sbase = m.i32(scnr + soff), HP._block_base(m, scnr + soff)
    for i in range(max(0, sn)) if sbase else []:
        se = sbase + i * ses
        for coff, ces in _CELL_BLOCKS:
            cn, cbase = m.i32(se + coff), HP._block_base(m, se + coff)
            for c in range(max(0, cn)) if cbase else []:
                ce = cbase + c * ces
                for foff in _CELL_WEAPON_FIELDS:
                    fn, fbase = m.i32(ce + foff), HP._block_base(m, ce + foff)
                    for k in range(max(0, fn)) if fbase else []:
                        used.add(struct.unpack_from(
                            '<h', m.data, fbase + k * 0x10 + _CELL_IDX_AT)[0])
    used.discard(-1)
    return used


def grow_palette(m, datums):
    """Relocate the Weapon Palette into partition slack and append entries.

    Stealing "unused" slots cannot work: sc150 has 17 slots against 23 player weapons,
    so every steal costs another weapon its place. Growing is the only way to have them
    all, and H3 stores tagblock pointers as realVA>>2 through the partition table, so a
    grown block has to move into an existing zero run rather than extend in place --
    the same dance _append_equipment_palette does for equipment.

    Returns {datum: new index}, or None if there is no run big enough.
    """
    lay = HP._MAP_WEAPONS[GAME]
    scnr = HP._scnr_base(m)
    poff, pes = lay['palette']
    pc, pbase = max(0, m.i32(scnr + poff)), HP._block_base(m, scnr + poff)
    if not pbase or not datums:
        return {}
    got = HP._h3_reserve(m, [(pc + len(datums)) * pes])
    if got is None:
        return None
    dest = got[0]
    m.data[dest:dest + pc * pes] = m.data[pbase:pbase + pc * pes]
    tmpl = bytes(m.data[pbase:pbase + pes])          # a weap tagRef, for the group id
    out = {}
    for j, datum in enumerate(datums):
        off = dest + (pc + j) * pes
        m.data[off:off + pes] = tmpl
        struct.pack_into('<I', m.data, off + lay['pal_id_at'], datum)
        out[datum] = pc + j
    struct.pack_into('<i', m.data, scnr + poff, pc + len(datums))
    struct.pack_into('<I', m.data, scnr + poff + 4, m.off2data(dest))
    return out


def make_placeable(m, weapons):
    """Give every named weapon a Weapon Palette entry, growing the block to fit.

    A starting profile references a weapon by tagRef, but a PLACEMENT indexes the
    palette -- so a weapon missing from it can be put in the player's hands and never
    left on the ground. The palette is also what AI squad cells index, which is why
    slots are never repurposed here: an apparently free slot may be what an enemy
    carries, and 17 slots cannot hold 23 weapons anyway.
    """
    lay = HP._MAP_WEAPONS[GAME]
    scnr = HP._scnr_base(m)
    poff, pes = lay['palette']
    pc, pbase = max(0, m.i32(scnr + poff)), HP._block_base(m, scnr + poff)
    have = {str(HP._tag_name_by_id(m, m.u32(pbase + i * pes + 0xC)) or '')
            .rsplit('\\', 1)[-1].lower() for i in range(pc)}
    want, datums = [], []
    for w in weapons:
        if w.lower() in have:
            continue
        wt = _weap(m, w)
        if not wt:
            continue
        d = HP._h3_tag_datum(m, 'weap', str(wt['name']))
        if d is not None:
            want.append(w)
            datums.append(d)
    if not want:
        print('    palette: all %d weapon(s) already present' % len(weapons))
        return []
    added = grow_palette(m, datums)
    if added is None:
        print('    !! no partition slack to grow the palette; %d weapon(s) stay '
              'grant-only: %s' % (len(want), ', '.join(want)))
        return []
    print('    palette: grew %d -> %d, added %s'
          % (pc, pc + len(want), ', '.join(want)))
    return want


def report(m, zone_base, weapons):
    """The table to read before shipping a map."""
    g = [e for lab, e in Z.zonesets(m, zone_base) if lab.startswith('GLOBAL')][0]
    pool = Z._pool(m, g, Z.ZS_REQUIRED_TAG_POOL)
    lay = HP._MAP_WEAPONS[GAME]
    scnr = HP._scnr_base(m)
    poff, pes = lay['palette']
    pc, pbase = max(0, m.i32(scnr + poff)), HP._block_base(m, scnr + poff)
    pal = {str(HP._tag_name_by_id(m, m.u32(pbase + i * pes + 0xC)) or '')
           .rsplit('\\', 1)[-1].lower() for i in range(pc)}
    print('    %-16s %-9s %-9s %-16s %-8s %s'
          % ('weapon', 'geometry', 'resident', 'HUD', 'palette', 'zoom'))
    allgood = True
    for w in weapons:
        wt = _weap(m, w)
        if not wt:
            print('    %-16s ABSENT' % w)
            allgood = False
            continue
        mode, jmad = geometry(m, zone_base, w)
        res = Z._has(pool, wt['index'])
        hud_id = m.u32(wt['base'] + WEAP_HUD + 0xC)
        hud = HP._tag_name_by_id(m, hud_id) if hud_id != 0xFFFFFFFF else None
        mag = magnification(m, wt['base'])
        # A HUD borrowed from a weapon that scopes differently is the misleading case.
        donor = _weap(m, str(hud).rsplit('\\', 1)[-1]) if hud else None
        if donor is None and hud and str(hud).endswith('carbine'):
            donor = _weap(m, 'covenant_carbine')
        mismatch = bool(donor and magnification(m, donor['base']) != mag)
        good = bool(mode and jmad and res and hud) and not mismatch
        allgood &= good
        print('    %-16s %-9s %-9s %-16s %-8s %dx  %s'
              % (w, 'm%d/a%d' % (mode, jmad), 'yes' if res else 'NO',
                 str(hud).rsplit('\\', 1)[-1] if hud else 'NULL',
                 'yes' if w.lower() in pal else 'no', mag,
                 '' if good else ('<-- HUD scopes differently' if mismatch else '<-- check')))
    return allgood


def prepare(name, do_build=True, placeable=(), verify_only=False,
            hud_overrides=None):
    path = os.path.join(EK.GAME, name + '.map')
    if not verify_only and do_build:
        print('  building %s (this takes ~4 minutes and is quiet for long '
              'stretches)' % name)
        if not EK.build(name):
            print('  !! build failed; leaving %s alone' % name)
            return False
        EK.install(name)                       # also repoints .bak and prunes copies

    m = HP.open_map(path, GAME)
    zb = Z._zone_tag(m)['base']
    ok, missing = present(m, zb)
    print('  player weapons in this map: %d with geometry, %d without'
          % (len(ok), len(missing)))
    for w in missing:
        print('    !! %s has NO geometry -- its scenario profile is missing, so it '
              'would black-screen if marked resident' % w)
    absent = [w for w in ek_weapon_universe()
              if w not in ok and w not in missing and not _weap(m, w)]
    if absent:
        print('  not in this map at all (add a starting profile in Guerilla to restore '
              'any you want): %s' % ', '.join(absent))
    if verify_only:
        report(m, zb, ok + missing)
        return not missing

    # Residency: every palette weapon, plus the restored ones (which are not in the
    # palette). --only-resolved is what keeps a tag with a dead chunk out of the pool.
    lay = HP._MAP_WEAPONS[GAME]
    scnr = HP._scnr_base(m)
    poff, pes = lay['palette']
    pc, pbase = max(0, m.i32(scnr + poff)), HP._block_base(m, scnr + poff)
    wanted = [str(HP._tag_name_by_id(m, m.u32(pbase + i * pes + 0xC)) or '')
              .rsplit('\\', 1)[-1] for i in range(pc)]
    wanted = [w for w in wanted if w] + list(ok)
    added = 0
    for w in wanted:
        r = Z.load_always(m, zb, w, only_resolved=True)
        added += r.get('tags_added', 0) if r.get('ok') else 0
    print('    residency: %d weapon(s), %d tag bit(s) added' % (len(wanted), added))

    fix_huds(m, ok, hud_overrides)
    # Every weapon should be placeable, not just grantable: a starting profile
    # uses a tagRef but a placement indexes the palette, so a weapon missing from
    # it can be handed to the player but never left on the ground.
    make_placeable(m, [w for w in (placeable or ok) if w in ok])

    m.save(path)
    # .bak must carry the same preparation, or the first patch rebuilds without it.
    import shutil
    shutil.copy2(path, path + '.bak')
    print('    saved, and .bak updated to match')

    m2 = HP.open_map(path, GAME)
    good = report(m2, Z._zone_tag(m2)['base'], ok)
    print('  %s: %s' % (name, 'READY' if good and not missing else 'NEEDS ATTENTION'))
    return good and not missing


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('maps', nargs='*', help='map basenames, e.g. sc150')
    ap.add_argument('--all', action='store_true', help='every ODST level in halo.json')
    ap.add_argument('--skip-build', action='store_true',
                    help='the map is already built and installed')
    ap.add_argument('--verify-only', action='store_true', help='report, change nothing')
    ap.add_argument('--placeable', help='comma list to limit which weapons get a '
                                        'palette slot; default is every one that can')
    ap.add_argument('--hud', metavar='WEAPON=CHUD', action='append', default=[],
                    help='force a HUD donor instead of the magnification-matched pick')
    a = ap.parse_args(argv)
    names = V.maps_for(GAME) if a.all else a.maps
    if not names:
        ap.error('name at least one map, or pass --all')
    placeable = [w.strip() for w in a.placeable.split(',')] if a.placeable else []
    huds = dict(x.split('=', 1) for x in a.hud) if a.hud else {}
    results = {}
    for n in names:
        print('\n=== %s ===' % n)
        try:
            results[n] = prepare(n, not a.skip_build, placeable, a.verify_only,
                                 huds)
        except Exception as e:
            print('  !! %s' % e)
            results[n] = False
    print('\nsummary')
    for n, good in results.items():
        print('  %-8s %s' % (n, 'ready' if good else 'needs attention'))
    return 0 if all(results.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
