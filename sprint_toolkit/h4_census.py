"""h4_census.py -- read what a Halo 4 campaign map ACTUALLY contains.

The Halo 4 counterpart of `reach_census.py`, and it changes that tool's evidence rule
on the user's instruction: a thing is listed when the map really PLACES it or really
USES it, not merely when it appears in a palette.

WHY THAT IS BOTH POSSIBLE AND BETTER HERE. Reach had to settle for the palette because
its squads say almost nothing about loadouts. Halo 4's squads say everything: every
Spawn Point carries a Character Type Index, an Initial Weapon Index, an Initial
Secondary Weapon Index, an Initial Equipment Index and a Vehicle Type Index, and every
Designer / Templated Cell carries the same four as little blocks of its own plus a
Grenade Type override. So the scenario states outright which palette slots the mission
fields, and the palette can be read as what it is -- an authoring convenience that
routinely outlives the content it was added for.

It matters. Dawn's palette offers an Elite Zealot, a Jackal Sniper and a Jackal Major;
no squad on the map fields any of the three, and the mission does not have them. Under
the Reach rule all three would have been written into halo.json as though they were
part of the level.

THE FOUR CHANNELS, and what each is trusted for:

  * PLACEMENT (the Weapons / Equipment / Vehicles / Bipeds / Giants blocks) -- a
    pickup or emplacement physically in the level.
  * SQUAD USE -- a palette slot some squad's spawn points or cells actually name.
    This is the channel that covers AI-carried weapons, which was Reach's whole
    reason for preferring palettes, and it covers them exactly rather than broadly.
  * BIPED PLACEMENT, matched back to the character palette by tag name. The Didact is
    the case that requires it: on Midnight he is in the character palette, no squad
    fields him, and he is placed directly as a biped.
  * CHARACTER KIT -- the `char` tag's own Grenades Properties, walked up Parent
    Character. This is the ONLY source for grenades, exactly as in Reach: the
    equipment palette holds placed pickups and undercounts badly.

    Deliberately NOT used for weapons. The parent walk reaches ancestors that declare
    broad AI pools plus every vehicle-mounted gun their gunners use, so it puts a SAW
    and a Fuel Rod Cannon on Dawn and a Rocket Launcher on Midnight, none of which are
    there. `--carried` shows what it would have added.

TWO ENUMS NAMED "Grenade Type", AND THEY DISAGREE. On the `char` tag it is
0 Human Fragmentation / 1 Covenant Plasma / 2 Pulse. On a squad cell it is
0 Default / 1 Frag / 2 Plasma / 3 Pulse -- shifted by one, with 0 meaning "whatever the
character carries" rather than a frag. Reading a cell with the character table would
turn every ordinary squad in the game into a frag-thrower.

Tag paths are matched with FORWARD slashes on purpose (see reach_census.py): with
backslashes every pattern is an escape-sequence hazard, and `\\a` is BEL.

    python sprint_toolkit/h4_census.py                    # per-map summary
    python sprint_toolkit/h4_census.py --map m10_crash -v # one map, every tag path
    python sprint_toolkit/h4_census.py --lists            # the halo.json mission fields
    python sprint_toolkit/h4_census.py --json out.json    # the full census
    python sprint_toolkit/h4_census.py --unmapped         # used tags no table claims
    python sprint_toolkit/h4_census.py --carried          # what the char walk would add
    python sprint_toolkit/h4_census.py --emit             # halo.json Missions block
"""

import argparse
import collections
import json
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import assembly_plugins
import halo_patch                                    # noqa: E402

ROOT = os.environ.get(
    'MCC_ROOT',
    r"C:\Program Files (x86)\Steam\steamapps\common\Halo The Master Chief Collection")
PLUGINS = assembly_plugins.plugins_dir()
MAPS = os.path.join(ROOT, 'halo4', 'maps')
GAME = 'Halo 4'

