r"""h4_wire_enemies.py -- give Halo 4's enemies their halo.json cards.

The `Specific Enemy modifier` half of what `h4_wire_weapons` does for weapons, and it
exists for the same reason: Halo 4 renamed every character tag with a `storm_` prefix,
so `objects\characters\elite\ai\elite*` finds nothing and the card resolves a Halo 3
path that is not there. Audited before this was written: of the enemy cards for the
five species Halo 4 shares, 71 were gated out by their `game` list, 40 had a tag that
does not exist in Halo 4, and 5 resolved.

WHAT A CHAR TAG LOOKS LIKE IN HALO 4. Every species is
`objects\characters\storm_<family>\ai\storm_<family>*`, with stimulus-response
variants one level deeper in `ai\stimuli\`. The wildcard this writes deliberately
matches the `ai\` level only, which is exactly what the inherited Halo 3 pattern
(`...\elite\ai\elite*`) does -- the stimuli tags are response overrides the AI swaps
to, not ranks, and no earlier game's card set has ever included them.

ENEMY-OWNED ASSETS COME TOO. A `char` tag is only behaviour; the gun, its projectile
and its damage effects live under the same family folder in other classes, and the
audit found all of them broken the same way -- `weap hunter_fuel_rod`,
`proj hunter_fuel_rod_bolt`, `jpt! grunt_backpack_destroyed`,
`jpt! sentinel_aggressor\damage_effects\death`. Those are folder-matched, and where
name matching cannot pick one the card takes all of them, the same fallback the weapon
tool uses.

`char ai\generic` is shared and Halo 4 keeps it, so cards naming it need nothing.

    python sprint_toolkit/h4_wire_enemies.py            # report
    python sprint_toolkit/h4_wire_enemies.py --show-ok
    python sprint_toolkit/h4_wire_enemies.py --apply
"""

import argparse
import collections
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import h4_census as hc                                 # noqa: E402
import h4_wire_weapons as W                            # noqa: E402

TOOL = W.TOOL
HALO_JSON = W.HALO_JSON
GAME = W.GAME
SEP = W.SEP

# Halo 1 keeps its AI on `actr` / `actv` and its vitality on `coll`; every later game
# uses `char`. A card whose tag resolves to one of those for Halo 4 is a HALO 1 card
# that was never wired past Halo 1 -- not a Halo 4 gap. Reported apart so the backlog
# does not swallow 27 cards that are not this tool's job.
HALO1_CLASSES = ('actr', 'actv', 'coll')

# Enemies whose weapon lives in the WEAPONS tree rather than under their own character
# folder. The Hunter's fuel rod is under `characters/storm_hunter/`, so it needs no
# entry; Halo 4 files the Sentinel's beam under `objects/weapons/pistol/` instead.
SPECIES_WEAPON = {'Sentinel': 'Sentinel Beam'}
# ...and those whose weapon has no vocabulary name at all, given as a folder
# pattern. The Watcher fires `storm_bishop_beam`, which is a weapon nothing
# carries and so was never named in halo.json.
SPECIES_WEAPON_PATTERN = {'Watcher': 'weapons/pistol/storm_bishop_beam/'}

