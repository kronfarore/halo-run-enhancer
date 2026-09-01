r"""Enemy-owned tags that are NOT the character tag, and whether any card touches them.

A `char` tag is only an enemy's BEHAVIOUR. Everything it hits you with lives elsewhere,
under the same `objects\characters\<family>\` folder but in another tag class:

    weap   the gun it carries        hunter\hunter_particle_cannon\...
    proj   what that gun fires       hunter\projectiles\...
    jpt!   its damage effects        elite\damage_effects\elite_melee
    hlmt   the model, and from Halo 2 on the VITALITY (New Damage Info)
    coll   Halo 1's vitality
    eqip   equipment it carries      engineer\...

`inherit_audit` and `coverage_audit` only ever look at char tags, so this whole surface
was invisible to both. The Hunter's fuel cannon is the obvious case — a weapon that
belongs to one enemy, in a class the enemy audits never open.

The family -> enemy mapping is DERIVED, not hardcoded: each enemy's own char tag names
its folder, so `objects\characters\hunter\ai\hunter*` claims the `hunter` family. A
folder no enemy claims is reported separately rather than silently dropped — that is
where a missing enemy would hide.

Usage:
    python sprint_toolkit/enemy_asset_audit.py                 # uncarded only
    python sprint_toolkit/enemy_asset_audit.py --all           # carded ones too
    python sprint_toolkit/enemy_asset_audit.py --enemy Hunter
"""
import argparse
import collections
import contextlib
import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_TOOL = os.path.dirname(_HERE)
os.chdir(_TOOL)
sys.path.insert(0, _TOOL)

with contextlib.redirect_stdout(io.StringIO()):
    import halo_enhancer as he                                     # noqa: E402
    import halo_patch as hp                                        # noqa: E402

B = chr(92)
CFG = json.load(open('settings.json', encoding='utf-8'))
_ROOT = CFG.get('mcc_root') or (
    r'C:\Program Files (x86)\Steam\steamapps\common'
    r'\Halo The Master Chief Collection')

CASES = [
    ('Halo 1', ['Halo1MCC', 'Halo1'], os.path.join(_ROOT, 'halo1', 'maps')),
    ('Halo 2', ['Halo2MCC', 'Halo2'],
     os.path.join(_ROOT, 'halo2', 'h2_maps_win64_dx11')),
    ('Halo 3', ['Halo3MCC', 'Halo3'], os.path.join(_ROOT, 'halo3', 'maps')),
    ('Halo 3: ODST', ['ODSTMCC', 'ODST'], os.path.join(_ROOT, 'halo3odst', 'maps')),
    ('Halo Reach', ['ReachMCC', 'Reach'], os.path.join(_ROOT, 'haloreach', 'maps')),
]

# Classes that hold a TUNABLE value. Everything else under a character's folder is
# art or physics -- shaders, bitmaps, models, particles, lights, animation graphs --
# and a card has nothing to say about it.
TUNABLE = {'weap', 'proj', 'jpt!', 'hlmt', 'coll', 'eqip', 'cntl', 'crea', 'bipd',
           'vehi', 'ltvl', 'mffn'}
# Of those, the ones worth reporting first: they carry damage, rate of fire, vitality.
PRIMARY = {'weap', 'proj', 'jpt!', 'hlmt', 'coll', 'eqip'}

# Halo 1 keeps its characters under a different root.
ROOTS = ('objects' + B + 'characters' + B, 'characters' + B)

# Sub-folders that hold props, gibs and cinematic doubles rather than anything a card
# would tune: severed limbs, dropped helmets, the Engineer's backpack bomb debris and
# its cinematic tentacle. They are enemy-owned and they are not gameplay.
NOISE_PARTS = ('garbage', 'cinematics', 'fx', 'engineer_parts', 'garlic')


# Tags that are enemy-owned, gameplay-shaped, and still not worth a card, each for a
# MEASURED reason rather than a hunch. Matched as a path substring, per game.
IGNORE = {
    'Halo 2': [
        # Every field reads 0 on 06a -- damage, radius, rider scale, duration, all of
        # it. It is the marker effect the charged bolt fires while winding up, not
        # something that hits you, so there is nothing an operator could scale.
        ('jpt!', 'sentinel_aggressor' + B + 'weapons' + B + 'charged_bolt'),
    ],
}


def is_ignored(game, cls, path):
    p = str(path).replace('/', B).lower()
    return any(c == cls and sub.lower() in p for c, sub in IGNORE.get(game, ()))


def is_noise(path):
    parts = str(path).replace('/', B).split(B)
    if any(p in NOISE_PARTS for p in parts):
        return True
    return any(p.endswith('_cin') or p.endswith('_cinematic') for p in parts)


def _iter_tags(m):
    """(class, name) for every tag, whatever the parser hands back.

    Halo 1's HaloMap keys a dict by (class, name); the Halo 3 family keeps a list of
    dicts. Both are iterated here so one audit covers all five games."""
    tags = getattr(m, 'tags', None)
    if isinstance(tags, dict):
        for key in tags:
            if isinstance(key, tuple) and len(key) == 2:
                yield key[0], key[1] or ''
        return
    for t in tags or []:
        if isinstance(t, dict):
            yield t.get('class'), t.get('name') or ''


