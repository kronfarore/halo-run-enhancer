r"""Fill every ODST level's `dz_enhancer` designer zone with every weapon and equipment piece.

What the user used to do by hand in Guerilla, level by level (h100 was the last one,
2026-11-25): put each weapon / equipment tag in the level's palette, then list every
palette entry in the designer zone `dz_enhancer`. A zone set that loads that zone keeps
all of it resident from the level start -- no placement, no starting profile. Halo 3
proved the route on 110 (2026-10-31: "Palette + dz_enhancer, no placement: PASSED").

The user still does, by hand:
  * add the designer zone `dz_enhancer` to the level,
  * add the enhancer_marker1 / 2 placements,
  * tick `dz_enhancer` in every zone set's Required Designer Zones.
This script refuses a level without `dz_enhancer`, and REPORTS the zone sets that do not
load it and whether the markers are there, so the hand steps can be checked too.

WHAT IT WRITES, per level and kind (weapon, equipment):
  resources\<lvl>.scenario_<kind>_resource   palette: the missing targets APPENDED
  <lvl>.scenario                            the same palette copy (Sapien keeps both
                                            identical; tool stomps the scenario's copy
                                            with the resource's at build time), and
                                            dz_enhancer's <kind> list: the palette
                                            indices it lacks, appended
Appending keeps every existing palette index, so placements and the other designer
zones are untouched. By default dz_enhancer ends up listing the WHOLE palette, as the
user's h100 and sc150 do (ammo and health packs included where a level has them);
`--targets-only` lists just the targets.

WHY A HEADLESS EDIT CAN WORK NOW when three earlier ones (odst_saw_place.py) gathered no
geometry: those wrote a profile slot, a palette entry and a placement, but never a
designer-zone membership, and `tool` gathers a tag's resources per zone. The edits here
are made through the tag's own layout (h3_loosetag.py), so the files are what Guerilla
would save: every count, record and chunk consistent. Verify a build before booting:
h3_chunk_check.py on each new weapon.

Targets are the explicit lists below, not a scan of the kit: a not-done port sitting in
objects\weapons must not leak into every level (Halo 2 lesson, 2026-10-24). Kit weapons
the list leaves out are printed, so a new port shows up as a decision to make.

    python odst_dz_enhancer.py                      # dry run, all nine levels
    python odst_dz_enhancer.py sc150 --write        # one level, backed up to E: first
    python odst_dz_enhancer.py --write --targets-only
    python odst_dz_enhancer.py h100 --check-built   # after the rebuild: every target in
                                                    # the map, with geometry, loadable
                                                    # from the start (H3ODSTEK\maps)

Later pass (enemy variants): KINDS takes 'biped' (scenario + bipeds resource) and
'character' (scenario only) the same way; their target lists are not written yet.
"""
import argparse
import datetime
import io
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL_DIR = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import h3_loosetag as H                                         # noqa: E402

B = '\\'
EK = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'H3ODSTEK')
TAGS = os.path.join(EK, 'tags')
ATLAS = os.path.join(TAGS, 'levels', 'atlas')
LEVELS = ('h100', 'sc100', 'sc110', 'sc120', 'sc130', 'sc140', 'sc150', 'l200', 'l300')
DZ = 'dz_enhancer'
MARKERS = ('enhancer_marker1', 'enhancer_marker2')
BACKUP_ROOT = os.path.join('E:' + os.sep, 'HaloBackups', 'odst_dz_enhancer')
#: kit programs that may hold a scenario open: a save from one of them after this script
#: ran would silently put the old palette back
EDITORS = ('sapien.exe', 'guerilla.exe', 'tool.exe', 'tool_fast.exe')


def _w(*parts):
    return B.join(('objects', 'weapons') + parts)