# Cards that resolve in Halo 4 and still must not be wired. Same contract as the
# weapon tool's SKIP_CARDS: a key is a card name (every species) or `Species/Card`.
SKIP_CARDS = {
    # The EMPTY-BLOCK class, and on char tags it is the norm rather than the exception:
    # from Halo 3 on most per-enemy property blocks ship zero-element and inherit from
    # `ai\generic`, so the plugin resolving a field proves nothing. Every one of these
    # was found by running deadcards.py against a wired halo.json -- it is the only
    # tool that asks the MAP. Re-run it after touching anything here.
    #
    # Pointing them at `ai\generic` instead is NOT the fix: that block is shared by
    # every species, so a Jackal card would retune Grunts and Elites too.
    'Hunter/I am not scared':
        'no Halo 4 hunter tag defines the block; it inherits from ai\\generic.',
    'Hunter/Maximum Firing Distance Hunter Fuel Rod':
        'no Halo 4 hunter tag defines the block; it inherits from ai\\generic.',
    'Hunter/Target Tracking & Leading':
        'no Halo 4 hunter tag defines the block; it inherits from ai\\generic.',
    'Hunter/Rate of Fire':
        'no Halo 4 hunter tag defines the block; it inherits from ai\\generic.',
    'Grunt/Rate of Fire':
        'no Halo 4 grunt tag defines the block; it inherits from ai\\generic.',
    'Jackal/Hearing Distance':
        'no Halo 4 jackal tag defines Perception Properties; it inherits from '
        'ai\\generic. (The block table agrees: Jackal defines no Perception at all.)',
    'Jackal/Perception':
        'no Halo 4 jackal tag defines Perception Properties; it inherits from '
        'ai\\generic.',
    # The same empty-block class on the three species h4_new_enemies authors. The
    # Watcher pair was PREDICTED by the model scoring -- Sentinel misses Cover x4, and
    # the Watcher defines no Cover Properties at all -- which is a good sign the
    # scoring and the map agree.
    'Knight/Maximum Firing Distance':
        'no Halo 4 knight tag defines the block; it inherits from %s.' % 'ai\\generic',
    'Knight/Rate of Fire':
        'no Halo 4 knight tag defines the block; it inherits from %s.' % 'ai\\generic',
    'Knight/Target Tracking & Leading':
        'no Halo 4 knight tag defines the block; it inherits from %s.' % 'ai\\generic',
    'Crawler/Maximum Firing Distance':
        'no Halo 4 crawler tag defines the block; it inherits from %s.' % 'ai\\generic',
    'Crawler/Special-Case Firing':
        'no Halo 4 crawler tag defines the block; it inherits from %s.' % 'ai\\generic',
    'Crawler/Grenades':
        'the Crawler defines no Grenades Properties -- it throws none.',
    'Watcher/I am not scared':
        'no Halo 4 bishop tag defines the block; it inherits from %s.' % 'ai\\generic',
    'Watcher/Cover Properties':
        'the Watcher defines no Cover Properties at all, which the model scoring '
        'predicted (Sentinel misses Cover x4).',
    # Halo 4 ships no jpt! under `characters/storm_grunt/` at all -- the methane-tank
    # explosion is not a per-grunt damage tag there. Dropped on the user's call
    # rather than left pending.
    'Grunt/Grunt Damage': 'Halo 4 has no grunt backpack damage tag.',
    'Grunt/Grunt Radius': 'Halo 4 has no grunt backpack damage tag.',
    'Jackal/Cover Chance':
        'measured dead: `ai\\generic` is present in Halo 4 but `Cover Chance Time` and '
        '`Cover Chance Time Max` are defined on NO tag in the map, so the write lands '
        'nowhere. Found by inherit_audit and confirmed by deadcards.',
}


def species_family():
    """{species: storm_ family folder}, straight off the census vocabulary."""
    out = {}
    for pat, name in hc.ENEMIES:
        if not name:
            continue
        fam = pat.strip('/').rsplit('/', 1)[-1]
        out[name] = fam
    return out


def _halo1_only(tag):
    """Is this tag defined for Halo 1 and nothing later?"""
    return isinstance(tag, dict) and set(tag) == {'Halo 1'}


def skip_reason(species, cname):
    return SKIP_CARDS.get('%s/%s' % (species, cname)) or SKIP_CARDS.get(cname)


def h4_char_wildcard(species, families, have):
    r"""`objects\characters\storm_x\ai\storm_x*`, or None if it matches nothing."""
    fam = families.get(species)
    if not fam:
        return None
    pat = (SEP.join(['objects', 'characters', fam, 'ai', fam])) + '*'
    return pat if W._wild_hits(pat, have.get('char', ())) else None


def h4_asset_paths(species, cls, families, have):
    """Enemy-owned tags of `cls` under this species' family folder."""
    fam = families.get(species)
    if not fam:
        return []
    needle = 'characters/%s/' % fam
    return sorted((p for p in have.get(cls, ()) if needle in hc._norm(p)),
                  key=lambda p: (len(p), p))


def _shared_engine(path):
    """A tag that belongs to the engine rather than to any one species."""
    n = hc._norm(path)
    return n.startswith('globals/') or n.startswith('ai/')


