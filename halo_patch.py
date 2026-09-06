# halo_patch.py — glue between the roller's selected effects and halo_map.py.
# Collects the effects chosen during a run, resolves each to its Assembly plugin,
# and applies typed operators to the map with a per-insert success/failure report.
# No GUI dependency; safe to unit-test headless.

import base64
import hashlib
import json
import math
import os
import re
import shutil
import struct
from pathlib import Path

import halo_map as hm


# Games that use the second-generation (Halo 2 MCC) cache format.
SECOND_GEN_GAMES = {'Halo 2'}
# Games that use the third-generation (Halo 3 MCC) cache format.
# ODST is a third-generation build and its maps parse with Halo3Map. Leaving it out
# sent open_map to the Halo 1 parser, which failed with "Tag index 'tags' magic
# missing" — every ODST patch died before it started.
THIRD_GEN_GAMES = {'Halo 3', 'Halo 3: ODST'}
# Games that use the fourth-generation (Halo: Reach MCC) cache format. Reach is close
# enough to third-gen that `reach_map.ReachMap` is a subclass of `Halo3Map` — but it
# is deliberately NOT in THIRD_GEN_GAMES, because that set also gates behaviour whose
# block offsets are Halo 3's (starting slots, cutscene removal, ident minting) and
# those have not been verified against Reach.
FOURTH_GEN_GAMES = {'Halo Reach'}


def open_map(map_path, game=None):
    """Open a map with the right parser for its game: Halo 2 -> `Halo2Map`
    (second-gen), Halo 3 -> `Halo3Map` (third-gen), Reach -> `ReachMap`
    (fourth-gen), everything else -> the Halo 1 `HaloMap`."""
    g = str(game).strip()
    if g in SECOND_GEN_GAMES:
        import halo2_map
        return halo2_map.Halo2Map(map_path)
    if g in THIRD_GEN_GAMES:
        import halo3_map
        return halo3_map.Halo3Map(map_path)
    if g in FOURTH_GEN_GAMES:
        import reach_map
        return reach_map.ReachMap(map_path)
    return hm.HaloMap(map_path)


class PluginRegistry:
    """Loads Assembly plugins per tag group, honoring an MCC override order
    (e.g. Halo1MCC before Halo1). Missing plugins resolve to None, not errors."""

    def __init__(self, plugins_root, subdirs):
        self.root = Path(plugins_root) if plugins_root else None
        self.subdirs = list(subdirs or [])
        self.cache = {}

    def get(self, group):
        if group in self.cache:
            return self.cache[group]
        plugin = None
        if self.root:
            for sub in self.subdirs:
                f = self.root / sub / f"{group}.xml"
                if f.is_file():
                    try:
                        plugin = hm.Plugin(f)
                    except Exception:
                        plugin = None
                    break
        self.cache[group] = plugin
        return plugin


def collect_effects(rounds, mission_id=None, valid_bosses=None):
    """Unique patchable effects from a run's rounds, in first-seen order, each
    with a selection `count`, and a source `group`/`cat` (specific weapon,
    player-general, specific enemy, enemy-general, friend, boss, exhaust) for
    display. Exhausts are one-map negatives: an exhaust is only included when
    patching the mission it was rolled in (mission_id), so leaving that mission
    drops it automatically (paired with apply_run's idempotent re-patch).

    `valid_bosses` works the same way for bosses: pass the boss names the mission
    being patched can actually field, and effects for a boss that no longer turns up
    are left out instead of cluttering the list with edits that can't do anything.
    They come back on their own if a later mission fields that boss again. Omit it
    (None) to keep every boss — callers without the database in hand, such as the
    magnitude collector, shouldn't silently drop effects."""
    seen, order = {}, []

    def add(mod, group, cat):
        if not isinstance(mod, dict) or mod.get('_game_excluded'):
            return
        tag = mod.get('tag')
        if not tag:
            return
        # A tag may still be a per-GAME dict ({'Halo 1': ..., 'Halo 3': ...}) when the
        # caller hasn't resolved it for a specific game — the patcher resolves first,
        # but the save path collects straight off the raw run. A dict can't be a dict
        # key, so flatten it for identity only; the entry keeps the original value.
        key = (tag if isinstance(tag, str) else repr(sorted(tag.items())),
               mod.get('name'))
        if key not in seen:
            seen[key] = {'name': mod.get('name'), 'desc': mod.get('desc', ''),
                         'desc_overrides': mod.get('desc_overrides'),  # #7
                         'tag': tag, 'targets': list(mod.get('targets') or []),
                         'skull': mod.get('skull'),
                         'affected_by_skull': mod.get('affected_by_skull'),
                         'harder_when': mod.get('harder_when'),
                         'easier_when': mod.get('easier_when'),
                         'init_defaults': mod.get('init_defaults'),
                         'constraints': mod.get('constraints'),
                         '_missing_in_db': mod.get('_missing_in_db'),
                         # source identity, so the patcher can remove it from the run
                         'weapon': mod.get('weapon'), 'enemy': mod.get('enemy'),
                         'equipment': mod.get('equipment'),
                         'group': group, 'cat': cat, 'count': 0}
            order.append(key)
        seen[key]['count'] += 1

    for rd in rounds or []:
        for pk in ('player1', 'player2'):
            mod = (rd.get(pk) or {}).get('mod')
            if isinstance(mod, dict):
                src = mod.get('weapon') or mod.get('equipment')
                add(mod, src if src else 'Player (general)', 0 if src else 1)
        for k in ('enemy1', 'enemy2'):
            mod = rd.get(k)
            if isinstance(mod, dict):
                # An effect whose tag several enemies share edits all of them, so it
                # belongs under the general group even though it was drafted from one
                # enemy's card (flagged upstream, where the game is known).
                specific = mod.get('enemy') and not mod.get('_generic_target')
                add(mod, mod['enemy'] if specific else 'Enemy (general)',
                    2 if specific else 3)
        # Displayed as Ally; the round key stays `wildcard` so saved runs still load.
        add(rd.get('wildcard'), 'Friend / Ally', 4)
        add(rd.get('wildcard2'), 'Friend / Ally', 4)    # player 2's ally slot
        # Heroes are drawn from the Other slot but are boss cards in every way that
        # matters here -- same section, same category, same valid_bosses check.
        for k in ('boss1', 'boss2', 'hero1', 'hero2'):
            b = rd.get(k)
            if isinstance(b, dict) and valid_bosses is not None:
                if b.get('boss') and b['boss'] not in valid_bosses:
                    continue        # that boss doesn't appear in this mission
            # One section per boss/hero rather than a single "Boss" heap: a level
            # can field several (Reach's Pillar of Autumn fields four) and lumping
            # them together hid which character each card actually hits.
            add(b, 'Boss: %s' % b['boss'] if isinstance(b, dict) and b.get('boss')
                else 'Boss', 5)
        # Skulls carry no per-field targets; they reach the patcher through their
        # `skull` key, and they only get there by being collected here first.
        for k in ('skull1', 'skull2'):
            add(rd.get(k), 'Skull', 4)
        for k in ('exhaust1', 'exhaust2'):
            ex = rd.get(k)
            if isinstance(ex, dict) and (mission_id is None
                                         or ex.get('_exhaust_mission') == mission_id):
                add(ex, 'Exhaust', 6)
    return [seen[k] for k in order]


# Bump when the MEANING of a written value changes, so codes from before and after
# don't compare equal and quietly suggest two players are in sync when they aren't.
SIGNATURE_VERSION = 1


def patch_signature(results, map_path=None, difficulty=None):
    """A short code identifying WHAT a patch wrote, for two players to compare.

    Built from the writes that actually landed — tag, field and the resulting value —
    not from the typed magnitudes, because the same magnitude on a different starting
    value produces different gameplay, and that is the disagreement worth catching.
    Sorted, so the order effects happen to be applied in can't change it, and rounded,
    so float noise can't either. The map and difficulty are folded in as well: the same
    edits on another level or difficulty are not the same patch.

    Codes are only comparable between the same tool version, since a change to how a
    value is computed SHOULD produce a different code — hence SIGNATURE_VERSION, bumped
    whenever the way values are computed changes."""
    lines = []
    for r in results or []:
        if not (r.get('ok') and not r.get('skip')):
            continue                       # skips/failures wrote nothing
        new = r.get('new')
        if isinstance(new, float):
            new = f"{new:.4f}"
        lines.append(f"{r.get('tag', '')}|{r.get('field', '')}|{new}")
    if not lines:
        return None
    head = f"{os.path.basename(str(map_path or ''))}|{difficulty or ''}|{SIGNATURE_VERSION}"
    blob = head + '\n' + '\n'.join(sorted(lines))
    digest = hashlib.sha256(blob.encode('utf-8')).digest()
    code = base64.b32encode(digest).decode('ascii').rstrip('=')[:8]
    return f"{code[:4]}-{code[4:8]}"


def _tag_variants(tag):
    """Every concrete tag string a mod's `tag` can stand for. A run holds effects
    UNRESOLVED, so the tag may still be a {game: tag} dict (see collect_effects)."""
    if isinstance(tag, str):
        return [tag]
    if isinstance(tag, dict):
        return [v for v in tag.values() if isinstance(v, str)]
    return []


def latest_round_keys(rounds, mission_id=None):
    """(tag, name) for every effect picked in the LAST round, so the patcher can
    highlight this round's picks — including ones drafted in an earlier round too,
    which carry no other visual cue and are otherwise hard to find in a long list.

    Built by running collect_effects over just that round, so it follows exactly the
    same slots (both players, enemies, wildcards, bosses, exhausts) automatically."""
    if not rounds:
        return set()
    keys = set()
    for e in collect_effects(rounds[-1:], mission_id):
        for tag in _tag_variants(e.get('tag')):
            keys.add((tag, e.get('name')))
    return keys


def group_effects(effects):
    """Group effects by their source group, ordered (weapons, player, specific
    enemies, enemy-general, friend, boss), then by group name. Returns an
    ordered list of (group_name, [effects])."""
    groups = {}
    for e in effects:
        groups.setdefault(e.get('group', '?'), []).append(e)
    def key(g):
        return (min(x.get('cat', 9) for x in groups[g]), g)
    return [(g, groups[g]) for g in sorted(groups, key=key)]


def preset_key(tag, name, field, game=None):
    """Cache key for a remembered magnitude/preset. `game` is included so the
    same effect can have different remembered values per game — most tags
    already differ by game (naturally separating the cache), but a few (e.g.
    matg-based effects) share the same tag/field in both games, and the right
    magnitude for the same field can still differ in scale between engines."""
    base = f"{tag}||{name}||{field}"
    return f"{base}||{game}" if game else base


def load_presets(path):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_presets(path, presets):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(presets, f, indent=2, ensure_ascii=False)


def default_map_path(mcc_root, map_subdir, mission_id):
    """<mcc_root>/<map_subdir>/<mission>.map. Falls back to a prefix match
    (<mission>*.map) so a mission id like '01b' resolves to Halo 2's
    '01b_spacestation.map'."""
    if not map_subdir or not mcc_root:
        return ''
    d = Path(mcc_root).resolve() / map_subdir
    exact = d / f'{mission_id}.map'
    if exact.is_file():
        return str(exact)
    matches = sorted(d.glob(f'{mission_id}*.map'))
    return str(matches[0]) if matches else str(exact)


def baseline_path(map_path, baseline_root=None, map_subdir=None):
    """Where the PRISTINE copy of `map_path` lives -- the bytes every patch rebuilds from.

    Two stores, one meaning. With no `baseline_root` this is the sibling `<map>.bak`
    every game has always used. Given a root it becomes
    `<baseline_root>/<map_subdir>/<map name>`, so the originals can sit on another
    drive and the game folder holds only what MCC actually loads -- which also puts
    them out of reach of a Steam update, which deletes modded maps in place.

    `map_subdir` is carried through because one root has to hold five games whose map
    names collide: Halo 1 and Reach both use bare mission ids.

    A root that resolves back onto the live map itself is ignored rather than obeyed --
    patching would then read and write one file and the "seed the pristine copy" step
    would copy it over itself.
    """
    sibling = str(map_path) + '.bak'
    if not baseline_root:
        return sibling
    d = Path(baseline_root)
    if map_subdir:
        d = d / map_subdir
    cand = d / Path(map_path).name
    same = (os.path.normcase(os.path.abspath(str(cand)))
            == os.path.normcase(os.path.abspath(str(map_path))))
    return sibling if same else str(cand)


# Some H2 char fields (e.g. Placement Properties' Upgrade Chance family) are
# difficulty-variant by SUFFIX ("<field> (Legendary)") using different tier
# names than the matg/weap-style difficulty PREFIX ("Impossible <field>"),
# which uses the tool's own Easy/Normal/Hard/Impossible combo-box names.
DIFFICULTY_SUFFIX_MAP = {'Easy': 'Easy', 'Normal': 'Normal', 'Hard': 'Heroic', 'Impossible': 'Legendary'}


def apply_difficulty(field, op, target_difficulty):
    """Expand a field name for the run's configured difficulty, per the
    target's flavor: 'difficulty' prefixes the matg/weap-style name; 'diff_suffix'
    appends the char-plugin style "(Name)" using DIFFICULTY_SUFFIX_MAP; 'diff_prefix'
    PREPENDS that same Heroic/Legendary tier name (e.g. H2 char Accuracy fields are
    named "Legendary Accuracy Bounds"). Note there is no 'Easy' accuracy tier, so an
    Easy run simply won't resolve those and skips them."""
    if op.get('difficulty'):
        return f"{target_difficulty} {field}"
    if op.get('diff_suffix'):
        return f"{field} ({DIFFICULTY_SUFFIX_MAP.get(target_difficulty, target_difficulty)})"
    if op.get('diff_prefix'):
        # H2 char accuracy tiers are Normal/Heroic/Legendary — there is NO 'Easy'
        # tier, so an Easy run produces a field name that won't resolve and the
        # target is simply skipped (surfaced in the editor as "not defined for …").
        return f"{DIFFICULTY_SUFFIX_MAP.get(target_difficulty, target_difficulty)} {field}"
    if op.get('diff_prefix_nl'):
        # Two-tier fields that only define Normal + Legendary (e.g. H2 Body/Shield
        # Vitality): Impossible -> Legendary, every other difficulty -> Normal.
        tier = 'Legendary' if target_difficulty == 'Impossible' else 'Normal'
        return f"{tier} {field}"
    return field


# The four whole-game dials in `matg globals\globals` -> Difficulty. Each is stored
# per difficulty ("Normal Enemy Damage", "Impossible Rate Of Fire", ...), which is what
# `apply_difficulty` builds, so the baseline only ever touches the tier being played.
DIFFICULTY_BASELINE_FIELDS = {
    'vitality': 'Enemy Vitality',
    'shield': 'Enemy Shield',
    'damage': 'Enemy Damage',
    'rof': 'Rate Of Fire',
}


def read_difficulty_baseline(m, registry, target_difficulty):
    """{key: current value} for the four dials at this difficulty, or None per key."""
    plugin = registry.get('matg')
    out = {}
    for key, field in DIFFICULTY_BASELINE_FIELDS.items():
        out[key] = None
        if plugin is None:
            continue
        try:
            out[key] = m.read_first('matg', 'globals' + chr(92) + 'globals',
                                    '%s %s' % (target_difficulty, field), plugin,
                                    block='Difficulty')
        except Exception:
            pass
    return out


def name_enum_results(results, fld):
    """Annotate an enum field's results with the OPTION NAMES behind old/new.

    The raw codes are meaningless to read back ("2 -> 1") and, on any enum a game
    reordered, actively misleading -- Reach's Firing Noise 4 is Halo 3's 2. The
    numbers stay on the row for anything that computes with them; the summary and the
    patch file prefer the names.
    """
    opts = (fld or {}).get('options') or {}
    if not opts:
        return results
    byval = {v: n for n, v in opts.items()}
    for r in results:
        for key in ('old', 'new'):
            v = r.get(key)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                n = byval.get(int(v))
                if n:
                    r[key + '_name'] = n.title()
    return results


def apply_difficulty_baseline(m, registry, target_difficulty, spec):
    """Set the whole-game enemy dials BEFORE any effect runs.

    `spec` = {'vitality'|'shield'|'damage'|'rof': absolute value or None}. A None (or a
    value equal to what is already there) leaves the field alone.

    These are SET, not scaled, and they run first on purpose: every enemy effect in a
    run then multiplies up from the chosen baseline rather than from Bungie's. Because
    `apply_run` always rebuilds from the pristine `.bak`, "before" means the shipped
    value every time -- the baseline never compounds across patches.
    """
    plugin = registry.get('matg')
    rows = []
    if not spec:
        return rows
    base = {'effect': 'Difficulty baseline', 'tag': 'matg globals' + chr(92) + 'globals'}
    if plugin is None:
        return [{**base, 'field': 'baseline', 'ok': False, 'reason': 'no matg plugin'}]
    for key, field in DIFFICULTY_BASELINE_FIELDS.items():
        want = spec.get(key)
        if want is None:
            continue
        name = '%s %s' % (target_difficulty, field)
        # apply_field already returns summary-shaped rows (ok/old/new, or ok=False with
        # a reason), so they are labelled and passed straight through rather than the
        # result being re-derived here.
        for r in m.apply_field('matg', 'globals' + chr(92) + 'globals', name, 'set',
                               float(want), plugin, block='Difficulty'):
            rows.append({**r, **base})
    return rows


def _apply_derived(m, cls, path, effect_name, op, plugin):
    """Write a derived field (sum of its source fields' current values) into
    every tag matching (cls, path). Needs the per-tag read/write interface of
    the H2 parser; H1 has no derived fields."""
    field, block = op['field'], op.get('block')
    index = op.get('index', 0) or 0
    ref = f"{cls} {path}"
    if not hasattr(m, 'p2o'):  # H2-only marker; H1 HaloMap also has read_tag_field
        return [{'effect': effect_name, 'tag': ref, 'field': field,
                 'ok': False, 'skip': True, 'reason': 'derived fields are Halo 2 only'}]
    tags = m.find_tags(cls, path)
    if not tags:
        return [{'effect': effect_name, 'tag': ref, 'field': field,
                 'ok': False, 'reason': 'not present in this map'}]
    results = []
    for tpath, tbase in tags:
        vals = [m.read_tag_field(tbase, sf, plugin, block, index)
                for sf in op['derived']]
        r = {'effect': effect_name, 'tag': f"{cls} {tpath}", 'field': field,
             'derived': True}
        if any(v is None for v in vals):
            results.append({**r, 'ok': False, 'reason': 'source field unresolved'})
            continue
        total = sum(vals)
        old = m.write_tag_field(tbase, field, total, plugin, block, index)
        if old is None:
            results.append({**r, 'ok': False, 'reason': 'derived field unresolved'})
        else:
            results.append({**r, 'ok': True, 'old': old, 'new': total})
    return results


def _apply_constraints(m, cls, path, effect_name, constraints, plugin):
    """Hold an effect's declared relations between two of its own fields.

    Each entry: {field, block, index, not_above | not_below, of}. After the effect's
    ops have run, `field` is re-read per tag and clamped to the current value of `of`
    if it has crossed it. Per tag rather than via read_first, because one card may name
    several tags (ODST's plasma_rifle & plasma_rifle_red) whose values differ.

    Reports only when it actually moves something — a clamp that fires silently would
    look like the typed magnitude was ignored.
    """
    out = []
    tags = m.find_tags(cls, path)
    if not tags:
        return out
    for c in constraints or []:
        field, other = c.get('field'), c.get('of')
        if not field or not other:
            continue
        block, index = c.get('block'), c.get('index', 0) or 0
        for tpath, tbase in tags:
            try:
                v = m.read_tag_field(tbase, field, plugin, block, index)
                ov = m.read_tag_field(tbase, other, plugin, block, index)
            except Exception:
                continue
            if v is None or ov is None:
                continue
            over = c.get('not_above') and v > ov
            under = c.get('not_below') and v < ov
            if not (over or under):
                continue
            m.write_tag_field(tbase, field, ov, plugin, block, index)
            out.append({'effect': effect_name, 'tag': f"{cls} {tpath}", 'field': field,
                        'ok': True, 'old': v, 'new': ov, 'clamped': True,
                        'reason': '%s must not be %s %s'
                                  % (field, 'above' if over else 'below', other)})
    return out


# --- giving an INHERITING character its own tag block -------------------------
#
# Character tags inherit through `Parent Character` (a tagRef at +0x4 in Halo 2,
# Halo 3, ODST and Reach alike). Several Hero-class enemies define nothing of their
# own -- Halo 2's elite_honor_guard and Halo 3/ODST's elite_specops_commander
# populate NO blocks at all -- so their Vitality Properties reflexive is count 0 and
# a card aimed at them patches nothing, while a card aimed at the parent buffs every
# sibling. Seeding the child its own copy is what makes such a card possible.
#
# The DATUM inside a tagRef is not at a fixed offset: Halo 2's tagRefs are 8 bytes
# with it at +0x4, everything later 16 bytes with it at +0xC -- the same split
# _STARTING_SLOTS records for weapon refs. Reading Halo 2 with the later offset picks
# a WRONG parent and seeds from garbage, which is exactly what it did before this was
# pinned down, so it is derived from the parser rather than guessed.
_PARENT_REF = 0x4
# Only carve from a zero run far larger than the request, and stay clear of the very
# end of the partition, so a short run that is really data is never touched.
_SLACK_MARGIN = 0x40
_SLACK_MIN_RUN = 0x400


def _tagref_datum(m):
    return 0x4 if type(m).__name__ == 'Halo2Map' else 0xC


def _parent_tag(m, base, datum):
    ident = m.u32(base + _PARENT_REF + datum)
    if ident == 0xFFFFFFFF:
        return None
    t = m.tag(ident & 0xFFFF) if hasattr(m, 'tag') else None
    return t if t and t.get('base') is not None else None


def seed_ancestor(m, base, blk_off, datum=None):
    """Nearest ancestor that actually POPULATES the block.

    One hop is not enough: Halo 3's elite_specops_commander inherits from
    elite_specops, which is itself empty, and the values only appear further up at
    elite_major. The nearest populated ancestor is also the semantically right seed --
    it is what the engine resolves for that character today, so a freshly seeded child
    starts out behaving exactly as it did."""
    datum = _tagref_datum(m) if datum is None else datum
    seen, cur = set(), _parent_tag(m, base, datum)
    while cur is not None and cur['name'] not in seen:
        seen.add(cur['name'])
        if m.i32(cur['base'] + blk_off) > 0:
            return cur
        cur = _parent_tag(m, cur['base'], datum)
    return None


def _partition_of(m, off):
    for i, (la, sz, fb) in enumerate(m.partitions):
        if fb is not None and sz and fb <= off < fb + sz:
            return i
    return None


def find_slack(m, size, prefer=None):
    """Carve `size` bytes from the tail of a zero run in a tag partition. `prefer`
    (the partition holding the tag) wins outright -- on Halo 3 and Reach alike every
    char tag lives in the last partition, so the new element belongs beside them."""
    best = None
    for i, (la, sz, fb) in enumerate(m.partitions):
        if not sz or fb is None:
            continue
        end = fb + sz
        run = 0
        while run < sz and m.data[end - 1 - run] == 0:
            run += 1
            if run > 0x40000:
                break
        if run < _SLACK_MIN_RUN or run < size + _SLACK_MARGIN:
            continue
        off = (end - _SLACK_MARGIN - size) & ~0xF
        if m.off2data(off) is None or m.data2off(m.off2data(off)) != off:
            continue
        cand = (off, run, i)
        if i == prefer:
            return cand
        if best is None or run > best[1]:
            best = cand
    return best


def insert_block_element(m, base, blk_off, esize, seed):
    """Give an empty reflexive one element seeded with `seed` bytes.

    Two strategies, picked by what the PARSER can do rather than by game:

      * APPEND, where the parser implements growth (Halo2Map). It relocates the block
        to end-of-image, pads to the 0x1000 segment alignment MCC demands and grows
        file_size/meta_size/tag_data_size. Strictly better than slack, so preferred.
      * SLACK, for the partition parsers (Halo3Map and its Reach subclass), which do
        not implement growth. The tag-data partition carries a long run of trailing
        zeroes -- far more than one element -- so the element is written there and the
        reflexive pointed at it. Nothing moves, so there is nothing to fix up.

    Both are confirmed in game: Reach m10 (slack) and Halo 2 Delta Halo (append) each
    made every Elite unkillable once seeded and repointed.

    Returns (file offset, strategy) or raises ValueError when there is no room."""
    if hasattr(m, 'append_block_element'):
        return m.append_block_element(base, blk_off, esize, seed), 'append'
    if not hasattr(m, 'partitions'):
        raise ValueError('parser %s can neither grow nor address slack'
                         % type(m).__name__)
    spot = find_slack(m, esize, prefer=_partition_of(m, base))
    if spot is None:
        raise ValueError('no usable slack for %d bytes' % esize)
    off, _run, _part = spot
    m.data[off:off + esize] = seed
    struct.pack_into('<i', m.data, base + blk_off, 1)
    struct.pack_into('<I', m.data, base + blk_off + 4, m.off2data(off))
    return off, 'slack'


def _apply_init_defaults(m, spec, registry):
    """One-time seeding of an enemy that lacks a field/block by default (e.g. Elite
    grenades): copy defaults from a `source` tag onto every target variant that
    isn't set yet. Runs BEFORE the effect's normal ops. `spec` (already resolved to
    the active game):
      tag           target variant wildcard (e.g. 'actv characters\\elite\\*')
      source        tag to read defaults from (e.g. Grunt Minor / base Grunt)
      block         (H2) tagblock holding the fields; grown if empty
      grow          True -> seed an EMPTY block with one element. Works in every
                    game: Halo 2 grows the image, the partition parsers use slack.
                    With no `source`, each target is seeded from its own nearest
                    populated ancestor.
      copy          (H1) list of root field names to copy from source
      set           {field: value} forced values (enum names allowed, e.g.
                    'Grenade Stimulus': 'Visible Target')
      only_if_zero  a field that must read 0/None on the target for it to be seeded
    """
    out = []
    cls, path = hm.split_tag(spec['tag'])
    plugin = registry.get(cls)
    if plugin is None:
        return [{'effect': 'init defaults', 'ok': False, 'reason': f'no plugin for {cls}'}]
    block = spec.get('block')
    # `source` is optional for a grow: without one the seed comes from the target's
    # own nearest populated ancestor, which is both more robust than naming a tag
    # (Halo 3's spec-ops commander needs a seed two hops up) and what the engine
    # already resolves for that character.
    src_base = None
    if spec.get('source'):
        scls, spath = hm.split_tag(spec['source'])
        src = m.find_tags(scls, spath)
        if not src:
            return [{'effect': 'init defaults', 'ok': False,
                     'reason': f'init source {spath} not in map'}]
        src_base = src[0][1]
    elif not spec.get('grow'):
        return [{'effect': 'init defaults', 'ok': False,
                 'reason': 'init_defaults needs a source unless it is a grow'}]

    if spec.get('grow') and block:
        bf = next((f for f in plugin.fields
                   if f['block_chain'] and f['block_chain'][-1].lower() == block.lower()), None)
        if not bf:
            return [{'effect': 'init defaults', 'ok': False, 'reason': f'block {block} not in plugin'}]
        boff, esize = bf['block_offsets'][-1], bf['block_sizes'][-1]
        shared = None
        if src_base is not None and m.i32(src_base + boff) > 0:
            leaf = m.follow(src_base, [boff], [esize], 0)
            shared = bytes(m.data[leaf:leaf + esize])
        for tpath, base in m.find_tags(cls, path):
            if m.i32(base + boff) != 0:
                continue                      # already has its own; nothing to seed
            elem = shared
            if elem is None:
                anc = seed_ancestor(m, base, boff)
                if anc is None:
                    out.append({'effect': 'init defaults', 'tag': f'{cls} {tpath}',
                                'ok': False,
                                'reason': f'no ancestor populates {block}'})
                    continue
                leaf = m.follow(anc['base'], [boff], [esize], 0)
                elem = bytes(m.data[leaf:leaf + esize])
            try:
                _off, how = insert_block_element(m, base, boff, esize, elem)
            except ValueError as e:
                out.append({'effect': 'init defaults', 'tag': f'{cls} {tpath}',
                            'ok': False, 'reason': str(e)})
                continue
            out.append({'effect': 'init defaults', 'tag': f'{cls} {tpath}', 'ok': True,
                        'old': '(empty)', 'new': f'{block} seeded ({how})'})
        return out

    copy_fields = spec.get('copy', []) or []
    set_map = spec.get('set', {}) or {}
    only_zero = spec.get('only_if_zero')
    srcvals = {f: m.read_tag_field(src_base, f, plugin, block=block) for f in copy_fields}
    for tpath, base in m.find_tags(cls, path):
        if only_zero is not None:
            cur = m.read_tag_field(base, only_zero, plugin, block=block)
            if cur not in (0, 0.0, None):
                continue
        n = 0
        for f in copy_fields:
            if srcvals.get(f) is not None and m.write_tag_field(base, f, srcvals[f], plugin, block=block) is not None:
                n += 1
        for f, val in set_map.items():
            fld = plugin.find(f, block)
            v = fld['options'].get(str(val).strip().lower()) if (fld and fld.get('options') and isinstance(val, str)) else val
            if v is not None and m.write_tag_field(base, f, v, plugin, block=block) is not None:
                n += 1
        if n:
            out.append({'effect': 'init defaults', 'tag': f'{cls} {tpath}', 'ok': True,
                        'old': '(unset)', 'new': f'{n} default(s) set'})
    return out