#: Every weapon a player can hold in ODST, the six ODST cut and the Halo 3 restorations
#: included, and the SAW port. Left out on purpose: multiplayer objectives (flag, ball,
#: bomb, skulls), the vidmaster rocket launcher, the overloaded Spartan Laser, and the
#: turrets' _integrated / _undeployed forms (vehicle and AI copies).
WEAPONS = (
    _w('melee', 'energy_blade', 'energy_blade'),
    _w('melee', 'gravity_hammer', 'gravity_hammer'),
    _w('pistol', 'automag', 'automag'),
    _w('pistol', 'excavator', 'excavator'),                     # the Mauler
    _w('pistol', 'magnum', 'magnum'),
    _w('pistol', 'needler', 'needler'),
    _w('pistol', 'plasma_pistol', 'plasma_pistol'),
    _w('rifle', 'assault_rifle', 'assault_rifle'),
    _w('rifle', 'battle_rifle', 'battle_rifle'),
    _w('rifle', 'beam_rifle', 'beam_rifle'),
    _w('rifle', 'covenant_carbine', 'covenant_carbine'),
    _w('rifle', 'plasma_rifle', 'plasma_rifle'),
    _w('rifle', 'plasma_rifle_red', 'plasma_rifle_red'),
    _w('rifle', 'saw', 'saw'),                                  # port, done in ODST
    _w('rifle', 'shotgun', 'shotgun'),
    _w('rifle', 'smg', 'smg'),
    _w('rifle', 'smg_silenced', 'smg_silenced'),
    _w('rifle', 'sniper_rifle', 'sniper_rifle'),
    _w('rifle', 'spike_rifle', 'spike_rifle'),
    _w('support_high', 'flak_cannon', 'flak_cannon'),           # the Fuel Rod Gun
    _w('support_high', 'rocket_launcher', 'rocket_launcher'),
    _w('support_high', 'spartan_laser', 'spartan_laser'),
    _w('support_low', 'brute_shot', 'brute_shot'),
    _w('support_low', 'sentinel_gun', 'sentinel_gun'),          # the Sentinel Beam
    _w('turret', 'flamethrower', 'flamethrower'),
    _w('turret', 'machinegun_turret', 'machinegun_turret'),
    _w('turret', 'missile_pod', 'missile_pod'),
    _w('turret', 'plasma_cannon', 'plasma_cannon'),
)


def _e(name):
    return B.join(('objects', 'equipment', name, name))


#: The four grenades (each an eqip pickup) and the eleven equipment PICKUPS. The deployed
#: objects (objects\equipment\<name>\...) come in as the pickups' dependencies. Superflare
#: is the pickup `superflare_equipment`, as Halo 3's kit places it; the user's h100 has
#: the deployed `superflare\superflare` in its palette, which stays.
EQUIPMENT = tuple(B.join(('objects', 'weapons', 'grenade', g, g)) for g in (
    'frag_grenade', 'plasma_grenade', 'claymore_grenade', 'firebomb_grenade')) + tuple(
    _e(n) for n in ('autoturret_equipment', 'bubbleshield_equipment', 'gravlift_equipment',
                    'instantcover_equipment', 'invincibility_equipment',
                    'invisibility_equipment', 'jammer_equipment', 'powerdrain_equipment',
                    'regenerator_equipment', 'superflare_equipment', 'tripmine_equipment'))

#: kind -> (tag group, file extension, resource suffix or None, resource palette field,
#:          scenario palette field, dz_enhancer list, targets)
KINDS = {
    'weapon': ('weap', 'weapon', 'weapons', 'weapon palette', 'weapon palette', 'weapon',
               WEAPONS),
    'equipment': ('eqip', 'equipment', 'equipment', 'equipment palette',
                  'equipment palette', 'equipment', EQUIPMENT),
}
ORDER = ('weapon', 'equipment')


def scenario_path(lvl):
    return os.path.join(ATLAS, lvl, lvl + '.scenario')