def enemy_tag_for(species, inherited, families, have, retarget=False):
    """(tag, reason) -- the Halo 4 tag for an inherited enemy tag.

    `retarget` is set when the card is being copied onto a DIFFERENT species, which
    is what h4_new_enemies does. It matters because by then the model's own card has
    usually been wired already, so its inherited tag is a perfectly valid Halo 4 path
    -- just the wrong species'. Without this the Watcher's weapon cards came out
    pointing at the Sentinel's beam.
    """
    cls, _, rest = inherited.partition(' ')
    paths = [p.strip() for p in rest.split('&')]

    # Shared engine tags Halo 4 keeps verbatim (`ai\generic`, globals\...). Those are
    # kept even when retargeting -- they belong to no species.
    kept = [p for p in paths if '*' not in p and p in have.get(cls, ())]
    if kept and len(kept) == len(paths) and (
            not retarget or all(_shared_engine(p) for p in paths)):
        return None, None                      # inherited tag already resolves

    if cls == 'char':
        wild = h4_char_wildcard(species, families, have)
        if not wild:
            return None, 'no Halo 4 char family for %s' % species
        return 'char ' + wild, None

    cands = h4_asset_paths(species, cls, families, have)
    if not cands:
        # The species' gun may live in the weapons tree instead. Reuse the WEAPON
        # vocabulary rather than inventing a second one.
        wname = SPECIES_WEAPON.get(species)
        if wname:
            cands = W.h4_paths(wname, cls, have, W.tag_patterns())
        pat = SPECIES_WEAPON_PATTERN.get(species)
        if not cands and pat:
            cands = sorted((p for p in have.get(cls, ()) if pat in hc._norm(p)),
                           key=lambda p: (len(p), p))
    if not cands:
        return None, 'no Halo 4 %s tag under this species' % cls
    if len(cands) == 1:
        return cls + ' ' + cands[0], None
    picked, _why, seen = [], None, set()
    for src in paths:
        got, w = W.disambiguate(cands, src)
        for g in (got or ()):
            if g not in seen:
                seen.add(g)
                picked.append(g)
    if not picked:
        picked = cands                          # take them all -- same rule as weapons
    return cls + ' ' + ' & '.join(picked), None