# scnr Player Starting Profile weapon-slot byte layout per game. A weapon tagRef is
# ['weap' magic @0][ ... ][id]; H1 is 16 bytes (ident at +0xC), H2 is 8 bytes
# (datum at +0x4). Round fields (int16) follow the ref within the profile element.
_WEAP_MAGIC = 0x77656170
_STARTING_SLOTS = {
    'Halo 1': {'ref_size': 16, 'id_at': 0xC,
               'primary':   {'ref': 0x28, 'loaded': 0x38, 'total': 0x3A},
               'secondary': {'ref': 0x3C, 'loaded': 0x4C, 'total': 0x4E}},
    'Halo 2': {'ref_size': 8, 'id_at': 0x4,
               'primary':   {'ref': 0x28, 'loaded': 0x30, 'total': 0x32},
               'secondary': {'ref': 0x34, 'loaded': 0x3C, 'total': 0x3E}},
    # H3's profile element is 0x58 (MCC) but the weapon slots sit exactly where H1
    # puts them, with the same 16-byte tagRef. Verified against all 11 campaign maps.
    'Halo 3': {'ref_size': 16, 'id_at': 0xC,
               'primary':   {'ref': 0x28, 'loaded': 0x38, 'total': 0x3A},
               'secondary': {'ref': 0x3C, 'loaded': 0x4C, 'total': 0x4E}},
    # ODST's Player Starting Profile is byte-identical to Halo 3's: same 0x58
    # element, same Primary/Secondary Weapon tagRefs at 0x28/0x3C. Checked against
    # both plugins rather than assumed, since almost every other ODST block moved.
    'Halo 3: ODST': {'ref_size': 16, 'id_at': 0xC,
                     'primary':   {'ref': 0x28, 'loaded': 0x38, 'total': 0x3A},
                     'secondary': {'ref': 0x3C, 'loaded': 0x4C, 'total': 0x4E}},
    # Reach moves the Player Starting Profile block (scnr 0x268, element 0x68) but the
    # slots inside it sit exactly where Halo 1 and Halo 3 put them. Read off the Reach
    # plugin and confirmed on all nine campaign maps: every profile carries 'weap'
    # magic at +0x28 and an ident that resolves to the weapon the level really starts
    # you with -- AR on m10/m45/m70, magnum on m50, DMR on m52/m60.
    # 'equipment' is Reach-only: the armor ability the profile spawns you holding,
    # a 16-byte eqip tagRef the earlier games have no equivalent of.
    'Halo Reach': {'ref_size': 16, 'id_at': 0xC, 'equipment': 0x54,
                   'primary':   {'ref': 0x28, 'loaded': 0x38, 'total': 0x3A},
                   'secondary': {'ref': 0x3C, 'loaded': 0x4C, 'total': 0x4E}},
}

# H3 tag idents are (index + salt) << 16 | index. Sampling every tagRef in the
# starting-profile block of all 11 campaign maps gives salt 0xE176 for 159 of 160
# refs, so it's the formula — but the map is asked first (see _h3_ident_salt) and
# this is only the fallback, since one outlier shows the salt isn't truly fixed.
_H3_IDENT_SALT = 0xE176


def _h3_ident_salt(m, scnr_base, boff, esize, count):
    """Recover this map's tag-ident salt from the tagRefs already in its starting
    profiles, so we mint idents the way the map itself does. Falls back to the
    observed constant when a map has no usable reference to learn from."""
    seen = {}
    for i in range(count):
        poff = m.follow(scnr_base, [boff], [esize], i)
        if poff is None:
            continue
        for ro in (0x28, 0x3C):
            rid = struct.unpack_from('<I', m.data, poff + ro + 0xC)[0]
            if rid == 0xFFFFFFFF:
                continue
            idx = rid & 0xFFFF
            t = m.tag(idx)
            if t and t.get('class') == 'weap':
                d = ((rid >> 16) - idx) & 0xFFFF
                seen[d] = seen.get(d, 0) + 1
    return max(seen, key=seen.get) if seen else _H3_IDENT_SALT


def _h3_profile_role(index, name):
    """('chief'|'dervish'|None, is_respawn) for a Player Starting Profile.

    Names are only trustworthy on some maps: 020_base, 030_outskirts, 070_waste and
    120_halo leave the four player profiles named 'player starting profile_N' or
    blank. The index convention does hold everywhere -- 0/1 are chief initial/respawn
    and 2/3 dervish initial/respawn, confirmed by the covenant weapons 2/3 always
    carry. So trust an explicit chief/dervish name where there is one, and fall back
    to the index only for generic/unnamed profiles. Named NPC profiles (marine_*,
    barracks_*, arbiter_*, johnson_swap, elite_insertion, shotty_man...) match
    neither rule and are deliberately left alone."""
    n = (name or '').strip().lower()
    generic = (not n) or n.startswith('player starting profile')
    if 'dervish' in n:
        role = 'dervish'
    elif 'chief' in n:
        role = 'chief'
    elif 'insertion' in n and ('elite' in n or 'arbiter' in n):
        # `elite_insertion` is the opposite number of `chief_insertion` (both ship on
        # 020_base and 040_voi). Only the chief one matched, so starting from one of
        # those insertion points armed player 1 and left player 2 with the map's
        # weapons. Deliberately narrow: the other arbiter_* profiles on 070_waste and
        # 120_halo are scripted mid-level loadout swaps, not spawn points, and the
        # ODST lesson is that a loose "anything not X" rule arms NPCs.
        role = 'dervish'
    elif generic and index in (0, 1):
        role = 'chief'
    elif generic and index in (2, 3):
        role = 'dervish'
    else:
        return None, False
    return role, ('respawn' in n) or (generic and index in (1, 3))


# Reach names its Player Starting Profiles, and unlike Halo 3 the names are worth
# trusting: every one of the 49 campaign profiles says what it is. The catch is that
# the index convention the earlier games rely on is GONE. Nightfall ships
#
#     0 sp_normal_initial   1 sp_heroic_initial   2 sp_legendary_initial
#     3 sp_normal_coop_initial  4 sp_normal_coop_respawn  5 sp_heroic_coop_initial ...
#
# so the pre-H3 default of "write profiles 0 and 1" armed Normal and Heroic and left
# Legendary vanilla, and the respawn options -- which hardcode index 1 -- emptied the
# HEROIC INITIAL profile instead of a respawn one. Both are name-driven here instead.
_REACH_PROFILE_MARKERS = ('single', 'coop', 'initial', 'starting', 'respawn',
                          'default', 'player')


def _reach_profile_role(name, has_ability):
    """(is_player, is_respawn) for a Reach Player Starting Profile.

    The player test is the ARMOR ABILITY, not the name. Every profile Reach actually
    spawns a player on carries one (sprint on most, jet_pack on Exodus's
    profile_jetpack, armor_lockup on the Pillar of Autumn respawns), and across all
    ten campaign maps exactly two profiles lack one: `profile_zealot` on Tip of the
    Spear and `v_profile` on The Package. Both are scripted loadout templates, and
    both are the ones a name-marker rule alone would also have to guess about. The
    ability test is strictly the more inclusive of the two -- it keeps the per-area
    player profiles (profile_outpost, profile_spire, profile_combat, profile_jetpack,
    profile_full_health) that carry no name marker at all. Names are still consulted,
    so a profile that says what it is is trusted even if the ability ref is missing."""
    n = (name or '').strip().lower()
    is_player = bool(has_ability) or any(k in n for k in _REACH_PROFILE_MARKERS)
    return is_player, ('respawn' in n)


def _reach_profiles(m, game, scnr_base, boff, esize, count):
    """{index: (is_player, is_respawn)} for every Reach starting profile."""
    lay = _STARTING_SLOTS.get(game) or {}
    eq = lay.get('equipment')
    roles = {}
    for i in range(count):
        poff = m.follow(scnr_base, [boff], [esize], i)
        if poff is None:
            continue
        nm = bytes(m.data[poff:poff + 0x20]).split(b'\0')[0].decode('latin1', 'replace')
        has = False
        if eq is not None:
            rid = struct.unpack_from('<I', m.data, poff + eq + lay['id_at'])[0]
            has = rid not in (0, 0xFFFFFFFF) and (rid & 0xFFFF) < len(getattr(m, 'tags', []))
        roles[i] = _reach_profile_role(nm, has)
    return roles


# Profiles the ability toolkit appends to a Halo 2 scenario (sprint_toolkit's
# h2_loosetag.add_sprint_profile). They exist only so the `unarmed` token tag is
# referenced by the scenario -- they are never spawned into -- and they are always
# appended AFTER the level's own profiles.
_H2_TOOL_PROFILE_PREFIX = 'ab_'
_H2_RESPAWN_NAME = 'respawn profile'      # what Bungie calls it on 03a/03b


def _profile_name(m, poff):
    return bytes(m.data[poff:poff + 0x20]).split(b'\0')[0].decode('latin1', 'replace')


def _h2_profile_names(m, scnr_base, boff, esize, count):
    out = []
    for i in range(count):
        poff = m.follow(scnr_base, [boff], [esize], i)
        out.append('' if poff is None else _profile_name(m, poff))
    return out


#: ODST profile names that are NOT player spawn profiles. `weapon insert` and
#: `insertion_profile` are templates the level's scripts hand a weapon from; every ODST
#: map trails its real profiles with them (Mombasa Streets has fourteen).
_SCRIPTED_PROFILE_NAMES = ('weapon insert', 'insertion_profile')


def _is_scripted_profile(name):
    return str(name or '').strip().lower() in _SCRIPTED_PROFILE_NAMES


def odst_profile_for(m, game, scnr_base, boff, esize, count, insertion_ordinal, player):
    """Index of the Player Starting Profile ODST uses for `player` at the
    `insertion_ordinal`-th live insertion point, or None.

    UNVERIFIED IN GAME -- this is the phase-4 test. The stride of four is inferred from
    naming and count across all nine maps: ODST supports four co-op players, every map
    declares exactly four starting locations per insertion point, and ONI Alpha Site
    names its first eight profiles

        0..3   Player, odst02, odst03, odst04
        4..7   dutch,  odst02, odst03, odst04

    which is one group of four per insertion point, player-major, with player 1 named
    for the character whose flashback it is (sc130 is Dutch's). Maps that do not name
    their profiles ship sixteen generic `player starting profile_N` -- four points'
    worth -- followed by the scripted ones.

    `insertion_ordinal` is the position of the insertion point among those the level
    actually uses, ascending, NOT the raw insertion index: Mombasa Streets uses 0, 7
    and 8, and its profile groups are 0-3, 4-7, 8-11.
    """
    idx = insertion_ordinal * 4 + player
    if not (0 <= idx < count):
        return None
    poff = m.follow(scnr_base, [boff], [esize], idx)
    if poff is None or _is_scripted_profile(_profile_name(m, poff)):
        return None
    return idx


def _h2_own_profiles(names):
    """Indices of the LEVEL's own starting profiles, i.e. everything before the
    toolkit's appended `ab_*` ones. Writing the run's weapons into `ab_sprint`
    replaces the `unarmed` token the sprint ability is built on, and on
    08b_deltacontrol -- the one map with a single profile -- `ab_sprint` lands at
    index 1, exactly where the default [0, 1] write goes."""
    return [i for i, n in enumerate(names)
            if not n.strip().lower().startswith(_H2_TOOL_PROFILE_PREFIX)]


def _h2_has_respawn_profile(names):
    """True if this map already has a second profile of its own to respawn into."""
    return len(_h2_own_profiles(names)) >= 2


def _h2_add_respawn_profile(m, registry):
    """Give a Halo 2 map a second Player Starting Profile, copied from the first.

    Every Halo 2 campaign map ships two -- index 0 for the initial spawn and index 1
    for respawning, named outright as such on 03a/03b ('respawn profile') and 07b
    ('coop respawn') -- EXCEPT 08b_deltacontrol, which ships exactly one. So a co-op
    death on The Great Journey respawns you with whatever the engine falls back to
    rather than with the run's weapons, and there is no profile for the patcher to
    write them into either.

    The new element is a verbatim copy of profile 0, so every field this code does
    not model (health/shield scales, grenade counts, the two weapon tagRefs and their
    round counts) keeps a known-good value; only the name is rewritten. It is then
    moved into position ahead of any `ab_*` toolkit profile, because the engine picks
    the respawn profile by INDEX and the toolkit's profile would otherwise sit in the
    slot the respawn profile has to occupy.

    Returns a result row. Structural (it relocates the block to end-of-image via
    grow_block, the same mechanism the H2 camo placement and the HUD passes use), so
    it is a no-op on any map that already has its own second profile.
    """
    scnr_plug = registry.get('scnr')
    scnr_base = _scnr_base(m)
    if scnr_plug is None or scnr_base is None:
        return {'effect': 'respawn profile', 'ok': False,
                'field': 'Player Starting Profile', 'reason': 'scnr plugin/tag unavailable'}
    bf = None
    for fn in ('Starting Health Damage', 'Starting Health Modifier'):
        bf = scnr_plug.find(fn, 'Player Starting Profile')
        if bf:
            break
    if not bf:
        return {'effect': 'respawn profile', 'ok': False,
                'field': 'Player Starting Profile', 'reason': 'block not in the scnr plugin'}
    boff, esize = bf['block_offsets'][-1], bf['block_sizes'][-1]
    count = m.i32(scnr_base + boff)
    if count < 1:
        return {'effect': 'respawn profile', 'ok': True, 'skip': True,
                'field': 'Player Starting Profile',
                'reason': 'this level has no starting profiles at all'}
    names = _h2_profile_names(m, scnr_base, boff, esize, count)
    if _h2_has_respawn_profile(names):
        # 12 of the 13 Halo 2 maps ship their own respawn profile; only
        # 08b_deltacontrol does not. Reporting a skip for the normal case put a row on
        # every other map that read like something had gone wrong, so say nothing and
        # let the one map that needs the work be the only one that shows up.
        return None
    src = m.follow(scnr_base, [boff], [esize], 0)
    if src is None:
        return {'effect': 'respawn profile', 'ok': False,
                'field': 'Player Starting Profile', 'reason': 'profile 0 unreadable'}
    elem = bytearray(m.data[src:src + esize])
    elem[0:0x20] = _H2_RESPAWN_NAME.encode('latin1')[:0x1F].ljust(0x20, b'\0')
    try:
        base = m.grow_block(scnr_base, boff, esize, [bytes(elem)])
    except Exception as e:
        return {'effect': 'respawn profile', 'ok': False,
                'field': 'Player Starting Profile', 'reason': str(e)}
    # grow_block appends, so the copy lands last. Rotate it into the slot right after
    # the level's own profiles, ahead of any ab_* the toolkit appended.
    want = len(_h2_own_profiles(names))
    last = count                       # index of the element just appended
    if want < last:
        blob = bytes(m.data[base:base + (count + 1) * esize])
        elems = [blob[i * esize:(i + 1) * esize] for i in range(count + 1)]
        elems.insert(want, elems.pop(last))
        m.data[base:base + (count + 1) * esize] = b''.join(elems)
    return {'effect': 'respawn profile', 'ok': True,
            'field': 'Player Starting Profile',
            'old': '%d profile(s), no respawn slot' % count,
            'new': 'added %r at index %d (copied from profile 0)'
                   % (_H2_RESPAWN_NAME, want)}


# Halo 2 scnr Squads. Offsets are from the Halo2MCC scnr plugin, checked against
# 08b_deltacontrol's 112 squads: element 0x74, name at +0x00, the two difficulty
# counts at +0x2C/+0x2E, and the Starting Locations child reflexive at +0x48 with a
# flat 0x64 element (no blocks of its own, so an element copies verbatim).
_H2_SQUAD_NORMAL_COUNT = 0x2C
_H2_SQUAD_INSANE_COUNT = 0x2E
_H2_SQUAD_STARTLOCS = 0x48
_H2_SQUAD_STARTLOC_SIZE = 0x64


def _h2_squads_block(m, registry):
    """(scnr_base, block_offset, elem_size, count) for the Squads block, or None."""
    scnr_plug = registry.get('scnr')
    scnr_base = _scnr_base(m)
    if scnr_plug is None or scnr_base is None:
        return None
    f = scnr_plug.find('Normal Difficulty Count', 'Squads')
    if not f:
        return None
    boff, esize = f['block_offsets'][-1], f['block_sizes'][-1]
    return scnr_base, boff, esize, m.i32(scnr_base + boff)


def _h2_find_squad(m, registry, name):
    """File offset of the squad element with this name, or None."""
    blk = _h2_squads_block(m, registry)
    if blk is None:
        return None
    scnr_base, boff, esize, count = blk
    want = name.strip().lower()
    for i in range(count):
        soff = m.follow(scnr_base, [boff], [esize], i)
        if soff is None:
            continue
        if _profile_name(m, soff).strip().lower() == want:
            return soff
    return None


def _h2_duplicate_squad(m, registry, squad_name, extra, spread=0.6):
    """Make a Halo 2 AI squad spawn `extra` more actors than it ships with.

    Halo 2 spawns min(difficulty count, len(Starting Locations)) actors for
    `ai_place <squad>` -- every squad on 08b has at least as many starting locations
    as its count, and the reinforcement squads carry 6-8 locations for a count of 2-4.
    So growing a squad means BOTH raising the two difficulty counts and giving it
    somewhere for the extra actors to stand.

    The new locations are verbatim copies of location 0 (a flat 0x64 struct with no
    child blocks, so a copy needs no fix-ups), nudged apart in X/Y by `spread` metres
    so two actors are not asked to occupy the same point. Anything the squad's command
    script does -- 08b sends Johnson to boss/ledge_perch -- then moves them properly.

    Returns a result row.
    """
    label = 'squad %s' % squad_name
    if extra <= 0:
        return {'effect': label, 'ok': True, 'skip': True, 'field': 'Squads',
                'reason': 'no extra actors requested'}
    soff = _h2_find_squad(m, registry, squad_name)
    if soff is None:
        return {'effect': label, 'ok': True, 'skip': True, 'field': 'Squads',
                'reason': 'no squad by that name on this level'}
    normal = struct.unpack_from('<h', m.data, soff + _H2_SQUAD_NORMAL_COUNT)[0]
    insane = struct.unpack_from('<h', m.data, soff + _H2_SQUAD_INSANE_COUNT)[0]
    nloc = m.i32(soff + _H2_SQUAD_STARTLOCS)
    if nloc < 1:
        return {'effect': label, 'ok': False, 'field': 'Squads',
                'reason': 'squad has no starting locations to copy'}
    lbase = _block_base(m, soff + _H2_SQUAD_STARTLOCS)
    if not lbase:
        return {'effect': label, 'ok': False, 'field': 'Squads',
                'reason': 'starting locations unreadable'}
    es = _H2_SQUAD_STARTLOC_SIZE
    proto = bytes(m.data[lbase:lbase + es])
    px, py, pz = struct.unpack_from('<fff', proto, 0)
    copies = []
    for k in range(extra):
        e = bytearray(proto)
        ang = 2.0 * math.pi * (k + 1) / (extra + 1)
        struct.pack_into('<fff', e, 0,
                         px + spread * math.cos(ang), py + spread * math.sin(ang), pz)
        copies.append(bytes(e))
    try:
        m.grow_block(soff, _H2_SQUAD_STARTLOCS, es, copies)
    except Exception as e:
        return {'effect': label, 'ok': False, 'field': 'Squads', 'reason': str(e)}
    struct.pack_into('<h', m.data, soff + _H2_SQUAD_NORMAL_COUNT,
                     max(1, min(32767, normal + extra)))
    struct.pack_into('<h', m.data, soff + _H2_SQUAD_INSANE_COUNT,
                     max(1, min(32767, insane + extra)))
    return {'effect': label, 'ok': True, 'field': 'Squads',
            'old': '%d actor(s), %d start location(s)' % (normal, nloc),
            'new': '%d actor(s), %d start location(s)' % (normal + extra, nloc + extra)}


def _weap_ref_id(m, name, game=None, salt=None):
    """Full tag ident (H1/H3) / datum (H2) for a weap tag by name, or None if that
    tag isn't in this map — the safety net for a picked weapon the map lacks."""
    if str(game).strip() in (THIRD_GEN_GAMES | FOURTH_GEN_GAMES):
        # The tag table stores a salt PER TAG, so the ident is readable rather than
        # guessable: ident = (salt << 16) | index, parsed into every tag by
        # Halo3Map._parse_index. Checked against every weapon-palette reference on the
        # Halo 3 and Reach campaign maps -- 191 refs, zero mismatches. Reach needs it:
        # its salt varies per tag, so the old fixed-salt mint would produce a ref that
        # points nowhere. The mint stays as a fallback for a map whose table is odd.
        for t in getattr(m, 'tags', []):
            if t.get('class') == 'weap' and t.get('name') == name:
                if t.get('ident'):
                    return t['ident']
                i = t['index']
                s = _H3_IDENT_SALT if salt is None else salt
                return (((i + s) & 0xFFFF) << 16) | (i & 0xFFFF)
        return None
    if isinstance(getattr(m, 'tags', None), dict):          # H1 HaloMap
        for i in range(m.tag_count):
            b = m.tag_array_off + i * 32
            if bytes(m.data[b:b + 4][::-1]).decode('latin1') != 'weap':
                continue
            try:
                if m._cstr((m.u32(b + 0x10) - m.magic) & 0xFFFFFFFF) == name:
                    return m.u32(b + 0xC)
            except Exception:
                pass
        return None
    for t in getattr(m, 'tags', []):                        # H2 Halo2Map
        if t.get('class') == 'weap' and t.get('name') == name:
            return t.get('datum')
    return None


def _weap_base(m, name):
    if isinstance(getattr(m, 'tags', None), dict):
        return m.tags.get(('weap', name))
    for t in getattr(m, 'tags', []):
        if t.get('class') == 'weap' and t.get('name') == name:
            return t.get('base')
    return None


def _scnr_base(m):
    if hasattr(m, 'scenario_tag'):                          # H2
        t = m.scenario_tag()
        return t['base'] if t else None
    tags = m.find_tags('scnr', 'levels' + chr(92) + '*')    # H1
    return tags[0][1] if tags else None


def _write_starting_weapon(m, poff, slot, refid, loaded, total, game):
    lay = _STARTING_SLOTS[game]
    s = lay[slot]
    ro = poff + s['ref']
    struct.pack_into('<I', m.data, ro, _WEAP_MAGIC)
    if lay['ref_size'] == 16:
        struct.pack_into('<II', m.data, ro + 4, 0, 0)       # clear the H1 name-ptr words
    struct.pack_into('<I', m.data, ro + lay['id_at'], refid & 0xFFFFFFFF)
    if loaded is not None:
        struct.pack_into('<h', m.data, poff + s['loaded'], max(-32768, min(32767, int(loaded))))
    if total is not None:
        struct.pack_into('<h', m.data, poff + s['total'], max(-32768, min(32767, int(total))))


def _null_starting_weapon(m, poff, slot, game):
    """Empty a profile's weapon slot: a null tagRef (class + id both -1) and 0 rounds.
    A null secondary is common in vanilla profiles; a null primary starts the player
    empty-handed."""
    lay = _STARTING_SLOTS[game]
    s = lay[slot]
    ro = poff + s['ref']
    struct.pack_into('<I', m.data, ro, 0xFFFFFFFF)
    if lay['ref_size'] == 16:
        struct.pack_into('<II', m.data, ro + 4, 0, 0)
    struct.pack_into('<I', m.data, ro + lay['id_at'], 0xFFFFFFFF)
    struct.pack_into('<h', m.data, poff + s['loaded'], 0)
    struct.pack_into('<h', m.data, poff + s['total'], 0)


def _profile_is_empty(m, poff, game):
    """True if this profile's Primary weapon slot is a null tagRef."""
    lay = _STARTING_SLOTS[game]
    ro = poff + lay['primary']['ref'] + lay['id_at']
    return struct.unpack_from('<I', m.data, ro)[0] == 0xFFFFFFFF


def _apply_starting_equipment(m, game, registry, starting):
    """Set the player Starting Profile weapons from the run's picks. `starting` =
    {'primary': weap-tag or None, 'secondary': weap-tag or None, 'profiles': [..]}.
    Rounds come from each weap tag's CURRENT Magazines values (so a Magazine effect
    already applied this run carries through; else vanilla). Missing weapons are
    skipped, not written (safety net)."""
    out = []
    scnr_plug = registry.get('scnr')
    weap_plug = registry.get('weap')
    scnr_base = _scnr_base(m)
    if scnr_plug is None or scnr_base is None:
        return [{'effect': 'starting weapons', 'ok': False,
                 'reason': 'scnr plugin/tag unavailable'}]
    bf = None
    for fn in ('Starting Health Damage', 'Starting Health Modifier'):
        bf = scnr_plug.find(fn, 'Player Starting Profile')
        if bf:
            break
    lay = _STARTING_SLOTS.get(game)
    if not bf or not lay:
        return [{'effect': 'starting weapons', 'ok': False,
                 'reason': 'Player Starting Profile layout unavailable'}]
    boff = bf['block_offsets'][-1]
    esize = bf['block_sizes'][-1]
    count = m.i32(scnr_base + boff)
    third_gen = str(game).strip() in THIRD_GEN_GAMES
    salt = _h3_ident_salt(m, scnr_base, boff, esize, count) if third_gen else None

    def _null_profiles(idxs, label):
        for i in idxs:
            poff = m.follow(scnr_base, [boff], [esize], i)
            if poff is None:
                continue
            for slot in ('primary', 'secondary'):
                _null_starting_weapon(m, poff, slot, game)
            out.append({'effect': 'starting weapons', 'field': label(i),
                        'ok': True, 'old': 'weapons', 'new': 'emptied (null)'})

    # A plan of (weapon slot, [profile indices], weap tag, report label). H3 with
    # 2-player coop is the only case where the two picks land on different profiles
    # rather than the two slots of the same one (#8).
    prim, sec = starting.get('primary'), starting.get('secondary')
    if starting.get('spawn_instead'):
        # The picks are being PLACED at the markers instead of written into a profile.
        # Clearing the slots is the other half of that, not a separate option: leaving
        # them set would hand the player the same weapon twice, once in hand and once
        # on the floor, and the floor copy would look like it had failed to work.
        prim = sec = None
        starting = dict(starting, null_empty_slots=True)
    if game == 'Halo 3' and starting.get('h3_coop'):
        roles = {}
        for i in range(count):
            poff = m.follow(scnr_base, [boff], [esize], i)
            if poff is None:
                continue
            nm = bytes(m.data[poff:poff + 0x20]).split(b'\0')[0].decode('latin1', 'replace')
            roles[i] = _h3_profile_role(i, nm)
        # The coop options act on the respawn profiles here, not on a fixed index 1.
        null_respawn = bool(starting.get('null_respawn'))
        hold_respawn = bool(starting.get('skip_respawn')) or null_respawn
        if null_respawn:
            _null_profiles([i for i, (r, resp) in sorted(roles.items()) if r and resp],
                           lambda i: f'Profile {i} (respawn)')
        def _of(role):
            return [i for i, (r, resp) in sorted(roles.items())
                    if r == role and not (hold_respawn and resp)]
        # guard_empty: this path matches profiles by role rather than by an index the
        # user named, so it can sweep in scripted weaponless ones (chief_pre_training).
        #
        # BOTH slots, not just the primary. Each character here belongs to one player,
        # so their profile carries that player's loadout: their first pick primary,
        # their second (if the run has given them one) secondary. Naming only the
        # primary left the map's own secondary in place, so every co-op spawn came with
        # a free vanilla gun on top of the pick -- profile 0 of 030_outskirts is
        # needler / battle_rifle, and the battle rifle survived every patch.
        #
        # The guard has to make ONE exception. Crow's Nest ships `player starting
        # profile_0` as NULL/NULL and spawns the player on it, so guarding it leaves
        # both players empty-handed -- the very bug the solo path was just fixed for.
        # A role's LOWEST-indexed profile is the one the level spawns that character
        # on, so that one is written unguarded and the rest stay guarded.
        def _split(role):
            got = _of(role)
            return (got[:1], got[1:]) if got else ([], [])

        chief_first, chief_rest = _split('chief')
        derv_first, derv_rest = _split('dervish')
        plan = []
        for slot, tag, label in (('primary', prim, 'Chief Weapon'),
                                 ('secondary', starting.get('primary2'),
                                  'Chief Second Weapon')):
            plan.append((slot, chief_first, tag, label, False))
            if chief_rest:
                plan.append((slot, chief_rest, tag, label + ' (other profiles)', True))
        for slot, tag, label in (('primary', sec, 'Dervish Weapon'),
                                 ('secondary', starting.get('secondary2'),
                                  'Dervish Second Weapon')):
            plan.append((slot, derv_first, tag, label, False))
            if derv_rest:
                plan.append((slot, derv_rest, tag, label + ' (other profiles)', True))
    else:
        # Pre-H3, and H3 with coop off: both picks go on the same profile(s), P1 as
        # Primary and P2 as Secondary. H3 uses profile 0 only — its other profiles
        # belong to the second character or to NPCs.
        # Profile 0 for third-generation games. ODST was briefly given every profile
        # not named *allies*, on the theory that its per-insertion-point profiles meant
        # profile 0 was never the live one. That was wrong: a profile problem would
        # fail every weapon uniformly, and in practice one weapon failed everywhere
        # while another worked on most maps. It was also unsafe — ODST names NPC
        # profiles 'dutch', 'buck', 'odst02', 'Player' and plain 'a', so "not allies"
        # armed squadmates.
        default = [0] if third_gen else [0, 1]
        reach_roles = None
        if str(game).strip() == 'Halo Reach':
            # Reach's profiles are keyed by difficulty AND co-op AND insertion area,
            # so there is no fixed index to write. Every non-respawn player profile
            # gets the picks; the respawn ones are left to the respawn options below.
            reach_roles = _reach_profiles(m, game, scnr_base, boff, esize, count)
            # Default is every player profile, respawns included -- the pre-H3 [0, 1]
            # meant "spawn and respawn", and this is that same intent spelled out for a
            # map that can have nine of them. The respawn options subtract from it.
            hold = bool(starting.get('skip_respawn')) or bool(starting.get('null_respawn'))
            default = [i for i, (pl, resp) in sorted(reach_roles.items())
                       if pl and not (hold and resp)] or [0]
        if str(game).strip() in SECOND_GEN_GAMES:
            # Halo 2's own profiles only: index 1 is the ability toolkit's `ab_sprint`
            # on 08b_deltacontrol (the one map that ships a single profile), and
            # arming it would replace the `unarmed` token the sprint ability needs.
            own = _h2_own_profiles(_h2_profile_names(m, scnr_base, boff, esize, count))
            default = own[:2] or [0]
        nulls = [p for p in (starting.get('null_profiles') or []) if 0 <= p < count]
        if reach_roles is not None:
            # "Empty respawn weapons" means index 1 everywhere else. In Reach index 1
            # is `sp_heroic_initial` on Nightfall and `default_coop` on ONI Sword Base,
            # so honouring it literally emptied a profile the player STARTS on. Ask the
            # names instead, and empty every real respawn profile.
            nulls = ([i for i, (pl, resp) in sorted(reach_roles.items()) if pl and resp]
                     if starting.get('null_respawn') else [])
        _null_profiles(nulls, lambda i: f'Profile {i}')
        if starting.get('by_insertion'):
            # Each player gets the profile their OWN insertion point uses, so the picks
            # follow the player instead of being sprayed across every profile. Both
            # players' profiles are collected here and written together, because this
            # branch feeds the same single `profiles` list the rest of the pre-H3 path
            # uses (P1 primary / P2 secondary on each profile) -- which is right for
            # ODST, where the two co-op players share a slot pair per profile group.
            wanted = []
            for ordinal in range(len(odst_player_starts(m, game)) or 1):
                for player in range(2):
                    p = odst_profile_for(m, game, scnr_base, boff, esize, count,
                                         ordinal, player)
                    if p is not None and p not in wanted:
                        wanted.append(p)
            profiles = wanted or [0]
        elif starting.get('all_profiles'):
            # Deliberate blanket write (ODST option). Which profile ODST spawns the
            # player on follows the insertion point and can change mid-mission, so a
            # run that must not lose its picks arms every one of them.
            #
            # Except the SCRIPTED ones. Every ODST level ends its profile list with
            # entries named `weapon insert` or `insertion_profile` -- Mombasa Streets
            # ships fourteen of them -- and those are not player spawn profiles at all;
            # they are the templates scripts hand a weapon from. Arming them is pure
            # noise, so the blanket write stops short of them.
            names = _h2_profile_names(m, scnr_base, boff, esize, count)
            profiles = [i for i in range(count)
                        if not _is_scripted_profile(names[i])]
        else:
            if reach_roles is not None:
                # The configured index list ([0, 1] by default) means nothing in Reach,
                # where the same two indices are Normal-initial and Heroic-initial on
                # one map and single/co-op on the next. Role selection wins outright.
                profiles = list(default)
            else:
                profiles = [i for i in (starting.get('profiles') or default)
                            if 0 <= i < count]
                if third_gen:
                    profiles = [i for i in profiles if i == 0]
        # No guard here: these profiles were named outright, and a map that starts
        # the player unarmed on purpose (Halo 1's a10) should still honour the picks.
        plan = [('primary', profiles, prim, 'Primary Weapon', False),
                ('secondary', profiles, sec, 'Secondary Weapon', False)]
        # Halo 3 solo: which profile is live depends on the ENTRY POINT. Crow's Nest
        # gives the player a profile per rally point (`ins_motorpool` and friends each
        # call unit_add_equipment with chief_insertion) while the level-start path
        # applies none, so arming index 0 alone leaves several entries untouched.
        # Sweep the other chief-role profiles too, GUARDED so a scripted weaponless
        # state (chief_pre_training) stays weaponless.
        if game == 'Halo 3' and starting.get('h3_all_chief'):
            roles = {}
            for i in range(count):
                poff = m.follow(scnr_base, [boff], [esize], i)
                if poff is None:
                    continue
                nm = bytes(m.data[poff:poff + 0x20]).split(b'\0')[0].decode('latin1', 'replace')
                roles[i] = _h3_profile_role(i, nm)
            extra = [i for i, (r, _resp) in sorted(roles.items())
                     if r == 'chief' and i not in profiles]
            if extra:
                plan += [('primary', extra, prim, 'Chief Weapon (other profiles)', True),
                         ('secondary', extra, sec, 'Chief Second Weapon (other profiles)', True)]

    null_empty = bool(starting.get('null_empty_slots'))
    for slot, profiles, tag, label, guard_empty in plan:
        if not tag:
            # #5: nothing to put here (a grenade pick, or no second player). Empty the
            # slot so the setting visibly takes effect instead of leaving the map's
            # vanilla weapon in place. Profiles already empty are left alone.
            if null_empty:
                n = 0
                for i in profiles:
                    poff = m.follow(scnr_base, [boff], [esize], i)
                    if poff is None or (guard_empty and _profile_is_empty(m, poff, game)):
                        continue
                    _null_starting_weapon(m, poff, slot, game)
                    n += 1
                if n:
                    out.append({'effect': 'starting weapons', 'field': label, 'ok': True,
                                'old': 'map default', 'new': f'emptied on {n} profile(s)'})
            continue
        _, name = hm.split_tag(tag)
        short = name.rsplit(chr(92), 1)[-1]
        refid = _weap_ref_id(m, name, game, salt)
        if refid is None:      # SAFETY NET: weapon tag absent from this map
            out.append({'effect': 'starting weapons', 'field': label,
                        'ok': False, 'reason': f'weapon not in this map: {short}'})
            continue
        wb = _weap_base(m, name)
        loaded = total = None
        if wb is not None and weap_plug is not None:
            loaded = m.read_tag_field(wb, 'Rounds Loaded Maximum', weap_plug, block='Magazines', index=0)
            total = m.read_tag_field(wb, 'Rounds Total Maximum', weap_plug, block='Magazines', index=0)
        # Battery weapons (energy sword, plasma pistol) have no Magazines block, so
        # there are no counts to copy. Vanilla profiles store 0 for these, not the
        # -1 the plugin calls "weapon default" (-1 didn't actually read back as a
        # default in testing), so match vanilla rather than leaving the replaced
        # weapon's counts behind.
        loaded = 0 if loaded is None else loaded
        total = 0 if total is None else total
        n = 0
        for i in profiles:
            poff = m.follow(scnr_base, [boff], [esize], i)
            if poff is None:
                continue
            # A null Primary is deliberate: it's a scripted empty-handed state
            # (chief_pre_training, no_weapon_profile, injured_profile...). Arming
            # those breaks the scene, so leave any weaponless profile weaponless.
            if guard_empty and _profile_is_empty(m, poff, game):
                continue
            _write_starting_weapon(m, poff, slot, refid, loaded, total, game)
            n += 1
        out.append({'effect': 'starting weapons', 'field': label,
                    'ok': True, 'old': short,
                    'new': f'set on {n} profile(s) ({loaded}/{total} rounds)'})
    return out