def game_maps(folder):
    if not os.path.isdir(folder):
        return []
    out = {}
    for fn in sorted(os.listdir(folder)):
        if fn.endswith('.map.bak'):
            out[fn[:-8]] = os.path.join(folder, fn)
        elif fn.endswith('.map') and fn[:-4] not in out:
            out.setdefault(fn[:-4], os.path.join(folder, fn))
    for junk in ('shared', 'campaign', 'single_player_shared', 'bitmaps', 'sounds',
                 'ui', 'mainmenu'):
        out.pop(junk, None)
    return [out[k] for k in sorted(out)]


def family_of(path):
    """The `<family>` folder segment of a character-owned tag path, or None."""
    p = str(path).replace('/', B)
    for root in ROOTS:
        if p.startswith(root):
            rest = p[len(root):].split(B)
            return rest[0] if rest and rest[0] else None
    return None


def enemy_families(db):
    """{family folder: enemy name}, derived from each enemy's own char/actor tags."""
    out = {}
    games = db.get_games()
    for enemy, mods in (db.enemy_mods or {}).items():
        for mod in mods or []:
            tag = mod.get('tag')
            for t in (list(tag.values()) if isinstance(tag, dict) else [tag]):
                if not isinstance(t, str) or ' ' not in t:
                    continue
                cls, _, rest = t.partition(' ')
                if cls not in ('char', 'actv', 'actr'):
                    continue
                for part in rest.split(' & '):
                    fam = family_of(part.strip())
                    if fam and fam not in ('ai',):
                        out.setdefault(fam.rstrip('*'), enemy)
    return out


def carded_tags(db, game):
    """Every tag string any card targets in this game, as (class, path) pairs."""
    games = db.get_games()
    out = set()

    def add(tag):
        if not isinstance(tag, str) or ' ' not in tag:
            return
        cls, _, rest = tag.partition(' ')
        for part in rest.split(' & '):
            out.add((cls, part.strip().rstrip('*').lower()))

    pools = [db.weapon_mods, db.enemy_mods, db.boss_mods,
             getattr(db, 'equipment_mods', {}) or {}]
    seqs = [list((p or {}).values()) for p in pools]
    seqs.append([[m] for m in (db.positive_pool + db.negative_pool + db.wildcard_pool
                               + list(db.skull_pool or []))])
    for seq in seqs:
        for mods in seq:
            for mod in mods or []:
                tag = mod.get('tag')
                add(he.resolve_gamed(tag, game, games) if isinstance(tag, dict) else tag)
                ts = mod.get('targets')
                ts = he.resolve_gamed(ts, game, games) if isinstance(ts, dict) else ts
                for t in ts or []:
                    if isinstance(t, dict) and t.get('tag'):
                        tt = t['tag']
                        add(he.resolve_gamed(tt, game, games) if isinstance(tt, dict) else tt)
    return out


def covered(cls, path, carded):
    """Is this tag reached by a card — exactly, or by a prefix a wildcard card used."""
    p = path.lower()
    if (cls, p) in carded:
        return True
    return any(c == cls and p.startswith(cp) for c, cp in carded if cp)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--all', dest='show_all', action='store_true',
                    help='list the carded tags as well')
    ap.add_argument('--enemy', help='restrict to one enemy')
    ap.add_argument('--classes', help='comma-separated tag classes (default: the '
                                      'value-bearing ones)')
    ap.add_argument('--with-noise', action='store_true',
                    help='include gibs, props and cinematic doubles')
    args = ap.parse_args()
    want = set((args.classes or '').split(',')) if args.classes else PRIMARY

    with contextlib.redirect_stdout(io.StringIO()):
        db = he.ModifierDatabase()
    fams = enemy_families(db)

    grand = 0
    for game, subs, folder in CASES:
        maps = game_maps(folder)
        if not maps:
            continue
        carded = carded_tags(db, game)
        seen = {}                      # (enemy, cls, path) -> set of map basenames
        unclaimed = collections.Counter()
        for mp in maps:
            try:
                m = hp.open_map(mp, game)
            except Exception:
                continue
            for cls, name in _iter_tags(m):
                if cls not in want:
                    continue
                fam = family_of(name)
                if not fam or (is_noise(name) and not args.with_noise):
                    continue
                if is_ignored(game, cls, name):
                    continue
                enemy = fams.get(fam)
                if enemy is None:
                    unclaimed[fam] += 1
                    continue
                if args.enemy and enemy.lower() != args.enemy.lower():
                    continue
                seen.setdefault((enemy, cls, name), set()).add(os.path.basename(mp))
        rows = []
        for (enemy, cls, name), maps_with in sorted(seen.items()):
            ok = covered(cls, name, carded)
            if ok and not args.show_all:
                continue
            rows.append((enemy, cls, name, len(maps_with), ok))
        print('=' * 92)
        print('%s   %d enemy-owned tag(s) in %s, %d uncarded'
              % (game, len(seen), ','.join(sorted(want)),
                 sum(1 for r in rows if not r[4])))
        last = None
        for enemy, cls, name, nmaps, ok in rows:
            if enemy != last:
                print('  %s' % enemy)
                last = enemy
            print('     %-5s %-64s %2d map(s)%s'
                  % (cls, name[:64], nmaps, '   [carded]' if ok else ''))
        grand += sum(1 for r in rows if not r[4])
        if unclaimed:
            print('  -- folders no enemy card claims: %s'
                  % ', '.join('%s(%d)' % (k, v) for k, v in unclaimed.most_common(8)))
    print()
    print('%d uncarded enemy-owned tag(s) total' % grand)


if __name__ == '__main__':
    main()