# The campaign, in story order. m05_prologue and m95_epilogue are the prologue and the
# epilogue -- neither is a mission, and neither is in halo.json.
#
# The keys are the FULL map basenames rather than Reach-style short ids because
# `mission_enemies` and friends are keyed by mission id ALONE, with no game in the key:
# 'm10', 'm30', 'm60' and 'm70' would every one of them collide with Reach's.
CAMPAIGN = [
    ('m10_crash', 'Dawn'),
    ('m020', 'Requiem'),
    ('m30_cryptum', 'Forerunner'),
    ('m40_invasion', 'Infinity'),
    ('m60_rescue', 'Reclaimer'),
    ('m70_liftoff', 'Shutdown'),
    ('m80_delta', 'Composer'),
    ('m90_sacrifice', 'Midnight'),
]

# MCC first, matching CONFIG['plugin_subdirs_by_game']. Load-bearing exactly as in
# Reach: Halo4MCC's scenario blocks sit 0x14 BELOW the 360-era Halo4 plugin's (Weapon
# Palette 0x1BC vs 0x1D0), so reading an MCC map with the 360 layout resolves every
# palette to zero entries instead of failing. There is no Halo4MCC/char.xml, so the
# char offsets below necessarily come from the 360 plugin; they are confirmed against
# the maps rather than assumed.
PLUGIN_SUBDIRS = ('Halo4MCC', 'Halo4')

# (key, palette block, placement block). Placement is evidence here, not a footnote.
CLASSES = [
    ('weapon',    'Weapon Palette',    'Weapons'),
    ('equipment', 'Equipment Palette', 'Equipment'),
    ('vehicle',   'Vehicle Palette',   'Vehicles'),
    ('character', 'Character Palette', None),
    ('biped',     'Biped Palette',     'Bipeds'),
    ('giant',     'Giant Palette',     'Giants'),
]
TAGREF_IDENT = 0xC          # datum index inside a 0x10 tagRef
PALETTE_INDEX = 0x0         # int16 palette index at the head of a placement

# scnr /Squads -- read from the plugin for the block itself, hardcoded below it because
# the plugin exposes the sub-blocks but the enhancer's Plugin.find cannot address a
# palette index inside one.
SPAWN_POINTS = (0x3C, 0x7C)
SPAWN_FIELDS = {'character': 0x2E, 'weapon': 0x30, 'weapon2': 0x32,
                'equipment': 0x34, 'vehicle': 0x36}
CELL_BLOCKS = ((0x54, 0x64), (0x60, 0x64))      # Designer Cells, Templated Cells
CELL_SUB = {'character': (0x0C, 0x8), 'weapon': (0x18, 0x8),
            'weapon2': (0x24, 0x8), 'equipment': (0x30, 0x8)}
CELL_SUB_INDEX = 0x4        # the palette index inside one of those 8-byte elements
CELL_GRENADE = 0x3C
CELL_VEHICLE = 0x3E

# char tag. Reach puts Grenades Properties at 0x204/0x3C; Halo 4 moved it to 0x228 and
# grew the element to 0x40, so the Reach constants read a neighbouring block here.
CHAR_PARENT = 0x4           # Parent Character tagRef
CHAR_GRENADES = (0x228, 0x40)
CHAR_GRENADE_TYPE = 0x4
CHAR_WEAPONS = (0x204, 0xCC, 0x04)      # (block, elem size, tagRef offset in element)
CHAR_EQUIPMENT = (0x258, 0x24, 0x00)
MAX_PARENT_HOPS = 8         # elite_zealot -> elite -> generic is 3; 8 is slack