# ---- Skulls -----------------------------------------------------------------
# "Betrayal": every human squad turns on the player. Campaign maps leave squad
# Team at Default and let the engine resolve allegiance from the character, so
# flipping sides means writing an explicit Team on the squads that are human.
#
# H1 keeps allegiance per ENCOUNTER (squads hang off the encounter); H2 and H3
# keep it per SQUAD, reaching the character through a palette -- directly in H2,
# via the Fire-Teams sub-block in H3.
# Which side the betrayed humans join, per game. Not Covenant: a third faction reads
# as its own event and keeps the Covenant fighting them too. H1's enum has no Heretic
# (slot 6 is Unused6), so Flood is the only real third option there. H3 does define
# Heretic even though the campaign has none, so its allegiances are untested —
# see the note in halo.json's Betrayal entry.
# Flood / Heretic / Heretic / Heretic. Every one of these games declares the same Team
# enum on a squad (0 Default, 1 Player, 2 Human, 3 Covenant, 4 Flood, 5 Sentinel,
# 6 Heretic, 7 Prophet, 8 Guilty), so the value carries; what differs is where the
# squad's CHARACTER reference lives, which is what _BETRAYAL below describes.
_BETRAYAL_TEAM = {'Halo 1': 4, 'Halo 2': 6, 'Halo 3': 6, 'Halo 3: ODST': 6}
_BETRAYAL = {
    'Halo 2': {'squads': (0x160, 0x74), 'team': 0x24, 'char_idx': 0x36,
               'palette': (0x178, 0x08), 'pal_id_at': 0x4, 'fireteams': None},
    'Halo 3': {'squads': (0x384, 0x40), 'team': 0x24, 'char_idx': 0x8,
               'palette': (0x3A8, 0x10), 'pal_id_at': 0xC, 'fireteams': (0x30, 0x60)},
    # ODST's squads are bigger (0x6C) and hold their characters in THREE sub-blocks
    # rather than at a fixed offset, so it cannot use the char_idx/fireteams shape at
    # all -- `cells` names those sub-blocks instead and _odst_squad_chars walks them.
    # Layout verified against sprint_toolkit/odst_squads.py, which reads the same
    # blocks to answer "which tag is this named character".
    'Halo 3: ODST': {'squads': (0x3B8, 0x6C), 'team': 0x24, 'char_idx': None,
                     'palette': (0x3E8, 0x10), 'pal_id_at': 0xC, 'fireteams': None,
                     'single_locations': (0x3C, 0x90, 0x32),
                     'cells': ((0x54, 0x84), (0x60, 0x84)), 'cell_char': (0x14, 0x10, 0xC)},
    # REACH IS NOT WIRED. Its plugin describes the same shape one step further along
    # -- squads 0x398/0x6C with Team at 0x24, palette 0x3EC, Spawn Points 0x3C/0x7C
    # with Character Type Index at 0x32 -- but the shipped maps do not match it: the
    # block at scnr+0x398 reads a count of ZERO on 30_settlement, through both the raw
    # offset and the plugin path that the rest of Reach support uses. So the real
    # scenario layout differs from the plugin and has to be located the way ODST's was
    # before this can be turned on. Wiring it from the plugin alone would produce a
    # Betrayal that silently flips nothing.
}


def _odst_squad_chars(m, sq, lay):
    """Character-palette indices a single ODST squad references.

    Three places carry them and all three are walked, because a squad may use any of
    them: Single Locations (one index per placed character), and the Designer and
    Templated Cells (each with a Character Type sub-block)."""
    out = []
    loff, lel, lci = lay['single_locations']
    for el in m.follow_all(sq, [loff], [lel], 'all'):
        out.append(struct.unpack_from('<h', m.data, el + lci)[0])
    coff2, cel2, cci = lay['cell_char']
    for coff, cel in lay['cells']:
        for cell in m.follow_all(sq, [coff], [cel], 'all'):
            for ct in m.follow_all(cell, [coff2], [cel2], 'all'):
                out.append(struct.unpack_from('<h', m.data, ct + cci)[0])
    return out
# Characters whose squads count as "human" for Betrayal. Matched against the last
# path component of the character/actor tag name. Keep these specific: a loose word
# like "commander" also matches `elite commander energy sword`, which flipped a
# Covenant encounter on b30 until it was removed.
_HUMAN_WORDS = ('marine', 'crewman', 'captain', 'johnson', 'miranda', 'keyes',
                'sergeant', 'pilot', 'civilian', 'odst')


# Belt-and-braces: whatever _HUMAN_WORDS matches, a tag naming a Covenant/Flood/
# Sentinel species is never human. Checked against the WHOLE path, since the species
# usually shows up in a parent folder (`characters\elite\elite commander\...`).
_NONHUMAN_WORDS = ('elite', 'grunt', 'jackal', 'brute', 'hunter', 'flood', 'sentinel',
                   'drone', 'engineer', 'prophet', 'monitor', 'bugger', 'skirmisher')


# Humans that stay loyal: a squad containing one of these never flips, even though it
# classifies as human. These are the STORY characters, and the point is that flipping
# them buys nothing — they are scripted, most of them cannot be killed at all, and the
# sequences that depend on them break instead.
#
# Read off the real char tags rather than guessed, per game:
#   Halo 1   `captain`, `captain_ingame` (Keyes)
#   Halo 2   `marine_johnson*`, `miranda`, `cortana`, `dervish` (the Arbiter)
#   Halo 3   the same, plus `marine_johnson_boss` / `_halo`
#   ODST     `marine_odst_buck*`, `_dare`/`_oni_op`, `_dutch`, `_romeo`, `_mickey`,
#            and `marine_sgt_hero`
# `dervish` matters because the Arbiter is a PLAYER character in co-op.
#
# Matched as substrings against the whole tag path, so `marine_odst_buck_goo` is caught
# by `_buck` and `captain_ingame` by `captain`.
_BETRAYAL_LOYAL = (
    'johnson', 'miranda', 'cortana', 'dervish', 'captain',
    '_buck', '_dare', 'oni_op', '_dutch', '_romeo', '_mickey', 'sgt_hero',
)


def _is_loyal_tag(name):
    return bool(name) and any(w in name.lower() for w in _BETRAYAL_LOYAL)


def _is_human_tag(name):
    if not name:
        return False
    low = name.lower()
    if any(w in low for w in _NONHUMAN_WORDS):
        return False
    return any(w in low.rsplit(chr(92), 1)[-1] for w in _HUMAN_WORDS)


def _apply_betrayal(m, game, registry):
    """Flip every human squad/encounter onto a hostile third faction (see
    _BETRAYAL_TEAM): Flood in Halo 1, Heretic in Halo 2 and 3."""
    scnr_base = _scnr_base(m)
    if scnr_base is None:
        return [{'effect': 'Betrayal', 'ok': False, 'reason': 'scenario tag unavailable'}]

    team = _BETRAYAL_TEAM.get(game)
    if team is None:
        return [{'effect': 'Betrayal', 'ok': False, 'reason': f'not supported in {game}'}]
    team_name = {4: 'Flood', 6: 'Heretic'}.get(team, str(team))

    flipped, skipped = [], 0
    if game == 'Halo 1':
        # H1: allegiance is per encounter, and an encounter's squads name actors
        # from the Actor Palette. Proven in-game on a10.
        pal = m.follow_all(scnr_base, [0x420], [0x10], 'all')
        names = []
        for el in pal:
            ident = struct.unpack_from('<I', m.data, el + 0xC)[0]
            names.append(_tag_name_by_id(m, ident) if ident != 0xFFFFFFFF else None)
        for e in m.follow_all(scnr_base, [0x42C], [0xB0], 'all'):
            kinds = set()
            for sq in m.follow_all(e, [0x80], [0xE8], 'all'):
                ati = struct.unpack_from('<h', m.data, sq + 0x20)[0]
                if 0 <= ati < len(names) and names[ati]:
                    kinds.add(names[ati])
            if not kinds:
                continue
            if all(_is_human_tag(k) for k in kinds) and not any(_is_loyal_tag(k) for k in kinds):
                struct.pack_into('<h', m.data, e + 0x24, team)
                flipped.append(_cstr_at(m, e))
            else:
                skipped += 1
        label = 'encounters'
    else:
        lay = _BETRAYAL.get(game)
        if not lay:
            return [{'effect': 'Betrayal', 'ok': False, 'reason': f'not supported in {game}'}]
        poff, pel = lay['palette']
        names = []
        for el in m.follow_all(scnr_base, [poff], [pel], 'all'):
            ident = struct.unpack_from('<I', m.data, el + lay['pal_id_at'])[0]
            names.append(_tag_name_by_id(m, ident) if ident != 0xFFFFFFFF else None)
        soff, sel = lay['squads']
        for sq in m.follow_all(scnr_base, [soff], [sel], 'all'):
            idxs = []
            if lay.get('cells'):
                idxs = _odst_squad_chars(m, sq, lay)
            elif lay['fireteams']:
                foff, fel = lay['fireteams']
                for ft in m.follow_all(sq, [foff], [fel], 'all'):
                    idxs.append(struct.unpack_from('<h', m.data, ft + lay['char_idx'])[0])
            else:
                idxs.append(struct.unpack_from('<h', m.data, sq + lay['char_idx'])[0])
            kinds = {names[i] for i in idxs if 0 <= i < len(names) and names[i]}
            if not kinds:
                continue
            if all(_is_human_tag(k) for k in kinds) and not any(_is_loyal_tag(k) for k in kinds):
                struct.pack_into('<h', m.data, sq + lay['team'], team)
                flipped.append(_cstr_at(m, sq))
            else:
                skipped += 1
        label = 'squads'
    return [{'effect': 'Betrayal', 'field': f'Squad Team ({label})', 'ok': True,
             'old': 'as the map defines', 'new': f'{len(flipped)} human {label} -> {team_name}',
             'detail': ', '.join(flipped[:12]) + ('…' if len(flipped) > 12 else '')}]


# "Eyepatch": zero every weapon's aim assist. Autoaim is the reticule's stickiness
# and Magnetism the pull that bends your aim onto a target; both exist in all three
# games (H3 additionally has the two Falloff Range fields). Deviation Angle is
# deliberately NOT included -- that's AI projectile scatter, not player aim assist.
_AIM_ASSIST_FIELDS = ('Autoaim Angle', 'Autoaim Range', 'Autoaim Falloff Range',
                      'Magnetism Angle', 'Magnetism Range', 'Magnetism Falloff Range')


_RED_PLASMA_TAG = ('objects' + chr(92) + 'weapons' + chr(92) + 'rifle' + chr(92)
                   + 'plasma_rifle_red' + chr(92) + 'plasma_rifle_red')


# eqip "Flags" is a flags16 at 0x1A6; bit 4 is "Never Dropped By AI". ODST sets it on
# every *_equipment PICKUP tag (11 of 37 on h100) where Halo 3 sets it on none of 27 --
# which is why Brutes drop equipment in Halo 3 and never in ODST, and why the
# "Brute Drop Chance" card has nothing to act on there.
_EQ_FLAGS_FIELD, _EQ_NEVER_DROPPED_BIT = 0x1A6, 4


def apply_equipment_ai_drops(m, game):
    """Clear "Never Dropped By AI" on every eqip tag, so AI can drop equipment again.

    ODST only. The flag is per-TAG, not per-placement, so one pass covers every piece
    the level carries and it composes with Brute Drop Chance, which tunes the relative
    weights the flag was suppressing outright.
    """
    if str(game).strip() != 'Halo 3: ODST':
        return []
    cleared = []
    for t in m.tags:
        if t.get('class') != 'eqip' or not t.get('base'):
            continue
        off = t['base'] + _EQ_FLAGS_FIELD
        fl = struct.unpack_from('<H', m.data, off)[0]
        if not fl & (1 << _EQ_NEVER_DROPPED_BIT):
            continue
        struct.pack_into('<H', m.data, off, fl & ~(1 << _EQ_NEVER_DROPPED_BIT))
        cleared.append(str(t.get('name') or '?').rsplit(chr(92), 1)[-1])
    if not cleared:
        return [{'effect': 'AI equipment drops', 'ok': True, 'skip': True,
                 'reason': 'no equipment had the flag set'}]
    return [{'effect': 'AI equipment drops', 'ok': True, 'tag': 'eqip',
             'field': 'Never Dropped By AI', 'old': 'set on %d piece(s)' % len(cleared),
             'new': 'cleared: ' + ', '.join(sorted(cleared))}]


def apply_red_plasma_as_brute(m, registry, tuning):
    """Retune ODST's red plasma rifle to Halo 2's Brute Plasma Rifle.

    ODST ships the red tag as its ordinary plasma rifle, where Halo 2 shipped the
    same weapon as a separate, stronger Brute Plasma Rifle. The differences are
    only these few fields, so the option reproduces them rather than importing a
    tag: faster fire and tighter dual-wield error.

    Applied from the map's CURRENT values by operator, so it composes with whatever
    plasma rifle effects the run also patched, and the .bak baseline model means it
    does not compound across repatches.
    """
    plugin = registry.get('weap')
    if plugin is None:
        return [{'effect': 'Brute Plasma Rifle', 'ok': False, 'reason': 'no weap plugin'}]
    if not m.find_tags('weap', _RED_PLASMA_TAG):
        return [{'effect': 'Brute Plasma Rifle', 'ok': False,
                 'reason': 'red plasma rifle not in this map'}]
    out = []
    for spec in tuning or []:
        op = {'+': 'add', '-': 'sub', '*': 'mul', '=': 'set'}.get(spec.get('op'), 'add')
        for r in m.apply_field('weap', _RED_PLASMA_TAG, spec['field'], op,
                               float(spec['value']), plugin,
                               block=spec.get('block'), nth=spec.get('nth', 0) or 0):
            r['effect'] = 'Brute Plasma Rifle'
            out.append(r)
    return out


def _apply_eyepatch(m, game, registry):
    """Zero the aim-assist fields on every weap tag in the map."""
    plugin = registry.get('weap')
    if plugin is None:
        return [{'effect': 'Eyepatch', 'ok': False, 'reason': 'no weap plugin'}]
    tags = m.find_tags('weap', '*')
    if not tags:
        return [{'effect': 'Eyepatch', 'ok': False, 'reason': 'no weapons in this map'}]
    zeroed, touched = 0, set()
    for field in _AIM_ASSIST_FIELDS:
        fld = plugin.find(field)
        if not fld or fld['block_chain']:        # not in this game's plugin
            continue
        fmt, _ = hm.TYPE_FMT[fld['type']]
        for name, base in tags:
            try:
                struct.pack_into(fmt, m.data, base + fld['offset'], 0)
            except Exception:
                continue
            zeroed += 1
            touched.add(name)
    if not zeroed:
        return [{'effect': 'Eyepatch', 'ok': False, 'reason': 'no aim-assist fields resolved'}]
    return [{'effect': 'Eyepatch', 'field': 'Aim assist (autoaim + magnetism)', 'ok': True,
             'old': 'as the map defines', 'tag': 'weap *',
             'new': f'zeroed on {len(touched)} weapon(s), {zeroed} field write(s)'}]


# Brute equipment loadout: char 'Equipment Definitions' (H3), elem 0x24 —
# Equipment tagRef @0x0 (ident at +0xC), Flags @0x10, Relative Drop Chance @0x14.
_EQUIP_DEFS = {'Halo 3': {'block': 0x1B0, 'elem': 0x24, 'id_at': 0xC, 'chance': 0x14},
               # ODST moved the block (0x1B0 -> 0x1D4) and kept the element, so the
               # within-element offsets carry over. Its Brutes really do carry the
               # Halo 3 equipment: a Tayari Plaza brute_captain drops a Bubble Shield
               # at chance 1.0 with no patching at all.
               'Halo 3: ODST': {'block': 0x1D4, 'elem': 0x24, 'id_at': 0xC,
                                'chance': 0x14}}
# Only Brutes carry equipment at all, so that's the whole search space.
_EQUIP_CARRIER_TAG = 'objects' + chr(92) + 'characters' + chr(92) + 'brute' + chr(92) + '*'


# scnr equipment placements + palette, per game (mirrors _MAP_WEAPONS). Equipment
# cards are Halo 3 only today, but the other two are laid out the same way.
_MAP_EQUIPMENT = {
    'Halo 1': {'items': (0x258, 0x28), 'palette': (0x264, 0x30), 'pal_id_at': 0xC,
               'palette_index': 0x0},
    'Halo 2': {'items': (0x80, 0x38), 'palette': (0x88, 0x28), 'pal_id_at': 0x4,
               'palette_index': 0x0},
    'Halo 3': {'items': (0xFC, 0x8C), 'palette': (0x108, 0x10), 'pal_id_at': 0xC,
               'palette_index': 0x0},
    # ODST's scenario blocks all shifted; entry sizes are unchanged. Note its levels
    # stock only health packs, ammo and grenades in the equipment palette, so a swap
    # to a Halo 3 piece still reports "not in this level's palette" — correctly.
    'Halo 3: ODST': {'items': (0x118, 0x8C), 'palette': (0x124, 0x10), 'pal_id_at': 0xC,
                     'palette_index': 0x0},
    # Reach: Equipment 0x144 (entry 0xB4), palette 0x150. Verified the same way as the
    # weapons row -- every palette entry resolves to an eqip tag, and the palettes read
    # like the levels do: m30 carries health_pack, active_camouflage, hologram and jet
    # pack, m50 sprint/jet pack/armor lock/drop shield. This is what the armour
    # abilities need in order to be PLACED rather than only tuned.
    'Halo Reach': {'items': (0x144, 0xB4), 'palette': (0x150, 0x10), 'pal_id_at': 0xC,
                   'palette_index': 0x0},
}


def map_equipment_placement_count(m, game):
    """How many equipment placements the level has — the denominator for an
    equipment replacement percentage."""
    lay = _MAP_EQUIPMENT.get(str(game).strip())
    scnr_base = _scnr_base(m)
    if not lay or scnr_base is None:
        return 0
    return max(0, m.i32(scnr_base + lay['items'][0]))


def _append_equipment_palette(m, lay, scnr_base, datums):
    """Append entries to the scenario Equipment Palette; returns {datum: index}.

    Only the palette is relocated — swapping rewrites existing placements' indices,
    so the placement block itself does not grow. Same mechanism
    _apply_spawn_equipment uses: an H3-derived map stores block pointers as
    realVA>>2 resolved through the partition table, so a grown block has to move
    into partition slack rather than being extended in place.

    Needed for ODST, where NO Halo 3 equipment is in any level's palette even
    though every level carries the tags.
    """
    poff, pes = lay['palette']
    pc = max(0, m.i32(scnr_base + poff))
    pbase = _block_base(m, scnr_base + poff)
    if not pbase or not datums:
        return {}
    got = _h3_reserve(m, [(pc + len(datums)) * pes])
    if got is None:
        return None
    pdest = got[0]
    m.data[pdest:pdest + pc * pes] = m.data[pbase:pbase + pc * pes]
    tmpl = m.data[pbase:pbase + pes]                # an eqip tagRef, for the group id
    out = {}
    for j, datum in enumerate(datums):
        off = pdest + (pc + j) * pes
        m.data[off:off + pes] = tmpl
        struct.pack_into('<I', m.data, off + lay['pal_id_at'], datum)
        out[datum] = pc + j
    struct.pack_into('<i', m.data, scnr_base + poff, pc + len(datums))
    struct.pack_into('<I', m.data, scnr_base + poff + 4, m.off2data(pdest))
    return out


def _apply_equipment_swaps(m, game, swaps):
    """Replace a share of the level's EQUIPMENT placements, scattered evenly.
    `swaps` = {eqip-tag: rate 0..1}. Same idea as _apply_weapon_swaps, minus the
    ammo bookkeeping — equipment placements carry no rounds."""
    out = []
    lay = _MAP_EQUIPMENT.get(str(game).strip())
    scnr_base = _scnr_base(m)
    if not lay or scnr_base is None:
        return [{'effect': 'map equipment', 'ok': False, 'reason': 'scnr/layout unavailable'}]
    ioff, ies = lay['items']
    poff, pes = lay['palette']
    N = m.i32(scnr_base + ioff)
    if N <= 0:
        return [{'effect': 'map equipment', 'ok': False,
                 'reason': 'no equipment placements in this level'}]
    ibase = _block_base(m, scnr_base + ioff)
    pbase = _block_base(m, scnr_base + poff)
    pcount = m.i32(scnr_base + poff)
    pal = {i: _tag_name_by_id(m, m.u32(pbase + i * pes + lay['pal_id_at']))
           for i in range(pcount)}

    # Pieces the level never stocks: ODST places NO Halo 3 equipment at all, so
    # without this every ODST swap would report "not in this level's palette" and do
    # nothing — even though the tags are all there and placing one works.
    want = {}
    for tag, rate in (swaps or {}).items():
        if not rate or rate <= 0:
            continue
        _, name = hm.split_tag(tag)
        if any(n == name for n in pal.values()):
            continue
        datum = _h3_tag_datum(m, 'eqip', name)
        if datum is not None:
            want.setdefault(datum, name)
    if want and hasattr(m, 'off2data'):      # H3-derived maps only
        added = _append_equipment_palette(m, lay, scnr_base, list(want))
        if added is None:
            out.append({'effect': 'map equipment', 'ok': False,
                        'reason': 'no free run to grow the equipment palette'})
        else:
            for datum, idx in added.items():
                pal[idx] = want[datum]
                out.append({'effect': 'map equipment',
                            'field': want[datum].rsplit(chr(92), 1)[-1], 'ok': True,
                            'old': 'not in this level', 'new': 'added to the palette'})

    assign = []
    for tag, rate in (swaps or {}).items():
        if not rate or rate <= 0:
            continue
        _, name = hm.split_tag(tag)
        short = name.rsplit(chr(92), 1)[-1]
        pi = next((i for i, n in pal.items() if n == name), None)
        if pi is None:                       # SAFETY NET: still not resolvable
            out.append({'effect': 'map equipment', 'field': short, 'ok': False,
                        'reason': "equipment not in this level's palette"})
            continue
        c = int(round(rate * N))
        if c <= 0:
            out.append({'effect': 'map equipment', 'field': short, 'ok': True,
                        'skip': True,
                        'reason': f'rate too low for {N} placements (rounds to 0)'})
            continue
        assign.append((pi, c, short))

    while sum(a[1] for a in assign) > N and assign:
        j = max(range(len(assign)), key=lambda k: assign[k][1])
        pi, c, s = assign[j]
        assign[j] = (pi, c - 1, s)

    # In Halo 3 a placement only renders where the swapped-in model streams, so confine
    # each piece to placements in a BSP where vanilla already puts it. H1/H2 have no
    # such per-zone streaming, so they spread across every slot as before.
    if str(game).strip() in THIRD_GEN_GAMES:
        slot_masks = [struct.unpack_from('<H', m.data, ibase + i * ies + _EQ_ATTACH)[0]
                      for i in range(N)]
        slots = _spread_slots_bsp(N, slot_masks,
                                  [(a[0], a[1], _h3_stream_mask(m, ioff, ies, a[0])) for a in assign])
    else:
        slots = _spread_slots(N, [(a[0], a[1]) for a in assign])
    # Same rule as the weapon swap: a MARKER is the player's own equipment position
    # and must not be scattered over. Without this the starting-equipment pass and the
    # replacement pass fight, and replacement wins because it runs second.
    for _pi in list(reach_protected_slots(m, game, block='equipment')):
        slots.pop(_pi, None)
    names = {a[0]: a[2] for a in assign}
    done = {}
    for slot, pi in slots.items():
        struct.pack_into('<h', m.data, ibase + slot * ies + lay['palette_index'], pi)
        done[pi] = done.get(pi, 0) + 1
    for pi, n in done.items():
        out.append({'effect': 'map equipment', 'field': names[pi], 'ok': True,
                    'tag': 'scnr', 'old': f'{N} placements',
                    'new': f'{n} swapped in'})
    for pi, c, short in assign:                  # streaming left a piece nowhere to go
        if pi not in done:
            out.append({'effect': 'map equipment', 'field': short, 'ok': True, 'skip': True,
                        'reason': 'no free placement in a BSP where it streams'})
    return out


