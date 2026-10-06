r"""Halo 1: every enemy actor variant RESIDENT in every campaign level (2026-10-06).

User: "every enemy and its variants in every H1 map". Scoping (memory
h1-all-enemies-every-map): tag memory is no limit (MCC H1 = 64 MiB, worst level ~22 MB
with everything); the 64-entry Actor Palette is (tool appends child scenario palettes).

WHAT IS BUILT IN. 40 'root' variants: every enemy actv of the ten levels (Elite, Grunt,
Jackal, Hunter, Flood, Sentinel) that no other variant names as its Major Variant, minus
the Grunt flee variants (user: not needed). The 9 majors come along with their minors.
The build tool includes every tag anything references, so a root gets in by either
  1. ANCHOR: the 20 shared kit slots (characters\enhancer\slot NN) each name one root
     as their Major Variant -- the same 20 roots in every level, no palette entry. The
     patcher's fill_slot overwrites the ref later; the tag stays in the map;
  2. PALETTE: the level's remaining missing roots are APPENDED to its Actor Palette
     (no existing index moves).
The anchor set is chosen greedily so every level fits (plan file, see below).

Once resident, a variant spawns by REPOINTING a palette entry at patch time
(h1_enemy_test_map does this) or by filling a slot (fill_slot copies any actv in the map).

    python h1_all_enemies.py plan [--replan]   compute / show the plan (h1_all_enemies_plan.json)
    python h1_all_enemies.py test --level a10  kit edit -> build -> kit put back -> TEST map
                                               (every Covenant squad cycled over the 40 roots,
                                               player god shield) -> halo1\maps\<lvl>_allenemies_test.map
    python h1_all_enemies.py test --level a10 --factions [--reuse-build]
                                               v2: one faction per encounter (explicit team),
                                               a Hunter squad first in every Covenant one
    python h1_all_enemies.py verify --map M    are all roots + majors in a built map?
    (h1_all_enemies_test.cmd deploy|restore [level] swaps the test map in / out)
"""
import argparse
import json
import os
import shutil
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import paths                       # noqa: E402
import h1_loosetag as L            # noqa: E402
import h1_kit_variants as kit      # noqa: E402
import h1_variant_slots as vs      # noqa: E402
import halo_patch                  # noqa: E402

BS = '\\'
LEVELS = ('a10', 'a30', 'a50', 'b30', 'b40', 'c10', 'c20', 'c40', 'd20', 'd40')
INDEX = os.path.join(ROOT, 'h1_actv_index.json')
PLAN = os.path.join(HERE, 'h1_all_enemies_plan.json')
MAPS = os.path.join(os.path.dirname(ROOT), 'halo1', 'maps')
ACTOR_PALETTE, PALETTE_MAX = 0x420, 64
ENCOUNTERS, ENC_SZ, SQUADS, SQ_SZ, LOCS, LOC_SZ = 0x42C, 0xB0, 0x80, 0xE8, 0xD0, 0x1C
SQ_TYPE, LOC_TYPE = 0x20, 0x18
ENEMY_SPECIES = ('elite', 'grunt', 'jackal', 'hunter', 'flood', 'sentinel')
COVENANT = ('elite', 'grunt', 'jackal', 'hunter')
BACKUP = '.before_allenemies'


def species(name):
    p = name.split(BS)
    return p[1] if len(p) > 2 and p[0] == 'characters' else ''


def is_enemy(name):
    return any(species(name).startswith(s) for s in ENEMY_SPECIES)


# ----------------------------------------------------------------------------- plan
def _palette(m):
    sb = m.tags[[k for k in m.tags if k[0] == 'scnr'][0]]
    n = m.u32(sb + ACTOR_PALETTE)
    p = (m.u32(sb + ACTOR_PALETTE + 4) - m.magic) & 0xFFFFFFFF
    return [m.tag_name_by_id(m.u32(p + i * 16 + 12)) for i in range(n)]


