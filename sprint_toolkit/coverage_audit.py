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

Usage:
    python sprint_toolkit/coverage_audit.py                 # the cross-game gaps
    python sprint_toolkit/coverage_audit.py --all           # every gap (very noisy)
    python sprint_toolkit/coverage_audit.py --enemy Jackal
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

_buf = io.StringIO()
with contextlib.redirect_stdout(_buf):
    import halo_enhancer as he                                    # noqa: E402
    import halo_patch as hp                                       # noqa: E402

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
]


def game_maps(folder):
    """Every level in a map folder, preferring the pristine .bak where one exists."""
    if not os.path.isdir(folder):
        return []
    out = {}
    for fn in sorted(os.listdir(folder)):
        if fn.endswith('.map.bak'):
            out[fn[:-8]] = os.path.join(folder, fn)
        elif fn.endswith('.map') and fn[:-4] not in out:
            out.setdefault(fn[:-4], os.path.join(folder, fn))
    # shared resource blobs, not levels
    for junk in ('shared', 'campaign', 'single_player_shared', 'bitmaps', 'sounds'):
        out.pop(junk, None)
    return [out[k] for k in sorted(out)]


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


def carded_fields(db, game, enemy, generic_only=False):
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
            if generic_only and not aimed_generic:
                continue
            ts = mod.get('targets')
            ts = he.resolve_gamed(ts, game, games) if isinstance(ts, dict) else ts
            for t in ts or []:
                if not isinstance(t, dict) or not he.target_applies(t, game):
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


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--all', dest='everything', action='store_true',
                    help='every uncarded field, not just the cross-game ones. Very '
                         'noisy — the char plugin declares hundreds of fields and most '
                         'were never meant to be cards (345 rows for the Jackal alone)')
    ap.add_argument('--enemy', help='restrict to one enemy')
    args = ap.parse_args()

    with contextlib.redirect_stdout(io.StringIO()):
        db = he.ModifierDatabase()

    enemies = sorted(db.enemy_mods)
    if args.enemy:
        enemies = [e for e in enemies if e.lower() == args.enemy.lower()] or enemies

    # game -> enemy -> {live fields}, and game -> enemy -> {carded fields}
    live, carded, viageneric, general = {}, {}, {}, {}
    for game, subs, folder in CASES:
        maps = game_maps(folder)
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
            viageneric[game][enemy] = carded_fields(db, game, enemy, generic_only=True)
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
    print('%d gap(s) total%s' % (total, '' if args.everything else ' (cross-game only; --all for everything)'))


if __name__ == '__main__':
    main()