# The `char` table. 0 and 1 line up with Reach; 2 is new.
GRENADE_TYPES = {0: 'Frag Grenade', 1: 'Plasma Grenade', 2: 'Pulse Grenade'}
# The squad-cell table, which is NOT the same enum. 0 means "leave it to the
# character", so it contributes nothing and is absent here on purpose.
CELL_GRENADE_TYPES = {1: 'Frag Grenade', 2: 'Plasma Grenade', 3: 'Pulse Grenade'}


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
        raise SystemExit('no Halo 4 %s plugin under %s' % (group, PLUGINS))
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

    # --- reflexives ---
    def _at(self, base, off):
        """(array file offset, count) for a reflexive at base+off, or (None, 0)."""
        count = self.map.i32(base + off)
        arr = self.map.data2off(self.map.u32(base + off + 4))
        return (arr, count) if arr is not None and count > 0 else (None, 0)

    def _block(self, block_name):
        if not block_name or block_name not in self.blocks:
            return None, 0, 0
        off, size = self.blocks[block_name]
        arr, count = self._at(self.base, off)
        return arr, count, size

    # --- palettes and placements ---
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
        """Palette slots at least one placement record points at."""
        arr, count, size = self._block(block_name)
        hits = set()
        for i in range(count):
            hits.add(self.map.i16(arr + i * size + PALETTE_INDEX))
        hits.discard(-1)
        return hits

    # --- squads ---
    def squad_use(self):
        """({kind: {palette index}}, {cell grenade type}) over every squad.

        Secondary weapons are folded into 'weapon': a weapon the mission hands an AI
        is in the mission whichever hand it goes in.
        """
        used = collections.defaultdict(set)
        grenades = set()
        off, size = self.blocks['Squads']
        arr, count = self._at(self.base, off)
        for i in range(count):
            squad = arr + i * size
            so, ssize = SPAWN_POINTS
            sarr, scount = self._at(squad, so)
            for j in range(scount):
                e = sarr + j * ssize
                for kind, fo in SPAWN_FIELDS.items():
                    v = self.map.i16(e + fo)
                    if v >= 0:
                        used[kind.rstrip('2')].add(v)
            for co, csize in CELL_BLOCKS:
                carr, ccount = self._at(squad, co)
                for j in range(ccount):
                    e = carr + j * csize
                    for kind, (bo, bsize) in CELL_SUB.items():
                        barr, bcount = self._at(e, bo)
                        for k in range(bcount):
                            v = self.map.i16(barr + k * bsize + CELL_SUB_INDEX)
                            if v >= 0:
                                used[kind.rstrip('2')].add(v)
                    v = self.map.i16(e + CELL_VEHICLE)
                    if v >= 0:
                        used['vehicle'].add(v)
                    grenades.add(self.map.i16(e + CELL_GRENADE))
        return used, {g for g in grenades if g in CELL_GRENADE_TYPES}

    # --- character kit ---
    def _char_tags(self):
        return {t['name']: t for t in self.map.tags
                if t['class'] == 'char' and t['name']}

    def char_kit(self, names):
        """(weapons, equipment, grenade types) the given characters carry.

        Walks Parent Character, because a Halo 4 variant inherits the way a Reach one
        does -- storm_elite_zealot defines almost nothing of its own. Only the grenade
        types are used for the mission lists; the other two are reported by --carried
        so the decision to leave them out stays visible.
        """
        by_name = self._char_tags()
        weapons, equipment, grenades = set(), set(), set()
        for name in names:
            t = by_name.get(name)
            hops = 0
            while t is not None and t['base'] is not None and hops < MAX_PARENT_HOPS:
                hops += 1
                for (bo, bsize, ro), sink in ((CHAR_WEAPONS, weapons),
                                              (CHAR_EQUIPMENT, equipment)):
                    arr, count = self._at(t['base'], bo)
                    for i in range(count):
                        ident = self.map.u32(arr + i * bsize + ro + TAGREF_IDENT)
                        r = self.map.tag(ident & 0xFFFF) if ident != 0xFFFFFFFF else None
                        if r and r['name']:
                            sink.add(r['name'])
                bo, bsize = CHAR_GRENADES
                arr, count = self._at(t['base'], bo)
                for i in range(count):
                    grenades.add(self.map.i16(arr + i * bsize + CHAR_GRENADE_TYPE))
                pid = self.map.u32(t['base'] + CHAR_PARENT + TAGREF_IDENT)
                t = self.map.tag(pid & 0xFFFF) if pid != 0xFFFFFFFF else None
        return weapons, equipment, {g for g in grenades if g in GRENADE_TYPES}