def equipment_drop_chances(m, game, eq_path):
    """[(brute short name, chance)] for one piece of equipment — the vanilla display
    for a drop-chance row, so the relative weights are visible before editing."""
    lay = _EQUIP_DEFS.get(str(game).strip())
    if not lay:
        return []
    out = []
    for name, base in m.find_tags('char', _EQUIP_CARRIER_TAG):
        for el in m.follow_all(base, [lay['block']], [lay['elem']], 'all'):
            rid = struct.unpack_from('<I', m.data, el + lay['id_at'])[0]
            if rid == 0xFFFFFFFF:
                continue
            nm = _tag_name_by_id(m, rid)
            if isinstance(nm, str) and nm == eq_path:
                out.append((name.rsplit(chr(92), 1)[-1],
                            round(struct.unpack_from('<f', m.data, el + lay['chance'])[0], 3)))
    return out


def _apply_equipment_drop(m, game, eq_path, oper, val):
    """Scale how often Brutes drop one piece of equipment.

    Relative Drop Chance is a WEIGHT within each character's own equipment list, not
    a probability — a Brute picks among its entries in proportion. So raising one
    entry shifts that Brute's odds toward it rather than guaranteeing a drop, and
    entries sitting at 0 stay at 0 under a multiply (they're deliberately disabled).
    """
    lay = _EQUIP_DEFS.get(str(game).strip())
    if not lay:
        return [{'effect': 'equipment drop', 'ok': False,
                 'reason': f'not supported in {game}'}]
    short = eq_path.rsplit(chr(92), 1)[-1]
    tags = m.find_tags('char', _EQUIP_CARRIER_TAG)
    if not tags:
        return [{'effect': 'equipment drop', 'field': short, 'ok': False,
                 'reason': 'no Brutes in this map'}]
    hits, changed = 0, 0
    for name, base in tags:
        for el in m.follow_all(base, [lay['block']], [lay['elem']], 'all'):
            rid = struct.unpack_from('<I', m.data, el + lay['id_at'])[0]
            if rid == 0xFFFFFFFF:
                continue
            nm = _tag_name_by_id(m, rid)
            if not isinstance(nm, str) or nm != eq_path:
                continue
            hits += 1
            old = struct.unpack_from('<f', m.data, el + lay['chance'])[0]
            new = max(0.0, hm.OP_FUNCS[oper](old, val))
            if abs(new - old) > 1e-9:
                struct.pack_into('<f', m.data, el + lay['chance'], new)
                changed += 1
    if not hits:
        return [{'effect': 'equipment drop', 'field': short, 'ok': False,
                 'reason': 'no Brute on this map carries it'}]
    return [{'effect': 'equipment drop', 'field': short, 'ok': True,
             'skip': changed == 0, 'tag': 'char brute*',
             'old': f'{hits} carrier entr{"y" if hits == 1 else "ies"}',
             'new': (f'{changed} changed' if changed
                     else 'all entries were 0 (equipment disabled on those Brutes)')}]


def _cstr_at(m, off, limit=0x20):
    return bytes(m.data[off:off + limit]).split(b'\0')[0].decode('latin1', 'replace')


# scnr weapon-placement + palette layout per game (Weapons list, Weapon Palette).
_MAP_WEAPONS = {
    'Halo 1': {'weapons': (0x270, 0x5C), 'palette': (0x27C, 0x30), 'pal_id_at': 0xC,
               'palette_index': 0x0, 'rounds_left': 0x48, 'rounds_loaded': 0x4A},
    'Halo 2': {'weapons': (0x90, 0x54), 'palette': (0x98, 0x28), 'pal_id_at': 0x4,
               'palette_index': 0x0, 'rounds_left': 0x4C, 'rounds_loaded': 0x4E},
    # Halo 3 was missing entirely, so map weapon swapping silently did nothing there
    # — the placement block just resolved to 0 entries. Palette elements are 16-byte
    # tagRefs (ident at +0xC) like the rest of H3.
    'Halo 3': {'weapons': (0x114, 0xA8), 'palette': (0x120, 0x10), 'pal_id_at': 0xC,
               'palette_index': 0x0, 'rounds_left': 0x6C, 'rounds_loaded': 0x6E},
    # ODST moved the scenario blocks (Weapons 0x114 -> 0x130, palette 0x120 -> 0x13C)
    # while keeping the same entry sizes, so the within-entry offsets carry over.
    'Halo 3: ODST': {'weapons': (0x130, 0xA8), 'palette': (0x13C, 0x10), 'pal_id_at': 0xC,
                     'palette_index': 0x0, 'rounds_left': 0x6C, 'rounds_loaded': 0x6E},
    # Reach grows the placement entry to 0xD0 and moves the rounds fields with it.
    # Read off its scnr plugin and verified on m10/m20/m30/m35/m50/m70: every palette
    # entry resolves to a weap tag and no placement's palette index falls outside the
    # palette. Without this row, map weapon replacement silently did nothing in Reach.
    'Halo Reach': {'weapons': (0x15C, 0xD0), 'palette': (0x168, 0x10), 'pal_id_at': 0xC,
                   'palette_index': 0x0, 'rounds_left': 0x70, 'rounds_loaded': 0x72},
}

# ODST's Auto Magnum / Silenced SMG / red Plasma Rifle and the base weapons they
# stand in for. The bases are in the weapon palette but never placed and never
# carried -- and on the PREPARED maps the plain magnum/smg/plasma_rifle are real,
# resident tags, which is what makes pointing something at them actually work.
_ODST_VARIANT_TAGS = {
    'Auto Magnum': (r'objects\weapons\pistol\automag\automag',
                    r'objects\weapons\pistol\magnum\magnum'),
    # both SMGs live under rifle\, not smg\ -- verified against the shipped maps
    'Silenced SMG': (r'objects\weapons\rifle\smg_silenced\smg_silenced',
                     r'objects\weapons\rifle\smg\smg'),
    # ODST's only obtainable plasma rifle is the red tag (Halo 2's Brute Plasma
    # Rifle). Only downgraded when the run models it as that separate upgrade --
    # otherwise the red tag simply IS the Plasma Rifle and must stay put.
    'Brute Plasma Rifle': (r'objects\weapons\rifle\plasma_rifle_red\plasma_rifle_red',
                           r'objects\weapons\rifle\plasma_rifle\plasma_rifle'),
}

# Where an ODST scenario names a weapon, beyond the placement list:
#   Squads (0x3B8, 0x6C) -> cell blocks (0x54 / 0x60, 0x84 elements) -> the cell's
#   Initial Weapon / Initial Secondary blocks (0x20 / 0x2C), whose 0x10 elements
#   carry an int16 index into the SAME Weapon Palette at +0xC.
# Confirmed by distribution rather than assumed: across h100's 2719 cell entries the
# index histogram is exactly ODST's Covenant loadout mix (plasma pistol, needler,
# carbine, red plasma rifle, spiker, flak cannon) with nothing implausible in it.
_ODST_SQUADS = (0x3B8, 0x6C)
_ODST_CELL_BLOCKS = ((0x54, 0x84), (0x60, 0x84))
_ODST_CELL_WEAPONS = (0x20, 0x2C)
_ODST_CELL_IDX_AT = 0xC


ODST_WEAP_FIRST_PERSON = 0x40C      # block; a player weapon has an fp model here


def odst_player_weapons(m):
    """Every weapon in the map a player can hold, by tag basename.

    The test is structural: a player weapon has a first-person model in its `First
    Person` block, which is exactly what separates the real weapons from turrets and
    vehicle guns. Derived per map because levels differ in what they carry -- a fixed
    list built from one level would silently miss whatever another level is short of.

    Lives here rather than in prepare_map so the preparation tool and the enhancer's
    offer pool cannot drift apart on what "this level supports" means.
    """
    out = set()
    for t in m.tags:
        if t.get('class') != 'weap' or not t.get('name'):
            continue
        base = t['base']
        blk = _block_base(m, base + ODST_WEAP_FIRST_PERSON)
        if not blk or m.i32(base + ODST_WEAP_FIRST_PERSON) <= 0:
            continue
        if m.u32(blk + 0xC) == 0xFFFFFFFF:              # no fp model = not holdable
            continue
        out.add(str(t['name']).rsplit(chr(92), 1)[-1])
    return sorted(out)


def _odst_squad_weapon_slots(m, scnr):
    """File offsets of every int16 weapon-palette index an AI squad cell holds."""
    soff, sel = _ODST_SQUADS
    sn, sbase = m.i32(scnr + soff), _block_base(m, scnr + soff)
    for i in range(max(0, sn)) if sbase else []:
        se = sbase + i * sel
        for coff, cel in _ODST_CELL_BLOCKS:
            cn, cbase = m.i32(se + coff), _block_base(m, se + coff)
            for c in range(max(0, cn)) if cbase else []:
                ce = cbase + c * cel
                for foff in _ODST_CELL_WEAPONS:
                    fn, fbase = m.i32(ce + foff), _block_base(m, ce + foff)
                    for k in range(max(0, fn)) if fbase else []:
                        yield fbase + k * 0x10 + _ODST_CELL_IDX_AT


def apply_odst_downgrade(m, keep=()):
    """Rewrite ODST's upgraded variants to their base weapon, map-wide.

    ODST hands out the upgraded sidearm, SMG and plasma rifle everywhere, which makes
    an upgrade CARD for them meaningless -- the map grants it anyway. With this on the
    map only stocks the base weapon until a player actually drafts the upgrade, so the
    card is what grants it.

    Placements alone are not enough, and that is why this used to be a silent no-op:
    ODST barely places these at all (sc150 places none of the three). They reach the
    player through AI loadouts -- what you pick up off a corpse -- and through the
    starting profiles. All three sites are rewritten here.

    `keep` names the variants a player has drafted; those are left alone entirely.
    """
    lay = _MAP_WEAPONS['Halo 3: ODST']
    scnr = _scnr_base(m)
    if scnr is None:
        return [{'effect': 'ODST base weapons', 'ok': False, 'reason': 'no scenario tag'}]
    poff, pel = lay['palette']
    names, idents = [], []
    for el in m.follow_all(scnr, [poff], [pel], 'all'):
        ident = struct.unpack_from('<I', m.data, el + lay['pal_id_at'])[0]
        names.append(_tag_name_by_id(m, ident) if ident != 0xFFFFFFFF else None)
        idents.append(ident)

    swaps, by_ident = {}, {}
    for label, (variant, base) in _ODST_VARIANT_TAGS.items():
        if label in keep:
            continue
        try:
            vi, bi = names.index(variant), names.index(base)
        except ValueError:
            continue                      # this level stocks neither, nothing to do
        swaps[vi] = (bi, label)
        by_ident[idents[vi]] = (idents[bi], label)
    if not swaps:
        return []

    counts = {}

    def _bump(label, site):
        counts.setdefault(label, {}).setdefault(site, 0)
        counts[label][site] += 1

    def _rewrite_index(off, site):
        idx = struct.unpack_from('<h', m.data, off)[0]
        if idx in swaps:
            bi, label = swaps[idx]
            struct.pack_into('<h', m.data, off, bi)
            _bump(label, site)

    woff, wel = lay['weapons']
    for pl in m.follow_all(scnr, [woff], [wel], 'all'):
        _rewrite_index(pl + lay['palette_index'], 'placed')
    for off in _odst_squad_weapon_slots(m, scnr):
        _rewrite_index(off, 'carried')

    # Starting profiles name the weapon by tagRef, not by palette index. The run's own
    # starting-weapon picks are written before this runs; they can only collide by
    # naming a variant, and a variant the run picked is a variant a player drafted, so
    # `keep` has already excluded it.
    slots = _STARTING_SLOTS['Halo 3: ODST']
    pbase, pcount = _block_base(m, scnr + 0x274), m.i32(scnr + 0x274)
    for i in range(max(0, pcount)) if pbase else []:
        pe = pbase + i * 0x58
        for slot in ('primary', 'secondary'):
            ro = pe + slots[slot]['ref'] + slots['id_at']
            hit = by_ident.get(struct.unpack_from('<I', m.data, ro)[0])
            if hit:
                struct.pack_into('<I', m.data, ro, hit[0])
                _bump(hit[1], 'start')
    if not counts:
        return []
    return [{'effect': 'ODST base weapons', 'ok': True, 'tag': 'scnr',
             'field': 'placements / AI loadouts / starting profiles',
             'old': 'upgraded variant',
             'new': '; '.join('%s -> base (%s)' % (l, ', '.join(
                 '%d %s' % (n, s) for s, n in sorted(sites.items())))
                 for l, sites in sorted(counts.items()))}]


def _tag_name_by_id(m, rid):
    row = rid & 0xFFFF
    if hasattr(m, 'tag'):                                   # H2
        t = m.tag(row)
        return t['name'] if t else None
    b = m.tag_array_off + row * 32                          # H1
    try:
        return m._cstr((m.u32(b + 0x10) - m.magic) & 0xFFFFFFFF)
    except Exception:
        return None


def _block_base(m, off):
    """File offset of a tagblock's element array. Each generation resolves its
    pointer differently: H1 subtracts the map magic, H2 exposes p2o(), and H3 stores
    realVA>>2 which data2off() unpacks."""
    ptr = m.u32(off + 4)
    if hasattr(m, 'data2off'):                       # Halo 3
        return m.data2off(ptr)
    if hasattr(m, 'p2o'):                            # Halo 2
        return m.p2o(ptr)
    return (ptr - m.magic) & 0xFFFFFFFF              # Halo 1


# --- Halo 3 starting equipment -------------------------------------------------
# H3 has no "Starting Equipment" profile field (Reach added one; in H3 that offset is
# the Editor Folder Index). What it can do is PLACE equipment, and an item sitting on
# a Player Starting Location is walked into the instant the level loads. Confirmed
# in-game on 020_base.
#
# A placement only appears if ALL of these hold:
#   Can Attach To BSP Flags @0x50 includes the BSP that loads there,
#   Placement Flags @0x4 has Not Automatically / Never Placed clear,
#   Editor Folder Index @0x42 is -1, or the scenario script's object_destroy_folder
#     calls delete it wherever it is,
#   Position @0x8 is exact — placed equipment never settles under gravity.
_H3_SPAWNS = (0x24C, 0x18)              # Player Starting Locations block
_H3_SPAWN_BSP, _H3_SPAWN_TYPE = 0x14, 0x16
_EQ_PALETTE, _EQ_NAME, _EQ_FLAGS, _EQ_POS = 0x0, 0x2, 0x4, 0x8
_EQ_NODES, _EQ_UID, _EQ_FOLDER, _EQ_ATTACH, _EQ_GAMEFLAGS = 0x24, 0x38, 0x42, 0x50, 0x5C
_PLACE_NOT_AUTO, _PLACE_NEVER = 1 << 0, 1 << 3
# Bit 8, and the same in every third-generation scnr. Without it an object is spawned
# FALLING rather than set down, so it tumbles, sinks into the floor, or ends up out of
# reach -- which reads exactly like a spawn that never happened. Anything this file
# appends should carry it.
_PLACE_AT_REST = 1 << 8

# REACH MOVES THESE, and using Halo 3's offsets on a Reach element is why starting
# equipment placed nothing in game on nine of the ten Reach maps while every result
# row said ok=True. Read off each game's scnr plugin:
#
#            UID   OriginBSP  Type  BSPPolicy  Folder  ZoneFlags  MPFlags  esz
#   Halo 3   0x38  0x3C       0x3E  0x40       0x42    --         --       0x8C
#   ODST     0x38  0x3C       0x3E  0x40       0x42    0x32       0x63     0x8C
#   Reach    0x3C  0x40       0x42  0x33       0x44    0x34       --       0xB4
#
# The fatal one is Folder: Halo 3 keeps Editor Folder Index at 0x42 and Reach keeps
# **Type** there, so writing the -1 that makes a placement immune to
# object_destroy_folder set Reach's object Type to 0xFFFF -- an invalid type the
# engine will not spawn. The UID and zone-mask writes landed on the wrong fields too
# (0x38 is Reach's Light Airprobe Name), and Reach dropped Multiplayer Flags entirely,
# so that write had no legitimate target at all.
#
# Halo 3 and ODST keep the values they have always used: their starting equipment is
# shipped and confirmed in game, so this only adds a Reach row.
_EQ_OFFSETS = {
    # `attach` is Can Attach To BSP Flags -- the same gate Halo 3 keeps at 0x50, which
    # Reach moved to 0x54. Pointing it at Reach's Zone Set Flags (0x34) instead was
    # wrong twice over: the BSP-attach mask was never written, so the appended object
    # kept the TEMPLATE's mask and could not attach to the BSP it was standing in, and
    # a zone mask got written where none was wanted. Zone Set Flags is now its own
    # entry, written 0 = unrestricted.
    'Halo Reach': {'uid': 0x3C, 'folder': 0x44, 'attach': 0x54, 'gameflags': None,
                   'never_bit': 6, 'type': 0x42, 'zone': 0x34},
}
_EQ_DEFAULT_OFFSETS = {'uid': _EQ_UID, 'folder': _EQ_FOLDER, 'attach': _EQ_ATTACH,
                       'gameflags': _EQ_GAMEFLAGS, 'never_bit': 3, 'type': 0x3E,
                       'zone': None}


def _eq_offsets(game):
    return _EQ_OFFSETS.get(str(game).strip(), _EQ_DEFAULT_OFFSETS)


# ODST's Player Starting Locations block moved and grew, and it has NO BSP Index --
# where Halo 3 has one at 0x14, ODST has an Insertion Point Index, matching the
# cell/insertion-point structure its scenario uses throughout. Reading 0x14 as a BSP
# index there would silently produce a nonsense mask, so ODST reports BSP -1 and the
# callers treat that as "no BSP gating known".
_SPAWNS_BY_GAME = {
    # The field at 0x14 is a BSP Index in Halo 3 and an INSERTION POINT INDEX in ODST
    # — same offset, unrelated meaning, which is why ODST's 'bsp' is None. ODST's is
    # read separately by odst_player_starts() below.
    'Halo 3': {'block': (0x24C, 0x18), 'bsp': 0x14},
    'Halo 3: ODST': {'block': (0x280, 0x1C), 'bsp': None, 'insertion': 0x14},
    # Reach follows ODST rather than Halo 3: its Player Starting Locations block
    # (scnr 0x274, entry 0x1C) declares an Insertion Point Index at 0x14, not a BSP
    # Index, so 'bsp' is None here for the same reason it is for ODST -- reading that
    # field as a BSP would build a nonsense visibility mask.
    'Halo Reach': {'block': (0x274, 0x1C), 'bsp': None, 'insertion': 0x14},
}


def h3_player_spawns(m, game='Halo 3'):
    """The level's Player Starting Locations as [(position, bsp_index), ...].

    Deliberately index-based, NOT filtered by Campaign Player Type: every H3 map has
    exactly four, but seven maps label them {chief, dervish, 4, 4} while Tsavo
    Highway, Floodgate and Cortana label all four as type 0. Matching on type would
    silently place nothing for player 2 on those levels. Index 0 is the solo spawn."""
    lay = _SPAWNS_BY_GAME.get(str(game).strip(), _SPAWNS_BY_GAME['Halo 3'])
    boff, esize = lay['block']
    bsp_at = lay['bsp']
    scnr_base = _scnr_base(m)
    if scnr_base is None:
        return []
    base = _block_base(m, scnr_base + boff)
    if not base:
        return []
    out = []
    for i in range(max(0, m.i32(scnr_base + boff))):
        e = base + i * esize
        bsp = (struct.unpack_from('<h', m.data, e + bsp_at)[0]
               if bsp_at is not None else -1)
        out.append((struct.unpack_from('<fff', m.data, e), bsp))
    return out


#: ODST's mission start. Every ODST map — all nine, measured on the shipped .bak
#: baselines — declares exactly FOUR Player Starting Locations at insertion point 0,
#: and they are the four co-op players' starts, in player order, sitting 0.5 to 4
#: units apart. Every other insertion index is a mid-mission revert point: the places
#: the game moves you to as the mission progresses, which is why they outnumber the
#: starts so heavily (Data Hive has 26 of them, ONI Alpha Site 38).
ODST_START_INSERTION = 0


def odst_player_starts(m, game='Halo 3: ODST'):
    """Player Starting Locations grouped by insertion point.

    {insertion index: [(position, bsp_index), ... one per player, in player order]}.

    This is the level's own answer to "where does each player begin", which the
    equipment placer used to have to guess at by clustering every location on the map
    together — a guess that could not tell a start from a checkpoint, and merged the
    four co-op slots of one place into a single point.

    `bsp_index` is always -1: ODST locations carry an insertion index where Halo 3
    carries a BSP index, so callers derive the BSP from the position the same way the
    curated anchors do. Returned as (pos, bsp) pairs anyway, so the result drops
    straight into everything already written against h3_player_spawns.
    """
    lay = _SPAWNS_BY_GAME.get(str(game).strip())
    if not lay or lay.get('insertion') is None:
        return {}
    boff, esize = lay['block']
    iat = lay['insertion']
    scnr_base = _scnr_base(m)
    if scnr_base is None:
        return {}
    base = _block_base(m, scnr_base + boff)
    if not base:
        return {}
    out = {}
    for i in range(max(0, m.i32(scnr_base + boff))):
        e = base + i * esize
        ip = struct.unpack_from('<h', m.data, e + iat)[0]
        out.setdefault(ip, []).append((struct.unpack_from('<fff', m.data, e), -1))
    return out


# scnr script data, shared with sprint_toolkit/h3_script_dump.py: Script Expressions
# 0x4DC (0x18 elements), and the script string blob behind the dataRef at 0x418.
_SCRIPT_EXPRS = (0x4DC, 0x18)
_SCRIPT_STRINGS = 0x418
_CUTSCENE_FLAGS = (0x468, 0x1C)
_TELEPORT_FLAG_RE = re.compile(r'^fl_(\w+?)_teleport_(\d+)$')


def _odst_teleport_points(m):
    """Where the HUB actually puts the player, read from its own scripts.

    Mombasa Streets does not start the player at a Player Starting Location for most of
    its entry points: `h100_reentry_cinematic` TELEPORTS them to cutscene flags named
    `fl_<scene>_teleport_<player>` depending on which mission they came back from. The
    scenario's starting locations only cover the very first entry and the two Firefight
    insertion points, so equipment placed on those left six of the eight level-select
    start points bare.

    Returns one averaged position per scene -- the four per-player flags of a set sit
    within ~3 units of each other, so a single drop reaches any of them.
    """
    scnr = _scnr_base(m)
    if scnr is None:
        return []
    n_expr = max(0, m.i32(scnr + _SCRIPT_EXPRS[0]))
    ebase = _block_base(m, scnr + _SCRIPT_EXPRS[0])
    soff = m.u32(scnr + _SCRIPT_STRINGS + 0xC)
    sbase = m.data2off(soff) if (soff and hasattr(m, 'data2off')) else None
    ssize = max(0, m.i32(scnr + _SCRIPT_STRINGS))
    nf = max(0, m.i32(scnr + _CUTSCENE_FLAGS[0]))
    fbase = _block_base(m, scnr + _CUTSCENE_FLAGS[0])
    if not (ebase and sbase and fbase):
        return []

    def _string_at(off):
        if not (0 <= off < ssize):
            return None
        end = m.data.find(b'\0', sbase + off, sbase + ssize)
        if end < 0:
            return None
        return bytes(m.data[sbase + off:end]).decode('latin1', 'replace')

    by_scene = {}
    for i in range(n_expr):
        e = ebase + i * _SCRIPT_EXPRS[1]
        s = _string_at(struct.unpack_from('<I', m.data, e + 0xC)[0])
        if not s:
            continue
        hit = _TELEPORT_FLAG_RE.match(s)
        if not hit:
            continue
        fi = struct.unpack_from('<I', m.data, e + 0x10)[0] & 0xFFFF
        if 0 <= fi < nf:
            by_scene.setdefault(hit.group(1), {})[fi] = struct.unpack_from(
                '<fff', m.data, fbase + fi * _CUTSCENE_FLAGS[1] + 0x4)
    out = []
    for scene in sorted(by_scene):
        pts = list(by_scene[scene].values())
        out.append((tuple(sum(c) / len(pts) for c in zip(*pts)), -1))
    return out


def _spawn_clusters(spawns, radius=8.0):
    """Distinct player-start PLACES, each keeping the entries that merged into it.

    Returns [(rep_pos, rep_bsp, [(pos, bsp), ...])].

    ODST levels list one starting location per player per insertion point -- Mombasa
    Streets has 21 for 4 real places, Tayari Plaza 22 for 3 -- so equipping "the spawn"
    has to mean equipping each PLACE, not each entry. The radius only has to separate
    insertion points from co-op slots at the same one; the closest distinct pair
    measured is 6.6 units apart.

    The MEMBERS are what makes per-player equipment possible: a place's members are its
    co-op slots (0.5 to 4 units apart on the levels measured), listed in the scenario's
    player order, so player i can be equipped at member i instead of both players
    sharing one drop between them.
    """
    out = []
    for pos, bsp in spawns:
        for i, (p, b, members) in enumerate(out):
            if math.dist(pos, p) < radius:
                if b < 0 <= bsp:
                    out[i] = (p, bsp, members)   # keep whichever entry knows its BSP
                members.append((pos, bsp))
                break
        else:
            out.append((pos, bsp, [(pos, bsp)]))
    return out


def _h3_reserve(m, sizes):
    """Reserve one 16-byte-aligned region per entry in `sizes`, all inside a SINGLE
    partition zero-run, each mapping back to a tag pointer. Returns the list of file
    offsets, or None if no run fits them all.

    H3 stores tagblock pointers as realVA>>2 resolved through the partition table, so
    a block may only live where a partition maps it: appending at EOF is unusable, and
    the partition holding the scenario can't be extended because the tail tables sit
    immediately behind it. Relocating into an existing zero run is the way in. Every
    playable H3 map has 31-62 KB of such slack; only the intro and epilogue cinematics
    have none, and those carry no equipment at all. Placing several grown blocks in one
    run keeps them from clobbering each other."""
    total = 0
    for sz in sizes:
        total = ((total + 15) & ~15) + sz
    for la, psz, fb in m.partitions:
        if fb is None or not psz or fb + psz > len(m.data):
            continue
        for mo in re.finditer(rb'\x00{%d,}' % (total + 16), bytes(m.data[fb:fb + psz])):
            offs, cur, ok = [], fb + mo.start(), True
            for sz in sizes:
                cur = (cur + 15) & ~15
                if cur + sz > fb + mo.end() or m.off2data(cur) is None:
                    ok = False
                    break
                offs.append(cur)
                cur += sz
            if ok:
                return offs
    return None


def _h3_free_run(m, need):
    """Single-region convenience wrapper over _h3_reserve."""
    got = _h3_reserve(m, [need])
    return got[0] if got else None


def _h3_tag_datum(m, cls, path):
    """The tag datum (salt<<16)|row for a class+path present in the map, or None.

    A palette entry references a tag by this datum, so it's what we must write to add
    a piece the level doesn't currently stock — the tag itself is already loaded (the
    equipment models ship in the map), it just isn't in the scenario's palette."""
    io = m.index_header_off
    tbl = m.va2off(m.u64(io + 0x18))                    # tag table: 8 bytes/row
    want = str(path).replace('/', '\\').lower()
    for t in m.tags:
        if t.get('class') == cls and t.get('name') \
                and str(t['name']).replace('/', '\\').lower() == want:
            row = t['index']
            salt = struct.unpack_from('<H', m.data, tbl + row * 8 + 2)[0]
            return ((salt << 16) | (row & 0xFFFF)) & 0xFFFFFFFF
    return None


# Hand-picked drop points (world pos) for maps where the Player Starting Location is
# unusable — a cinematic/vehicle spot, or spawn-protected. Confirmed reachable in-game.
# Maps not listed drop on the player spawn. See the project memory on BSP/streaming.
#
# KEEP THESE. Measured 2026-08-16 against the ODST machinery (_spawn_is_dead +
# _live_equipment_spot), which does NOT supersede them: the live-equipment fallback
# lands 66u from the 020_base anchor and 98u from 120_halo's, where those maps' own
# spawns are 14u and 12u away. The two mechanisms detect different faults — the
# heuristic finds an ISOLATED spawn (Kikowani's sits 240u from anything), while these
# maps' spawns are perfectly populated and merely unreachable while a cinematic or
# vehicle ride owns the player. 100_citadel is the proof: its spawn is 266u from the
# on-foot start yet reads "live", because the Pelican it rides in on has objects
# around it. No positional test can see that; only playing the level can.
#
# 040_voi is NOT a counter-example. _spawn_is_dead flags it, but all four of its
# spawns agree, carry a valid BSP mask, and sit 30u from the nearest crate — open
# ground, not the 240u void the 15u threshold was tuned for. H3 does not run that
# check anyway.
_H3_LOADOUT_ANCHOR = {
    '020_base':    (-25.8, 44.4, -7.2),      # hallway by the armory racks
    '100_citadel': (-254.0, 215.2, -10.5),   # the on-foot start after the Pelican
    '120_halo':    (-269.6, -424.1, -10.0),  # just before the drop to the control centre
    # REACH. Its starting locations are the least trustworthy of any game -- six of ten
    # are isolated, because most missions begin in a cinematic or a vehicle and the
    # player is put down somewhere the scenario never records.
    #
    # m20: the supply cluster the player described, found by its Target Locator, which
    # is the one landmark here that is unique in the file. Everything they listed is
    # within 1.2 units of it and all of it is AUTO -- so this is demonstrably a spot
    # the engine spawns pickups at and the player reaches:
    #
    #   target_laser  (-57.3, 34.7, 13.1)   attach 0x10  auto   "a target locator"
    #   dmr           (-57.4, 35.9, 13.1)   attach 0x10  auto   "2 dmr"
    #   dmr           (-57.5, 35.8, 13.1)   attach 0x10  auto
    #   equipment_case (-58.1, 33.1, 12.8)  attach 0x10  auto   the "crates" -- scenery
    #   equipment_case (-57.3, 34.6, 12.9)  attach 0x10  auto   cases the guns sit in
    #   equipment_case (-57.4, 35.8, 12.9)  attach 0x10  auto
    #
    # The third case holds nothing in vanilla, which is where the two armor locks the
    # player sees must come from -- no armor_lockup placement exists in ANY class on
    # this map, so they are script-spawned. The player was right that they are not ours.
    # This is ~106 units from the declared starting location, which is the measure of
    # how little that location is worth on Reach.
    'm20':         (-56.8, 34.3, 13.1),
}