def make_plan():
    idx = json.load(open(INDEX))['actv']
    present = {lv: set() for lv in LEVELS}
    major = {}
    for e in idx:
        if 'enhancer' in e['name']:
            continue
        present[e['level']].add(e['name'])
        if e['major']:
            major[e['name']] = e['major']
    every = set().union(*present.values())
    enemies = sorted(n for n in every if is_enemy(n) and ' flee ' not in n)
    majors = sorted(set(major[n] for n in enemies if n in major))
    roots = [n for n in enemies if n not in majors]
    palette = {}
    for lv in LEVELS:
        import h1_rebuild_all as rb
        base = halo_patch.existing_baseline(os.path.join(MAPS, lv + '.map'),
                                            rb.baseline_root(), rb.SUBDIR)
        m = halo_patch.open_map(base, 'Halo 1')
        palette[lv] = len(_palette(m))
    need = {lv: set(r for r in roots if r not in present[lv]) for lv in LEVELS}
    free = {lv: PALETTE_MAX - palette[lv] for lv in LEVELS}
    anchors = []
    for _ in range(vs.SLOTS_PER_LEVEL):
        def score(a):
            short = [max(0, len(need[lv] - set(anchors) - {a}) - free[lv]) for lv in LEVELS]
            return (sum(short), max(short), -sum(a in need[lv] for lv in LEVELS))
        anchors.append(min(sorted(set(roots) - set(anchors)), key=score))
    adds = {lv: sorted(need[lv] - set(anchors)) for lv in LEVELS}
    plan = dict(roots=roots, majors=majors, anchors=anchors, palette_adds=adds,
                built_palette=palette)
    with open(PLAN, 'w') as f:
        json.dump(plan, f, indent=1)
    return plan


def load_plan(replan=False):
    if replan or not os.path.isfile(PLAN):
        return make_plan()
    return json.load(open(PLAN))


def show(plan):
    print('%d roots, %d majors ride along, %d anchors (slot Major Variant):' % (
        len(plan['roots']), len(plan['majors']), len(plan['anchors'])))
    for i, a in enumerate(plan['anchors'], 1):
        print('   slot %02d -> %s' % (i, a))
    for lv in LEVELS:
        n, add = plan['built_palette'][lv], len(plan['palette_adds'][lv])
        print('%s palette %d + %d = %d / %d%s' % (lv, n, add, n + add, PALETTE_MAX,
                                                  '' if n + add <= PALETTE_MAX else '  OVER'))


# ----------------------------------------------------------------------------- kit
def _scenario(lv):
    return os.path.join(paths.HCEEK, 'tags', 'levels', lv, lv + '.scenario')


def kit_files(levels):
    return [kit.tag_file(vs.slot_path(i)) for i in range(1, vs.SLOTS_PER_LEVEL + 1)] + \
           [_scenario(lv) for lv in levels]


def kit_backup(levels):
    for f in kit_files(levels):
        if os.path.exists(f + BACKUP):
            raise SystemExit('%s exists -- a previous run was not restored' % (f + BACKUP))
    for f in kit_files(levels):
        shutil.copy2(f, f + BACKUP)


def kit_restore(levels):
    for f in kit_files(levels):
        if os.path.exists(f + BACKUP):
            shutil.copy2(f + BACKUP, f)
            os.remove(f + BACKUP)


def kit_apply(plan, levels):
    missing = [r for r in plan['roots'] if not os.path.isfile(kit.tag_file(r))]
    if missing:
        raise SystemExit('not in the kit: %s' % missing)
    for i, anchor in enumerate(plan['anchors'], 1):
        head, body, refs, colours = kit.read(vs.slot_path(i))
        refs[0x24] = anchor
        body[0x24:0x28] = kit.GROUPS[0x24]
        kit.write(vs.slot_path(i), head, body, refs, colours)
    for lv in levels:
        sp = _scenario(lv)
        data = bytearray(open(sp, 'rb').read())
        have = set(L.read_block_paths(data, paths.SCNR_XML, ACTOR_PALETTE))
        added = 0
        for p in plan['palette_adds'][lv]:
            if p not in have:
                L.insert_block_element(data, paths.SCNR_XML, ACTOR_PALETTE,
                                       L._tagref(b'actv', p), p)
                added += 1
        open(sp, 'wb').write(data)
        print('%s: 20 slot anchors, %d palette entries appended' % (lv, added))