def resource_path(lvl, suffix):
    return os.path.join(ATLAS, lvl, 'resources', '%s.scenario_%s_resource' % (lvl, suffix))


def _paths(block):
    return [e.subs['name'].ref()[1] for e in block]


def _norm(p):
    return p.lower().replace('/', B)


def missing_from_kit():
    """Targets with no tag file in the kit (a typo, or a port not built yet)."""
    out = []
    for kind in ORDER:
        grp, ext = KINDS[kind][0], KINDS[kind][1]
        for p in KINDS[kind][6]:
            if not os.path.isfile(os.path.join(TAGS, p + '.' + ext)):
                out.append('%s %s' % (grp, p))
    return out


def kit_weapons_left_out():
    """Weapon tags under objects\\weapons the WEAPONS list does not carry."""
    root = os.path.join(TAGS, 'objects', 'weapons')
    have = {_norm(p) for p in WEAPONS}
    out = []
    for d, _dirs, files in os.walk(root):
        for f in files:
            if f.endswith('.weapon'):
                rel = os.path.relpath(os.path.join(d, f[:-len('.weapon')]), TAGS)
                if _norm(rel) not in have:
                    out.append(rel)
    return sorted(out)


def offers_unmatched():
    """halo.json ODST offers whose card tags name none of the targets."""
    try:
        with io.open(os.path.join(TOOL_DIR, 'halo.json'), encoding='utf-8') as fh:
            d = json.load(fh)
    except (OSError, ValueError):
        return ['(halo.json not readable)']
    targets = {_norm(p) for k in ORDER for p in KINDS[k][6]}
    offered = {}
    for mis in d['Missions']['Halo 3: ODST'].values():
        for k in ('weapons', 'turrets', 'equipment', 'grenades'):
            for n in mis.get(k) or []:
                offered[n] = k
    weap = d['Player Modifiers']['Specific Weapon Modifier']
    eq = d.get('Equipment') or {}
    out = []
    for n, k in sorted(offered.items()):
        if k == 'grenades':
            g = n.lower().replace(' ', '_')
            if _norm(B.join(('objects', 'weapons', 'grenade', g, g))) not in targets:
                out.append('%s (%s)' % (n, k))
            continue
        src = eq.get(n) if k == 'equipment' else weap.get(n)
        tags = set()
        for c in (src or {}).values():
            if not isinstance(c, dict):
                continue
            t = c.get('tag')
            vals = [t.get('Halo 3: ODST') or t.get('Halo 3')] if isinstance(t, dict) else [t]
            for v in vals:
                if isinstance(v, str) and v.split(' ', 1)[0] in ('weap', 'eqip'):
                    for part in v.split(' ', 1)[1].split(' & '):
                        tags.add(_norm(part.strip()))
        if n in ('Magnum', 'Auto Magnum', 'Pistol'):
            tags.add(_norm(_w('pistol', 'automag', 'automag')))
        if n in ('SMG', 'Silenced SMG'):
            tags.add(_norm(_w('rifle', 'smg_silenced', 'smg_silenced')))
        if n in ('Plasma Rifle', 'Brute Plasma Rifle'):
            tags.add(_norm(_w('rifle', 'plasma_rifle_red', 'plasma_rifle_red')))
        if not tags & targets:
            out.append('%s (%s)' % (n, k))
    return out


def editors_running():
    try:
        out = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'], capture_output=True,
                             text=True, timeout=30).stdout.lower()
    except (OSError, subprocess.SubprocessError):
        return ['(tasklist failed)']
    return [e for e in EDITORS if '"%s"' % e in out]