# (map -> equipment basenames) that do NOT stream at that map's start — their model
# resources are only loaded in a later zone, so a placement at the start renders
# nothing (baked in the PVS, unfixable). Such a piece is dropped instead on the nearest
# weapon in a BSP where it DOES stream. Confirmed in-game 2026-07-23.
_H3_NO_START_STREAM = {
    '040_voi':     frozenset({'gravlift_equipment'}),
    '070_waste':   frozenset({'autoturret_equipment'}),
    '100_citadel': frozenset({'autoturret_equipment'}),
}


# Every object placement carries the same Can Attach To BSP Flags at 0x50 and the
# same position at 0x8, so any of them can say which BSP is live somewhere. Weapons
# alone are far too sparse: at Uplift Reserve's start the nearest is 241 units away
# and in a different BSP, and at Kikowani Station 225 — which is why equipment
# patched cleanly there and then never appeared. Scenery and crates sit within 9-39
# units on both, and on every level that already worked the nearest placement of any
# type agrees with the weapon-derived answer.
_PLACEMENT_BLOCKS = {
    'Halo 3': {'scenery': (0xB4, 0xB4), 'bipeds': (0xCC, 0x74),
               'vehicles': (0xE4, 0xA8), 'equipment': (0xFC, 0x8C),
               'weapons': (0x114, 0xA8), 'crates': (0x5BC, 0xB0)},
    'Halo 3: ODST': {'scenery': (0xD0, 0xB4), 'bipeds': (0xE8, 0x74),
                     'vehicles': (0x100, 0xA8), 'equipment': (0x118, 0x8C),
                     'weapons': (0x130, 0xA8), 'crates': (0x5FC, 0xB0)},
    # Reach was missing entirely, so _nearest_placement_mask returned None for it and
    # the dead-spawn detector could not run on a Reach map at all. Read off
    # ReachMCC/scnr.xml; the element sizes all grew, which is why every offset moved.
    'Halo Reach': {'scenery': (0xFC, 0xDC), 'bipeds': (0x114, 0x78),
                   'vehicles': (0x12C, 0xD0), 'equipment': (0x144, 0xB4),
                   'weapons': (0x15C, 0xD0), 'crates': (0x600, 0xD8)},
}
_PLACE_POS, _PLACE_ATTACH = 0x8, 0x50


def _nearest_placement_mask(m, pos, game):
    """Attach mask of the nearest placement of ANY type, or None."""
    blocks = _PLACEMENT_BLOCKS.get(str(game).strip())
    scnr = _scnr_base(m)
    if not blocks or scnr is None:
        return None
    best = None
    for off, esize in blocks.values():
        n = m.i32(scnr + off)
        base = _block_base(m, scnr + off)
        if not base or n <= 0:
            continue
        att_at = _eq_offsets(game)['attach']
        for i in range(n):
            e = base + i * esize
            att = struct.unpack_from('<H', m.data, e + att_at)[0]
            if not att:
                continue
            p = struct.unpack_from('<fff', m.data, e + _PLACE_POS)
            d = sum((a - b) ** 2 for a, b in zip(p, pos))
            if best is None or d < best[0]:
                best = (d, att)
    return best[1] if best else None


# A Player Starting Location the game never uses sits in empty space. Measured across
# all 19 H3 and ODST levels, spawn 0 is 0.2-9.9 units from the nearest placement on
# seventeen of them and then jumps to 28.6 (Kikowani Station) and 30.0 (040_voi) -- a
# real gap, not a threshold fitted to one map. Kikowani is the confirmed case: a live
# scan put the player ~240 units from its spawn, among crates and decals, while the
# spawn itself has nothing near it but the other three spawns. So isolation finds a
# dead spawn without hand-picking an anchor per map, which is what Halo 3 needs today.
_DEAD_SPAWN_UNITS = 15.0


def _spawn_is_dead(m, pos, game):
    """True if nothing in the level sits near this spawn, so the game cannot be
    starting the player there."""
    blocks = _PLACEMENT_BLOCKS.get(str(game).strip())
    scnr = _scnr_base(m)
    if not blocks or scnr is None:
        return False
    limit = _DEAD_SPAWN_UNITS ** 2
    for off, esize in blocks.values():
        n, base = m.i32(scnr + off), _block_base(m, scnr + off)
        if not base or n <= 0:
            continue
        for i in range(n):
            p = struct.unpack_from('<fff', m.data, base + i * esize + _PLACE_POS)
            if any(v != v for v in p):
                continue
            if sum((a - b) ** 2 for a, b in zip(p, pos)) <= limit:
                return False
    return True


def _live_equipment_spot(m, game, near=None):
    """Position and mask of an equipment placement that actually renders.

    Used when the spawn is dead: a pickup spot the level itself uses is somewhere
    the player demonstrably goes. A zero attach mask means the placement never
    renders, so those are skipped -- on Kikowani that is exactly what separates the
    two far-flung placements from the four beside the real start.

    `near` picks the CLOSEST such spot to a point instead of the first in the block.
    Taking the first is arbitrary, and on Reach arbitrary is a long way: it put the
    drop 128 units from m20's starting location when a valid spot sat at 71, and 537
    units away on m52. The starting location may not be exactly where the player is
    put down, but it is the level's own declaration of where the mission begins, so
    it is a far better anchor than block order."""
    lay = _MAP_EQUIPMENT.get(str(game).strip())
    scnr = _scnr_base(m)
    if not lay or scnr is None:
        return None
    off, esize = lay['items']
    n, base = m.i32(scnr + off), _block_base(m, scnr + off)
    att_at = _eq_offsets(game)['attach']
    best = None
    for i in range(max(0, n)):
        e = base + i * esize
        att = struct.unpack_from('<H', m.data, e + att_at)[0]
        if not att:
            continue
        p = struct.unpack_from('<fff', m.data, e + _EQ_POS)
        if any(v != v for v in p):          # NaN guard, as in _spawn_is_dead
            continue
        if near is None:
            return p, att
        d = sum((a - b) ** 2 for a, b in zip(p, near))
        if best is None or d < best[0]:
            best = (d, p, att)
    return (best[1], best[2]) if best else None


def _h3_mask_at(m, pos, game='Halo 3'):
    """Attach mask of the nearest vanilla placement to `pos` — approximates which BSP
    is loaded there, so a placement dropped at pos attaches to the right BSP.

    ODST looks at every placement type; Halo 3 keeps its weapons-only behaviour, whose
    curated start anchors were tuned in-game against exactly that answer. Widening it
    there would change masks on maps that already work, with no evidence of a problem
    to fix — the ODST tables are present so it can be switched over if that changes.
    """
    # Reach joins ODST here. Scanning EVERY placement class beats scanning weapons
    # alone, and Reach needs it more than either: its starting locations sit far from
    # any gun (70.8 units on m20, 140.7 on m45), so a weapons-only scan picks whatever
    # happens to be nearest across the level and can return a BSP the drop point is
    # not in -- and a wrong Can Attach To BSP Flags means the object silently never
    # spawns. Halo 3 is left on the weapons scan deliberately: its equipment is
    # shipped and confirmed in game, and its spawns are not isolated (only 040 is).
    if str(game).strip() in ('Halo 3: ODST', 'Halo Reach'):
        got = _nearest_placement_mask(m, pos, game)
        if got:
            return got
    lay = _MAP_WEAPONS.get(str(game).strip(), _MAP_WEAPONS['Halo 3'])
    wo, we = lay['weapons']
    scnr = _scnr_base(m)
    wN, wb = max(0, m.i32(scnr + wo)), _block_base(m, scnr + wo)
    best, bestd = 1, None
    # Reach moved Can Attach To BSP Flags from 0x50 to 0x54, and the object placement
    # blocks share the field layout within a game, so the equipment offset serves the
    # weapons block too. Reading 0x50 on a Reach element returned a Connection Marker
    # stringid as if it were a BSP mask.
    att_at = _eq_offsets(game)['attach']
    for i in range(wN) if wb else []:
        e = wb + i * we
        att = struct.unpack_from('<H', m.data, e + att_at)[0]
        if not att:
            continue
        wp = struct.unpack_from('<fff', m.data, e + _EQ_POS)
        dd = sum((a - b) ** 2 for a, b in zip(wp, pos))
        if bestd is None or dd < bestd:
            bestd, best = dd, att
    return best


def _h3_stream_mask(m, block_off, elem, pal_idx):
    """BSP mask where a palette entry is known to stream — the union of attach masks of
    every vanilla placement in the block at `block_off` (equipment or weapon) using it.
    A placement only renders where the model streams, i.e. where vanilla puts it."""
    scnr = _scnr_base(m)
    N, base = max(0, m.i32(scnr + block_off)), _block_base(m, scnr + block_off)
    mask = 0
    for i in range(N) if base else []:
        e = base + i * elem
        if struct.unpack_from('<h', m.data, e)[0] == pal_idx:   # palette index @0x0
            mask |= struct.unpack_from('<H', m.data, e + _EQ_ATTACH)[0]
    return mask


def _spread_slots_bsp(N, slot_masks, assign):
    """Like _spread_slots, but each key is confined to placements whose BSP mask
    (slot_masks[i]) overlaps the key's own stream mask, so a swapped-in piece only lands
    where its model streams. `assign` = [(key, count, stream_mask)]. Returns {slot: key}.
    A piece whose stream BSPs have too few free slots simply gets fewer than requested."""
    # Serve the most BSP-constrained pieces FIRST: one with few eligible slots must claim
    # them before a broad piece (which has alternatives) eats them, so each piece keeps
    # its fair share whenever the slots exist. Without this, a broad piece processed
    # first can starve a narrow one even when a fair split was possible.
    def eligible(smask):
        return N if not smask else sum(1 for mm in slot_masks if mm & smask)
    order = sorted(range(len(assign)), key=lambda j: eligible(assign[j][2]))

    taken = {}
    for j in order:
        key, c, smask = assign[j]
        if c <= 0:
            continue
        # smask == 0 means the piece has no vanilla placements to learn its streaming
        # from (e.g. an enemy-carried-only weapon) — don't restrict it, since it may
        # well stream via enemy loadouts we can't see. Otherwise confine to its BSPs.
        valid = [i for i in range(N)
                 if i not in taken and (not smask or (slot_masks[i] & smask))]
        if not valid:
            continue
        c = min(c, len(valid))
        for k in range(c):                       # evenly spaced, distinct for c<=len
            taken[valid[min(len(valid) - 1, int((k + 0.5) * len(valid) / c))]] = key
    return taken


def _h3_fallback_weapon(m, from_pos, equip_mask, used):
    """Nearest vanilla weapon placement (index not in `used`) whose attach mask overlaps
    equip_mask — i.e. a designer-placed floor spot in the first BSP zone where a piece
    that can't stream at the start DOES stream. Returns (index, pos, mask) or None."""
    lay = _MAP_WEAPONS['Halo 3']
    wo, we = lay['weapons']
    scnr = _scnr_base(m)
    wN, wb = max(0, m.i32(scnr + wo)), _block_base(m, scnr + wo)
    cands = []
    for i in range(wN) if wb else []:
        if i in used:
            continue
        e = wb + i * we
        att = struct.unpack_from('<H', m.data, e + _EQ_ATTACH)[0]
        if att & equip_mask:
            wp = struct.unpack_from('<fff', m.data, e + _EQ_POS)
            cands.append((sum((a - b) ** 2 for a, b in zip(wp, from_pos)), i, wp, att & equip_mask))
    if not cands:
        return None
    cands.sort(key=lambda c: c[0])
    _, i, wp, mask = cands[0]
    return i, wp, mask


_AUTOTURRET_EQUIP = r'objects\equipment\autoturret_equipment\autoturret_equipment'
_AUTOTURRET_UNIT = r'objects\equipment\autoturret\autoturret'


def _run_grants_autoturret(spawn_equipment, equipment_swaps):
    """Does this run put an Auto Turret into the level, by either route?"""
    for g in ((spawn_equipment or {}).get('groups') or []):
        for t in (g or []):
            if _AUTOTURRET_EQUIP in str(t).lower():
                return True
    for tag, rate in (equipment_swaps or {}).items():
        if rate and rate > 0 and _AUTOTURRET_EQUIP in str(tag).lower():
            return True
    return False


def _fix_autoturret_team(m, game, registry):
    r"""Make the deployed Auto Turret read as YOURS instead of as a Guardian.

    The piece you throw is only a spawner: the `eqip` spawns
    `vehi objects\equipment\autoturret\autoturret`, and that vehicle in turn spawns the
    CHARACTER that drives it. The character is what decides allegiance, so the field
    that matters is `char objects\equipment\autoturret\autoturret` ->
    General Properties -> **Type**, which ships as `Guardian` (0x18) and wants to be
    `Marine` (0x7). Confirmed 0x18 on all eleven maps that carry the turret.

    The vehicle's own `Default Team` is set to Human alongside it, but ONLY as the
    secondary: it ships as `Sentinel` (5) and looks like the answer, and it is not --
    changing it by itself was tested in game and did nothing, because the turret's
    behaviour comes from its driver. Left in because it costs one write and makes the
    two tags agree; if this ever needs trimming, the char Type is the one to keep.

    One write per map covers every turret on it, thrown or map-placed, since they all
    come from the one tag. Idempotent, and undone by re-patching from the pristine .bak
    like everything else.
    """
    out = []

    def _one(cls, path, field, plugin, option, block=None):
        base = {'effect': 'Auto Turret', 'tag': cls + ' ' + path, 'field': field}
        if plugin is None:
            return {**base, 'ok': False, 'reason': 'no %s plugin' % cls}
        fld = plugin.find(field, block)
        want = (fld or {}).get('options', {}).get(option)
        if want is None:
            return {**base, 'ok': False,
                    'reason': '%s plugin has no %s/%s' % (cls, field, option)}
        # write_tag_field, not write(): the third-generation map classes expose the
        # base-offset form on every game, while `write` is Halo 1 only.
        olds = [m.write_tag_field(t[1] if isinstance(t, tuple) else t,
                                  field, want, plugin, block=block)
                for t in m.find_tags(cls, path)]
        olds = [o for o in olds if o is not None]
        if not olds:
            return {**base, 'ok': False, 'reason': '%s did not resolve' % field}
        return {**base, 'ok': True, 'skip': all(o == want for o in olds),
                'old': olds[0], 'new': want}

    # Whenever the run puts a turret in, this runs -- the ONLY thing that stops it is
    # the level not carrying the tags. That is a reported skip, not silence, so the
    # summary accounts for the option either way.
    if not m.find_tags('char', _AUTOTURRET_UNIT):
        return [{'effect': 'Auto Turret', 'tag': 'char ' + _AUTOTURRET_UNIT,
                 'field': 'Type', 'ok': True, 'skip': True,
                 'reason': 'the Auto Turret is not in this level'}]
    out.append(_one('char', _AUTOTURRET_UNIT, 'Type', registry.get('char'),
                    'marine', block='General Properties'))
    if m.find_tags('vehi', _AUTOTURRET_UNIT):
        out.append(_one('vehi', _AUTOTURRET_UNIT, 'Default Team', registry.get('vehi'),
                        'human'))
    return out


def _no_equipment_reason(game):
    """Why a piece could not be placed, and in Reach what to do about it.

    Reach earns the longer message: an ability the vanilla cache does not already use
    cannot be made to spawn by patching at all -- the map has to be rebuilt in the
    editing kit with that ability placed, which imports its resources. Reporting a bare
    "not present in this level" there sends the reader looking for a bug in the patcher,
    which is where several sessions went.
    """
    if str(game).strip() == 'Halo Reach':
        return ('not in this level -- Reach needs the map REBUILT in the editing kit '
                'with this ability placed (weapon_availability.py --equipment says '
                'which maps are ready)')
    return 'equipment not present in this level'


#: Object Names block per game: (scnr offset, element size, name kind). Reach stores
#: the name as a stringID; Halo 3 and ODST as a 32-byte ASCII string.
_OBJECT_NAMES = {
    'Halo 3':       (0xA8, 0x24, 'ascii'),
    'Halo 3: ODST': (0xC4, 0x24, 'ascii'),
    'Halo Reach':   (0xF0, 0x08, 'sid'),
}
#: What the user names a marker in Sapien. `enhancer_marker1` is player 1's position,
#: `enhancer_marker2` player 2's.
REACH_MARKER_PREFIX = 'enhancer_marker'


def _reach_named_placements(m, game, block):
    """[(placement index, Object Names index)] for placements that HAVE a name."""
    lay = (_MAP_WEAPONS if block == 'weapons' else _MAP_EQUIPMENT).get(
        str(game).strip())
    scnr = _scnr_base(m)
    if not lay or scnr is None:
        return []
    ioff, ies = lay['weapons' if block == 'weapons' else 'items']
    n = max(0, m.i32(scnr + ioff))
    base = _block_base(m, scnr + ioff)
    out = []
    for i in range(n) if base else []:
        ni = struct.unpack_from('<h', m.data, base + i * ies + 0x2)[0]
        if ni >= 0:
            out.append((i, ni))
    return out


def _reach_name_delta(m, game, wanted):
    """Offset from an Object Names stringID index to the real string-table index.

    Calibrated per map, never hardcoded. Scored only over placements that are NAMED
    AND inert: a marker is by definition a placement the designer named and left
    flagged Not Automatically, and that pair of conditions is what makes exactly one
    offset fit. Scoring more loosely ties, because the sids and the table indices are
    both sequential -- every offset then lines up the same number of pairs and the
    winner is arbitrary.
    """
    cache = getattr(m, '_reach_delta', None)
    if cache is not None:
        return cache
    spec = _OBJECT_NAMES[str(game).strip()]
    off, esize, _kind = spec
    scnr = _scnr_base(m)
    obase = _block_base(m, scnr + off)
    ocount = max(0, m.i32(scnr + off))
    never = 1 << _eq_offsets(game)['never_bit']
    pairs = []
    for block in ('equipment', 'weapons'):
        lay = (_MAP_WEAPONS if block == 'weapons' else _MAP_EQUIPMENT).get(
            str(game).strip())
        if not lay:
            continue
        ioff, ies = lay['weapons' if block == 'weapons' else 'items']
        ibase = _block_base(m, scnr + ioff)
        for pi, ni in _reach_named_placements(m, game, block):
            if not (0 <= ni < ocount) or not ibase:
                continue
            fl = struct.unpack_from('<I', m.data, ibase + pi * ies + _EQ_FLAGS)[0]
            if not (fl & (_PLACE_NOT_AUTO | never)):
                continue                       # a marker is inert; this one is live
            sid = struct.unpack_from('<I', m.data, obase + ni * esize)[0] & 0xFFFF
            pairs.append((block, ni, sid))
    # Two offsets can explain the same number of markers, and then picking whichever
    # was scanned first is a coin toss that has already landed wrong: on m52 the true
    # offset 4747 names equipment 29 and 30 -- the ability pair the designer marked --
    # while 4870 names an unrelated rocket launcher and its ammo crate 540 units away,
    # and the launcher scans first. So a tie is broken on shape instead of order.
    # Markers are placed as a set: they live in ONE placement block and their Object
    # Names entries sit together. A coincidence rarely does both.
    best, best_key = None, None
    for _blk, _ni, sid in pairs:
        for ti in wanted:
            d = ti - sid
            hit = [(b2, n2) for (b2, n2, s2) in pairs if (s2 + d) in wanted]
            if not hit:
                continue
            targets = {s2 + d for (_b2, _n2, s2) in pairs if (s2 + d) in wanted}
            entries = [n2 for (_b2, n2) in hit]
            key = (len(targets), -len({b2 for (b2, _n2) in hit}),
                   -(max(entries) - min(entries)))
            if best_key is None or key > best_key:
                best, best_key = d, key
    m._reach_delta = best if (best_key and best_key[0]) else None
    return m._reach_delta


def reach_named_markers(m, game, prefix=REACH_MARKER_PREFIX, block='equipment'):
    """{name: placement index} for placements the LEVEL DESIGNER named.

    A named placement says which PLAYER a position belongs to, so the patcher sets that
    position's palette entry to whatever that player picked rather than guessing a spot
    or relying on block order. `enhancer_marker1` is player 1, `enhancer_marker2`
    player 2.

    Resolved from the PLACEMENT side -- placement Name index -> Object Names entry --
    and never from the entry's own Placement Index. On m10 those disagree: the entries
    naming the two equipment markers report `type=Weapon, placement=20/21`, which if
    believed sends the lookup to two vanilla rifles on the far side of the level. The
    placement's own Name index is the authoritative link.

    `block` picks which placement block to read; the same Object Names block and Name
    field serve equipment and weapons alike, so weapon markers need no new mechanism.
    """
    spec = _OBJECT_NAMES.get(str(game).strip())
    scnr = _scnr_base(m)
    if not spec or scnr is None:
        return {}
    off, esize, kind = spec
    ocount = max(0, m.i32(scnr + off))
    obase = _block_base(m, scnr + off)
    if not obase or not ocount:
        return {}
    named = _reach_named_placements(m, game, block)
    if not named:
        return {}
    if kind == 'ascii':
        # Halo 3 / ODST store the name inline, so no calibration is needed.
        out = {}
        for pi, ni in named:
            if not (0 <= ni < ocount):
                continue
            e = obase + ni * esize
            nm = bytes(m.data[e:e + 0x20]).split(bytes([0]))[0].decode(
                'latin1', 'replace')
            if nm.startswith(prefix):
                out[nm] = pi
        return out
    if not (hasattr(m, '_locate_stringids') and m._locate_stringids()):
        return {}
    wanted = {}
    for i in range(getattr(m, 'str_tbl_count', 0)):
        s = m._string_at(i)
        if s and s.startswith(prefix):
            wanted[i] = s
    if not wanted:
        return {}
    delta = _reach_name_delta(m, game, wanted)
    if delta is None:
        return {}
    out = {}
    for pi, ni in named:
        if not (0 <= ni < ocount):
            continue
        sid = struct.unpack_from('<I', m.data, obase + ni * esize)[0] & 0xFFFF
        nm = wanted.get(sid + delta)
        if nm:
            out[nm] = pi
    return out


def reach_equipment_markers(m, game):
    """{eqip basename: [placement index, ...]} for every INERT equipment placement.

    The UNNAMED fallback. A named marker says which player a position belongs to and
    is preferred; this catches a prepared map whose markers were never named, where
    block order is all there is to go on -- the first inert placement of a piece is
    player 1's, the second player 2's.
    """
    lay = _MAP_EQUIPMENT.get(str(game).strip())
    scnr = _scnr_base(m)
    if not lay or scnr is None:
        return {}
    eqo = _eq_offsets(game)
    ioff, ies = lay['items']
    poff, pes = lay['palette']
    base = _block_base(m, scnr + ioff)
    pbase = _block_base(m, scnr + poff)
    if not base or not pbase:
        return {}
    names = {}
    for i in range(max(0, m.i32(scnr + poff))):
        nm = _tag_name_by_id(m, m.u32(pbase + i * pes + lay['pal_id_at']))
        if nm:
            names[i] = str(nm).replace('/', chr(92)).lower()
    out = {}
    for i in range(max(0, m.i32(scnr + ioff))):
        e = base + i * ies
        nm = names.get(struct.unpack_from('<h', m.data, e)[0])
        if not nm:
            continue
        fl = struct.unpack_from('<I', m.data, e + _EQ_FLAGS)[0]
        if fl & (_PLACE_NOT_AUTO | (1 << eqo['never_bit'])):
            out.setdefault(nm, []).append(i)
    return out


def reach_map_items(m, game, kind='weapons'):
    """Basenames of what this Reach map can actually give the player.

    The rule differs by kind because the evidence does:

      weapons    everything in the weapon PALETTE. Map replacement can repoint any
                 placement at any palette entry, and a palette entry means the level
                 ships that weapon's resources.
      equipment  only what the map PLACES -- automatically, or as an inert marker.
                 Palette membership is NOT enough here: m10 ships drop_shield in its
                 vanilla palette and it still would not spawn from a patched-in
                 placement, because the cache lacks its resources. Anything with a
                 real placement has demonstrably got them.
    """
    lay = (_MAP_WEAPONS if kind == 'weapons' else _MAP_EQUIPMENT).get(str(game).strip())
    scnr = _scnr_base(m)
    if not lay or scnr is None:
        return set()
    poff, pes = lay['palette']
    pbase = _block_base(m, scnr + poff)
    pcount = max(0, m.i32(scnr + poff))
    names = {}
    for i in range(pcount) if pbase else []:
        nm = _tag_name_by_id(m, m.u32(pbase + i * pes + lay['pal_id_at']))
        if nm:
            names[i] = str(nm).rsplit(chr(92), 1)[-1]
    if kind == 'weapons':
        return set(names.values())
    ioff, ies = lay['items']
    ibase = _block_base(m, scnr + ioff)
    out = set()
    for i in range(max(0, m.i32(scnr + ioff))) if ibase else []:
        nm = names.get(struct.unpack_from('<h', m.data, ibase + i * ies)[0])
        if nm:
            out.add(nm)
    return out


def reach_protected_slots(m, game, block='equipment'):
    """Placement indices a swap must LEAVE ALONE.

    A named marker is the player's own loadout position: the patcher puts the ability
    (later the weapon) they picked on it. Map replacement scatters picks over existing
    placements, so without this it would happily overwrite the very placement the
    starting-equipment pass just set, and the player would arrive to find something
    else there. Only Reach has markers, so this is empty everywhere else.
    """
    if str(game).strip() != 'Halo Reach':
        return set()
    named = reach_named_markers(m, game, block=block)
    return set(named.values())


def _reach_set_marker(m, game, index, tag_path):
    """Point a named marker at `tag_path` and switch it on. Grows the palette if the
    map does not already stock that piece."""
    lay = _MAP_EQUIPMENT[str(game).strip()]
    scnr = _scnr_base(m)
    ioff, ies = lay['items']
    poff, pes = lay['palette']
    label = str(tag_path).rsplit(chr(92), 1)[-1]
    pbase = _block_base(m, scnr + poff)
    pc = max(0, m.i32(scnr + poff))
    want = str(tag_path).replace('/', chr(92)).lower()
    pi = None
    for i in range(pc):
        nm = _tag_name_by_id(m, m.u32(pbase + i * pes + lay['pal_id_at']))
        if nm and str(nm).replace('/', chr(92)).lower() == want:
            pi = i
            break
    if pi is None:
        datum = _h3_tag_datum(m, 'eqip', tag_path)
        if datum is None:
            return {'effect': 'starting equipment', 'field': label, 'ok': True,
                    'skip': True, 'reason': _no_equipment_reason(game)}
        added = _append_equipment_palette(m, lay, scnr, [datum])
        if not added:
            return {'effect': 'starting equipment', 'field': label, 'ok': False,
                    'reason': 'could not grow the equipment palette'}
        pi = added[datum]
        # the palette moved; re-read the placement base before writing into it
        scnr = _scnr_base(m)
    e = _block_base(m, scnr + ioff) + index * ies
    struct.pack_into('<h', m.data, e, pi)
    pos = reach_enable_marker(m, game, index)
    return {'effect': 'starting equipment', 'field': label, 'ok': True,
            'old': 'marker', 'new': 'on marker %d at (%.0f, %.0f, %.0f)'
                                    % (index, pos[0], pos[1], pos[2])}


def reach_enable_marker(m, game, index):
    """Clear Not Automatically / Never Placed on one placement, so it spawns."""
    lay = _MAP_EQUIPMENT[str(game).strip()]
    eqo = _eq_offsets(game)
    ioff, ies = lay['items']
    e = _block_base(m, _scnr_base(m) + ioff) + index * ies
    fl = struct.unpack_from('<I', m.data, e + _EQ_FLAGS)[0]
    struct.pack_into('<I', m.data, e + _EQ_FLAGS,
                     fl & ~(_PLACE_NOT_AUTO | (1 << eqo['never_bit'])))
    return struct.unpack_from('<fff', m.data, e + _EQ_POS)


def reach_spawn_ready(m, game):
    """Can this map actually take placed weapons? True only if it carries markers."""
    return str(game).strip() == 'Halo Reach' and bool(reach_named_markers(m, game))