def check(species, cname, card, have, registry, order, families,
          retarget=False):
    """(ok, plan-or-reason), mirroring h4_wire_weapons.check."""
    inherited = W.resolve(card.get('tag'), GAME, order)
    if not isinstance(inherited, str) or ' ' not in inherited:
        return False, 'no tag to inherit'
    cls = inherited.split(' ', 1)[0]
    if cls in HALO1_CLASSES or _halo1_only(card.get('tag')):
        # A HALO 1 card. Two shapes: a Halo 1 tag CLASS (`actr`/`actv`/`coll`), or a
        # tag dict whose only entry is Halo 1 -- the Sentinel's Projectiles Per Shot is
        # the second kind, and its `block` walks back to Halo 1's `Triggers` where
        # every later game says `Barrels`. Neither is a Halo 4 gap; both would need a
        # modern equivalent authored, which is a different job.
        return None, ('Halo 1-only card: its game list names no game after Halo 1, '
                      'and Halo 1 keeps AI on actr/actv and vitality on coll. '
                      'Verified across all 30 of them -- not a Halo 4 gap.')
    tag, why = enemy_tag_for(species, inherited, families, have, retarget)
    if why:
        return False, why

    plugin = registry.get(cls)
    if plugin is None:
        return False, 'no %s plugin for Halo 4' % cls
    targets = W.resolve(card.get('targets'), GAME, order) or []
    if not targets:
        return False, 'no targets for Halo 4'
    bad, good, tplan = [], 0, {}
    for i, t in enumerate(targets):
        if not isinstance(t, dict):
            continue
        if isinstance(t.get('games'), list) and GAME not in t['games']:
            tplan.setdefault(i, {})['games'] = True
        if any(t.get(k) for k in W.NON_PLUGIN_KEYS):
            continue
        tplugin, own = plugin, t.get('tag')
        if own is not None:
            it = W.resolve(own, GAME, order)
            if not isinstance(it, str) or ' ' not in it:
                bad.append('(target tag unresolved)')
                continue
            tcls = it.split(' ', 1)[0]
            ttag, twhy = enemy_tag_for(species, it, families, have, retarget)
            if twhy:
                bad.append('target tag: ' + twhy)
                continue
            if ttag and isinstance(own, dict) and GAME not in own:
                tplan.setdefault(i, {})['tag'] = ttag
            tplugin = registry.get(tcls)
            if tplugin is None:
                bad.append('no %s plugin for Halo 4' % tcls)
                continue
        blk = W.resolve(t.get('block'), GAME, order)
        nth = W.resolve(t.get('nth'), GAME, order) or 0
        names = W.field_names(t, order)
        if not names:
            bad.append('(unnamed field)')
            continue
        if any(tplugin.find(n, blk, nth) for n in names):
            good += 1
        elif nth and any(tplugin.find(n, blk, 0) for n in names):
            tplan.setdefault(i, {})['nth'] = 0
            good += 1
        else:
            bad.append(names[0] + (' in %s' % blk if blk else ''))
    if bad:
        scope = ('field absent (%d of %d resolve)' % (good, good + len(bad))
                 if good else 'field absent')
        return False, scope + ': ' + '; '.join(bad)
    return True, {'tag': tag, 'targets': tplan}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--show-ok', action='store_true')
    a = ap.parse_args()

    doc = json.load(io.open(HALO_JSON, encoding='utf-8'))
    order = list(doc['Missions'])
    se = doc['Enemy modifiers']['Specific Enemy modifier']
    names = set()
    for mm in doc['Missions'][GAME].values():
        names |= set(mm.get('enemies') or [])

    print('resolving Halo 4 char tags...')
    have, _melee = W.campaign_tags()
    families = species_family()
    registry = W.halo_patch.PluginRegistry(W.PLUGINS, W.SUBDIRS)

    ok, bad, skipped = [], [], []
    for sp in sorted(names & set(se)):
        for cname, card in se[sp].items():
            if not isinstance(card, dict):
                continue
            g = card.get('game')
            gl = [g] if isinstance(g, str) else list(g or [])
            if (isinstance(card.get('tag'), dict) and GAME in card['tag']) or GAME in gl:
                continue
            why = skip_reason(sp, cname)
            if why:
                skipped.append((sp, cname, why))
                continue
            good, res = check(sp, cname, card, have, registry, order, families)
            if good is None:
                # A closed category, not pending work -- reported with the skips.
                skipped.append((sp, cname, res))
                continue
            if good and res['tag'] is None and not gl and not res.get('targets'):
                # No `game` key means the card already applies everywhere, and its
                # inherited tag already resolves in Halo 4 -- there is nothing to
                # write. Counting it as pending re-offered it on every run.
                continue
            (ok if good else bad).append((sp, cname, res))

    print('\n=== would wire (%d) ===' % len(ok))
    if a.show_ok:
        for s, n, plan in ok:
            tag = plan['tag']
            print('   %-12s %-26s %s'
                  % (s, n, (tag.split(' ', 1)[1][:74] if tag
                            else '(inherited tag already resolves)')))
    else:
        byw = collections.defaultdict(list)
        for s, n, _p in ok:
            byw[s].append(n)
        for s in sorted(byw):
            print('   %-12s %d: %s' % (s, len(byw[s]), ', '.join(sorted(byw[s]))))

    print('\n=== needs real work (%d) ===' % len(bad))
    byreason = collections.defaultdict(list)
    for s, n, why in bad:
        byreason[str(why).split(':')[0]].append('%s/%s' % (s, n))
    for r in sorted(byreason):
        print('   %-34s %3d  e.g. %s'
              % (r, len(byreason[r]), ', '.join(byreason[r][:3])))
    if skipped:
        print('\n=== deliberately NOT wired (%d) ===' % len(skipped))
        for s, n, why in skipped:
            print('   %s / %s\n      %s' % (s, n, why))

    missing = sorted(names - set(se))
    if missing:
        print('\n=== Halo 4 species with NO entry at all (%d) ===' % len(missing))
        print('   ' + ', '.join(missing) + '   (authoring -- h4_new_enemies.py)')

    if not a.apply:
        print('\n(report only -- pass --apply)')
        return
    lines = io.open(HALO_JSON, encoding='utf-8').read().split('\n')
    written = 0
    for s, n, plan in ok:
        if W.wire_card(lines, s, n, plan, order):
            written += 1
    out = '\n'.join(lines)
    json.loads(out)
    io.open(HALO_JSON, 'w', encoding='utf-8', newline='').write(out)
    print('\nwired %d card(s) into halo.json' % written)


if __name__ == '__main__':
    main()