class Level(object):
    """One level's scenario + resources, and the plan for them."""

    def __init__(self, lvl, targets_only=False):
        self.lvl = lvl
        self.targets_only = targets_only
        self.scn = H.LooseTag(scenario_path(lvl))
        self.res = {}
        for kind in ORDER:
            self.res[kind] = H.LooseTag(resource_path(lvl, KINDS[kind][2]))
        r = self.scn.root
        self.zones = r['designer zones']
        names = [z.subs['name'].text() for z in self.zones]
        self.dz_index = names.index(DZ) if DZ in names else None
        self.dz = self.zones[self.dz_index] if self.dz_index is not None else None
        zsets = r['zone sets']
        self.zone_sets = [z.subs['name'].text() for z in zsets]
        self.unloaded = []
        # A zone set has TWO masks over the designer zones, required and forbidden, side
        # by side in Guerilla. A forbidden tick keeps the zone out of that zone set; on
        # 2026-11-26 sc150 had dz_enhancer forbidden in all seven and required in none.
        self.forbidden = []
        if self.dz_index is not None:
            for z in zsets:
                if not (z.get('required designer zones') >> self.dz_index) & 1:
                    self.unloaded.append(z.subs['name'].text())
                if (z.get('forbidden designer zones') >> self.dz_index) & 1:
                    self.forbidden.append(z.subs['name'].text())
        # A marker counts only as an EQUIPMENT PLACEMENT carrying the name (what the
        # patcher resolves, placement -> object name). The object-names entry alone says
        # nothing: h100's two have type/datum -1 although both are placed.
        objn = [e.get('name') for e in r['object names']]
        placed = {e.get('name') for e in r['equipment']}
        self.markers = [m for m in MARKERS if m in objn and objn.index(m) in placed]
        self.problems = []
        self.plan = {}

    def make_plan(self):
        for kind in ORDER:
            grp, ext, suffix, rfield, sfield, dzfield, targets = KINDS[kind]
            rp = self.res[kind].root[rfield]
            sp = self.scn.root[sfield]
            rpaths, spaths = _paths(rp), _paths(sp)
            if [_norm(p) for p in rpaths] != [_norm(p) for p in spaths]:
                self.problems.append(
                    '%s palette differs between the scenario (%d) and the resource (%d): '
                    'save the level in Sapien first' % (kind, len(spaths), len(rpaths)))
                continue
            have = [_norm(p) for p in rpaths]
            add = [t for t in targets if _norm(t) not in have]
            final = have + [_norm(t) for t in add]
            if len(final) > rp.max_count:
                self.problems.append('%s palette would hold %d (max %d)'
                                     % (kind, len(final), rp.max_count))
            if self.targets_only:
                want = sorted({final.index(_norm(t)) for t in targets})
            else:
                want = list(range(len(final)))
            cur = []
            if self.dz is not None:
                cur = [e.get('palette index') for e in self.dz.subs[dzfield]]
            dz_add = [i for i in want if i not in cur]
            stray = [i for i in cur if not 0 <= i < len(final)]
            if stray:
                self.problems.append('dz_enhancer %s list names palette indices %s outside '
                                     'the palette' % (kind, stray))
            self.plan[kind] = {'palette': len(rpaths), 'add': add, 'dz': len(cur),
                               'dz_add': dz_add, 'final': len(final)}
        if self.dz is None:
            self.problems.insert(0, 'no designer zone %s: add it (and tick it in every zone '
                                    'set) first' % DZ)
        return self.plan

    def changes(self):
        return sum(len(p['add']) + len(p['dz_add']) for p in self.plan.values())

    def apply(self):
        for kind in ORDER:
            grp, ext, suffix, rfield, sfield, dzfield, targets = KINDS[kind]
            p = self.plan[kind]
            for pal in (self.res[kind].root[rfield], self.scn.root[sfield]):
                for t in p['add']:
                    e = pal.append_copy(pal[0]) if len(pal) else pal.append_new()
                    e.set_ref('name', grp, t)
            blk = self.dz.subs[dzfield]
            for i in p['dz_add']:
                e = blk.append_new()
                e.set('palette index', i)

    def files(self):
        return [self.scn] + [self.res[k] for k in ORDER]

    def verify(self):
        """Re-read the files from disk and check the plan landed."""
        bad = []
        again = Level(self.lvl, self.targets_only)
        for kind in ORDER:
            grp, ext, suffix, rfield, sfield, dzfield, targets = KINDS[kind]
            rp = [_norm(x) for x in _paths(again.res[kind].root[rfield])]
            sp = [_norm(x) for x in _paths(again.scn.root[sfield])]
            if rp != sp:
                bad.append('%s: scenario and resource palettes differ' % kind)
            for t in targets:
                if _norm(t) not in rp:
                    bad.append('%s: %s not in the palette' % (kind, t))
            idx = {e.get('palette index') for e in again.dz.subs[dzfield]}
            want = range(len(rp)) if not self.targets_only else \
                {rp.index(_norm(t)) for t in targets}
            lost = [i for i in want if i not in idx]
            if lost:
                bad.append('%s: dz_enhancer lacks palette indices %s' % (kind, lost))
        return bad