def _apply_spawn_weapons(m, game, spec):
    """Reach: hand a player their weapons by PLACING them at the marker.

    The alternative to writing the Starting Profile. A profile weapon is in the
    player's hands on the first frame; a placed one lies at their feet and is picked
    up, which is the point -- the level's own opening loadout survives, and a run can
    hand over several weapons at once without inventing profile slots for them.

    `spec` = {'groups': [[weap tag path, ...], ...]}: group i belongs to player i+1 and
    goes to `enhancer_marker<i+1>`. Every tag in a group is placed, so the caller
    decides whether a group holds one weapon or all of them.

    Placements are APPENDED at the marker's coordinates rather than repointing
    anything. The marker itself is an equipment placement -- it is what the abilities
    use -- and the inert weapon placements around it are the designer's, so taking one
    over would silently delete a pickup the level meant to offer. Appending was also
    the arrangement proven in game: thirteen weapons at one marker's coordinates, all
    thirteen present.

    Weapons stack, each a little above the last. They are placed Create At Rest, so
    they stay where they are put instead of dropping through the floor.
    """
    out = []
    if str(game).strip() != 'Halo Reach':
        return out
    lay = _MAP_WEAPONS.get('Halo Reach')
    scnr = _scnr_base(m)
    groups = [[t for t in (g or []) if t] for g in (spec.get('groups') or [])]
    if not lay or scnr is None or not any(groups):
        return out

    named = reach_named_markers(m, game)
    if not named:
        return [{'effect': 'spawned weapons', 'ok': False,
                 'reason': 'this map carries no enhancer markers'}]
    E = _MAP_EQUIPMENT['Halo Reach']
    eoff, ees = E['items']
    ebase = _block_base(m, scnr + eoff)
    anchors = {}
    for nm, idx in named.items():
        e = ebase + idx * ees
        anchors[nm] = (struct.unpack_from('<fff', m.data, e + _EQ_POS),
                       struct.unpack_from('<H', m.data, e + 0x54)[0])

    woff, wes = lay['weapons']
    poff, pes = lay['palette']
    N = max(0, m.i32(scnr + woff))
    base = _block_base(m, scnr + woff)
    pbase = _block_base(m, scnr + poff)
    if not N or not base or not pbase:
        return [{'effect': 'spawned weapons', 'ok': False,
                 'reason': 'level has no weapon placements to extend'}]
    pal = {}
    for i in range(max(0, m.i32(scnr + poff))):
        nm = _tag_name_by_id(m, m.u32(pbase + i * pes + lay['pal_id_at']))
        if isinstance(nm, str):
            pal[nm.replace('/', chr(92)).lower()] = i

    LIFT, STACK = 0.30, 0.40
    plan = []
    for gi, g in enumerate(groups):
        key = '%s%d' % (REACH_MARKER_PREFIX, gi + 1)
        anchor = anchors.get(key)
        if anchor is None:
            for t in g:
                out.append({'effect': 'spawned weapons',
                            'field': str(t).rsplit(chr(92), 1)[-1], 'ok': False,
                            'reason': 'no %s on this map' % key})
            continue
        (ax, ay, az), mask = anchor
        for k, t in enumerate(g):
            short = str(t).rsplit(chr(92), 1)[-1]
            pi = pal.get(str(t).replace('/', chr(92)).lower())
            if pi is None:
                out.append({'effect': 'spawned weapons', 'field': short, 'ok': False,
                            'reason': 'not in this level weapon palette'})
                continue
            plan.append((pi, (ax, ay, az + LIFT + k * STACK), mask, short, key))
    if not plan:
        return out

    # A template with a VALID Type, so appended elements inherit real Type / Source /
    # BSP Policy rather than guessed ones. Auto is only a tie-break -- the copy clears
    # NOT_AUTO/NEVER anyway, and a map can ship an all-zero placement whose Type is -1.
    tyoff = _eq_offsets(game).get('type')

    def _type_ok(i):
        if tyoff is None:
            return True
        return struct.unpack_from('<h', m.data, base + i * wes + tyoff)[0] >= 0

    def _is_auto(i):
        return not (struct.unpack_from('<I', m.data, base + i * wes + _EQ_FLAGS)[0]
                    & (_PLACE_NOT_AUTO | (1 << _eq_offsets(game)['never_bit'])))

    tmpl = next((i for i in range(N) if _type_ok(i) and _is_auto(i)), None)
    if tmpl is None:
        tmpl = next((i for i in range(N) if _type_ok(i)), None)
    if tmpl is None:
        return out + [{'effect': 'spawned weapons', 'ok': False,
                       'reason': 'no weapon placement to use as a template'}]

    got = _h3_reserve(m, [(N + len(plan)) * wes])
    if got is None:
        return out + [{'effect': 'spawned weapons', 'ok': False,
                       'reason': 'no free space to grow the weapon block'}]
    dest = got[0]
    m.data[dest:dest + N * wes] = m.data[base:base + N * wes]
    uids = [m.u32(base + i * wes + _eq_offsets(game)['uid']) for i in range(N)]
    salt = (uids[tmpl] >> 16) if uids else 0
    nxt = (max(u & 0xFFFF for u in uids) + 1) if uids else 1
    eqo = _eq_offsets(game)
    for k, (pi, pos, mask, short, key) in enumerate(plan):
        e = dest + (N + k) * wes
        m.data[e:e + wes] = m.data[base + tmpl * wes: base + (tmpl + 1) * wes]
        struct.pack_into('<h', m.data, e, pi)
        struct.pack_into('<h', m.data, e + 0x2, -1)          # unnamed
        struct.pack_into('<I', m.data, e + _EQ_FLAGS, _PLACE_AT_REST)
        struct.pack_into('<fff', m.data, e + _EQ_POS, *pos)
        struct.pack_into('<H', m.data, e + eqo['zone'], 0)   # every zone set
        struct.pack_into('<H', m.data, e + 0x54, mask)       # the marker's own BSPs
        struct.pack_into('<h', m.data, e + eqo['folder'], -1)
        struct.pack_into('<I', m.data, e + eqo['uid'],
                         ((salt << 16) | (nxt + k)) & 0xFFFFFFFF)
        out.append({'effect': 'spawned weapons', 'field': short, 'ok': True,
                    'old': key, 'new': 'placed at (%.1f, %.1f, %.1f)' % pos})
    struct.pack_into('<i', m.data, scnr + woff, N + len(plan))
    struct.pack_into('<I', m.data, scnr + woff + 4, m.off2data(dest))
    return out


def _apply_spawn_equipment(m, game, spec, odst_all_insertions=False):
    """Grant Halo 3 starting equipment by APPENDING placements at the player start.

    `spec` = {'groups': [[eqip tag path, ...], ...]}. Group i is player i's items:
    group 0 -> player 1, group 1 -> player 2. With 2-player coop off the caller hands a
    single merged group. Each group drops at that player's start — the curated
    _H3_LOADOUT_ANCHOR where the spawn is unusable, else the Player Starting Location.

    A piece that does not stream at the start (_H3_NO_START_STREAM) can't render there,
    so it falls back to the nearest weapon in a BSP where it does stream; several such
    pieces spread across the nearest distinct weapons rather than stacking on one.

    Appending rather than reusing a vanilla placement is the point: relocating an
    existing one would delete that pickup from wherever the level put it."""
    out = []
    lay = _MAP_EQUIPMENT.get(str(game).strip())
    scnr_base = _scnr_base(m)
    groups = [[t for t in (g or []) if t] for g in (spec.get('groups') or [])]
    # Reach joins once its Equipment layout exists: same placement shape, same 16-byte
    # palette tagRef, and the ident it needs is now READ from the tag table rather than
    # minted, which is what made a Reach ref unwritable before.
    if (str(game).strip() not in ('Halo 3', 'Halo 3: ODST', 'Halo Reach')
            or not lay or scnr_base is None or not any(groups)):
        return out
    # REACH: prefer flipping a marker the map already carries over inventing a spot.
    # A rebuilt Reach map ships one inert placement per ability, put where the designer
    # wants it; enabling that is both more reliable than a derived position and the
    # only route that works at all for an ability the vanilla cache cannot spawn (see
    # reach_equipment_markers). Anything with no marker falls through to the append
    # path below, which is what still serves Halo 3 and ODST.
    if str(game).strip() == 'Halo Reach':
        # NAMED markers first. `enhancer_marker1` is player 1's position and
        # `enhancer_marker2` player 2's, so group i goes to marker i+1 and the
        # position's palette entry is repointed at whatever that player picked --
        # no guessing a spot, no reliance on block order, and the coordinates are
        # the designer's.
        named = reach_named_markers(m, game)
        if named:
            left = []
            for gi, g in enumerate(groups):
                keep = []
                slot = named.get('%s%d' % (REACH_MARKER_PREFIX, gi + 1))
                for t in g:
                    if slot is None:
                        keep.append(t)
                        continue
                    r = _reach_set_marker(m, game, slot, t)
                    out.append(r)
                    slot = None          # one item per named position
                    if not r.get('ok'):
                        keep.append(t)
                left.append(keep)
            groups = left
            if not any(groups):
                return out
        markers = reach_equipment_markers(m, game)
        if markers:
            left = []
            for g in groups:
                keep = []
                for t in g:
                    key = str(t).replace('/', chr(92)).lower()
                    idxs = markers.get(key)
                    if idxs:
                        pos = reach_enable_marker(m, game, idxs.pop(0))
                        out.append({'effect': 'starting equipment',
                                    'field': str(t).rsplit(chr(92), 1)[-1], 'ok': True,
                                    'old': 'inert marker',
                                    'new': 'enabled at (%.0f, %.0f, %.0f)' % pos})
                    else:
                        keep.append(t)
                left.append(keep)
            groups = left
            if not any(groups):
                return out
    eqo = _eq_offsets(game)
    ioff, ies = lay['items']
    poff, pes = lay['palette']
    N = max(0, m.i32(scnr_base + ioff))
    base = _block_base(m, scnr_base + ioff)
    if not N or not base:
        return [{'effect': 'starting equipment', 'ok': False,
                 'reason': 'level has no equipment placements to extend'}]

    # A placement references the Equipment Palette by index. A piece the level never
    # uses isn't in the palette, but its tag IS loaded (the models ship in the map), so
    # we can append a palette entry pointing at it rather than giving up.
    pal = {}                        # tag path (lower) -> palette index
    pal_by_datum = {}               # tag datum -> palette index (name-independent)
    pc = max(0, m.i32(scnr_base + poff))
    pbase = _block_base(m, scnr_base + poff)
    for i in range(pc) if pbase else []:
        datum = m.u32(pbase + i * pes + lay['pal_id_at'])
        pal_by_datum.setdefault(datum, i)
        nm = _tag_name_by_id(m, datum)
        if isinstance(nm, str):
            pal[nm.replace('/', '\\').lower()] = i

    spawns = h3_player_spawns(m, game)
    if not spawns:
        return [{'effect': 'starting equipment', 'ok': False,
                 'reason': 'no player starting locations'}]

    map_id = str(getattr(m, 'internal_name', '') or '')
    anchor = _H3_LOADOUT_ANCHOR.get(map_id)
    skip = _H3_NO_START_STREAM.get(map_id, frozenset())
    anchor_mask = _h3_mask_at(m, anchor, game) if anchor else None
    dead_spawn = None

    # Some levels keep a Player Starting Location the game never uses. Kikowani
    # Station's four sit in empty space ~240 units from where the player actually
    # starts, so anything dropped on them is placed somewhere nobody goes. Detect that
    # instead of curating another anchor by hand, and fall back to a pickup spot the
    # level itself uses -- on Kikowani those land ~12 units from the real start.
    # ODST only for now. 040_voi's spawn is just as isolated (30.0 units), but Halo 3
    # levels have not been re-tested against this and H3 starting equipment works
    # today, so moving its drop point is a separate, verifiable change.
    # Reach joins ODST here too, and it is the bigger case: SIX of its ten campaign
    # maps have an isolated starting location (m20 m30 m45 m52 m60 m70), against one
    # in Halo 3 and one in ODST. Reach starts most missions from a cinematic or a
    # vehicle, so the scenario's Player Starting Location is frequently not where the
    # player is put down -- which is why equipment dropped there was never found.
    if (not anchor and str(game).strip() in ('Halo 3: ODST', 'Halo Reach')
            and _spawn_is_dead(m, spawns[0][0], game)):
        # anchored on the starting location, not on block order
        spot = _live_equipment_spot(m, game, near=spawns[0][0])
        if spot:
            anchor, anchor_mask = spot
            dead_spawn = spawns[0][0]
            out.append({'effect': 'starting equipment', 'field': 'anchor', 'ok': True,
                        'note': 'player start (%.0f, %.0f, %.0f) is unused by this '
                                'level; dropping at (%.0f, %.0f, %.0f) instead'
                                % (tuple(dead_spawn) + tuple(anchor))})
        else:
            return [{'effect': 'starting equipment', 'ok': False,
                     'reason': 'player start is unused by this level and it has no '
                               'placed equipment to fall back to'}]

    def _resolve_pi(tag, key, label):
        """Palette index for a tag (appending an entry if needed), or (None, None) with
        a skip already emitted. Second value = whether a palette entry was appended."""
        pi = pal.get(key, new_pal_idx.get(key))
        if pi is not None:
            return pi, False
        datum = _h3_tag_datum(m, 'eqip', tag)
        if datum is None:
            out.append({'effect': 'starting equipment', 'field': label, 'ok': True,
                        'skip': True, 'reason': _no_equipment_reason(game)})
            return None, None
        # duplicate guard: reuse an entry already present by datum (name-independent)
        if datum in pal_by_datum:
            new_pal_idx[key] = pal_by_datum[datum]
            return pal_by_datum[datum], False
        pi = pc + len(new_pal)
        new_pal.append(datum)
        new_pal_idx[key] = pi
        return pi, True

    plan = []                   # (pi, pos, mask, label, si, added, mode)
    new_pal = []                # datums to append to the palette, in assignment order
    new_pal_idx = {}            # path key -> the palette index it will get
    used_weapons = set()        # weapon placements already used as a fallback drop
    # ODST levels start the player at an INSERTION POINT, and the scenario says which
    # locations belong to which one. Insertion 0 is the mission's real start and holds
    # exactly four locations on every ODST map -- the four co-op players, in player
    # order -- so player i is equipped at insertion-0 location i and nowhere else.
    #
    # This replaces clustering every starting location on the map together. That could
    # not tell a start from a mid-mission revert point, so it armed all of them: ONI
    # Alpha Site resolved to 5 places and dropped a player's single Invincibility pick
    # at all five. It also merged one place's four co-op slots (0.5-4 units apart) into
    # a single point, which is why the two players shared a drop and swapping their
    # loadouts moved nothing visible.
    #
    # `extra` keeps the old behaviour available where it is actually earned: the hub's
    # scripted teleport destinations (six of Mombasa Streets' eight level-select start
    # points, which no starting location covers), and -- opt in -- the level's other
    # insertion points. Halo 3 is untouched: its four spawns ARE the two players'
    # starts, with no insertion points involved.
    odst = str(game).strip() == 'Halo 3: ODST'
    starts = None                   # [(pos, bsp) per player] at insertion 0
    extra = []                      # additional (pos, bsp) drops, shared by all players
    if odst and not anchor:
        by_ip = odst_player_starts(m, game)
        starts = by_ip.get(ODST_START_INSERTION) or None
        if starts:
            tp = _odst_teleport_points(m)
            if odst_all_insertions:
                for ip, locs in sorted(by_ip.items()):
                    if ip != ODST_START_INSERTION:
                        tp = tp + list(locs)
            # de-duplicate against the starts and each other, so a teleport point that
            # lands on a start does not double the drop there
            seen_pts = list(starts)
            for pos, bsp in tp:
                if not any(math.dist(pos, p) < 8.0 for p, _ in seen_pts):
                    seen_pts.append((pos, bsp))
                    extra.append((pos, bsp))

    def _mask_for(pos, bsp):
        # ODST and Reach spawns carry no BSP index (ODST uses insertion points, Reach
        # stores -1), so the BSP a placement must ATTACH to is derived from the
        # nearest vanilla placement there instead — the same approximation the curated
        # anchors already use. Getting this mask wrong is silent: the object is in the
        # scenario, has a valid type, and simply cannot attach to the BSP it stands
        # in, so nothing spawns.
        return (1 << bsp) if bsp >= 0 else _h3_mask_at(m, pos, game)

    ring = {}                   # base-point key -> how many items dropped there so far
    fallback_done = set()       # (label, group) already given a fallback drop
    for si, items in enumerate(groups):
        if not items:
            continue
        if anchor:
            targets = [('anchor', anchor, anchor_mask)]
        elif starts is not None:
            # Player si's own start, plus whatever `extra` earned a shared drop. A
            # level with fewer starting locations than players (none ship that way, but
            # a modified scenario could) falls back to the last one rather than
            # equipping nobody.
            pos, bsp = starts[si] if si < len(starts) else starts[-1]
            targets = [('start%d' % si, pos, _mask_for(pos, bsp))]
            targets += [('extra%d.%d' % (i, si), p, _mask_for(p, b))
                        for i, (p, b) in enumerate(extra)]
        elif si < len(spawns):
            targets = [(si, spawns[si][0], _mask_for(*spawns[si]))]
        elif spawns:
            # FEWER LOCATIONS THAN PLAYERS. Reach's m50, m70 and m70_bonus declare
            # exactly ONE Player Starting Location, so player 2 matched nothing here
            # and was reported as a skip -- they got no equipment at all, on three of
            # the ten maps. Fall back to the last location, which is what the ODST
            # branch above already does for the same reason; the ring offset below is
            # what keeps two players' items from landing inside each other.
            pos, bsp = spawns[-1]
            targets = [(si, pos, _mask_for(pos, bsp))]
        else:
            # a non-error outcome (a level with no starting locations at all)
            for tag in items:
                out.append({'effect': 'starting equipment',
                            'field': str(tag).rsplit('\\', 1)[-1], 'ok': True, 'skip': True,
                            'reason': f'no player starting location {si}'})
            continue
        for bkey, base_pos, base_mask in targets:
            for tag in items:
                key = str(tag).replace('/', '\\').lower()
                label = str(tag).rsplit('\\', 1)[-1]
                pi, added = _resolve_pi(tag, key, label)
                if pi is None:
                    continue
                if label in skip:
                    # can't stream at the start -> drop on the nearest weapon in a BSP
                    # where it does; multiple such pieces spread over distinct weapons.
                    # Once per piece, not once per cluster: the fallback spot is chosen
                    # by proximity and would otherwise consume a weapon per cluster.
                    if (label, si) in fallback_done:
                        continue
                    emask = _h3_stream_mask(m, ioff, ies, pi)
                    fb = _h3_fallback_weapon(m, base_pos, emask, used_weapons) if emask else None
                    if fb is None:
                        out.append({'effect': 'starting equipment', 'field': label,
                                    'ok': True, 'skip': True,
                                    'reason': "can't spawn at start, no fallback spot"})
                        fallback_done.add((label, si))
                        continue
                    used_weapons.add(fb[0])
                    fallback_done.add((label, si))
                    plan.append((pi, fb[1], fb[2], label, bkey, added, 'fallback'))
                else:
                    # Tight ring around the base point so multiple items don't
                    # interpenetrate. Keyed by the POSITION, not by the player or
                    # cluster: where two players share a base point -- which is now
                    # the normal case on the three Reach maps with a single starting
                    # location -- a per-player ring restarted at angle 0 for each of
                    # them and stacked both loadouts on the same spot.
                    rkey = (round(base_pos[0], 2), round(base_pos[1], 2),
                            round(base_pos[2], 2))
                    kk = ring.get(rkey, 0)
                    ring[rkey] = kk + 1
                    ang = kk * 1.9
                    # 0.8 units is too tight for Reach: a ring of six abilities at
                    # that radius on m20 put five of them INSIDE the equipment cases
                    # the level's guns sit in -- one was visible but stuck in a wall
                    # and the rest could not be found at all. 2.0 clears that scenery.
                    # Halo 3 and ODST keep 0.8, where the drops are shipped and
                    # confirmed in game and a wider ring is an untested change.
                    rad = 2.0 if str(game).strip() == 'Halo Reach' else 0.8
                    p = (base_pos[0] + rad * math.cos(ang),
                         base_pos[1] + rad * math.sin(ang), base_pos[2])
                    plan.append((pi, p, base_mask, label, bkey, added, 'start'))
    if not plan:
        return out

    # A template placement that already spawns on its own, so new elements inherit
    # valid Type / Source / BSP Policy instead of guessed values.
    # A VALID Type is the first requirement, not auto-spawning. Exodus (m50) ships one
    # placement that is all zeros with Type -1, and it is the only one of its 46 that
    # is not flagged Not Automatically -- so an auto-first scan picked exactly the one
    # element that carries no usable Type, and every appended placement inherited
    # Type -1 and never spawned. Auto is still preferred among valid candidates, but
    # only as a tie-break: the copy clears NOT_AUTO/NEVER on the new element anyway.
    def _type_ok(i):
        off = eqo.get('type')
        if off is None:
            return True
        return struct.unpack_from('<h', m.data, base + i * ies + off)[0] >= 0

    def _is_auto(i):
        return not (struct.unpack_from('<I', m.data, base + i * ies + _EQ_FLAGS)[0]
                    & (_PLACE_NOT_AUTO | (1 << eqo['never_bit'])))

    tmpl = next((i for i in range(N) if _type_ok(i) and _is_auto(i)), None)
    if tmpl is None:
        # Mombasa Streets and ONI Alpha Site flag ALL their equipment non-auto --
        # script-spawned -- and refusing there meant no starting equipment at all on
        # two levels for no real reason. Take any placement with a usable Type.
        tmpl = next((i for i in range(N) if _type_ok(i)), None)
    if tmpl is None:
        tmpl = 0 if N else None
    if tmpl is None:
        return out + [{'effect': 'starting equipment', 'ok': False,
                       'reason': 'no equipment placement to use as a template'}]

    # Reserve slack for both grown blocks in one run so neither clobbers the other.
    items_need = (N + len(plan)) * ies
    pal_need = (pc + len(new_pal)) * pes
    sizes = [items_need] + ([pal_need] if new_pal else [])
    got = _h3_reserve(m, sizes)
    if got is None:
        return out + [{'effect': 'starting equipment', 'ok': False,
                       'reason': f'no free run of {sum(sizes)} bytes to relocate blocks'}]
    dest = got[0]

    # --- grow the palette first (placements below reference its new indices) ---
    if new_pal:
        pdest = got[1]
        m.data[pdest:pdest + pc * pes] = m.data[pbase:pbase + pc * pes]
        pal_tmpl = m.data[pbase:pbase + pes]            # an eqip tagRef, for the group id
        for j, datum in enumerate(new_pal):
            pe_off = pdest + (pc + j) * pes
            m.data[pe_off:pe_off + pes] = pal_tmpl
            struct.pack_into('<I', m.data, pe_off + lay['pal_id_at'], datum)
        struct.pack_into('<i', m.data, scnr_base + poff, pc + len(new_pal))
        struct.pack_into('<I', m.data, scnr_base + poff + 4, m.off2data(pdest))

    # --- grow the placements ---
    m.data[dest:dest + N * ies] = m.data[base:base + N * ies]
    uids = [m.u32(base + i * ies + eqo['uid']) for i in range(N)]
    nxt = max(u & 0xFFFF for u in uids) + 1
    salt = uids[tmpl] >> 16

    for k, (pi, pos, mask, label, bkey, added, mode) in enumerate(plan):
        e = dest + (N + k) * ies
        m.data[e:e + ies] = m.data[base + tmpl * ies: base + (tmpl + 1) * ies]
        struct.pack_into('<h', m.data, e + _EQ_PALETTE, pi)
        struct.pack_into('<h', m.data, e + _EQ_NAME, -1)
        fl = struct.unpack_from('<I', m.data, e + _EQ_FLAGS)[0] & ~(
            _PLACE_NOT_AUTO | (1 << eqo['never_bit']))
        struct.pack_into('<I', m.data, e + _EQ_FLAGS, fl)
        struct.pack_into('<fff', m.data, e + _EQ_POS, pos[0], pos[1], pos[2])
        struct.pack_into('<ii', m.data, e + _EQ_NODES, 0, 0)     # own no Node Orientations
        struct.pack_into('<I', m.data, e + eqo['uid'],
                         ((salt << 16) | (nxt + k)) & 0xFFFFFFFF)
        struct.pack_into('<h', m.data, e + eqo['folder'], -1)    # immune to object_destroy_folder
        struct.pack_into('<H', m.data, e + eqo['attach'], mask)
        if eqo.get('zone') is not None:
            # Reach's zone-set mask is a SEPARATE field from the BSP-attach one, and
            # 0 means unrestricted -- which is what Reach's own placements use
            # (22/22 on m10, 47/55 on m30). The template's mask could restrict the
            # drop to zone sets the player never enters, so it is cleared outright.
            struct.pack_into('<H', m.data, e + eqo['zone'], 0)
        if eqo['gameflags'] is not None:
            # Reach has no Multiplayer Flags on a placement at all, so there is
            # nothing to clear -- writing anyway would corrupt whatever it does keep.
            struct.pack_into('<H', m.data, e + eqo['gameflags'], 0)  # campaign, not MP-only
        if mode == 'fallback':
            where = "at nearest weapon (can't stream at start)"
        elif anchor:
            where = 'at start anchor'
        else:
            # bkey names the drop point: a cluster id on ODST (one per insertion
            # point), else the player index whose start it is.
            where = ('at start cluster %s' % str(bkey)[1:] if str(bkey).startswith('c')
                     else 'on spawn %s' % bkey)
        row = {'effect': 'starting equipment', 'field': label, 'ok': True,
               'old': 'not present', 'new': where + (' (+palette)' if added else '')}
        if str(game).strip() == 'Halo Reach':
            # An APPENDED Reach placement is a guess in two ways: this map ships no
            # marker for the piece, and if the vanilla cache never uses that ability
            # it will not spawn here no matter how the placement reads. Measured on
            # m10: three of six spawned from a patched-in placement, all six from the
            # rebuild. Say so on the row rather than letting a silent no-show look
            # like a patcher bug.
            row['note'] = ('appended, not a marker -- if it does not appear this map '
                           'needs rebuilding with the ability placed '
                           '(weapon_availability.py --equipment)')
        out.append(row)

    # repoint the placements last, so the map stays consistent if anything above raised
    struct.pack_into('<i', m.data, scnr_base + ioff, N + len(plan))
    struct.pack_into('<I', m.data, scnr_base + ioff + 4, m.off2data(dest))
    return out


def _spread_slots(N, counts):
    """Assign each (key, count) `count` placement slots EVENLY spread across [0, N)
    — evenly-spaced positions with collisions bumped to the nearest free slot, so a
    weapon's replacements are scattered through the level (not clustered up front),
    and different weapons interleave. Returns {slot_index: key}."""
    target = {}
    for key, c in counts:
        if c <= 0:
            continue
        for k in range(c):
            pos = min(int((k + 0.5) * N / c), N - 1)
            if pos not in target:
                target[pos] = key
                continue
            for d in range(1, N):
                if pos + d < N and (pos + d) not in target:
                    target[pos + d] = key
                    break
                if pos - d >= 0 and (pos - d) not in target:
                    target[pos - d] = key
                    break
            else:
                break
    return target


def map_weapon_placement_count(m, game):
    """How many weapon placements the level has — the denominator a Map Presence
    percentage applies to. 0 if the game has no known layout."""
    lay = _MAP_WEAPONS.get(str(game).strip())
    scnr_base = _scnr_base(m)
    if not lay or scnr_base is None:
        return 0
    return max(0, m.i32(scnr_base + lay['weapons'][0]))


def _apply_weapon_swaps(m, game, registry, swaps):
    """Replace a fraction of the map's weapon placements with the players' picked
    weapons, scattered evenly. `swaps` = {weap-tag: rate 0..1}. Rounds are set to the
    weapon's VANILLA magazine values (this runs BEFORE the effect ops, so Magazine
    picks don't apply). Weapons absent from the map's Weapon Palette are skipped."""
    out = []
    lay = _MAP_WEAPONS.get(game)
    scnr_base = _scnr_base(m)
    if not lay or scnr_base is None:
        return [{'effect': 'map weapons', 'ok': False, 'reason': 'scnr/layout unavailable'}]
    woff, wes = lay['weapons']
    poff, pes = lay['palette']
    N = m.i32(scnr_base + woff)
    if N <= 0:
        return [{'effect': 'map weapons', 'ok': False, 'reason': 'no weapon placements in map'}]
    wbase = _block_base(m, scnr_base + woff)
    pbase = _block_base(m, scnr_base + poff)
    pcount = m.i32(scnr_base + poff)
    pal = {i: _tag_name_by_id(m, m.u32(pbase + i * pes + lay['pal_id_at'])) for i in range(pcount)}
    weap_plug = registry.get('weap')

    assign = []          # (palette_index, count, rounds_left, rounds_loaded, short)
    for tag, rate in swaps.items():
        if not rate or rate <= 0:
            continue
        _, name = hm.split_tag(tag)
        short = name.rsplit(chr(92), 1)[-1]
        pi = next((i for i, n in pal.items() if n == name), None)
        if pi is None:                          # SAFETY NET: not in the map's palette
            out.append({'effect': 'map weapons', 'field': short, 'ok': False,
                        'reason': 'weapon not in this map\'s palette'})
            continue
        c = int(round(rate * N))
        if c <= 0:
            out.append({'effect': 'map weapons', 'field': short, 'ok': True, 'skip': True,
                        'reason': f'rate too low for {N} placements (rounds to 0)'})
            continue
        rl = rd = -1
        wb = _weap_base(m, name)
        if wb is not None and weap_plug is not None:
            t = m.read_tag_field(wb, 'Rounds Total Maximum', weap_plug, block='Magazines', index=0)
            l = m.read_tag_field(wb, 'Rounds Loaded Maximum', weap_plug, block='Magazines', index=0)
            rl = int(t) if t is not None else -1
            rd = int(l) if l is not None else -1
        assign.append((pi, c, rl, rd, short))

    # never replace more than N placements (UI caps the slider sum, this is a guard)
    while sum(a[1] for a in assign) > N and assign:
        j = max(range(len(assign)), key=lambda k: assign[k][1])
        pi, c, rl, rd, s = assign[j]
        assign[j] = (pi, c - 1, rl, rd, s)

    # NOTE: no BSP/streaming filter here (unlike _apply_equipment_swaps). Weapons are
    # carried by nearly every enemy and marine, so their models stream in essentially
    # every combat zone — i.e. everywhere weapon placements sit — and the streaming gate
    # never bites. Confining to placement BSPs would only under-place a common weapon
    # whose own placements happen to cluster in a few zones.
    slots = _spread_slots(N, [(a[0], a[1]) for a in assign])
    # Never scatter a pick onto a MARKER. It is the player's own loadout position and
    # the starting-equipment pass has already put their choice there; overwriting it
    # would silently swap the item they picked for something else.
    for _pi in list(reach_protected_slots(m, game, block='weapons')):
        slots.pop(_pi, None)
    info = {a[0]: (a[2], a[3], a[4]) for a in assign}
    done = {}
    for slot, pi in slots.items():
        e = wbase + slot * wes
        struct.pack_into('<h', m.data, e + lay['palette_index'], pi)
        rl, rd, short = info[pi]
        if rl >= 0:
            struct.pack_into('<h', m.data, e + lay['rounds_left'], max(-32768, min(32767, rl)))
        if rd >= 0:
            struct.pack_into('<h', m.data, e + lay['rounds_loaded'], max(-32768, min(32767, rd)))
        done[short] = done.get(short, 0) + 1
    for short, n in done.items():
        out.append({'effect': 'map weapons', 'field': short, 'ok': True,
                    'old': f'{N} placements', 'new': f'{n} swapped in'})
    # a pick that survived rate-rounding but got trimmed to 0 by the N cap
    for _pi, _c, _rl, _rd, short in assign:
        if done.get(short, 0) == 0:
            out.append({'effect': 'map weapons', 'field': short, 'ok': True, 'skip': True,
                        'reason': f'trimmed to 0 (total capped at {N} placements)'})
    return out