def _basename(tag):
    return (tag or '').replace('\\', '/').rsplit('/', 1)[-1]


def collect(name):
    c = Census(name)
    pal = {key: c.palette(pb) for key, pb, _ in CLASSES}
    placed = {key: {pal[key][i] for i in c.placed_slots(plb)
                    if 0 <= i < len(pal[key]) and pal[key][i]}
              for key, _, plb in CLASSES if plb}
    used, cell_grenades = c.squad_use()

    def by_index(key):
        return {pal[key][i] for i in used[key]
                if 0 <= i < len(pal[key]) and pal[key][i]}

    # A character counts as present when a squad fields it OR its biped is placed
    # directly -- the Didact on Midnight is only ever the latter.
    placed_bipeds = {_basename(t) for t in placed.get('biped', ())}
    characters = by_index('character') | {t for t in pal['character']
                                          if t and _basename(t) in placed_bipeds}
    weapons_carried, equipment_carried, char_grenades = c.char_kit(characters)

    rec = {'_scenario': c.scenario_name}
    for key, _, plb in CLASSES:
        rec[key] = {
            'palette': [t for t in pal[key] if t],
            'placed': sorted(placed.get(key, ())),
            'squad': sorted(by_index(key)),
        }
    rec['character']['used'] = sorted(characters)
    rec['carried'] = {'weapon': sorted(weapons_carried),
                      'equipment': sorted(equipment_carried)}
    rec['grenade_types'] = sorted(char_grenades)
    rec['cell_grenades'] = sorted(cell_grenades)
    # Which detached turret weapons exist in this map at all. Deliberately the TAG
    # INDEX rather than the weapon palette: the detached variant is what the player
    # ends up holding after ripping the gun off, and it is spawned by the engine on
    # detach, so it need not be in a palette or placed anywhere.
    rec['detachable'] = sorted({pat for _, _, pat in TURRETS
                               if any(pat in _norm(t['name'])
                                      for t in c.map.tags
                                      if t['class'] == 'weap' and t['name'])})
    return rec


# ---------------------------------------------------------------- halo.json names
#
# Tag path -> the name halo.json uses, matched as a SUBSTRING of the path with forward
# slashes, longest pattern winning. Patterns name the FOLDER wherever possible
# (`weapons/rifle/storm_forerunner_smg/`) rather than the leaf, because Halo 4 keeps a
# weapon's variants beside it -- `_npc`, `_pve`, `_pawnhead`, `_knight`, `_m40` -- and
# they are the same weapon. That folds them in automatically, which is the rule this
# project settled on for Reach: where a tag names several paths, keep the ones that
# exist.
#
# Names marked NEW have no entry in halo.json's vocabulary yet. They are written into
# the mission lists anyway: a name with no modifier entry is silently dropped from the
# offer pool by ModifierDatabase.get_level_weapons, so it is inert rather than
# harmful, and the list stays a truthful record of the map.

ENEMIES = [
    ('characters/storm_knight/', 'Knight'),                 # NEW
    ('characters/storm_pawn/', 'Crawler'),                  # NEW
    ('characters/storm_bishop/', 'Watcher'),                # NEW
    ('characters/storm_elite/', 'Elite'),
    ('characters/storm_grunt/', 'Grunt'),
    ('characters/storm_jackal/', 'Jackal'),
    ('characters/storm_hunter/', 'Hunter'),
    ('characters/storm_sentinel/', 'Sentinel'),
]
# Allies, civilians, story characters and AI scaffolding. `null_*` are the engine's
# placeholder drivers and turret gunners -- they are a seat, not a species.
NOT_ENEMIES = ('characters/null/', 'characters/storm_marine',
               'characters/storm_spartans_ai', 'characters/storm_civilian_',
               'characters/storm_cortana', 'characters/storm_lasky',
               'characters/storm_didact')

