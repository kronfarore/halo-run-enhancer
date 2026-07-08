# halo_patch.py — glue between the roller's selected effects and halo_map.py.
# Collects the effects chosen during a run, resolves each to its Assembly plugin,
# and applies typed operators to the map with a per-insert success/failure report.
# No GUI dependency; safe to unit-test headless.

import json
import shutil
from pathlib import Path

import halo_map as hm


# Games that use the second-generation (Halo 2 MCC) cache format.
SECOND_GEN_GAMES = {'Halo 2'}


def open_map(map_path, game=None):
    """Open a map with the right parser for its game. Second-generation games
    (Halo 2) use `Halo2Map`; everything else uses the Halo 1 `HaloMap`."""
    if str(game).strip() in SECOND_GEN_GAMES:
        import halo2_map
        return halo2_map.Halo2Map(map_path)
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


def collect_effects(rounds):
    """Unique patchable effects from a run's rounds, in first-seen order, each
    with a selection `count`, and a source `group`/`cat` (specific weapon,
    player-general, specific enemy, enemy-general, friend, boss) for display."""
    seen, order = {}, []

    def add(mod, group, cat):
        if not isinstance(mod, dict):
            return
        tag = mod.get('tag')
        if not tag:
            return
        key = (tag, mod.get('name'))
        if key not in seen:
            seen[key] = {'name': mod.get('name'), 'desc': mod.get('desc', ''),
                         'tag': tag, 'targets': list(mod.get('targets') or []),
                         'harder_when': mod.get('harder_when'),
                         'init_defaults': mod.get('init_defaults'),
                         'group': group, 'cat': cat, 'count': 0}
            order.append(key)
        seen[key]['count'] += 1

    for rd in rounds or []:
        for pk in ('player1', 'player2'):
            mod = (rd.get(pk) or {}).get('mod')
            if isinstance(mod, dict):
                add(mod, mod['weapon'] if mod.get('weapon') else 'Player (general)',
                    0 if mod.get('weapon') else 1)
        for k in ('enemy1', 'enemy2'):
            mod = rd.get(k)
            if isinstance(mod, dict):
                add(mod, mod['enemy'] if mod.get('enemy') else 'Enemy (general)',
                    2 if mod.get('enemy') else 3)
        add(rd.get('wildcard'), 'Friend / Wildcard', 4)
        for k in ('boss1', 'boss2'):
            add(rd.get(k), 'Boss', 5)
    return [seen[k] for k in order]


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


def default_map_path(app_dir, map_subdir, mission_id):
    """<MCC root>/<map_subdir>/<mission>.map, MCC root being the tool's parent.
    Falls back to a prefix match (<mission>*.map) so a mission id like '01b'
    resolves to Halo 2's '01b_spacestation.map'."""
    if not map_subdir:
        return ''
    d = Path(app_dir).resolve().parent / map_subdir
    exact = d / f'{mission_id}.map'
    if exact.is_file():
        return str(exact)
    matches = sorted(d.glob(f'{mission_id}*.map'))
    return str(matches[0]) if matches else str(exact)


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


def _apply_derived(m, cls, path, effect_name, op, plugin):
    """Write a derived field (sum of its source fields' current values) into
    every tag matching (cls, path). Needs the per-tag read/write interface of
    the H2 parser; H1 has no derived fields."""
    field, block = op['field'], op.get('block')
    index = op.get('index', 0) or 0
    ref = f"{cls} {path}"
    if not hasattr(m, 'read_tag_field'):
        return [{'effect': effect_name, 'tag': ref, 'field': field,
                 'ok': False, 'reason': 'derived fields are Halo 2 only'}]
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


def _apply_init_defaults(m, spec, registry):
    """One-time seeding of an enemy that lacks a field/block by default (e.g. Elite
    grenades): copy defaults from a `source` tag onto every target variant that
    isn't set yet. Runs BEFORE the effect's normal ops. `spec` (already resolved to
    the active game):
      tag           target variant wildcard (e.g. 'actv characters\\elite\\*')
      source        tag to read defaults from (e.g. Grunt Minor / base Grunt)
      block         (H2) tagblock holding the fields; grown if empty
      grow          (H2) True -> copy source's whole block element into an empty block
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
    scls, spath = hm.split_tag(spec['source'])
    src = m.find_tags(scls, spath)
    if not src:
        return [{'effect': 'init defaults', 'ok': False, 'reason': f'init source {spath} not in map'}]
    src_base = src[0][1]
    block = spec.get('block')

    if spec.get('grow') and block and hasattr(m, 'append_block_element'):
        bf = next((f for f in plugin.fields
                   if f['block_chain'] and f['block_chain'][-1].lower() == block.lower()), None)
        if not bf:
            return [{'effect': 'init defaults', 'ok': False, 'reason': f'block {block} not in plugin'}]
        boff, esize = bf['block_offsets'][-1], bf['block_sizes'][-1]
        if m.i32(src_base + boff) == 0:
            return [{'effect': 'init defaults', 'ok': False, 'reason': 'init source block empty'}]
        src_leaf = m.follow(src_base, [boff], [esize], 0)
        elem = bytes(m.data[src_leaf:src_leaf + esize])
        for tpath, base in m.find_tags(cls, path):
            if m.i32(base + boff) == 0:
                m.append_block_element(base, boff, esize, elem)
                out.append({'effect': 'init defaults', 'tag': f'{cls} {tpath}', 'ok': True,
                            'old': '(empty)', 'new': f'{block} seeded'})
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


def apply_run(map_path, plan, registry, target_difficulty, backup=True, game=None):
    """Apply a plan to the map. Each plan item: {tag, name, ops:[{field, block,
    difficulty, op_str}]}. Returns (results, backup_path). The map is only saved
    (and a one-time .bak made) if at least one write succeeds."""
    m = open_map(map_path, game)
    results = []
    for item in plan:
        cls, path = hm.split_tag(item['tag'])
        plugin = registry.get(cls)
        if item.get('init_defaults'):
            # Seed enemies that lack a field/block by default (e.g. Elite grenades)
            # BEFORE the normal ops, so those scale the freshly-set baseline.
            results.extend(_apply_init_defaults(m, item['init_defaults'], registry))
        for op in item.get('ops', []):
            base = {'effect': item['name'], 'tag': item['tag'], 'field': op['field']}
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
                for r in m.apply_field(cls, path, field, 'set', float(sval), plugin,
                                       block=op.get('block'), index=op.get('index', 0) or 0,
                                       nth=op.get('nth', 0) or 0):
                    r['effect'] = item['name']
                    results.append(r)
                continue
            parsed = hm.parse_operator(op.get('op_str'))
            if not parsed:
                results.append({**base, 'ok': False, 'reason': 'blank/invalid operator'})
                continue
            oper, val = parsed
            negate = bool(op.get('negate'))
            if negate:                                # H2 stores the inverse sign
                val = -val
            field = apply_difficulty(op['field'], op, target_difficulty)
            for r in m.apply_field(cls, path, field, oper, val, plugin,
                                   block=op.get('block'), index=op.get('index', 0) or 0,
                                   nth=op.get('nth', 0) or 0):
                r['effect'] = item['name']
                if negate:
                    r['negated'] = True
                results.append(r)

    backup_path = None
    if any(r.get('ok') for r in results):
        if backup:
            bp = Path(str(map_path) + '.bak')
            if not bp.exists():                     # keep the pristine original
                shutil.copy2(map_path, bp)
            backup_path = str(bp)
        m.save(map_path)
    return results, backup_path