def build(lv):
    r = subprocess.run([sys.executable, os.path.join(HERE, 'h1_rebuild_all.py'), '--maps', lv,
                        '--no-ship'], capture_output=True, text=True)
    if 'DONE: 1 ok' not in r.stdout:
        print(r.stdout[-2000:], r.stderr[-800:])
        raise SystemExit('build failed')
    return os.path.join(paths.HCEEK, 'maps', lv + '.map')


# ----------------------------------------------------------------------------- map side
def verify(m, plan):
    actv = set(n for c, n in m.tags if c == 'actv')
    lost = [n for n in plan['roots'] + plan['majors'] if n not in actv]
    print('resident: %d of %d roots + majors%s' % (
        len(plan['roots']) + len(plan['majors']) - len(lost),
        len(plan['roots']) + len(plan['majors']), ('; MISSING ' + ', '.join(lost)) if lost else ''))
    return not lost


def _elems(m, at, size):
    n = m.u32(at)
    p = (m.u32(at + 4) - m.magic) & 0xFFFFFFFF
    return [p + i * size for i in range(n)]


def _test_order(roots):
    """Interleave the roots species by species, so the first squads show every species."""
    by = {}
    for r in roots:
        by.setdefault(species(r), []).append(r)
    order = ['hunter', 'floodcombat elite', 'sentinel', 'floodcarrier', 'jackal',
             'floodcombat_human', 'flood_infection', 'elite', 'grunt']
    order += sorted(s for s in by if s not in order)
    out = []
    while any(by.values()):
        for s in order:
            if by.get(s):
                out.append(by[s].pop(0))
    return out


FACTIONS = {                       # scnr encounter Team Index (+0x24)
    'covenant': (3, ('elite', 'grunt', 'jackal', 'hunter')),
    'flood': (4, ('flood',)),
    'sentinel': (5, ('sentinel',)),
}
ENC_TEAM = 0x24
KEEP_ENCOUNTERS = ('cryo_bane',)    # a10 tutorial actor: invulnerable, scripted, erased


