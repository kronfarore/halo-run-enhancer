"""reach_census.py -- read what a Halo: Reach campaign map ACTUALLY contains.

Built to replace halo.json's Reach mission lists, which shipped as copies of Halo 3
maps and were wrong in both directions -- they gave Winter Contingency Brutes, Buggers,
Hunters, Engineers and Bubble Shields (it has none of those; its Covenant are Grunts,
Jackals, Skirmishers and Elites) and omitted the DMR, needle rifle, plasma repeater and
concussion rifle it does have.

WHAT COUNTS AS EVIDENCE. Not the tag index. m70_bonus carries a `bugger` tag, a
`brute_shot`-era melee tag and plenty else besides; tags arrive as dependencies of
other tags and prove nothing about what spawns. The scenario's PALETTES are the right
level -- a palette entry exists because the scenario is set up to spawn that tag.
(Buggers turn out to be real in Reach, on m35/m52/m70/m70_bonus, but the palette is
what establishes that, not the tag.)

Placement is reported alongside but is NOT the bar for weapons: on m10 only 4 of 13
palette weapons are placed as pickups, and the other 9 -- plasma pistol, needle rifle,
needler, energy sword, sniper, concussion rifle, plasma repeater, plasma rifle and
Jorge's turret -- are carried by AI and drop when they die.

For AI species the Character Palette is used rather than the Biped Palette: `char`
tags name the actual species-and-rank set (elite_ultra, grunt_specops, skirmisher),
while the biped palette holds only the handful of bipeds placed directly.

Grenades come from the characters, not the equipment palette. That palette holds only
placed pickups, and Winter Contingency places frags but no plasmas -- yet five of its
characters carry Covenant Plasma. Reading it from the palette alone would have listed
frags only, on nearly every map in the game.

    python sprint_toolkit/reach_census.py                  # per-map summary
    python sprint_toolkit/reach_census.py --map m10 -v     # one map, every tag path
    python sprint_toolkit/reach_census.py --union          # distinct tags, campaign-wide
    python sprint_toolkit/reach_census.py --lists          # the halo.json mission fields
    python sprint_toolkit/reach_census.py --unmapped       # palette tags no table claims
    python sprint_toolkit/reach_census.py --json out.json
"""

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import halo_patch                                    # noqa: E402