WEAPONS = [
    ('weapons/rifle/storm_assault_rifle/', 'Assault Rifle'),
    ('weapons/rifle/storm_br/', 'Battle Rifle'),
    ('weapons/rifle/storm_dmr/', 'DMR'),
    ('weapons/rifle/storm_shotgun/', 'Shotgun'),
    ('weapons/rifle/storm_sniper_rifle/', 'Sniper Rifle'),
    ('weapons/rifle/storm_lmg/', 'SAW'),                    # NEW
    ('weapons/rifle/storm_rail_gun/', 'Railgun'),           # NEW
    ('weapons/pistol/storm_magnum/', 'Magnum'),             # alias -> "Pistol"
    ('weapons/pistol/storm_sticky_detonator/', 'Sticky Detonator'),   # NEW
    ('weapons/pistol/storm_target_laser/', 'Target Designator'),      # NEW
    ('weapons/support_high/storm_rocket_launcher/', 'Rocket Launcher'),
    ('weapons/support_high/storm_spartan_laser/', 'Spartan Laser'),
    ('weapons/rifle/storm_assault_carbine/', 'Storm Rifle'),          # NEW
    ('weapons/rifle/storm_covenant_carbine/', 'Covenant Carbine'),
    ('weapons/rifle/storm_beam_rifle/', 'Beam Rifle'),
    ('weapons/rifle/storm_concussion_rifle/', 'Concussion Rifle'),
    ('weapons/pistol/storm_needler/', 'Needler'),
    ('weapons/pistol/storm_plasma_pistol/', 'Plasma Pistol'),
    ('weapons/pistol/storm_sentinel_beam/', 'Sentinel Beam'),
    # halo.json has called this weapon family Flak Cannon since Halo 3, whose tag
    # is `flak_cannon` too. Halo 4 renamed the tag, not the gun; a second name for
    # it would inherit none of the cards the family already has.
    ('weapons/support_high/storm_fuel_rod_cannon/', 'Flak Cannon'),
    ('weapons/melee/storm_energy_sword/', 'Energy Blade'),
    ('weapons/melee/storm_gravity_hammer/', 'Gravity Hammer'),
    ('weapons/pistol/storm_stasis_pistol/', 'Boltshot'),              # NEW
    ('weapons/rifle/storm_forerunner_rifle/', 'LightRifle'),          # NEW
    ('weapons/rifle/storm_forerunner_smg/', 'Suppressor'),            # NEW
    ('weapons/rifle/storm_forerunner_sniper_rifle/', 'Binary Rifle'),  # NEW
    ('weapons/rifle/storm_spread_gun/', 'Scattershot'),               # NEW
    ('weapons/support_high/storm_forerunner_incineration_launcher/',
     'Incineration Cannon'),                                          # NEW
]
# Weapons that exist as objects but are not weapons a run can hand out: the Jackal's
# shield arm, the empty-hands tag, and the Crawler Sniper's head gun (a body part).
IGNORE_WEAPONS = ('weapons/melee/jackal_shield/', 'weapons/melee/unarmed/',
                  'characters/storm_pawn/weapons/')

# The player's three grenades, and the authority for that is `globals/grenade_list`
# (a `gggl` tag) rather than a guess from the names: its Grenades block has exactly
# three rows and their Equipment refs are storm_frag_grenade, storm_plasma_grenade and
# **storm_energy_drain_grenade**. `storm_disruption_grenade` was mapped to Pulse here
# first, on the strength of the name and of being squad-assigned on Midnight, and that
# was wrong -- it is not one of the three the player carries.
GRENADES = [
    ('weapons/grenade/storm_frag_grenade/', 'Frag Grenade'),
    ('weapons/grenade/storm_plasma_grenade/', 'Plasma Grenade'),
    ('weapons/grenade/storm_energy_drain_grenade/', 'Pulse Grenade'),   # NEW
]
EQUIPMENT = [
    ('equipment/storm_active_camo/', 'Active Camouflage'),
    ('equipment/storm_active_shield/', 'Hardlight Shield'),     # NEW
    ('equipment/storm_auto_turret/', 'Auto Turret'),   # ODST's name for the same idea
    ('equipment/storm_forerunner_vision/', 'Promethean Vision'),  # NEW
    ('equipment/storm_hologram/', 'Hologram'),
    ('equipment/storm_jet_pack/', 'Jet Pack'),
    ('equipment/storm_thruster_pack/', 'Thruster Pack'),        # NEW
]
# Equipment that is never a player pickup: AI-only gear (only ever squad-assigned,
# never placed) and the scripted story drops.
IGNORE_EQUIPMENT = ('equipment/shield_projector/', 'equipment/story_drops/')