# --- zoom-UI copy: give a scopeless weapon a working scope overlay -----------
# The scope lives in the weapon's HUD tag (H2 nhdt / H1 wphi), reached via the weap
# tag's HUD-interface tagRef. We copy the donor's scope sub-elements into the target
# HUD by growing the relevant block(s). Elements are copied verbatim, so embedded
# tagRefs (scope masks/bitmaps) keep their map-global datums and resolve to the
# donor's art in place.
#
# H1 needs BOTH parts of the scope: the full-screen mask is a "Screen Effect" block
# element (with Mask tagRefs), and the reticle is a "Zoom Overlay" Crosshair. A HUD
# is "scoped" iff it has a Screen Effect. H2's scope is a set of zoom-gated Bitmap
# Widgets (flat), gated on the [Yes]Unit "Zoomed" flag bits. Each source block gives
# a selector (which elements are the scope) and, if its elements carry a child
# reflexive (H1 Crosshair -> Crosshair Overlays), a (child_off, child_elem) to
# relocate into the target's own tag data so the copy owns it (see _selfcontain).
_ZOOM_UI = {
    'Halo 1': {'hud_ref': 0x480, 'id_at': 0xC,
               'scoped_block': 0xAC,       # Screen Effect present => already scoped
               'donor_pref': ('sniper rifle', 'pistol'),
               'blocks': [
                   {'off': 0xAC, 'elem': 0xB8, 'sel': ('all',), 'child': None},        # scope mask
                   {'off': 0x84, 'elem': 0x68, 'sel': ('eq', 0x0, 1),                   # zoom reticle
                    'child': (0x34, 0x6C)},                                            # Crosshair Overlays
               ]},
    'Halo 2': {'hud_ref': 0x2B0, 'id_at': 0x4,
               'scoped_block': None,       # detected via the zoom-gated widget selector
               'donor_pref': ('sniper_rifle', 'beam_rifle', 'battle_rifle'),
               'blocks': [
                   {'off': 0x8, 'elem': 0x64, 'sel': ('and', 0x8, 0b11 << 7), 'child': None},
               ]},
    # H3 and ODST share the chud_definition layout, but NOT the weap layout: ODST moved
    # every late weap field on by 0x10 (HUD Interface 0x408 -> 0x418, Magazines 0x424 ->
    # 0x434, First Person 0x3FC -> 0x40C, Magnification Levels 0x31E -> 0x32E). Checked
    # against both plugins rather than assumed -- reading ODST's offset on a Halo 3 map
    # finds no HUD at all. The scope is NOT a flat block on the HUD like the earlier
    # games': it is Bitmap/Text widgets NESTED inside top-level HUD Widgets, so these use
    # the nested copier below rather than 'blocks'.
    'Halo 3': {'hud_ref': 0x408, 'id_at': 0xC, 'scoped_block': None, 'nested': True,
               'donor_pref': ('sniper_rifle', 'beam_rifle', 'battle_rifle', 'carbine',
                              'spartan_laser', 'rocket_launcher')},
    'Halo 3: ODST': {'hud_ref': 0x418, 'id_at': 0xC, 'scoped_block': None, 'nested': True,
                     'donor_pref': ('sniper_rifle', 'beam_rifle', 'battle_rifle',
                                    'carbine', 'automag', 'smg_silenced')},
    # Reach: the weap plugin names no HUD field, so 0x3C4 was found by scanning every
    # weapon struct for a datum resolving to a chdt (8/8 hit, correctly named). Its
    # chud keeps Halo 3's nested shape but at different offsets, and detects zoom
    # through a trigger rather than a bitfield -- see _CHUD_BLOCKS / _REACH_ZOOM.
    'Halo Reach': {'hud_ref': 0x3C4, 'id_at': 0xC, 'scoped_block': None, 'nested': True,
                   'donor_pref': ('sniper_rifle', 'dmr', 'needle_rifle', 'focus_rifle',
                                  'magnum')},
}

# chud_definition, per the ODSTMCC plugin. A widget's State Data carries "Unit Zoom
# State" at +0x26: bit0 Unzoomed, bit1 Zoom Lvl 1, bit2 Zoom Lvl 2. A widget whose
# every state demands zoom IS the scope. Checked against all twelve ODST weapon HUDs:
# the six scoped ones have such widgets, the six unscoped ones have exactly zero.
_H3_CHUD_WIDGETS = (0x0, 0x50)
_H3_CHUD_BITMAPS = (0x38, 0x54)
_H3_CHUD_TEXTS = (0x44, 0x48)
# Reach kept the nesting but moved and grew every block, so the three are per-game
# rather than module constants. Halo 3 and ODST genuinely share these.
_CHUD_BLOCKS = {
    'Halo 3': {'widgets': (0x0, 0x50), 'bitmaps': (0x38, 0x54), 'texts': (0x44, 0x48)},
    'Halo 3: ODST': {'widgets': (0x0, 0x50), 'bitmaps': (0x38, 0x54), 'texts': (0x44, 0x48)},
    'Halo Reach': {'widgets': (0x0, 0xDC), 'bitmaps': (0x98, 0x9C), 'texts': (0xA4, 0x84)},
}
# Reach's zoom test: a widget whose 'Yes' State Data carries trigger code 0x55 only
# renders while zoomed. States (0x1C, 0x38) -> 'Yes' States (0x0, 0xC) ->
# Triggers (0x0, 0x8), code in the u32 at +0x4.
_REACH_ZOOM = {'states': (0x1C, 0x38), 'yes': (0x0, 0xC), 'trig': (0x0, 0x8),
               'code_at': 0x4, 'code': 0x55}


def _chud_blocks(game):
    return _CHUD_BLOCKS.get(str(game).strip(), _CHUD_BLOCKS['Halo 3: ODST'])
# ...but State Data is NOT shared. ODST inserted Skull / Survival Round / Wave / Lives
# / Difficulty / Pda ahead of the unit fields, growing the element and pushing Unit
# Zoom State down by 0x10. Using ODST's numbers on a Halo 3 map strides the wrong
# distance and reads the wrong halfword, so no widget ever looks zoom-only and the
# donor search reports "no scoped donor weapon in this map" on every level.
_H3_CHUD_STATE_LAYOUT = {
    'Halo 3': {'states': (0x8, 0x2C), 'zoom_at': 0x16},
    'Halo 3: ODST': {'states': (0x8, 0x3C), 'zoom_at': 0x26},
}
_H3_ZOOM_LEVELS, _H3_UNZOOMED = 0b110, 0b001


def _h3_chud_elems(m, base, blk):
    """File offsets of one chud sub-block's elements."""
    off, esz = blk
    n = m.i32(base + off)
    b = _block_base(m, base + off)
    return [b + i * esz for i in range(max(0, n))] if (b and n > 0) else []


def _reach_zoom_only(m, widget):
    """Reach: does this widget's 'Yes' state demand zoom (trigger code 0x55)?

    Reach dropped Halo 3's Unit Zoom State bitfield for a trigger list, so the test is
    a membership check rather than a mask. Validated against every weapon on m10
    against the ground truth of its own Magnification Levels: 5 scoped all detected,
    22 unscoped all clean.
    """
    z = _REACH_ZOOM
    for sd in _h3_chud_elems(m, widget, z['states']):
        for y in _h3_chud_elems(m, sd, z['yes']):
            for tr in _h3_chud_elems(m, y, z['trig']):
                if m.u32(tr + z['code_at']) == z['code']:
                    return True
    return False


def _h3_zoom_only(m, widget, game='Halo 3: ODST'):
    """True if this widget only ever renders while zoomed -- i.e. it is scope."""
    if str(game).strip() == 'Halo Reach':
        return _reach_zoom_only(m, widget)
    lay = _H3_CHUD_STATE_LAYOUT.get(game) or _H3_CHUD_STATE_LAYOUT['Halo 3: ODST']
    states = _h3_chud_elems(m, widget, lay['states'])
    if not states:
        return False
    for sd in states:
        z = m.u32(sd + lay['zoom_at']) & 0xFFFF
        if not (z & _H3_ZOOM_LEVELS) or (z & _H3_UNZOOMED):
            return False
    return True


def _h3_scope_parts(m, hud_base, game='Halo 3: ODST'):
    """[(widget, [scope bitmaps], [scope texts])] for every widget owning scope."""
    out = []
    B = _chud_blocks(game)
    for w in _h3_chud_elems(m, hud_base, B['widgets']):
        bms = [b for b in _h3_chud_elems(m, w, B['bitmaps'])
               if _h3_zoom_only(m, b, game)]
        txt = [t for t in _h3_chud_elems(m, w, B['texts'])
               if _h3_zoom_only(m, t, game)]
        # Reach also marks the OWNING widget, not just its children; Halo 3 never
        # does, so this only ever adds parts where the game really uses them.
        if not bms and not txt and _h3_zoom_only(m, w, game):
            out.append((w, [], []))
            continue
        if bms or txt:
            out.append((w, bms, txt))
    return out


def _h3_copy_scope(m, dst_hud, src_hud, game='Halo 3: ODST'):
    """Append the donor HUD's scope widgets to `dst_hud`. Returns elements copied.

    Only the ARRAYS are newly allocated: a copied element's own child blocks (State,
    Placement, Animation, Render) keep pointing at the donor's data. H3 tag data is one
    contiguous buffer addressed through the partition table, so a pointer into another
    tag resolves the same way -- unlike H1, where _selfcontain has to relocate children
    because that engine will not render a reflexive across tags.

    Each copied top-level widget keeps the donor's own state/placement so the overlay
    lands where the donor put it, but its children are filtered to the scope-only ones,
    so none of the donor's ordinary HUD (its crosshair, its ammo) comes along.
    """
    parts = _h3_scope_parts(m, src_hud, game)
    if not parts:
        return 0
    B = _chud_blocks(game)                 # Reach moved and grew every chud block
    woff, wesz = B['widgets']
    dst_n = max(0, m.i32(dst_hud + woff))
    dst_base = _block_base(m, dst_hud + woff)
    if dst_base is None:
        return 0
    sizes = [(dst_n + len(parts)) * wesz]
    for _, bms, txt in parts:
        sizes += [len(bms) * B['bitmaps'][1], len(txt) * B['texts'][1]]
    offs = _h3_reserve(m, [s for s in sizes if s])
    if offs is None:
        return None                       # no slack: caller reports it, nothing written
    it = iter(offs)
    warr = next(it)
    m.data[warr:warr + dst_n * wesz] = m.data[dst_base:dst_base + dst_n * wesz]
    copied = 0
    for i, (w, bms, txt) in enumerate(parts):
        e = warr + (dst_n + i) * wesz
        m.data[e:e + wesz] = m.data[w:w + wesz]
        for (boff, besz), kids in ((B['bitmaps'], bms), (B['texts'], txt)):
            if not kids:
                struct.pack_into('<iI', m.data, e + boff, 0, 0)
                continue
            arr = next(it)
            for j, k in enumerate(kids):
                m.data[arr + j * besz:arr + (j + 1) * besz] = m.data[k:k + besz]
            struct.pack_into('<iI', m.data, e + boff, len(kids), m.off2data(arr))
            copied += len(kids)
    # repoint last, so a failure above leaves the HUD untouched
    struct.pack_into('<iI', m.data, dst_hud + woff, dst_n + len(parts), m.off2data(warr))
    return copied


def _selfcontain(m, elem, child):
    """H1: relocate an element's child reflexive block into freshly appended tag
    data and repoint it there, so the copied element owns its child instead of
    pointing into the donor tag (which the H1 engine won't render across tags).
    `child` = (child_reflexive_offset, child_elem_size); None -> element unchanged."""
    if not child:
        return elem
    coff, cesz = child
    cnt = struct.unpack_from('<I', elem, coff)[0]
    ptr = struct.unpack_from('<I', elem, coff + 4)[0]
    if cnt <= 0:
        return elem
    src = (ptr - m.magic) & 0xFFFFFFFF
    new_off = m.append_raw(bytes(m.data[src:src + cnt * cesz]))
    b = bytearray(elem)
    struct.pack_into('<I', b, coff + 4, (new_off + m.magic) & 0xFFFFFFFF)
    return bytes(b)


def _hud_base(m, game, weap_base):
    """Follow a weap tag's HUD-interface tagRef to its HUD tag's base offset."""
    z = _ZOOM_UI[game]
    rid = m.u32(weap_base + z['hud_ref'] + z['id_at'])
    if rid in (0, 0xFFFFFFFF):
        return None
    row = rid & 0xFFFF
    if hasattr(m, 'tag'):                                   # H2: datum row -> tag
        t = m.tag(row)
        return t['base'] if t else None
    b = m.tag_array_off + row * 32                          # H1: tag-array meta_ptr
    off = (m.u32(b + 0x14) - m.magic) & 0xFFFFFFFF
    return off if 0 <= off < len(m.data) else None


def _block_elems(m, hud_base, bs):
    """Elements of one HUD source block matching its selector (list of raw bytes)."""
    cnt = m.i32(hud_base + bs['off'])
    if cnt <= 0:
        return []
    off = _block_base(m, hud_base + bs['off'])
    sel = bs['sel']
    out = []
    for i in range(cnt):
        e = off + i * bs['elem']
        if sel[0] == 'all':
            hit = True
        else:
            val = struct.unpack_from('<H', m.data, e + sel[1])[0]
            hit = (val == sel[2]) if sel[0] == 'eq' else bool(val & sel[2])
        if hit:
            out.append(bytes(m.data[e:e + bs['elem']]))
    return out


def _hud_is_scoped(m, game, hud_base):
    """True if this HUD already renders a scope (so we leave it alone)."""
    z = _ZOOM_UI[game]
    if z.get('nested'):                                    # H3/ODST: a zoom-only widget
        return bool(_h3_scope_parts(m, hud_base, game))
    if z['scoped_block'] is not None:                      # H1: Screen Effect present
        return m.i32(hud_base + z['scoped_block']) > 0
    return bool(_block_elems(m, hud_base, z['blocks'][0]))  # H2: a zoom-gated widget


def _weapons_sharing_hud(m, game, hud_base):
    """Short names of every weapon in the map whose HUD is this tag."""
    if isinstance(getattr(m, 'tags', None), dict):          # H1
        weaps = [(n, off) for (c, n), off in m.tags.items() if c == 'weap']
    else:
        weaps = [(t['name'], t['base']) for t in m.tags
                 if t.get('class') == 'weap' and t.get('base') and t.get('name')]
    out = set()
    for name, wb in weaps:
        try:
            if _hud_base(m, game, wb) == hud_base:
                out.add(str(name).rsplit(chr(92), 1)[-1])
        except Exception:
            continue
    return out


def _zoom_donor(m, game, exclude_hud, prefer=None):
    """The scoped donor weapon to copy from (its HUD base + short name), or
    (None, None). If `prefer` (a weap tag path) names a weapon that is present and
    scoped on this map, it wins; otherwise the best configured/auto donor is used."""
    z = _ZOOM_UI[game]
    if prefer:
        _, pname = hm.split_tag(prefer)
        wb = _weap_base(m, pname)
        if wb is not None:
            hud = _hud_base(m, game, wb)
            if hud is not None and hud != exclude_hud and _hud_is_scoped(m, game, hud):
                return hud, pname.rsplit(chr(92), 1)[-1]
    if isinstance(getattr(m, 'tags', None), dict):          # H1
        weaps = [(n, off) for (c, n), off in m.tags.items() if c == 'weap']
    else:                                                   # H2
        weaps = [(t['name'], t['base']) for t in m.tags
                 if t.get('class') == 'weap' and t.get('base')]
    cands = []
    for name, wb in weaps:
        hud = _hud_base(m, game, wb)
        if hud is None or hud == exclude_hud or not _hud_is_scoped(m, game, hud):
            continue
        cands.append((name, hud))
    if not cands:
        return None, None
    pref = z['donor_pref']
    cands.sort(key=lambda it: (pref.index(it[0].rsplit(chr(92), 1)[-1])
                               if it[0].rsplit(chr(92), 1)[-1] in pref else len(pref)))
    name, hud = cands[0]
    return hud, name.rsplit(chr(92), 1)[-1]


def _apply_zoom_ui(m, game, targets, prefer_donor=None):
    """Give each target weapon (weap tag paths) a scope if its HUD lacks one, by
    copying every scope source block from a donor weapon on the map. `prefer_donor`
    (a weap tag path) is used when present + scoped, else an auto donor. Idempotent:
    a HUD already scoped (vanilla, or shared with a weapon patched earlier this run)
    is left alone."""
    z = _ZOOM_UI.get(game)
    out = []
    if not z:
        return out
    grown = set()
    # A Zoom effect's tag may name SEVERAL weapons ("weap a & b") -- ODST's plasma
    # rifle is `plasma_rifle & plasma_rifle_red`, and every other consumer splits on
    # ' & '. Looking the joined string up as one tag name matched nothing, so the
    # variant tags never got a scope even though their Zoom fields were patched.
    names = []
    for tag in targets:
        _, joined = hm.split_tag(tag)
        for part in str(joined).split(' & '):
            part = part.strip()
            if part and part not in names:
                names.append(part)
    for name in names:
        short = name.rsplit(chr(92), 1)[-1]
        wb = _weap_base(m, name)
        if wb is None:
            out.append({'effect': 'zoom UI', 'field': short, 'ok': False,
                        'reason': 'weapon not in this map'})
            continue
        hud = _hud_base(m, game, wb)
        if hud is None:
            out.append({'effect': 'zoom UI', 'field': short, 'ok': False,
                        'reason': 'weapon has no HUD interface'})
            continue
        if hud in grown or _hud_is_scoped(m, game, hud):
            out.append({'effect': 'zoom UI', 'field': short, 'ok': True, 'skip': True,
                        'old': short, 'new': 'already has a scope — unchanged'})
            continue
        donor_hud, donor = _zoom_donor(m, game, exclude_hud=hud, prefer=prefer_donor)
        if donor_hud is None:
            out.append({'effect': 'zoom UI', 'field': short, 'ok': False,
                        'reason': 'no scoped donor weapon in this map'})
            continue
        if z.get('nested'):
            copied = _h3_copy_scope(m, hud, donor_hud, game)
            if copied is None:
                out.append({'effect': 'zoom UI', 'field': short, 'ok': False,
                            'reason': 'no free space in the map to grow the HUD'})
                continue
        else:
            copied = 0
            for bs in z['blocks']:
                elems = _block_elems(m, donor_hud, bs)
                if not elems:
                    continue
                if bs['child']:            # relocate each element's child sub-block
                    elems = [_selfcontain(m, e, bs['child']) for e in elems]
                m.grow_block(hud, bs['off'], bs['elem'], elems)
                copied += len(elems)
        grown.add(hud)
        # A HUD tag is shared by every weapon that points at it, so the scope lands on
        # all of them. Say so rather than letting it surprise: in ODST the restored
        # magnum rides on the Mauler's HUD until a dedicated ui\chud\magnum exists.
        also = sorted(_weapons_sharing_hud(m, game, hud) - {short})
        shared = (' — also scopes %s (shared HUD)' % ', '.join(also)) if also else ''
        out.append({'effect': 'zoom UI', 'field': short, 'ok': True, 'old': short,
                    'new': f'scope copied from {donor} ({copied} element(s)){shared}'})
    return out


# --- Sprint (New Features / Experimental) ----------------------------------
# Tunes a map that was BUILT with the sprint mod (invisible weapon + the
# global_scripts sprint.hsc). All of it is field/byte edits, no rebuild:
#   speed%      matg Run/Sneak Forward, and every player-held weapon's Forward
#               Movement Penalty (the sprint weapon alone stays at 0, so holding
#               it = full speed). Normal movement is unchanged.
#   duration    sprint_ticks   short global   (seconds * 30)
#   cooldown    sprint_cooldown short global   (seconds * 30)
#   enabled     sprint_enabled  boolean global (the master gate)
# See halo1-sprint-from-scratch memory for the storage format.
_SPRINT_STOCK_RUN, _SPRINT_STOCK_SNEAK = 2.25, 0.9
_SPRINT_WEAP = 'weapons\\sprint\\sprint'
_SPRINT_AI_ONLY = ('weapons\\energy sword\\energy sword',
                   'weapons\\fuel rod gun\\hunter fuel rod')


def _sprint_player_held(name):
    """Weapons the player can carry on foot get the movement penalty. Vehicle
    guns and AI-only weapons must stay at 0 or they'd sprint permanently."""
    return not name.startswith('vehicles\\') and name not in _SPRINT_AI_ONLY


def set_global(m, name, value):
    """Patch a Halo 1 script-global's init value in a built map, by name, no
    rebuild. scnr Globals block (0x4A8, elem 0x5C): each global's Init Expression
    Index (@0x28) indexes the Script Syntax Data blob (dataref @0x474; 56-byte
    header, then 20-byte nodes). Value TYPE is int16 @node+0x04 (5=bool, 6=real,
    7=short, 8=long); the constant is at node+0x10 (bool=1 byte, short=int16,
    real=f32, long=i32). Returns (old, new) or None if the global is absent.

    Halo 2 keeps its globals somewhere else entirely, so those go through h2_tune."""
    if _is_h2_map(m):
        return _h2_global(m, name, value, write=True)
    scnr = next((k for k in m.tags if k[0] == 'scnr'), None)
    if scnr is None:
        return None
    meta = m.tags[scnr]
    syn = (m.u32(meta + 0x474 + 12) - m.magic) & 0xFFFFFFFF
    cnt = m.i32(meta + 0x4A8)
    ptr = (m.u32(meta + 0x4A8 + 4) - m.magic) & 0xFFFFFFFF
    for i in range(cnt):
        b = ptr + i * 0x5C
        if m._cstr(b) != name:
            continue
        node = m.u32(b + 0x28) & 0xFFFF
        nb = syn + 56 + node * 20
        vtype = struct.unpack_from('<h', m.data, nb + 0x04)[0]
        off = nb + 0x10
        if vtype == 5:                                   # boolean: 1 byte
            old = m.data[off]; m.data[off] = 1 if value else 0
            return old, m.data[off]
        if vtype == 6:                                   # real
            old = struct.unpack_from('<f', m.data, off)[0]
            struct.pack_into('<f', m.data, off, float(value)); return old, float(value)
        if vtype == 8:                                   # long
            old = struct.unpack_from('<i', m.data, off)[0]
            struct.pack_into('<i', m.data, off, int(value)); return old, int(value)
        old = struct.unpack_from('<h', m.data, off)[0]   # short (default)
        struct.pack_into('<h', m.data, off, int(value)); return old, int(value)
    return None


def read_global(m, name):
    """Read a script-global's init value by name. Same layout as set_global.
    Returns the value, or None if the global isn't in this map."""
    if _is_h2_map(m):
        return _h2_global(m, name)
    scnr = next((k for k in m.tags if k[0] == 'scnr'), None)
    if scnr is None:
        return None
    meta = m.tags[scnr]
    syn = (m.u32(meta + 0x474 + 12) - m.magic) & 0xFFFFFFFF
    cnt = m.i32(meta + 0x4A8)
    ptr = (m.u32(meta + 0x4A8 + 4) - m.magic) & 0xFFFFFFFF
    for i in range(cnt):
        b = ptr + i * 0x5C
        if m._cstr(b) != name:
            continue
        nb = syn + 56 + (m.u32(b + 0x28) & 0xFFFF) * 20
        vtype = struct.unpack_from('<h', m.data, nb + 0x04)[0]
        off = nb + 0x10
        if vtype == 5:
            return bool(m.data[off])
        if vtype == 6:
            return struct.unpack_from('<f', m.data, off)[0]
        if vtype == 8:
            return struct.unpack_from('<i', m.data, off)[0]
        return struct.unpack_from('<h', m.data, off)[0]
    return None


# Flashlight-key abilities, matching sprint.hsc's ability0/ability1 selector.
_ABILITY_IDS = {'none': 0, 'sprint': 1, 'overshield': 2, 'camo': 3, 'regeneration': 4}

# Camo's duration is not a script global: it's the Powerup Time on the camo equipment
# tag (stock 45s), mirrored into the script's camo window. Cooldown is separate and
# starts when that window ends, so a full cycle is duration + cooldown.
_CAMO_TAG = 'powerups\\active camouflage'
_CAMO_SECONDS = 5.0
_CAMO_COOLDOWN_TICKS = 900      # 30s

# --- per game ------------------------------------------------------------------
# The two games' ability scripts were written years apart and do NOT share names or
# shape. Halo 1 selects an ability PER PLAYER (ability0/ability1) and gives each its own
# cooldown; Halo 2 runs one ability for both players (ab_kind) behind a single
# ab_cooldown, and has no separate overshield duration. Only vit_max, medi_rate,
# medi_ticks, sprint_ticks, camo_ticks and the fx_* set are spelled the same.
_SPRINT_WEAP_BY_GAME = {
    'Halo 1': _SPRINT_WEAP,
    # H2 already shipped an invisible token -- the weapon melee-only characters carry.
    'Halo 2': 'objects\\weapons\\melee\\unarmed\\unarmed',
}
_CAMO_TAG_BY_GAME = {
    'Halo 1': _CAMO_TAG,
    'Halo 2': 'objects\\powerups\\active_camouflage\\active_camouflage',
}
# Halo 1 global name -> the Halo 2 script's name, or None where H2 has no counterpart
# and the write is simply dropped.
#
# Nearly identity now: the per-player rewrite (h2_genscript.py) put the H2 script on H1
# naming, so ability0/ability1, os_shield, os_ticks and the four separate cooldowns all
# exist under their H1 names. Only the two H1 bookkeeping globals have no H2 twin.
#
# Maps built BEFORE that rewrite still carry the old shared names (ab_kind, ab_shield,
# ab_cooldown). They are handled in _apply_sprint by falling back to ab_kind rather than
# by aliasing here, so a stale deployed map keeps working and just runs one ability for
# both players.
_GLOBAL_ALIASES_H2 = {
    'medi_heal': None,      # H2 heals purely from medi_rate
    'os_body': None,        # H1-only, and unused there too
}


def _is_h2_map(m):
    """Halo 2 maps get the second-gen parser, which is also how the script globals are
    laid out differently -- see _h2_global()."""
    return type(m).__name__ == 'Halo2Map'


def _h2_tune():
    """Imported lazily: h2_tune imports THIS module, so a top-level import would be
    circular."""
    import importlib
    import sys as _sys
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sprint_toolkit')
    if here not in _sys.path:
        _sys.path.insert(0, here)
    return importlib.import_module('h2_tune')


def _h2_global(m, name, value=None, write=False):
    """Read or write a Halo 2 script global, going through h2_tune so the second-gen
    layout lives in exactly one place (globals at scnr+0x1C0 elem 0x28, and the syntax
    node table at scnr+0x23C -- NOT the 0x1A8 the Assembly plugin lists)."""
    name = _GLOBAL_ALIASES_H2.get(name, name)
    if name is None:
        return None
    t = _h2_tune()
    if t.read_global(m, name) is None:
        return None
    if not write:
        return t.read_global(m, name)
    old = t.read_global(m, name)
    return old, t.write_global(m, name, value)

# The engine's absolute vitality scale, measured in-game: a full body/shield is 75
# units. object_set_shield's argument is in 1/75 units (so x3 overshield = 3/75), and
# regeneration's per-tick write-back must scale the [0,1] getters by exactly this.
_VIT_MAX = 75.0
_OS_SHIELD_BASE = 1.0 / _VIT_MAX

# ...but only in Halo 1. Measured the same way in Halo 2 (no health bar there, so the
# SHIELD is the instrument: x1/x2/x3 came out at 0.01425/0.0285/0.04275, i.e. 1/70) the
# scale is 70. Close enough to 75 to look plausible and wrong enough to drift, so
# nothing measured in one game may be assumed to carry to the other.
_VIT_MAX_BY_GAME = {'Halo 1': 75.0, 'Halo 2': 70.0}

# Regeneration plays a pulsing effect so the ability is legible -- essential in H2,
# which shows no health at all, and clearer than a creeping bar in H1. The effect ids
# are per game (different tag sets entirely) and were picked by testing every
# candidate in-game; see the tables in sprint.hsc / global_scripts.hsc. Only
# self-contained effects show on a player: impact/contact and weapon effects resolve
# against a surface or their own markers and silently draw nothing.
# 'kind'/'every' drive the regeneration pulse; 'ready' is the burst fired when a
# cooldown expires, which is a different shape of cue and wanted a different effect in
# both games. All four ids were chosen by walking candidate ladders in-game.
_FX_BY_GAME = {
    'Halo 1': {'kind': 5, 'every': 10,      # cyborg shield depletion
               'ready': 30, 'ready_n': 3, 'ready_gap': 5},    # jackal shield depletion
    'Halo 2': {'kind': 8, 'every': 45,      # regret teleport
               'ready': 2, 'ready_n': 3, 'ready_gap': 10},    # elite shield recharge
}


def _vit_max(game):
    return _VIT_MAX_BY_GAME.get(str(game).strip(), _VIT_MAX)


def _sprint_null_ref(m, base, roff):
    struct.pack_into('<I', m.data, base + roff + 0, 0xFFFFFFFF)
    struct.pack_into('<I', m.data, base + roff + 12, 0xFFFFFFFF)


