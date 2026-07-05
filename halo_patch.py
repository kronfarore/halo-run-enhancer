# halo_patch.py — glue between the roller's selected effects and halo_map.py.
# Collects the effects chosen during a run, resolves each to its Assembly plugin,
# and applies typed operators to the map with a per-insert success/failure report.
# No GUI dependency; safe to unit-test headless.

import json
import shutil
from pathlib import Path

import halo_map as hm


def open_map(map_path, game=None):
    """Open a map with the right parser for its game. Halo 2 uses the
    second-gen `Halo2Map`; everything else uses the Halo 1 `HaloMap`."""
    if game and '2' in str(game):
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


def preset_key(tag, name, field):
    return f"{tag}||{name}||{field}"


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


def apply_run(map_path, plan, registry, target_difficulty, backup=True, game=None):
    """Apply a plan to the map. Each plan item: {tag, name, ops:[{field, block,
    difficulty, op_str}]}. Returns (results, backup_path). The map is only saved
    (and a one-time .bak made) if at least one write succeeds."""
    m = open_map(map_path, game)
    results = []
    for item in plan:
        cls, path = hm.split_tag(item['tag'])
        plugin = registry.get(cls)
        for op in item.get('ops', []):
            base = {'effect': item['name'], 'tag': item['tag'], 'field': op['field']}
            if plugin is None:
                results.append({**base, 'ok': False, 'reason': f'no plugin for {cls}'})
                continue
            parsed = hm.parse_operator(op.get('op_str'))
            if not parsed:
                results.append({**base, 'ok': False, 'reason': 'blank/invalid operator'})
                continue
            oper, val = parsed
            field = op['field']
            if op.get('difficulty'):
                field = f"{target_difficulty} {field}"
            for r in m.apply_field(cls, path, field, oper, val, plugin,
                                   block=op.get('block'), index=op.get('index', 0) or 0):
                r['effect'] = item['name']
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