# Mounted guns the player can actually take.
#
# THE TEST IS A DETACHED WEAPON TAG, not the emplacement. A turret only earns a place
# in a run if the player can rip it off its mount and carry it, and Halo 4 says so in
# the tags: a detachable emplacement ships a separate `weapon\...` variant beside it,
# and the engine is explicit enough about the distinction to ship a
# `plasma_turret_mounted_nodetach`. So each row pairs the emplacement with the weapon
# that must ALSO be in the map, and `mission_lists` emits the turret only when both are
# there -- the rule checks itself per map rather than being asserted once here.
#
# The Shade is the case that motivated it (user, 2026-09-07). It is placed on Requiem,
# Infinity and Shutdown, and it is static: its only weapon is
# `storm_shade\weapons\storm_shade_plasma_cannon`, mounted, with no detached variant
# anywhere in the game. It is NOT a turret a run can hand out. Do not re-add it.
#
# Left out for the same reason, all detachless: the Forerunner emplacements
# (anti_infantry_turret, anti_vehicle_turret, tracer_turret) and the set-piece UNSC
# guns (asteroid_gun, unsc_artillery, turret_missile_battery), which are scripted props
# or rail sections. --unmapped lists them so the choice stays visible.
#
# Note the Machine Gun's detached tag does NOT live beside its emplacement the way the
# Plasma Cannon's does -- it is off in `objects/weapons/turret/`.
TURRETS = [
    ('vehicles/human/turrets/machinegun/', 'Machine Gun',
     'weapons/turret/storm_machinegun_turret/'),
    ('vehicles/covenant/turrets/plasma_turret/', 'Plasma Cannon',
     'turrets/plasma_turret/weapon/plasma_turret_detached/'),
]