def backup(levels, root):
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    dest = os.path.join(root, stamp)
    for lv in levels:
        d = os.path.join(dest, lv.lvl)
        os.makedirs(d, exist_ok=True)
        for t in lv.files():
            shutil.copy2(t.path, os.path.join(d, os.path.basename(t.path)))
    return dest


#: MCC ODST cache layout, from Assembly's ODSTMCC scnr plugin. NOT its `ODST` plugin --
#: that is the Xbox 360 layout (0x70/0x24, 0x774) and reads zero zone sets on an MCC map.
#: Halo 3 MCC differs again: 0x58/0x28, 0x6E4/0xBC.
SCNR_ZONE_SETS = (0x74, 0x28)
ZS_LOADED_DZ = 0x10                  # Runtime Loaded Designer Zonesets, one bit per zone
SCNR_DESIGNER_ZONES = (0x724, 0xC8)
OBJ_MODEL, HLMT_RENDER = 0x34, 0x0
KIT_MAPS = os.path.join(EK, 'maps')


def check_built(path):
    """Read a BUILT map: is every target in it, with geometry, loadable from the start?

    'From the start' = its tag in the zone tag's GLOBAL set, or in dz_enhancer with every
    zone set loading dz_enhancer. The pool bits are a lead rather than proof
    (h3_zone_pools.py), so the geometry count -- render model (and, for a weapon, its
    first-person animation) owning chunks -- is the half that decides "tool gathered it".
    """
    import contextlib
    sys.path.insert(0, TOOL_DIR)
    import halo_patch as HP                                     # noqa: E402
    import h3_zone_pools as Z                                   # noqa: E402
    import prepare_map as PM                                    # noqa: E402
    with contextlib.redirect_stdout(io.StringIO()):
        m = HP.open_map(path, 'Halo 3: ODST', readonly=True)
    scnr = HP._scnr_base(m)

    def block(off, es):
        n = max(0, m.i32(scnr + off))
        b = HP._block_base(m, scnr + off)
        return [b + i * es for i in range(n)] if b else []

    def sid(v):
        try:
            return m.resolve_stringid(v)
        except Exception:
            return None
    zones = [sid(m.u32(e)) for e in block(*SCNR_DESIGNER_ZONES)]
    di = zones.index(DZ) if DZ in zones else None
    masks = [m.u32(e + ZS_LOADED_DZ) for e in block(*SCNR_ZONE_SETS)]
    unloaded = [i for i, mk in enumerate(masks) if di is None or not mk >> di & 1]
    zb = next((t['base'] for t in m.tags if t.get('class') == 'zone'), None)
    pools = {}
    for label, e in Z.zonesets(m, zb) if zb is not None else []:
        key = ('dz' if label.endswith(' ' + DZ) else
               'global' if label.startswith('GLOBAL') else None)
        if key and key not in pools:
            pools[key] = (Z._pool(m, e, Z.ZS_REQUIRED_TAG_POOL),
                          Z._pool(m, e, Z.ZS_OPTIONAL_TAG_POOL))
    owned = Z.chunks_by_tag(m, zb) if zb is not None else {}

    def inpool(key, row):
        p = pools.get(key)
        return bool(p) and (Z._has(p[0], row) or Z._has(p[1], row))
    rows = {}
    for t in m.tags:
        if t.get('name'):
            rows.setdefault((t.get('class'), _norm(str(t['name']))), t)
    dz_live = di is not None and masks and not unloaded
    items = []
    for kind in ORDER:
        grp = KINDS[kind][0]
        for p in KINDS[kind][6]:
            t = rows.get((grp, _norm(p)))
            rec = {'kind': kind, 'tag': p}
            if t is None:
                rec['verdict'] = 'NOT IN MAP'
                items.append(rec)
                continue
            row = t['index'] & 0xFFFF if 'index' in t else None
            g, z = inpool('global', row), inpool('dz', row)
            if kind == 'weapon':
                mode, jmad = PM.geometry(m, zb, p.rsplit(B, 1)[-1])
                if _norm(p).startswith(_norm(_w('turret')) + B):
                    jmad = None     # carried in third person: no first-person graph
            else:
                mode, jmad = 0, None
                hlmt = m.u32(t['base'] + OBJ_MODEL + 0xC)
                ht = m.tag(hlmt & 0xFFFF) if hlmt != 0xFFFFFFFF else None
                if ht and ht.get('base'):
                    rm = m.u32(ht['base'] + HLMT_RENDER + 0xC)
                    if rm != 0xFFFFFFFF:
                        mode = len(owned.get(rm & 0xFFFF, []))
            if not mode or jmad == 0:
                verdict = 'NO GEOMETRY (mode %d, jmad %s): tool did not gather it' % (mode, jmad)
            elif g or (z and dz_live):
                verdict = 'ok'
            elif z:
                verdict = 'dz_enhancer only, and not every zone set loads it'
            else:
                verdict = 'NOT IN GLOBAL OR dz_enhancer'
            rec.update(global_=g, dz=z, mode=mode, jmad=jmad, verdict=verdict)
            items.append(rec)
    return {'dz_index': di, 'zone_sets': len(masks), 'unloaded': unloaded, 'items': items}