ROOT = os.environ.get(
    'MCC_ROOT',
    r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection")
PLUGINS = os.environ.get(
    'ASSEMBLY_PLUGINS',
    r"C:\Program Files (x86)\Steam\steamapps\common\HCEEK"
    r"\Assembly-1-2023-11-29-1702446457\Plugins")
MAPS = os.path.join(ROOT, 'haloreach', 'maps')
GAME = 'Halo Reach'

# The campaign, in story order. m05 is the intro and m70_a a sub-map of The Pillar of
# Autumn; neither is a mission, and neither is in halo.json.
CAMPAIGN = ['m10', 'm20', 'm30', 'm35', 'm45', 'm50', 'm52', 'm60', 'm70', 'm70_bonus']

# MCC first, matching CONFIG['plugin_subdirs_by_game']. This order is load-bearing:
# ReachMCC's scenario blocks sit 0x14 lower than the 360-era Reach plugin's (Weapon
# Palette 0x168 vs 0x17C), so reading an MCC map with the Reach layout silently
# resolves every palette to zero entries rather than failing.
PLUGIN_SUBDIRS = ('ReachMCC', 'Reach')

# (key, palette block, placement block). Placement is informational only.
CLASSES = [
    ('weapon',    'Weapon Palette',    'Weapons'),
    ('equipment', 'Equipment Palette', 'Equipment'),
    ('vehicle',   'Vehicle Palette',   'Vehicles'),
    ('character', 'Character Palette', None),
    ('biped',     'Biped Palette',     'Bipeds'),
    ('giant',     'Giant Palette',     'Giants'),
]
TAGREF_IDENT = 0xC          # datum index inside a 0x10 tagRef
PALETTE_INDEX = 0x0         # int16 index into the palette, at the head of a placement

# char tag: Grenades Properties block, and the Grenade Type enum inside an element.
# There is no ReachMCC/char.xml, so these come from the 360-era Reach plugin; they are
# confirmed against the maps rather than assumed (every campaign map yields a sane
# Human Fragmentation / Covenant Plasma mix and nothing out of range).
CHAR_GRENADES = (0x204, 0x3C)
CHAR_GRENADE_TYPE = 0x4
GRENADE_TYPES = {0: 'Frag Grenade', 1: 'Plasma Grenade'}


def _plugin_path(group):
    for sub in PLUGIN_SUBDIRS:
        p = os.path.join(PLUGINS, sub, group + '.xml')
        if os.path.isfile(p):
            return p
    return None


def plugin_blocks(group='scnr'):
    """{block name: (offset, elementSize)} for a tag's top-level blocks."""
    p = _plugin_path(group)
    if not p:
        raise SystemExit('no Reach %s plugin under %s' % (group, PLUGINS))
    out = {}
    for ch in ET.parse(p).getroot():
        name, off = ch.get('name'), ch.get('offset')
        if name and off and ch.tag.lower() == 'tagblock':
            out[name] = (int(off, 16), int(ch.get('elementSize', '0'), 16))
    return out


class Census:
    def __init__(self, name):
        self.name = name
        self.map = halo_patch.open_map(os.path.join(MAPS, name + '.map'), GAME)
        self.blocks = plugin_blocks()
        scnr = self.map.scenario_tag()
        if not scnr or scnr['base'] is None:
            raise SystemExit('%s: no scenario tag' % name)
        self.base = scnr['base']
        self.scenario_name = self.map.scenario_name

    def _block(self, block_name):
        """(array file offset, count, element size) for a top-level scenario block."""
        if not block_name or block_name not in self.blocks:
            return None, 0, 0
        off, size = self.blocks[block_name]
        count = self.map.i32(self.base + off)
        arr = self.map.data2off(self.map.u32(self.base + off + 4))
        if arr is None or count <= 0:
            return None, 0, size
        return arr, count, size

    def palette(self, block_name):
        """Palette slot -> tag name (None where the slot is empty/unresolved)."""
        arr, count, size = self._block(block_name)
        out = []
        for i in range(count):
            ident = self.map.u32(arr + i * size + TAGREF_IDENT)
            t = self.map.tag(ident & 0xFFFF) if ident != 0xFFFFFFFF else None
            out.append(t['name'] if t and t['name'] else None)
        return out

    def placed_slots(self, block_name):
        """Palette slots that at least one placement record points at."""
        arr, count, size = self._block(block_name)
        hits = set()
        for i in range(count):
            hits.add(self.map.i16(arr + i * size + PALETTE_INDEX))
        hits.discard(-1)
        return hits

    def ai_grenade_types(self):
        """Grenade Type enum values used by the characters in this map's palette.

        The equipment palette alone badly undercounts grenades: it holds only what is
        PLACED as a pickup, and most grenades in Reach come off dead enemies. Winter
        Contingency places frags but no plasmas, yet five of its characters carry
        Covenant Plasma -- listing frags only would have been wrong on every map.
        """
        pal = set(self.palette('Character Palette'))
        off, esz = CHAR_GRENADES
        out = set()
        for t in self.map.tags:
            if t['class'] != 'char' or t['base'] is None or t['name'] not in pal:
                continue
            n = self.map.i32(t['base'] + off)
            p = self.map.data2off(self.map.u32(t['base'] + off + 4))
            if p is None or not (0 < n < 32):
                continue
            for k in range(n):
                out.add(self.map.i16(p + k * esz + CHAR_GRENADE_TYPE))
        return out


def collect(name):
    c = Census(name)
    rec = {'_scenario': c.scenario_name}
    for key, pal_block, place_block in CLASSES:
        pal = c.palette(pal_block)
        placed = c.placed_slots(place_block) if place_block else set()
        rec[key] = {
            'palette': [p for p in pal if p],
            'placed': sorted({pal[i] for i in placed
                              if 0 <= i < len(pal) and pal[i]}),
        }
    rec['ai_grenades'] = sorted(c.ai_grenade_types())
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--map', action='append', help='map basename (repeatable)')
    ap.add_argument('--json', help='write the full census to this file')
    ap.add_argument('--union', action='store_true',
                    help='list distinct tags across every map, with the maps holding them')
    ap.add_argument('-v', '--verbose', action='store_true',
                    help='list every tag path, not just counts')
    ap.add_argument('--lists', action='store_true',
                    help='emit the halo.json mission fields for each map')
    ap.add_argument('--unmapped', action='store_true',
                    help='show every palette tag no name table claims')
    a = ap.parse_args()
    names = a.map or CAMPAIGN
    all_out = {nm: collect(nm) for nm in names}

    if a.lists or a.unmapped:
        leftovers = []
        for nm in names:
            ml = mission_lists(all_out[nm])
            leftovers += [(nm,) + u for u in ml.pop('_unmapped')]
            if a.lists:
                print("=== %s" % nm)
                for k in ('enemies', 'boss', 'weapons', 'grenades', 'equipment', 'turret'):
                    if k in ml:
                        v = ml[k]
                        if isinstance(v, list):
                            tagged = [('%s*' % x if x in NEW_VOCAB else x) for x in v]
                            print("   %-10s %s" % (k, ', '.join(tagged)))
                        else:
                            print("   %-10s %s" % (k, v))
        if a.unmapped:
            print("\n=== palette tags no name table claims (%d)" % len(leftovers))
            for nm, kind, tag in sorted(set(leftovers), key=lambda x: (x[1], x[2])):
                print("   %-10s %-10s %s" % (nm, kind, tag))
        if a.lists:
            print("\n* = no halo.json modifier/equipment entry yet (inert until added)")
        return

    if a.union:
        for key, _, _ in CLASSES:
            seen = {}
            for nm in names:
                for t in all_out[nm][key]['palette']:
                    seen.setdefault(t, []).append(nm)
            print("=== %s (%d distinct)" % (key, len(seen)))
            for t in sorted(seen):
                print("   %-72s %s" % (t, ' '.join(seen[t])))
    else:
        for nm in names:
            rec = all_out[nm]
            print("=== %s (%s)" % (nm, rec['_scenario']))
            for key, _, _ in CLASSES:
                r = rec[key]
                print("   %-10s palette=%-4d placed=%d"
                      % (key, len(r['palette']), len(r['placed'])))
                if a.verbose:
                    pl = set(r['placed'])
                    for n in r['palette']:
                        print("        %s %s" % ('PLACED' if n in pl else '  ....', n))
    if a.json:
        with open(a.json, 'w', encoding='utf-8') as f:
            json.dump(all_out, f, indent=1)
        print("\nwrote %s" % a.json)




# ---------------------------------------------------------------- halo.json names
#
# Tag path -> the name halo.json uses. Patterns are matched as SUBSTRINGS of the tag
# path with forward slashes (tag names are normalised first), longest pattern wins.
# Forward slashes are not cosmetic: writing these with backslashes makes every entry
# an escape-sequence hazard (`\a` is BEL), and the normalisation removes that entirely.
# Longest-wins is what keeps `jackal/ai/skirmisher` from being filed as a Jackal.
#
# Names marked NEW have no entry in halo.json's vocabulary yet (Specific Weapon
# Modifier / Specific Enemy modifier / Equipment). They are written into the mission
# lists anyway: a name with no modifier entry is silently dropped from the offer pool
# by ModifierDatabase.get_level_weapons, so it is inert rather than harmful, and the
# list stays a truthful record of the map. Substituting a near-neighbour that DOES
# have an entry (Drop Shield -> "Bubble Shield") would be worse -- it would look like
# it worked while patching a Halo 3 tag Reach does not have.

ENEMIES = [
    ('characters/jackal/ai/skirmisher', 'Skirmisher'),      # NEW
    ('characters/brute/ai/brute_chieftain', None),          # boss, handled apart
    ('characters/elite/', 'Elite'),
    ('characters/grunt/', 'Grunt'),
    ('characters/jackal/', 'Jackal'),
    ('characters/brute/', 'Brute'),
    ('characters/hunter/', 'Hunter'),
    ('characters/bugger/', 'Bugger'),
    ('characters/engineer/', 'Engineer'),
]
# Characters that are allies, ambient life or AI scaffolding rather than enemies.
NOT_ENEMIES = ('characters/marine', 'characters/spartans', 'characters/civilian',
               'characters/null/', 'characters/ambient_life', 'characters/mule')
BOSSES = [('characters/brute/ai/brute_chieftain', 'Brute Chieftain')]

WEAPONS = [
    ('weapons/rifle/assault_rifle', 'Assault Rifle'),
    ('weapons/pistol/magnum', 'Magnum'),                    # alias -> "Pistol"
    ('weapons/pistol/plasma_pistol', 'Plasma Pistol'),
    ('weapons/pistol/needler', 'Needler'),
    ('weapons/rifle/plasma_rifle', 'Plasma Rifle'),
    ('weapons/rifle/sniper_rifle', 'Sniper Rifle'),         # incl. Jun's variant
    ('weapons/rifle/shotgun', 'Shotgun'),
    ('weapons/rifle/spike_rifle', 'Spike Rifle'),
    ('weapons/support_high/rocket_launcher', 'Rocket Launcher'),
    ('weapons/support_high/flak_cannon', 'Flak Cannon'),
    ('weapons/support_high/spartan_laser', 'Spartan Laser'),
    ('weapons/melee/energy_sword', 'Energy Blade'),
    ('weapons/melee/gravity_hammer', 'Gravity Hammer'),
    ('weapons/rifle/dmr', 'DMR'),                           # NEW
    ('weapons/rifle/needle_rifle', 'Needle Rifle'),         # NEW
    ('weapons/rifle/plasma_repeater', 'Plasma Repeater'),   # NEW
    ('weapons/rifle/concussion_rifle', 'Concussion Rifle'), # NEW
    ('weapons/rifle/focus_rifle', 'Focus Rifle'),           # NEW
    ('weapons/rifle/grenade_launcher', 'Grenade Launcher'), # NEW
    ('weapons/support_high/plasma_launcher', 'Plasma Launcher'),  # NEW
    ('weapons/pistol/target_laser', 'Target Locator'),      # NEW
]
GRENADES = [
    ('weapons/grenade/frag_grenade', 'Frag Grenade'),
    ('weapons/grenade/plasma_grenade', 'Plasma Grenade'),
]
EQUIPMENT = [
    ('equipment/armor_lockup', 'Armor Lock'),               # NEW
    ('equipment/drop_shield', 'Drop Shield'),               # NEW
    ('equipment/sprint', 'Sprint'),                         # NEW
    ('equipment/jet_pack', 'Jet Pack'),                     # NEW
    ('equipment/hologram', 'Hologram'),                     # NEW
    ('equipment/active_camouflage', 'Active Camouflage'),   # NEW
    ('equipment/health_pack', 'Health Pack'),               # NEW
]
# Mounted guns the player can actually use. The vehicle palette also holds one-off
# emplacements (anti_air_cannon, anti_infantry_turret, bfg, frigate_turret,
# mac_15cm, corvette_cannon) that are set pieces or scripted props rather than
# turrets a run can hand out, so they are deliberately left out rather than invented
# into the vocabulary. `--unmapped` lists them so the choice stays visible.
TURRETS = [
    ('weapons/turret/machinegun_turret_jorge', 'Machine Gun'),
    ('vehicles/human/turrets/machinegun/machinegun', 'Machine Gun'),
    ('turrets/plasma_turret', 'Plasma Cannon'),
    ('turrets/shade', 'Shade'),                             # NEW
]
# Ammo/gear pickups that are not player equipment and are not meant to be listed.
IGNORE_EQUIPMENT = ('gear/human/military',)

# Names halo.json has no modifier/equipment entry for yet.
NEW_VOCAB = {'Skirmisher', 'DMR', 'Needle Rifle', 'Plasma Repeater', 'Concussion Rifle',
             'Focus Rifle', 'Grenade Launcher', 'Plasma Launcher', 'Target Locator',
             'Armor Lock', 'Drop Shield', 'Sprint', 'Jet Pack', 'Hologram',
             'Active Camouflage', 'Health Pack', 'Shade'}


def _norm(tag):
    return (tag or '').replace('\\', '/').lower()


def _match(tag, table):
    """Longest matching pattern wins, so specific beats general."""
    t = _norm(tag)
    for pat, name in sorted(table, key=lambda kv: -len(kv[0])):
        if pat in t:
            return pat, name
    return None


def mission_lists(rec):
    """halo.json mission fields for one map's census, plus what did not map."""
    unmapped = []
    enemies, bosses = set(), set()
    for t in rec['character']['palette']:
        n = _norm(t)
        if any(p in n for p in NOT_ENEMIES):
            continue
        b = _match(t, BOSSES)
        if b:
            bosses.add(b[1])
            continue
        m = _match(t, ENEMIES)
        if m is None:
            unmapped.append(('character', t))
        elif m[1]:
            enemies.add(m[1])

    weapons, turrets = set(), set()
    for t in rec['weapon']['palette']:
        m = _match(t, TURRETS)
        if m:
            turrets.add(m[1])
            continue
        m = _match(t, WEAPONS)
        if m:
            weapons.add(m[1])
        else:
            unmapped.append(('weapon', t))

    grenades, equipment = set(), set()
    for gt in rec.get('ai_grenades', ()):
        if gt in GRENADE_TYPES:
            grenades.add(GRENADE_TYPES[gt])
    for t in rec['equipment']['palette']:
        n = _norm(t)
        if any(p in n for p in IGNORE_EQUIPMENT):
            continue
        m = _match(t, GRENADES)
        if m:
            grenades.add(m[1])
            continue
        m = _match(t, EQUIPMENT)
        if m:
            equipment.add(m[1])
        else:
            unmapped.append(('equipment', t))

    for t in rec['vehicle']['palette']:
        m = _match(t, TURRETS)
        if m:
            turrets.add(m[1])

    out = {'enemies': sorted(enemies)}
    if bosses:
        out['boss'] = sorted(bosses)[0] if len(bosses) == 1 else sorted(bosses)
    out['weapons'] = sorted(weapons)
    out['grenades'] = sorted(grenades)
    if equipment:
        out['equipment'] = sorted(equipment)
    if turrets:
        out['turret'] = sorted(turrets)
    out['_unmapped'] = unmapped
    return out


if __name__ == '__main__':
    main()