# Names halo.json has no modifier/equipment entry for yet. Checked against
# `Specific Weapon Modifier`, `Enemy modifiers/Specific Enemy modifier` and
# `Equipment` rather than guessed: Elite, Grunt, Jackal, Hunter, Sentinel, Battle
# Rifle, DMR, Sentinel Beam, Concussion Rifle and Gravity Hammer are all already
# there, and Magnum resolves through the existing alias to Pistol.
NEW_VOCAB = {'Knight', 'Crawler', 'Watcher', 'SAW', 'Railgun',
             'Sticky Detonator', 'Target Designator', 'Storm Rifle', 'Boltshot',
             'LightRifle', 'Suppressor', 'Binary Rifle', 'Scattershot',
             'Incineration Cannon', 'Pulse Grenade', 'Hardlight Shield',
             'Promethean Vision', 'Thruster Pack', 'Shade'}


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

    enemies = set()
    for t in rec['character']['used']:
        n = _norm(t)
        if any(p in n for p in NOT_ENEMIES):
            continue
        m = _match(t, ENEMIES)
        if m is None:
            unmapped.append(('character', t))
        elif m[1]:
            enemies.add(m[1])

    weapons, turrets = set(), set()
    for t in set(rec['weapon']['placed']) | set(rec['weapon']['squad']):
        n = _norm(t)
        if any(p in n for p in IGNORE_WEAPONS):
            continue
        m = _match(t, WEAPONS)
        if m:
            weapons.add(m[1])
        else:
            unmapped.append(('weapon', t))

    grenades, equipment = set(), set()
    for g in rec['grenade_types']:
        grenades.add(GRENADE_TYPES[g])
    for g in rec['cell_grenades']:
        grenades.add(CELL_GRENADE_TYPES[g])
    for t in set(rec['equipment']['placed']) | set(rec['equipment']['squad']):
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

    detachable = set(rec.get('detachable', ()))
    for t in set(rec['vehicle']['placed']) | set(rec['vehicle']['squad']):
        m = _match(t, [(pat, (name, det)) for pat, name, det in TURRETS])
        if m and m[1][1] in detachable:
            turrets.add(m[1][0])
        elif '/turrets/' in _norm(t):
            # Either nothing claims it, or it claims a detached weapon this map does
            # not have -- both mean "not a turret a run can hand out", and both should
            # be visible rather than silently dropped.
            unmapped.append(('turret', t))

    out = {'enemies': sorted(enemies), 'weapons': sorted(weapons),
           'grenades': sorted(grenades)}
    if equipment:
        out['equipment'] = sorted(equipment)
    if turrets:
        out['turrets'] = sorted(turrets)
    out['_unmapped'] = unmapped
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--map', action='append', help='map basename (repeatable)')
    ap.add_argument('--json', help='write the full census to this file')
    ap.add_argument('-v', '--verbose', action='store_true',
                    help='list every tag path, not just counts')
    ap.add_argument('--lists', action='store_true',
                    help='emit the halo.json mission fields for each map')
    ap.add_argument('--unmapped', action='store_true',
                    help='show every USED tag no name table claims')
    ap.add_argument('--carried', action='store_true',
                    help='show what the character-kit walk would have added')
    ap.add_argument('--emit', action='store_true',
                    help='print the halo.json Missions block for Halo 4')
    a = ap.parse_args()

    names = a.map or [m for m, _ in CAMPAIGN]
    titles = dict(CAMPAIGN)
    all_out = {nm: collect(nm) for nm in names}

    if a.emit:
        block = {}
        for nm in names:
            ml = mission_lists(all_out[nm])
            ml.pop('_unmapped')
            block[nm] = {'name': titles.get(nm, nm), **ml}
        print(json.dumps({'Halo 4': block}, indent=2))
        return

    if a.carried:
        for nm in names:
            rec = all_out[nm]
            known = set(rec['weapon']['placed']) | set(rec['weapon']['squad'])
            extra = sorted(set(rec['carried']['weapon']) - known)
            print("=== %s -- %d weapons the char walk would add" % (nm, len(extra)))
            for t in extra:
                print("   %s" % t)
        return

    if a.lists or a.unmapped:
        leftovers = []
        for nm in names:
            ml = mission_lists(all_out[nm])
            leftovers += [(nm,) + u for u in ml.pop('_unmapped')]
            if a.lists:
                print("=== %s (%s)" % (nm, titles.get(nm, '?')))
                for k in ('enemies', 'weapons', 'grenades', 'equipment', 'turrets'):
                    if k in ml:
                        tagged = [('%s*' % x if x in NEW_VOCAB else x) for x in ml[k]]
                        print("   %-10s %s" % (k, ', '.join(tagged)))
        if a.unmapped:
            print("\n=== used tags no name table claims (%d)" % len(set(leftovers)))
            for nm, kind, tag in sorted(set(leftovers), key=lambda x: (x[1], x[2])):
                print("   %-14s %-10s %s" % (nm, kind, tag))
        if a.lists:
            print("\n* = no halo.json modifier/equipment entry yet (inert until added)")
        return

    for nm in names:
        rec = all_out[nm]
        print("=== %s (%s)" % (nm, rec['_scenario']))
        for key, _, plb in CLASSES:
            r = rec[key]
            extra = (' used=%d' % len(r['used'])) if 'used' in r else ''
            print("   %-10s palette=%-4d placed=%-4d squad=%-4d%s"
                  % (key, len(r['palette']), len(r['placed']), len(r['squad']), extra))
            if a.verbose:
                live = set(r.get('used') or (set(r['placed']) | set(r['squad'])))
                for n in r['palette']:
                    print("        %s %s" % ('USED  ' if n in live else '  ....', n))

    if a.json:
        with open(a.json, 'w', encoding='utf-8') as f:
            json.dump(all_out, f, indent=1)
        print("\nwrote %s" % a.json)


if __name__ == '__main__':
    main()