def report_built(lvl, path, r):
    bad = [i for i in r['items'] if i['verdict'] != 'ok']
    print('== %s  %s  (%s)' % (lvl, 'ALL OK' if not bad and not r['unloaded'] else 'PROBLEMS',
                               path))
    if r['dz_index'] is None:
        print('   %s: MISSING in the build' % DZ)
    else:
        print('   %s: zone %d, loaded by %d of %d zone sets'
              % (DZ, r['dz_index'], r['zone_sets'] - len(r['unloaded']), r['zone_sets']))
    for kind in ORDER:
        mine = [i for i in r['items'] if i['kind'] == kind]
        print('   %-9s %d of %d ok' % (kind, sum(i['verdict'] == 'ok' for i in mine), len(mine)))
    for i in bad:
        print('      %-9s %-58s %s' % (i['kind'], i['tag'], i['verdict']))
    return not bad and not r['unloaded']


def report(lv):
    print('== %s' % lv.lvl)
    if lv.dz is None:
        print('   %s: MISSING' % DZ)
    else:
        print('   %s: designer zone %d; zone sets loading it: %d of %d%s'
              % (DZ, lv.dz_index, len(lv.zone_sets) - len(lv.unloaded), len(lv.zone_sets),
                 '' if not lv.unloaded else '  NOT IN: ' + ', '.join(lv.unloaded)))
        if lv.forbidden:
            print('   %s FORBIDDEN in %d zone sets (untick it there): %s'
                  % (DZ, len(lv.forbidden), ', '.join(lv.forbidden)))
    print('   markers (placed equipment): %s' % (', '.join(lv.markers) or 'none') +
          ('' if len(lv.markers) == len(MARKERS) else
           '  (missing %s)' % ', '.join(m for m in MARKERS if m not in lv.markers)))
    for kind in ORDER:
        p = lv.plan.get(kind)
        if not p:
            continue
        print('   %-9s palette %2d -> %2d   dz_enhancer %2d -> %2d'
              % (kind, p['palette'], p['final'], p['dz'], p['dz'] + len(p['dz_add'])))
        for t in p['add']:
            print('      + %s' % t)
    for msg in lv.problems:
        print('   PROBLEM: %s' % msg)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('levels', nargs='*', help='levels (default: all nine)')
    ap.add_argument('--write', action='store_true', help='apply (backs up first)')
    ap.add_argument('--targets-only', action='store_true',
                    help='dz_enhancer lists only the targets, not the whole palette')
    ap.add_argument('--backup-dir', default=BACKUP_ROOT)
    ap.add_argument('--force', action='store_true',
                    help='write even while Sapien / Guerilla / tool is running')
    ap.add_argument('--check-built', nargs='?', const=KIT_MAPS, metavar='DIR',
                    help='instead: audit the BUILT maps in DIR (default the kit maps folder)')
    a = ap.parse_args(argv)
    names = a.levels or list(LEVELS)
    for n in names:
        if n not in LEVELS:
            raise SystemExit('unknown level %r (have %s)' % (n, ', '.join(LEVELS)))
    if a.check_built:
        good = 0
        for n in names:
            p = os.path.join(a.check_built, n + '.map')
            if not os.path.isfile(p):
                print('== %s  no map at %s' % (n, p))
                continue
            good += report_built(n, p, check_built(p))
        return 0 if good == len(names) else 1

    print('kit: %s' % EK)
    gone = missing_from_kit()
    if gone:
        print('TARGETS WITH NO TAG IN THE KIT (fix the lists first):')
        for g in gone:
            print('   %s' % g)
        raise SystemExit(1)
    left = kit_weapons_left_out()
    print('weapon targets %d, equipment targets %d (grenades included)'
          % (len(WEAPONS), len(EQUIPMENT)))
    print('kit weapons NOT targeted (%d): %s' % (len(left), ', '.join(
        os.path.basename(x) for x in left)))
    un = offers_unmatched()
    if un:
        print('halo.json ODST offers with no target tag: %s' % ', '.join(un))

    levels = []
    for n in names:
        lv = Level(n, a.targets_only)
        lv.make_plan()
        report(lv)
        levels.append(lv)

    todo = [lv for lv in levels if lv.dz is not None and not lv.problems and lv.changes()]
    skipped = [lv.lvl for lv in levels if lv.dz is None or lv.problems]
    print()
    print('to write: %s' % (', '.join(lv.lvl for lv in todo) or 'nothing'))
    if skipped:
        print('skipped (see PROBLEM lines): %s' % ', '.join(skipped))
    if not a.write:
        print('dry run -- add --write to apply')
        return 0
    if not todo:
        return 0
    busy = editors_running()
    if busy and not a.force:
        raise SystemExit('refusing to write while %s is running: a save from it would put '
                         'the old palettes back (close it, or --force)' % ', '.join(busy))
    dest = backup(todo, a.backup_dir)
    print('backed up to %s' % dest)
    failed = False
    for lv in todo:
        lv.apply()
        for t in lv.files():
            t.save()
        bad = lv.verify()
        print('%-6s written%s' % (lv.lvl, '' if not bad else '  VERIFY FAILED:'))
        for b in bad:
            print('       %s' % b)
            failed = True
    if not failed:
        print('Next: tick %s in any zone set listed above, then rebuild '
              '(h3_build_map.py, PORT_EK=odst) and check each new weapon with '
              'h3_chunk_check.py before booting.' % DZ)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