def make_test(m, plan, factions=False):
    """Repoint the level's Covenant squads (and Covenant starting-location overrides).
    Default (v1): every squad cycles over the 40 roots -> mixed encounters.
    factions (v2): each enemy encounter becomes ONE faction (Covenant / Flood / Sentinel in
    turn, team set explicitly), its squads cycling over that faction's roots, and every
    Covenant encounter's first squad a Hunter -- a10 v1 showed the team is per ENCOUNTER.
    Slot palette entries are repointed at the anchors so all 40 are in the palette; the
    player gets a god shield (h1_enemy_test_map's)."""
    import h1_enemy_test_map as etm
    d = m.data
    ids = etm.tag_ids(m)
    sb = m.tags[[k for k in m.tags if k[0] == 'scnr'][0]]
    pal_at = _elems(m, sb + ACTOR_PALETTE, 16)
    names = {v[0]: k[1] for k, v in ids.items()}
    pal = [names.get(struct.unpack_from('<I', d, e + 12)[0], '') for e in pal_at]
    for i, anchor in enumerate(plan['anchors'], 1):
        j = pal.index(vs.slot_path(i))
        tid, nptr = ids[('actv', anchor)]
        struct.pack_into('<I', d, pal_at[j] + 4, nptr)
        struct.pack_into('<I', d, pal_at[j] + 12, tid)
        pal[j] = anchor
    where = {}
    for j, p in enumerate(pal):
        where.setdefault(p, j)
    cycle = _test_order(plan['roots'])
    lost = [r for r in cycle if r not in where]
    if lost:
        raise SystemExit('not in the palette: %s' % lost)
    cov = set(j for j, p in enumerate(pal) if species(p).startswith(COVENANT))
    if factions:
        cycles = {f: [r for r in cycle if species(r).startswith(sp)]
                  for f, (_t, sp) in FACTIONS.items()}
        turn = ['sentinel', 'flood', 'covenant']   # a10: crossfire_anti (3rd) = Covenant
        pos = {f: 0 for f in FACTIONS}
    k, n_enc, log = 0, 0, []
    for enc in _elems(m, sb + ENCOUNTERS, ENC_SZ):
        ename = bytes(d[enc:enc + 32]).split(b'\0')[0].decode('latin-1')
        if ename in KEEP_ENCOUNTERS:
            continue
        sqs = [sq for sq in _elems(m, enc + SQUADS, SQ_SZ)
               if struct.unpack_from('<h', d, sq + SQ_TYPE)[0] in cov]
        if not sqs:
            continue
        if factions:
            fac = turn[n_enc % len(turn)]
            n_enc += 1
            struct.pack_into('<h', d, enc + ENC_TEAM, FACTIONS[fac][0])
            log.append('%s = %s' % (ename, fac.upper()))
        for si, sq in enumerate(sqs):
            t = struct.unpack_from('<h', d, sq + SQ_TYPE)[0]
            if not factions:
                new = cycle[k % len(cycle)]
                k += 1
            elif fac == 'covenant' and si == 0:
                new = next(r for r in cycles['covenant'] if species(r) == 'hunter')
            else:
                c = cycles[fac]
                new = c[pos[fac] % len(c)]
                pos[fac] += 1
                if fac == 'covenant' and species(new) == 'hunter':
                    new = c[pos[fac] % len(c)]
                    pos[fac] += 1
            struct.pack_into('<h', d, sq + SQ_TYPE, where[new])
            for loc in _elems(m, sq + LOCS, LOC_SZ):
                if struct.unpack_from('<h', d, loc + LOC_TYPE)[0] in cov:
                    struct.pack_into('<h', d, loc + LOC_TYPE, where[new])
            log.append('   %s: %s x%d -> %s' % (
                ename, pal[t].rsplit(BS, 1)[-1], struct.unpack_from('<h', d, sq + 0x7C)[0],
                new.rsplit(BS, 1)[-1]))
    coll = m.tags[('coll', etm.COLL)]
    for off, v in ((etm.MAX_BODY, 1e6), (etm.MAX_SHIELD, 1e6), (etm.LEAK, 0.0),
                   (etm.STUN, 0.0), (etm.RECHARGE, 0.1)):
        struct.pack_into('<f', d, coll + off, v)
    return log


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('plan')
    p.add_argument('--replan', action='store_true')
    t = sub.add_parser('test')
    t.add_argument('--level', default='a10')
    t.add_argument('--factions', action='store_true',
                   help='v2: one faction per encounter, explicit team, Hunters up front')
    t.add_argument('--reuse-build', action='store_true',
                   help='skip the kit build: the kit maps folder <level>.map is already the anchor build')
    v = sub.add_parser('verify')
    v.add_argument('--map', required=True)
    a = ap.parse_args()
    if a.cmd == 'plan':
        show(load_plan(a.replan))
        return
    plan = load_plan()
    if a.cmd == 'verify':
        sys.exit(0 if verify(halo_patch.open_map(a.map, 'Halo 1'), plan) else 1)
    lv = a.level
    out = os.path.join(MAPS, lv + '_allenemies_test.map')
    if a.reuse_build:
        shutil.copy2(os.path.join(paths.HCEEK, 'maps', lv + '.map'), out)
    else:
        kit_backup([lv])
        try:
            kit_apply(plan, [lv])
            shutil.copy2(build(lv), out)
        finally:
            kit_restore([lv])
            print('kit put back (slots + %s scenario)' % lv)
    m = halo_patch.open_map(out, 'Halo 1')
    print('palette in the build: %d' % len(_palette(m)))
    if not verify(m, plan):
        raise SystemExit('not every variant got in -- test map not finished')
    log = make_test(m, plan, a.factions)
    m.save(out)
    for line in log if a.factions else log[:25]:
        print('   ' + line)
    print('wrote %s' % out)


if __name__ == '__main__':
    main()