def _apply_sprint(m, game, registry, cfg):
    """Tune the pre-built ability mod (flashlight-key abilities, one per player).

    cfg keys, all optional:
      player_abilities  {0: name, 1: name} where name is none/sprint/overshield/
                        regeneration. Falls back to enabled_players/enabled, which
                        mean sprint, so older callers keep working.
      sprint            speed_pct, duration_ticks, cooldown_ticks
      overshield        os_mult, os_duration_ticks, os_cooldown_ticks
      regeneration      medi_percent, medi_duration_ticks, medi_cooldown_ticks

    No-op with a reported skip if the map wasn't built with the toolkit."""
    ref = {'effect': 'Abilities', 'tag': 'matg globals\\globals', 'field': 'ability'}
    gname = str(game).strip()
    is_h2 = _is_h2_map(m)
    # Guard: the map must actually carry the mod. Checked BEFORE any write so a plain
    # map is never touched. Halo 1 is identified by its purpose-built sprint weapon;
    # Halo 2 reuses the stock `unarmed` token, which every map has, so the ability
    # SCRIPT is the tell there instead.
    if is_h2:
        # `ability0` is the current per-player script; `ab_kind` is the older shared one,
        # still accepted so a map deployed before the rewrite keeps working.
        if read_global(m, 'ability0') is None and read_global(m, 'ab_kind') is None:
            return [{**ref, 'ok': True, 'skip': True,
                     'reason': 'no ability script on this map (not built with the mod)'}]
    elif not m.find_tags('weap', _SPRINT_WEAP_BY_GAME.get(gname, _SPRINT_WEAP)):
        return [{**ref, 'ok': True, 'skip': True,
                 'reason': 'no sprint weapon on this map (not built with the mod)'}]
    # Per-player ability. `player_abilities` is authoritative; otherwise fall back to
    # the older enabled_players/enabled (a bool set meaning "sprint").
    pa = cfg.get('player_abilities')
    if pa is None:
        ep = cfg.get('enabled_players')
        if ep is None:
            ep = {0, 1} if cfg.get('enabled') else set()
        pa = {p: ('sprint' if p in set(ep) else 'none') for p in (0, 1)}
    pa = {int(p): (n or 'none') for p, n in pa.items()}
    active = {n for n in pa.values() if n != 'none'}

    # Deployed maps span several script generations, so check that this map's script
    # actually carries what each requested ability needs BEFORE writing anything --
    # enabling regeneration on a map built before vit_max existed would silently
    # ratchet health and shield to full.
    needs = {'regeneration': ('medi_rate', 'vit_max'), 'overshield': ('os_shield',),
             'camo': ('camo_ticks',)}
    camo_tag = _CAMO_TAG_BY_GAME.get(gname, _CAMO_TAG)
    if 'camo' in active and not m.find_tags('eqip', camo_tag):
        return [{**ref, 'ok': True, 'skip': True,
                 'reason': 'camo needs a map built with the camo pickup '
                           '(rebuild with the current toolkit)'}]
    for name in sorted(active):
        missing = [g for g in needs.get(name, ()) if read_global(m, g) is None]
        if missing:
            return [{**ref, 'ok': True, 'skip': True,
                     'reason': '%s needs a map built with the current toolkit '
                               '(missing %s)' % (name, ', '.join(missing))}]

    # Maps built with the multi-ability script carry ability0/ability1 -- BOTH games now.
    # A pre-rebuild map only knows sprint, gated by sprint_enabled0/1 (or one shared
    # sprint_enabled).
    #
    # Halo 2 used to run ONE ability for both players, because the script API has no
    # per-player input: H1 discriminates with unit_get_current_flashlight_state <unit>,
    # and H2 has no such verb -- every player_action_test_* takes no argument. That is
    # lifted by the `p2-vision-trigger` halo2.dll patch, which repoints the unused
    # unit_get_enterable_by_player at player 2's slot of the action bitfield (see
    # sprint_toolkit/h2_dll_patch.py). Maps rebuilt since then carry ability0/ability1
    # like H1; maps deployed before it still carry ab_kind and fall back below.
    chosen = None
    wrote = False
    for p in (0, 1):
        if set_global(m, 'ability%d' % p,
                      _ABILITY_IDS.get(pa.get(p, 'none'), 0)) is not None:
            wrote = True
    if not wrote and is_h2 and read_global(m, 'ab_kind') is not None:
        # Legacy shared-ability map: player 1's pick wins, and player 2's is reported as
        # ignored rather than silently dropped.
        chosen = pa.get(0, 'none')
        if chosen == 'none':
            chosen = pa.get(1, 'none')
        set_global(m, 'ab_kind', _ABILITY_IDS.get(chosen, 0))
        wrote = True
    if not wrote:
        s0 = 1 if pa.get(0) == 'sprint' else 0
        s1 = 1 if pa.get(1) == 'sprint' else 0
        r0 = set_global(m, 'sprint_enabled0', s0)
        r1 = set_global(m, 'sprint_enabled1', s1)
        if r0 is None and r1 is None:
            if set_global(m, 'sprint_enabled', 1 if (s0 or s1) else 0) is None:
                return [{**ref, 'ok': True, 'skip': True,
                         'reason': 'ability script globals missing '
                                   '(map not built with the mod)'}]
        if active - {'sprint'}:
            return [{**ref, 'ok': True, 'skip': True,
                     'reason': 'map predates the powerup abilities -- rebuild it to use '
                               '%s' % ', '.join(sorted(active - {'sprint'}))}]

    # --- tuning, written whenever supplied so a card can tune a shared value --------
    # Regeneration heals a fixed amount PER TICK; the division is done here because
    # dividing by a short global inside HaloScript misbehaved.
    if cfg.get('medi_duration_ticks') is not None:
        set_global(m, 'medi_ticks', max(1, int(cfg['medi_duration_ticks'])))
    if cfg.get('medi_cooldown_ticks') is not None:
        set_global(m, 'medi_cooldown', max(0, int(cfg['medi_cooldown_ticks'])))
    if cfg.get('medi_percent') is not None:
        heal = float(cfg['medi_percent']) / 100.0 * _vit_max(game)
        ticks = cfg.get('medi_duration_ticks') or read_global(m, 'medi_ticks') or 150
        set_global(m, 'medi_heal', heal)
        set_global(m, 'medi_rate', heal / float(max(1, int(ticks))))
    # The write-back scale has to match the unit's true max or regeneration ratchets.
    set_global(m, 'vit_max', _vit_max(game))

    # Regeneration pulse. Rate is user-facing (per game); the effect id falls back to
    # the tested default. Written only when the globals exist, so maps built before the
    # pulse was added still patch cleanly.
    fx = _FX_BY_GAME.get(str(game).strip(), _FX_BY_GAME['Halo 1'])
    if read_global(m, 'fx_every') is not None:
        per_game = cfg.get('regen_fx_every_by_game') or {}
        every = per_game.get(str(game).strip()) or cfg.get('regen_fx_every') or fx['every']
        set_global(m, 'fx_every', max(1, int(every)))
        set_global(m, 'fx_kind', int(cfg.get('regen_fx_kind') or fx['kind']))
        # The ready cue is pointless when the ability returns before it finishes, so
        # suppress it rather than firing into the middle of the effect.
        dur = int(cfg.get('medi_duration_ticks') or read_global(m, 'medi_ticks') or 150)
        cool = int(cfg.get('medi_cooldown_ticks') or read_global(m, 'medi_cooldown') or 0)
        if read_global(m, 'fx_ready') is not None:
            set_global(m, 'fx_ready', fx['ready'] if cool > dur else 0)
            set_global(m, 'fx_ready_n', fx['ready_n'])
            set_global(m, 'fx_ready_gap', fx['ready_gap'])

    # Camo: the real duration is the equipment tag's Powerup Time, mirrored into the
    # script window. Only written when camo is actually in play -- the tag is shared
    # with any stock camo pickups in the level, so an unused ability must not touch it.
    # Gated on camo actually being in play, never on the cfg merely carrying a value:
    # callers pass their defaults every time, and Powerup Time is a VANILLA tag shared
    # with any stock camo pickups in the level.
    if 'camo' in active:
        secs = float(cfg.get('camo_seconds') or _CAMO_SECONDS)
        eq = registry.get('eqip')
        if eq is not None and m.find_tags('eqip', camo_tag):
            m.apply_field('eqip', camo_tag, 'Powerup Time', 'set', secs, eq)
        set_global(m, 'camo_ticks', max(1, int(cfg.get('camo_duration_ticks')
                                               or round(secs * 30))))
        set_global(m, 'camo_cooldown',
                   max(0, int(cfg.get('camo_cooldown_ticks', _CAMO_COOLDOWN_TICKS))))

    if cfg.get('os_mult') is not None:
        set_global(m, 'os_shield', float(cfg['os_mult']) * _OS_SHIELD_BASE)
    if cfg.get('os_duration_ticks') is not None:
        set_global(m, 'os_ticks', max(1, int(cfg['os_duration_ticks'])))
    if cfg.get('os_cooldown_ticks') is not None:
        set_global(m, 'os_cooldown', max(0, int(cfg['os_cooldown_ticks'])))

    set_global(m, 'sprint_ticks', int(cfg.get('duration_ticks', 90)))
    set_global(m, 'sprint_cooldown', int(cfg.get('cooldown_ticks', 60)))

    # A LEGACY H2 map has a single ab_cooldown rather than one per ability, and every
    # *_cooldown above aliases onto it -- so whichever was written last would win by
    # accident. Write the ACTIVE ability's cooldown here, after them all, so it wins on
    # purpose. Rebuilt maps carry the four separate cooldowns and skip this.
    if chosen and chosen != 'none':
        cool = {'sprint': cfg.get('cooldown_ticks', 60),
                'overshield': cfg.get('os_cooldown_ticks'),
                'regeneration': cfg.get('medi_cooldown_ticks'),
                'camo': cfg.get('camo_cooldown_ticks', _CAMO_COOLDOWN_TICKS)}.get(chosen)
        if cool is not None:
            set_global(m, 'ab_cooldown', max(0, int(cool)))

    results = []
    if not active:
        # Nothing enabled: close the gates and leave the map at its vanilla baseline
        # speed (apply_run patches from the .bak baseline, so no speed edits = vanilla).
        results.append({**ref, 'ok': True, 'old': 'ability', 'new': 'off'})
    elif chosen:
        # LEGACY H2 map, built before the per-player rewrite: one selector for both
        # players, so report what actually happens rather than echoing a per-player
        # choice this map cannot honour.
        results.append({**ref, 'effect': chosen.capitalize(), 'ok': True,
                        'old': 'ability', 'new': '%s on both players' % chosen})
        other = [pa.get(p, 'none') for p in (0, 1) if pa.get(p, 'none') not in ('none', chosen)]
        if other:
            results.append({**ref, 'ok': True, 'skip': True,
                            'reason': 'this Halo 2 map predates per-player abilities, so '
                                      'one runs for both players -- %s was not applied '
                                      '(rebuild it to use both)'
                                      % ', '.join(sorted(set(other)))})
    else:
        for p in (0, 1):
            if pa.get(p, 'none') == 'none':
                continue
            results.append({**ref, 'effect': pa[p].capitalize(),
                            'ok': True, 'old': 'ability',
                            'new': '%s on P%d' % (pa[p], p + 1)})
    # The sprint SPEED mechanic is sprint-only: raising global run speed and penalising
    # every real weapon back down. Powerups must leave the baseline alone, so if nobody
    # has sprint we simply don't write it.
    if 'sprint' not in active:
        for cr in cfg.get('card_reports') or []:
            results.append({'ok': True, 'tag': cr.get('tag') or ref['tag'],
                            'effect': cr.get('effect', 'Ability'), 'field': cr.get('field', ''),
                            'old': cr.get('old'), 'new': cr.get('new')})
        return results

    mg, wp = registry.get('matg'), registry.get('weap')
    if mg is None or wp is None:
        return [{**ref, 'ok': False, 'reason': 'matg/weap plugin missing'}]

    mult = max(1.0, cfg.get('speed_pct', 150) / 100.0)
    penalty = 1.0 - (1.0 / mult) if mult > 1.0 else 0.0
    # Global run/sneak speed = sprint speed; a held real weapon penalises back to normal.
    mg_ref = ('matg', 'globals\\globals')
    m.apply_field(*mg_ref, 'Run Forward', 'set', _SPRINT_STOCK_RUN * mult, mg,
                  block='Player Information')
    m.apply_field(*mg_ref, 'Sneak Forward', 'set', _SPRINT_STOCK_SNEAK * mult, mg,
                  block='Player Information')
    for name, _ in m.read_all('weap', '*', 'Forward Movement Penalty', wp):
        if not _sprint_player_held(name):
            continue
        val = 0.0 if name == _SPRINT_WEAP else penalty
        m.apply_field('weap', name, 'Forward Movement Penalty', 'set', val, wp)
    # Sprint weapon: no fast strafing, and empty first person (null the flag FP refs).
    if m.find_tags('weap', _SPRINT_WEAP):
        m.apply_field('weap', _SPRINT_WEAP, 'Sideways Movement Penalty', 'set', 0.5, wp)
        wbase = m.find_tags('weap', _SPRINT_WEAP)[0][1]
        _sprint_null_ref(m, wbase, 0x45C)    # First Person Model
        _sprint_null_ref(m, wbase, 0x46C)    # First Person Animations
    sp = {p for p, n in pa.items() if n == 'sprint'}
    who = 'P1+P2' if sp == {0, 1} else ('P1' if sp == {0} else ('P2' if sp == {1} else '-'))
    state = 'on %s %d%%, %.1fs / %.1fs cd' % (
        who, cfg.get('speed_pct', 150), cfg.get('duration_ticks', 90) / 30.0,
        cfg.get('cooldown_ticks', 60) / 30.0)
    results = [r for r in results if r.get('effect') != 'Sprint']
    results.append({**ref, 'effect': 'Sprint', 'ok': True, 'old': 'sprint', 'new': state})
    # Each drafted tuning card (Speed/Duration/Cooldown) reports its own before→new
    # step, so it reads like a normal field edit in the summary instead of a skip.
    for cr in cfg.get('card_reports') or []:
        results.append({'ok': True, 'tag': cr.get('tag') or ref['tag'],
                        'effect': cr.get('effect', 'Sprint'), 'field': cr.get('field', ''),
                        'old': cr.get('old'), 'new': cr.get('new')})
    return results


def apply_run(map_path, plan, registry, target_difficulty, backup=True, game=None,
              starting=None, weapon_swaps=None, zoom_ui=None, zoom_donor=None,
              from_baseline=True, remove_cutscenes=False, skulls=(),
              equipment_swaps=None, spawn_equipment=None, spawn_weapons=None,
              sprint=None,
              difficulty_baseline=None,
              red_plasma=None, odst_downgrade=None, equipment_ai_drops=False,
              add_respawn_profile=False, extra_squads=None,
              keep_title_hud=False, baseline_root=None, map_subdir=None):
    """Apply a plan to the map. Each plan item: {tag, name, ops:[{field, block,
    difficulty, op_str}]}. `starting` optionally sets the player Starting Profile
    weapons. Returns (results, backup_path). The map is only saved (and a one-time
    .bak made) if at least one write succeeds.

    Patching is idempotent: whenever a .bak (the pristine original) exists, the
    map is rebuilt FROM that baseline rather than compounded onto the live file.
    So re-patching never double-applies, and dropping an effect from the plan
    (e.g. a spent one-map Exhaust) cleanly removes it — the baseline restores the
    bytes and only the remaining effects are re-applied. Pass from_baseline=False
    to instead patch the live file in place (used by the debug single-field
    patch, which must not wipe the other already-applied effects).

    `baseline_root`/`map_subdir` move that pristine copy off the game folder entirely;
    see `baseline_path`. Unset, the baseline stays the sibling `.bak` it has always
    been, so every existing caller keeps its behaviour."""
    bak = Path(baseline_path(map_path, baseline_root, map_subdir))
    baseline = str(bak) if (from_baseline and backup and bak.exists()) else map_path
    m = open_map(baseline, game)
    results = []
    if difficulty_baseline:
        # FIRST of everything: the whole-game dials are the floor the run's own enemy
        # effects then scale up from, so they have to be in place before any op reads a
        # field. Nothing else in the pass depends on them, so ordering costs nothing.
        results.extend(apply_difficulty_baseline(m, registry, target_difficulty,
                                                 difficulty_baseline))
    if weapon_swaps:
        # Scatter picked weapons through the map's placements. Runs BEFORE the ops so
        # each swapped weapon gets its VANILLA rounds (Magazine picks don't apply).
        results.extend(_apply_weapon_swaps(m, game, registry, weapon_swaps))
    if equipment_swaps:
        # Same placement-scatter idea, on the equipment block.
        results.extend(_apply_equipment_swaps(m, str(game).strip(), equipment_swaps))
    # Skulls are whole-map rules, applied BEFORE the per-field ops. Order matters for
    # any skull that zeroes a field a normal effect also touches (Eyepatch vs an
    # aim-assist buff): running the skull first leaves the effect something to act on,
    # whereas running it last would flatten the effect's result to the skull's value.
    for skull in (skulls or ()):
        s = str(skull).strip().lower()
        if s == 'betrayal':
            results.extend(_apply_betrayal(m, str(game).strip(), registry))
        elif s == 'eyepatch':
            results.extend(_apply_eyepatch(m, str(game).strip(), registry))
    # (effect name, tag) of every card for which "not present in this map" is an
    # expected outcome rather than a failure: enemy/boss cards (that enemy doesn't
    # fight here) and the ODST escort mirrors (Data Hive has no olifaunt).
    absent_ok = set()
    for item in plan:
        if not item.get('absent_is_skip'):
            continue
        absent_ok.add((item.get('name'), item.get('tag')))
        # a target may redirect onto another tag; that row is reported under it
        for op in item.get('ops') or []:
            if op.get('tag'):
                absent_ok.add((item.get('name'), op['tag']))
    plan_start = len(results)
    for item in plan:
        if item.get('missing_in_db'):
            # The effect was removed or renamed out of halo.json since this run was
            # drafted, so all we hold is the frozen snapshot taken when it was picked.
            # Its tag/fields may no longer mean what they did — patching from stale
            # data is worse than not patching, so report it as skipped and move on.
            results.append({'effect': item['name'], 'tag': item['tag'], 'field': '',
                            'ok': True, 'skip': True,
                            'reason': 'no longer in halo.json — skipped '
                                      '(remove it from the run, or re-add the effect)'})
            continue
        cls, path = hm.split_tag(item['tag'])
        plugin = registry.get(cls)
        if item.get('init_defaults'):
            # Seed enemies that lack a field/block by default (e.g. Elite grenades)
            # BEFORE the normal ops, so those scale the freshly-set baseline.
            results.extend(_apply_init_defaults(m, item['init_defaults'], registry))
        for op in item.get('ops', []):
            base = {'effect': item['name'], 'tag': item['tag'], 'field': op['field']}
            if op.get('equip_drop'):
                # Brute equipment loadout: the element to edit is picked by which
                # equipment its tagRef points at, which no index/block target can
                # express — hence a dedicated op rather than a plugin field write.
                parsed = hm.parse_operator(op.get('op_str'))
                if not parsed:
                    results.append({**base, 'ok': False, 'reason': 'blank/invalid operator'})
                    continue
                oper, val = parsed
                for r in _apply_equipment_drop(m, str(game).strip(), op['equip_drop'], oper, val):
                    r['effect'] = item['name']
                    results.append(r)
                continue
            if op.get('reload_anim') or op.get('swap_anim'):
                # Halo 3 reload-speed: scale the first-person reload ANIMATION length
                # (these weapons carry no tag-side Reload Time). item['tag'] is the
                # jmad fp-graph pattern; the operator supplies the multiplier.
                parsed = hm.parse_operator(op.get('op_str'))
                if not parsed:
                    results.append({**base, 'ok': False, 'reason': 'blank/invalid operator'})
                    continue
                oper, val = parsed
                mult = hm.OP_FUNCS[oper](1.0, val)   # *0.5 or =0.5 -> 0.5
                import halo3_reload
                # Same machinery, different actions: the swap is `ready` + `put_away`.
                match = (('ready', 'put_away') if op.get('swap_anim') else ('reload',))
                rep = halo3_reload.scale_reload(m, path, mult, game=game, match=match)
                r = {**base}
                if rep.get('ok'):
                    r.update(ok=True, skip=bool(rep.get('skip')),
                             old=('swap anim' if op.get('swap_anim') else 'reload anim'),
                             new=(rep.get('reason') if rep.get('skip')
                                  else f"x{mult:g} ({rep['animations']} anim, {rep['graphs']} graph)"))
                else:
                    r.update(ok=False, reason=rep.get('reason', 'reload scale failed'))
                results.append(r)
                continue
            if op.get('tag'):
                # This target lives on a DIFFERENT tag from the rest of the card, so
                # the write is redirected -- one card can then set a value on a weapon
                # and the same value on its projectile without being split into two
                # cards the player would have to pick separately. Everything after
                # this point is unchanged; only where it lands moves.
                cls, path = hm.split_tag(op['tag'])
                plugin = registry.get(cls)
                base = {**base, 'tag': op['tag']}
            if plugin is None:
                results.append({**base, 'ok': False, 'reason': f'no plugin for {cls}'})
                continue
            if op.get('derived'):
                # Auto-computed field: value = sum of the source fields' CURRENT
                # (post-edit) values, per tag. Ordered after the normal ops, so
                # edits to the sources are already in the in-memory image.
                results.extend(_apply_derived(m, cls, path, item['name'], op, plugin))
                continue
            if op.get('set') is not None:
                # Fixed set: force the field to a constant regardless of magnitude
                # (e.g. an enum enabler like Special-Fire Mode -> Overcharge). The
                # value may be an enum OPTION NAME, resolved via the plugin.
                field = apply_difficulty(op['field'], op, target_difficulty)
                fld = plugin.find(field, op.get('block'), op.get('nth', 0) or 0)
                sval = op['set']
                if isinstance(sval, str):
                    sval = (fld or {}).get('options', {}).get(sval.strip().lower())
                if sval is None:
                    results.append({**base, 'ok': False,
                                    'reason': f"unknown set value {op['set']!r}"})
                    continue
                for r in name_enum_results(
                        m.apply_field(cls, path, field, 'set', float(sval), plugin,
                                      block=op.get('block'), index=op.get('index', 0) or 0,
                                      nth=op.get('nth', 0) or 0), fld):
                    r['effect'] = item['name']
                    results.append(r)
                continue
            parsed = hm.parse_operator(op.get('op_str'))
            if not parsed:
                results.append({**base, 'ok': False, 'reason': 'blank/invalid operator'})
                continue
            oper, val = parsed
            # `negate`/`offset` describe how this game STORES the setting relative to
            # what the magnitude means: meaning = scale * stored + offset. H1 keeps a
            # modifier that is 1 when normal and rises; H2 keeps a damage that is 0
            # when normal and falls, i.e. meaning = -stored + 1. Expressing it as a
            # mapping (rather than flipping the typed number, which only ever worked
            # for + and -) is what makes '*' and '=' agree across the two games: on
            # the base-0 field, '*2' used to multiply 0 and change nothing.
            negate = bool(op.get('negate'))
            scale = -1.0 if negate else 1.0
            offset = float(op.get('offset') or 0.0)
            field = apply_difficulty(op['field'], op, target_difficulty)
            # Optional bounds from halo.json. A probability field is 0..1 whatever
            # the operator says, and a grouped row applies one magnitude to several
            # fields at once, which makes overshoot easier to reach by accident.
            cmin = op.get('min')
            cmax = op.get('max')
            for r in name_enum_results(
                    m.apply_field(cls, path, field, oper, val, plugin,
                                  block=op.get('block'), index=op.get('index', 0) or 0,
                                  nth=op.get('nth', 0) or 0,
                                  scale=scale, offset=offset,
                                  clamp_min=None if cmin is None else float(cmin),
                                  clamp_max=None if cmax is None else float(cmax),
                                  zero_is=op.get('zero_is')),
                    plugin.find(field, op.get('block'), op.get('nth', 0) or 0)):
                r['effect'] = item['name']
                if op.get('redirected_from'):
                    # say where the write actually landed; a Starting Shield card
                    # silently raising health would read as a bug
                    r['inherited_from'] = op['redirected_from']
                if negate or offset:
                    r['negated'] = True     # summary marks the remapped write
                if ((cmin is not None or cmax is not None)
                        and isinstance(r.get('new'), (int, float))
                        and r.get('ok')):
                    r['clamped'] = (cmin, cmax)
                results.append(r)

        # Relations between two of this effect's own fields, held after every op of
        # the effect has landed (see _apply_constraints).
        if item.get('constraints'):
            results.extend(_apply_constraints(m, cls, path, item['name'],
                                              item['constraints'], plugin))

    # A card whose tag simply isn't in this map is not a broken card when the tag was
    # never guaranteed: that enemy doesn't fight on this level, or that escort isn't on
    # it. Kikowani has no Hunters, so the Hunter's fuel cannon (a weap tag under
    # objects\characters, which otherwise reads like a failed player-weapon patch) and
    # every Flood/Elite card reported as failures. Downgrade them to skips so a real
    # failure stays visible in the report.
    if absent_ok:
        for i in range(plan_start, len(results)):
            r = results[i]
            if (not r.get('ok') and r.get('reason') == 'not present in this map'
                    and (r.get('effect'), r.get('tag')) in absent_ok):
                results[i] = {**r, 'ok': True, 'skip': True,
                              'reason': 'not on this level'}

    if extra_squads and str(game).strip() in SECOND_GEN_GAMES:
        # Structural, and deliberately before the respawn profile so both grow-block
        # passes happen together. {squad name: extra actors}.
        for _sq, _n in sorted(extra_squads.items()):
            results.append(_h2_duplicate_squad(m, registry, _sq, int(_n or 0)))

    if add_respawn_profile and str(game).strip() in SECOND_GEN_GAMES:
        # Before the starting-weapon write below, so a profile added here is armed by
        # this same patch instead of only by the next one. Structural (it relocates
        # the profile block to end-of-image), and a no-op on the 13 maps that already
        # ship a respawn profile of their own.
        _rp = _h2_add_respawn_profile(m, registry)
        if _rp is not None:                 # None = the map already has one
            results.append(_rp)

    if starting:
        # After the ops (so any Magazine effect is already in the weap tags),
        # set the player Starting Profile weapons + rounds from the run's picks.
        if starting.get('spawn_instead') and not reach_spawn_ready(m, game):
            # Clearing the profile is only half of placing the weapons, and doing
            # half leaves the player with nothing at all -- worse than either mode
            # on its own. With no markers there is nowhere to place them, so write
            # the profile as usual and say why.
            starting = dict(starting, spawn_instead=False)
            spawn_weapons = None
            results.append({'effect': 'spawned weapons', 'ok': False,
                            'reason': 'no enhancer markers on this map; wrote the '
                                      'starting profile instead'})
        results.extend(_apply_starting_equipment(m, game, registry, starting))

    if spawn_weapons:
        results.extend(_apply_spawn_weapons(m, game, spawn_weapons))
    if spawn_equipment:
        # Halo 3 starting equipment. Structural (it grows the Equipment block by
        # relocating it), so it runs after every value op — but before the zoom UI,
        # which relocates HUD blocks and would otherwise compete for the same slack.
        results.extend(_apply_spawn_equipment(
            m, game, spawn_equipment,
            odst_all_insertions=bool((spawn_equipment or {}).get('all_insertions'))))

    # The Auto Turret reaches a level by TWO routes -- granted in the loadout
    # (spawn_equipment) and scattered through the map's placements by its Map Presence
    # card (equipment_swaps) -- and its driver fights for the Guardians either way. An
    # earlier version keyed only off the loadout, which is the recurring bug in this
    # codebase: fix one path, leave the other. Both are checked here, once, after both
    # have run. Every H3 and ODST map carries the turret's tags (the rebuilds brought
    # them in everywhere), so wherever it can turn up, this can correct it.
    if _run_grants_autoturret(spawn_equipment, equipment_swaps):
        results.extend(_fix_autoturret_team(m, game, registry))

    if zoom_ui:
        # Structural growth LAST: copy a donor scope overlay into each scopeless
        # target weapon's HUD tag. Done after every value op so the relocated HUD
        # block can't disturb them.
        results.extend(_apply_zoom_ui(m, game, zoom_ui, prefer_donor=zoom_donor))

    if keep_title_hud:
        # Keep the HUD up through chapter/cinematic titles. An in-map script edit, so
        # unlike the h1/h2/h3_keep_hud tools it needs no editing kit and no rebuild --
        # which is what makes it usable as a run option at all. Halo 1 and Halo 2
        # report a skip: their scenarios use an older script format.
        import hud_titles
        rep = hud_titles.remove_title_hud_hiding(m, game, _block_base, _scnr_base(m))
        row = {'tag': 'scnr', 'field': 'chapter title HUD',
               'effect': 'Keep HUD during titles'}
        if rep.get('skip'):
            row.update(ok=True, skip=True, reason=rep.get('reason'))
        elif rep.get('ok'):
            row.update(ok=True, skip=(rep.get('removed', 0) == 0), old='hidden',
                       new='%d hide call(s) removed, %d restore(s) kept'
                           % (rep.get('removed', 0), rep.get('kept', 0)))
        else:
            row.update(ok=False, reason=rep.get('reason', 'script edit failed'))
        results.append(row)

    if remove_cutscenes and str(game).strip() in THIRD_GEN_GAMES:
        # Halo 3 opt-in: neutralise the Cortana/Gravemind vision cutscenes on the map
        # (in-place HSC statement-skip). Runs from the pristine baseline like everything
        # else, so it's reversible by turning the option off and re-patching.
        import halo3_cutscene
        rep = halo3_cutscene.remove_cortana_flicker(m)
        r = {'tag': 'scnr', 'field': 'Cortana/Gravemind cutscenes',
             'effect': 'Remove Halo 3 cutscenes'}
        if rep.get('ok'):
            r.update(ok=True, skip=(rep['edits'] == 0),
                     old='present', new=f"removed ({rep['removed_exprs']} exprs)")
        elif rep.get('reason') == 'no cutscene recipe for this map':
            r.update(ok=True, skip=True, reason=rep['reason'])   # H3 map w/o cutscenes: N/A
        else:
            r.update(ok=False, reason=rep.get('reason', 'cutscene removal failed'))
        results.append(r)

    if sprint:
        # Sprint tuning (speed + duration/cooldown/enable). Whole-map, value-only,
        # so order among the structural passes doesn't matter — do it last.
        results.extend(_apply_sprint(m, game, registry, sprint))
    if odst_downgrade is not None:
        # Placement rewrite, so it belongs with the structural passes rather than the
        # value ops. `keep` is the variants a player actually drafted.
        results.extend(apply_odst_downgrade(m, odst_downgrade))
    if equipment_ai_drops:
        # Whole-tag flag flip, independent of the value ops, so order does not matter.
        results.extend(apply_equipment_ai_drops(m, game))
    if red_plasma:
        # ODST only. After the per-field ops so it composes on top of whatever the
        # run patched onto the plasma rifle, rather than being overwritten by it.
        results.extend(apply_red_plasma_as_brute(m, registry, red_plasma))

    backup_path = None
    if any(r.get('ok') and not r.get('skip') for r in results):
        if backup:
            bp = Path(baseline_path(map_path, baseline_root, map_subdir))
            if not bp.exists():                     # keep the pristine original
                bp.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(map_path, bp)
            backup_path = str(bp)
        m.save(map_path)
    return results, backup_path
