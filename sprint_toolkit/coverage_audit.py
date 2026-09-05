r"""Fields an enemy really defines that NO card touches -- the gap that fails silently.

`inherit_audit.py` finds cards pointing at nothing. That direction is loud: the card is
there, it is drafted, it does nothing, and eventually somebody notices. This tool finds
the opposite and much quieter direction -- a field a character carries, in a game, that
no card has ever offered. Nothing fails, nothing is reported, the mechanic simply is not
in the game.

It shows up whenever a character gains a mechanic between games and the card set was
authored against the earlier one. The DEFAULT view is the high-signal subset: a field
some OTHER game already has a card for, live here, uncarded here. That is almost always
an oversight rather than a decision. `--all` drops that filter and is very noisy: the
char plugin declares hundreds of fields and most were never meant to be cards.

A third section, printed above the gaps, catches the quietest case of all -- a card that
exists, works, and edits `ai\generic`, while the enemy it names defines the field on its
own tags again in this game. Nothing fails there either; the card simply stopped being
about that enemy.

A fourth section leaves the `char` tag entirely. Everything above only ever looks at
character BEHAVIOUR, and an enemy's gun, its projectile and its damage effects live in
other tag classes under the same folder -- so a weapon that belongs to one enemy was
invisible to all three passes. That section (formerly `enemy_asset_audit.py`, now folded
in here so one command is the whole check) lists enemy-owned weap/proj/jpt!/hlmt/coll/
eqip tags that no card reaches. It covers all five games, as do the field passes above
from Halo 2 on -- Halo 1 is the only game left out, its actor tags being a different
layout entirely.

A fifth section does turrets, which fall outside BOTH of the above. A turret is not a
character, so the family derivation cannot claim it, and a mounted one is not a weapon
pickup either -- it is a VEHICLE placement, which is why a weapons-only reader reports
zero for a gun you can plainly rip off its mount. The detachable turrets the player
picks up are already carded as weapons; what this finds is the mounted set an enemy
sits in and shoots you with.

Usage:
    python sprint_toolkit/coverage_audit.py                 # every section
    python sprint_toolkit/coverage_audit.py --all           # every gap (very noisy)
    python sprint_toolkit/coverage_audit.py --enemy Jackal
    python sprint_toolkit/coverage_audit.py --only fields   # sections 1-3 (char only)
    python sprint_toolkit/coverage_audit.py --only assets   # section 4
    python sprint_toolkit/coverage_audit.py --only turrets  # section 5

The five sections group into three --only choices: the first three all read `char`
through a plugin and share one sweep, so they are selected together as 'fields'.
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
sys.path.insert(0, _HERE)          # for the enemy-owned-tag pass, below

_buf = io.StringIO()
with contextlib.redirect_stdout(_buf):
    import halo_enhancer as he                                    # noqa: E402
    import halo_patch as hp                                       # noqa: E402
    # The enemy-owned-tag pass. Imported rather than reimplemented: the family ->
    # enemy mapping is derived from the card database and there must be exactly one
    # copy of that derivation, or the two audits disagree about who owns what.
    import enemy_asset_audit as eaa                               # noqa: E402
    # Placement data: which turrets a level actually puts in the world. Its
    # Halo 1 and Halo 2 vehicle support is what makes those two games
    # answerable at all -- without it they reported no vehicles whatsoever.
    import weapon_availability as wa                              # noqa: E402

CFG = json.load(open('settings.json', encoding='utf-8'))
_ROOT = CFG.get('mcc_root') or (
    r'C:\Program Files (x86)\Steam\steamapps\common'
    r'\Halo The Master Chief Collection')

# EVERY level of each game, not one representative. A single map can only under-report:
# it reports a gap for a field that map defines, so it cannot produce a false positive,
# but any enemy it does not field is invisible. That bit for real -- auditing Halo 3 on
# 030_outskirts alone hid every Flood gap, because 030 has no Flood. The union across a
# game's maps is the only honest answer to "does this character define this field".
CASES = [
    ('Halo 2', ['Halo2MCC', 'Halo2'],
     os.path.join(_ROOT, 'halo2', 'h2_maps_win64_dx11')),
    ('Halo 3', ['Halo3MCC', 'Halo3'],
     os.path.join(_ROOT, 'halo3', 'maps')),
    ('Halo 3: ODST', ['ODSTMCC', 'ODST'],
     os.path.join(_ROOT, 'halo3odst', 'maps')),
    # Reach's char layout is close enough to run the same passes: it adds 22 blocks and
    # 112 fields over ODST and removes one block, so the field walk works unchanged.
    # What it does NOT share is field NAMES -- Reach replaced the Perception set
    # (Central/Maximum Vision Angle, Peripheral Distance) with Reliable/Peripheral
    # Vision Distance and Surprise Distance -- so a Vision or Perception gap here is a
    # rename, not an oversight, and needs a Reach-specific target rather than adding
    # Reach to the existing card. Reach also ships no .map.bak, so this reads the live
    # maps; that is fine for the question asked, which is whether a block is DEFINED.
    ('Halo Reach', ['ReachMCC', 'Reach'],
     os.path.join(_ROOT, 'haloreach', 'maps')),
]


def game_maps(folder, game=None):
    """Delegates to enemy_asset_audit, which owns the one pristine-aware version.

    This file used to carry a near-identical copy that differed only in its junk list,
    so a fix to one silently missed the other -- and three of the four callers here
    already went through eaa.game_maps.
    """
    # eaa returns a list of paths and already drops a SUPERSET of the blobs this
    # file used to filter (its junk list adds ui and mainmenu), so there is nothing
    # left to strip here.
    return eaa.game_maps(folder, game)


# Fields no card should ever offer: identifiers, indices, editor bookkeeping, and the
# tag references that name other tags rather than tune a value.
SKIP_EXACT = {'Name', 'Parent Character', 'Editor Folder Index', 'Unknown', 'Flags'}
SKIP_SUBSTR = ('Index', 'Variant Name', 'Definitions', 'Type', 'Unknown', 'Flags')


def _interesting(field):
    if field in SKIP_EXACT:
        return False
    return not any(s in field for s in SKIP_SUBSTR)


def _plugin_fields(plugin):
    """[(field name, block path)] for every numeric field the char plugin declares."""
    out, seen = [], set()
    for f in getattr(plugin, 'fields', []):
        if not str(f.get('type', '')).startswith(('float', 'int', 'real', 'rangef',
                                                  'degree', 'short', 'uint')):
            continue
        blk = '/'.join(f.get('block_chain') or []) or None
        key = (f['name'], blk)
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


GENERIC = 'ai' + chr(92) + 'generic'


def carded_fields(db, game, enemy, generic_only=False, enemy_only=False):
    """{field name} this enemy's cards target in this game.

    `generic_only` narrows it to the fields whose card is aimed at the shared AI base
    rather than at the enemy. Those are the cards to re-check whenever an enemy starts
    defining a field again in a later game: the card still works, it just no longer
    edits the enemy it names."""
    games = db.get_games()
    got = set()
    pools = [db.enemy_mods.get(enemy) or []]
    for name, mods in (db.boss_mods or {}).items():
        if name == enemy or str(name).startswith(str(enemy)):
            pools.append(mods)
    for mods in pools:
        for mod in mods:
            if not db._game_ok(mod, game):
                continue
            tag = mod.get('tag')
            tag = he.resolve_gamed(tag, game, games) if isinstance(tag, dict) else tag
            aimed_generic = (isinstance(tag, str)
                             and tag.split(' ', 1)[-1].strip() == GENERIC)
            ts = mod.get('targets')
            ts = he.resolve_gamed(ts, game, games) if isinstance(ts, dict) else ts
            for t in ts or []:
                if not isinstance(t, dict) or not he.target_applies(t, game):
                    continue
                # A TARGET may redirect onto a tag of its own -- which is how a card
                # aimed at the shared base still reaches an enemy that defines the
                # field itself. Judge each target by where IT lands, not by the card's
                # tag, or a redirect that was added to fix this exact problem keeps
                # being reported as the problem.
                own = t.get('tag')
                own = he.resolve_gamed(own, game, games) if isinstance(own, dict) else own
                t_generic = (aimed_generic if not isinstance(own, str)
                             else own.split(' ', 1)[-1].strip() == GENERIC)
                if generic_only and not t_generic:
                    continue
                if enemy_only and t_generic:
                    continue
                f = t.get('field')
                f = he.resolve_gamed(f, game, games) if isinstance(f, dict) else f
                if isinstance(f, str):
                    # strip the difficulty flavour so "Legendary Body Vitality" and
                    # "Body Vitality" compare equal
                    for pre in ('Normal ', 'Heroic ', 'Legendary ', 'Easy ', 'Impossible '):
                        if f.startswith(pre):
                            f = f[len(pre):]
                    got.add(f)
    return got


def general_generic_fields(db, game):
    """{field} covered ONLY by a General modifiers card aimed at the shared AI base.

    These are the campaign-wide mechanics -- Vision, Accuracy, Grenade Properties,
    Retreat, Firing Patterns -- that reach an enemy purely BY INHERITANCE. The moment a
    later game gives that enemy its own copy of the block, the general card stops
    reaching it and there is no enemy-specific card to take over. Nothing fails; the
    enemy is simply no longer covered by the card that claims to cover everyone.
    """
    games = db.get_games()
    raw = json.load(open('halo.json', encoding='utf-8'))
    gm = ((raw.get('Enemy modifiers') or {}).get('General modifiers') or {})
    out = set()
    for card in gm.values():
        if not isinstance(card, dict):
            continue
        tag = card.get('tag')
        tag = he.resolve_gamed(tag, game, games) if isinstance(tag, dict) else tag
        if not (isinstance(tag, str) and tag.strip().endswith(GENERIC)):
            continue
        ts = card.get('targets')
        ts = he.resolve_gamed(ts, game, games) if isinstance(ts, dict) else ts
        for t in ts or []:
            if not isinstance(t, dict) or not he.target_applies(t, game):
                continue
            f = t.get('field')
            f = he.resolve_gamed(f, game, games) if isinstance(f, dict) else f
            if isinstance(f, str):
                out.add(f)
    return out


def enemy_tag_patterns(db, enemy):
    r"""Every char tag pattern this enemy's cards name, in ANY game, minus ai\generic.

    Taking the pattern from the card for THIS game would hide the most interesting
    case there is. When an enemy stops defining a field, the card is often repointed at
    `ai\generic` -- Jackal Cover Chance is `char ai\generic` in Halo 2 and Halo 3 --
    and then the audit would compare the generic base against itself and see no gap at
    all. Reading the enemy's OWN tags from whichever game still names them is what makes
    "this enemy defines the field again, and only the shared base is being edited"
    visible.
    """
    games = db.get_games()
    out = []
    for mod in db.enemy_mods.get(enemy) or []:
        tag = mod.get('tag')
        cands = list(tag.values()) if isinstance(tag, dict) else [tag]
        for t in cands:
            if not isinstance(t, str) or not t.startswith('char '):
                continue
            for part in t.split(' ', 1)[1].split(' & '):
                part = part.strip()
                if part and part != 'ai' + chr(92) + 'generic' and part not in out:
                    out.append(part)
    return out


# Things a mission list OFFERS that have no cards, and that the USER HAS DECIDED to
# leave that way. They are reported as DEFERRED, never as gaps, so they stop coming
# back round as findings. Each entry records whose call it was and why, because that
# is the part that gets lost -- the fact itself is re-derivable in a minute.
#
# Add to this list rather than arguing with the audit output. Removing an entry turns
# it back into a normal gap.
OFFER_DEFERRED = {
    ('Halo Reach', 'Health Pack'):
        "USER'S CALL, repeatedly (last 2026-09-03): do not card it and do not keep "
        "raising it. The eqip tag is real and carries 15 tunables, so this is a "
        "decision and not a missing capability.",
    ('Halo 1', 'Flamethrower'):
        "USER'S CALL (2026-08-26): its card set is Halo 3 only. The flamethrower is "
        "not normally available in Halo 1, so it waits until every H1 weapon ships "
        "on every map -- one entry in a much larger job, not a one-off patch.",
}


def offer_pass(db, args):
    r"""Every name a mission list can OFFER, against whether it resolves to cards.

    The field passes above ask "does this character have an uncarded field". This asks
    the blunter question one level up: can the run offer this THING at all, and is
    there anything to draft once it does. A name with no cards and no tag is a dead
    offer -- it can be picked and does nothing -- which no other section here sees,
    because there is no tag for them to find a field on.
    """
    gaps = 0
    for game in ('Halo 1', 'Halo 2', 'Halo 3', 'Halo 3: ODST', 'Halo Reach'):
        mids = [m for m, g in db.mission_games.items() if g == game]
        if not mids:
            continue
        rows, deferred = [], []
        seen = set()
        for attr, kind in (('mission_weapons', 'weapon'),
                           ('mission_equipment', 'equipment'),
                           ('mission_grenades', 'grenade'),
                           ('mission_turrets', 'turret')):
            for mid in mids:
                for name in (getattr(db, attr, {}) or {}).get(mid) or []:
                    if (kind, name) in seen:
                        continue
                    seen.add((kind, name))
                    if kind == 'equipment':
                        cards = [m for m in (db.equipment_mods.get(name) or [])
                                 if db._game_ok(m, game)]
                        tag = db.eqip_tag_for(name, game)
                    else:
                        cards = [m for m in db.weapon_mods.get(
                            db.resolve_weapon(name), []) if db._game_ok(m, game)]
                        tag = db.weap_tag_for(name, game)
                    if cards:
                        continue
                    why = OFFER_DEFERRED.get((game, name))
                    (deferred if why else rows).append((kind, name, tag, why))
        print('=' * 84)
        print('%-14s %d offer(s) with no cards, %d deferred'
              % (game, len(rows), len(deferred)))
        for kind, name, tag, _ in sorted(rows):
            gaps += 1
            print('   %-10s %-22s %s' % (kind, name,
                                         'NO TAG EITHER -- dead offer' if not tag
                                         else 'tag resolves, no cards'))
        for kind, name, tag, why in sorted(deferred):
            print('   %-10s %-22s DEFERRED' % (kind, name))
            print('        %s' % why)
    print()
    print('%d un-deferred offer gap(s) total' % gaps)
    return gaps


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--all', dest='everything', action='store_true',
                    help='every uncarded field, not just the cross-game ones. Very '
                         'noisy — the char plugin declares hundreds of fields and most '
                         'were never meant to be cards (345 rows for the Jackal alone)')
    ap.add_argument('--enemy', help='restrict to one enemy')
    ap.add_argument('--only',
                    choices=('fields', 'assets', 'turrets', 'placed', 'offers',
                             'all'),
                    default='all',
                    help="'fields' = the char-field passes, 'assets' = the "
                         "enemy-owned tag pass, 'turrets' = every uncarded turret "
                         "tag, 'placed' = only the turrets a level actually places "
                         "and that are not just some vehicle's gun, 'offers' = names "
                         "a mission list offers that resolve to no cards. Default "
                         "runs all.")
    ap.add_argument('--with-noise', action='store_true',
                    help='asset pass: include gibs, props and cinematic doubles')
    ap.add_argument('--no-useful', action='store_true',
                    help='asset pass: skip the cross-reference against fields cards '
                         'already tune (it opens maps, so it is the slow half)')
    args = ap.parse_args()

    with contextlib.redirect_stdout(io.StringIO()):
        db = he.ModifierDatabase()

    enemies = sorted(db.enemy_mods)
    if args.enemy:
        enemies = [e for e in enemies if e.lower() == args.enemy.lower()] or enemies

    if args.only == 'assets':
        print()
        return 0 if asset_pass(db, args) == 0 else 1
    if args.only == 'turrets':
        print()
        return 0 if turret_pass(db, args) == 0 else 1
    if args.only == 'placed':
        print()
        return 0 if placed_turret_pass(db, args) == 0 else 1
    if args.only == 'offers':
        print()
        return 0 if offer_pass(db, args) == 0 else 1

    # game -> enemy -> {live fields}, and game -> enemy -> {carded fields}
    live, carded, viageneric, general = {}, {}, {}, {}
    for game, subs, folder in CASES:
        maps = game_maps(folder, game)
        if not maps:
            print('%s: no maps under %s' % (game, folder)); continue
        reg = hp.PluginRegistry(CFG['assembly_plugins_dir'], subs)
        plug = reg.get('char')
        if plug is None:
            continue
        fields = [(f, b) for f, b in _plugin_fields(plug) if _interesting(f)]
        live[game], carded[game], viageneric[game] = {}, {}, {}
        general[game] = set()
        print('%s: reading %d level(s)…' % (game, len(maps)), flush=True)
        for mp in maps:
            try:
                m = hp.open_map(mp, game)
            except Exception:
                continue
            for enemy in enemies:
                pats = enemy_tag_patterns(db, enemy)
                tags = []
                for pat in pats:
                    tags += [p for p, _ in m.find_tags('char', pat) if p not in tags]
                if not tags:
                    continue
                got = live[game].setdefault(enemy, set())
                for f, b in fields:
                    if f in got:
                        continue
                    for p in tags:
                        try:
                            if m.read_all('char', p, f, plug, b, 'all'):
                                got.add(f)
                                break
                        except Exception:
                            pass
        for enemy in list(live[game]):
            carded[game][enemy] = carded_fields(db, game, enemy)
            viageneric[game][enemy] = (
                carded_fields(db, game, enemy, generic_only=True)
                # ...minus anything a sibling target already writes on the enemy's own
                # tags. A card may do BOTH -- edit the shared base for the levels where
                # the enemy inherits, and redirect onto the enemy for the levels where
                # it does not -- and that is a fix, not a finding.
                - carded_fields(db, game, enemy, enemy_only=True))
        general[game] = general_generic_fields(db, game)

    # a field is "carded somewhere" if any game's card set names it
    anywhere = collections.defaultdict(set)          # enemy -> {field}
    for g in carded:
        for e, fs in carded[g].items():
            anywhere[e] |= fs

    total = 0
    for game in [g for g, _, _ in CASES if g in live]:
        rows, misaimed, outgrown = [], [], []
        for enemy in sorted(live[game]):
            gap = live[game][enemy] - carded[game][enemy]
            for f in sorted(gap):
                elsewhere = f in anywhere[enemy]
                if not args.everything and not elsewhere:
                    continue
                rows.append((enemy, f, elsewhere))
            # The quietest case of all: a card that exists, works, and edits the
            # shared base -- while this enemy defines the field on its own tags again.
            for f in sorted(viageneric[game][enemy] & live[game][enemy]):
                misaimed.append((enemy, f))
            # A campaign-wide mechanic that used to reach this enemy through the shared
            # base, and no longer does because the enemy defines the block itself here.
            for f in sorted((general[game] & live[game][enemy])
                            - carded[game][enemy]):
                outgrown.append((enemy, f))
        print('=' * 84)
        print('%s   %d uncarded field(s) this level actually defines' % (game, len(rows)))
        total += len(rows)
        if outgrown:
            print('  --- a General card reaches these through ai/generic, but the enemy')
            print('      defines the block itself here, so it no longer lands on them')
            for enemy, f in outgrown:
                print('      %-18s %s' % (enemy, f))
        if misaimed:
            print('  --- aimed at ai/generic while the enemy defines it here')
            for enemy, f in misaimed:
                print('      %-18s %s' % (enemy, f))
        last = None
        for enemy, f, elsewhere in rows:
            if enemy != last:
                print('  %s' % enemy)
                last = enemy
            print('      %-44s %s' % (f, 'CARDED IN ANOTHER GAME' if elsewhere else ''))
    print()
    print('%d field gap(s) total%s'
          % (total, '' if args.everything
             else ' (cross-game only; --all for everything)'))

    if args.only != 'fields':
        print()
        asset_pass(db, args)
        print()
        turret_pass(db, args)
        print()
        placed_turret_pass(db, args)
        print()
        offer_pass(db, args)


def _carded_fields_by_class(db, game):
    r"""{tag class: {(field, block)}} that ANY card already edits in this game.

    This is what turns the raw uncarded-tag list into a worklist. A tag nobody has
    carded is only interesting if there is something ON it worth tuning, and the
    strongest evidence that a field is worth tuning is that a card somewhere already
    tunes it -- the value is known good, the operator shape is known, and the card text
    is already written. A field no card anywhere touches is the speculative case, and
    is left out of the useful list on purpose.
    """
    games = db.get_games()
    out = collections.defaultdict(set)
    pools = [db.weapon_mods, db.enemy_mods, db.boss_mods,
             getattr(db, 'equipment_mods', {}) or {}]
    seqs = [list((p or {}).values()) for p in pools]
    seqs.append([[m] for m in (db.positive_pool + db.negative_pool + db.wildcard_pool
                               + list(db.skull_pool or []))])
    for seq in seqs:
        for mods in seq:
            for mod in mods or []:
                if not db._game_ok(mod, game):
                    continue
                tag = mod.get('tag')
                tag = he.resolve_gamed(tag, game, games) if isinstance(tag, dict) else tag
                ts = mod.get('targets')
                ts = he.resolve_gamed(ts, game, games) if isinstance(ts, dict) else ts
                for t in ts or []:
                    if not isinstance(t, dict) or not he.target_applies(t, game):
                        continue
                    own = t.get('tag')
                    own = (he.resolve_gamed(own, game, games)
                           if isinstance(own, dict) else own) or tag
                    if not isinstance(own, str) or ' ' not in own:
                        continue
                    cls = own.split(' ', 1)[0]
                    fld = t.get('field')
                    if not fld:
                        continue
                    blk = t.get('block')
                    blk = (he.resolve_gamed(blk, game, games)
                           if isinstance(blk, dict) else blk)
                    out[cls].add((str(fld), str(blk) if blk else None))
    return out


def _useful_fields(m, cls, path, plug, wanted):
    """Which already-carded fields this uncarded tag actually DEFINES on this map.

    Defined, not merely declared by the plugin: a plugin lists every field the class
    can have, and most tags carry only some of them. Reading is the only way to tell,
    and a field that reads nothing here would make a card that silently does nothing --
    which is the entire failure mode these audits exist to catch."""
    got = set()
    for fld, blk in wanted:
        if (fld, blk) in got:
            continue
        try:
            if m.read_all(cls, path, fld, plug, blk, 'all'):
                got.add((fld, blk))
        except Exception:
            pass
    return got


# A turret is not a character, so `enemy_asset_audit`'s family derivation cannot see it,
# and it is not a weapon pickup either -- a mounted one is a VEHICLE placement, which is
# why a weapons-only reader reports zero for a gun you can plainly rip off its mount. So
# turrets fell through every audit so far, the same way the Hunter's fuel cannon did.
#
# Two kinds, and only one of them is a gap:
#   DETACHABLE  objects\weapons\turret\...  the player picks these up, so they are
#               already offered as weapons and already carded.
#   MOUNTED     objects\vehicles\..._turret_...\, the Shades, Halo 1's `c gun turret`
#               -- the ones an ENEMY sits in and shoots you with. Uncarded.
# The pass reports whatever is uncarded, so the split maintains itself rather than being
# asserted here.
TURRET_MARKERS = ('turret', 'shade', 'plasma_cannon', 'machinegun', 'aa_gun',
                  'gun turret', 'agtg', 'flak_cannon_stationary')
TURRET_CLASSES = {'vehi', 'weap', 'proj', 'jpt!'}


def _is_turret(name):
    low = str(name or '').lower()
    return any(k in low for k in TURRET_MARKERS)


def placed_turret_pass(db, args):
    r"""Turrets that are a thing in their own right AND that a level actually places.

    `turret_pass` above answers "what turret tags is nothing carding", which is the
    honest full picture and 300 rows long. This answers the narrower question you act
    on: which turrets are worth a card at all. Three filters, each doing work:

      1. NOT owned by a bigger vehicle -- the same ownership rule, so the Warthog's
         chaingun and the Wraith's mortar drop out.
      2. The OWNER must itself be turret-shaped. This is what rules out a turret that
         is ONLY a part of a vehicle: the Phantom's plasma turret survives filter 1,
         because a Phantom is a standalone vehicle, but it is still just the Phantom's
         gun. A Shade or a fixed plasma_cannon IS the turret.
      3. PLACED in a campaign map, read from the Vehicles palette. A resident tag
         proves nothing and a palette entry with no placements proves nothing --
         placement is the proof. This is why the pass needs Halo 1 and Halo 2 vehicle
         support in weapon_availability; without it both games reported nothing.

    Each row also carries the two signals that decide whether a turret is interesting
    to a PLAYER-side card, since a turret that cannot be picked up or that never runs
    dry is a card for the enemy or for a vehicle instead:

      detach   the folder has a `detach_gun` damage effect -- the engine's own "player
               ripped this off its mount" event
      ammo     whether the turret's weapons declare a Magazines element at all. No
               Magazines means no reserve to run out: unlimited.
    """
    grand = 0
    print('#' * 84)
    print('TURRETS WORTH CARDING   (standalone, and actually placed)')
    for game, subs, folder in eaa.CASES:
        maps = eaa.game_maps(folder, game)
        if not maps:
            continue
        reg = hp.PluginRegistry(CFG['assembly_plugins_dir'], subs)
        wp = reg.get('weap')
        carded = eaa.carded_tags(db, game)
        placed = collections.Counter()
        turret_tags, vehi_folders, detach_folders = [], set(), set()
        all_weaps = []                     # (folder, tag) for every weap in the game
        print('%s: reading %d level(s)…' % (game, len(maps)), flush=True)
        for mp in maps:
            try:
                m = hp.open_map(mp, game)
            except Exception:
                continue
            for base, rec in (wa.vehicle_survey(m, game) or {}).items():
                placed[base] += rec['placed']
            for cls, name in eaa._iter_tags(m):
                if not name:
                    continue
                low = str(name).lower()
                if cls in ('vehi', 'gint'):
                    vehi_folders.add(low.rsplit(chr(92), 1)[0])
                if cls == 'jpt!' and 'detach' in low:
                    detach_folders.add(low.rsplit(chr(92), 1)[0])
                if cls == 'weap' and (low, name) not in all_weaps:
                    all_weaps.append((low, name))
                if cls in TURRET_CLASSES and _is_turret(name):
                    if eaa.is_noise(name) or eaa.is_ignored(game, cls, name):
                        continue
                    if (cls, name) not in turret_tags:
                        turret_tags.append((cls, name))

        def top_owner(path):
            parts = str(path).lower().split(chr(92))
            own = None
            for i in range(len(parts), 0, -1):
                if chr(92).join(parts[:i]) in vehi_folders:
                    own = chr(92).join(parts[:i])
                    break
            if own is None:
                return None
            up = own.split(chr(92))
            for i in range(1, len(up)):
                if chr(92).join(up[:i]) in vehi_folders:
                    return chr(92).join(up[:i])
            return own

        sets = collections.defaultdict(list)
        for cls, name in turret_tags:
            fold = str(name).rsplit(chr(92), 1)[0]
            own = top_owner(fold)
            key = own if own is not None else fold.lower()
            if not _is_turret(key):
                continue                       # only a part of some vehicle
            if not eaa.covered(cls, name, carded):
                sets[key].append((cls, name))

        weaps_under = collections.defaultdict(list)
        for low, name in all_weaps:
            for key in sets:
                if low.startswith(key):
                    weaps_under[key].append(name)

        rows = []
        for key, parts in sets.items():
            n = placed.get(key.rsplit(chr(92), 1)[-1], 0)
            if n <= 0:
                continue
            detach = any(d.startswith(key) for d in detach_folders)
            # Ammo is read from EVERY weap the turret owns, not just the uncarded
            # ones. On Halo 3 and ODST the gun itself is already carded as a player
            # weapon, so the uncarded parts are the vehi and a damage effect -- asking
            # only those gave "no weap of its own" for turrets that plainly have one.
            #
            # And a Magazines element is not by itself proof of finite ammo: Halo 1's
            # `c gun turret gun` declares one holding 0/0/0, which is a magazine that
            # can never run down. Rounds > 0 is the real test.
            rounds = 0
            for wname in weaps_under.get(key, ()):
                if wp is None:
                    break
                for mp in maps:
                    try:
                        m = hp.open_map(mp, game)
                    except Exception:
                        continue
                    if not m.find_tags('weap', wname):
                        continue
                    try:
                        r = m.read_all('weap', wname, 'Rounds Total Initial', wp,
                                       'Magazines', 'all')
                    except Exception:
                        r = None
                    for _p, v in (r or []):
                        try:
                            rounds = max(rounds, int(v))
                        except (TypeError, ValueError):
                            pass
                    break
            rows.append((n, key, sorted(set(parts)), detach, rounds))
        grand += len(rows)
        print('=' * 84)
        print('%s   %d turret(s) worth a look' % (game, len(rows)))
        for n, key, parts, detach, rounds in sorted(rows, key=lambda r: -r[0]):
            ammo = ('%d rounds' % rounds) if rounds > 0 else 'UNLIMITED'
            keep = 'CARD' if (detach and rounds > 0) else 'skip'
            print('   %-46s placed x%-4d detach=%-4s ammo=%-11s %s'
                  % (key[:46], n, 'yes' if detach else 'no', ammo, keep))
            for cls, name in parts:
                print('        %-5s %s' % (cls, name))
    print()
    print('%d placed standalone turret(s) with uncarded parts' % grand)
    return grand


def turret_pass(db, args):
    r"""Turret tags no card reaches, and which of them carry an already-carded field.

    Grouped by the folder the tag sits in, because a turret is a SET -- the vehicle, the
    gun it mounts, what that gun fires, and the damage it does -- and carding one part
    while missing the rest is the failure this is meant to surface.
    """
    grand = useful_total = 0
    standalone_total = [0]
    want_fields = not args.no_useful
    print('#' * 84)
    print('TURRETS   (%s)' % ', '.join(sorted(TURRET_CLASSES)))
    for game, subs, folder in eaa.CASES:
        maps = eaa.game_maps(folder, game)
        if not maps:
            continue
        reg = hp.PluginRegistry(CFG['assembly_plugins_dir'], subs)
        by_class = _carded_fields_by_class(db, game) if want_fields else {}
        carded = eaa.carded_tags(db, game)
        seen, first_map, vehi_folders = {}, {}, set()
        print('%s: reading %d level(s)…' % (game, len(maps)), flush=True)
        for mp in maps:
            try:
                m = hp.open_map(mp, game)
            except Exception:
                continue
            for cls, name in eaa._iter_tags(m):
                # Every vehicle's own folder, whatever it is called -- the
                # ownership map the grouping below is built on. `gint` counts as
                # well as `vehi`: the Scarab is a GIANT, not a vehicle, so a
                # vehi-only sweep left its main_turret looking like a standalone
                # emplacement instead of the gun on the biggest vehicle in the
                # game. Derived rather than listed, so it needs no per-game
                # upkeep, and it is what keeps `warthog\turrets\chaingun` filed
                # under the warthog while `c_turret_ap` stands on its own.
                if cls in ('vehi', 'gint') and name:
                    vehi_folders.add(str(name).rsplit(chr(92), 1)[0].lower())
                if cls not in TURRET_CLASSES or not name or not _is_turret(name):
                    continue
                if eaa.is_noise(name) or eaa.is_ignored(game, cls, name):
                    continue
                seen.setdefault((cls, name), set()).add(os.path.basename(mp))
                first_map.setdefault((cls, name), mp)
        rows = [(c, n, len(mm)) for (c, n), mm in sorted(seen.items())
                if not eaa.covered(c, n, carded)]

        # Which uncarded ones carry a field some card already tunes -- the same
        # proven-value test the asset pass uses.
        useful = {}
        if by_class and rows:
            cache = {}
            for cls, name, _n in rows:
                wanted, plug = by_class.get(cls), reg.get(cls)
                mp = first_map.get((cls, name))
                if not wanted or plug is None or mp is None:
                    continue
                m = cache.get(mp)
                if m is None:
                    try:
                        m = cache[mp] = hp.open_map(mp, game)
                    except Exception:
                        continue
                hit = _useful_fields(m, cls, name, plug, wanted)
                if hit:
                    useful[(cls, name)] = hit

        # Splitting the turret an enemy climbs into from the gun bolted onto some
        # other vehicle. "Does its folder hold a vehicle" is NOT the test: in Halo's
        # object model every turret seat is itself a vehicle, so the Wraith's mortar
        # answers yes just as loudly as a Shade does. What actually separates them is
        # whether an ANCESTOR folder is a vehicle too -- `wraith\turrets\mortar` sits
        # under `wraith`, while `c_turret_ap` sits under plain `objects\vehicles` and
        # belongs to nothing. Derived, so it needs no per-game list.
        # Which vehicle a tag belongs to: the DEEPEST vehicle folder that is a prefix
        # of its own. That is what keeps a turret's parts with the turret -- the
        # Shade's `c_turret_ap\weapon\gun` sits in no vehicle folder itself, but its
        # nearest vehicle ancestor is the Shade, so it groups there rather than being
        # filed as somebody else's mounted gun.
        def owner(name):
            parts = str(name).lower().split(chr(92))[:-1]      # drop the tag basename
            for i in range(len(parts), 0, -1):
                f = chr(92).join(parts[:i])
                if f in vehi_folders:
                    return f
            return None

        def standalone(name):
            own = owner(name)
            if own is None:
                return False
            up = own.split(chr(92))
            for i in range(1, len(up)):
                if chr(92).join(up[:i]) in vehi_folders:
                    return False                               # owned by that vehicle
            return True

        # Three answers, not two. A tag that no vehicle claims at ALL is a fixed
        # emplacement rather than somebody's mounted gun -- Halo 2's
        # `objects\weapons\fixed\plasma_cannon` is the case -- and filing it under
        # "vehicle-mounted" would be simply untrue.
        groups = [('STANDALONE turrets — an enemy mans these',
                   [r for r in rows if standalone(r[1])]),
                  ('guns belonging to another vehicle',
                   [r for r in rows if owner(r[1]) and not standalone(r[1])]),
                  ('fixed emplacements — no vehicle claims these',
                   [r for r in rows if not owner(r[1])])]
        print('=' * 84)
        print('%s   %d turret tag(s), %d uncarded, %d of those useful'
              % (game, len(seen), len(rows), len(useful)))
        for title, grp in groups:
            if not grp:
                continue
            print('  --- %s  (%d)' % (title, len(grp)))
            last = None
            for cls, name, nmaps in grp:
                folder_of = str(name).rsplit(chr(92), 1)[0]
                if folder_of != last:
                    print('      %s' % folder_of)
                    last = folder_of
                mark = '   << USEFUL' if (cls, name) in useful else ''
                print('         %-5s %-52s %2d map(s)%s'
                      % (cls, str(name).rsplit(chr(92), 1)[-1][:52], nmaps, mark))
                for f, b in sorted(useful.get((cls, name), ())):
                    print('              %-38s %s' % (f, b or ''))
        grand += len(rows)
        useful_total += len(useful)
        standalone_total[0] += sum(1 for r in rows if standalone(r[1]))
    print()
    print('%d uncarded turret tag(s) total, %d of them USEFUL '
          '(%d are STANDALONE turrets, the rest are guns on other vehicles)'
          % (grand, useful_total, standalone_total[0]))
    return grand


def asset_pass(db, args):
    r"""Enemy-owned tags that are NOT the character tag, and whether a card reaches them.

    Everything above this reads `char`, which is only an enemy's BEHAVIOUR. What it
    hits you with lives elsewhere under the same folder: the gun in `weap`, what that
    gun fires in `proj`, its damage effects in `jpt!`, its vitality in `hlmt` (Halo 2
    on) or `coll` (Halo 1). A weapon that belongs to one enemy is therefore invisible
    to every field pass above -- which is how the Hunter's fuel cannon went uncarded.

    The family -> enemy mapping is DERIVED from each enemy's own char tag naming its
    folder, so it cannot drift out of step with the card database. A folder no enemy
    claims is reported rather than dropped: that is where a missing enemy would hide.

    Runs over all five games, where the field passes cover the three with a comparable
    `char` layout.
    """
    want = eaa.PRIMARY
    fams = eaa.enemy_families(db)
    grand = 0
    useful_total = 0
    print('#' * 84)
    print('ENEMY-OWNED TAGS OUTSIDE char   (%s)' % ', '.join(sorted(want)))
    for game, subs, folder in eaa.CASES:
        maps = eaa.game_maps(folder, game)
        if not maps:
            continue
        reg = hp.PluginRegistry(CFG['assembly_plugins_dir'], subs)
        by_class = _carded_fields_by_class(db, game) if not args.no_useful else {}
        carded = eaa.carded_tags(db, game)
        seen = {}
        first_map = {}          # tag -> a map that carries it, for the field read
        unclaimed = collections.Counter()
        print('%s: reading %d level(s)…' % (game, len(maps)), flush=True)
        for mp in maps:
            try:
                m = hp.open_map(mp, game)
            except Exception:
                continue
            for cls, name in eaa._iter_tags(m):
                if cls not in want:
                    continue
                fam = eaa.family_of(name)
                if not fam or (eaa.is_noise(name) and not args.with_noise):
                    continue
                if eaa.is_ignored(game, cls, name):
                    continue
                enemy = fams.get(fam)
                if enemy is None:
                    unclaimed[fam] += 1
                    continue
                if args.enemy and enemy.lower() != args.enemy.lower():
                    continue
                seen.setdefault((enemy, cls, name), set()).add(os.path.basename(mp))
                first_map.setdefault((cls, name), mp)
        rows = [(e, c, n, len(mw)) for (e, c, n), mw in sorted(seen.items())
                if not eaa.covered(c, n, carded)]
        print('=' * 84)
        print('%s   %d enemy-owned tag(s), %d uncarded' % (game, len(seen), len(rows)))

        # Which of the uncarded tags carry a field some card already tunes. One map is
        # opened per tag CLASS group rather than per tag, since re-opening a 100 MB map
        # for each of forty tags is the difference between seconds and minutes.
        useful = {}
        if by_class:
            cache = {}
            for enemy, cls, name, _n in rows:
                wanted = by_class.get(cls)
                plug = reg.get(cls)
                if not wanted or plug is None:
                    continue
                mp = first_map.get((cls, name))
                if mp is None:
                    continue
                m = cache.get(mp)
                if m is None:
                    try:
                        m = cache[mp] = hp.open_map(mp, game)
                    except Exception:
                        continue
                hit = _useful_fields(m, cls, name, plug, wanted)
                if hit:
                    useful[(enemy, cls, name)] = hit
        if useful:
            print('  --- USEFUL: uncarded, but carries a field a card already tunes')
            for (enemy, cls, name), flds in sorted(useful.items()):
                print('      %-16s %-5s %s' % (enemy, cls, name[:56]))
                for f, b in sorted(flds):
                    print('           %-40s %s' % (f, b or ''))
            useful_total += len(useful)
        last = None
        for enemy, cls, name, nmaps in rows:
            mark = '  << USEFUL' if (enemy, cls, name) in useful else ''
            if enemy != last:
                print('  %s' % enemy)
                last = enemy
            print('     %-5s %-62s %2d map(s)%s' % (cls, name[:62], nmaps, mark))
        grand += len(rows)
        if unclaimed:
            print('  -- folders no enemy card claims: %s'
                  % ', '.join('%s(%d)' % (k, v) for k, v in unclaimed.most_common(8)))
    print()
    print('%d uncarded enemy-owned tag(s) total, %d of them USEFUL '
          '(carry a field some card already tunes)' % (grand, useful_total))
    return grand


if __name__ == '__main__':
    main()
