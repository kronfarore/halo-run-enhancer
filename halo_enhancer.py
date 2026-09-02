# halo_enhancer.py - Final version

import copy
import html
import json
import os
import random
import shutil
import sys
import threading
from datetime import datetime
from pathlib import Path
try:
    from PySide6.QtWidgets import *
    from PySide6.QtCore import *
    from PySide6.QtGui import *
except ImportError as e:
    sys.stderr.write(
        "ERROR: PySide6 is required to run Halo Run Enhancer but is not installed.\n"
        "Install the dependencies first:\n"
        "    pip install -r requirements.txt\n"
        f"(import error: {e})\n")
    sys.exit(1)


# Tool version. Convention (user): stay on 0.2.x for the whole Halo-2 era —
# bump only the last component for changes; the middle 2 becomes 3 only when
# support reaches the next Halo game. Stamped into saved runs and patch logs.
VERSION = "0.4.0"


def resource_path(filename):
    """Absolute path to a bundled data file — works as a plain script and as a
    PyInstaller build (onefile unpacks bundled data to sys._MEIPASS)."""
    base = getattr(sys, '_MEIPASS', None) or Path(__file__).resolve().parent
    return str(Path(base) / filename)


def app_data_dir():
    """Writable directory for saved runs: next to the .exe when frozen, else the
    current working directory (preserving the original script behavior)."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def presets_path():
    return app_data_dir() / "magnitude_presets.json"


def load_presets():
    try:
        with open(presets_path(), encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def run_magnitudes(rounds, mission_id, presets=None):
    """The remembered magnitudes belonging to a run's own effects.

    A saved run holds the draft but NOT the numbers typed for it -- those live in
    magnitude_presets.json -- which is why sharing a run meant sending that whole file
    too, overwriting the other player's unrelated values. This pulls out just this
    run's entries so they can travel inside the run file.

    Preset keys are 'tag||name||field||game', so every entry for an effect is matched
    by its 'tag||name||' prefix. That deliberately avoids re-deriving field names
    (per-game dicts, difficulty suffixes, fallbacks), which is where a mismatch would
    silently drop a magnitude."""
    import halo_patch          # imported lazily, as everywhere else in this module
    presets = load_presets() if presets is None else presets
    effects = halo_patch.collect_effects(rounds or [], mission_id)
    # A run is collected UNRESOLVED (the patcher resolves per-game dicts for the game
    # being patched; saving has no single game in hand), so an effect's tag may still
    # be a {game: tag} dict. Take every variant: preset keys end in the game, so the
    # extra prefixes only match that effect's own entries, and the magnitude still
    # travels if the run is later patched for a different game.
    prefixes = []
    for e in effects:
        tag = e.get('tag')
        if not tag:
            continue
        for one in ([tag] if isinstance(tag, str) else list(tag.values())):
            if isinstance(one, str):
                prefixes.append('%s||%s||' % (one, e.get('name')))
    if not prefixes:
        return {}
    return {k: v for k, v in presets.items() if k.startswith(tuple(prefixes))}


def merge_presets(incoming):
    """Merge shared magnitudes into the local presets, keeping every local entry the
    bundle doesn't mention. Returns how many keys were written."""
    if not incoming:
        return 0
    local = load_presets()
    changed = {k: v for k, v in incoming.items() if local.get(k) != v}
    if not changed:
        return 0
    local.update(changed)
    try:
        with open(presets_path(), 'w', encoding='utf-8') as f:
            json.dump(local, f, indent=2, ensure_ascii=False)
    except Exception:
        return 0
    return len(changed)


class _NullWriter:
    """Stand-in for sys.stdout/err in a windowed (--noconsole) build where they
    are None, so diagnostic print() calls never raise."""
    def write(self, *args):
        pass

    def flush(self):
        pass


# Settings that persist across runs (editable in-app), stored next to saves.
SETTINGS_FILE = 'settings.json'

# Gameplay options exposed in the Options menu. These are BOTH global defaults
# (persisted in settings.json) AND snapshotted into each saved run, so loading a
# run restores the options it was played with. Keep this list in sync with
# OptionsDialog and RunState's options round-trip.
RUN_FILE_MARKER = 'halo-run-enhancer'   # stamped into saved runs so loading can validate


def is_valid_run(data):
    """True if `data` looks like one of our saved runs — either it carries the
    format marker, or (older saves without it) it has the run's structural keys."""
    if not isinstance(data, dict):
        return False
    if data.get('format') == RUN_FILE_MARKER:
        return True
    return any(k in data for k in ('phase', 'mission_id', 'rounds', 'selected_pairs'))


OPTION_KEYS = ('target_difficulty', 'remove_single_game_mods', 'remove_boss_mods',
               'new_weapon_chance', 'include_grenades',
               'weapon_choice_negatives', 'special_rate_factor', 'set_starting_weapons',
               'two_player_coop', 'coop_no_starting_weapons', 'null_coop_starting_equipment',
               'zoom_ui_on_scopeless', 'turrets_are_weapons',
               'combine_heretic_hologram', 'remove_h3_cutscenes',
               'ignore_elite_in_h3', 'remove_flood_from_odst',
               'debug_mode', 'card_width', 'card_height',
               'card_width_override', 'card_height_override', 'card_spacing',
               'card_row_margin', 'grenades_need_weapon', 'brute_chieftain_bosses',
               'reach_elite_bosses', 'reach_grunt_ultra_bosses',
               'reach_jackal_sniper_bosses', 'h2_honor_guard_bosses',
               'odst_specops_bosses', 'h3_specops_bosses', 'heroes_are_bosses',
               'h2_sentinel_enforcer_bosses',
               'h3_equipment_in_rolls', 'equipment_need_weapon',
               'auto_new_weapon_abilities', 'auto_new_weapon_duals',
               'auto_new_weapon_upgrades',
               'score_scaling', 'score_step', 'score_cap_mult', 'score_live_push',
               'betrayal_marines_score',
               'death_penalty_scaling', 'death_penalty_per_round',
               'death_penalty_base',
               'difficulty_baseline',
               'odst_red_plasma_as_brute', 'odst_variants_as_base',
               'odst_downgrade_unupgraded', 'odst_shield_into_health',
               'odst_patch_hub', 'odst_pools_from_map',
               'odst_all_starting_profiles', 'odst_ai_equipment_drops',
               'odst_escort_buff', 'odst_equipment_all_insertions',
               'odst_profiles_by_insertion', 'carry_magnitudes_across_games',
               'other_chance', 'other_weights', 'other_hero_enabled',
               'other_exhaust_enabled', 'other_skull_enabled', 'other_ally_enabled',
               'set_starting_equipment', 'equipment_all_selected',
               'h2_add_respawn_profile', 'h2_extra_squads', 'swap_player_loadouts',
               'h3_all_chief_profiles',
               'remove_superseded_vitality_cards',
               'remove_superflare_jammer', 'remove_invincibility_invisibility',
               'denied_equipment_as_enemy_mods', 'weapon_swap_cards',
               'upgrade_inherits_base',
               'hide_tags', 'hide_fields',
               'sprint_feature', 'sprint_start_with', 'sprint_as_card', 'sprint_mod_cards',
               'sprint_need_weapon', 'sprint_speed_pct', 'sprint_duration_s',
               'sprint_cooldown_s',
               'abilities_offered', 'ability_cards_for', 'ability_start_which',
               'overshield_mult', 'regen_percent', 'regen_duration_s',
               'regen_fx_every',
               'camo_duration_s', 'camo_cooldown_s')


class _WheelGuard(QObject):
    """App-wide filter so the mouse wheel doesn't nudge a number field the user is
    only scrolling PAST. A spin box reacts to the wheel only while it holds focus
    (click into it first); otherwise the scroll is redirected to the enclosing
    scroll area, so the options list keeps scrolling and the value is left alone.
    Clicking still focuses normally, so focus-then-scroll to adjust still works."""

    def eventFilter(self, obj, ev):
        if ev.type() != QEvent.Wheel:
            return False
        # The wheel is delivered to whatever sits under the cursor, which for a spin box
        # is usually its internal QLineEdit and for a combo can be its line edit too --
        # matching only the control itself let the event through to the parent, which
        # then changed the value. So walk UP to the owning control.
        ctl, node = None, obj
        while isinstance(node, QWidget):
            if isinstance(node, (QAbstractSpinBox, QComboBox)):
                ctl = node
                break
            if isinstance(node, QAbstractScrollArea):
                break            # reached the scrolling list: not over a field
            node = node.parentWidget()
        if ctl is None or ctl.hasFocus():
            return False         # focus-then-scroll still adjusts, as before
        # Combo boxes need this as much as spin boxes: scrolling past a dropdown would
        # otherwise silently change the selection. An OPEN popup is a separate top-level
        # view, so this never blocks scrolling within the list itself.
        p = ctl.parentWidget()
        while p is not None and not isinstance(p, QAbstractScrollArea):
            p = p.parentWidget()
        if p is not None:
            QApplication.sendEvent(p.viewport(), ev)
        return True              # never let an unfocused field consume the wheel


# Height of one dropdown row — must match the QComboBox item min-height in the app
# stylesheet, since the popup height is computed from it.
COMBO_ROW_PX = 30


def tune_combo(cb, min_chars=14):
    """Make a dropdown show its whole list and its longest label. Qt sizes the popup
    from the closed box, so a short list still ends up scrolling in a sliver; give the
    view an explicit height for the rows it actually has."""
    cb.setMaxVisibleItems(12)
    cb.setSizeAdjustPolicy(QComboBox.AdjustToContents)
    # The wheel must never focus these (spin boxes and combos default to WheelFocus),
    # or scrolling the options list would grab a field and start changing it.
    cb.setFocusPolicy(Qt.StrongFocus)
    fm = cb.fontMetrics()
    widest = max([fm.horizontalAdvance(cb.itemText(i)) for i in range(cb.count())]
                 or [0])
    cb.setMinimumWidth(max(widest, fm.horizontalAdvance('x') * min_chars) + 44)
    view = cb.view()
    if view is not None:
        view.setMinimumWidth(cb.minimumWidth())
        rows = min(cb.count(), cb.maxVisibleItems())
        if rows:
            view.setMinimumHeight(rows * COMBO_ROW_PX + 8)
    return cb


def boss_mods_removed():
    """Boss cards are suppressed when 'Remove boss mods' is set, or when 'Remove
    single-game mods' is set (bosses are unique per game, so they qualify)."""
    return bool(CONFIG.get('remove_boss_mods') or CONFIG.get('remove_single_game_mods'))


def make_boss_mod(pool_mod, boss_name):
    """Stamp a drawn boss-pool mod with the boss it represents. The 'boss' key
    names the card ('☠ BOSS: <name>'); the mod keeps its own 'enemy' key (from
    the DB) as the blacklist source. Single place the boss-card convention lives."""
    return {**pool_mod, 'boss': boss_name}


# Weapons whose scope the zoom-UI copy can source from, per game — real scoped
# weapons (mask bitmaps confirmed) that map to halo.json weapon names. The patcher
# only offers the ones present on the map being patched ("guaranteed on the map").
ZOOM_DONOR_WEAPONS = {
    'Halo 1': ['Sniper Rifle', 'Pistol'],
    'Halo 2': ['Sniper Rifle', 'Beam Rifle', 'Battle Rifle'],
    # H3/ODST copy the scope out of the donor's chud the same way, once _ZOOM_UI knew
    # how their nested widgets are laid out. ODST's Auto Magnum and Silenced SMG are
    # scoped too and make much subtler donors than a sniper scope on a sidearm.
    'Halo 3': ['Sniper Rifle', 'Beam Rifle', 'Battle Rifle', 'Covenant Carbine'],
    'Halo 3: ODST': ['Sniper Rifle', 'Beam Rifle', 'Covenant Carbine',
                     'Auto Magnum', 'Silenced SMG'],
    # Reach's scoped weapons, by measurement: the only five with Magnification Levels
    # above 0 are the sniper rifle, DMR, needle rifle, magnum and rocket launcher.
    # The magnum's 1x is the subtlest donor, as ODST's automag is there.
    'Halo Reach': ['Sniper Rifle', 'DMR', 'Needle Rifle', 'Pistol', 'Rocket Launcher'],
}

# 'zoom_donor' persists the user's chosen scope source per game ({game: weapon}).
# 'mcc_root' is the remembered "Halo The Master Chief Collection" folder that maps are
# found under (per-game subfolder); defaults to the tool's parent when unset.
SETTINGS_KEYS = ('assembly_plugins_dir', 'zoom_donor', 'mcc_root', 'show_new_at_top',
                 'options_dialog_size', 'patcher_dialog_size',
                 'shared_session_dir', 'shared_session_autosave',
                 'vault_dir') + OPTION_KEYS


def mcc_root():
    """The remembered MCC install folder, or the tool's parent as a fallback (works
    for the default <MCC>/tool layout). Every map is resolved under here."""
    return CONFIG.get('mcc_root') or str(Path(__file__).resolve().parent.parent)


def load_settings():
    try:
        with open(app_data_dir() / SETTINGS_FILE, encoding='utf-8') as f:
            data = json.load(f)
        for k in SETTINGS_KEYS:
            if k in data:
                CONFIG[k] = data[k]
    except Exception:
        pass


def save_settings():
    try:
        payload = {k: CONFIG.get(k) for k in SETTINGS_KEYS}
        with open(app_data_dir() / SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# Configuration
CONFIG = {
    "font_size_title": 20,
    "font_size_subtitle": 18,
    "font_size_name": 16,
    "font_size_desc": 14,
    "font_size_small": 12,
    "font_size_button": 17,
    "font_size_weapon": 18,
    
    # Mod/weapon card size. Both dimensions are normally derived from the screen by
    # card_metrics() so every card is the same size and stops resizing with its
    # content; these values only take effect when the matching *_override is on.
    "card_width": 600,
    "card_height": 800,
    "card_width_override": False,
    "card_height_override": False,
    "card_spacing": 20,        # gap between the three cards
    "card_row_margin": 20,     # gap around the row
    "card_wildcard_extra": 250,
    # Appearance: hide the "Tag:" / "Fields:" lines on selection cards.
    "hide_tags": False,
    "hide_fields": False,
    # Debug mode: exposes developer tools (the patcher "＋ field" button and the
    # main-window "ADD MOD" search). Off for normal play.
    "debug_mode": True,

    # RETIRED 2026-08-31, replaced by other_chance + other_weights. Kept only so an
    # older settings.json still loads without a KeyError; nothing reads them.
    "wildcard_chance": 0.1,
    "exhaust_chance": 0.1,
    "new_weapon_chance": 0.0,
    # Scales how often 'special' (escalating-odds) player effects surface; <1 makes
    # them rarer. ~0.67 = about a third less often.
    "special_rate_factor": 0.67,
    # When patching, set the scenario's starting Primary/Secondary Weapon to the
    # players' picked weapons (profiles 0 & 1: single-player + co-op start).
    "set_starting_weapons": True,
    "starting_weapon_profiles": [0, 1],
    # Halo 2 only. Every H2 campaign map ships two Player Starting Profiles --
    # 0 for the initial spawn, 1 for respawning, named outright as such on
    # 03a/03b ("respawn profile") and 07b ("coop respawn") -- except
    # 08b_deltacontrol, which ships exactly one. This adds the missing second
    # profile as a copy of the first, so a co-op death on The Great Journey
    # respawns with the run's weapons like every other level. Structural: it
    # relocates the profile block, so it is worth being able to turn off.
    "h2_add_respawn_profile": True,
    # Halo 3 solo: also write the run's weapons into every other Chief-role
    # starting profile, not just index 0. Crow's Nest hands the player a profile
    # per rally point and applies NONE at level start, so index 0 alone leaves
    # entries unarmed. Scripted weaponless profiles are still skipped.
    "h3_all_chief_profiles": True,
    # Write player 1's loadout where player 2's would go and vice versa — starting
    # weapons, starting equipment and abilities together. Only affects what is
    # PATCHED; the run itself, the cards and the history are untouched. For when
    # the person sitting at player 2 drafted the arsenal player 1 is holding.
    "swap_player_loadouts": False,
    # Drop the cards the real Player Health / Player Shield ones supersede.
    # Starting Health/Shield Modifier write the scenario profile MULTIPLIER and
    # Enemy Damage Reduction is a third way to say the same thing; with the pool
    # itself now editable they mostly muddy the draft. Off by default — they are
    # not broken, just redundant.
    "remove_superseded_vitality_cards": False,
    # Halo 2 only. Extra actors to add to a named AI squad, per mission:
    # {mission id: {squad name: how many MORE than the level ships}}. Halo 2
    # spawns min(difficulty count, starting locations) actors for `ai_place`,
    # so the patch raises both. Ships aimed at the one case it was built for:
    # Tartarus on 08b, where the speedrun tech is to duplicate Johnson so his
    # Sentinel Beam strips the shield faster. 0 = vanilla.
    "h2_extra_squads": {"08b": {"boss_johnson": 0}},
    # Halo 3 only. H3's Player Starting Profile has no equipment field (Reach added
    # one), so the run's picked equipment is granted by APPENDING a placement onto the
    # player's starting location — the item is walked into as the level loads. Vanilla
    # placements are never touched. A piece the level doesn't stock in its palette is
    # added to it (the equipment models ship in every map); only a piece whose tag the
    # map never loads at all is skipped. On vehicle/cinematic starts where nothing can
    # spawn on the exact start point, a per-map anchor drops it at the nearest reachable
    # spot instead. Player 1's lands on spawn 0, player 2's on 1;
    # with 2-player coop off, everything lands on spawn 0. By default only the FIRST
    # equipment each player carries is placed.
    "set_starting_equipment": False,
    # Place EVERY equipment each player carries, not just their first.
    "equipment_all_selected": False,
    "skull_chance": 0.0,                    # RETIRED, see other_weights
    "two_player_coop": True,                # #8: H3 only — P1 plays Chief, P2 plays the Dervish
    "coop_no_starting_weapons": False,      # #1: don't give the coop profile (index 1) the picks
    "null_coop_starting_equipment": False,  # #2: empty the coop profile's starting weapons
    # When a Zoom effect is applied to a weapon that has no vanilla scope (e.g.
    # Brute Shot, Sentinel Beam), copy a scope overlay from a scoped weapon on the
    # map into its HUD so the zoom actually shows a scope. Structurally grows the
    # HUD tag — verify a patched map still loads in-game.
    "zoom_ui_on_scopeless": True,
    # Detached turrets -- the machinegun turret, plasma cannon, missile pod and
    # flamethrower -- are placed as VEHICLES, not weapon pickups, so they never
    # appeared in a level's `weapons` list and could never be drawn. With this on,
    # each level also offers the turrets it actually carries (its measured `turrets`
    # list). Off by default: a turret is a heavy, movement-penalised weapon and
    # handing one out changes a level's feel more than a normal draw does.
    "turrets_are_weapons": False,
    # Preferred scope source per game for the zoom-UI copy ({game: weapon name}).
    # Used when that weapon is present on the map being patched, else auto-picked.
    "zoom_donor": {},
    # Whether deliberate weapon choices (start-of-run picks and the New Weapon
    # button) carry a tied negative. Random new-weapon pairs from
    # new_weapon_chance are unaffected (their pair always has an enemy). False
    # strips negatives from those deliberate weapon choices.
    "weapon_choice_negatives": True,

    # When True, mods that can only ever apply in one game (an explicit "game"
    # filter, or a tag that isn't a per-game dict covering both games) are kept
    # out of every roll — useful for a combined H1+H2 run that only wants
    # effects that work in both. Structural test; see ModifierDatabase._is_single_game_mod.
    "remove_single_game_mods": False,
    # Suppress boss cards entirely. Forced on while remove_single_game_mods is on
    # (bosses are unique per game). See boss_mods_removed().
    "remove_boss_mods": False,
    # Boss option: make Heretic Leader boss mods target the leader AND his decoy
    # holograms together (one card tunes both).
    "combine_heretic_hologram": False,

    # Halo 3 only: on patch, remove the Cortana flicker + Gravemind vision cutscenes
    # from the map (opt-in, OFF by default). Composes with the .bak baseline model —
    # applied fresh from the pristine baseline each patch, so toggling it off and
    # re-patching restores the cutscenes. Reproduces "Halo 3 Cortana Begone".
    "remove_h3_cutscenes": True,   # #4: on by default — skip the vision cutscenes
    "ignore_elite_in_h3": True,   # H3 Elites are allies — don't patch Elite enemy effects there
    # Debug-only switch, but it stays in force whether or not debug mode is on: the
    # Flood are gone from ODST onward while their tags are not, so their cards would
    # otherwise keep being offered and patched into levels that field none.
    "remove_flood_from_odst": True,

    "include_grenades": True,          # #2: treat grenades as weapons; False hides them
    "grenades_need_weapon": False,     # #4: only offer grenades once a real gun is held
    # Chieftains and the Enforcer used to be declared in halo.json's mission `boss`
    # data, so they were always on; they now come from HERO_OPTIONS instead and these
    # default True to keep that behaviour. The genuinely new heroes below default off.
    "brute_chieftain_bosses": True,    # Chieftains (Halo 3, ODST and Reach)
    "h2_sentinel_enforcer_bosses": True,   # Halo 2's heavy Sentinel
    # Reach has no scripted boss fight, but it does ship tougher named variants that
    # define their OWN vitality rather than inheriting it, which is what makes a boss
    # card able to touch them without buffing every sibling. Off by default, like the
    # Chieftain option.
    "reach_elite_bosses": False,       # Elite Generals + the Zealots count as bosses
    "reach_grunt_ultra_bosses": False,  # Grunt Ultras count as bosses
    "reach_jackal_sniper_bosses": False,   # Reach sniper Jackals count as bosses
    "h2_honor_guard_bosses": False,        # Halo 2 Honor Guard Elites count as bosses
    "odst_specops_bosses": False,          # ODST spec-ops commanders count as bosses
    "h3_specops_bosses": False,            # Halo 3's ALLIED spec-ops commander
    # Master switch for the recurring Hero archetypes (HERO_NAMES). Default True, which
    # preserves the behaviour that shipped before heroes were a category: Brute
    # Chieftain and Sentinel Enforcer are declared bosses in halo.json's own mission
    # data, and turning this off is what now separates them from the named story
    # fights (Tartarus, Prophet Regret, Heretic Leader, 343 Guilty Spark).
    "heroes_are_bosses": True,
    "h3_equipment_in_rolls": False,     # H3 only: equipment can turn up in New Weapon draws
    "equipment_need_weapon": False,     # ...and only once the player holds a real gun
    # What the AUTOMATIC new-weapon rolls (new_weapon_chance) may offer beyond the
    # level's plain weapon pool. The New Weapon BUTTON always offers duals and
    # upgrades; these three let the automatic rolls do the same. Default False, which
    # is exactly what the automatic rolls did before the options existed.
    "auto_new_weapon_abilities": False,
    "auto_new_weapon_duals": False,
    "auto_new_weapon_upgrades": False,
    # Metagame scoring: pay more per kill for enemies the run has made nastier.
    # This edits <mcc_root>\Data\UI\scoredb.xml, OUTSIDE the map folders, and MCC
    # only re-reads that file at startup — so it is opt-in and off by default, and
    # every place it surfaces must say a restart is required.
    "score_scaling": False,
    "score_step": 0.05,        # multiplier per point of summed effect weight
    "score_cap_mult": 0.0,     # 0 = uncapped; otherwise the largest multiplier
    # ...and then push the same numbers into the RUNNING game, so the patch takes
    # effect without restarting MCC. Harmless when MCC is closed (it reports "not
    # running" and the file edit stands on its own), so it defaults on.
    "score_live_push": True,
    # Scale the campaign metagame's PLAYER DEATH penalty with how much the run has
    # taken on: penalty = 25 * (1 + per_round * rounds). Unlike everything else here
    # this is not a map patch -- Halo 1 and Halo 2 have no campaign metagame in their
    # own dlls, and the one scoring engine all five games share is the MCC wrapper.
    # So it is a live process write, and it works in every game for that reason.
    # Under the Betrayal skull the Marines turn on you, so killing one stops
    # being a betrayal and should pay out like any other kill. Two things have to
    # be true for that: the ScoreDB Marine rows must be positive, and the
    # wrapper's sign guard has to be opened, because it discards a row that is
    # not negative and charges a flat -50 instead. Both are undone when the run
    # has no Betrayal, so a normal run keeps vanilla scoring.
    "betrayal_marines_score": True,
    "death_penalty_scaling": False,
    "death_penalty_per_round": 0.10,   # +10% of the base penalty per round taken
    "death_penalty_base": 25.0,        # what MCC ships; 0 rounds leaves it unchanged

    # Whole-game enemy dials, per game, applied BEFORE any effect. Empty/absent means
    # "leave the shipped value alone"; a stored 0 means the same (the spin boxes show
    # 0 as "vanilla"). Reach and Halo 4 have entries so the settings survive until
    # those games are actually installed.
    "difficulty_baseline": {},
    # ODST's obtainable plasma rifle is the RED tag, which Halo 2 shipped as the
    # separate Brute Plasma Rifle. With this on it is offered under that name and
    # retuned on patch to match Halo 2's version. Normal Plasma Rifle effects reach
    # the red tag either way -- that is in the tag data, not this option.
    "odst_red_plasma_as_brute": False,
    # ODST replaces the sidearm and SMG outright: plain magnum and smg are in every
    # level's palette but never placed and never carried, only automag and
    # smg_silenced are. Two ways to model that, and they are alternatives:
    #
    #   odst_variants_as_base (ON)  - they ARE the Magnum and the SMG. One ordinary
    #       weapon card; picking it gives the ODST variant. No upgrade cards.
    #   odst_variants_as_base (OFF) - they are UPGRADES of the Magnum and SMG, with
    #       their own cards, and odst_downgrade_unupgraded then decides whether the
    #       map still hands them out for free.
    "odst_variants_as_base": True,
    # Only meaningful while the above is OFF. Rewrites the map's automag /
    # smg_silenced (and, with odst_red_plasma_as_brute on, plasma_rifle_red) to the
    # base weapon unless a player drafted that upgrade, so the upgrade card is what
    # actually grants it rather than the map doing it anyway. Covers all three places
    # a scenario names a weapon -- placements, AI loadouts and starting profiles --
    # since ODST hands these out mostly by AI loadout and barely places them at all.
    # Needs a PREPARED map: on a shipped one the base tags are in the palette but not
    # resident, and pointing anything at a non-resident tag silently yields nothing.
    "odst_downgrade_unupgraded": False,
    "odst_variant_bases": {"Auto Magnum": "Magnum", "Silenced SMG": "SMG"},
    # ODST's player has no shield -- it has stamina, which is not in the tags. The
    # Starting Shield field still exists and still takes a write, it just does not
    # do anything useful: a 10x starting shield was confirmed in game to drain
    # immediately. With this on, a Starting Shield card spends itself on Starting
    # Health instead, so drafting one is not a wasted pick.
    "odst_shield_into_health": True,
    # ODST returns to Mombasa Streets between every story mission, so a run that
    # only ever patches the mission leaves the hub vanilla — the level the player
    # spends the most time in. With this on, patching an ODST mission patches the
    # hub with the SAME plan. Effects for enemies the hub does not field are
    # harmless no-ops, and because patching runs from the .bak baseline the hub
    # always carries the current run rather than accumulating old ones.
    "odst_patch_hub": True,
    "odst_hub_mission": "h100",
    # A PREPARED ODST map can hand the player every weapon in it, not just the ones
    # the level naturally stocks. Off, each level offers its own list from halo.json
    # (levels keep their character -- Kikowani stays a thin level). On, the pool is
    # rebuilt from what the map file actually supports, which is what the preparation
    # work bought; the cost is that ODST levels stop differing from each other.
    # Derived from the map rather than hardcoded, so a level that was never prepared
    # correctly offers less instead of offering weapons that will not appear.
    "odst_pools_from_map": False,
    # ODST chooses the player's Starting Profile from the insertion point, and which
    # one is live can change as a mission progresses -- so the picks can be written to
    # profile 0 and the game can spawn the player on another one holding the map's
    # vanilla weapons. With this on, EVERY profile in the scenario gets the run's
    # starting weapons, so wherever the game spawns you the loadout is right.
    # Off by default: ODST also names NPC profiles (dutch, buck, odst02, 'a'), so this
    # hands squadmates the player's weapons too. Harmless to a run, but visible.
    "odst_all_starting_profiles": False,
    # ODST sets "Never Dropped By AI" on every equipment PICKUP tag; Halo 3 sets it on
    # none. That is why Brutes never drop equipment in ODST, and why a Brute Drop
    # Chance card has nothing to act on there. With this on, the flag is cleared on
    # every eqip tag in the map so AI can drop equipment again and the card works.
    "odst_ai_equipment_drops": False,
    # Data Hive and Coastal Highway fail if the Engineer (or, on Coastal Highway, the
    # olifaunt) dies, and neither scales with the run. On, the player's own vitality
    # cards are mirrored onto them. See ESCORT_BUFF_TAGS for the measured numbers.
    "odst_escort_buff": False,
    # ODST equipment normally drops at the mission START only (insertion point 0, one
    # location per player). On, it ALSO drops at every mid-mission insertion point the
    # level declares — the checkpoint places you revert to. That is what the old
    # cluster-everything behaviour did implicitly, and it is why a single Invincibility
    # pick turned into five pickups across ONI Alpha Site.
    "odst_equipment_all_insertions": False,
    # Give each ODST player the starting profile their own insertion point uses,
    # instead of writing profile 0 (player 1 only) or every profile (which also arms
    # the co-op slots of insertion points you are not at). UNVERIFIED in game — the
    # stride of four is inferred from profile naming and count; see
    # halo_patch.odst_profile_for.
    "odst_profiles_by_insertion": False,
    # Moving a run up a game used to blank every operator box: the preset key carries
    # both the tag and the game, and both change between engines, so a Halo 2 leg's
    # magnitudes could never be found again in Halo 3. On, a card with no value yet in
    # this game is prefilled from its OWN value in the nearest earlier game. Operators
    # carry cleanly by construction -- "*1.5" means the same thing on any base value.
    "carry_magnitudes_across_games": True,

    # --- The OTHER slot ---------------------------------------------------------
    # A pair has four slots: Player, Enemy, Boss and Other. Boss is the guaranteed
    # card on a level with a named STORY fight. Other is one card drawn from four
    # kinds -- Hero, Exhaust, Skull, Ally -- and it is rolled in two steps: does this
    # pair get one at all (other_chance), then WHICH kind (other_weights, relative).
    #
    # Rolling the kind first is what makes the group tunable: raising the Skull weight
    # trades skulls against the other three rather than against nothing, which is what
    # the old independent per-kind chances did.
    #
    # A kind that is switched off, or that has nothing left to give on this level (no
    # hero here, every skull already active), simply drops out of the roll and the
    # remaining weights share it out.
    "other_chance": 0.35,
    # Hero 4 / Exhaust 3 / Ally 2 are the user's chosen defaults. Skull stays at 1:
    # a skull is a whole-map rule that lasts the REST OF THE RUN, so it should be
    # the rarest of the four.
    "other_weights": {"hero": 4.0, "exhaust": 3.0, "skull": 1.0, "ally": 2.0},
    "other_hero_enabled": True,
    "other_exhaust_enabled": True,
    "other_skull_enabled": True,
    "other_ally_enabled": True,
    # Tag basename -> the name that weapon is offered under. Anything not named here
    # (multiplayer props like the ball and flag, turrets, vehicle guns) is not a run
    # weapon and is simply not offered, so an unknown basename fails closed.
    # NOTE: the Mauler's tag is "excavator" -- that is its internal name, not a
    # separate cut weapon, and halo.json's Mauler mods already point at it.
    "odst_map_pool_names": {
        "assault_rifle": "Assault Rifle", "automag": "Auto Magnum",
        "battle_rifle": "Battle Rifle", "beam_rifle": "Beam Rifle",
        "brute_shot": "Brute Shot", "covenant_carbine": "Covenant Carbine",
        "energy_blade": "Energy Blade", "excavator": "Mauler",
        "flak_cannon": "Flak Cannon",
        "gravity_hammer": "Gravity Hammer", "magnum": "Magnum", "needler": "Needler",
        "plasma_pistol": "Plasma Pistol", "plasma_rifle": "Plasma Rifle",
        "plasma_rifle_red": "Plasma Rifle", "rocket_launcher": "Rocket Launcher",
        "shotgun": "Shotgun", "smg": "SMG", "smg_silenced": "Silenced SMG",
        "sniper_rifle": "Sniper Rifle", "spartan_laser": "Spartan Laser",
        "spike_rifle": "Spike Rifle"
    },
    # Which tag a weapon IS, when that differs from whose effects it borrows. Only
    # starting weapons care: they write one tagRef, where an effect may legitimately
    # name several tags at once. ODST files its sidearm and SMG under their own tags
    # while taking the Magnum's and SMG's mods, and its live plasma rifle is the RED
    # tag -- the plain one is present but never placed and never carried.
    "weapon_tag_overrides": {
        "Halo 3: ODST": {
            "Magnum": "weap objects\\weapons\\pistol\\automag\\automag",
            "Pistol": "weap objects\\weapons\\pistol\\automag\\automag",
            "Auto Magnum": "weap objects\\weapons\\pistol\\automag\\automag",
            "SMG": "weap objects\\weapons\\rifle\\smg_silenced\\smg_silenced",
            "Silenced SMG": "weap objects\\weapons\\rifle\\smg_silenced\\smg_silenced",
            "Plasma Rifle": "weap objects\\weapons\\rifle\\plasma_rifle_red\\plasma_rifle_red",
            "Brute Plasma Rifle": "weap objects\\weapons\\rifle\\plasma_rifle_red\\plasma_rifle_red"
        }
    },
    "odst_shield_into_health_pair": {"from": "Starting Shield Modifier",
                                     "to": "Starting Health Modifier"},
    # The only differences between Halo 2's Brute Plasma Rifle and its plasma rifle.
    # Rounds Per Second is a range, so both ends move; Error Angle likewise. Minimum
    # Error and Error Angle are defined TWICE in Barrels -- dual wield first, single
    # second -- and nth 0 is the dual pair, which is the one that differs.
    "odst_brute_plasma_tuning": [
        {"field": "Rounds Per Second", "block": "Barrels", "op": "+", "value": 2.0},
        {"field": "Rounds Per Second Max", "block": "Barrels", "op": "+", "value": 2.0},
        {"field": "Minimum Error", "block": "Barrels", "nth": 0, "op": "-", "value": 0.5},
        {"field": "Error Angle", "block": "Barrels", "nth": 0, "op": "-", "value": 0.5},
        {"field": "Error Angle Max", "block": "Barrels", "nth": 0, "op": "-", "value": 0.5}
    ],
    # Deny specific equipment to the player. Grouped the way they play: two
    # "deny the enemy information" pieces, two "become untouchable" pieces.
    "remove_superflare_jammer": False,
    "remove_invincibility_invisibility": False,
    # Anything denied above can instead be offered as an ENEMY modifier, since
    # Brutes are the only characters that carry equipment.
    "denied_equipment_as_enemy_mods": False,
    # #7: offer map-replacement as a per-weapon CARD instead of the patcher's
    # sliders. The two are the same mechanism, so only one is shown at a time.
    "weapon_swap_cards": False,
    # Sprint (New Features / Experimental). Only functions on maps built with the
    # sprint mod; on a plain map these are inert. sprint_feature is the master
    # switch; start-with vs card is how it enters a run; speed% scales the sprint
    # boost, duration/cooldown are in seconds (converted to 30-tick script globals).
    "sprint_feature": False,
    "sprint_start_with": True,
    "sprint_as_card": False,
    "sprint_need_weapon": False,
    "sprint_mod_cards": True,     # offer the Speed/Duration/Cooldown tuning cards
    "sprint_speed_pct": 150,
    "sprint_duration_s": 3.0,
    "sprint_cooldown_s": 2.0,
    # Which flashlight-key abilities may appear in the weapon selection, and which one
    # "start with an ability" grants. Powerups need a map built with the current
    # toolkit; the patcher skips them (with a reason) on older builds.
    # Co-op sharing: a folder both machines can see (a cloud-synced one works best).
    # After a patch the run is written there, magnitudes included, so the other machine
    # can pick it up with one click instead of passing two files around by hand.
    "shared_session_dir": "",
    "shared_session_autosave": True,
    "abilities_offered": ["sprint"],
    "ability_cards_for": ["sprint"],   # whose tuning cards may enter the pool
    "ability_start_which": "sprint",
    "overshield_mult": 3.0,       # x normal shield
    "regen_percent": 100.0,       # % of max health healed per use
    "regen_duration_s": 5.0,      # healed over this long
    # Regeneration feedback pulse, in ticks between flashes. Per game: the effects and
    # how dense they read differ (H1 cyborg shimmer vs H2 teleport).
    "regen_fx_every": {"Halo 1": 10, "Halo 2": 45},
    "camo_duration_s": 5.0,
    "camo_cooldown_s": 30.0,      # starts when the camo window ends
    # #7: one-handed weapons that can be offered as "Dual <Weapon>" in the
    # New Weapon card (only once the player already owns the base weapon).
    "one_handed_weapons": ["Pistol", "Plasma Pistol", "Plasma Rifle", "Needler", "SMG", "Brute Plasma Rifle"],
    # Dual wield and weapon upgrades only unlock from these games onward
    # (matched against game order in the JSON). Set to the first game to allow everywhere.
    "dual_wield_from_game": "Halo 2",
    "upgrades_from_game": "Halo 2",

    # --- Map patching (Halo 1 for now) ---
    "target_difficulty": "Impossible",   # which difficulty slot difficulty-effects write to
    "assembly_plugins_dir": r"F:\SteamLibrary\steamapps\common\HCEEK\Assembly-1-2023-11-29-1702446457\Plugins",
    "plugin_subdirs_by_game": {"Halo 1": ["Halo1MCC", "Halo1"], "Halo 2": ["Halo2MCC", "Halo2"],
                               "Halo 3": ["Halo3MCC", "Halo3"],
                               "Halo 3: ODST": ["ODSTMCC", "ODST"],
                               "Halo Reach": ["ReachMCC", "Reach"]},
    "map_game_folder": {"Halo 1": "halo1/maps", "Halo 2": "halo2/h2_maps_win64_dx11",
                        "Halo 3": "halo3/maps", "Halo 3: ODST": "halo3odst/maps",
                        "Halo Reach": "haloreach/maps"},
    # A game that reuses another's effects. ODST is a later Halo 3 build sharing its
    # tag paths, so effects authored for Halo 3 apply there unless a field ODST
    # removed says otherwise. See HaloDB._game_ok.
    "game_inherits": {"Halo 3: ODST": "Halo 3"},
    # Halo 1 campaign scenario basenames, in order — used by the "Apply Sprint to
    # maps" action to walk the whole campaign (mod maps live under the same folder).
    "h1_campaign_maps": ["a10", "a30", "a50", "b30", "b40", "c10", "c20", "c40", "d20", "d40"],
    # #6: alternate internal names mapped to a canonical weapon. The alias
    # shares the canonical weapon's modifiers and is not treated as new.
    # e.g. {"Magnum": "Pistol"}
    "weapon_aliases": {"Magnum": "Pistol"},
    # #3: upgrade weapons offered in the New Weapon card only once the player
    # owns the required base weapon. Value = base weapon (also the mod source
    # unless the upgrade has its own entry in the JSON). Picking an upgrade while
    # dual-wielding the base also grants "Dual <upgrade>".
    "weapon_upgrades": {"Brute Plasma Rifle": "Plasma Rifle",
                        # Halo 2 only. Measured against the ordinary beam it is
                        # the same weapon -- identical projectile, +50% damage,
                        # and ~12% more heat and ~17% more age per round.
                        "Sentinel Eliminator Beam": "Sentinel Beam"},
    # An upgrade weapon is a marginal variant of its base (Brute Plasma Rifle vs
    # Plasma Rifle), so it uses the BASE's effects: the base's cards patch the
    # upgrade's tag as well, and the upgrade stops offering its own duplicate cards.
    # The upgrade is still offered as a WEAPON — only its effect cards go away.
    "upgrade_inherits_base": True,
    # Upgrades / dual-wields that exist in only SOME games, beyond the blanket
    # *_from_game gates above. Key = the offered weapon, value = the games where it
    # may be offered. Halo 3 dropped the Brute Plasma Rifle and made the Needler
    # two-handed, so neither should ever be offered there.
    "weapon_only_in_games": {"Brute Plasma Rifle": ["Halo 2"],
                             "Dual Needler": ["Halo 2"],
                             "Sentinel Eliminator Beam": ["Halo 2"]},

    "blacklist_label_separator": ": ",
}

# border / background hex for mod widgets, keyed by logical color name
# Vertical slice taken by the header, weapon row, button row and status bar. Rough
# by nature — card_metrics() clamps whatever falls out, and the pairs area scrolls.
# The horizontal gaps are user-adjustable (card_spacing / card_row_margin).
CARD_CHROME_HEIGHT = 340


# Pseudo-items that stand for the flashlight-key abilities in the weapon-selection pool.
# They are NOT real weapon tags — they ride the pick-a-card flow the way H3 equipment
# does, and picking one turns that ability on for that player (see _sprint_spec). Kept
# distinct from any real weapon name so is_ability_item / is_real_weapon can tell them
# apart everywhere. The values are the patcher's ability names (halo_patch._ABILITY_IDS).
SPRINT_ITEM = '⚡ Sprint'
OVERSHIELD_ITEM = '🛡 Overshield'
REGEN_ITEM = '✚ Regeneration'
CAMO_ITEM = '👁 Camo'

ABILITY_ITEMS = {
    SPRINT_ITEM: 'sprint',
    OVERSHIELD_ITEM: 'overshield',
    REGEN_ITEM: 'regeneration',
    CAMO_ITEM: 'camo',
}
ABILITY_ITEM_OF = {v: k for k, v in ABILITY_ITEMS.items()}

ABILITY_BLURBS = {
    'sprint': "Unlocks sprinting for this player (hold the flashlight key).",
    'overshield': "Press the flashlight key for an instant overshield.",
    'regeneration': "Press the flashlight key to regenerate health over a few seconds.",
    'camo': "Press the flashlight key to turn invisible for a few seconds.",
}

# Abilities limited to one player per run. Empty: every ability is per-player now.
# Sprint is confirmed working in co-op, and camo gained a pickup per player
# (camo_ability0/1) so two players no longer contend over one shared object.
ABILITY_ONE_PER_RUN = set()


# halo.json tuning cards carry a `sprint` marker on their target whose value is the
# parameter they tune; this maps each parameter to the ability it belongs to, so a card
# is only offered to a player who actually has that ability.
ABILITY_CARD_PARAMS = {
    'speed': 'sprint', 'duration': 'sprint', 'cooldown': 'sprint', 'enable': 'sprint',
    'os_mult': 'overshield',
    'regen_percent': 'regeneration', 'regen_duration': 'regeneration',
    'camo_duration': 'camo', 'camo_cooldown': 'camo',
}


def ability_of_param(param):
    return ABILITY_CARD_PARAMS.get(param)


def ability_cards_for():
    """Abilities whose tuning cards may enter the pool. Falls back to the older
    sprint_mod_cards boolean so settings saved before the per-ability list still work."""
    v = CONFIG.get('ability_cards_for')
    if v is None:
        return ['sprint'] if CONFIG.get('sprint_mod_cards', True) else []
    return list(v)


def is_ability_item(name):
    return name in ABILITY_ITEMS


def ability_of_item(name):
    """The patcher's ability name for a pool item, or None if it isn't an ability."""
    return ABILITY_ITEMS.get(name)


def is_sprint_item(name):
    return name == SPRINT_ITEM


def is_real_weapon(db, name):
    """An actual gun — not a grenade, H3 equipment, or an ability item. Holding only a
    Bubble Shield (or only Sprint) doesn't make a player armed."""
    return (bool(name) and not is_ability_item(name)
            and not db.is_grenade(name) and not db.is_equipment(name))


def strip_denied_equipment(db, items):
    """Drop equipment the player is denied from an offer pool."""
    denied = denied_equipment()
    if not denied:
        return items
    return [w for w in items
            if not (db.is_equipment(w) and db.resolve_equipment(w) in denied)]


def gate_offer_pool(db, weapons, run_state, player=None):
    """Drop grenades and/or equipment from an offer pool while the player has no
    real gun (#4, and its equipment counterpart).

    Without this a player's very first pick can be a grenade or a Bubble Shield,
    leaving them with nothing to actually shoot with. `player` None means "nobody in
    particular" — the start-of-run choice — which is exactly the case that must be
    gated, so it checks both. Each half is off unless its own option is enabled,
    which in turn requires the feature it gates to be on."""
    gate_gren = bool(CONFIG.get('grenades_need_weapon') and CONFIG.get('include_grenades', True))
    gate_equip = bool(CONFIG.get('equipment_need_weapon') and CONFIG.get('h3_equipment_in_rolls'))
    if not (gate_gren or gate_equip):
        return weapons
    players = [player] if player else ['player1', 'player2']
    if all(any(is_real_weapon(db, w) for w in (run_state.weapons_for(p) if run_state else []))
           for p in players):
        return weapons                      # everyone concerned already has a gun
    return [w for w in weapons
            if not (gate_gren and db.is_grenade(w))
            and not (gate_equip and db.is_equipment(w))]


# ---------------------------------------------------------------------------
# Offer-pool rules shared by BOTH new-weapon sources: the New Weapon button
# (MainWindow._weapon_offer_pool) and the automatic per-pair rolls
# (RunEnhancer._new_weapon_pool). They used to exist only in the button's path,
# which is why the automatic rolls silently never offered abilities, duals or
# upgrades. Keep the rule here and let both paths call it, so the two cannot
# drift apart again.
# ---------------------------------------------------------------------------

def game_at_least(db, game, min_game):
    """True if `game` is `min_game` or later in JSON game order."""
    games = db.get_games()
    if game in games and min_game in games:
        return games.index(game) >= games.index(min_game)
    return True                             # unknown ordering -> don't restrict


def has_equipment(game):
    """Games with an equipment sandbox — Halo 3's, or Reach's armour abilities.

    ODST was long assumed to be Halo 3 only. It is not: every level carries the
    equipment tags (8 or 9 of the 9 levels have all eleven), and placing a Bubble
    Shield in Tayari Plaza was confirmed in game to spawn, be picked up and work.
    What ODST does NOT do is hand it out — no level places any, and although its
    Brutes list the equipment at drop chance 1.0 the drop never happens.

    Reach's armour abilities are eqip tags too, and all six ship on every campaign
    map. They are a different sandbox — held, not consumed, and run off a recharging
    energy meter rather than charges — but they enter the offer pools the same way,
    which is what this gate decides. The PLACEMENT paths are separately gated by
    `_MAP_EQUIPMENT` in halo_patch, which has no Reach layout, so starting equipment
    and Map Presence stay inert here rather than writing with Halo 3's offsets.
    """
    return str(game).strip() in ('Halo 3', 'Halo 3: ODST', 'Halo Reach')


def equipment_placement_supported(game):
    """Games whose equipment can be PLACED into a map (starting gear, Map Presence).

    Narrower than has_equipment on purpose. Placement needs a per-game scenario
    layout, and `_MAP_EQUIPMENT` in halo_patch has none for Reach — so Reach can be
    offered its armour abilities and have their tags tuned, while the placement paths
    stay switched off instead of quietly producing a spec that writes nothing.
    """
    return str(game).strip() in ('Halo 3', 'Halo 3: ODST')


def weapon_upgrades():
    """The upgrade -> base map, including ODST's variants when they are modelled as
    upgrades rather than as the base weapons themselves.

    ODST's Auto Magnum and Silenced SMG are the only sidearm and SMG the game
    actually places, so whether they are "the Magnum" or "an upgrade to the Magnum"
    is a design choice, not a fact about the data. Resolved per call so the option
    takes effect without reloading halo.json.
    """
    ups = dict(CONFIG.get('weapon_upgrades', {}))
    if not CONFIG.get('odst_variants_as_base', True):
        ups.update(CONFIG.get('odst_variant_bases', {}))
    return ups


def upgrade_allowed_here(game, weapon):
    """False if `weapon` is restricted to games other than `game`. Covers weapons
    that simply don't exist in a later game (the Brute Plasma Rifle) or stopped
    being dual-wieldable (the Halo 3 Needler)."""
    allowed = CONFIG.get('weapon_only_in_games', {}).get(weapon)
    if not allowed:
        return True
    # ODST's red plasma rifle IS Halo 2's Brute Plasma Rifle, so while the run models
    # it as that weapon it has to be offerable here too -- otherwise the option turns
    # the upgrade on and no card for it can ever appear.
    if (weapon == 'Brute Plasma Rifle' and game == 'Halo 3: ODST'
            and CONFIG.get('odst_red_plasma_as_brute')):
        return True
    return game in allowed


# Games with NO dual wielding, whatever the lower bound says. `dual_wield_from_game`
# is just that -- a bound, "Halo 2 or later" -- and two games after it do not have the
# mechanic: ODST never shipped it (see the shelved dual-wield experiment) and Reach
# dropped it from the sandbox. Reach's weap plugin agrees, having no `Dual Wield
# Damage Scale` field at all, so the Dual Weapon cards would have offered a weapon the
# player cannot hold and then patched a field that does not exist.
DUAL_WIELD_ABSENT = frozenset({'Halo 3: ODST', 'Halo Reach', 'Halo 4'})


def dual_wield_allowed(db, game):
    return (game not in DUAL_WIELD_ABSENT
            and game_at_least(db, game, CONFIG.get('dual_wield_from_game', 'Halo 2')))


def unlocked_offer_items(db, game, owned, blacklist, duals=True, upgrades=True):
    """The items a player unlocks by what they ALREADY own: 'Dual <W>' for each
    owned one-handed weapon (#7), and upgrade weapons whose base is owned (#3).
    Both only from their configured game onward. `owned` is that player's weapons;
    `blacklist` is the run blacklist (labels)."""
    owned = set(owned)
    out = []
    if duals and dual_wield_allowed(db, game):
        one_handed = CONFIG.get('one_handed_weapons', [])
        for w in owned:
            if w in one_handed and not w.startswith('Dual '):
                dual = f"Dual {w}"
                if (dual not in owned and db.weapon_label(dual) not in blacklist
                        and upgrade_allowed_here(game, dual)):
                    out.append(dual)
    if upgrades and game_at_least(db, game, CONFIG.get('upgrades_from_game', 'Halo 2')):
        # Compare bases through resolve_weapon: a player owns the CANONICAL name, and
        # an upgrade's base may be an alias of it. ODST's Auto Magnum bases on "Magnum",
        # which is an alias of "Pistol" -- the name actually held -- so a literal
        # comparison never matched and that upgrade could never be offered.
        owned_canon = {db.resolve_weapon(w) for w in owned}
        for upgrade, base in weapon_upgrades().items():
            if not upgrade_allowed_here(game, upgrade):
                continue
            if (db.resolve_weapon(base) in owned_canon and upgrade not in owned
                    and db.weapon_label(upgrade) not in blacklist):
                out.append(upgrade)
    return out


def _tags_not_already_in(twin, base):
    """`twin` reduced to the tag paths `base` does not already name, or None.

    A tag is "<class> <path>[ & <path>...]" — one class, several targets. Comparing the
    whole string treats a partial overlap as brand new, which double-applies whatever
    the two share.
    """
    if not twin or not isinstance(twin, str):
        return None
    if not base or not isinstance(base, str):
        return twin
    cls, _, rest = twin.partition(' ')
    bcls, _, brest = base.partition(' ')
    paths = [p.strip() for p in rest.split(' & ') if p.strip()]
    if bcls == cls:
        have = {p.strip() for p in brest.split(' & ')}
        paths = [p for p in paths if p not in have]
    return ('%s %s' % (cls, ' & '.join(paths))) if paths else None


def drop_weapons_taken(db, weapons, run_state):
    """Weapons are UNIQUE across the run: one already held by either player is not
    offered again, to anyone.

    Excluding only the asking player's own weapons meant player 2 kept being offered
    what player 1 had drafted rounds earlier. Every path that can put a weapon card on
    screen has to apply this, or the duplicate just reappears on whichever path was
    missed -- the New Weapon button, the automatic rolls and the rerolls all pass here.

    Equipment and abilities are left alone: they carry their own sharing rules (a piece
    of equipment is not a weapon slot, and sprint/camo already have a one-per-run
    pair), so weapon uniqueness must not quietly become the rule for them too.
    """
    if run_state is None:
        return list(weapons)
    held = set(run_state.weapons_for('player1')) | set(run_state.weapons_for('player2'))
    if not held:
        return list(weapons)
    return [w for w in weapons
            if w not in held or is_ability_item(w) or db.is_equipment(w)]


def ability_offer_pool(db, game, run_state, player=None):
    """The ability items offerable in a weapon selection. H1 only, and only when
    abilities are configured as a drafted pick (not 'start with'). A player who
    already holds an ability isn't offered another — one ability per player, since
    the script runs exactly one per player. Sprint and camo additionally drop out
    once EITHER player owns them (see ABILITY_ONE_PER_RUN). With 'requires a gun' on
    it's gated to players who already hold a real weapon, which also keeps abilities
    out of the very first pick, when nobody is armed."""
    if game != 'Halo 1':
        return []
    if not (CONFIG.get('sprint_feature') and CONFIG.get('sprint_as_card')):
        return []
    if CONFIG.get('sprint_start_with'):
        return []                       # already always on — a card would be moot
    if run_state is None:
        return []
    players = [player] if player else ['player1', 'player2']
    if any(any(is_ability_item(w) for w in run_state.weapons_for(p)) for p in players):
        return []                       # that player already has their one ability
    if CONFIG.get('sprint_need_weapon'):
        if not all(any(is_real_weapon(db, w) for w in run_state.weapons_for(p))
                   for p in players):
            return []
    held = {ability_of_item(w) for w in
            run_state.weapons_for('player1') + run_state.weapons_for('player2')
            if is_ability_item(w)}
    offered = CONFIG.get('abilities_offered') or ['sprint']
    return [item for item, ab in ABILITY_ITEMS.items()
            if ab in offered and not (ab in ABILITY_ONE_PER_RUN and ab in held)]


def card_metrics():
    """(width, height) for every selection card, the same for all of them.

    Derived from the screen rather than the content: cards used to hug their text,
    so every reroll resized them. Assumes a roughly fullscreen window — three cards
    across the available width — and either dimension can be pinned in Options via
    its override checkbox. The pairs area keeps its scrollbar, so a smaller window
    scrolls instead of squashing the cards."""
    w = h = None
    try:
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            gap = int(CONFIG.get('card_spacing', 20))
            margin = int(CONFIG.get('card_row_margin', 20))
            w = (geo.width() - 2 * margin - 2 * gap - 24) // 3   # 24 ≈ scrollbar
            h = geo.height() - CARD_CHROME_HEIGHT
    except Exception:
        pass                                    # headless / odd platform: use defaults
    if not w or w < 240:
        w = 600
    if not h or h < 300:
        h = 800
    if CONFIG.get('card_width_override'):
        w = int(CONFIG.get('card_width', w) or w)
    if CONFIG.get('card_height_override'):
        h = int(CONFIG.get('card_height', h) or h)
    return max(240, min(int(w), 1400)), max(300, min(int(h), 2000))


# Halo 3 missions that actually PLACE a Brute Chieftain (checked against each map's
# scnr character palette, not just the tags it carries). 010 uses the
# brute_chieftain_armor_no_grenade variant, which the tag wildcard still covers.
# Brute Chieftains are Hero-class in Halo 3, ODST and Reach alike (Halo 2's chieftain
# is Tartarus, a named boss). These used to be declared in halo.json's mission `boss`
# fields, which made this option a no-op everywhere except ODST sc100/sc120; the
# heroes now live here instead, so the option is the single source.
# ODST's list is all NINE missions -- every one carries a chieftain in its character
# palette, though halo.json had only ever declared seven.
CHIEFTAIN_MISSIONS = (
    '010', '020', '030', '040', '070', '100',                       # Halo 3
    'h100', 'l200', 'l300', 'sc100', 'sc110', 'sc120', 'sc130',     # ODST
    'sc140', 'sc150',
    'm50', 'm70', 'm70_bonus',                                      # Reach
)
# Halo 2's heavy Sentinel. Note the engine does NOT class it Hero -- its char tag
# populates no metagame bucket at all and inherits one -- so it sits with the heroes
# by intent rather than by the census.
SENTINEL_ENFORCER_MISSIONS = ('06a', '06b')

# Reach missions that actually FIELD each optional boss -- read off the maps with
# sprint_toolkit/reach_census.py, by crossing the character palette with the squads
# that reference it (Spawn Points + Designer/Templated Cells). Palette presence alone
# was not enough: m50 carries grunt_ultra in its palette but no squad fields it, and
# m70_bonus carries both Brute Chieftain variants the same way.
REACH_GENERAL_MISSIONS = ('m10', 'm20', 'm30', 'm35', 'm45', 'm60', 'm70', 'm70_bonus')
# The story Elites -- Bungie's own squads call them zealots ('sq_facility_zealot',
# 'sq_zealot_elite_*'). Only m70's `elite_story_unique` defines its own vitality and
# charge blocks; the plain `elite_story` on m10 and m35 populates just Variants,
# General Properties and Campaign Metagame Bucket and inherits everything mechanical
# from elite_ultra. The Zealot cards therefore target elite_story_unique alone, so
# they cannot buff every Ultra as a side effect -- which is why m10 and m35 are NOT in
# this list. Adding them would offer a boss card that patches nothing.
REACH_ZEALOT_MISSIONS = ('m70',)
REACH_GRUNT_ULTRA_MISSIONS = ('m10', 'm35', 'm45')
# Hero-class on nine of the ten missions and, unusually for an inheriting variant, it
# carries its OWN vitality (60 body Normal / 90 Legendary, triple a plain Jackal).
REACH_JACKAL_SNIPER_MISSIONS = ('m20', 'm30', 'm35', 'm45', 'm50', 'm52', 'm60',
                                'm70', 'm70_bonus')
H2_HONOR_GUARD_MISSIONS = ('05a', '05b', '06a', '07a')
ODST_SPECOPS_MISSIONS = ('h100', 'l200', 'l300', 'sc100', 'sc110', 'sc120',
                         'sc130', 'sc140')
H3_SPECOPS_MISSIONS = ('050',)

# --- Heroes -------------------------------------------------------------------
#
# The engine itself grades every campaign character: the campaign-metagame bucket
# carries a Class enum (0 Infantry, 1 Leader, 2 Hero, 3 Specialist) and its options
# are identical in all five games. `sprint_toolkit/hero_census.py` reads it.
#
# Hero covers two very different things, though, so class alone is not the split:
# Tartarus is Hero and is plainly a one-off story boss, while a Brute Chieftain is
# Hero and turns up on six missions. HERO_NAMES is therefore the RECURRING archetypes
# only. The named story fights -- Tartarus, Prophet Regret, Heretic Leader and 343
# Guilty Spark -- stay ordinary bosses and are unaffected by the Heroes switch.
#
# Sentinel Enforcer sits here rather than with them: it is a recurring heavy that
# Halo 2 fields on two missions, not a named character.
HERO_NAMES = frozenset({
    'Brute Chieftain', 'Sentinel Enforcer', 'Elite General', 'Elite Zealot',
    'Grunt Ultra', 'Jackal Sniper', 'Elite Honor Guard', 'Elite Specops Commander',
})

# Games where the Elites are on your side (Halo 3) or absent entirely (ODST, which
# still ships every Elite tag and therefore still resolves every Elite card).
ELITE_ALLY_GAMES = ('Halo 3', 'Halo 3: ODST')

# The Flood stop appearing after Halo 3, but ODST still ships their whole tag set —
# every floodcombat/floodcarrier/pureform/infection tag resolves there, so a Flood card
# drafted on a Halo 2 or Halo 3 level goes on being offered and patched onto levels
# where nothing it edits will ever spawn.
FLOOD_FREE_GAMES = ('Halo 3: ODST', 'Halo Reach')

# --- ODST escort buff ---------------------------------------------------------
#
# Data Hive and Coastal Highway are escort levels: the mission fails if the Engineer
# (Vergil) dies, and on Coastal Highway the olifaunt has to survive as well. Neither
# scales with the run, so a few enemy-damage cards make them impossible to keep alive.
#
# The escort is the FREEFORM engineer, read out of the scenario rather than guessed —
# `sprint_toolkit/odst_squads.py` resolves each squad's characters through the
# Character Palette:
#
#     l200  sq_dc_engineer_01, sq_fa_engineer_01   -> engineer_freeform
#           sq_sur_eng_01..08                      -> engineer_slaveform
#     l300  sq_engineer  (the only engineer squad) -> engineer_freeform
#
# The two Data Hive squads are the ones the dc_engineer_follow_* / fa_engineer_follow_*
# scripts drive behind obj_escort_engineer_set. So every OTHER engineer on Data Hive is
# the enemy-side slaveform, which shares the plain `engineer` model — buffing that model
# would toughen the enemies the level throws at you while you escort Vergil. Only the
# freeform model is touched.
#
# Vergil ships far frailer than a normal engineer, which is why the level got unwinnable
# once the run's enemy cards stacked up. Measured on both maps:
#
#     hlmt                              health  shield  recharge
#     engineer            (slaveform)     50      300     0.5      <- NOT buffed
#     engineer_freeform   (Vergil)        50       50     0.25
#     olifaunt (l300 only)               500     5000     0.333
#     odst_oni_op_player                  80       80     0.333
#
# Enemy vitality lives on the hlmt model tag in Halo 2 onward, not on char, which is
# why these are hlmt paths. The buff rides the player's OWN vitality cards: whatever
# operator the run put on Player Health / Shield / Shield Recharge is mirrored onto
# the escorts, so they scale with the player instead of being tuned separately.
ESCORT_BUFF_MISSIONS = ('l200', 'l300')
ESCORT_BUFF_CARDS = ('Player Health', 'Player Shield', 'Player Shield Recharge')
ESCORT_BUFF_TAGS = (
    'hlmt objects' + chr(92) + 'characters' + chr(92) + 'engineer' + chr(92) + 'engineer_freeform',
    # Coastal Highway only; on Data Hive this reports as a skip, which is correct —
    # that level has no olifaunt tag at all.
    'hlmt objects' + chr(92) + 'vehicles' + chr(92) + 'olifaunt' + chr(92) + 'olifaunt',
)
FLOOD_ENEMIES = frozenset({
    'Flood Combat Form', 'Flood Carrier Form', 'Flood Infection Form', 'Flood Pure Form',
})


def _is_absent_flood_mod(mod, game):
    """True when `mod` edits the Flood in a game that no longer fields them."""
    if not CONFIG.get('remove_flood_from_odst', True):
        return False
    if str(game).strip() not in FLOOD_FREE_GAMES:
        return False
    who = mod.get('enemy') or mod.get('boss') or ''
    return isinstance(who, str) and who in FLOOD_ENEMIES


def _is_allied_elite_mod(mod, game):
    """True when `mod` edits Elites in a game where they aren't enemies.

    Matches the species card (`enemy` == 'Elite') AND the hero/boss cards, which are
    stamped with `boss` instead — the spec-ops commander is the one that reached a
    played ODST session."""
    if str(game).strip() not in ELITE_ALLY_GAMES:
        return False
    if mod.get('enemy') == 'Elite':
        return True
    who = mod.get('boss') or ''
    return isinstance(who, str) and who.startswith('Elite')

# (config key, boss name, missions). Every entry is additionally gated by
# `heroes_are_bosses`; these switches choose WHICH heroes, that one chooses whether
# heroes count at all.
# Ordered by the game each archetype FIRST appears in, matching halo.json's game
# order (Halo 1, 2, 3, ODST, Reach). Brute Chieftain spans Halo 3, ODST and Reach
# under one switch and is filed under its first appearance.
HERO_OPTIONS = (
    ('h2_sentinel_enforcer_bosses', 'Sentinel Enforcer', SENTINEL_ENFORCER_MISSIONS),
    ('h2_honor_guard_bosses', 'Elite Honor Guard', H2_HONOR_GUARD_MISSIONS),
    ('brute_chieftain_bosses', 'Brute Chieftain', CHIEFTAIN_MISSIONS),
    ('h3_specops_bosses', 'Elite Specops Commander', H3_SPECOPS_MISSIONS),
    ('odst_specops_bosses', 'Elite Specops Commander', ODST_SPECOPS_MISSIONS),
    ('reach_elite_bosses', 'Elite General', REACH_GENERAL_MISSIONS),
    ('reach_elite_bosses', 'Elite Zealot', REACH_ZEALOT_MISSIONS),
    ('reach_grunt_ultra_bosses', 'Grunt Ultra', REACH_GRUNT_ULTRA_MISSIONS),
    ('reach_jackal_sniper_bosses', 'Jackal Sniper', REACH_JACKAL_SNIPER_MISSIONS),
)

# Equipment the player can be denied, grouped as the two options present them.
DENIABLE_EQUIPMENT = {
    'remove_superflare_jammer': ('Superflare', 'Jammer'),
    'remove_invincibility_invisibility': ('Invincibility', 'Invisibility'),
}
# Halo 3 missions where a Brute that ACTUALLY carries each piece can spawn — read
# from every map's character palette crossed with the char Equipment Definitions
# block, counting only carriers whose Relative Drop Chance is above zero. Brutes are
# the only characters that carry equipment at all. Jammer and Invisibility ride
# solely on brute_stalker, which is why they are limited to two missions.
EQUIPMENT_CARRIER_MISSIONS = {
    'Superflare':    ('010', '020', '030', '040', '070', '100'),
    'Jammer':        ('070', '100'),
    'Invincibility': ('010', '020', '040', '070', '100'),
    'Invisibility':  ('070', '100'),
    'Bubble Shield': ('010', '020', '030', '040', '070', '100'),
    'Instant Cover': ('010', '020', '030', '040', '070', '100'),
    'Power Drain':   ('020', '030', '040', '070', '100'),
    'Regenerator':   ('010', '020', '040', '070', '100'),
    'Trip Mine':     ('020', '030', '070', '100'),
}


def denied_equipment():
    """Equipment names the player is currently denied, per the two options."""
    out = set()
    for key, names in DENIABLE_EQUIPMENT.items():
        if CONFIG.get(key):
            out.update(names)
    return out

# Direction-indicator colours, matching the positive/negative card borders.
EASIER_GREEN = '#4CAF50'
HARDER_RED = '#f44336'

MOD_COLORS = {
    'green': {'border': '4CAF50', 'bg': '0a1a0a'},
    'red':   {'border': 'f44336', 'bg': '1a0a0a'},
    'gold':  {'border': 'FFD700', 'bg': '1a1a0a'},
    'boss':  {'border': 'AA00FF', 'bg': '160016'},  # #4: menacing purple
    'special': {'border': '00E5FF', 'bg': '06201f'},  # #3: standout cyan
    'dual': {'border': '00E676', 'bg': '0a2012'},   # dual-wield-only effects
    'exhaust': {'border': 'FF7043', 'bg': '1e0f06'},  # #5: one-map exhaust (ember orange)
    'skull': {'border': 'D8D0C0', 'bg': '141210'},  # #7: skull — bone on near-black
    'equipment': {'border': 'ADCB2E', 'bg': '13160a'},  # H3 equipment — yellow-green
}


def skull_watermark_path():
    """Path to a faded ☠ image, rendered once into the app data dir.

    Qt stylesheets can only take a background-image from a file (no inline data),
    so the glyph is painted to a PNG rather than shipped as an asset."""
    p = app_data_dir() / "skull_bg.png"
    if not p.exists():
        try:
            from PySide6.QtGui import QPixmap, QPainter, QColor, QFont
            pm = QPixmap(256, 256)
            pm.fill(Qt.transparent)
            painter = QPainter(pm)
            font = QFont()
            font.setPointSize(170)
            painter.setFont(font)
            painter.setPen(QColor(216, 208, 192, 30))   # faint, so text stays readable
            painter.drawText(pm.rect(), Qt.AlignCenter, "☠")
            painter.end()
            pm.save(str(p))
        except Exception:
            return None                                 # cosmetic only — never fatal
    return p if p.exists() else None

# Historical effect renames: old name -> current halo.json key. Consulted by
# _refresh_mod_definition when a saved/loaded run's frozen mod name no longer
# exists in halo.json, so old saves keep working after an effect is renamed.
EFFECT_RENAMES = {
    # Rate of fire was three card names for one thing ('Rounds Per Second' on the
    # Assault Rifle, 'Rate of Fire' on the Flamethrower, 'More Shooting' on the
    # rest); they are all 'More Shooting' now, and it carries Rounds Per Second +
    # Shots Per Fire on every weapon. Fire Recovery Time stays its OWN card — it is
    # the cooldown on your trigger input, not the rate — and now exists on every
    # weapon rather than only the ones that ship a non-zero one.
    'Rounds Per Second': 'More Shooting',
    'Rate of Fire': 'More Shooting',
    'Rate of Fire (Charged)': 'More Shooting (Charged)',
    'Burst Fire': 'More Shooting',
    'Burst Fire (Charged)': 'More Shooting (Charged)',
    'Age Misfire': 'Misfire',
    'Berserk Melee Behaviour': 'Melee Behavior',
    'Berserk Triggerin': 'Melee Behavior',
    'Berserk Melee Leap': 'Melee Leap',
    'Target Tracking': 'Target Tracking & Leading',
    'Target Leading': 'Target Tracking & Leading',
    'Defensive': 'Cover Properties',
    'Projectile Error': 'Accuracy',
    'Effective Range?': 'Projectile',   # merged into Projectile
}

# The four difficulty flavors halo_patch.apply_difficulty understands. A plan op
# must carry whichever one its target declares, or the field name is looked up
# unexpanded and the write silently misses (e.g. "Body Vitality" instead of
# "Legendary Body Vitality").
DIFF_FLAVOR_KEYS = ('difficulty', 'diff_suffix', 'diff_prefix', 'diff_prefix_nl')

# Public difficulty names shown in the UI vs. the internal slot names the game (and
# halo_patch) use. Only the labels change: Hard is presented as Heroic, Impossible as
# Legendary. Stored/target_difficulty values stay internal, so nothing downstream
# needs to know about the public names.
DIFF_DISPLAY = (('Easy', 'Easy'), ('Normal', 'Normal'),
                ('Heroic', 'Hard'), ('Legendary', 'Impossible'))
_DIFF_TO_PUBLIC = {intern: pub for pub, intern in DIFF_DISPLAY}


def _fill_difficulty_combo(combo, current_internal):
    """Populate a QComboBox with public difficulty labels carrying their internal
    value as itemData, and select the row matching current_internal. Read the choice
    back with combo.currentData()."""
    combo.clear()
    for pub, intern in DIFF_DISPLAY:
        combo.addItem(pub, intern)
    i = combo.findData(current_internal)
    combo.setCurrentIndex(i if i >= 0 else 1)   # default Normal
    tune_combo(combo)


def _diff_flavor(target):
    return {k: target.get(k) for k in DIFF_FLAVOR_KEYS}


def _is_writable_now(path):
    """Can this file be opened for writing right now?

    Windows refuses a second write handle while another process holds one, which is
    exactly what MCC does to a map it has resident. Opening 'r+b' and closing it
    immediately is the cheapest reliable test and changes nothing. A missing file
    counts as writable so the caller reports its own, more specific error."""
    try:
        if not os.path.exists(path):
            return True
        with open(path, 'r+b'):
            return True
    except OSError:
        return False


def _patch_error_text(e):
    """A player-actionable message for a patch failure. A PermissionError (Errno 13)
    almost always means the map file is locked or read-only — surface the likely
    causes instead of a bare traceback."""
    if isinstance(e, PermissionError) or getattr(e, 'errno', None) == 13:
        fn = getattr(e, 'filename', None)
        return ("Windows denied write access to the map file (Errno 13: permission "
                "denied).\n\nUsual causes, most common first:\n"
                "  • Halo MCC is open — close the game completely, then patch again.\n"
                "  • The .map or its .bak is marked read-only — right-click → Properties "
                "and clear Read-only.\n"
                "  • The map lives under Program Files, which needs elevation — run this "
                "tool as administrator.\n\n"
                + (f"File: {fn}\n" if fn else "")
                + f"({e})")
    return str(e)


def active_skull_names(run_state):
    """Names of the skulls already locked into this run — every committed round plus
    the current round's selections. A skull is a whole-map rule, so once it's picked
    it governs every later patch of that level."""
    names = set()
    if run_state is None:
        return names

    def scan(mod):
        if isinstance(mod, dict) and mod.get('skull'):
            names.add(mod.get('name'))

    for rd in getattr(run_state, 'rounds', None) or []:
        for k in ('enemy1', 'enemy2', 'wildcard', 'wildcard2',
                  'boss1', 'boss2', 'exhaust1', 'exhaust2'):
            scan(rd.get(k))
        for pk in ('player1', 'player2'):
            scan((rd.get(pk) or {}).get('mod'))
    for pk in ('player1', 'player2'):
        sel = (getattr(run_state, 'selected_pairs', None) or {}).get(pk)
        if isinstance(sel, dict):
            for k in ('enemy_mod', 'wildcard_mod', 'boss_mod', 'exhaust_mod'):
                scan(sel.get(k))
    return names


def skull_conflict(mod, run_state):
    """The active skull that neutralises `mod`, or None. `affected_by_skull` may
    name one skull or several; only an ACTIVE one is worth warning about, since the
    note is meaningless in a run where that skull was never drawn."""
    want = (mod or {}).get('affected_by_skull')
    if not want:
        return None
    names = [want] if isinstance(want, str) else list(want)
    active = active_skull_names(run_state)
    hit = [n for n in names if n in active]
    return ', '.join(hit) if hit else None


def mod_ignored(mod):
    """Is this effect held back from the offer pools?

    halo.json's own header has documented `ignore` ("Whether to ignore this effect in
    the tools pool. yes/no. defaults to no") since the file was written, but nothing
    ever read it. It is how a card stays in the DB -- wired, verified, ready -- without
    being drawn: the Reach Accuracy Penalties on weapons that ship 0, where an operator
    would have nothing to bite on. Flipping one back on is a one-word edit.

    Accepts the yes/no the header specifies, plus the true/false a JSON author is
    likely to reach for. Anything unrecognised means NOT ignored, so a typo cannot
    silently delete a card from the game.
    """
    v = mod.get('ignore')
    if isinstance(v, bool):
        return v
    return isinstance(v, str) and v.strip().lower() in ('yes', 'true', '1')


def target_applies(target, game):
    """Does this target apply in `game`?

    Two opposite filters, because both readings come up:
      games       an ALLOW list -- only these games. Use when the field exists
                  nowhere else.
      skip_games  a DENY list -- every game except these. Use when the field EXISTS
                  everywhere but is not worth offering somewhere, e.g. Plasma Rifle's
                  Fire Recovery Time, which ships 0 in most games; the target stays in
                  halo.json for later rather than being deleted and re-derived.
    A target may carry either; `skip_games` wins if somehow both name the game.
    """
    if game in (target.get('skip_games') or []):
        return False
    return not target.get('games') or game in target['games']


def effect_desc(mod, game=None, games=None):
    """#7: the description to show for `mod` in `game` — its 'desc_overrides' entry
    for this game if one resolves, else the plain 'desc'. Kept as a SEPARATE key
    rather than turning 'desc' itself into a per-game dict, so every existing
    flat-string desc in halo.json needs no migration; only mods that actually
    need a different wording per game gain the extra key."""
    ov = mod.get('desc_overrides')
    resolved = resolve_gamed(ov, game, games) if ov else None
    return resolved if resolved else mod.get('desc', '')


def effect_debug_desc(mod, game=None, games=None):
    """The MECHANISM behind `mod`, if halo.json records one -- what tag and field it
    touches, why the value behaves the way it does, what was measured.

    Kept apart from `desc` on purpose. A card's visible text should answer "what does
    this do to my game", in a line; everything else is reference material that made
    the cards unreadable when it sat in the same string. This is shown as the
    description's tooltip, so it costs no space until someone wants it. Resolves
    per-game exactly like desc_overrides."""
    d = mod.get('debug_desc')
    return (resolve_gamed(d, game, games) if isinstance(d, dict) else d) or ''


def _is_gamed(value, games):
    """Is this dict keyed BY GAME, or is it a plain structured value?

    `resolve_gamed` assumes the former and returns None for anything whose keys are
    not game names -- which silently deletes the value. That is fine for `tag` and
    `field`, which are only ever a string or a per-game dict, but `init_defaults` is
    a SPEC dict ({tag, block, grow}) that may or may not be wrapped per game. Passing
    an unwrapped spec through resolve_gamed dropped it, so seeding never ran and the
    patcher reported "inherits from base" on a hero it was supposed to have seeded.
    """
    return any(k in value for k in list(games) + ['default'])


def resolve_gamed(value, game, games=None):
    """A `tag`/`field` value may be a plain string (applies to all games) or a
    dict keyed by game name. Resolution for the active game:
      1. exact game match wins;
      2. else an explicit 'default' key, if present;
      3. else the nearest EARLIER game that has an entry (e.g. a missing Halo 3
         falls back to Halo 2's value — a newer engine often inherits an
         older one's tag/field unless overridden), using `games` as the order;
      4. otherwise the value simply isn't defined for this game — return None.
         An entry defined only for a LATER game (e.g. an H2-only tag/field)
         must NOT leak backward into an earlier game's resolution; the two
         engines' tag/field namespaces are unrelated, so borrowing a later
         game's value would silently patch the wrong (or a nonexistent) tag.
    `games` is the ordered list of game names (from the DB). Callers that
    need a display fallback should do `resolve_gamed(...) or 'N/A'`; callers
    that build a patch plan should treat None as "not available this game"."""
    if not isinstance(value, dict):
        return value
    if game and game in value:
        return value[game]
    if 'default' in value:
        return value['default']
    if game and games and game in games:
        idx = games.index(game)
        for g in reversed(games[:idx]):      # nearest earlier game
            if g in value:
                return value[g]
    return None


def target_fields_display(mod_data, game, games):
    """Human-readable list of the target field names an effect actually patches
    for the active game (replaces the old cosmetic mod-level 'field'). Resolves
    per-game `targets` and per-game field names, and drops targets that don't
    apply to this game."""
    targets = mod_data.get('targets')
    if isinstance(targets, dict):
        targets = resolve_gamed(targets, game, games) or []
    names = []
    for t in targets or []:
        if not isinstance(t, dict):
            continue
        if not target_applies(t, game):
            continue
        fld = resolve_gamed(t.get('field'), game, games)
        if fld:
            names.append(str(fld))
    return ", ".join(names) if names else "—"


GAME_SHORT = {'Halo 1': 'H1', 'Halo 2': 'H2', 'Halo 3': 'H3', 'Halo 3: ODST': 'ODST',
              'Halo Reach': 'Reach'}

# Every game the difficulty baseline offers a row for. Halo 4 is not installed here
# (its folder holds only sound stubs), so its vanilla readouts show as absent -- but
# the settings persist, so it is ready if that game ever arrives. Reach WAS in that
# position and no longer is: it is installed, parses, and its name here must match the
# key halo.json's Missions section uses, which is 'Halo Reach' (no colon).
BASELINE_GAMES = ['Halo 1', 'Halo 2', 'Halo 3', 'Halo 3: ODST', 'Halo Reach', 'Halo 4']
BASELINE_COLS = [('vitality', 'Vitality'), ('shield', 'Shield'),
                 ('damage', 'Damage'), ('rof', 'Rate of Fire')]


def mod_game_scope(mod_data):
    """Every game an effect can actually apply in, or None when it is unrestricted.

    An effect authored for one game also reaches any game that INHERITS that one --
    ODST is a later Halo 3 build, so a "Halo 3" effect works there too (see
    ModifierDatabase._game_ok, which is what decides whether it is offered). Scope has
    to be computed the same way, or the card contradicts the filter that let it
    through: a great many Halo 3 effects are live in ODST while reading "H3 only".
    """
    games = mod_data.get('games') or []
    if len(games) == 1:
        authored = list(games)
    elif not games and isinstance(mod_data.get('tag'), dict):
        authored = list(mod_data['tag'])
    elif games:
        authored = list(games)
    else:
        return None                       # plain-string tag: valid everywhere
    inherits = CONFIG.get('game_inherits', {})
    scope = list(authored)
    grew = True
    while grew:                           # follow chains, not just direct children
        grew = False
        for child, parent in inherits.items():
            if parent in scope and child not in scope:
                scope.append(child)
                grew = True
    return scope


def single_game_badge(mod_data):
    """'◆ H1 only' / '◆ H3/ODST only' for an effect that cannot apply everywhere
    (matches ModifierDatabase._is_single_game_mod), or None for cross-game ones."""
    scope = mod_game_scope(mod_data)
    if not scope or len(scope) >= len(GAME_SHORT):
        return None                       # reaches every game: nothing to warn about
    return "◆ %s only" % '/'.join(GAME_SHORT.get(g, g) for g in scope)


def heretic_combine_active(mod_data, game, games):
    """True if the 'Combine Heretic Leader & holograms' option will make this boss
    card also tune the decoy holograms. Mirrors the patch-time check in
    on_patch_map so the card shows what patching will actually do."""
    if not (CONFIG.get('combine_heretic_hologram')
            and mod_data.get('boss') == 'Heretic Leader'):
        return False
    tag = resolve_gamed(mod_data.get('tag'), game, games)
    return isinstance(tag, str) and 'heretic_leader' in tag


def card_meta_text(mod_data, game, games):
    """The card's 'Tag:' / 'Fields:' lines, honoring the hide_tags/hide_fields
    appearance options. Empty string if both are hidden."""
    parts = []
    if not CONFIG.get('hide_tags'):
        tag = resolve_gamed(mod_data.get('tag', 'N/A'), game, games) or 'N/A'
        parts.append(f"Tag: {tag[:60]}{'...' if len(tag) > 60 else ''}")
    if not CONFIG.get('hide_fields'):
        parts.append(f"Fields: {target_fields_display(mod_data, game, games)}")
    return "\n".join(parts)


class ModifierDatabase:
    """Load and manage all modifiers from halo.json"""
    
    def __init__(self, json_path=None):
        # Resolve relative to this script (or the bundled data dir when frozen).
        self.json_path = json_path or resource_path('halo.json')
        self.data = None
        self.positive_pool = []
        self.negative_pool = []
        self.wildcard_pool = []
        self.skull_pool = []        # #7: negative-slot alternatives, whole-map rules
        self.weapon_mods = {}
        self.enemy_mods = {}
        self.boss_mods = {}         # boss name -> mods (Boss enemy modifier section)
        # {game: {tag}} for enemy tags that AREN'T enemy-specific — the same tag used by
        # two or more enemies, e.g. H2's `char ai\generic`, which several species share.
        # Editing one there hits every AI that shares it, so such an effect belongs
        # under "general" rather than the enemy it happened to be drafted from.
        # It is per GAME: Flood Carrier's Accuracy is its own tag in H1, generic in H2.
        self.generic_enemy_tags = {}
        self.mission_enemies = {}
        self.mission_list = []
        self.games = []             # game names in JSON order
        self.mission_games = {}     # mission_id -> game name
        self.mission_weapons = {}   # mission_id -> level weapon pool
        self.mission_turrets = {}   # mission_id -> detached turrets the level carries
        self.mission_grenades = {}  # mission_id -> grenade pool (#2)
        self.mission_equipment = {} # mission_id -> H3 equipment pool
        self.equipment_mods = {}    # equipment name -> [mods], offered once it's owned
        self.mission_boss = {}      # mission_id -> list of boss names (#4)
        self._odst_pool_cache = {}  # mission_id -> offer names derived from the map
        try:
            self.load_data()
        except Exception as e:
            print(f"Error loading data: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def load_data(self):
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            self._categorize()
            print(f"✅ Loaded {self.json_path} successfully")
        except FileNotFoundError:
            print(f"❌ {self.json_path} not found in current directory")
            raise
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing {self.json_path}: {e}")
            raise
    
    @staticmethod
    def _parse_games(value):
        """Normalize the optional `game` field to a list. Blank/missing = all games."""
        if not value:
            return []
        if isinstance(value, str):
            return [value]
        return list(value)

    def _index_generic_enemy_tags(self):
        """Find enemy tags that several enemies share, PER GAME.

        A "specific enemy" effect can still resolve to a tag that isn't specific at
        all: in Halo 2, Accuracy for Brute, Bugger and both Flood forms all point at
        `char ai\\generic`. Patching it from one of those cards changes every AI that
        shares the tag, and two such cards drafted from different enemies are really
        the same edit — which is why they stacked, filed under whichever enemy was
        drafted first. Detected by structure rather than a hand-maintained list, so a
        newly-added shared effect classifies itself."""
        games = self.get_games() or []
        seen = {}       # (game, tag) -> {enemy}
        for enemy, mods in self.enemy_mods.items():
            for mod in mods:
                for g in games:
                    tag = resolve_gamed(mod.get('tag'), g, games)
                    if isinstance(tag, str) and tag:
                        seen.setdefault((g, tag), set()).add(enemy)
        self.generic_enemy_tags = {}
        for (g, tag), enemies in seen.items():
            if len(enemies) > 1:
                self.generic_enemy_tags.setdefault(g, set()).add(tag)

    def is_generic_enemy_mod(self, mod, game):
        """True if this enemy effect's tag is shared with other enemies in `game`."""
        if not isinstance(mod, dict) or not mod.get('enemy'):
            return False
        tag = resolve_gamed(mod.get('tag'), game, self.get_games())
        return isinstance(tag, str) and tag in self.generic_enemy_tags.get(game, ())

    def _build_mod(self, mod_name, mod_data, extra=None):
        mod = {
            'name': mod_name,
            'desc': mod_data.get('desc', ''),
            'desc_overrides': mod_data.get('desc_overrides'),  # #7: per-game desc overrides
            'ignore': mod_data.get('ignore'),                  # held out of the pools
            'debug_desc': mod_data.get('debug_desc'),          # mechanism, shown as a tooltip
            'tag': mod_data.get('tag', ''),
            'games': self._parse_games(mod_data.get('game')),
            'wildcard': bool(mod_data.get('wildcard', False)),
            'skull': mod_data.get('skull'),   # #7: whole-map rule, not a tag edit
            # Name(s) of skull(s) that neutralise this effect. Only surfaced on the
            # card while one of them is actually active in the run.
            'affected_by_skull': mod_data.get('affected_by_skull'),
            'special': bool(mod_data.get('special', False)),  # escalating-odds effect
            'dual_only': bool(mod_data.get('dual_only', False)),  # needs 'Dual <X>'
            'harder_when': mod_data.get('harder_when'),  # 'increased'/'decreased' direction hint
            'easier_when': mod_data.get('easier_when'),  # ...and its opposite (all 4 uses are mod-level)
            'init_defaults': mod_data.get('init_defaults'),  # seed unset enemies (e.g. Elite grenades)
            'targets': mod_data.get('targets') if isinstance(mod_data.get('targets'), dict)
                       else list(mod_data.get('targets', []) or []),  # map-patch targets
        }
        if extra:
            mod.update(extra)
        return mod

    def _categorize(self):
        if 'Player Modifiers' in self.data:
            if 'General Modifiers' in self.data['Player Modifiers']:
                for mod_name, mod_data in self.data['Player Modifiers']['General Modifiers'].items():
                    self.positive_pool.append(self._build_mod(mod_name, mod_data))
            if 'Specific Weapon Modifier' in self.data['Player Modifiers']:
                for weapon, mods in self.data['Player Modifiers']['Specific Weapon Modifier'].items():
                    self.weapon_mods[weapon] = [
                        self._build_mod(mod_name, mod_data, {'weapon': weapon})
                        for mod_name, mod_data in mods.items()
                    ]
        if 'Enemy modifiers' in self.data:
            if 'General modifiers' in self.data['Enemy modifiers']:
                for mod_name, mod_data in self.data['Enemy modifiers']['General modifiers'].items():
                    self.negative_pool.append(self._build_mod(mod_name, mod_data))
            if 'Specific Enemy modifier' in self.data['Enemy modifiers']:
                for enemy, mods in self.data['Enemy modifiers']['Specific Enemy modifier'].items():
                    self.enemy_mods[enemy] = []
                    for mod_name, mod_data in mods.items():
                        self.enemy_mods[enemy].append(
                            self._build_mod(mod_name, mod_data, {'enemy': enemy}))
            # Bosses live in their own section; keyed like enemies (mod['enemy'] =
            # boss name) but only ever drawn via the boss pool, never as a normal
            # enemy card.
            # Two sections, one pool. halo.json keeps them apart so the data says which
            # is which -- 'Boss enemy modifier' is the named one-off story fights,
            # 'Hero enemy modifier' the recurring archetypes (HERO_NAMES) -- but both
            # are drawn through the same boss pool, so they load into one dict.
            for section in ('Boss enemy modifier', 'Hero enemy modifier'):
                for boss, mods in (self.data['Enemy modifiers'].get(section)
                                   or {}).items():
                    self.boss_mods[boss] = [self._build_mod(n, md, {'enemy': boss})
                                            for n, md in mods.items()]
        # Equipment effects are keyed like weapon effects, but only ever surface once
        # the player is actually carrying that piece (see get_player_modifiers_filtered).
        if 'Equipment' in self.data:
            for eq, mods in self.data['Equipment'].items():
                self.equipment_mods[eq] = [
                    self._build_mod(n, md, {'equipment': eq}) for n, md in mods.items()]
        # #7: Skulls are negatives that change a whole-map rule instead of tag values,
        # so they're drawn in place of a normal negative rather than alongside one.
        if 'Skull modifiers' in self.data:
            for mod_name, mod_data in self.data['Skull modifiers'].items():
                self.skull_pool.append(self._build_mod(mod_name, mod_data))
        # Wildcard pool: Friend modifiers are wildcards by nature, plus any mod
        # anywhere flagged `wildcard: true`.
        if 'Friend modifiers' in self.data:
            for mod_name, mod_data in self.data['Friend modifiers'].items():
                mod = self._build_mod(mod_name, mod_data)
                mod['wildcard'] = True
                self.wildcard_pool.append(mod)
        for pool in (self.positive_pool, self.negative_pool):
            self.wildcard_pool.extend(m for m in pool if m.get('wildcard'))
        for mods in list(self.weapon_mods.values()) + list(self.enemy_mods.values()):
            self.wildcard_pool.extend(m for m in mods if m.get('wildcard'))
        if 'Missions' in self.data:
            for game, missions in self.data['Missions'].items():
                if game not in self.games:
                    self.games.append(game)
                for mission_id, mission_data in missions.items():
                    self.mission_enemies[mission_id] = {
                        'name': mission_data.get('name', mission_id),
                        'enemies': mission_data.get('enemies', []),
                        # Optional free-text warning for levels whose behaviour is
                        # driven by their script rather than their tags — see
                        # mission_note().
                        'note': mission_data.get('note')
                    }
                    self.mission_games[mission_id] = game
                    self.mission_weapons[mission_id] = mission_data.get('weapons', [])
                    self.mission_turrets[mission_id] = mission_data.get('turrets', [])
                    self.mission_grenades[mission_id] = mission_data.get('grenades', [])
                    self.mission_equipment[mission_id] = mission_data.get('equipment', [])
                    boss = mission_data.get('boss')
                    self.mission_boss[mission_id] = ([boss] if isinstance(boss, str)
                                                     else list(boss) if boss else [])
                    self.mission_list.append((mission_id, mission_data.get('name', mission_id)))
        # Kept in halo.json order, NOT sorted by mission id: Halo 2's ids don't run in
        # campaign order (Gravemind 07a -> Uprising 08a -> High Charity 07b), so sorting
        # listed the missions in an order the game never plays them in — and silently
        # undid a hand-fixed order in the file.
        # After Missions, because the games list it builds is what the per-game tag
        # resolution needs.
        self._index_generic_enemy_tags()
        print(f"✅ Categorized: {len(self.positive_pool)} general positive, "
              f"{len(self.negative_pool)} general negative, "
              f"{len(self.wildcard_pool)} wildcard, "
              f"{sum(len(m) for m in self.weapon_mods.values())} weapon mods")
        print(f"✅ Games: {', '.join(self.games)}")
        print(f"✅ Missions: {len(self.mission_list)} available")
        for mission_id, name in self.mission_list:
            print(f"   - {mission_id} [{self.mission_games.get(mission_id, '?')}]: {name}")

    def resolve_weapon(self, name):
        """Map a display/arsenal name to the weapon whose mods it uses:
        strip a 'Dual ' prefix (#7), apply aliases (#6), then fall back an
        upgrade to its base weapon for mods (#3) if it has no own entry."""
        if not name:
            return name
        if name.startswith('Dual '):
            name = name[len('Dual '):]
        name = CONFIG.get('weapon_aliases', {}).get(name, name)
        if name not in self.weapon_mods:
            # ODST's variants fall back to their base for MODS whichever way they are
            # modelled: which effects apply is a data question, not a design one, and
            # a run saved under one setting must still resolve under the other.
            name = (weapon_upgrades().get(name)
                    or CONFIG.get('odst_variant_bases', {}).get(name)
                    or name)
            # An upgrade's base may itself be an alias: ODST's Auto Magnum bases on
            # Magnum, which is an alias of Pistol. Without a second alias pass it
            # resolved to a name with no mods and the weapon was dropped from every
            # offer pool in silence.
            name = CONFIG.get('weapon_aliases', {}).get(name, name)
        return name

    @staticmethod
    def base_for_upgrade(weapon):
        """The weapon an upgrade is a variant of ('Brute Plasma Rifle' -> 'Plasma
        Rifle'), or None — for the upgrade itself, when the inherit option is on.
        None when the option is off, so everything behaves as it did."""
        if not CONFIG.get('upgrade_inherits_base', True):
            return None
        return weapon_upgrades().get(weapon)

    def upgrades_of(self, weapon):
        """Upgrade weapons that treat `weapon` as their base, when inheriting is on."""
        if not CONFIG.get('upgrade_inherits_base', True):
            return []
        return [up for up, base in weapon_upgrades().items()
                if base == weapon]

    def upgrade_twin_tag(self, weapon, effect_name, game):
        """The tag an upgrade's OWN copy of `effect_name` uses, so a base-weapon card
        can patch the upgrade too. Read from the upgrade's entry rather than guessed,
        because the right tag differs per effect (a damage effect points at a jpt!,
        a projectile one at a proj), and returns None when the upgrade simply has no
        counterpart for that effect."""
        for up in self.upgrades_of(weapon):
            twin = next((m for m in self.weapon_mods.get(up, [])
                         if m.get('name') == effect_name), None)
            if not twin:
                continue
            if not self._game_ok(twin, game):
                # The upgrade has no card of this name IN THIS GAME, so there is
                # nothing to mirror. Without this test, resolve_gamed's earlier-game
                # fallback happily hands back the Halo 2 tag: every one of the Brute
                # Plasma Rifle's 17 Halo-2-only cards was mirrored onto
                # `brute_plasma_rifle`, a tag no Halo 3 or ODST map has, so each one
                # became a guaranteed "not present in this map" failure in the report.
                # The fallback is right for a card that exists in both games and only
                # names its tag once; it is wrong for a card that does not exist here.
                continue
            tag = resolve_gamed(twin.get('tag'), game, self.get_games())
            if isinstance(tag, str) and tag:
                return tag
        return None

    def weapon_label(self, weapon):
        """Blacklist label for a weapon (distinct from modifier labels)."""
        return f"Weapon{CONFIG['blacklist_label_separator']}{weapon}"

    def is_grenade(self, name):
        """Grenades are equipment, not weapons — they never carry a weap tag and
        must be excluded from the starting-weapon / map-weapon-swap features."""
        return any(name in gl for gl in self.mission_grenades.values())

    def is_equipment(self, name):
        """H3 equipment (Bubble Shield, Regenerator...): an `eqip` tag, not a
        `weap` one. Like grenades, never a Primary/Secondary starting weapon."""
        return any(name in el for el in self.mission_equipment.values())

    def weap_tag_for(self, weapon_name, game):
        """The `weap ...` tag for a weapon in the given game, taken from any of its
        effects (used to set the scenario's starting weapons). None if unknown.

        Returns exactly ONE tag. An effect may name several with ' & ' so it patches
        them together — ODST's Plasma Rifle covers both the dead plasma_rifle and the
        live plasma_rifle_red that way — but a starting weapon is a single tagRef, and
        writing the joined string looked up a tag that does not exist.

        A game may also file a weapon under its own tag while borrowing another's
        effects: ODST's Silenced SMG and Auto Magnum take the SMG's and Magnum's mods,
        so without an override they resolved to the base weapon, which ODST does not
        even ship in every level."""
        override = (CONFIG.get('weapon_tag_overrides', {}).get(game, {})
                    .get(weapon_name))
        # The ODST overrides exist because the base weapons used to be unreachable
        # there. On a PREPARED map they are real, so once a variant is modelled as an
        # UPGRADE the base NAME has to mean the base TAG again -- otherwise a "Magnum"
        # card would still hand out the auto magnum it is supposed to be an upgrade
        # from. The two variant families are governed by different options, and a
        # variant's OWN name always keeps its override: that name IS that tag.
        if override and game == 'Halo 3: ODST' and weapon_name not in (
                set(CONFIG.get('odst_variant_bases', {})) | {'Brute Plasma Rifle'}):
            sidearm = not CONFIG.get('odst_variants_as_base', True)
            if weapon_name == 'Plasma Rifle':
                # only an upgrade while it is being modelled as Halo 2's Brute one
                override = None if CONFIG.get('odst_red_plasma_as_brute') else override
            elif sidearm:
                override = None
        if override:
            return override
        for mod in self.weapon_mods.get(self.resolve_weapon(weapon_name), []):
            tag = resolve_gamed(mod.get('tag'), game, self.get_games())
            if isinstance(tag, str) and tag.startswith('weap '):
                # first of a multi-tag effect; they are variants of one weapon
                return tag.split(' & ')[0].strip()
        return None

    def eqip_tag_for(self, name, game):
        """The `eqip ...` tag for a piece of equipment, taken from any of its effects.
        The counterpart of weap_tag_for, used to grant Halo 3 starting equipment by
        placing it on the player spawn. None if unknown."""
        for mod in self.equipment_mods.get(self.resolve_equipment(name), []):
            tag = resolve_gamed(mod.get('tag'), game, self.get_games())
            if isinstance(tag, str) and tag.startswith('eqip '):
                return tag
        return None

    def get_weapon_modifiers(self, weapon_name):
        """Mods for a weapon slot. `dual_only` effects are offered only when
        the slot is a 'Dual <X>' (the dual upgrade was taken)."""
        mods = self.weapon_mods.get(self.resolve_weapon(weapon_name), [])
        is_dual = bool(weapon_name) and str(weapon_name).startswith('Dual ')
        return mods if is_dual else [m for m in mods if not m.get('dual_only')]

    def get_offer_modifiers(self, item):
        """Mods to show on an offer card, whatever KIND of item it is.

        An offer pool mixes weapons, H3/ODST equipment and abilities, and equipment
        mods live in their own table -- asking get_weapon_modifiers for a Bubble Shield
        degrades to [], which is why a freshly offered piece of equipment showed "0
        available modifiers" instead of its own effects.
        """
        if is_ability_item(item):
            return []
        key = self.resolve_equipment(item)
        if key:
            return list(self.equipment_mods.get(key, []))
        return self.get_weapon_modifiers(item)

    def denied_equipment_enemy_mods(self, mission_id):
        """Equipment the player is denied, re-offered as ENEMY modifiers (#4).

        Brutes are the only characters that carry equipment, so a piece the player
        can't have is still live on the map as a Brute's toy — tuning it becomes a
        negative. Restricted to missions where a Brute that actually carries it can
        spawn (EQUIPMENT_CARRIER_MISSIONS), so e.g. Jammer and Invisibility only
        appear on The Ark and The Covenant, the two missions with brute_stalker."""
        if not CONFIG.get('denied_equipment_as_enemy_mods'):
            return []
        out = []
        for name in sorted(denied_equipment()):
            key = self.resolve_equipment(name)
            if not key or mission_id not in EQUIPMENT_CARRIER_MISSIONS.get(name, ()):
                continue
            for m in self.equipment_mods.get(key, []):
                # Re-tagged as a Brute effect so it groups, labels and blacklists
                # like any other enemy modifier. Copied so the player-side pool
                # entry is never mutated.
                out.append({**m, 'enemy': 'Brute', 'equipment': None,
                            'name': f'{name} {m["name"]}'})
        return out

    def get_enemy_modifiers(self, mission_id):
        if mission_id not in self.mission_enemies:
            return list(self.negative_pool)
        enemy_names = self.mission_enemies[mission_id]['enemies']
        specific_mods = []
        for enemy in enemy_names:
            if enemy in self.enemy_mods:
                specific_mods.extend(self.enemy_mods[enemy])
        return (specific_mods + self.denied_equipment_enemy_mods(mission_id)
                + self.negative_pool)

    def get_available_weapons(self):
        return list(self.weapon_mods.keys())

    def odst_map_pool(self, mission_id):
        """Offer names for every weapon the level's MAP can actually give a player.

        Read from the patch baseline (`.map.bak`) when there is one, since that is what
        a patch is built from and therefore what the run will really be played on.
        Empty when the map cannot be read at all -- the caller then keeps the level's
        halo.json list, so a missing or unreadable map narrows nothing silently.
        """
        if mission_id in self._odst_pool_cache:
            return self._odst_pool_cache[mission_id]
        names, folder = [], CONFIG.get('map_game_folder', {}).get('Halo 3: ODST')
        try:
            import halo_patch          # imported lazily, as everywhere else here
            base = Path(mcc_root()) / folder / (mission_id + '.map')
            path = Path(str(base) + '.bak') if Path(str(base) + '.bak').exists() else base
            m = halo_patch.open_map(str(path), 'Halo 3: ODST')
            table = CONFIG.get('odst_map_pool_names', {})
            for short in halo_patch.odst_player_weapons(m):
                nm = table.get(short)
                if nm and nm not in names:
                    names.append(nm)
        except Exception as e:
            print(f"ODST pool from map failed for {mission_id}: {e}")
            names = []
        self._odst_pool_cache[mission_id] = names
        return names

    def get_level_weapons(self, mission_id):
        """Weapon pool for a level: its `weapons` list (plus grenades unless
        disabled in CONFIG), restricted to entries that resolve to real mods.
        Aliases collapse to their canonical weapon. Falls back to all weapons."""
        wl = list(self.mission_weapons.get(mission_id) or [])
        if (CONFIG.get('odst_pools_from_map')
                and self.mission_games.get(mission_id) == 'Halo 3: ODST'):
            wl = self.odst_map_pool(mission_id) or wl
        # ODST's Auto Magnum / Silenced SMG. Treated as the base weapon, the level
        # offers the ordinary card (the variant is what the player actually gets, in
        # the map); treated as upgrades, the base card is what the level offers and
        # the variant is only reachable through the upgrade.
        if self.mission_games.get(mission_id) == 'Halo 3: ODST':
            bases = CONFIG.get('odst_variant_bases', {})
            wl = [bases.get(w, w) for w in wl]
        # ODST's obtainable plasma rifle is the tag Halo 2 shipped as the Brute
        # Plasma Rifle, so with that option on the level offers it under that name
        # wherever it stocks a plasma rifle. Resolved per call, like bosses_for, so
        # toggling the option takes effect without reloading halo.json.
        if (CONFIG.get('odst_red_plasma_as_brute')
                and self.mission_games.get(mission_id) == 'Halo 3: ODST'
                and 'Plasma Rifle' in wl and 'Brute Plasma Rifle' not in wl):
            wl.append('Brute Plasma Rifle')
        # Turrets are placed as vehicles, so they are listed separately and only
        # join the pool when the option is on. Same shape as the grenade fold below.
        if CONFIG.get('turrets_are_weapons'):
            wl += [t for t in (self.mission_turrets.get(mission_id) or []) if t not in wl]
        if CONFIG.get('include_grenades', True):
            wl += [g for g in (self.mission_grenades.get(mission_id) or []) if g not in wl]
        result = []
        for w in wl:
            canon = self.resolve_weapon(w)
            if canon in self.weapon_mods and canon not in result:
                result.append(canon)
        return result or list(self.weapon_mods.keys())

    def get_game_weapons(self, game):
        """Union of every level's weapon pool across a game (that have mods)."""
        weapons = []
        for mid, g in self.mission_games.items():
            if g == game:
                for w in self.get_level_weapons(mid):
                    if w not in weapons:
                        weapons.append(w)
        return weapons or list(self.weapon_mods.keys())

    # ---- Boss (#4) ----
    def mission_note(self, mission_id):
        """A free-text warning halo.json attaches to a level, shown in the patcher.

        For levels whose behaviour is driven by their SCRIPT rather than by tags, so
        the cards that look like they tune it plainly say that they do not — 08b's
        Tartarus fight being the case that cost a play session."""
        return (self.mission_enemies.get(mission_id) or {}).get('note')

    def bosses_for(self, mission_id):
        """Boss names for a mission: those declared in halo.json, plus Brute
        Chieftains when that option is on. Resolved per call rather than baked into
        mission_boss at load, so toggling the option takes effect without a reload."""
        names = list(self.mission_boss.get(mission_id) or [])
        if not CONFIG.get('heroes_are_bosses', True):
            # Heroes off: strip the recurring archetypes wherever they came from,
            # including halo.json's own mission data (Brute Chieftain and Sentinel
            # Enforcer are declared there), and add none. What survives is the named
            # story fights.
            return [n for n in names if n not in HERO_NAMES]
        for key, boss, missions in HERO_OPTIONS:
            if not CONFIG.get(key) or mission_id not in missions:
                continue
            # Halo 3's spec-ops commander is an ALLY -- the allied Elites from
            # Floodgate onward. The existing "Elites are allies in Halo 3" switch
            # suppresses Elite enemy effects there, and it must suppress this too or
            # the two options would contradict each other on the same map. ODST
            # inherits Halo 3's cards and fields no Elites at all, so its own spec-ops
            # switch has to answer to the same rule -- listing only the Halo 3 key here
            # is what let the commander's cards into a played ODST run.
            if (key in ('h3_specops_bosses', 'odst_specops_bosses')
                    and CONFIG.get('ignore_elite_in_h3', True)):
                continue
            if boss not in names:
                names.append(boss)
        return names

    def story_bosses_for(self, mission_id):
        """The named STORY fights this mission has — Tartarus, Regret, the Heretic
        Leader. Recurring archetypes (Chieftains, Enforcers, Zealots) are heroes and
        belong to the Other slot, not to the guaranteed Boss slot.

        `bosses_for` deliberately still returns both: it is what stamps a card's
        validity at patch time, and a hero card is every bit as valid as a boss one."""
        return [n for n in self.bosses_for(mission_id) if n not in HERO_NAMES]

    def heroes_for(self, mission_id):
        """The recurring archetypes this mission fields, after the per-hero options."""
        return [n for n in self.bosses_for(mission_id) if n in HERO_NAMES]

    def mission_has_boss(self, mission_id):
        return bool(self.bosses_for(mission_id))

    def mission_has_story_boss(self, mission_id):
        return bool(self.story_bosses_for(mission_id))

    def get_boss_name(self, mission_id):
        """Every boss this mission fields, joined for DISPLAY.

        NOT for stamping a card. `make_boss_mod` writes this name into the mod and
        `halo_patch.collect_effects` matches it against the mission's boss list, so on
        a level with several heroes the joined string matched nothing and the card was
        dropped at patch time in silence -- available in the run, absent from the
        patcher. Use `draw_boss`, which names exactly one."""
        names = self.bosses_for(mission_id)
        return ", ".join(names) if names else None

    def get_boss_modifiers_filtered(self, mission_id, blacklist, game=None):
        """Boss pool: the boss encounter's OWN mods, so a boss card only ever
        touches the boss. Those mods target the boss's char tag alone, which in
        Halo 2 means they must name fields the boss variant itself holds — a
        field it merely inherits from its parent lives on the parent, and
        patching it there would buff every sibling enemy too.

        Only when a boss has no catered pool yet do we fall back to the general
        negative pool (which hits all enemies), so boss levels still draw a card."""
        mods = []
        for boss in self.bosses_for(mission_id):
            mods.extend(self.boss_mods.get(boss) or self.enemy_mods.get(boss, []))
        specific = self.filter_blacklisted(mods, blacklist, game)
        if specific:
            return specific
        return self.filter_blacklisted(list(self.negative_pool), blacklist, game)

    def boss_pools_for(self, mission_id, blacklist, game=None, names=None):
        """{boss name: its OWN filtered cards} for the bosses this mission fields,
        skipping any whose pool comes out empty.

        `names` narrows it to a subset — the story bosses for the guaranteed Boss
        slot, the heroes for the Other slot — so the two draws cannot poach from
        each other."""
        out = {}
        for boss in (names if names is not None else self.bosses_for(mission_id)):
            mods = self.filter_blacklisted(
                self.boss_mods.get(boss) or self.enemy_mods.get(boss, []),
                blacklist, game)
            if mods:
                out[boss] = mods
        return out

    def draw_boss(self, mission_id, blacklist, game=None, names=None):
        """(boss name, its cards) for ONE boss on this mission, or (None, []).

        `names` restricts the draw to a subset (story bosses, or heroes).

        A boss card names a single character -- `make_boss_mod` stamps that name and
        `halo_patch.collect_effects` matches it against the mission's boss list. With
        several heroes on a level, naming all of them (the old ', '.join) produced a
        name that matched nothing and the card was dropped at patch time without a
        word. So exactly one is drawn.

        Every call draws independently: player 2's roll and each reroll pick their own
        hero rather than inheriting player 1's, so a level with several heroes really
        does spread across them."""
        pools = self.boss_pools_for(mission_id, blacklist, game, names=names)
        if pools:
            boss = random.choice(sorted(pools))
            return boss, pools[boss]
        # No hero has a catered pool yet: fall back to the general negative pool so
        # boss levels still draw something, but still name one boss so the card
        # survives the patcher's filter.
        pool_names = names if names is not None else self.bosses_for(mission_id)
        fallback = self.filter_blacklisted(list(self.negative_pool), blacklist, game)
        if not pool_names or not fallback:
            return None, []
        return random.choice(pool_names), fallback

    def get_games(self):
        return list(self.games)

    def get_game_for_mission(self, mission_id):
        return self.mission_games.get(mission_id)

    def get_missions_for_game(self, game):
        """In halo.json order, NOT sorted by mission id — the same rule mission_list
        already follows, and for the same reason. Sorting broke Halo 2 (Gravemind 07a
        -> Uprising 08a -> High Charity 07b) and breaks ODST harder still, where
        Coastal Highway (l300) would land before Tayari Plaza (sc100). mission_games
        is built by walking halo.json, so plain iteration is already the right order."""
        return [(mid, self.mission_enemies[mid]['name'])
                for mid, g in self.mission_games.items() if g == game]

    def get_mission_list(self):
        return self.mission_list

    @staticmethod
    def _game_ok(mod, game):
        games = mod.get('games')
        if (not games) or (game is None) or (game in games):
            return True
        # A game may INHERIT another's effects. ODST is a later Halo 3 build and
        # shares its tag paths and nearly all its fields, so an effect written for
        # Halo 3 applies there too. Doing it here rather than by adding
        # "Halo 3: ODST" to ~60 halo.json entries keeps the data honest about which
        # engine an effect was authored for, and means an effect added for Halo 3
        # later works in ODST without a second edit that is easy to forget.
        #
        # resolve_gamed already assumes exactly this: a tag or field missing for a
        # game falls back to the nearest EARLIER game, so ODST resolves Halo 3's
        # values with no per-effect entry.
        #
        # Fields ODST actually removed are excluded per effect in halo.json, since
        # inheriting them would only fail later at patch time.
        parent = CONFIG.get('game_inherits', {}).get(game)
        while parent:
            if parent in games:
                return True
            parent = CONFIG.get('game_inherits', {}).get(parent)
        return False

    @staticmethod
    def _is_single_game_mod(mod):
        """Structural test for a mod that can apply in only one game: it carries
        an explicit single-game filter, or its tag is a per-game dict with a
        single game key. A PLAIN-STRING tag is NOT single-game — it's a shared
        tag valid in every game (e.g. matg 'globals\\globals'), the most
        cross-game kind there is.

        Inheritance counts: a Halo 3 effect also applies in ODST, so it reaches two
        games and this option must not strip it. Shared with single_game_badge so the
        card's badge and this filter can never disagree."""
        scope = mod_game_scope(mod)
        return bool(scope) and len(scope) == 1

    def _cross_game_ok(self, mod):
        """Honor the 'remove single-game mods' option. Off by default, so it has
        no effect unless the user enables it in Options."""
        return not (CONFIG.get('remove_single_game_mods') and self._is_single_game_mod(mod))

    def get_mod_label(self, mod, source=None):
        if source:
            return f"{source}{CONFIG['blacklist_label_separator']}{mod['name']}"
        elif mod.get('weapon'):
            return f"{mod['weapon']}{CONFIG['blacklist_label_separator']}{mod['name']}"
        elif mod.get('enemy'):
            return f"{mod['enemy']}{CONFIG['blacklist_label_separator']}{mod['name']}"
        else:
            return f"General{CONFIG['blacklist_label_separator']}{mod['name']}"

    # Cards the Player Health / Player Shield pair supersedes. Starting Health and
    # Starting Shield Modifier scale the scenario profile rather than the pool, and
    # Enemy Damage Reduction is a third route to the same felt outcome.
    SUPERSEDED_VITALITY_CARDS = ('Starting Health Modifier', 'Starting Shield Modifier',
                                 'Enemy Damage Reduction')

    def filter_blacklisted(self, mods, blacklist, game=None):
        drop = (set(self.SUPERSEDED_VITALITY_CARDS)
                if CONFIG.get('remove_superseded_vitality_cards') else ())
        return [m for m in mods
                if self.get_mod_label(m) not in blacklist and self._game_ok(m, game)
                and self._cross_game_ok(m) and not mod_ignored(m)
                # Every offer path funnels through here, so one test covers the
                # initial selection, the New Weapon draw and every reroll — the
                # recurring bug class of fixing only one of them.
                and (m.get('name') not in drop)
                # Enemies the game no longer fields, whose tags nonetheless resolve:
                # the Flood from ODST on, and the Elites from Halo 3 on. Both are
                # excluded at patch time too — this is the offer half of the pair.
                and not _is_absent_flood_mod(m, game)
                and not (CONFIG.get('ignore_elite_in_h3')
                         and _is_allied_elite_mod(m, game))]

    def map_swap_mod(self, weapon_name, game=None):
        """#7: the per-weapon "Map Presence" card — replace a share of the level's
        weapon placements with this weapon. Synthesized rather than stored in
        halo.json so it tracks the weapon list automatically, and because it isn't a
        tag-field edit: the magnitude is a percentage handed to the same swap
        mechanism the patcher's sliders drive (which is why only one is shown)."""
        if not CONFIG.get('weapon_swap_cards'):
            return None
        tag = self.weap_tag_for(weapon_name, game)
        if not tag:
            return None                    # grenades/equipment have no weap tag
        return {
            'name': 'Map Presence',
            'desc': f'Replace a share of the level\'s weapon placements with the '
                    f'{weapon_name}. Enter the percentage to swap.',
            'tag': tag, 'games': [game] if game else [],
            'weapon': weapon_name, 'wildcard': False, 'special': False,
            'dual_only': False, 'skull': None, 'affected_by_skull': None,
            'desc_overrides': None, 'debug_desc': None, 'ignore': None,
            'harder_when': None, 'easier_when': None,
            'init_defaults': None,
            'targets': [{'field': 'Map replacement %', 'map_swap': True}],
        }

    def get_weapon_modifiers_filtered(self, weapon_name, blacklist, game=None):
        mods = list(self.get_weapon_modifiers(weapon_name))
        swap = self.map_swap_mod(weapon_name, game)
        if swap:
            mods.append(swap)
        return self.filter_blacklisted(mods, blacklist, game)

    def get_player_modifiers_filtered(self, weapons, blacklist, game=None):
        """Player pool = the union of each owned weapon's mods (a player may own
        several) plus the general positive pool. `weapons` may be a str or list."""
        if isinstance(weapons, str):
            weapons = [weapons]
        weapon_mods = []
        for w in weapons or []:
            if not w:
                continue
            # A carried piece of equipment contributes its own effects, exactly like a
            # weapon does — which is what keeps them out of the pool until it's taken.
            if self.is_equipment(w):
                weapon_mods.extend(self.get_equipment_modifiers_filtered(w, blacklist, game))
            else:
                # An upgrade weapon draws the BASE's effects instead of its own, so the
                # two don't offer near-identical cards; the patch mirrors them onto the
                # upgrade's tag. Skipped entirely if the player also holds the base, or
                # the same cards would be offered twice.
                base = self.base_for_upgrade(w)
                if base and base not in (weapons or []):
                    w = base
                elif base:
                    continue
                weapon_mods.extend(self.get_weapon_modifiers_filtered(w, blacklist, game))
        # Ability tuning cards are gated by the New Features options: nothing unless the
        # feature is on, then only the cards for an ability this player actually has,
        # and only for abilities enabled in "Offer cards for". (The ability unlocks
        # themselves are offered in the weapon selection, not here.)
        def _sprint_card_ok(m):
            params = {t.get('sprint') for t in (m.get('targets') or [])
                      if isinstance(t, dict) and t.get('sprint')}
            if not params:
                return True                      # not an ability card
            if not CONFIG.get('sprint_feature'):
                return False
            if 'enable' in params:
                # The unlock is offered in the weapon selection now (like H3 equipment),
                # never in the modifier-card draft.
                return False
            abilities = {ability_of_param(p) for p in params} - {None}
            if not abilities & set(ability_cards_for()):
                return False
            # Only offer tuning for an ability the player actually has: the start-with
            # ability when starting with one, else whichever ability item they hold.
            if CONFIG.get('sprint_start_with', True):
                return CONFIG.get('ability_start_which', 'sprint') in abilities
            return bool(abilities & {ability_of_item(w) for w in (weapons or [])})

        # Copy each general mod before tagging it so we never mutate the
        # shared pool entries that random.choice hands back elsewhere.
        general_mods = [{**m, 'source': 'General'}
                        for m in self.filter_blacklisted(self.positive_pool, blacklist, game)
                        if _sprint_card_ok(m)]
        return weapon_mods + general_mods

    def resolve_equipment(self, name):
        """Match a carried item to its Equipment key in halo.json, tolerating
        spacing/case differences between the mission lists ("Bubble Shield") and the
        effect keys ("Bubbleshield") — a silent mismatch here would just drop the
        item's effects with no error."""
        if not name:
            return None
        if name in self.equipment_mods:
            return name
        norm = name.replace(' ', '').lower()
        for k in self.equipment_mods:
            if k.replace(' ', '').lower() == norm:
                return k
        return None

    def get_equipment_modifiers_filtered(self, name, blacklist, game=None):
        key = self.resolve_equipment(name)
        if not key:
            return []
        return self.filter_blacklisted(self.equipment_mods[key], blacklist, game)

    def get_enemy_modifiers_filtered(self, mission_id, blacklist, game=None):
        mods = self.get_enemy_modifiers(mission_id)
        return self.filter_blacklisted(mods, blacklist, game)

    def get_wildcard_modifier_filtered(self, blacklist, game=None):
        # The Other slot's own switches decide whether allies are offered at all.
        if not self.wildcard_pool:
            return None
        # Filter first, then pick, so a blacklisted roll doesn't suppress
        # the wildcard entirely when other choices remain.
        available = [m for m in self.wildcard_pool
                     if self.get_mod_label(m) not in blacklist and self._game_ok(m, game)
                     and self._cross_game_ok(m) and not mod_ignored(m)]
        return random.choice(available) if available else None

    def get_skull_modifier_filtered(self, active_names, blacklist, game=None):
        """#7: draw a Skull to stand in for a normal negative. A skull is a whole-map
        rule, so the same one twice does nothing extra — already-active skulls are
        excluded. Whether skulls are offered at all is the Other slot's own switch."""
        available = [m for m in self.skull_pool
                     if m.get('name') not in active_names
                     and self.get_mod_label(m) not in blacklist
                     and self._game_ok(m, game) and self._cross_game_ok(m)
                     and not mod_ignored(m)]
        return random.choice(available) if available else None

    def get_exhaust_modifier_filtered(self, active_names, blacklist, game=None):
        """#5: draw a one-map Exhaust from the general negative pool, excluding
        negatives already active this run (so there's never an overlap to
        unwind) and anything blacklisted / off-game. None if nothing is left."""
        available = [m for m in self.negative_pool
                     if m.get('name') not in active_names
                     and self.get_mod_label(m) not in blacklist
                     and self._game_ok(m, game) and self._cross_game_ok(m)
                     and not mod_ignored(m)]
        return random.choice(available) if available else None

    def special_names(self):
        """Names of the escalating-odds special effects (#3)."""
        return [m['name'] for m in self.positive_pool if m.get('special')]

class RunState:
    def __init__(self):
        self.mission_id = "a10"
        self.mission_name = "The Pillar of Autumn"
        self.player1_weapon = None   # primary weapon (first of the list)
        self.player2_weapon = None
        self.player1_weapons = []     # a player may accumulate several weapons
        self.player2_weapons = []
        self.selected_pairs = {'player1': None, 'player2': None}
        self.options = {}            # per-run gameplay options snapshot (see OPTION_KEYS)
        self.current_turn = 'player1'
        self.phase = 'weapon_selection'
        self.pairs = []
        self.enemy_mod = None
        self.wildcard_mod = None
        self.weapon_selection_made = False
        self.blacklist = set()
        self.rounds = []
        self.new_weapon_count = 0   # #4: how many new-weapon pairs P1 was offered
        self.special_counters = {}  # special effect name -> rounds since last picked
        # patcher: (tag, name) of every effect already applied to a map — anything not
        # in here is "new" (highlighted / optionally shown first) until the next patch.
        self.patched_effect_keys = set()
        # #5: a player who picked an Exhaust gets one no-negative choice next round.
        self.free_negative_pending = {'player1': False, 'player2': False}
        # #8: the signature of the most recent patch, kept on the RUN rather than
        # on the window so it survives a save/load and travels to the co-op
        # partner — comparing codes is the whole point, and the partner loading
        # the run is exactly who needs to compare. {code, map, difficulty, when}.
        self.last_patch = None

    def weapons_for(self, player):
        return self.player1_weapons if player == 'player1' else self.player2_weapons

    def set_weapon(self, player, weapon):
        """Replace a player's arsenal with a single weapon (or clear it)."""
        weapons = [weapon] if weapon else []
        if player == 'player1':
            self.player1_weapon, self.player1_weapons = weapon, weapons
        else:
            self.player2_weapon, self.player2_weapons = weapon, weapons

    def add_weapon(self, player, weapon):
        """Add a weapon to a player's arsenal without removing existing ones."""
        if not weapon:
            return
        lst = self.weapons_for(player)
        if weapon not in lst:
            lst.append(weapon)
        if player == 'player1' and not self.player1_weapon:
            self.player1_weapon = weapon
        elif player == 'player2' and not self.player2_weapon:
            self.player2_weapon = weapon

    def to_dict(self):
        # `rounds` is the source of truth for the completed selection; the
        # top-level fields are a convenience snapshot derived from the last
        # round (both players' enemies included).
        last = self.rounds[-1] if self.rounds else None
        p1 = self.selected_pairs['player1']
        p2 = self.selected_pairs['player2']
        return {
            "tool_version": VERSION,
            "options": {k: CONFIG.get(k) for k in OPTION_KEYS},
            "mission": {"id": self.mission_id, "name": self.mission_name},
            "players": {
                "player1": {
                    "weapon": self.player1_weapon,
                    "weapons": list(self.player1_weapons),
                    "selected_mod": p1['player1_mod'] if p1 else None
                },
                "player2": {
                    "weapon": self.player2_weapon,
                    "weapons": list(self.player2_weapons),
                    "selected_mod": p2['player2_mod'] if p2 else None
                }
            },
            "enemy_mod": (last['enemy1'] if last else (p1['enemy_mod'] if p1 else None)),
            "enemy_mod2": (last['enemy2'] if last else (p2['enemy_mod'] if p2 else None)),
            "wildcard_mod": (last['wildcard'] if last else (p1.get('wildcard_mod') if p1 else None)),
            "phase": self.phase,
            "current_turn": self.current_turn,
            "timestamp": datetime.now().isoformat(),
            "blacklist": list(self.blacklist),
            "special_counters": dict(self.special_counters),
            "free_negative_pending": dict(self.free_negative_pending),
            "patched_effect_keys": [list(k) for k in self.patched_effect_keys],
            "last_patch": self.last_patch,
            "rounds": self.rounds
        }

    @classmethod
    def from_dict(cls, data):
        state = cls()
        # Restore the options this run was played with (applied to the live CONFIG
        # so the loaded run behaves as saved). Only known option keys are honored.
        opts = data.get('options') or {}
        state.options = {k: opts[k] for k in OPTION_KEYS if k in opts}
        for k, v in state.options.items():
            CONFIG[k] = v
        state.mission_id = data.get('mission', {}).get('id', 'a10')
        state.mission_name = data.get('mission', {}).get('name', 'The Pillar of Autumn')
        p1data = data.get('players', {}).get('player1', {})
        p2data = data.get('players', {}).get('player2', {})
        state.player1_weapon = p1data.get('weapon')
        state.player2_weapon = p2data.get('weapon')
        # Prefer the weapon list; fall back to the single primary for old saves.
        state.player1_weapons = p1data.get('weapons') or ([state.player1_weapon] if state.player1_weapon else [])
        state.player2_weapons = p2data.get('weapons') or ([state.player2_weapon] if state.player2_weapon else [])
        state.rounds = data.get('rounds', [])
        state.patched_effect_keys = {tuple(k) for k in data.get('patched_effect_keys', [])}
        lp = data.get('last_patch')
        state.last_patch = lp if isinstance(lp, dict) else None

        p1_mod = p1data.get('selected_mod')
        p2_mod = p2data.get('selected_mod')

        last = state.rounds[-1] if state.rounds else None
        if last:
            enemy1 = last.get('enemy1')
            enemy2 = last.get('enemy2')
            wildcard = last.get('wildcard')
            p1_mod = p1_mod or last.get('player1', {}).get('mod')
            p2_mod = p2_mod or last.get('player2', {}).get('mod')
        else:
            enemy1 = data.get('enemy_mod')
            enemy2 = data.get('enemy_mod2', data.get('enemy_mod'))
            wildcard = data.get('wildcard_mod')

        if p1_mod and p2_mod and (enemy1 or enemy2):
            state.selected_pairs['player1'] = {
                'player1_mod': p1_mod, 'player2_mod': p2_mod,
                'enemy_mod': enemy1, 'wildcard_mod': wildcard
            }
            state.selected_pairs['player2'] = {
                'player1_mod': p1_mod, 'player2_mod': p2_mod,
                'enemy_mod': enemy2, 'wildcard_mod': wildcard
            }
            state.weapon_selection_made = True

        state.phase = data.get('phase', 'weapon_selection')
        state.current_turn = data.get('current_turn', 'player1')
        state.blacklist = set(data.get('blacklist', []))
        state.special_counters = dict(data.get('special_counters', {}))
        fnp = data.get('free_negative_pending') or {}
        state.free_negative_pending = {'player1': bool(fnp.get('player1')),
                                       'player2': bool(fnp.get('player2'))}
        return state

class WeaponSelectionCard(QGroupBox):
    def __init__(self, pair_data, parent=None, is_player2=False, mode='initial'):
        super().__init__(parent)
        self.pair_data = pair_data
        self.parent_widget = parent
        self.is_player2 = is_player2
        self.mode = mode  # 'initial' start-of-run pick, or 'add' New Weapon button (#3)
        self.setup_ui()

    def setup_ui(self):
        if self.layout() is not None:
            layout = self.layout()
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
        else:
            layout = QVBoxLayout(self)
            self.setLayout(layout)

        layout.setSpacing(10)
        db = self.parent_widget.db if self.parent_widget else None
        item = self.pair_data.get('weapon')
        ability = ability_of_item(item)
        is_sprint = bool(ability)          # any flashlight-key ability, not just sprint
        is_equip = bool(db and db.is_equipment(item))
        player_text = "PLAYER 2" if self.is_player2 else "PLAYER 1"
        if self.mode == 'add':
            heading = (item.split(' ', 1)[0] + " ABILITY" if ability
                       else ("🎒 NEW EQUIPMENT" if is_equip else "🔫 NEW WEAPON"))
        else:
            heading = "CHOICE"
        title = QLabel(f"{player_text} - {heading} {self.pair_data['id']}")
        title.setStyleSheet(f"font-weight: bold; font-size: {CONFIG['font_size_title']}px; color: #e0e0e0;")
        layout.addWidget(title)

        # An ability is not a gun — render it with the equipment scheme, so it reads as
        # the special pick it is, and describe it instead of listing modifiers.
        scheme = MOD_COLORS['equipment'] if (is_equip or is_sprint) else MOD_COLORS['green']
        group_title = "ABILITY" if is_sprint else ("EQUIPMENT" if is_equip else "WEAPON")
        weapon_group = QGroupBox(group_title)
        weapon_group.setStyleSheet(f"border: 2px solid #{scheme['border']}; border-radius: 4px; "
                                   f"padding: 10px; margin-top: 5px; background-color: #{scheme['bg']};")
        weapon_layout = QVBoxLayout(weapon_group)
        kind = "Ability" if is_sprint else ("Equipment" if is_equip else "Weapon")
        weapon_label = QLabel(f"{kind}: {self.pair_data['weapon']}")
        weapon_label.setStyleSheet(f"font-weight: bold; font-size: {CONFIG['font_size_weapon']}px; "
                                   f"color: #{scheme['border']};")
        weapon_layout.addWidget(weapon_label)
        if ability:
            sub = QLabel(ABILITY_BLURBS.get(ability, "A flashlight-key ability."))
            sub.setWordWrap(True)
        else:
            mod_count = len(self.pair_data.get('modifiers', []))
            sub = QLabel(f"Available modifiers: {mod_count}")
        sub.setStyleSheet(f"color: #aaa; font-size: {CONFIG['font_size_desc']}px;")
        weapon_layout.addWidget(sub)
        layout.addWidget(weapon_group)

        if self.pair_data['enemy_mod']:
            enemy_widget = self.create_mod_widget(self.pair_data['enemy_mod'], "ENEMY (tied to this choice)", "red")
            layout.addWidget(enemy_widget)

        reroll_btn = QPushButton("🔁 Reroll This Choice")
        reroll_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #2a3a5a;
                color: white;
                font-weight: bold;
                font-size: {CONFIG['font_size_desc']}px;
                padding: 8px;
                border-radius: 5px;
            }}
            QPushButton:hover {{ background-color: #3a5a7a; }}
        """)
        reroll_btn.clicked.connect(self.on_reroll)
        layout.addWidget(reroll_btn)

        # Every weapon card can blacklist, not just the New Weapon ones — the
        # blacklist is a run-long control and the starting pick is where a weapon
        # you never want to see is most likely to turn up.
        blacklist_btn = QPushButton("🚫 Blacklist Weapon")
        blacklist_btn.setToolTip("Never offer this weapon again this run")
        blacklist_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #5a2a2a; color: white; font-weight: bold;
                font-size: {CONFIG['font_size_desc']}px; padding: 8px; border-radius: 5px;
            }}
            QPushButton:hover {{ background-color: #7a3a3a; }}
        """)
        blacklist_btn.clicked.connect(self.on_blacklist_weapon)
        layout.addWidget(blacklist_btn)

        select_btn = QPushButton("ADD WEAPON" if self.mode == 'add' else "SELECT WEAPON")
        select_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #2a5a2a;
                color: white;
                font-weight: bold;
                font-size: {CONFIG['font_size_button']}px;
                padding: 12px;
                border-radius: 5px;
            }}
            QPushButton:hover {{ background-color: #3a7a3a; }}
        """)
        select_btn.clicked.connect(self.on_select)
        layout.addWidget(select_btn)

        # #2/#3: fancier border for special weapons (dual wield, upgrades).
        weapon = self.pair_data.get('weapon', '')
        if weapon.startswith('Dual '):
            self.setStyleSheet("QGroupBox { border: 3px double #FFD700; border-radius: 8px; "
                               "padding: 15px; background-color: #12100a; }")
        elif weapon in weapon_upgrades():
            self.setStyleSheet("QGroupBox { border: 3px double #FF8C00; border-radius: 8px; "
                               "padding: 15px; background-color: #120c08; }")
        else:
            self.setStyleSheet("QGroupBox { border: 1px solid #444; border-radius: 8px; "
                               "padding: 15px; background-color: #0d0d0d; }")
        # 'add' cards carry a tied negative + an extra button, so they need more
        # room than the start-of-run weapon picks or they get squished.
        # Same screen-derived width as PairCard so the two screens line up. Height
        # still hugs content here: these cards appear on their own selection screen,
        # not in a row that needs matching heights.
        self.setFixedWidth(card_metrics()[0])
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Maximum)

    def create_mod_widget(self, mod_data, label, color):
        scheme = MOD_COLORS.get(color, MOD_COLORS['red'])
        widget = QGroupBox(label)
        widget.setStyleSheet(f"""
            QGroupBox {{
                border: 1px solid #{scheme['border']};
                border-radius: 4px;
                padding: 10px;
                margin-top: 5px;
                background-color: #{scheme['bg']};
            }}
        """)
        layout = QVBoxLayout(widget)
        source = mod_data.get('enemy', 'General')
        name = QLabel(f"{source}: {mod_data.get('name', 'Unknown')}")
        name.setStyleSheet(f"font-weight: bold; font-size: {CONFIG['font_size_name']}px; color: #e0e0e0;")
        layout.addWidget(name)
        badge = single_game_badge(mod_data)   # #2: single-game indicator
        if badge:
            bl = QLabel(badge)
            bl.setStyleSheet(f"color: #d0a24a; font-size: {CONFIG['font_size_small']}px; font-weight: bold;")
            layout.addWidget(bl)
        game = self.parent_widget._current_game() if self.parent_widget else None
        games = self.parent_widget.db.get_games() if self.parent_widget else None
        if heretic_combine_active(mod_data, game, games):   # reflect the combine option
            combo = QLabel("⛨ Also tunes his decoy holograms (Combine option on)")
            combo.setWordWrap(True)
            combo.setStyleSheet(f"color: #c07af0; font-size: {CONFIG['font_size_small']}px; font-weight: bold;")
            layout.addWidget(combo)
        _rs = self.parent_widget.run_state if self.parent_widget else None
        _sk = skull_conflict(mod_data, _rs)
        if _sk:     # only shown while that skull is actually active in the run
            warn = QLabel(f"☠ Affected by Skull: {_sk}")
            warn.setWordWrap(True)
            warn.setStyleSheet(f"color: #{MOD_COLORS['skull']['border']}; "
                               f"font-size: {CONFIG['font_size_small']}px; font-weight: bold;")
            layout.addWidget(warn)
        desc = QLabel(effect_desc(mod_data, game, games))
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: #aaa; font-size: {CONFIG['font_size_desc']}px;")
        _dbg = effect_debug_desc(mod_data, game, games)
        if _dbg:
            desc.setToolTip(_dbg)
        layout.addWidget(desc)
        meta = card_meta_text(mod_data, game, games)   # #3: hideable Tag/Fields lines
        if meta:
            tag_field = QLabel(meta)
            tag_field.setStyleSheet(f"color: #666; font-size: {CONFIG['font_size_small']}px; font-family: monospace;")
            tag_field.setWordWrap(True)   # #1: wrap long "Fields:" text instead of clipping
            layout.addWidget(tag_field)
        blacklist_btn = QPushButton("🚫 Blacklist")
        blacklist_btn.setMaximumWidth(100)
        blacklist_btn.setToolTip("Add this modifier to blacklist")
        blacklist_btn.clicked.connect(lambda: self.on_blacklist(mod_data, source=source))
        layout.addWidget(blacklist_btn)
        return widget

    def on_select(self):
        if not self.parent_widget:
            return
        player = 'player2' if self.is_player2 else 'player1'
        if self.mode == 'add':
            self.parent_widget.on_manual_weapon_selected(player, self.pair_data['id'])
        elif self.is_player2:
            self.parent_widget.on_weapon_selected_p2(self.pair_data['id'])
        else:
            self.parent_widget.on_weapon_selected(self.pair_data['id'])

    def on_reroll(self):
        if not self.parent_widget:
            return
        player = 'player2' if self.is_player2 else 'player1'
        if self.mode == 'add':
            self.parent_widget.reroll_manual_weapon(self.pair_data['id'], player)
        elif self.is_player2:
            self.parent_widget.reroll_weapon_choice_p2(self.pair_data['id'])
        else:
            self.parent_widget.reroll_weapon_choice_p1(self.pair_data['id'])

    def on_blacklist_weapon(self):
        # Mirrors on_reroll: blacklisting rerolls the card, so it has to reroll
        # through the SAME path this card's reroll button uses.
        if not self.parent_widget:
            return
        player = 'player2' if self.is_player2 else 'player1'
        weapon = self.pair_data['weapon']
        if self.mode == 'add':
            self.parent_widget.blacklist_manual_weapon(weapon, self.pair_data['id'], player)
        else:
            self.parent_widget.blacklist_weapon_choice(weapon, self.pair_data['id'], player)

    def on_blacklist(self, mod_data, source=None):
        if self.parent_widget:
            self.parent_widget.add_to_blacklist(mod_data, source)

class PairCard(QGroupBox):
    def __init__(self, pair, parent=None, show_player1=True, show_player2=True):
        super().__init__(parent)
        self.pair = pair
        self.parent_widget = parent
        self.show_player1 = show_player1
        self.show_player2 = show_player2
        self.setup_ui()

    def setup_ui(self):
        if self.layout() is not None:
            layout = self.layout()
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
        else:
            layout = QVBoxLayout(self)
            self.setLayout(layout)

        layout.setSpacing(8)
        # Tight top/left margins so there's no dead space above the PAIR title
        # or between it and the first card.
        layout.setContentsMargins(10, 4, 10, 10)
        player_text = ""
        if self.show_player1 and not self.show_player2:
            player_text = "PLAYER 1 - "
        elif self.show_player2 and not self.show_player1:
            player_text = "PLAYER 2 - "
        title = QLabel(f"{player_text}PAIR {self.pair['id']}")
        title.setStyleSheet(f"font-weight: bold; font-size: {CONFIG['font_size_title']}px; color: #e0e0e0; margin: 0; padding: 0;")
        layout.addWidget(title)

        # Three fixed bands — player card(s), enemy/negative, third slot — each given
        # the same stretch. That keeps the negative block starting at the same height
        # on every card in the row, even when a card leaves a slot empty, instead of
        # each block floating to wherever the one above it happened to end.
        positive, negative, third = [], [], []

        # The positive (player) card is replaced by a new-weapon offer when the
        # pair rolled one (#4); the enemy/negative card below still shows.
        db = self.parent_widget.db if self.parent_widget else None

        def _new_heading(player_label):
            nw = self.pair.get('new_weapon')
            tag = "🎒 NEW EQUIPMENT" if (db and db.is_equipment(nw)) else "🔫 NEW WEAPON"
            return f"{player_label} - {tag}"

        if self.show_player1:
            if self.pair.get('new_weapon'):
                positive.append(self.create_weapon_widget(
                    self.pair['new_weapon'], _new_heading("PLAYER 1"), 'player1'))
            elif self.pair['player1_mod']:
                w1 = self.pair['player1_mod'].get('weapon')
                positive.append(self.create_mod_widget(
                    self.pair['player1_mod'],
                    f"PLAYER 1 ({w1})" if w1 else "Player (General)",
                    "green", 'player1'))

        if self.show_player2:
            if self.pair.get('new_weapon'):
                positive.append(self.create_weapon_widget(
                    self.pair['new_weapon'], _new_heading("PLAYER 2"), 'player2'))
            elif self.pair['player2_mod']:
                w2 = self.pair['player2_mod'].get('weapon')
                positive.append(self.create_mod_widget(
                    self.pair['player2_mod'],
                    f"PLAYER 2 ({w2})" if w2 else "Player (General)",
                    "green", 'player2'))

        if self.pair['enemy_mod']:
            negative.append(self.create_mod_widget(self.pair['enemy_mod'], "ENEMY", "red", 'enemy'))
        elif self.pair.get('no_negative'):
            # #5: exhaust reward — this pair carries no enemy buff.
            free = QLabel("✦ NO ENEMY BUFF  (exhaust reward)")
            free.setStyleSheet("color: #00E676; font-weight: bold; font-size: "
                               f"{CONFIG['font_size_name']}px; padding: 8px; "
                               "border: 1px dashed #00E676; border-radius: 4px; "
                               "background-color: #0a2012;")
            free.setWordWrap(True)
            negative.append(free)

        # The guaranteed Boss card, on a level with a named story fight.
        if self.pair.get('boss_mod'):
            boss_name = self.pair['boss_mod'].get('boss') or self.pair['boss_mod'].get('enemy', 'Boss')
            third.append(self.create_mod_widget(self.pair['boss_mod'], f"☠ BOSS: {boss_name}", "boss", 'boss'))

        # The OTHER slot — exactly one of these four, drawn together (see
        # RunEnhancer._draw_other). Each keeps its own colour and its own reroll and
        # blacklist handle, because they are different KINDS of card, not one card
        # with four faces.
        if self.pair.get('hero_mod'):
            hero_name = (self.pair['hero_mod'].get('boss')
                         or self.pair['hero_mod'].get('enemy', 'Hero'))
            third.append(self.create_mod_widget(
                self.pair['hero_mod'], f"⚔ HERO: {hero_name}", "boss", 'hero'))

        # "Ally" is what the player sees; the stored key stays `wildcard_mod` so every
        # saved run still loads.
        if self.pair['wildcard_mod']:
            third.append(self.create_mod_widget(self.pair['wildcard_mod'], "🎲 ALLY", "gold", 'wildcard'))

        if self.pair.get('exhaust_mod'):
            third.append(self.create_mod_widget(
                self.pair['exhaust_mod'], "🜂 EXHAUST (one map)", "exhaust", 'exhaust'))

        if self.pair.get('skull_mod'):
            third.append(self.create_mod_widget(
                self.pair['skull_mod'], "💀 SKULL", "skull", 'skull'))

        for band in (positive, negative, third):
            holder = QWidget()
            hl = QVBoxLayout(holder)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(6)
            for w in band:
                hl.addWidget(w)
            hl.addStretch()          # content sits at the top of its band
            layout.addWidget(holder, 1)

        select_btn = QPushButton("SELECT")
        select_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #2a5a2a;
                color: white;
                font-weight: bold;
                font-size: {CONFIG['font_size_button']}px;
                padding: 12px;
                border-radius: 5px;
            }}
            QPushButton:hover {{ background-color: #3a7a3a; }}
            QPushButton:disabled {{ background-color: #444; color: #888; }}
        """)
        select_btn.clicked.connect(self.on_select)
        layout.addWidget(select_btn)

        self.setStyleSheet("QGroupBox { border: 1px solid #444; border-radius: 8px; padding: 6px 12px 12px 12px; background-color: #0d0d0d; }")
        # One screen-derived size for every card. Letting the height hug its content
        # meant each reroll resized the cards and shifted the positive/negative blocks
        # to different heights across the row; a fixed size holds them in place.
        cw, ch = card_metrics()
        self.setFixedSize(cw, ch)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def on_blacklist_weapon(self, weapon, mod_type):
        if self.parent_widget:
            self.parent_widget.add_weapon_to_blacklist(weapon, self.pair['id'], mod_type)

    def create_weapon_widget(self, weapon, label, mod_type):
        """Offer to add a weapon (or, in H3 with the option on, a piece of
        equipment) to the arsenal — replaces the positive card."""
        db = self.parent_widget.db if self.parent_widget else None
        is_equip = bool(db and db.is_equipment(weapon))
        scheme = MOD_COLORS['equipment'] if is_equip else MOD_COLORS['green']
        widget = QGroupBox(label)
        widget.setStyleSheet(f"""
            QGroupBox {{
                border: 2px solid #{scheme['border']};
                border-radius: 4px; padding: 10px; margin-top: 5px;
                background-color: #{scheme['bg']};
            }}
        """)
        layout = QVBoxLayout(widget)
        name = QLabel(f"➕ Add {'equipment' if is_equip else 'weapon'}: {weapon}")
        name.setStyleSheet(f"font-weight: bold; font-size: {CONFIG['font_size_name']}px; "
                           f"color: #{scheme['border']};")
        layout.addWidget(name)
        info = QLabel(f"Selecting this pair adds the {'equipment' if is_equip else 'weapon'} to "
                      "your arsenal instead of a positive effect. The enemy effect below still applies.")
        info.setWordWrap(True)
        info.setStyleSheet(f"color: #aaa; font-size: {CONFIG['font_size_desc']}px;")
        layout.addWidget(info)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)
        reroll_btn = QPushButton("🔁 Reroll")
        reroll_btn.setMaximumWidth(100)
        reroll_btn.setToolTip("Roll a different weapon")
        reroll_btn.clicked.connect(lambda: self.on_reroll(mod_type))
        button_layout.addWidget(reroll_btn)
        blacklist_btn = QPushButton("🚫 Blacklist")
        blacklist_btn.setMaximumWidth(100)
        blacklist_btn.setToolTip("Never offer this weapon again this run")
        blacklist_btn.clicked.connect(lambda: self.on_blacklist_weapon(weapon, mod_type))
        button_layout.addWidget(blacklist_btn)
        layout.addLayout(button_layout)
        return widget

    def create_mod_widget(self, mod_data, label, color, mod_type):
        if mod_type == 'player1' or mod_type == 'player2':
            if mod_data.get('source') == 'General':
                source = 'General'
            else:
                # weaponless = general player effect; equipment names its own piece
                source = mod_data.get('weapon') or mod_data.get('equipment') or 'General'
        elif mod_type == 'enemy':
            source = 'Skull' if mod_data.get('skull') else mod_data.get('enemy', 'General')
        elif mod_type in ('boss', 'hero'):
            source = mod_data.get('boss') or mod_data.get('enemy',
                                                          'Hero' if mod_type == 'hero' else 'Boss')
        elif mod_type == 'exhaust':
            source = 'Exhaust'
        elif mod_type == 'skull':
            source = 'Skull'
        else:
            source = 'Ally'

        scheme = MOD_COLORS.get(color, MOD_COLORS['green'])
        border_width = 2 if color in ('gold', 'boss', 'exhaust') else 1  # emphasize 3rd-slot cards
        special = bool(mod_data.get('special'))  # #3: escalating-odds effect
        dual = bool(mod_data.get('dual_only'))   # dual-wield-only effect
        skull = bool(mod_data.get('skull'))      # #7: whole-map rule
        if skull:
            scheme = MOD_COLORS['skull']
            border_width = 3
        elif special:
            scheme = MOD_COLORS['special']
            border_width = 3
        elif dual:
            scheme = MOD_COLORS['dual']
            border_width = 3
        # Sprint cards read as H3-style equipment — give them the equipment border.
        if any(isinstance(t, dict) and t.get('sprint')
               for t in (mod_data.get('targets') or [])):
            scheme = MOD_COLORS['equipment']
            border_width = 2
        # #7: skull cards get the glyph as a faint background watermark.
        bg_img = ''
        if skull:
            wm = skull_watermark_path()
            if wm:
                bg_img = (f"background-image: url({str(wm).replace(chr(92), '/')});"
                          "background-repeat: no-repeat; background-position: center;")
        widget = QGroupBox(label)
        widget.setStyleSheet(f"""
            QGroupBox {{
                border: {border_width}px {'double' if special or dual or skull else 'solid'} #{scheme['border']};
                border-radius: 4px;
                padding: 10px;
                margin-top: 5px;
                background-color: #{scheme['bg']};
                {bg_img}
            }}
        """)
        layout = QVBoxLayout(widget)
        marker = '☠ ' if skull else '★ ' if special else '⚔ ' if dual else ''
        name = QLabel(f"{marker}{source}: {mod_data.get('name', 'Unknown')}")
        name.setStyleSheet("font-weight: bold; font-size: %dpx; color: %s;"
                           % (CONFIG['font_size_name'],
                              '#D8D0C0' if skull else '#00E5FF' if special
                              else '#00E676' if dual else '#e0e0e0'))
        layout.addWidget(name)
        badge = single_game_badge(mod_data)   # #2: single-game indicator
        if badge:
            bl = QLabel(badge)
            bl.setStyleSheet(f"color: #d0a24a; font-size: {CONFIG['font_size_small']}px; font-weight: bold;")
            layout.addWidget(bl)
        game = self.parent_widget._current_game() if self.parent_widget else None
        games = self.parent_widget.db.get_games() if self.parent_widget else None
        if heretic_combine_active(mod_data, game, games):   # reflect the combine option
            combo = QLabel("⛨ Also tunes his decoy holograms (Combine option on)")
            combo.setWordWrap(True)
            combo.setStyleSheet(f"color: #c07af0; font-size: {CONFIG['font_size_small']}px; font-weight: bold;")
            layout.addWidget(combo)
        _rs = self.parent_widget.run_state if self.parent_widget else None
        _sk = skull_conflict(mod_data, _rs)
        if _sk:     # only shown while that skull is actually active in the run
            warn = QLabel(f"☠ Affected by Skull: {_sk}")
            warn.setWordWrap(True)
            warn.setStyleSheet(f"color: #{MOD_COLORS['skull']['border']}; "
                               f"font-size: {CONFIG['font_size_small']}px; font-weight: bold;")
            layout.addWidget(warn)
        desc = QLabel(effect_desc(mod_data, game, games))
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: #aaa; font-size: {CONFIG['font_size_desc']}px;")
        _dbg = effect_debug_desc(mod_data, game, games)
        if _dbg:
            desc.setToolTip(_dbg)
        layout.addWidget(desc)
        meta = card_meta_text(mod_data, game, games)   # #3: hideable Tag/Fields lines
        if meta:
            tag_field = QLabel(meta)
            tag_field.setStyleSheet(f"color: #666; font-size: {CONFIG['font_size_small']}px; font-family: monospace;")
            tag_field.setWordWrap(True)   # #1: wrap long "Fields:" text instead of clipping
            layout.addWidget(tag_field)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)

        reroll_btn = QPushButton("🔁 Reroll")
        reroll_btn.setMaximumWidth(100)
        reroll_btn.setToolTip("Reroll this effect")
        reroll_btn.clicked.connect(lambda: self.on_reroll(mod_type))
        button_layout.addWidget(reroll_btn)

        blacklist_btn = QPushButton("🚫 Blacklist")
        blacklist_btn.setMaximumWidth(100)
        blacklist_btn.setToolTip("Add this modifier to blacklist")
        if mod_type == 'player1' or mod_type == 'player2':
            if mod_data.get('source') == 'General':
                bl_source = 'General'
            else:
                bl_source = mod_data.get('weapon', 'Unknown Weapon')
        elif mod_type == 'enemy':
            bl_source = mod_data.get('enemy', 'General')
        elif mod_type == 'boss':
            # Boss effects come from the enemy/negative pool; blacklist by their real source.
            bl_source = mod_data.get('enemy', 'General')
        elif mod_type == 'exhaust':
            bl_source = 'Exhaust'
        else:
            bl_source = 'Ally'
        blacklist_btn.clicked.connect(lambda: self.on_blacklist(mod_data, bl_source, self.pair['id'], mod_type))
        button_layout.addWidget(blacklist_btn)

        layout.addLayout(button_layout)
        return widget

    def on_select(self):
        if self.parent_widget:
            self.parent_widget.on_pair_selected(self.pair['id'])

    def on_reroll(self, mod_type):
        if self.parent_widget:
            self.parent_widget.on_reroll_modifier(self.pair['id'], mod_type)
            
    def on_blacklist(self, mod_data, source, pair_id=None, mod_type=None):
        if self.parent_widget:
            self.parent_widget.add_to_blacklist(mod_data, source, pair_id, mod_type)

class StartDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.choice = None
        self.loaded_state = None
        self.loaded_path = None     # where a loaded run came from (see _open_run_file)
        self.setWindowTitle("Halo Run Enhancer")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setMinimumHeight(200)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        title = QLabel("🎯 HALO RUN ENHANCER")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #4CAF50;")
        layout.addWidget(title)
        subtitle = QLabel("Enhance your Halo run with tied modifier pairs")
        subtitle.setStyleSheet("color: #aaa; font-size: 12px;")
        layout.addWidget(subtitle)
        layout.addSpacing(20)
        new_btn = QPushButton("🆕 New Run")
        new_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a5a2a;
                color: white;
                font-weight: bold;
                padding: 15px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3a7a3a;
            }
        """)
        new_btn.clicked.connect(lambda: self.accept_choice('new'))
        layout.addWidget(new_btn)
        load_btn = QPushButton("📂 Load Saved Run")
        load_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a3a5a;
                color: white;
                font-weight: bold;
                padding: 15px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3a5a7a;
            }
        """)
        load_btn.clicked.connect(self.load_saved_run)
        layout.addWidget(load_btn)
        # Co-op shortcut: grab whatever the other machine shared most recently.
        if (CONFIG.get('shared_session_dir') or '').strip():
            shared_btn = QPushButton("🤝 Load Latest Shared Session")
            shared_btn.setToolTip("Open the newest run in the shared session folder, "
                                  "magnitudes included.")
            shared_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2a4a5a;
                    color: white;
                    font-weight: bold;
                    padding: 15px;
                    border-radius: 5px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #3a6a7a;
                }
            """)
            shared_btn.clicked.connect(self.load_latest_shared)
            layout.addWidget(shared_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: #888;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
        """)
        layout.addWidget(cancel_btn)
    
    def accept_choice(self, choice):
        self.choice = choice
        self.accept()
    
    def load_saved_run(self):
        start = (CONFIG.get('shared_session_dir') or '').strip() or "selections/"
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Saved Run",
            start,
            "Halo Run (*.run);;JSON Files (*.json)"
        )
        if file_path:
            self._open_run_file(file_path)

    def load_latest_shared(self):
        """One-click pickup of the newest run in the shared folder — the other machine's
        end of the sharing workflow."""
        folder = (CONFIG.get('shared_session_dir') or '').strip()
        if not folder:
            QMessageBox.information(self, "No shared folder",
                                    "Set a shared session folder in Options first "
                                    "(point both machines at the same synced folder).")
            return
        runs = sorted(Path(folder).glob('*.run'), key=lambda p: p.stat().st_mtime,
                      reverse=True) if Path(folder).is_dir() else []
        if not runs:
            QMessageBox.information(self, "Nothing shared yet",
                                    f"No .run files in:\n{folder}")
            return
        self._open_run_file(str(runs[0]))

    def _open_run_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Not a valid run",
                                 f"Couldn't read this file as a run:\n{e}")
            return
        if not is_valid_run(data):
            QMessageBox.critical(self, "Not a valid run",
                                 "This file isn't a Halo Run Enhancer save "
                                 "(missing the run marker/structure).")
            return
        try:
            self.loaded_state = RunState.from_dict(data)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load run:\n{str(e)}")
            return
        # Remember where it came from, so saving offers to write back to the SAME file
        # instead of proposing a fresh timestamped name every round.
        self.loaded_path = file_path
        # Merge any magnitudes the run carries, so the patch reproduces the sharer's
        # numbers without touching this machine's other remembered values.
        n = merge_presets(data.get('magnitudes') or {})
        if n:
            QMessageBox.information(self, "Run loaded",
                                    f"Loaded {Path(file_path).name}\n\n"
                                    f"{n} shared magnitude(s) merged — patching this run "
                                    "will reproduce the same values.")
        self.choice = 'load'
        self.accept()


def row_value(widget):
    """The text of a magnitude row, whichever widget it uses.

    Most rows are a QLineEdit holding an operator; a `choice` row is a QComboBox
    holding an enum option name. Every read goes through here so adding the combo
    could not break the places that used to call .text() directly."""
    return widget.currentText() if hasattr(widget, 'currentText') else widget.text()


# An enum's options are stored in a different ORDER per game (Reach moved Quiet and
# Loud on the AI noise enum), but the names mean the same thing everywhere. Since a
# choice is applied by name the display order is free, so pin it: keyed by the exact
# set of option names, so it covers every tag carrying that enum (weap Firing Noise,
# biped/vehicle Constant Sound Volume, projectile Impact/Detonation Noise) without
# naming any of them. The order chosen is the one four of the five games store.
CHOICE_DISPLAY_ORDER = {
    frozenset(('silent', 'quiet', 'medium', 'loud', 'shout')):
        ('silent', 'medium', 'loud', 'shout', 'quiet'),
}


def choice_option_names(opts, allowed=None):
    """Display order for a `choice` row's options: the canonical order if this enum
    has one, else by stored value so the list reads the way the tag is ordered.

    `allowed` narrows the list to the options a card actually wants to offer. The
    plugin knows every value the FIELD can hold; whether all of them are worth
    offering is a design question the card answers -- Movement Penalty Type offers
    Always and When Zoomed Or Reloading but deliberately not When Zoomed, because
    turrets cannot be reloaded yet and the two would behave identically today.
    Matched case-insensitively so halo.json can write them readably."""
    canon = CHOICE_DISPLAY_ORDER.get(frozenset(opts))
    names = list(canon) if canon else [n for _v, n in sorted((v, n) for n, v in opts.items())]
    if allowed:
        keep = {str(a).strip().lower() for a in allowed}
        names = [n for n in names if n.lower() in keep]
    return [n.title() for n in names]


def target_tag(eff, target):
    """The tag THIS target writes to.

    Normally a card has one tag and every target lands on it, but a target may name
    its own -- Firing Noise sets the weapon's enum and the same value on its
    projectile's Impact/Detonation Noise, which live on a different tag entirely.
    Every read that displays a vanilla value has to follow the same redirect the
    write does, or the row shows a number from the wrong tag."""
    return target.get('tag') or eff.get('tag')


def choice_preset_key(eff, field):
    """Remembered pick for a choice row -- deliberately WITHOUT the game.

    A magnitude is a number whose right value can differ per engine, so preset_key
    scopes those by game (and by the per-game tag path). A choice is a NAME, and the
    name means the same thing in every game, so scoping it that way meant a pick made
    on Halo 3 was invisible on Reach and the card fell back to the vanilla value.
    Keyed on the weapon (or the effect name, for cards that have no weapon) so it
    survives the tag path changing between games as well."""
    return 'choice||%s||%s||%s' % (eff.get('weapon') or eff.get('name'),
                                   eff.get('name'), field)


def is_operator_box(widget):
    """True only for the QLineEdit rows that hold an OPERATOR.

    self.rows also carries read-only boxes (derived / fixed-set / sprint enabler) and,
    since Firing Noise, QComboBoxes for `choice` targets. A combo has no isReadOnly at
    all, so normalisation, focus navigation and the operator collectors have to test
    for the real thing rather than assume a line edit -- clicking Patch Map raised
    AttributeError on the first combo it met."""
    return widget is not None and hasattr(widget, 'isReadOnly') and not widget.isReadOnly()


class MagnitudeEditorDialog(QDialog):
    """Per-run editor: lists the selected effects grouped by tag, shows each
    field's vanilla value, takes a typed operator (-n/+n/*n or xn/=n) per target
    (pre-filled from the presets library), then backs up and patches the .map."""

    _CUSTOM = '__custom__'

    def __init__(self, parent, effects, subdirs, map_path, presets_path, target_difficulty,
                 game=None, map_subdir='', mission_id=None):
        super().__init__(parent)
        import halo_patch
        self._hp = halo_patch
        self.parent_gui = parent    # gives the fallback-preset lookup access to .db
        self.game = game
        self.subdirs = subdirs
        self.map_subdir = map_subdir      # per-game maps folder, for re-finding on root change
        self.mission_id = mission_id
        self._round_keys = None     # lazily built by _this_round_keys()
        self.presets_path = presets_path
        self.presets = halo_patch.load_presets(presets_path)
        self.target_difficulty = target_difficulty
        self.effects = effects
        self.rows = []          # (effect, target, QLineEdit)
        self._srcmap = None     # cached read-source map for vanilla values
        self.setWindowTitle("Apply Effects to Map")
        self.setModal(True)
        self.setMinimumSize(940, 760)
        # Remember how the user sized this window between sessions (same as Options).
        _sz = CONFIG.get('patcher_dialog_size')
        if isinstance(_sz, (list, tuple)) and len(_sz) == 2:
            try:
                self.resize(max(940, int(_sz[0])), max(760, int(_sz[1])))
            except (TypeError, ValueError):
                pass
        # #5: allow maximizing/minimizing the dialog.
        self.setWindowFlags(self.windowFlags()
                            | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        # #4: make inputs/labels visible against the dark background.
        self.setStyleSheet("""
            QLineEdit { background-color: #1a1a1a; color: #e0e0e0;
                        border: 1px solid #3a3a3a; padding: 4px; border-radius: 3px; }
            QLabel { color: #e0e0e0; }
            QGroupBox { color: #e0e0e0; border: 1px solid #3a3a3a;
                        border-radius: 5px; margin-top: 8px; }
            /* #9: high-contrast scrollbars that stand out from the dark background */
            QScrollBar:vertical { background: #202020; width: 16px; margin: 0; }
            QScrollBar::handle:vertical { background: #6a6a6a; min-height: 40px;
                        border-radius: 5px; border: 1px solid #808080; }
            QScrollBar::handle:vertical:hover { background: #8fb8ff; border-color: #8fb8ff; }
            QScrollBar:horizontal { background: #202020; height: 16px; margin: 0; }
            QScrollBar::handle:horizontal { background: #6a6a6a; min-width: 40px;
                        border-radius: 5px; border: 1px solid #808080; }
            QScrollBar::handle:horizontal:hover { background: #8fb8ff; border-color: #8fb8ff; }
            QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
            QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
        """)
        self._build_registry()
        self._build(map_path)

    # ---- registry / vanilla source ----
    def _build_registry(self):
        self.registry = self._hp.PluginRegistry(CONFIG.get('assembly_plugins_dir'), self.subdirs)

    def _read_source(self):
        """Load (once) the map used to display vanilla values — the pristine
        .bak if it exists, else the map itself. False if it can't be read."""
        if self._srcmap is not None:
            return self._srcmap
        path = self.map_edit.text().strip()
        src = path + '.bak' if Path(path + '.bak').is_file() else path
        try:
            self._srcmap = self._hp.open_map(src, self.game)
        except Exception:
            self._srcmap = False
        return self._srcmap

    def _vanilla_str(self, tag, target):
        # Value is read from the FIRST matching tag as the representative (all
        # variants of an enemy share the same base value). Distinguish an absent
        # tag (enemy/weapon not in this map) from a bad field name.
        m = self._read_source()
        if not m:
            return "?"
        cls, path = self._hp.hm.split_tag(tag)
        plugin = self.registry.get(cls)
        if plugin is None:
            return "no plugin"
        if not m.find_tags(cls, path):
            return "— not in map"
        field = self._hp.apply_difficulty(target['field'], target, self.target_difficulty)
        v = m.read_first(cls, path, field, plugin, target.get('block'),
                         target.get('index', 0) or 0, nth=target.get('nth', 0) or 0)
        if v is None:
            return "field?"
        v = self._shown_value(target, v)        # stored -> the units shown/typed
        return f"{round(v, 4)}" if isinstance(v, float) else str(v)

    def _vanilla_num(self, tag, field, block=None, nth=0):
        """Numeric vanilla value of a field (first matching tag), or None."""
        m = self._read_source()
        if not m:
            return None
        cls, path = self._hp.hm.split_tag(tag)
        plugin = self.registry.get(cls)
        if plugin is None:
            return None
        return m.read_first(cls, path, field, plugin, block, 0, nth=nth)

    def _absent_from_game(self, eff):
        """True if this effect's weapon/equipment doesn't exist in the selected game
        at all (as opposed to merely not being placed on the current level)."""
        if not isinstance(eff, dict):
            return False
        db = getattr(self.parent_gui, 'db', None)
        if db is None or not self.game:
            return False
        w = eff.get('weapon')
        if w:
            # Equipment is Halo 3 only; otherwise ask the game's own weapon pool.
            if db.is_equipment(w):
                return self.game != 'Halo 3'
            return db.resolve_weapon(w) not in db.get_game_weapons(self.game)
        games = eff.get('games') or []
        return bool(games) and self.game not in games

    @staticmethod
    def _shown_value(target, v):
        """Map a STORED value into the units the row's magnitude works in.

        Only matters where a game stores the setting against a different zero or
        direction than the label implies — Halo 2 keeps Starting Health as a *Damage*
        (0 = normal, falling) while the row is labelled, and now operated on, as a
        *Modifier* (1 = normal, rising). Showing the raw 0 next to a field the user
        multiplies as a modifier reads as a contradiction. Identity for every other
        field, since only these targets declare negate/offset."""
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            return v
        # A placeholder 0 is shown as what it stands for (see apply_field's
        # `zero_is`), so the vanilla column agrees with what an operator will do
        # to it — showing 0 beside a field a multiply turns into 60 is the
        # contradiction this whole mechanism exists to remove.
        zi = target.get('zero_is')
        if zi is not None and not v:
            v = zi
        scale = -1.0 if target.get('negate') else 1.0
        offset = float(target.get('offset') or 0.0)
        if scale == 1.0 and offset == 0.0:
            return v
        return scale * v + offset

    def _difficulty_values_str(self, tag, target):
        """Every difficulty's value for a per-difficulty field, e.g.
        'Easy 0.4 · Normal 0.5 · ▶Heroic 0.6 · Legendary 0.7'.

        Only these fields have one value per difficulty; the row otherwise shows just
        the one being patched, which gives no sense of the scale it sits on. The
        difficulty actually being written is marked. A tier the game doesn't define
        (there is no Easy accuracy tier, for instance) shows as '—' rather than being
        hidden, so its absence is visible. Empty string when the field isn't
        per-difficulty, so callers can append it unconditionally."""
        if not any(target.get(k) for k in DIFF_FLAVOR_KEYS):
            return ''
        m = self._read_source()
        if not m:
            return ''
        cls, path = self._hp.hm.split_tag(tag)
        plugin = self.registry.get(cls)
        if plugin is None or not m.find_tags(cls, path):
            return ''
        parts, seen_any = [], False
        for pub, intern in DIFF_DISPLAY:
            field = self._hp.apply_difficulty(target['field'], target, intern)
            v = m.read_first(cls, path, field, plugin, target.get('block'),
                             target.get('index', 0) or 0, nth=target.get('nth', 0) or 0)
            if v is None:
                shown = '—'
            else:
                shown = f"{round(v, 4)}" if isinstance(v, float) else str(v)
                seen_any = True
            mark = '▶' if intern == self.target_difficulty else ''
            parts.append(f"{mark}{pub} {shown}")
        # All four unreadable means the field name is wrong for every tier; the row's
        # normal "field?" reporting covers that better than a row of dashes.
        return ('all difficulties:  ' + '  ·  '.join(parts)) if seen_any else ''

    def _variant_values_str(self, tag, target, eff=None):
        """List every matching variant's vanilla value(s) as 'values (variants)',
        collapsing variants that share the same value(s) onto one line. When a target
        spans multiple block elements (index='all'), each variant shows all its leaf
        values — this is how an effect stays a SINGLE modifiable field yet still
        exposes every per-variant/per-index vanilla value (H1 per-variant listing
        extended to H2's indexed blocks). enum fields are shown by option name. If the
        effect seeds this field on unset variants (init_defaults), the seeded default
        is appended as '→ value (seeded default)' so the new behavior is visible."""
        m = self._read_source()
        if not m:
            return "?"
        cls, path = self._hp.hm.split_tag(tag)
        if target.get('equip_drop'):
            try:
                rows = self._hp.equipment_drop_chances(m, self.game, target['equip_drop'])
                if not rows:
                    return "— no Brute on this level carries it"
                live = [f'{n}={c:g}' for n, c in rows if c > 0]
                zero = sum(1 for _, c in rows if c <= 0)
                return (('  '.join(live) if live else 'every carrier is at 0')
                        + (f'   (+{zero} at 0)' if zero else ''))
            except Exception:
                return "relative drop weight on Brutes"
        if target.get('map_equip'):
            try:
                n = self._hp.map_equipment_placement_count(m, self.game)
                return f'{n} equipment placements on this level  (enter e.g. =25 for 25%)'
            except Exception:
                return "percentage of the level's equipment placements"
        if target.get('map_swap'):
            # Not a tag field — the magnitude is a percentage of the level's weapon
            # placements. Show how many there are so the % means something.
            try:
                n = self._hp.map_weapon_placement_count(m, self.game)
                return f'{n} weapon placements on this level  (enter e.g. =25 for 25%)'
            except Exception:
                return 'percentage of the level\'s weapon placements'
        if target.get('reload_anim') or target.get('swap_anim'):
            # Reload animation: show the current reload length in seconds (frames / 30fps)
            # per graph (Master Chief / Arbiter), instead of a plugin field value.
            try:
                import halo3_reload
                rows = halo3_reload.reload_frames(m, path, self.game)
                if not rows:
                    return "— no reload animation on this map"
                labels = []
                for who, fcs in rows:
                    secs = ", ".join("%.2fs" % (f / halo3_reload.FPS) for f in fcs)
                    labels.append("%s  (%s)" % (secs, who))
                return "\n".join(labels)
            except Exception:
                return "reload animation"
        if target.get('sprint'):
            # Not a tag field — routes into the ability config. Show the Options base
            # this card nudges (and stacks onto), or that the enabler unlocks sprint.
            p = target['sprint']
            if p == 'enable':
                return 'drafting this unlocks sprint for the rest of the run'
            base = {'speed': '%s%%' % CONFIG.get('sprint_speed_pct', 150),
                    'duration': '%ss' % CONFIG.get('sprint_duration_s', 3.0),
                    'cooldown': '%ss' % CONFIG.get('sprint_cooldown_s', 2.0),
                    'os_mult': 'x%s' % CONFIG.get('overshield_mult', 3.0),
                    'regen_percent': '%s%%' % CONFIG.get('regen_percent', 100.0),
                    'regen_duration': '%ss' % CONFIG.get('regen_duration_s', 5.0),
                    'camo_duration': '%ss' % CONFIG.get('camo_duration_s', 5.0),
                    'camo_cooldown': '%ss' % CONFIG.get('camo_cooldown_s', 30.0)}.get(p, '')
            return '%s %s — Options base %s; apply an operator (+n/-n/*n or xn/=n)' % (
                ability_of_param(p) or 'ability', p, base)
        plugin = self.registry.get(cls)
        if plugin is None:
            return "no plugin"
        field = self._hp.apply_difficulty(target['field'], target, self.target_difficulty)
        nth = target.get('nth', 0) or 0
        fld = plugin.find(field, target.get('block'), nth)
        if fld is None and (target.get('difficulty') or target.get('diff_prefix')
                            or target.get('diff_prefix_nl') or target.get('diff_suffix')):
            # e.g. H2 accuracy has no 'Easy' tier — flag it rather than showing "field?"
            return f"⚠ no definition for {self.target_difficulty} difficulty"
        enum_names = {v: k.title() for k, v in fld['options'].items()} if (fld and fld.get('options')) else {}
        def fmtval(x):
            if isinstance(x, int) and x in enum_names:
                return enum_names[x]
            x = self._shown_value(target, x)    # stored -> the units shown/typed
            return round(x, 4) if isinstance(x, float) else x
        default_line = self._init_default_line(eff, target, field, m, plugin, fmtval)
        rows = m.read_all_leaves(cls, path, field, plugin, target.get('block'),
                                 target.get('index', 0) or 0, nth=nth)
        if not rows:
            if default_line:
                return default_line
            if m.find_tags(cls, path):
                return "field?"
            # Distinguish "this game doesn't have this weapon/equipment at all" from
            # "it exists in this game but isn't placed on this particular level".
            return ("— not in the selected game" if self._absent_from_game(eff)
                    else "— not in map")
        # collapse variants sharing the same value-list onto one line.
        by_vals = {}
        for p, vals in rows:
            key = tuple(fmtval(v) for v in vals)
            by_vals.setdefault(key, []).append(p.rsplit(chr(92), 1)[-1])

        def show(key):
            # An index:'all' target over a big block (e.g. ai\generic's per-weapon
            # Weapons Properties, 40+ entries) would otherwise dump a wall of numbers
            # with no way to tell what each belongs to. Summarise long numeric lists as
            # a range + count instead; short lists still show every value.
            if len(key) > 6:
                nums = [k for k in key if isinstance(k, (int, float))]
                if len(nums) == len(key):
                    lo, hi = min(nums), max(nums)
                    span = f"all {lo:g}" if lo == hi else f"{lo:g} – {hi:g}"
                    return f"{len(key)} entries: {span}"
            return ", ".join(str(k) for k in key)
        # H2/H3 resolve their singleton scnr/matg tags by returning the nominal
        # wildcard path ('levels\*') unchanged, so the per-variant label came out as a
        # bare '*' — not a real variant. Strip those meaningless labels so such a
        # target renders like a plain singleton ("0.0, 0.0") instead of "0.0, 0.0  (*)".
        by_vals = {k: [n for n in names if n != '*'] for k, names in by_vals.items()}
        # For a per-variant effect (wildcard tag) always name the variant(s), even
        # when only one variant carries the data — so the user sees WHICH variant it
        # is. A true singleton (exact tag, or a wildcard that didn't expand to real
        # names) shows a bare value.
        if len(by_vals) == 1 and not default_line and (
                '*' not in path or not next(iter(by_vals.values()))):
            return show(next(iter(by_vals)))
        out = "\n".join(
            (f"{show(key)}   ({', '.join(names)})" if names else show(key))
            for key, names in by_vals.items())
        return out + ("\n" + default_line if default_line else "")

    def _init_default_line(self, eff, target, field, m, plugin, fmtval):
        """'→ value (seeded default)' for a field that this effect's init_defaults
        will seed onto unset variants, or None if it doesn't seed this field."""
        init = eff.get('init_defaults') if isinstance(eff, dict) else None
        if not isinstance(init, dict):
            return None
        base_field = target['field']
        setmap = {k.lower(): v for k, v in (init.get('set') or {}).items()}
        if base_field.lower() in setmap:
            return "→ %s (seeded default)" % setmap[base_field.lower()]
        covers = base_field in (init.get('copy') or [])
        if init.get('grow') and init.get('block') and target.get('block') \
                and str(target.get('block')).lower() == str(init.get('block')).lower():
            covers = True
        if not covers:
            return None
        src_base = None
        if init.get('source'):
            scls, spath = self._hp.hm.split_tag(init['source'])
            s = m.find_tags(scls, spath)
            if not s:
                return None
            src_base = s[0][1]
        else:
            # A source-less grow seeds each variant from its own nearest populated
            # ANCESTOR, so that is the value to show: an inheriting hero reads back
            # nothing of its own, and a card with no vanilla value looks broken even
            # though the number it will start from is perfectly well defined.
            src_base = self._inherited_base(init, eff, m, plugin)
        if src_base is None:
            return None
        v = m.read_tag_field(src_base, field, plugin, block=init.get('block'), index=0)
        return None if v is None else "→ %s (inherited)" % fmtval(v)

    def _inherited_base(self, init, eff, m, plugin):
        """Tag base of the nearest ancestor that populates the block this effect
        seeds -- the same one halo_patch.seed_ancestor picks when it does the seeding,
        so the value shown is the value that will be written."""
        block = init.get('block')
        bf = next((f for f in plugin.fields
                   if f['block_chain']
                   and f['block_chain'][-1].lower() == str(block).lower()), None)
        if not bf:
            return None
        boff = bf['block_offsets'][-1]
        cls, path = self._hp.hm.split_tag(init.get('tag') or eff.get('tag'))
        for _tpath, base in m.find_tags(cls, path):
            if m.i32(base + boff) > 0:          # this variant has its own; not seeded
                continue
            anc = self._hp.seed_ancestor(m, base, boff)
            if anc is not None:
                return anc['base']
        return None

    # ---- targets (halo.json + preset fallbacks, #7) ----
    def _effect_targets(self, eff):
        base = list(eff.get('targets') or [])
        custom = list(self.presets.get(self._hp.preset_key(eff['tag'], eff['name'], self._CUSTOM, self.game)) or [])
        for c in custom:
            c['custom'] = True
        return base + custom, (not base and bool(custom))

    # A field lives here that took over for a field from an earlier game (so
    # far only Halo 2's 'Shots Per Fire' family replacing 'Rounds Per Second'
    # on capped-burst weapons). No saved preset yet for the new field? Fall
    # back to whatever the user last typed for the field it replaced, on the
    # SAME weapon+effect, so the magnitude doesn't reset to blank just because
    # the underlying field changed between games.
    _FIELD_CARRYOVER = {
        'Shots Per Fire': 'Rounds Per Second',
        'Shots Per Fire Max': 'Rounds Per Second Max',
    }

    def _source_mod(self, eff):
        """The halo.json definition this effect was drafted from, or None.

        Matched on name AND on the tag resolving to the same string for the current
        game, so two enemies that share a card name (every one of them has a `Body
        Vitality`) cannot be confused for each other."""
        db = getattr(self.parent_gui, 'db', None)
        if db is None:
            return None
        cached = getattr(self, '_srcmod_cache', None)
        if cached is None:
            cached = self._srcmod_cache = {}
        key = (eff.get('name'), eff.get('tag'))
        if key in cached:
            return cached[key]
        games = db.get_games()
        pools = [db.weapon_mods, db.enemy_mods, db.boss_mods,
                 getattr(db, 'equipment_mods', {}) or {}]
        seqs = [list((p or {}).values()) for p in pools]
        seqs.append([[m] for m in (db.positive_pool + db.negative_pool
                                   + db.wildcard_pool + list(db.skull_pool or []))])
        found = None
        for seq in seqs:
            for mods in seq:
                for m in mods or []:
                    if m.get('name') != eff.get('name'):
                        continue
                    if resolve_gamed(m.get('tag'), self.game, games) == eff.get('tag'):
                        found = m
                        break
                if found:
                    break
            if found:
                break
        cached[key] = found
        return found

    def _carry_from_earlier_game(self, eff, target):
        """This card+field's magnitude from the NEAREST earlier game, or None.

        Moving a run up a game rebuilt every operator box empty, because the preset key
        is `tag||name||field||game` and BOTH the tag and the game change between engines
        — so nothing a Halo 2 leg had typed could ever be found again in Halo 3, even
        though most cards edit the same field for the same reason.

        Operators carry cleanly: `*1.5` means the same thing whatever the vanilla value
        underneath it is, which is the whole point of storing an operator rather than a
        number. The earlier game's TAG is read from the card's own definition rather
        than guessed, so this can only ever find the same card's own history."""
        field = target.get('field')
        if not isinstance(field, str):
            return None
        db = getattr(self.parent_gui, 'db', None)
        src = self._source_mod(eff)
        if db is None or not src or not isinstance(src.get('tag'), dict):
            return None
        games = db.get_games()
        if self.game not in games:
            return None
        for g in reversed(games[:games.index(self.game)]):     # nearest earlier first
            tag = resolve_gamed(src['tag'], g, games)
            if not isinstance(tag, str) or not tag:
                continue
            val = self.presets.get(self._hp.preset_key(tag, eff['name'], field, g))
            if val not in (None, '') and not isinstance(val, list):
                return val, g
        return None

    def _fallback_preset_value(self, eff, target):
        src_field = self._FIELD_CARRYOVER.get(target.get('field'))
        db = getattr(self.parent_gui, 'db', None)
        weapon = eff.get('group')
        if not (src_field and db and weapon):
            return None
        orig = next((m for m in db.weapon_mods.get(weapon, []) if m['name'] == eff['name']), None)
        if not orig or not isinstance(orig.get('tag'), dict):
            return None
        games = db.get_games()
        for g in games:
            if g == self.game:
                continue
            src_tag = resolve_gamed(orig['tag'], g, games)
            if not src_tag:
                continue
            key = self._hp.preset_key(src_tag, eff['name'], src_field, g)
            val = self.presets.get(key)
            if val is not None and not isinstance(val, list):
                return val
        return None

    # ---- build ----
    @staticmethod
    def _wrap(layout):
        w = QWidget()
        w.setLayout(layout)
        return w

    def _build(self, map_path):
        layout = QVBoxLayout(self)

        # The setup rows (folders, map, difficulty, legend) SCROLL WITH the effect
        # list rather than being pinned above it — pinned, they permanently ate the
        # vertical space the effect list needs. The Find row is the exception and IS
        # pinned, below. They go in their own widget inside
        # the scroll area, kept separate from `self.form` because _populate() clears
        # that layout on every repopulate (difficulty change, reload, reorder).
        head_w = QWidget()
        head = QVBoxLayout(head_w)
        head.setContentsMargins(0, 0, 0, 0)

        mrow = QHBoxLayout()
        mrow.addWidget(QLabel("MCC folder:"))
        self.mcc_edit = QLineEdit(mcc_root())
        self.mcc_edit.setToolTip("Your 'Halo The Master Chief Collection' folder — maps are "
                                 "auto-found here. Remembered across sessions.")
        mrow.addWidget(self.mcc_edit, 1)
        mbrowse = QPushButton("Browse…")
        mbrowse.clicked.connect(self._browse_mcc_root)
        mrow.addWidget(mbrowse)
        head.addLayout(mrow)

        prow = QHBoxLayout()
        prow.addWidget(QLabel("Assembly plugins folder:"))
        self.plugins_edit = QLineEdit(CONFIG.get('assembly_plugins_dir', ''))
        prow.addWidget(self.plugins_edit, 1)
        pbrowse = QPushButton("Browse…")
        pbrowse.clicked.connect(self._browse_plugins)
        prow.addWidget(pbrowse)
        head.addLayout(prow)

        maprow = QHBoxLayout()
        maprow.addWidget(QLabel("Map file:"))
        self.map_edit = QLineEdit(map_path)
        maprow.addWidget(self.map_edit, 1)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse_map)
        maprow.addWidget(browse)
        reload_btn = QPushButton("Reload")
        reload_btn.setToolTip("Re-read vanilla values with the current paths")
        reload_btn.clicked.connect(self._reload)
        maprow.addWidget(reload_btn)
        head.addLayout(maprow)

        drow = QHBoxLayout()
        drow.addWidget(QLabel("Difficulty:"))
        self.diff_combo = QComboBox()
        _fill_difficulty_combo(self.diff_combo, self.target_difficulty)
        self.diff_combo.currentIndexChanged.connect(
            lambda _=0: self._on_difficulty_changed(self.diff_combo.currentData()))
        drow.addWidget(self.diff_combo)
        # "n" stands for the number, so the multiply alias reads as an alias rather
        # than as literal text to type (the old "*x multiply" invited typing "*x").
        help_lbl = QLabel("operators:  =n set   +n add   -n subtract   *n or xn multiply"
                          "   (blank = skip)")
        help_lbl.setStyleSheet("color: #aaa; font-size: 12px;")
        drow.addSpacing(16)
        drow.addWidget(help_lbl)
        drow.addStretch()
        head.addLayout(drow)

        _r = f'<span style="color: {HARDER_RED};">'
        _g = f'<span style="color: {EASIER_GREEN};">'
        legend = QLabel("Direction indicator: &nbsp;"
                        f"{_r}▲</span> raising makes it harder &nbsp; &nbsp;"
                        f"{_r}▼</span> lowering makes it harder &nbsp; &nbsp;"
                        f"{_g}▲</span> raising makes it easier &nbsp; &nbsp;"
                        f"{_g}▼</span> lowering makes it easier &nbsp; "
                        "(shown per field where the direction isn't obvious)"
                        "<br>Effects: &nbsp;🔆 picked this round &nbsp; &nbsp;"
                        "🆕 not patched to a map yet")
        legend.setStyleSheet("color: #c8c8c8; font-size: 12px; padding: 2px;")
        legend.setWordWrap(True)
        head.addWidget(legend)

        _note = None
        if self.parent_gui is not None and getattr(self.parent_gui, 'db', None) is not None:
            _note = self.parent_gui.db.mission_note(self.mission_id)
        if _note:
            note = QLabel("\u26a0 " + _note)
            note.setWordWrap(True)
            note.setStyleSheet("color: #e0c060; font-size: 12px; background-color: #2a2410; "
                               "border: 1px solid #5a4a20; border-radius: 4px; padding: 6px;")
            head.addWidget(note)

        swap_group = self._build_weapon_swap_group()
        if swap_group:
            head.addWidget(swap_group)

        zoom_row = self._build_zoom_source_row()
        if zoom_row:
            head.addWidget(zoom_row)

        # #5/#7: search-to-effect + "show new effects first" toggle.
        #
        # PINNED, unlike the setup rows above: the whole point of Find is to jump around
        # a list too long to see at once, and a search box that scrolls off the top with
        # the rest of the header is unreachable exactly when it is wanted. It is one
        # row, so it costs the effect list almost nothing.
        srow = QHBoxLayout()
        srow.setContentsMargins(0, 0, 0, 0)
        srow.addWidget(QLabel("🔍 Find:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("effect name… (Enter / F3 cycles matches, Shift+Enter goes back)")
        self.search_edit.textChanged.connect(lambda s: self._search_effect(s, advance=False))
        self.search_edit.returnPressed.connect(
            lambda: self._search_effect(self.search_edit.text(), advance=True))
        srow.addWidget(self.search_edit, 1)
        self.search_count = QLabel("")
        self.search_count.setStyleSheet("color: #7aa0c0; font-size: 12px; min-width: 70px;")
        srow.addWidget(self.search_count)
        self.new_top_cb = QCheckBox("Show new effects at the top")
        self.new_top_cb.setToolTip("List effects not yet applied to a map first, until you patch")
        self.new_top_cb.setChecked(bool(CONFIG.get('show_new_at_top')))
        self.new_top_cb.toggled.connect(self._toggle_new_top)
        srow.addWidget(self.new_top_cb)
        srow_w = QWidget()
        srow_w.setLayout(srow)
        layout.addWidget(srow_w)
        # F3 / Shift+F3 cycle without needing focus in the box.
        QShortcut(QKeySequence(Qt.Key_F3), self,
                  lambda: self._search_effect(self.search_edit.text(), advance=True))
        QShortcut(QKeySequence("Shift+F3"), self,
                  lambda: self._search_effect(self.search_edit.text(), advance=True, back=True))
        QShortcut(QKeySequence("Shift+Return"), self.search_edit,
                  lambda: self._search_effect(self.search_edit.text(), advance=True, back=True))

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._cont = QWidget()
        cont_v = QVBoxLayout(self._cont)
        cont_v.setContentsMargins(0, 0, 0, 0)
        cont_v.addWidget(head_w)
        # self.form holds ONLY the effect rows: _populate() clears it wholesale, so
        # the header above must not live in it.
        self.form = QVBoxLayout()
        cont_v.addLayout(self.form)
        cont_v.addStretch(1)
        self._scroll.setWidget(self._cont)
        layout.addWidget(self._scroll, 1)
        self._populate()

        self.results = QTextEdit()
        self.results.setReadOnly(True)
        self.results.setMaximumHeight(170)
        self.results.setStyleSheet("background-color: #1a1a1a; color: #e0e0e0; font-family: monospace; font-size: 12px;")
        layout.addWidget(self.results)

        btns = QHBoxLayout()
        apply_btn = QPushButton("💾 Patch Map")
        apply_btn.setToolTip("Back up and apply to the map \u2014 writes every magnitude typed here "
                             "into the level's .map. The level's pristine .bak is made on the "
                             "first patch and every later patch rebuilds FROM it, so patching "
                             "is repeatable and never compounds.")
        apply_btn.setStyleSheet("background-color: #5a3a2a; color: white; font-weight: bold; padding: 8px 16px; border-radius: 5px;")
        apply_btn.clicked.connect(self._apply)
        next_empty_btn = QPushButton("⤓ Next empty entry")
        next_empty_btn.setToolTip("Jump to the next blank operator field")
        next_empty_btn.setStyleSheet("background-color: #2a3a5a; color: white; padding: 8px 14px; border-radius: 5px;")
        next_empty_btn.clicked.connect(self._jump_to_next_empty)
        top_btn = QPushButton("↑ Top")
        top_btn.setToolTip("Back to the top of the list — the map and difficulty rows "
                           "live up there and scroll with it (Find stays pinned)")
        top_btn.setMaximumWidth(70)
        top_btn.setStyleSheet("background-color: #2a3a5a; color: white; padding: 8px 10px; border-radius: 5px;")
        top_btn.clicked.connect(self._scroll_to_top)
        next_round_btn = QPushButton("🔆 Next effect this round")
        next_round_btn.setToolTip("Jump to the next effect drafted in the latest round. An effect "
                                  "picked again this round already has a magnitude, so 'next empty "
                                  "entry' walks straight past it. Falls back to the effects not "
                                  "patched to a map yet (🆕) when this round drafted nothing.")
        next_round_btn.setStyleSheet("background-color: #4a3a1a; color: white; padding: 8px 14px; border-radius: 5px;")
        next_round_btn.clicked.connect(self._jump_to_next_marked)
        log_btn = QPushButton("📂 Patch log")
        log_btn.setToolTip("Open the patch log written for this map — the effects, fields "
                           "and old → new values of the last patch — to check them by "
                           "hand. Opens the patches folder if nothing is logged yet.")
        log_btn.setStyleSheet("background-color: #3a3a2a; color: white; padding: 8px 14px; border-radius: 5px;")
        log_btn.clicked.connect(self._open_patch_file)
        keep_btn = QPushButton("⭳ Save magnitudes to presets")
        keep_btn.setToolTip("Write the magnitudes typed here into the global preset file "
                            "now, without patching. Handy after loading a shared run, or "
                            "to keep values you've tuned but aren't ready to apply — "
                            "otherwise they're only remembered when you patch.")
        keep_btn.setStyleSheet("background-color: #2a4a3a; color: white; padding: 8px 14px; border-radius: 5px;")
        keep_btn.clicked.connect(lambda _=False: self._save_magnitudes_now())
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        btns.addWidget(apply_btn)
        btns.addWidget(top_btn)
        btns.addWidget(next_round_btn)
        btns.addWidget(next_empty_btn)
        btns.addWidget(keep_btn)
        btns.addWidget(log_btn)
        btns.addStretch()
        btns.addWidget(close_btn)
        layout.addLayout(btns)

        # Nothing in this dialog may be the DEFAULT button. Qt hands Return to the
        # default button as well as to the focused QLineEdit, so pressing Enter in the
        # Find box also fired the first Browse… in the dialog and threw up a folder
        # picker — which is what made cycling through matches look impossible. There is
        # no Enter action worth having here (Patch Map should never be one keystroke
        # away), so every button opts out and Return belongs to whatever has focus.
        for b in self.findChildren(QPushButton):
            b.setAutoDefault(False)
            b.setDefault(False)

    def _normalize_entries(self):
        """Rewrite every editable operator box into its canonical form (see
        halo_map.normalize_op_text). Read-only rows carry derived/fixed text that is
        not an operator, so they are left alone."""
        seen = set()
        for _eff, _t, le in self.rows:
            if not is_operator_box(le) or id(le) in seen:
                continue
            seen.add(id(le))            # grouped rows share one box; touch it once
            le.setText(self._hp.hm.normalize_op_text(le.text()))

    def _save_magnitudes_now(self, report=True):
        """Write the magnitudes typed in this dialog into the global preset file, without
        patching. Magnitudes are otherwise only remembered as a side effect of applying,
        so a run loaded from a co-op partner (or values tuned but not yet applied) would
        be lost by closing the dialog."""
        self._normalize_entries()
        written, cleared = 0, 0
        for eff, t, le in self.rows:
            if t.get('choice'):
                # A choice row has a real user value even though it is not an operator
                # box, so saving magnitudes has to keep it or the pick is lost on close.
                key = choice_preset_key(eff, t['field'])
                chosen = row_value(le).strip()
                if chosen and self.presets.get(key) != chosen:
                    self.presets[key] = chosen
                    written += 1
                continue
            if not is_operator_box(le) or t.get('set') is not None:
                continue                      # derived/fixed rows carry no user value
            key = self._hp.preset_key(eff['tag'], eff['name'], t['field'], self.game)
            txt = row_value(le).strip()
            if txt:
                if self.presets.get(key) != txt:
                    written += 1
                self.presets[key] = txt
            elif isinstance(self.presets.get(key), str) and self.presets[key]:
                # An emptied field is a deliberate "leave this alone" — mirror it, so
                # reopening (or a partner loading the run) doesn't resurrect the number.
                self.presets[key] = ''
                cleared += 1
        self._hp.save_presets(self.presets_path, self.presets)
        bits = []
        if written:
            bits.append(f"{written} value(s) saved")
        if cleared:
            bits.append(f"{cleared} cleared")
        if not report:
            return
        msg = ", ".join(bits) if bits else "nothing changed — presets already match"
        self.results.setPlainText(
            f"Magnitudes → {Path(self.presets_path).name}: {msg}.\n"
            "These are now the remembered defaults for these effects, and travel with "
            "the run when you save or share it.")

    def _scroll_to_top(self):
        """Back to the top of the effect list — the setup rows (folders, map,
        difficulty, search) scroll WITH the list, so reaching them from the bottom
        of a long run meant dragging the whole way."""
        self._scroll.verticalScrollBar().setValue(0)
        # Restart both jump cursors, so the next press of either walks the list
        # from the top rather than from wherever it had got to.
        self._marked_idx = -1
        self._jump_order_idx = -1

    def _jump_to_next_marked(self):
        """Scroll to and focus the next effect drafted in the latest round (🔆),
        cycling through them.

        Distinct from "next empty entry", which walks blank INPUTS wherever they are:
        an effect picked again this round usually already has a magnitude, so it has no
        blank field to stop at, and in a long list it is exactly the one that is hard
        to find. Falls back to the not-yet-patched (🆕) effects when this round drafted
        nothing new to look at -- a run loaded from a partner has no "latest round" of
        its own to jump to, but does have unpatched effects worth reviewing."""
        boxes = getattr(self, '_marked_boxes', None) or []
        if not boxes:
            boxes = getattr(self, '_new_boxes', None) or []
        if not boxes:
            self.results.setPlainText(
                "Nothing to jump to — no effect in this list was drafted this round, "
                "and none is still waiting for its first patch.")
            return
        idx = (getattr(self, '_marked_idx', -1) + 1) % len(boxes)
        self._marked_idx = idx
        self._scroll.ensureWidgetVisible(boxes[idx], 50, 60)
        # Focus the box's first editable operator so the value can be typed straight
        # away, the way the empty-entry jump leaves the caret ready.
        for eff, t, le in self.rows:
            if is_operator_box(le) and le.window() is self                     and self._box_of(le) is boxes[idx]:
                le.setFocus()
                le.selectAll()
                break

    @staticmethod
    def _box_of(widget):
        """The QGroupBox an input lives in, walking up the parent chain."""
        w = widget
        while w is not None:
            if isinstance(w, QGroupBox):
                return w
            w = w.parentWidget()
        return None

    def _jump_to_next_empty(self):
        """Scroll to and focus the next blank operator field (wrapping around). Uses a
        persistent pointer rather than focusWidget() — clicking the button itself
        steals focus, so focusWidget() would otherwise always report the button and
        never advance past the current entry."""
        order = [le for _, t, le in self.rows if is_operator_box(le)]
        empties = [(i, le) for i, le in enumerate(order) if not le.text().strip()]
        if not empties:
            return
        start = getattr(self, '_jump_order_idx', -1)
        after = [(i, le) for i, le in empties if i > start]
        i, le = after[0] if after else empties[0]     # wrap to the first empty
        self._jump_order_idx = i
        self._scroll.ensureWidgetVisible(le, 50, 60)
        le.setFocus()
        le.selectAll()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                # Unparent before deleteLater: takeAt only drops it from the layout,
                # so an un-managed child stays visible until the event loop runs the
                # deferred delete — which repopulating mid-signal doesn't wait for.
                w.setParent(None)
                w.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _odst_hub_path(self, map_path):
        """Path to Mombasa Streets, or None when the hub patch does not apply.

        None when: not ODST, the option is off, the mission BEING patched already IS
        the hub (patching it twice would be pointless and would double-report), or
        the hub map is not on disk.
        """
        if self.game != 'Halo 3: ODST' or not CONFIG.get('odst_patch_hub', True):
            return None
        hub_id = CONFIG.get('odst_hub_mission') or 'h100'
        if self.mission_id == hub_id:
            return None
        p = self._hp.default_map_path(mcc_root(),
                                      CONFIG.get('map_game_folder', {}).get(self.game, ''),
                                      hub_id)
        return p if p and os.path.exists(p) else None

    def _odst_shield_into_health(self, plan):
        """In ODST, spend a Starting Shield card on Starting Health instead.

        ODST's player has stamina, not a shield. The shield field is still there and
        still accepts a write; it just does nothing useful — a 10x starting shield
        was confirmed in game to drain immediately. Redirecting means drafting the
        card is not a wasted pick.

        Done on the finished plan, where the effect is still identifiable by name and
        the health field can be taken from the health effect's OWN target rather than
        hardcoded — the two fields differ per game and are both remapped values
        (negate/offset), so copying the real target keeps that mapping intact.
        """
        if self.game != 'Halo 3: ODST' or not CONFIG.get('odst_shield_into_health'):
            return plan
        pair = CONFIG.get('odst_shield_into_health_pair') or {}
        src, dst = pair.get('from'), pair.get('to')
        if not src or not dst:
            return plan
        # The health effect's own target, taken from the DATABASE rather than from
        # this run's rows: the redirect has to work whether or not the player also
        # drafted the health card, and usually they have not.
        db = getattr(self.parent_gui, 'db', None)
        games = db.get_games() if db else None
        donor = None
        for mod in (getattr(db, 'positive_pool', None) or []):
            if mod.get('name') != dst:
                continue
            tl = mod.get('targets')
            tl = resolve_gamed(tl, self.game, games) if isinstance(tl, dict) else tl
            if tl:
                donor = tl[0]
            break
        if donor is None:
            return plan
        fld = resolve_gamed(donor.get('field'), self.game, games)
        if not fld:
            return plan
        for item in plan:
            if item.get('name') != src:
                continue
            for op in item['ops']:
                op['field'] = fld
                op['block'] = resolve_gamed(donor.get('block'), self.game, games)
                # negate/offset belong to the DESTINATION field's mapping, not the
                # source's — both are stored as "damage" (0 = normal, falling) and
                # presented as a rising modifier, and using the shield's mapping on
                # the health field would write the value backwards.
                op['negate'] = resolve_gamed(donor.get('negate'), self.game, games)
                op['offset'] = resolve_gamed(donor.get('offset'), self.game, games)
                op['redirected_from'] = src
        return plan

    def _odst_downgrade_keep(self):
        """Variants to LEAVE placed, or None when the downgrade is not in play.

        None rather than an empty set is the "do nothing" signal: an empty set means
        downgrade everything, which is exactly what a fresh run wants, so the two
        cannot be conflated.
        """
        if self.game != 'Halo 3: ODST':
            return None
        if CONFIG.get('odst_variants_as_base', True):
            return None          # they ARE the base weapons; nothing to downgrade
        if not CONFIG.get('odst_downgrade_unupgraded'):
            return None
        rs = getattr(self.parent_gui, 'run_state', None)
        held = set()
        if rs is not None:
            for p in ('player1', 'player2'):
                held |= {w for w in rs.weapons_for(p)}
        keep = {v for v in CONFIG.get('odst_variant_bases', {}) if v in held}
        # The red plasma rifle is only an upgrade when the run models it as Halo 2's
        # Brute Plasma Rifle. Without that option there is no card to earn it back
        # with -- it simply IS this game's Plasma Rifle -- so it must never be
        # downgraded, drafted or not.
        if not CONFIG.get('odst_red_plasma_as_brute') or 'Brute Plasma Rifle' in held:
            keep.add('Brute Plasma Rifle')
        return keep

    def _baseline_spec(self):
        """The whole-game enemy dials for THIS game, or None.

        A 0 means "leave the shipped value alone" and is dropped rather than written --
        the spin boxes display 0 as "vanilla" for exactly that reason, so the option can
        be set for one dial without disturbing the other three.
        """
        cfg = (CONFIG.get('difficulty_baseline') or {}).get(self.game) or {}
        spec = {k: float(v) for k, v in cfg.items() if v}
        return spec or None

    def _apply_score_scaling(self):
        """Rescale <mcc_root>\\Data\\UI\\scoredb.xml from this run's enemy effects.

        Returns result rows rather than raising: this writes a different file than the
        map patch, and a map patch that actually succeeded must not be reported as
        failed because a side file could not be written (missing MCC root, the file
        read-only after a Steam verify, and so on)."""
        import scoredb_patch
        rows = []
        path = os.path.join(mcc_root(), scoredb_patch.SCOREDB_REL)
        if not os.path.exists(path):
            return [{'tag': scoredb_patch.SCOREDB_REL, 'effect': 'Metagame scores',
                     'ok': False, 'field': 'scores', 'reason':'not found under the MCC folder — set '
                                            'the MCC root in Options'}]
        db = getattr(self.parent_gui, 'db', None)
        data = getattr(db, 'data', None) or {}
        spec = (data.get('Enemy modifiers') or {}).get('Specific Enemy modifier') or {}
        if not spec:
            return [{'tag': scoredb_patch.SCOREDB_REL, 'effect': 'Metagame scores',
                     'ok': False, 'field': 'scores', 'reason':'halo.json enemy data unavailable'}]
        try:
            cap = float(CONFIG.get('score_cap_mult') or 0) or None
            mults = scoredb_patch.multipliers_for(
                self.effects, spec,
                step=float(CONFIG.get('score_step', 0.05)), cap_mult=cap)
            if not mults:
                return [{'tag': scoredb_patch.SCOREDB_REL, 'effect': 'Metagame scores',
                         'ok': True, 'skip': True,
                         'reason': 'no enemy effects in this run to score'}]
            changed, _ = scoredb_patch.apply(path, mults, cap=None)
        except Exception as e:
            return [{'tag': scoredb_patch.SCOREDB_REL, 'effect': 'Metagame scores',
                     'ok': False, 'field': 'scores', 'reason':str(e)}]
        # The summary renders applied rows as "<effect>: <field>  <old> -> <new>", so
        # this has to speak that shape or it prints "None -> None". Old/new carry the
        # actual story: which enemies went up and by how much.
        top = sorted(mults.items(), key=lambda kv: -kv[1])[:4]
        detail = ', '.join('%s x%.2f' % (b[1], m) for b, m in top)
        more = '' if len(mults) <= len(top) else ', +%d more' % (len(mults) - len(top))
        pushed = self._push_scores_live(path) if CONFIG.get('score_live_push') else None
        # Only claim the restart is needed when it actually is. Saying "RESTART MCC"
        # after a successful live push would send the user off to do the one thing this
        # feature exists to avoid.
        tail = ' — RESTART MCC to apply'
        if pushed and pushed.get('ok'):
            tail = ' — pushed live to MCC (%d records, no restart)' % pushed['written']
        rows.append({'tag': scoredb_patch.SCOREDB_REL, 'effect': 'Metagame scores',
                     'ok': True,
                     'field': '%d entries' % changed,
                     'old': 'base scores',
                     'new': 'raised %s%s%s' % (detail, more, tail)})
        if pushed and not pushed.get('ok'):
            # A failed push is NOT a failed patch: the file is written either way and
            # a restart still applies it. Reported as its own row, skipped rather than
            # failed when the reason is simply that MCC is closed.
            closed = pushed.get('reason') == 'MCC is not running'
            rows.append({'tag': 'MCC process', 'effect': 'Metagame scores',
                         'field': 'live push', 'ok': closed, 'skip': closed,
                         'reason': pushed.get('reason')})
        return rows

    def _apply_betrayal_scoring(self, skulls):
        r"""Make Marines score like enemies while the Betrayal skull is active.

        Betrayal turns every human squad on the player, at which point charging you for
        killing one is backwards. Two independent things stand in the way and BOTH have
        to be handled, which is why this is one step rather than a scoredb edit:

          * the ScoreDB Marine rows are negative, and
          * the wrapper only honours a row when it IS negative -- `jbe` at
            +0x00437F6E -- discarding anything else in favour of a flat -50.

        So the rows are flipped positive and the guard is opened. Measured in game in
        Halo 2 and Halo 3: Marines then award their row value, scaled by the difficulty
        multiplier like any other kill.

        Runs AFTER the score rescale, which regenerates the whole file from the pristine
        baseline; the flip is sign-only and idempotent so the two compose in that order.
        Both halves are undone when the run has no Betrayal, so turning the skull off --
        or patching a different map -- puts vanilla scoring back.
        """
        import scoredb_patch
        sys.path.insert(0, str(Path(__file__).resolve().parent / 'sprint_toolkit'))
        on = any(str(s).strip().lower() == 'betrayal' for s in (skulls or ()))
        path = os.path.join(mcc_root(), scoredb_patch.SCOREDB_REL)
        if not os.path.exists(path):
            return []
        rows = []
        try:
            changed = scoredb_patch.set_marine_sign(path, positive=on)
        except Exception as e:
            return [{'tag': scoredb_patch.SCOREDB_REL, 'effect': 'Betrayal scoring',
                     'field': 'Marine rows', 'ok': False, 'reason': str(e)}]
        try:
            import death_penalty, score_live
        except Exception as e:
            return [{'tag': 'MCC process', 'effect': 'Betrayal scoring',
                     'field': 'sign guard', 'ok': False, 'reason': str(e)}]
        pushed = score_live.push_from_xml(path) if changed else None
        h, base, pid, err = death_penalty.attach()
        if err:
            closed = 'not running' in str(err)
            return [{'tag': 'MCC process', 'effect': 'Betrayal scoring',
                     'field': 'sign guard', 'ok': closed, 'skip': closed,
                     'reason': err}]
        try:
            if on:
                ok, e = death_penalty.betrayal_open(h, base)
            else:
                ok, e = death_penalty.betrayal_restore(h, base)
        finally:
            death_penalty.k32.CloseHandle(h)
        tail = ''
        if pushed is not None:
            tail = (' — pushed live (%d records)' % pushed['written']
                    if pushed.get('ok') else ' — live push failed: %s'
                    % pushed.get('reason'))
        rows.append({'tag': scoredb_patch.SCOREDB_REL, 'effect': 'Betrayal scoring',
                     'field': 'Marine rows', 'ok': bool(ok),
                     'old': 'cost points' if on else 'award points',
                     'new': ('award points%s' % tail) if on
                            else ('cost points%s' % tail),
                     'reason': None if ok else e})
        return rows

    def _apply_death_penalty(self):
        r"""Scale the metagame's player-death penalty with the run's round count.

        This is the one patch in the tool that is NOT a map edit, and it has to be:
        Halo 1 and Halo 2 carry no campaign metagame in their own dlls, so no .map
        could ever hold this for them. The MCC wrapper is the single scoring engine
        all five games share, so one live write covers every game -- and being live,
        it also tracks the round count as the run grows instead of freezing whatever
        it was when the map was last patched.

        Returns result rows rather than raising, for the same reason the score
        rescaling does: a map patch that succeeded must not read as failed because a
        side effect on another process could not be applied.
        """
        sys.path.insert(0, str(Path(__file__).resolve().parent / 'sprint_toolkit'))
        try:
            import death_penalty
        except Exception as e:
            return [{'tag': 'MCC process', 'effect': 'Death penalty', 'field': 'penalty',
                     'ok': False, 'reason': 'death_penalty.py unavailable: %s' % e}]
        rs = getattr(self.parent_gui, 'run_state', None)
        rounds = len(getattr(rs, 'rounds', None) or [])
        per = float(CONFIG.get('death_penalty_per_round', 0.10) or 0)
        base = float(CONFIG.get('death_penalty_base', 25.0) or 25.0)
        try:
            res = death_penalty.push(rounds=rounds, per_round=per,
                                     value=death_penalty.penalty_for(rounds, per, base))
        except Exception as e:
            return [{'tag': 'MCC process', 'effect': 'Death penalty', 'field': 'penalty',
                     'ok': False, 'reason': str(e)}]
        if not res.get('ok'):
            # MCC being closed is not a failure -- there is simply nothing to write
            # into yet, and the next patch with it open will do it.
            closed = 'not running' in str(res.get('reason', ''))
            return [{'tag': 'MCC process', 'effect': 'Death penalty', 'field': 'penalty',
                     'ok': closed, 'skip': closed, 'reason': res.get('reason')}]
        return [{'tag': 'MCC process', 'effect': 'Death penalty',
                 'field': '%d round(s) x %+.0f%%' % (rounds, per * 100),
                 'ok': True, 'old': res.get('old'), 'new': res.get('new')}]

    def _push_scores_live(self, path):
        """Mirror the freshly written scoredb.xml into the running MCC.

        MCC parses that file once at startup, so without this every score change costs a
        full restart — and on this install a Microsoft account login with it. The push
        writes the same numbers into the parsed records in memory, keyed by the bucket
        (class, type) pair, so afterwards memory says exactly what the file says however
        far the file had drifted since MCC loaded it.

        Never raises: this is a convenience on top of a file edit that already succeeded.
        """
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent / 'sprint_toolkit'))
            import score_live
            return score_live.push_from_xml(path)
        except Exception as e:
            return {'ok': False, 'reason': str(e)}

    def _remove_effect(self, eff):
        """Delete an effect from the run itself, not just from this patch session.

        `collect_effects` folds every pick of the same effect into one entry, so
        one removal has to clear every slot in every round that produced it. The
        run's own copies may still carry a pre-rename name (they were frozen when
        the card was drawn), hence the EFFECT_RENAMES fallback when matching."""
        name, weapon, enemy = eff['name'], eff.get('weapon'), eff.get('enemy')

        def matches(mod):
            if not isinstance(mod, dict):
                return False
            if mod.get('weapon') != weapon or mod.get('enemy') != enemy:
                return False
            n = mod.get('name')
            return n == name or EFFECT_RENAMES.get(n) == name

        if QMessageBox.question(
                self, "Remove effect",
                f"Remove '{name}' from the run entirely?\n\n"
                f"It was picked {eff['count']}× and will be cleared from every round.\n"
                f"The change only becomes permanent when you save the run.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return

        removed = 0
        for rd in self.parent_gui.run_state.rounds or []:
            for pk in ('player1', 'player2'):
                slot = rd.get(pk)
                if isinstance(slot, dict) and matches(slot.get('mod')):
                    slot['mod'] = None
                    removed += 1
            for k in ('enemy1', 'enemy2', 'wildcard', 'wildcard2', 'boss1', 'boss2'):
                if matches(rd.get(k)):
                    rd[k] = None
                    removed += 1

        self.effects = [e for e in self.effects if e is not eff]
        self._populate()
        self.parent_gui.update_history()
        self.parent_gui._sync_save_button()
        self.parent_gui.update_status(f"Removed '{name}' from the run ({removed} pick(s)).")

    def _patched_keys(self):
        rs = getattr(self.parent_gui, 'run_state', None)
        return getattr(rs, 'patched_effect_keys', set()) if rs else set()

    def _is_new(self, eff):
        return (eff.get('tag'), eff.get('name')) not in self._patched_keys()

    def _this_round_keys(self):
        """(tag, name) of everything picked in the latest round, cached per dialog."""
        if getattr(self, '_round_keys', None) is None:
            rs = getattr(self.parent_gui, 'run_state', None)
            rounds = getattr(rs, 'rounds', None) or []
            self._round_keys = self._hp.latest_round_keys(rounds, self.mission_id)
        return self._round_keys

    def _is_this_round(self, eff):
        """Picked in the round just drafted. Distinct from _is_new: an effect picked
        again this round may well have been patched already, which is exactly the case
        that was hard to find in the list."""
        return (eff.get('tag'), eff.get('name')) in self._this_round_keys()

    @staticmethod
    def _group_targets(targets):
        """[(representative, [members])] — targets sharing a `group` collapse to one row.

        Opt-in via an explicit `"group"` key rather than by inferring it from equal
        labels, so adding a group to one effect cannot silently merge rows in another.

        The point is fields that are one CONCEPT split across several plugin fields:
        Cover Chance is Cover Chance + its Max + the shielded and depleted variants
        (and Cover Chance Time in ODST), and asking for five numbers that should all
        move together is just five chances to set them inconsistently.

        Order is by first appearance, so the display order the file implies is kept.
        """
        order = []
        groups = {}
        for t in targets:
            key = t.get('group') if isinstance(t, dict) else None
            if not key:
                order.append(('', t))          # ungrouped: its own row, as before
                continue
            if key not in groups:
                groups[key] = []
                order.append((key, t))
            groups[key].append(t)
        out = []
        for key, first in order:
            out.append((first, groups[key] if key else [first]))
        return out

    def _populate(self):
        self._clear_layout(self.form)
        self.rows = []
        self._effect_boxes = []     # (name, box) for the search jump
        # Boxes the "next effect from this round" jump walks, in the order they are
        # rendered so the jump follows what the eye sees rather than run order.
        self._marked_boxes = []     # picked this round (the amber 🔆 boxes)
        self._new_boxes = []        # not patched to a map yet (the blue 🆕 boxes)
        self._search_idx = -1
        self._marked_idx = -1
        self._jump_order_idx = -1   # row order changed; restart the empty-entry cursor

        def render_group(grp, effs, color="#4CAF50"):
            hdr = QLabel(grp)
            hdr.setStyleSheet(f"font-weight: bold; font-size: 15px; color: {color}; margin-top: 8px;")
            self.form.addWidget(hdr)
            for eff in effs:
                box = self._effect_box(eff)
                self._effect_boxes.append((eff.get('name', ''), box))
                if self._is_this_round(eff):
                    self._marked_boxes.append(box)
                if self._is_new(eff):
                    self._new_boxes.append(box)
                self.form.addWidget(box)

        groups = self._hp.group_effects(self.effects)
        if CONFIG.get('show_new_at_top'):
            # #7: a "New" section first (effects not yet patched, in normal order),
            # then the regular groups with those effects removed so each shows once.
            new_effs = [e for e in self.effects if self._is_new(e)]
            # Only split when the list is genuinely mixed. Before the first patch of
            # a run — and after loading a save written before patched_effect_keys
            # existed — *everything* is new, and hoisting all of it reorders nothing
            # while making the real groups vanish behind one header.
            if new_effs and len(new_effs) < len(self.effects):
                render_group(f"🆕 New effects ({len(new_effs)})", new_effs, color="#8fb8ff")
                newset = {id(e) for e in new_effs}
                groups = [(g, [e for e in effs if id(e) not in newset]) for g, effs in groups]
        for grp, effs in groups:
            if effs:
                render_group(grp, effs)
        self.form.addStretch()

    def _toggle_new_top(self, on):
        CONFIG['show_new_at_top'] = bool(on)
        save_settings()
        self._populate()

    def _search_effect(self, text, advance=False, back=False):
        """Jump to a matching effect box; Enter/F3 walks the matches, Shift+ walks back.

        The counter matters as much as the jump: without "3/11" there is no way to tell
        a search that found one thing from one that is parked on the first of eleven,
        which is what made cycling look broken."""
        q = (text or '').strip().lower()
        lbl = getattr(self, 'search_count', None)
        if not q:
            self._search_idx = -1
            if lbl is not None:
                lbl.setText("")
            return
        matches = [box for nm, box in getattr(self, '_effect_boxes', []) if q in nm.lower()]
        if not matches:
            self._search_idx = -1
            if lbl is not None:
                lbl.setText("no match")
            return
        cur = getattr(self, '_search_idx', -1)
        if not advance:
            idx = 0                       # typing restarts at the first match
        elif back:
            idx = (cur - 1) % len(matches)
        else:
            idx = (cur + 1) % len(matches)
        self._search_idx = idx
        if lbl is not None:
            lbl.setText("%d/%d" % (idx + 1, len(matches)))
        self._scroll.ensureWidgetVisible(matches[idx], 50, 60)

    def _effect_box(self, eff):
        is_new = self._is_new(eff)
        is_now = self._is_this_round(eff)
        title = ('🆕 ' if is_new else '') + ('🔆 ' if is_now else '') \
            + f"{eff['name']}   ×{eff['count']}"
        box = QGroupBox(title)
        if is_now:
            # Picked this round — amber, and it WINS over the "new" border: an effect
            # drafted again after being patched shows no other cue, and finding this
            # round's picks quickly is the point.
            box.setStyleSheet("QGroupBox { border: 2px solid #e0a94a; border-radius: 5px; "
                              "margin-top: 8px; } QGroupBox::title { color: #e0a94a; }")
            box.setToolTip("Picked in the latest round" + (" (not patched yet)" if is_new else
                                                          " (already patched in an earlier round)"))
        elif is_new:
            # #6: highlight effects not yet applied to a map; cleared on the next patch.
            box.setStyleSheet("QGroupBox { border: 2px solid #8fb8ff; border-radius: 5px; "
                              "margin-top: 8px; } QGroupBox::title { color: #8fb8ff; }")
        v = QVBoxLayout(box)
        hdr = QHBoxLayout()
        hdr.addStretch()
        rm = QPushButton("✕ Remove")
        rm.setToolTip("Delete this effect from the run entirely (every round that picked it)")
        rm.setMaximumWidth(90)
        rm.setStyleSheet("QPushButton { background-color:#3a2222; color:#e0a0a0; border:1px solid #5a3a3a; "
                         "border-radius:3px; padding:2px 8px; font-size:11px; } "
                         "QPushButton:hover { background-color:#5a2a2a; }")
        rm.clicked.connect(lambda _=False, e=eff: self._remove_effect(e))
        hdr.addWidget(rm)
        v.addLayout(hdr)
        if eff.get('_missing_in_db'):
            warn = QLabel("⚠ Effect not present in halo.json — using the saved snapshot; it may be outdated.")
            warn.setStyleSheet("color: #e05a5a; font-size: 12px; font-weight: bold;")
            warn.setWordWrap(True)
            v.addWidget(warn)
        _sk = skull_conflict(eff, getattr(self.parent_gui, 'run_state', None))
        if _sk:     # the skull zeroes this field first — say so before a value is typed
            sw = QLabel(f"☠ Affected by Skull: {_sk} — it zeroes this field before your "
                        "edit, so a multiply stays 0. Use = or + to set a value that sticks.")
            sw.setWordWrap(True)
            sw.setStyleSheet(f"color: #{MOD_COLORS['skull']['border']}; font-size: 12px; font-weight: bold;")
            v.addWidget(sw)
        _games = self.parent_gui.db.get_games() if self.parent_gui else None
        _desc = effect_desc(eff, self.game, _games)
        if _desc:
            d = QLabel(_desc)
            d.setWordWrap(True)
            d.setStyleSheet("color: #aaa; font-size: 12px;")
            _dbg = effect_debug_desc(eff, self.game, _games)
            if _dbg:
                d.setToolTip(_dbg)
            v.addWidget(d)
        tagl = QLabel(eff['tag'])
        tagl.setStyleSheet("color: #666; font-size: 11px; font-family: monospace;")
        v.addWidget(tagl)

        # Direction indicator is now PER FIELD (see the row loop); the legend at the
        # top of the dialog explains the 🔺/🔻 symbols. A mod-level harder_when
        # applies to all its fields; a target may override with its own harder_when.
        targets, fallback = self._effect_targets(eff)
        if eff.get('skull'):
            # #7: a skull is a whole-map rule with no per-field targets, so the
            # "no target defined" and fallback warnings don't apply — having none
            # is correct here. Say what it will do instead.
            note = QLabel("☠ Skull — a whole-map rule, applied on patch. Nothing to set.")
            note.setStyleSheet(f"color: #{MOD_COLORS['skull']['border']}; font-size: 12px;")
            note.setWordWrap(True)
            v.addWidget(note)
        elif fallback:
            flag = QLabel("Not defined in halo.json — using fallback field(s) from magnitude_presets.")
            flag.setStyleSheet("color: #e0b83a; font-size: 12px;")
            flag.setWordWrap(True)
            v.addWidget(flag)
        elif not targets:
            note = QLabel("⚠ No target defined in halo.json — add one with ‘＋ field’ below.")
            note.setStyleSheet("color: #e08a3a; font-size: 12px;")
            note.setWordWrap(True)
            v.addWidget(note)

        local_rows = []   # (target, line-edit) of THIS effect, for derived wiring
        for t, _members in self._group_targets(targets):
            if t.get('follows_choice'):
                # Slaved to this card's choice row: it takes whatever that row is set
                # to, so giving it an input of its own would only invite the two to
                # disagree. Handled entirely in the plan builder.
                continue
            row = QHBoxLayout()
            derived = t.get('derived')
            # per-field direction symbols (target overrides the mod's). harder_when
            # marks the direction that makes the game HARDER (red ▲/▼); easier_when the
            # direction that makes it EASIER (green ▲/▼). Both are the geometric glyph
            # tinted through rich text rather than an emoji, so the pair matches
            # exactly and each can carry its own colour. The two are opposites, so
            # normally only one is set per field.
            def _dir(kind):
                v = t.get(kind) or eff.get(kind)
                v = resolve_gamed(v, self.game) if isinstance(v, dict) else v
                return v.lower() if isinstance(v, str) else ''
            hw = _dir('harder_when')
            ew = _dir('easier_when')
            hw_glyph = '▲' if hw == 'increased' else ('▼' if hw == 'decreased' else '')
            ew_glyph = '▲' if ew == 'increased' else ('▼' if ew == 'decreased' else '')
            # 'label' overrides the displayed name only — t['field'] stays the real,
            # per-game-resolved field the patch actually reads/writes (e.g. H2's
            # "Starting Health Damage" internally, shown to the user as the more
            # meaningful "Starting Health Modifier").
            # `group` names the row when several fields share one input; `label`
            # still renames a single field. Both are display only — t['field'] stays
            # the real per-game-resolved field the patch reads and writes.
            fname = (t.get('group') or t.get('label') or t['field']) + (
                f"  [{_DIFF_TO_PUBLIC.get(self.target_difficulty, self.target_difficulty)}]"
                if t.get('difficulty') else "")
            if t.get('diff_suffix') or t.get('diff_prefix'):
                fname += "  [%s]" % self._hp.DIFFICULTY_SUFFIX_MAP.get(self.target_difficulty, self.target_difficulty)
            if t.get('diff_prefix_nl'):
                fname += "  [%s]" % ('Legendary' if self.target_difficulty == 'Impossible' else 'Normal')
            if t.get('custom'):
                fname += "  (preset)"
            if t.get('negate'):
                fname += "  (needs negative values for some reason)"
            if derived:
                fname += "  (auto = " + " + ".join(derived) + ")"
            if t.get('set') is not None:
                fname += "  (fixed → %s)" % t['set']
            # #1: field name on top, operator input directly below it.
            left = QVBoxLayout()
            left.setSpacing(2)
            lbl = QLabel(fname)
            if hw_glyph or ew_glyph:
                # Rich text only where a symbol is shown, so it can be tinted. Escape
                # the rest and keep the double-spacing HTML would otherwise collapse.
                marks = ''
                if hw_glyph:
                    marks += f'<span style="color: {HARDER_RED};">{hw_glyph}</span> '
                if ew_glyph:
                    marks += f'<span style="color: {EASIER_GREEN};">{ew_glyph}</span> '
                lbl.setTextFormat(Qt.RichText)
                lbl.setText(marks + html.escape(fname).replace('  ', '&nbsp; '))
            lbl.setWordWrap(True)   # #1: wrap long field names instead of clipping
            left.addWidget(lbl)
            inrow = QHBoxLayout()
            le = QLineEdit()
            le.setMaximumWidth(120)
            if derived:
                # Auto-computed field: display-only; recalculated at patch time.
                le.setReadOnly(True)
                le.setToolTip("Auto-computed from the fields above; not editable.")
                le.setStyleSheet("background-color: #101010; color: #7ac07a; "
                                 "border: 1px dashed #3a3a3a; padding: 4px; border-radius: 3px;")
            elif t.get('choice'):
                # Enum choice: a dropdown of the options THIS GAME's plugin defines, so
                # a game that reorders or renames them needs no halo.json change. The
                # value is applied by name, never by index.
                _cls = self._hp.hm.split_tag(target_tag(eff, t))[0]
                _plug = self.registry.get(_cls)
                _fld = _plug.find(t['field'], t.get('block'),
                                  t.get('nth', 0) or 0) if _plug else None
                _opts = (_fld or {}).get('options') or {}
                # options is {lowercased name: value}; one stable display order
                # across games -- the pick is applied by name, so order is cosmetic.
                _names = choice_option_names(_opts, t.get('options'))
                le = QComboBox()
                le.addItems(_names or ['(no options)'])
                le.setMaximumWidth(140)
                # Preselect the weapon's CURRENT value, not the first option. A
                # choice row always emits its set, so defaulting to index 0 would have
                # made every untouched Firing Noise card silence the weapon.
                _prev = self.presets.get(choice_preset_key(eff, t['field']))
                if not _prev:
                    # picks made before the key stopped carrying the game
                    _prev = self.presets.get(self._hp.preset_key(
                        eff['tag'], eff['name'], t['field'], self.game))
                if not _prev:
                    _cur = self._vanilla_num(target_tag(eff, t), t['field'],
                                             t.get('block'), t.get('nth', 0) or 0)
                    if _cur is not None:
                        _byval = {v: n for n, v in _opts.items()}
                        _prev = (_byval.get(int(_cur)) or '').title() or None
                if _prev:
                    _i = le.findText(str(_prev), Qt.MatchFixedString)
                    if _i >= 0:
                        le.setCurrentIndex(_i)
                le.setToolTip("Sets %s outright. Options come from this game's own "
                              "plugin and are applied by NAME, so the pick carries "
                              "across games even though Reach stores this enum in a "
                              "different order." % t['field'])
            elif t.get('set') is not None:
                # Fixed set (enum enabler): display-only, always applied with the effect.
                le.setReadOnly(True)
                le.setText("= %s" % t['set'])
                le.setToolTip("Always set to %s whenever this effect is patched." % t['set'])
                le.setStyleSheet("background-color: #101010; color: #d0a24a; "
                                 "border: 1px dashed #3a3a3a; padding: 4px; border-radius: 3px;")
            elif t.get('sprint') == 'enable':
                # Enabler card: no magnitude — drafting it unlocks sprint for the run.
                le.setReadOnly(True)
                le.setText("= on")
                le.setToolTip("Unlocks sprint for the rest of the run when this card is drafted.")
                le.setStyleSheet("background-color: #101010; color: #d0a24a; "
                                 "border: 1px dashed #3a3a3a; padding: 4px; border-radius: 3px;")
            elif t.get('sprint'):
                # Ability tuning card — a full operator applied to the Options base for
                # this value (in row order, so multiple cards stack). Same operator
                # grammar as any other field: -x / +x / *x / =x. Lower cooldown is the
                # improvement, so cut it with -x or *0.x.
                unit = {'speed': '% of run speed', 'duration': 'seconds',
                        'cooldown': 'seconds', 'os_mult': 'x normal shield',
                        'regen_percent': '% of max health', 'regen_duration': 'seconds',
                        'camo_duration': 'seconds',
                        'camo_cooldown': 'seconds'}.get(t['sprint'], '')
                le.setPlaceholderText("-n / +n / *n (or xn) / =n")
                le.setToolTip("An operator on the base %s %s (in %s): +n/-n add or "
                              "subtract, *n (or xn) scales, =n sets."
                              % (ability_of_param(t['sprint']) or 'ability',
                                 t['sprint'], unit))
                key = self._hp.preset_key(eff['tag'], eff['name'], t['field'], self.game)
                if key in self.presets and not isinstance(self.presets[key], list):
                    le.setText(str(self.presets[key]))
            else:
                le.setPlaceholderText("-n / +n / *n (or xn) / =n")
                key = self._hp.preset_key(eff['tag'], eff['name'], t['field'], self.game)
                if key in self.presets and not isinstance(self.presets[key], list):
                    le.setText(str(self.presets[key]))
                else:
                    fallback = self._fallback_preset_value(eff, t)
                    if fallback is not None:
                        le.setText(str(fallback))
                        le.setToolTip("Carried over from %s (no value set for this field yet)"
                                      % self._FIELD_CARRYOVER.get(t['field'], ''))
                    elif CONFIG.get('carry_magnitudes_across_games', True):
                        # Same card, same field, previous game. Shown in the carried
                        # colour so it is obvious this is a suggestion from the last
                        # leg rather than something typed for this one — it still has
                        # to be applied to be remembered here.
                        carried = self._carry_from_earlier_game(eff, t)
                        if carried is not None:
                            val, src_game = carried
                            le.setText(str(val))
                            le.setStyleSheet("color: #c8b48a;")
                            le.setToolTip("Carried over from %s — this card's magnitude "
                                          "on the previous game. Patch to keep it, or "
                                          "clear it to leave the field alone."
                                          % src_game)
            if hasattr(le, 'isReadOnly') and not le.isReadOnly():
                # #7: rewrite shorthand into its canonical form once the field is left,
                # so '*.5' reads back as '*0.5' (and is remembered, and shared, that
                # way). Purely cosmetic -- parse_operator accepted both all along.
                le.editingFinished.connect(
                    lambda ed=le: ed.setText(self._hp.hm.normalize_op_text(ed.text())))
            inrow.addWidget(le)
            eh = le.sizeHint().height()   # keep row-adornment buttons the input's height
            # #1: debug-only per-field patch — write just this one field to the map.
            if (CONFIG.get('debug_mode') and not derived
                    and t.get('set') is None and not t.get('choice')):
                one = QPushButton("⤓ field")
                one.setMaximumWidth(72)
                one.setFixedHeight(eh)   # don't inflate the row (misaligns the value column)
                one.setToolTip("Patch ONLY this field into the map now (debug)")
                one.clicked.connect(lambda _=False, e=eff, tt=t, ed=le: self._apply_single(e, tt, ed))
                inrow.addWidget(one)
            if t.get('custom'):
                rm = QPushButton("✕")
                rm.setMaximumWidth(28)
                rm.setFixedHeight(eh)
                rm.setToolTip("Remove this fallback field")
                rm.clicked.connect(lambda _=False, e=eff, tt=t: self._remove_custom(e, tt))
                inrow.addWidget(rm)
            inrow.addStretch()
            left.addLayout(inrow)
            leftw = self._wrap(left)
            leftw.setMinimumWidth(240)
            row.addWidget(leftw)
            # #1/#2: variant values on the right, one line per distinct value, plus
            # every difficulty's value where the field has one per difficulty.
            _vals = self._variant_values_str(target_tag(eff, t), t, eff)
            _diffs = self._difficulty_values_str(eff['tag'], t)
            variants = QLabel(_vals + ('\n' + _diffs if _diffs else ''))
            variants.setStyleSheet("color: #7aa0c0; font-size: 12px; font-family: monospace;")
            variants.setWordWrap(True)
            variants.setAlignment(Qt.AlignTop)
            row.addWidget(variants, 1)
            v.addWidget(self._wrap(row))
            # Every member of the group is registered against the SAME input, so one
            # value drives them all. self.rows is what builds the patch plan, so
            # grouping needs no change there — each field is still planned
            # individually, they just share where their operator came from.
            for _mt in _members:
                self.rows.append((eff, _mt, le))
            local_rows.append((t, le))

        # Wire derived rows: live-recompute from the source rows' vanilla values
        # with the user's pending operators applied.
        for dt, dle in [(t2, l2) for t2, l2 in local_rows if t2.get('derived')]:
            def make_upd(dt=dt, dle=dle, srcs=tuple(dt['derived']), tag=eff['tag']):
                def upd():
                    total, seen = 0.0, 0
                    for t2, l2 in local_rows:
                        f2 = t2.get('field')
                        if t2 is dt or f2 not in srcs:
                            continue
                        base_v = self._vanilla_num(tag, f2, t2.get('block'),
                                                   t2.get('nth', 0) or 0)
                        if base_v is None:
                            continue
                        txt = row_value(l2).strip()
                        parsed = self._hp.hm.parse_operator(txt) if txt else None
                        val = (self._hp.hm.OP_FUNCS[parsed[0]](base_v, parsed[1])
                               if parsed else base_v)
                        total += val
                        seen += 1
                    dle.setText(str(int(round(total))) if seen else "?")
                return upd
            upd = make_upd()
            for t2, l2 in local_rows:
                if t2 is not dt and t2.get('field') in dt['derived']:
                    l2.textChanged.connect(upd)
            upd()

        if CONFIG.get('debug_mode'):    # developer-only: add/override an arbitrary field
            addbtn = QPushButton("＋ field")
            addbtn.setMaximumWidth(120)
            addbtn.setToolTip("Add / override the patch field for this effect")
            addbtn.clicked.connect(lambda _=False, e=eff: self._add_custom_field(e))
            v.addWidget(addbtn)
        return box

    def _add_custom_field(self, eff):
        text, ok = QInputDialog.getText(
            self, "Add / override field",
            "Plugin field name (use 'Block::Field' if it lives in a block):")
        if not ok or not text.strip():
            return
        field, block = text.strip(), None
        if '::' in field:
            block, field = [s.strip() for s in field.split('::', 1)]
        key = self._hp.preset_key(eff['tag'], eff['name'], self._CUSTOM, self.game)
        lst = self.presets.get(key) or []
        lst.append({'field': field, 'block': block})
        self.presets[key] = lst
        self._hp.save_presets(self.presets_path, self.presets)
        self._populate()

    def _remove_custom(self, eff, target):
        key = self._hp.preset_key(eff['tag'], eff['name'], self._CUSTOM, self.game)
        lst = [c for c in (self.presets.get(key) or [])
               if not (c.get('field') == target['field'] and c.get('block') == target.get('block'))]
        if lst:
            self.presets[key] = lst
        else:
            self.presets.pop(key, None)
        self._hp.save_presets(self.presets_path, self.presets)
        self._populate()

    def _on_difficulty_changed(self, internal):
        # #2: switch the difficulty slot; vanilla values re-read from the same map.
        # `internal` is the game's slot name (Hard/Impossible), not the public label.
        self.target_difficulty = internal
        CONFIG['target_difficulty'] = internal
        save_settings()
        self._populate()

    # ---- path handling ----
    def _browse_mcc_root(self):
        start = self.mcc_edit.text().strip() or str(app_data_dir())
        path = QFileDialog.getExistingDirectory(
            self, "Select the 'Halo The Master Chief Collection' folder", start)
        if path:
            self._set_mcc_root(path)

    def _set_mcc_root(self, path):
        """Remember the MCC folder and re-resolve this dialog's map from it."""
        self.mcc_edit.setText(path)
        CONFIG['mcc_root'] = path
        save_settings()
        if self.map_subdir and self.mission_id:
            found = self._hp.default_map_path(path, self.map_subdir, self.mission_id)
            if found:
                self.map_edit.setText(found)
                self._reload()

    def _browse_plugins(self):
        start = self.plugins_edit.text().strip() or str(app_data_dir())
        path = QFileDialog.getExistingDirectory(self, "Select Assembly plugins folder", start)
        if path:
            self.plugins_edit.setText(path)
            self._reload()

    def _browse_map(self):
        start = self.map_edit.text().strip() or str(app_data_dir())
        path, _ = QFileDialog.getOpenFileName(self, "Select .map file", start, "Map files (*.map)")
        if path:
            self.map_edit.setText(path)
            self._reload()

    def _reload(self):
        # #1: persist the plugins path and rebuild the registry + vanilla values.
        CONFIG['assembly_plugins_dir'] = self.plugins_edit.text().strip()
        save_settings()
        self._build_registry()
        self._srcmap = None
        self._populate()

    def _build_weapon_swap_group(self):
        """Sliders (one per unique arsenal weapon) for scattering picked weapons into
        the map's weapon placements; sum capped at 100%. None if no arsenal/parent."""
        self._swap_sliders = {}
        self._swap_total_lbl = None
        # #7: with map-replacement offered as per-weapon cards, the sliders are the
        # same mechanism twice — hide them so there's one obvious place to set it.
        if CONFIG.get('weapon_swap_cards'):
            return None
        rs = getattr(self.parent_gui, 'run_state', None) if self.parent_gui else None
        if rs is None:
            return None
        db = getattr(self.parent_gui, 'db', None)
        arsenal = []
        for pl in ('player1', 'player2'):
            try:
                for w in rs.weapons_for(pl):
                    if w and w not in arsenal and not (db and db.is_grenade(w)):
                        arsenal.append(w)   # grenades are equipment, not swappable weapons
            except Exception:
                pass
        if not arsenal:
            return None
        saved = (getattr(rs, 'options', {}) or {}).get('weapon_swap_rates', {})
        self._swap_spins = {}
        box = QGroupBox("Replace map weapons with picks (scattered across the level)")
        box.setStyleSheet(
            "QGroupBox { color:#e0e0e0; border:1px solid #3a3a3a; border-radius:5px; "
            "margin-top:8px; padding:8px 6px 6px 6px; } "
            "QGroupBox::title { subcontrol-origin: margin; left:10px; padding:0 4px; } "
            "QSlider::groove:horizontal { height:6px; background:#242424; border-radius:3px; } "
            "QSlider::sub-page:horizontal { background:#2f7a3a; border-radius:3px; } "
            "QSlider::add-page:horizontal { background:#242424; border-radius:3px; } "
            "QSlider::handle:horizontal { background:#4CAF50; width:14px; margin:-5px 0; border-radius:7px; } "
            "QSlider::handle:horizontal:hover { background:#69d16b; } "
            "QSpinBox { background:#141414; color:#8fe08f; border:1px solid #3a3a3a; "
            "border-radius:3px; padding:2px 4px; } "
            "QSpinBox:focus { border:1px solid #4CAF50; }")
        v = QVBoxLayout(box)
        for w in arsenal:
            row = QHBoxLayout()
            nl = QLabel(w); nl.setMinimumWidth(170); nl.setStyleSheet("color:#e0e0e0;")
            sl = QSlider(Qt.Horizontal); sl.setRange(0, 100); sl.setValue(int(saved.get(w, 0)))
            sp = QSpinBox(); sp.setRange(0, 100); sp.setSuffix("%"); sp.setFixedWidth(70)
            sp.setValue(sl.value()); sp.setToolTip("Type a %, or drag the slider")
            sl.valueChanged.connect(lambda val, ww=w: self._set_swap(ww, val))
            sp.valueChanged.connect(lambda val, ww=w: self._set_swap(ww, val))
            row.addWidget(nl); row.addWidget(sl, 1); row.addWidget(sp)
            v.addLayout(row)
            self._swap_sliders[w] = sl
            self._swap_spins[w] = sp
        self._swap_total_lbl = QLabel()
        v.addWidget(self._swap_total_lbl)
        self._update_swap_total()
        return box

    def _set_swap(self, weapon, val):
        """Slider/spin both route here: cap so the total across weapons stays ≤ 100%,
        then mirror the capped value into both widgets (signals blocked)."""
        others = sum(s.value() for k, s in self._swap_sliders.items() if k != weapon)
        val = max(0, min(int(val), 100 - others))
        for wdg in (self._swap_sliders[weapon], self._swap_spins.get(weapon)):
            if wdg is not None and wdg.value() != val:
                wdg.blockSignals(True); wdg.setValue(val); wdg.blockSignals(False)
        self._update_swap_total()

    def _update_swap_total(self):
        if self._swap_total_lbl is not None:
            t = sum(s.value() for s in self._swap_sliders.values())
            self._swap_total_lbl.setText(f"Total: {t}% of the map's weapon spots (max 100%)")
            self._swap_total_lbl.setStyleSheet("color:%s; font-size:12px;" % ('#e0803a' if t >= 100 else '#888'))

    def _weapon_swaps_spec(self):
        """{weap-tag: rate} from the sliders, or None. Also snapshots the rates onto
        the run so they persist for the session."""
        db = getattr(self.parent_gui, 'db', None) if self.parent_gui else None
        if db is None:
            return None
        rates, swaps = {}, {}
        for wname, sl in getattr(self, '_swap_sliders', {}).items():
            if sl.value() <= 0:
                continue
            rates[wname] = sl.value()
            tag = db.weap_tag_for(wname, self.game)
            if tag:
                swaps[tag] = swaps.get(tag, 0.0) + sl.value() / 100.0
        rs = getattr(self.parent_gui, 'run_state', None)
        if rs is not None and rates:
            opts = getattr(rs, 'options', None)
            if isinstance(opts, dict):
                opts['weapon_swap_rates'] = rates
        return swaps or None

    def _player_slots(self):
        """(slot 1, slot 2) as run-state player keys, honouring the swap option.

        "Slot 1" is whatever the game treats as the first player: the Primary starting
        weapon before Halo 3, the Chief in Halo 3 co-op, spawn 0's equipment, and
        ability0. Swapping here rather than at each call site is what keeps weapons,
        equipment and abilities swapping TOGETHER — they are three separate specs and
        a per-spec flag would inevitably drift apart.
        """
        return (('player2', 'player1') if CONFIG.get('swap_player_loadouts')
                else ('player1', 'player2'))

    def _starting_weapons_spec(self):
        """Starting-weapons spec from the run's picks (Primary = P1's first weapon,
        Secondary = P2's). Coop is profile index 1: #1 can exclude it from the picked
        weapons, #2 can empty it entirely. Returns None if nothing to do."""
        if not self.parent_gui:
            return None
        rs = getattr(self.parent_gui, 'run_state', None)
        db = getattr(self.parent_gui, 'db', None)
        if rs is None or db is None:
            return None
        null_coop = bool(CONFIG.get('null_coop_starting_equipment'))    # #2
        # #1: also implied by #2 — don't hand the picked weapons to the coop profile.
        skip_coop = bool(CONFIG.get('coop_no_starting_weapons')) or null_coop
        prim = sec = prim2 = sec2 = None
        if CONFIG.get('set_starting_weapons'):
            slot1, slot2 = self._player_slots()
            p1 = getattr(rs, slot1 + '_weapon', None)
            p2 = getattr(rs, slot2 + '_weapon', None)
            # grenades and equipment aren't a valid Primary/Secondary starting weapon
            # (weap_tag_for would already return None for either — this just documents
            # why, and skips the lookup)
            def _startable(w):
                return (bool(w) and not is_sprint_item(w)
                        and not db.is_grenade(w) and not db.is_equipment(w))

            def _upgraded(weapon, player):
                """Start with the UPGRADE of this weapon once the player has drafted it.

                Taking Silenced SMG after starting with the SMG has to move the loadout
                onto the silenced one -- otherwise the upgrade is a card that changes
                nothing about what the player spawns holding. Bases are compared through
                resolve_weapon because an upgrade's base may be an alias of the name
                actually held (Auto Magnum bases on "Magnum", an alias of "Pistol").
                """
                if not weapon:
                    return weapon
                owned = set(rs.weapons_for(player))
                want = db.resolve_weapon(weapon)
                for up, base in weapon_upgrades().items():
                    if up in owned and db.resolve_weapon(base) == want:
                        return up
                return weapon

            p1 = _upgraded(p1, slot1)
            p2 = _upgraded(p2, slot2)
            prim = db.weap_tag_for(p1, self.game) if _startable(p1) else None
            sec = db.weap_tag_for(p2, self.game) if _startable(p2) else None

            def _second(player, first):
                """That player's next startable weapon after `first`.

                Only Halo 3 co-op uses it: there each character is one player, so the
                two slots of their profile are that player's own loadout rather than
                one slot each for P1 and P2."""
                for w in rs.weapons_for(player):
                    w = _upgraded(w, player)
                    if w != first and _startable(w):
                        t = db.weap_tag_for(w, self.game)
                        if t:
                            return t
                return None

            prim2 = _second(slot1, p1)
            sec2 = _second(slot2, p2)
        # #8: Halo 3 has two playable characters. With 2-player coop on, each pick
        # becomes its own character's weapon (P1 -> Chief, P2 -> Dervish) and the
        # coop options act on the respawn profiles; with it off, H3 behaves like the
        # earlier games but writes profile 0 only.
        h3_coop = (self.game == 'Halo 3') and bool(CONFIG.get('two_player_coop', True))
        profiles = [p for p in CONFIG.get('starting_weapon_profiles', [0, 1])
                    if not (skip_coop and p == 1)]
        null_profiles = [1] if null_coop else []
        # #5: with the option on, a slot we can't fill is emptied rather than left
        # holding the map's vanilla weapon — otherwise picking a grenade (or a weapon
        # this map lacks) silently leaves the vanilla gun in place, which reads as the
        # setting having done nothing.
        null_empty = bool(CONFIG.get('set_starting_weapons'))
        if not (prim or sec or prim2 or sec2) and not (null_profiles or (h3_coop and null_coop) or null_empty):
            return None
        # ODST picks the starting profile from the insertion point, and which one is
        # live can change mid-mission — so a run can spawn on a profile the patch never
        # touched and lose its weapons. With this on, every profile gets the picks.
        all_profiles = (self.game == 'Halo 3: ODST'
                        and bool(CONFIG.get('odst_all_starting_profiles')))
        # The targeted alternative to the blanket write: give each player the profile
        # their own insertion point uses, rather than one profile or all of them.
        # Opt-in and UNVERIFIED — see halo_patch.odst_profile_for and phase 4 of the
        # placement plan. It wins over all_profiles when both are set, since it is the
        # more specific instruction.
        by_insertion = (self.game == 'Halo 3: ODST'
                        and bool(CONFIG.get('odst_profiles_by_insertion')))
        return {'primary': prim, 'secondary': sec, 'null_empty_slots': null_empty,
                'primary2': prim2, 'secondary2': sec2,
                'all_profiles': all_profiles and not by_insertion,
                'by_insertion': by_insertion,
                'profiles': profiles, 'null_profiles': null_profiles,
                'h3_coop': h3_coop,
                'h3_all_chief': (self.game == 'Halo 3'
                                 and bool(CONFIG.get('h3_all_chief_profiles', True))),
                'skip_respawn': bool(CONFIG.get('coop_no_starting_weapons')),
                'null_respawn': null_coop}

    def _sprint_spec(self):
        """Sprint config for this patch. None for non-Halo-1 games (no sprint maps
        exist elsewhere). For Halo 1 it ALWAYS returns a spec — so a patch also turns
        sprint OFF when the feature is disabled — and the patcher no-ops on any map
        without the sprint weapon, so this is safe.

        `enabled_players` (a set of {0,1}) is PER PLAYER: both on "Start with Sprint",
        else just the player(s) who drafted the Sprint card (co-op). Speed/duration/
        cooldown are engine-global (shared), so the tuning cards stack for everyone."""
        if self.game != 'Halo 1':
            return None
        feature = bool(CONFIG.get('sprint_feature'))
        # Shared tuning: fold the drafted Speed/Duration/Cooldown cards onto the
        # Options base. Each card takes a full operator (+ - * =) just like any other
        # card and they apply in row order, so they stack the same way stacked field
        # ops do. `card_reports` records each card's before→after step so the patch
        # summary can show it (matching a normal field's "old -> new" line).
        vals = {'speed': float(CONFIG.get('sprint_speed_pct', 150)),
                'duration': float(CONFIG.get('sprint_duration_s', 3.0)),
                'cooldown': float(CONFIG.get('sprint_cooldown_s', 2.0)),
                'os_mult': float(CONFIG.get('overshield_mult', 3.0)),
                'regen_percent': float(CONFIG.get('regen_percent', 100.0)),
                'regen_duration': float(CONFIG.get('regen_duration_s', 5.0)),
                'camo_duration': float(CONFIG.get('camo_duration_s', 5.0)),
                'camo_cooldown': float(CONFIG.get('camo_cooldown_s', 30.0))}
        unit = {'speed': '%', 'duration': 's', 'cooldown': 's', 'os_mult': 'x',
                'regen_percent': '%', 'regen_duration': 's',
                'camo_duration': 's', 'camo_cooldown': 's'}
        card_reports = []
        for _eff, t, le in self.rows:
            p = t.get('sprint')
            if p not in vals:
                continue
            parsed = self._hp.hm.parse_operator(le.text())
            if not parsed:
                continue
            op, v = parsed
            before = vals[p]
            after = self._hp.hm.OP_FUNCS[op](before, v)
            vals[p] = after
            pre = 'x' if unit[p] == 'x' else ''
            suf = '' if unit[p] == 'x' else unit[p]
            card_reports.append({
                'effect': _eff.get('name', 'Ability'), 'tag': _eff.get('tag'),
                'field': '%s %s' % (ability_of_param(p) or 'ability', p),
                'old': '%s%g%s' % (pre, round(before, 3), suf),
                'new': '%s%g%s' % (pre, round(after, 3), suf)})
        speed, dur, cd = vals['speed'], vals['duration'], vals['cooldown']
        # Per-player ability. "Start with" gives both players the chosen ability;
        # otherwise each player gets whichever ability item their arsenal holds.
        player_abilities = {0: 'none', 1: 'none'}
        if feature:
            if bool(CONFIG.get('sprint_start_with', True)):
                which = CONFIG.get('ability_start_which', 'sprint')
                if which in ABILITY_ITEM_OF:
                    player_abilities = {0: which, 1: which}
            else:
                rs = getattr(self.parent_gui, 'run_state', None)
                if rs is not None:
                    for idx, p in enumerate(self._player_slots()):
                        for w in rs.weapons_for(p):
                            ab = ability_of_item(w)
                            if ab:
                                player_abilities[idx] = ab
                                break
        # Sprint's own per-player set, kept for the speed mechanic and older maps.
        enabled = {i for i, ab in player_abilities.items() if ab == 'sprint'}
        speed_pct = int(round(max(100.0, speed)))
        duration_ticks = max(1, round(max(0.5, dur) * 30))
        cooldown_ticks = max(0, round(max(0.0, cd) * 30))
        # If a card pushed a value past its floor (speed <100%, duration <0.5s,
        # cooldown <0s, an overshield below normal, and so on), the engine can't apply
        # the raw figure — show the last card for that value landing on the clamped
        # result, noting the pre-clamp figure.
        floor_hit = {'speed': speed < 100.0, 'duration': dur < 0.5, 'cooldown': cd < 0.0,
                     'os_mult': vals['os_mult'] < 1.0,
                     'regen_percent': vals['regen_percent'] < 1.0,
                     'regen_duration': vals['regen_duration'] < 0.1,
                     'camo_duration': vals['camo_duration'] < 0.5,
                     'camo_cooldown': vals['camo_cooldown'] < 0.0}
        clamped = {'speed': '%g%%' % speed_pct,
                   'duration': '%gs' % round(duration_ticks / 30.0, 3),
                   'cooldown': '%gs' % round(cooldown_ticks / 30.0, 3),
                   'os_mult': 'x%g' % max(1.0, vals['os_mult']),
                   'regen_percent': '%g%%' % max(1.0, vals['regen_percent']),
                   'regen_duration': '%gs' % max(0.1, vals['regen_duration']),
                   'camo_duration': '%gs' % max(0.5, vals['camo_duration']),
                   'camo_cooldown': '%gs' % max(0.0, vals['camo_cooldown'])}
        last_of = {}
        for i, cr in enumerate(card_reports):
            last_of[cr['field'].split()[-1]] = i
        for param, i in last_of.items():
            if floor_hit.get(param):
                card_reports[i]['new'] = '%s (clamped from %s)' % (
                    clamped[param], card_reports[i]['new'])
        return {
            'player_abilities': player_abilities,
            'enabled_players': enabled,
            'enabled': bool(enabled),
            'speed_pct': speed_pct,
            'duration_ticks': duration_ticks,
            'cooldown_ticks': cooldown_ticks,
            # Powerup tuning, drafted cards already folded in. The patcher converts
            # these to its raw globals (the multiplier to 1/75 units, the heal percent
            # to a per-tick rate).
            'os_mult': max(1.0, vals['os_mult']),
            'medi_percent': max(1.0, vals['regen_percent']),
            'medi_duration_ticks': max(1, round(max(0.1, vals['regen_duration']) * 30)),
            'regen_fx_every_by_game': CONFIG.get('regen_fx_every') or {},
            'camo_seconds': max(0.5, vals['camo_duration']),
            'camo_cooldown_ticks': max(0, round(max(0.0, vals['camo_cooldown']) * 30)),
            'card_reports': card_reports,
        }

    def _spawn_equipment_spec(self):
        """Halo 3 starting equipment: the equipment each player carries, appended as
        placements on their spawn.

        H3's Player Starting Profile has no equipment field at all, so unlike starting
        weapons this cannot be written into a profile — the item is placed on the
        starting location and walked into as the level loads. Player 1's equipment goes
        on spawn 0 and player 2's on spawn 1; with 2-player coop off both merge onto
        spawn 0. By default only each player's first equipment is placed; the
        'all selected' option places everything they carry."""
        if (not equipment_placement_supported(self.game)
                or not CONFIG.get('set_starting_equipment')):
            return None
        rs = getattr(self.parent_gui, 'run_state', None)
        db = getattr(self.parent_gui, 'db', None)
        if rs is None or db is None:
            return None
        first_only = not CONFIG.get('equipment_all_selected')

        def paths(names):
            # carried items are weapons AND equipment mixed; keep only equipment, as
            # eqip tag paths, order preserved, de-duplicated
            out, seen = [], set()
            for w in (names or []):
                if not db.is_equipment(w):
                    continue
                tag = db.eqip_tag_for(w, self.game)
                p = tag.split(' ', 1)[1].strip() if tag else None
                if p and p not in seen:
                    seen.add(p)
                    out.append(p)
                    if first_only:
                        break
            return out

        slot1, slot2 = self._player_slots()
        p1 = paths(getattr(rs, slot1 + '_weapons', None))
        p2 = paths(getattr(rs, slot2 + '_weapons', None))
        if bool(CONFIG.get('two_player_coop', True)):
            groups = [p1, p2]                       # each player's own spawn
        else:
            # solo: player 2 isn't in the level, so fold their picks onto spawn 0
            merged = p1 + [x for x in p2 if x not in p1]
            groups = [merged]
        if not any(groups):
            return None
        # ODST only: also drop at the level's mid-mission insertion points, not just at
        # the mission start. Off by default — arming every one of them is what put five
        # Invincibility pickups across ONI Alpha Site.
        return {'groups': groups,
                'all_insertions': bool(CONFIG.get('odst_equipment_all_insertions'))}

    def _zoom_ui_spec(self, plan):
        """weap tag paths of the Zoom effects in this plan, so scopeless weapons
        that gain magnification also get a scope overlay. The patcher skips any
        weapon already scoped (vanilla or shared HUD), so passing them all is safe."""
        if not CONFIG.get('zoom_ui_on_scopeless', True):
            return None
        tags = [item['tag'] for item in plan
                if item.get('name') == 'Zoom' and str(item.get('tag', '')).startswith('weap ')]
        return tags or None

    def _zoom_donor_candidates(self):
        """Scope-source weapons offered to the user: real scoped weapons that are
        guaranteed present on this mission's map (its level weapon pool)."""
        db = getattr(self.parent_gui, 'db', None)
        rs = getattr(self.parent_gui, 'run_state', None)
        if db is None or rs is None:
            return []
        mid = getattr(rs, 'mission_id', None)
        onmap = set(db.mission_weapons.get(mid, []) or [])
        # Honour an expanded ODST pool: with odst_pools_from_map on, the level really
        # does carry every weapon the prepared map supports, so a donor the halo.json
        # list happens not to mention is still a legitimate scope source. Read from the
        # map rather than the list, or the option widens the offers but not the donors.
        if CONFIG.get('odst_pools_from_map') and db.mission_games.get(mid) == 'Halo 3: ODST':
            onmap |= set(db.odst_map_pool(mid) or ())
        return [w for w in ZOOM_DONOR_WEAPONS.get(self.game, []) if w in onmap]

    def _build_zoom_source_row(self):
        """A combo to pick which weapon's scope overlay to copy, shown only when a
        weapon Zoom is being patched and there are eligible on-map donors. Defaults
        to the remembered choice when it's available on this map, else Auto."""
        if not CONFIG.get('zoom_ui_on_scopeless', True):
            return None
        if not any(e.get('name') == 'Zoom' and str(e.get('tag', '')).startswith('weap ')
                   for e in self.effects):
            return None
        cands = self._zoom_donor_candidates()
        if not cands:
            return None
        box = QGroupBox("Scope overlay source")
        h = QHBoxLayout(box)
        h.addWidget(QLabel("Copy the scope from:"))
        self.zoom_src_combo = QComboBox()
        self.zoom_src_combo.addItem("Auto (any scoped weapon on the map)", None)
        for w in cands:
            self.zoom_src_combo.addItem(w, w)
        remembered = (CONFIG.get('zoom_donor') or {}).get(self.game)
        if remembered in cands:
            self.zoom_src_combo.setCurrentIndex(cands.index(remembered) + 1)
        self.zoom_src_combo.currentIndexChanged.connect(self._on_zoom_src_changed)
        h.addWidget(self.zoom_src_combo)
        h.addStretch()
        return box

    def _on_zoom_src_changed(self):
        """Remember the choice per game (persisted); it is reused on any later map
        that has that weapon (else the patcher falls back to auto)."""
        w = self.zoom_src_combo.currentData()
        zd = dict(CONFIG.get('zoom_donor') or {})
        if w:
            zd[self.game] = w
        else:
            zd.pop(self.game, None)
        CONFIG['zoom_donor'] = zd
        save_settings()

    def _zoom_donor_spec(self):
        """The chosen scope-source as a weap tag path, or None for auto. Reads the
        combo when shown, else the remembered per-game preference."""
        combo = getattr(self, 'zoom_src_combo', None)
        w = combo.currentData() if combo is not None else (CONFIG.get('zoom_donor') or {}).get(self.game)
        db = getattr(self.parent_gui, 'db', None)
        if not w or db is None:
            return None
        return db.weap_tag_for(w, self.game)

    def _run_busy(self, fn, title="Patching", label="Working"):
        """Run fn() off the GUI thread while showing an animated busy dialog, so a long
        patch is visibly distinct from a hang. Returns fn()'s value; re-raises whatever
        it raised. Patching is pure file/tag work with no Qt calls, so a plain worker
        thread is safe — the GUI thread only spins the event loop and the dots."""
        result = {}

        def work():
            try:
                result['value'] = fn()
            except BaseException as e:      # carry it back to the GUI thread to re-raise
                result['error'] = e

        dlg = QProgressDialog(label, None, 0, 0, self)   # 0,0 = indeterminate busy bar
        dlg.setWindowTitle(title)
        dlg.setCancelButton(None)                        # patching can't be interrupted safely
        dlg.setWindowModality(Qt.WindowModal)
        dlg.setMinimumDuration(0)
        dlg.setAutoClose(False)
        dlg.setAutoReset(False)
        dlg.show()
        t = threading.Thread(target=work, daemon=True)
        t.start()
        dots = 0
        while t.is_alive():
            dots = dots % 3 + 1
            dlg.setLabelText(label + "." * dots + " " * (3 - dots))
            QApplication.processEvents()
            t.join(0.6)                                  # ~every 0.6 s a dot appears
        QApplication.processEvents()
        dlg.close()
        if 'error' in result:
            raise result['error']
        return result.get('value')

    def _apply(self):
        map_path = self.map_edit.text().strip()
        if not Path(map_path).is_file():
            QMessageBox.warning(self, "Map not found", f"Not a file:\n{map_path}")
            return

        # #7: canonicalize every entry BEFORE it is read, so the magnitudes stored in
        # the presets (and shared in the run file) are canonical too. editingFinished
        # can't be relied on here -- clicking Apply from a field that still has focus
        # doesn't always emit it, and a value typed and never left never emits at all.
        self._normalize_entries()

        # #7: Map Presence rows aren't tag edits — their magnitude is a percentage fed
        # to the same weapon-swap mechanism the sliders drive, so they're collected
        # here and merged into the swap spec rather than becoming plan ops.
        card_swaps, equip_swaps = {}, {}
        for eff, t, le in self.rows:
            if not (t.get('map_swap') or t.get('map_equip')):
                continue
            txt = row_value(le).strip()
            self.presets[self._hp.preset_key(eff['tag'], eff['name'], t['field'], self.game)] = txt
            parsed = self._hp.hm.parse_operator(txt)
            if not parsed:
                continue
            pct = parsed[1]
            if pct > 0:
                bucket = equip_swaps if t.get('map_equip') else card_swaps
                bucket[eff['tag']] = bucket.get(eff['tag'], 0.0) + pct / 100.0

        # Sprint tuning rows fold into the sprint spec (_sprint_spec) rather than
        # becoming plan ops, so like the swap rows above they're skipped below — but
        # their entered delta should still be remembered so reopening the dialog
        # restores it. The enabler row is read-only, so nothing to save there.
        for eff, t, le in self.rows:
            # Every ability parameter, not just the sprint three — a new one added to
            # ABILITY_CARD_PARAMS would otherwise silently fail to be remembered.
            p = t.get('sprint')
            if p and p != 'enable' and p in ABILITY_CARD_PARAMS:
                self.presets[self._hp.preset_key(
                    eff['tag'], eff['name'], t['field'], self.game)] = le.text().strip()

        plan_map = {}
        for eff, t, le in self.rows:
            if (t.get('derived') or t.get('set') is not None or t.get('choice')
                    or t.get('map_swap') or t.get('map_equip') or t.get('sprint')):
                continue          # display-only / fixed-set / choice / swap / sprint
            txt = row_value(le).strip()
            # #11: remember the input as-is, including an empty one — an empty entry is
            # a valid "leave this field alone" that sticks (so a cleared value doesn't
            # come back from a fallback next time). Only a non-empty input adds an op.
            self.presets[self._hp.preset_key(eff['tag'], eff['name'], t['field'], self.game)] = txt
            if not txt:
                continue
            key = (eff['tag'], eff['name'])
            plan_map.setdefault(key, {'tag': eff['tag'], 'name': eff['name'], 'ops': [],
                                      'init_defaults': eff.get('init_defaults'),
                                      'constraints': eff.get('constraints'),
                                      # whose effect this is, so a base weapon's edits
                                      # can be mirrored onto its upgrade's tag below
                                      'weapon': eff.get('weapon'),
                                      # An enemy/boss card's tag missing from the map
                                      # means that enemy isn't on this level — a SKIP,
                                      # not a failure. Covers enemy-owned WEAPONS too
                                      # (the Hunter's fuel rod is a weap tag under
                                      # objects\characters), which read as a broken
                                      # player-weapon card otherwise. cats: 2 specific
                                      # enemy, 3 enemy-general, 5 boss/hero.
                                      'absent_is_skip': eff.get('cat') in (2, 3, 5),
                                      # carried so the patcher can report it as skipped
                                      # rather than patching from a stale snapshot
                                      'missing_in_db': bool(eff.get('_missing_in_db'))})
            plan_map[key]['ops'].append({'field': t['field'], 'block': t.get('block'),
                                         **_diff_flavor(t),
                                         'index': t.get('index', 0), 'op_str': txt,
                                         'negate': t.get('negate'),
                                         'offset': t.get('offset'),
                                         'reload_anim': t.get('reload_anim'),
                                         'swap_anim': t.get('swap_anim'),
                                         'equip_drop': t.get('equip_drop'),
                                         # optional bounds on the RESULT (e.g. a
                                         # probability is 0..1 whatever was typed)
                                         'min': t.get('min'), 'max': t.get('max'),
                                         'zero_is': t.get('zero_is'),
                                         'tag': t.get('tag'),
                                         'nth': t.get('nth', 0) or 0})
        # Auto-computed fields: recompute whenever their effect has any edit.
        # Appended after the normal ops so the sources are already patched.
        for eff, t, le in self.rows:
            if not t.get('derived'):
                continue
            key = (eff['tag'], eff['name'])
            if key in plan_map:
                plan_map[key]['ops'].append({'field': t['field'], 'block': t.get('block'),
                                             'index': t.get('index', 0),
                                             'derived': list(t['derived'])})
        # Choice rows CREATE their plan entry rather than tagging along the way a
        # fixed set does: a card whose only target is the choice would otherwise never
        # be patched, because nothing else would have put its effect in the plan.
        for eff, t, le in self.rows:
            if not t.get('choice'):
                continue
            chosen = row_value(le).strip()
            self.presets[choice_preset_key(eff, t['field'])] = chosen
            if not chosen or chosen.startswith('('):
                continue
            key = (eff['tag'], eff['name'])
            plan_map.setdefault(key, {'tag': eff['tag'], 'name': eff['name'], 'ops': [],
                                      'init_defaults': eff.get('init_defaults'),
                                      'constraints': eff.get('constraints'),
                                      'weapon': eff.get('weapon'),
                                      'missing_in_db': bool(eff.get('_missing_in_db'))})
            plan_map[key]['ops'].append({'field': t['field'], 'block': t.get('block'),
                                         'index': t.get('index', 0),
                                         'nth': t.get('nth', 0) or 0,
                                         'tag': t.get('tag'),
                                         **_diff_flavor(t), 'set': chosen})
            # Followers ride along on the same pick. They are looked up on the effect
            # rather than tracked as rows, because they deliberately have no row.
            for f in eff.get('targets') or []:
                if not f.get('follows_choice'):
                    continue
                plan_map[key]['ops'].append({'field': f['field'],
                                             'block': f.get('block'),
                                             'index': f.get('index', 0),
                                             'nth': f.get('nth', 0) or 0,
                                             'tag': f.get('tag'),
                                             **_diff_flavor(f), 'set': chosen})

        # Fixed-set fields (e.g. Special-Fire Mode -> Overcharge) tag along whenever
        # their effect is being patched at all, so the enabler is applied with it.
        for eff, t, le in self.rows:
            if t.get('set') is None:
                continue
            key = (eff['tag'], eff['name'])
            if key in plan_map:
                plan_map[key]['ops'].append({'field': t['field'], 'block': t.get('block'),
                                             'index': t.get('index', 0), 'nth': t.get('nth', 0) or 0,
                                             **_diff_flavor(t), 'set': t['set']})
        plan = list(plan_map.values())
        plan = self._odst_shield_into_health(plan)
        # An upgrade weapon is a variant of its base, so the base's cards patch the
        # upgrade's tag as well — one card, both weapons. The upgrade's OWN tag for
        # that effect is read from its halo.json entry rather than guessed, since it
        # differs per effect; effects the upgrade has no counterpart for are left
        # alone, and a map without the upgrade reports the usual "not present".
        db = getattr(self.parent_gui, 'db', None)
        if db is not None and CONFIG.get('upgrade_inherits_base', True):
            for item in list(plan):
                if item.get('missing_in_db') or not item.get('weapon'):
                    continue
                twin_tag = db.upgrade_twin_tag(item['weapon'], item['name'], self.game)
                # Only mirror the tags the base card does NOT already patch. A tag may
                # name several paths with ' & ', and a plain inequality test missed the
                # overlap: Plasma Rifle's melee is "strike_melee & smash_melee" while the
                # Brute Plasma Rifle's is "strike_melee", so the mirror row applied
                # strike_melee a SECOND time and the card hit at double magnitude.
                extra = _tags_not_already_in(twin_tag, item.get('tag'))
                if extra:
                    plan.append({**item, 'tag': extra, 'mirrored_to_upgrade': True})
        # ODST escort levels: mirror the player's own vitality cards onto the Engineer
        # and the olifaunt, so the characters the mission fails without scale with the
        # player instead of staying at Bungie's numbers while the enemies climb.
        if (CONFIG.get('odst_escort_buff')
                and self.game == 'Halo 3: ODST'
                and self.mission_id in ESCORT_BUFF_MISSIONS):
            for item in list(plan):
                if item.get('missing_in_db') or item['name'] not in ESCORT_BUFF_CARDS:
                    continue
                for tag in ESCORT_BUFF_TAGS:
                    plan.append({**item, 'tag': tag, 'escort_buff': True,
                                 # a tag this level doesn't have (the olifaunt on Data
                                 # Hive) is a skip, not a failed patch
                                 'absent_is_skip': True})
        starting = self._starting_weapons_spec()
        # Cards and sliders are the same mechanism and never both shown, so whichever
        # is active supplies the swaps.
        weapon_swaps = card_swaps or self._weapon_swaps_spec()
        spawn_equipment = self._spawn_equipment_spec()
        zoom_ui = self._zoom_ui_spec(plan)
        remove_cutscenes = bool(CONFIG.get('remove_h3_cutscenes')) and self.game == 'Halo 3'
        # #7: skulls carry no per-field targets, so they never reach plan_map — collect
        # them straight off the effects list.
        skulls = [e['skull'] for e in self.effects if e.get('skull')]
        sprint = self._sprint_spec()
        # A spec that turns everything OFF rides along with other edits; it shouldn't
        # force a patch on an otherwise-empty selection (only ENABLING is standalone).
        active_abilities = sorted({a for a in (sprint or {}).get(
            'player_abilities', {}).values() if a and a != 'none'})
        sprint_on = bool(active_abilities)
        if (not plan and not starting and not weapon_swaps and not remove_cutscenes
                and not skulls and not equip_swaps and not spawn_equipment and not sprint_on):
            QMessageBox.information(self, "Nothing to apply",
                                   "Enter at least one operator, or set starting / map weapons.")
            return

        extras = ([] + (["set starting weapons"] if starting else [])
                  + ([f"place {sum(len(g) for g in spawn_equipment['groups'])} "
                      f"starting equipment"] if spawn_equipment else [])
                  + (["scatter map weapons"] if weapon_swaps else [])
                  + (["add scope UI where missing"] if zoom_ui else [])
                  + (["remove Cortana/Gravemind cutscenes"] if remove_cutscenes else [])
                  + ([f"apply skull: {', '.join(skulls)}"] if skulls else [])
                  + ([f"enable {', '.join(active_abilities)}"] if sprint_on else [])
                  + (["rescale metagame scores (needs an MCC restart)"]
                     if CONFIG.get('score_scaling') else [])
                  + (["retune the Red Plasma Rifle to the Brute Plasma Rifle"]
                     if (CONFIG.get('odst_red_plasma_as_brute')
                         and self.game == 'Halo 3: ODST') else [])
                  + (["also patch Mombasa Streets (the hub)"]
                     if self._odst_hub_path(map_path) else []))
        confirm = QMessageBox.question(
            self, "Apply to map?",
            f"Write {sum(len(i['ops']) for i in plan)} edit(s)"
            + (" + " + " + ".join(extras) if extras else "")
            + f" into:\n{map_path}\n\nA one-time backup (.bak) of the original will be made first.")
        if confirm != QMessageBox.Yes:
            return

        try:
            results, backup = self._run_busy(lambda: self._hp.apply_run(
                map_path, plan, self.registry,
                self.target_difficulty, game=self.game,
                starting=starting, weapon_swaps=weapon_swaps,
                zoom_ui=zoom_ui, zoom_donor=self._zoom_donor_spec(),
                remove_cutscenes=remove_cutscenes,
                skulls=skulls,
                equipment_swaps=equip_swaps or None,
                spawn_equipment=spawn_equipment,
                sprint=sprint,
                difficulty_baseline=self._baseline_spec(),
                red_plasma=(CONFIG.get('odst_brute_plasma_tuning')
                            if (CONFIG.get('odst_red_plasma_as_brute')
                                and self.game == 'Halo 3: ODST') else None),
                odst_downgrade=self._odst_downgrade_keep(),
                add_respawn_profile=bool(CONFIG.get('h2_add_respawn_profile', True)),
                extra_squads=(CONFIG.get('h2_extra_squads') or {}).get(self.mission_id),
                equipment_ai_drops=bool(CONFIG.get('odst_ai_equipment_drops'))
                and self.game == 'Halo 3: ODST'))
        except Exception as e:
            QMessageBox.critical(self, "Patch failed", _patch_error_text(e))
            return

        # Mombasa Streets gets the same plan, so the level the player passes through
        # between every mission is not left vanilla. Never fatal: the story mission
        # has already been written, and a hub failure must not report it as failed.
        hub = self._odst_hub_path(map_path)
        if hub and not _is_writable_now(hub):
            # MCC keeps Mombasa Streets RESIDENT for the whole ODST campaign — it is
            # the level the game returns to between missions, so once a run is under
            # way the file is held open and a patch either cannot be written or is
            # written and then ignored by the copy already in memory. Say so instead
            # of reporting a hub failure the player cannot act on.
            results.append({'effect': 'Mombasa Streets (hub)', 'field': 'patch',
                            'ok': True, 'skip': True,
                            'reason': 'the hub map is locked — MCC holds it open for '
                                      'the whole ODST campaign. Patch it with the game '
                                      'closed (or before starting the run).'})
            hub = None
        if hub:
            try:
                hub_results, _ = self._run_busy(lambda: self._hp.apply_run(
                    hub, plan, self.registry,
                    self.target_difficulty, game=self.game,
                    skulls=skulls,
                    red_plasma=(CONFIG.get('odst_brute_plasma_tuning')
                                if CONFIG.get('odst_red_plasma_as_brute') else None),
                    odst_downgrade=self._odst_downgrade_keep(),
                equipment_ai_drops=bool(CONFIG.get('odst_ai_equipment_drops'))
                and self.game == 'Halo 3: ODST'))
                ok = sum(1 for r in hub_results if r.get('ok') and not r.get('skip'))
                results.append({'effect': 'Mombasa Streets (hub)',
                                'tag': Path(hub).name, 'ok': True,
                                'field': '%d edit(s)' % ok,
                                'old': 'vanilla', 'new': 'patched with this run'})
            except Exception as e:
                results.append({'effect': 'Mombasa Streets (hub)', 'field': 'patch',
                                'ok': False, 'reason': str(e)})

        # Effects that were on screen but had no value typed produced no ops, so the
        # patcher never saw them and they'd otherwise stay "new" forever. Report them
        # as a deliberate skip so the summary accounts for every effect in the run.
        # Added before the patch log is written so it records them too.
        planned = {(i.get('tag'), i.get('name')) for i in plan}
        for eff in self.effects:
            if (eff.get('tag'), eff.get('name')) in planned or eff.get('skull'):
                continue
            # Sprint effects (the enabler + the Speed/Duration/Cooldown tuning cards)
            # never become plan ops — they're reported by _apply_sprint instead (an
            # aggregate line plus a per-card old→new line), so don't add a stray
            # "no value changed" skip for them here.
            if any(isinstance(t, dict) and t.get('sprint')
                   for t in (eff.get('targets') or [])):
                continue
            results.append({'tag': eff.get('tag'), 'effect': eff.get('name'),
                            'ok': True, 'skip': True, 'reason': 'no value changed'})

        # Metagame scores last, and never fatally: it writes a different file than the
        # map patch, so a failure here must not make a SUCCESSFUL map patch look failed.
        # Reported as a normal result row so the summary and the patch log both record it.
        if CONFIG.get('score_scaling'):
            # Its own busy dialog. This runs AFTER the patch dialog has closed, and with
            # the live push on it scans MCC's whole address space for the score table --
            # tens of seconds during which the window sat there with no bar and looked
            # hung. The label says which half is running so the wait is legible.
            label = ("Rescaling metagame scores and pushing them to MCC"
                     if CONFIG.get('score_live_push') else "Rescaling metagame scores")
            results.extend(self._run_busy(self._apply_score_scaling,
                                          title="Metagame scores", label=label))

        # AFTER the rescale: that regenerates scoredb.xml from the pristine baseline,
        # so a sign flip applied before it would simply be overwritten.
        if CONFIG.get('betrayal_marines_score'):
            results.extend(self._run_busy(
                lambda: self._apply_betrayal_scoring(skulls),
                title="Betrayal scoring",
                label="Setting how Marines score"))

        # Same footing: a live write to another process, never fatal to the map patch.
        if CONFIG.get('death_penalty_scaling'):
            results.extend(self._apply_death_penalty())

        self._hp.save_presets(self.presets_path, self.presets)
        self._write_patch_file(map_path, plan, results, backup)
        self._srcmap = None  # map changed on disk; re-read vanilla next time

        # #6: every effect present at patch time is no longer "new" — including the
        # ones left blank, which were a deliberate "leave this alone", not an oversight.
        rs = getattr(self.parent_gui, 'run_state', None)
        if rs is not None and any(r.get('ok') and not r.get('skip') for r in results):
            for eff in self.effects:
                rs.patched_effect_keys.add((eff.get('tag'), eff.get('name')))
            self._populate()
            # Hand the run (magnitudes included) to the shared folder, so the co-op
            # partner's machine can pick up this exact patch with one click. Done after
            # save_presets above, so the values written into it are the ones just used.
            if CONFIG.get('shared_session_autosave', True):
                exporter = getattr(self.parent_gui, 'export_shared_session', None)
                if exporter is not None:
                    self._shared_path = exporter()

        self._show_results(results, backup)

    def done(self, r):
        # #2: keep the magnitudes typed here, on EVERY close including Cancel.
        # They used to survive only a patch or an explicit press of ‘Save
        # magnitudes to presets’, so tuning a run and closing without patching
        # threw the numbers away — and, because the run file embeds magnitudes by
        # reading the preset FILE (see _run_bundle/run_magnitudes), the run saved
        # or shared afterwards carried none of them. Silent: closing a dialog is
        # not the moment for a report, and the keep button still gives one.
        try:
            self._save_magnitudes_now(report=False)
        except Exception:
            pass        # never let a preset write block the dialog from closing
        # Remember the size on close, including Cancel — a window preference, not a
        # patch setting. Read here rather than tracked on resize, so it's one write.
        CONFIG['patcher_dialog_size'] = [self.width(), self.height()]
        save_settings()
        super().done(r)

    def _show_results(self, results, backup):
        # #4: three buckets — Applied (a real write), Skipped (a deliberate no-op:
        # already-scoped scope, weapon that rounds/trims to 0, an H2-only field on
        # an H1 map), and Failed (an edit that should have landed but didn't).
        applied = [r for r in results if r.get('ok') and not r.get('skip')]
        skipped = [r for r in results if r.get('skip')]
        failed = [r for r in results if not r.get('ok') and not r.get('skip')]
        lines = [f"Applied {len(applied)}   ·   Skipped {len(skipped)}   ·   Failed {len(failed)}"]
        # #10: a short code standing for what was written, so two players can check
        # they ended up with the same patch instead of comparing lists by eye.
        code = self._hp.patch_signature(results, self.map_edit.text().strip(),
                                        self.target_difficulty)
        if code:
            lines.append(f"Patch code: {code}   (same code = same patch; compare with "
                         f"your co-op partner)")
            # #8: also park it in the main window, where it stays readable after
            # this dialog is gone. Every patch path lands here (_apply, the hub
            # pass and the debug single-field patch all end in _show_results), so
            # this is the one place it needs wiring.
            setter = getattr(self.parent_gui, 'set_last_patch_code', None)
            if setter is not None:
                setter(code, self.map_edit.text().strip(), self.target_difficulty)
        if backup:
            lines.append(f"Backup: {backup}")
        shared = getattr(self, '_shared_path', None)
        if shared:
            lines.append(f"Shared with co-op: {shared.name}  "
                         f"(other machine: Load Latest Shared Session)")
            self._shared_path = None
        lines.append("")
        def _fmt(x):
            return round(x, 4) if isinstance(x, (int, float)) else x

        def _val(r, key):
            # An enum reads back as its option name; halo_patch attaches those for any
            # field that has them, so a Firing Noise row says "Loud -> Medium" instead
            # of "2 -> 1" -- which on Reach would not even mean the same thing.
            return r.get(key + '_name') or _fmt(r.get(key))
        for r in applied:
            hint = ("   (needs negative values for some reason)" if r.get('negated')
                    else "   (auto-computed)" if r.get('derived') else "")
            if r.get('inherited_from'):
                hint += f"   (inherited from {r['inherited_from'].rsplit(chr(92), 1)[-1]})"
            tag = f"   [{r['tag']}]" if r.get('tag') else ""
            lines.append(f"  OK    {r['effect']}: {r.get('field', '')}  "
                         f"{_val(r, 'old')} -> {_val(r, 'new')}{tag}{hint}")
        for r in skipped:
            tag = f"   [{r['tag']}]" if r.get('tag') else ""
            why = r.get('reason') or r.get('new') or 'no change needed'
            lines.append(f"  SKIP  {r['effect']}: {r.get('field', '')}  ({why}){tag}")
        for r in failed:
            tag = f"   [{r['tag']}]" if r.get('tag') else ""
            lines.append(f"  FAIL  {r['effect']}: {r.get('field')}  ({r.get('reason')}){tag}")
        self.results.setPlainText("\n".join(lines))

    def _apply_single(self, eff, t, le):
        """#1 (debug): patch just this one field into the current map, using the
        operator currently in its box. Skips the starting/weapon/zoom passes."""
        map_path = self.map_edit.text().strip()
        if not Path(map_path).is_file():
            QMessageBox.warning(self, "Map not found", f"Not a file:\n{map_path}")
            return
        txt = le.text().strip()
        if not txt:
            QMessageBox.information(self, "Nothing to apply",
                                   "Enter an operator for this field first.")
            return
        op = {'field': t['field'], 'block': t.get('block'), **_diff_flavor(t),
              'index': t.get('index', 0), 'op_str': txt, 'negate': t.get('negate'),
              'nth': t.get('nth', 0) or 0}
        plan = [{'tag': eff['tag'], 'name': eff['name'], 'ops': [op],
                 'init_defaults': eff.get('init_defaults')}]
        try:
            # Incremental: patch this one field onto the live map, preserving the
            # other already-applied effects (don't restore the baseline).
            results, backup = self._run_busy(lambda: self._hp.apply_run(
                map_path, plan, self.registry,
                self.target_difficulty, game=self.game,
                from_baseline=False))
        except Exception as e:
            QMessageBox.critical(self, "Patch failed", _patch_error_text(e))
            return
        self.presets[self._hp.preset_key(eff['tag'], eff['name'], t['field'], self.game)] = txt
        self._hp.save_presets(self.presets_path, self.presets)
        self._write_patch_file(map_path, plan, results, backup)
        self._srcmap = None  # map changed on disk; re-read vanilla next time
        self._show_results(results, backup)

    def _patch_dir(self):
        return app_data_dir() / "patches"

    def _latest_patch_file(self):
        """The patch log this run most recently wrote, else the newest one for this
        map (patching happens per map, so that's the relevant history)."""
        if getattr(self, '_last_patch_file', None) and Path(self._last_patch_file).is_file():
            return Path(self._last_patch_file)
        mission = Path(self.map_edit.text().strip() or '').stem
        if not mission:
            return None
        found = sorted(self._patch_dir().glob(f"patch_{mission}_*.json"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        return found[0] if found else None

    def _open_patch_file(self):
        """#13: open the patch log for this run so its effects can be checked by hand."""
        target = self._latest_patch_file()
        if target is None:
            d = self._patch_dir()
            if not d.is_dir():
                QMessageBox.information(self, "No patch log yet",
                                        "Nothing has been patched yet — the log is written "
                                        "when you apply to a map.")
                return
            target = d          # fall back to the folder
        try:
            if sys.platform == 'win32':
                os.startfile(str(target))            # noqa: S606 - user-invoked
            else:
                import subprocess
                subprocess.Popen(['xdg-open' if sys.platform.startswith('linux') else 'open',
                                  str(target)])
        except Exception as e:
            QMessageBox.warning(self, "Couldn't open it",
                                f"{target}\n\n{e}")

    def _write_patch_file(self, map_path, plan, results, backup):
        try:
            patch_dir = self._patch_dir()
            patch_dir.mkdir(exist_ok=True)
            mission = Path(map_path).stem
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            grouped = {}
            for item in plan:
                grouped.setdefault(self._hp.hm.split_tag(item['tag'])[0], []).append(item)
            data = {"tool_version": VERSION, "map": map_path, "backup": backup,
                    "target_difficulty": self.target_difficulty,
                    # same code the results box shows, so a past patch can still be
                    # compared with a partner after the fact
                    "patch_code": self._hp.patch_signature(results, map_path,
                                                           self.target_difficulty),
                    "timestamp": ts, "groups": grouped, "results": results}
            out = patch_dir / f"patch_{mission}_{ts}.json"
            with open(out, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._last_patch_file = str(out)     # what "open patch log" reaches for
        except Exception:
            pass  # patch-log failure shouldn't block the actual patch


# The halo2.dll fixes worth exposing, grouped the way they have to be applied. The
# Arbiter camo fix is three edits that are meaningless apart: two stop him cloaking on
# his own (either alone does nothing, they are separate sites) and the third removes the
# difficulty-scaled 8s cap that was cutting the powerup to 4s on Legendary. The
# diagnostics in h2_dll_patch, and camo-no-difficulty-scale (the conservative
# alternative to the third edit), are deliberately not offered here.
H2_PATCH_SETS = [
    ("Arbiter camo fix (no native cloak, no 4s cap)",
     ['no-camo-grant', 'no-arbiter-camo', 'camo-duration-unlimited'],
     "Halo 2 Arbiter levels: the Arbiter cloaks on his own, which blocks the camo "
     "powerup entirely, and the engine cuts any cloak to 8s scaled by difficulty "
     "(4s on Legendary). This disables his native cloak and the cap, so the Camo "
     "ability behaves the same as on Chief levels."),
    ("Legendary co-op: no forced Iron",
     ['coop-no-forced-iron'],
     "Halo 2 ENFORCES the Iron skull on Legendary co-op -- it is not a skull you can "
     "turn off and not an option. This makes it behave like every other difficulty."),
]


def _h2_dll_patch():
    """The dll patcher, imported lazily so the Enhancer still starts on a machine
    without the Halo 2 toolkit."""
    import importlib
    import sys as _sys
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sprint_toolkit')
    if here not in _sys.path:
        _sys.path.insert(0, here)
    return importlib.import_module('h2_dll_patch')


class _OptPage:
    """Adapter so a page reads like a layout: addWidget puts the group above the
    trailing stretch (which otherwise has to be re-added after every insert), at the
    position its `order` asks for rather than wherever it happened to be built."""

    def __init__(self, layout, orders):
        self._layout = layout
        self._orders = orders

    def addWidget(self, w, order=100):
        i = 0
        while i < len(self._orders) and self._orders[i] <= order:
            i += 1
        self._orders.insert(i, order)
        self._layout.insertWidget(i, w)


class OptionsDialog(QDialog):
    """Edits the run options in OPTION_KEYS. Reads current values from CONFIG;
    values() returns the edited set. The caller persists them (global + per-run).

    Grouped onto pages reached from a list on the left. `_opt_page(name)` hands back
    the layout for a page, creating it (and its nav entry) on first use, so adding a
    group is one line at the point it is built. `order` places the group on that page
    independently of the order the groups happen to be BUILT in — build order follows
    widget dependencies, page order should follow what the reader expects.
    """

    def _sync_debug_only_options(self):
        """Show/hide the debug-only option rows to match the Debug checkbox.

        Only their VISIBILITY follows debug mode. Their values keep applying either
        way, so turning debug off cannot silently undo a rule the run depends on."""
        on = self.debug_mode_cb.isChecked()
        for w in getattr(self, '_debug_only_rows', ()):
            w.setVisible(on)
            lbl = w.parentWidget().layout().labelForField(w) if w.parentWidget() else None
            if lbl is not None:
                lbl.setVisible(on)

    def _opt_page(self, name):
        page = self._opt_pages.get(name)
        if page is None:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            cont = QWidget()
            page = QVBoxLayout(cont)
            page.addStretch(1)          # kept LAST; groups insert before it
            scroll.setWidget(cont)
            self._opt_pages[name] = page
            self._opt_stack.addWidget(scroll)
            self._opt_nav.addItem(name)
            if self._opt_nav.currentRow() < 0:
                self._opt_nav.setCurrentRow(0)
        return _OptPage(page, self._opt_order.setdefault(name, []))

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙ Options")
        self.setModal(True)
        self.setMinimumWidth(460)
        # Readable against the dark theme: light text, dark inputs, clear checks.
        self.setStyleSheet("""
            QDialog { background-color: #141414; }
            QLabel { color: #e0e0e0; font-size: 13px; }
            QCheckBox { color: #e0e0e0; font-size: 13px; spacing: 8px; }
            QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #4a4a4a;
                                   border-radius: 3px; background-color: #1a1a1a; }
            QCheckBox::indicator:checked { background-color: #4CAF50; border: 1px solid #4CAF50; }
            QComboBox, QDoubleSpinBox, QSpinBox, QLineEdit {
                background-color: #1a1a1a; color: #e0e0e0;
                border: 1px solid #3a3a3a; border-radius: 3px; padding: 4px 6px;
            }
            /* QLineEdit had no rule at all until the Folders group brought the first
               one into this dialog, so its text fell back to the palette default and
               came out near-black on the dark input. */
            QLineEdit:disabled { background-color: #131313; color: #5c5c5c;
                                 border: 1px solid #262626; }
            QPushButton { background-color: #2a2a2a; color: #e0e0e0;
                          border: 1px solid #3a3a3a; border-radius: 3px;
                          padding: 4px 10px; }
            QPushButton:hover { background-color: #343434; }
            QPushButton:disabled { background-color: #1a1a1a; color: #5c5c5c;
                                   border: 1px solid #262626; }
            QComboBox QAbstractItemView {
                background-color: #1a1a1a; color: #e0e0e0;
                selection-background-color: #2a5a2a;
            }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
            QSpinBox::up-button, QSpinBox::down-button { width: 16px; }
            QGroupBox { color: #e0e0e0; border: 1px solid #3a3a3a; border-radius: 5px;
                        margin-top: 10px; padding: 10px 6px 6px 6px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
            /* Disabled variants MUST live here, not only in the app stylesheet: a
               widget's own stylesheet wins over the application one for its children,
               so the enabled colours above would otherwise keep an inert row looking
               exactly like a live one. Every colour set above needs its counterpart. */
            QLabel:disabled, QCheckBox:disabled, QGroupBox:disabled { color: #5c5c5c; }
            QGroupBox::title:disabled { color: #5c5c5c; }
            QComboBox:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled {
                background-color: #131313; color: #5c5c5c; border: 1px solid #262626;
            }
            QCheckBox::indicator:disabled { border: 1px solid #333333;
                                            background-color: #141414; }
            QCheckBox::indicator:checked:disabled { background-color: #2f5b31;
                                                    border: 1px solid #2f5b31; }
        """)
        outer = QVBoxLayout(self)
        # #6: a category list on the left driving a stack on the right. The dialog had
        # grown to fourteen group boxes in one column, and finding anything meant
        # scrolling past everything. Each page scrolls on its own, so a long page (the
        # abilities) does not make the short ones scroll.
        split = QHBoxLayout()
        self._opt_nav = QListWidget()
        self._opt_nav.setFixedWidth(150)
        # An unselected row inherited the dialog-wide input colour, which is
        # near-black against this panel, so the category names were unreadable
        # until highlighted. Set the item colour explicitly.
        self._opt_nav.setStyleSheet(
            "QListWidget { background-color: #171717; border: 1px solid #2a2a2a; "
            "border-radius: 5px; padding: 4px; font-size: 13px; color: #e0e0e0; } "
            "QListWidget::item { padding: 7px 8px; border-radius: 4px; "
            "color: #e0e0e0; background-color: transparent; } "
            "QListWidget::item:selected { background-color: #3a4a6a; color: #ffffff; } "
            "QListWidget::item:hover:!selected { background-color: #232323; "
            "color: #ffffff; }")
        self._opt_stack = QStackedWidget()
        self._opt_pages = {}
        self._opt_order = {}
        self._opt_nav.currentRowChanged.connect(self._opt_stack.setCurrentIndex)
        split.addWidget(self._opt_nav)
        split.addWidget(self._opt_stack, 1)
        outer.addLayout(split, 1)

        # Pre-create the pages so the nav order is the designed one rather than
        # whichever group happens to be built first.
        for _name in ['Run rules', 'Loadout', 'Co-op', 'Abilities', 'Patching', 'Interface']:
            self._opt_page(_name)

        # ---- Map archive: first, because it is about protecting what everything
        # below it edits, and it is the one action here that touches nothing else ----
        # #3: the MCC and Assembly plugin folders live in the patcher dialog, where
        # they are only reachable once a run has effects to patch. They are plain
        # CONFIG keys, so the same two keys are edited here and the two views stay in
        # step by construction — no copy, no sync step, whichever one you set last wins.
        folders_g = QGroupBox("Folders")
        fform = QFormLayout(folders_g)
        fform.setLabelAlignment(Qt.AlignRight)

        def _folder_row(label, key, caption, tip, default=''):
            edit = QLineEdit(CONFIG.get(key) or default)
            edit.setToolTip(tip)
            btn = QPushButton("Browse…")
            btn.setMaximumWidth(90)
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(edit, 1)
            row.addWidget(btn)
            holder = QWidget()
            holder.setLayout(row)

            def pick(_=False):
                start = edit.text().strip() or str(app_data_dir())
                got = QFileDialog.getExistingDirectory(self, caption, start)
                if got:
                    edit.setText(got)
            btn.clicked.connect(pick)
            fform.addRow(label, holder)
            return edit

        self.mcc_root_edit = _folder_row(
            "MCC folder:", 'mcc_root',
            "Select the 'Halo The Master Chief Collection' folder",
            "Your 'Halo The Master Chief Collection' folder. Every map the patcher "
            "writes is resolved under here. The same setting as the patcher's MCC "
            "folder box — changing it in either place changes both.",
            default=mcc_root())
        self.plugins_dir_edit = _folder_row(
            "Assembly plugins:", 'assembly_plugins_dir',
            "Select Assembly plugins folder",
            "The Assembly/HCEEK Plugins folder holding the per-game tag definitions "
            "(Halo1MCC, Halo2MCC, Halo3MCC, ODSTMCC). Without it no field can be "
            "resolved and nothing patches. The same setting as the patcher's box.")
        self._opt_page("Patching").addWidget(folders_g, 10)

        vault_g = QGroupBox("Map archive")
        vform = QFormLayout(vault_g)
        vform.setLabelAlignment(Qt.AlignRight)
        self.vault_btn = QPushButton("Archive vanilla maps…")
        self.vault_btn.setToolTip(
            "Copy each game's PRISTINE campaign maps into one archive per game, in a "
            "folder you pick, so the originals live somewhere safe instead of as loose "
            ".bak copies. The map list comes from halo.json, so it covers exactly the "
            "maps the patcher touches. Nothing is deleted and nothing is overwritten.")
        self.vault_btn.clicked.connect(self._archive_vanilla_maps)
        vform.addRow("Originals:", self.vault_btn)

        # The two ways back, beside the way out. Both are stopgaps until map
        # availability is handled properly, and both spell out what they overwrite
        # before doing it \u2014 a restore is as destructive as the mod it undoes.
        self.restore_bak_btn = QPushButton("Restore all .bak\u2026")
        self.restore_bak_btn.setToolTip(
            "Copy every map\u2019s preserved copy back over the live map, for every game "
            "(Halo 2\u2019s live in a parallel _bak folder, and .vanilla.bak wins over .bak). "
            "Note a preserved copy is only as pristine as whatever wrote it last \u2014 after "
            "an Editing Kit rebuild it holds THAT build, not the shipped map.")
        self.restore_bak_btn.clicked.connect(self._restore_all_bak)
        vform.addRow("Restore .bak:", self.restore_bak_btn)

        self.restore_vault_btn = QPushButton("Restore from archive\u2026")
        self.restore_vault_btn.setToolTip(
            "Unpack the archives written above back over the live maps, checking every "
            "map against the archive\u2019s own hashes as it goes. This overwrites anything "
            "built and deployed since \u2014 ability plumbing, imported weapons, HUD edits.")
        self.restore_vault_btn.clicked.connect(self._restore_from_archive)
        vform.addRow("Restore archive:", self.restore_vault_btn)
        self._opt_page("Patching").addWidget(vault_g, 20)

        # ---- Run rules ----
        func = QGroupBox("Run rules")
        form = QFormLayout(func)
        form.setLabelAlignment(Qt.AlignRight)

        self.diff_combo = QComboBox()
        _fill_difficulty_combo(self.diff_combo, CONFIG.get('target_difficulty', 'Normal'))
        self.diff_combo.setToolTip("Which difficulty slot the patcher writes. Effects with per-difficulty "
                                   "fields (enemy damage, accuracy tiers, upgrade chances) are applied to "
                                   "this difficulty — set it to the one you actually play. (Heroic and "
                                   "Legendary are the game's Hard and Impossible slots.)")
        form.addRow("Target difficulty:", self.diff_combo)

        self.single_game_cb = QCheckBox("Remove mods that only appear in one game")
        self.single_game_cb.setChecked(bool(CONFIG.get('remove_single_game_mods')))
        self.single_game_cb.setToolTip("Only offer effects that work in every game, so a run can move "
                                       "between Halo 1/2/3 without cards becoming unpatchable. Also forces "
                                       "Boss mods off, since bosses are game-specific.")
        form.addRow("Cross-game only:", self.single_game_cb)

        self.no_vit_cards_cb = QCheckBox("Hide the cards Player Health/Shield replaced")
        self.no_vit_cards_cb.setChecked(bool(CONFIG.get('remove_superseded_vitality_cards')))
        self.no_vit_cards_cb.setToolTip(
            "Stop offering Starting Health Modifier, Starting Shield Modifier and "
            "Enemy Damage Reduction. The first two scale the scenario profile rather "
            "than the health pool itself, and Enemy Damage Reduction is a third way "
            "to say the same thing — with Player Health and Player Shield editing the "
            "pool directly they mostly muddy the draft. They still work; this only "
            "stops them being drawn.")
        form.addRow("Superseded cards:", self.no_vit_cards_cb)

        # ---- Difficulty baseline ----
        # These four live in `matg globals\globals` -> Difficulty and scale EVERY enemy
        # in the game, so they are the floor a run's own enemy cards then build on. They
        # are set before any effect runs, and because a patch always rebuilds from the
        # pristine .bak the baseline never compounds.
        base_g = QGroupBox("Difficulty baseline \u2014 whole-game enemy dials")
        bgrid = QGridLayout(base_g)
        bgrid.setHorizontalSpacing(10)
        note = QLabel("Set the value each dial STARTS at, before this run's enemy cards "
                      "are applied. 0 = leave the game's own value alone. The number in "
                      "brackets is what the game ships for the difficulty selected "
                      "above.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#9aa0a6; font-size:11px;")
        bgrid.addWidget(note, 0, 0, 1, 5)
        for c, (_key, title) in enumerate(BASELINE_COLS):
            h = QLabel(title)
            h.setStyleSheet("font-weight: bold;")
            h.setAlignment(Qt.AlignHCenter)
            bgrid.addWidget(h, 1, c + 1)

        self.baseline_spins = {}          # (game, key) -> QDoubleSpinBox
        self.baseline_vanilla = {}        # (game, key) -> QLabel
        saved = CONFIG.get('difficulty_baseline') or {}
        for r, game in enumerate(BASELINE_GAMES):
            lbl = QLabel(game)
            lbl.setToolTip(game)
            bgrid.addWidget(lbl, r + 2, 0)
            for c, (key, title) in enumerate(BASELINE_COLS):
                cell = QWidget()
                row = QHBoxLayout(cell)
                row.setContentsMargins(0, 0, 0, 0)
                row.setSpacing(4)
                sp = QDoubleSpinBox()
                sp.setRange(0.0, 20.0)
                sp.setSingleStep(0.05)
                sp.setDecimals(3)
                # 0 reads as "vanilla" rather than as a real zero -- a genuine 0 here
                # would mean enemies deal no damage / have no health, which is never
                # what an empty box should mean.
                sp.setSpecialValueText("vanilla")
                sp.setValue(float((saved.get(game) or {}).get(key) or 0.0))
                sp.setToolTip("%s \u2014 %s. 0 leaves the shipped value alone."
                              % (game, title))
                van = QLabel("")
                van.setStyleSheet("color:#8ab4f8; font-size:11px;")
                van.setMinimumWidth(46)
                row.addWidget(sp)
                row.addWidget(van)
                bgrid.addWidget(cell, r + 2, c + 1)
                self.baseline_spins[(game, key)] = sp
                self.baseline_vanilla[(game, key)] = van
        self._refresh_baseline_vanilla()
        self.diff_combo.currentIndexChanged.connect(
            lambda *_a: self._refresh_baseline_vanilla())
        self._opt_page("Run rules").addWidget(base_g)

        self._opt_page("Run rules").addWidget(func)

        # ---- Weapon (#4): sits right under the run rules ----
        weap_g = QGroupBox("Weapon")
        wform = QFormLayout(weap_g)
        wform.setLabelAlignment(Qt.AlignRight)

        self.negatives_cb = QCheckBox("Deliberate weapon picks carry a tied negative")
        self.negatives_cb.setChecked(bool(CONFIG.get('weapon_choice_negatives')))
        self.negatives_cb.setToolTip("When you deliberately choose a weapon, an enemy card is tied to that "
                                     "choice — taking what you want costs you something.")
        wform.addRow("Weapon-choice negatives:", self.negatives_cb)

        self.upgrade_inherit_cb = QCheckBox("Upgrade weapons use their base weapon's effects")
        self.upgrade_inherit_cb.setChecked(bool(CONFIG.get('upgrade_inherits_base', True)))
        self.upgrade_inherit_cb.setToolTip(
            "An upgrade weapon (Brute Plasma Rifle) is a marginal variant of its base "
            "(Plasma Rifle), so it inherits every upgrade the base gets: the base's "
            "cards patch the upgrade's tag too, and the upgrade stops offering its own "
            "near-duplicate effect cards. The upgrade is still offered as a WEAPON — "
            "only its effect cards go away.")
        wform.addRow("Upgrade inherits base:", self.upgrade_inherit_cb)

        self.swap_cards_cb = QCheckBox("Offer map weapon replacement as per-weapon cards")
        self.swap_cards_cb.setChecked(bool(CONFIG.get('weapon_swap_cards')))
        self.swap_cards_cb.setToolTip("Each weapon gains a “Map Presence” card whose magnitude is "
                                      "the percentage of the level's weapon placements replaced with "
                                      "it. Same mechanism as the patcher's swap sliders, so the "
                                      "sliders are hidden while this is on.")
        wform.addRow("Map replacement:", self.swap_cards_cb)

        self.zoom_ui_cb = QCheckBox("Add a scope overlay to scopeless weapons given a Zoom")
        self.zoom_ui_cb.setChecked(bool(CONFIG.get('zoom_ui_on_scopeless', True)))
        self.zoom_ui_cb.setToolTip("On patch: if a Zoom effect is applied to a weapon with no vanilla scope "
                                   "(e.g. Brute Shot, Sentinel Beam), copy a scope overlay from a scoped weapon "
                                   "on the map so the zoom shows a scope. Structurally grows the HUD tag.")
        wform.addRow("Scope UI:", self.zoom_ui_cb)

        self.turret_weapons_cb = QCheckBox("Turrets are weapons")
        self.turret_weapons_cb.setChecked(bool(CONFIG.get('turrets_are_weapons')))
        self.turret_weapons_cb.setToolTip(
            "Detached turrets -- machinegun turret, plasma cannon, missile pod, "
            "flamethrower -- are placed as VEHICLES, not weapon pickups, so they are "
            "never in a level's weapon list and can never be drawn. With this on, each "
            "level also offers the turrets it actually carries (18 levels do). Off by "
            "default: a turret is heavy and movement-penalised, so handing one out "
            "changes a level more than a normal draw does.")
        wform.addRow("Turrets:", self.turret_weapons_cb)
        self._opt_page("Loadout").addWidget(weap_g)

        # ---- Starting loadout (#5): sits right under Weapon ----
        load_g = QGroupBox("Starting loadout")
        lform = QFormLayout(load_g)
        lform.setLabelAlignment(Qt.AlignRight)

        self.starting_weapons_cb = QCheckBox("Set starting weapons from picks (scenario profiles 0 & 1)")
        self.starting_weapons_cb.setChecked(bool(CONFIG.get('set_starting_weapons')))
        self.starting_weapons_cb.setToolTip("On patch: The first weapon picked by each player is set as the starting\n"
                                            "weapon for every map IF the weapon is available on the map.\n"
                                            "Check out co-op settings for 2 player and get the rebuild maps to have all weapons on all maps.")
        lform.addRow("Starting weapons:", self.starting_weapons_cb)

        self.starting_equipment_cb = QCheckBox("Place first equipment per player at their spawn (Halo 3)")
        self.starting_equipment_cb.setChecked(bool(CONFIG.get('set_starting_equipment')))
        self.starting_equipment_cb.setToolTip(
            "Halo 3 only. Halo 3's starting profile has no equipment field, so a picked "
            "piece is granted by PLACING it near the player's starting location — you "
            "walk into it as the level loads. Player 1's first equipment goes at their "
            "start, player 2's at theirs; with 2-player coop off, both go to player 1. "
            "A NEW placement is added, so the level's own equipment is untouched. If the "
            "piece isn't in the level's palette it's added; only a piece the map never "
            "loads is skipped.\n\n"
            "Note: a few levels start you in a vehicle or mid-cinematic, so the drop uses "
            "a hand-picked reachable spot there instead of the raw spawn. And a piece the "
            "level only streams later (e.g. Auto Turret on some maps) can't appear at the "
            "start at all — it's placed on the nearest weapon in the first area where it "
            "does load, so you pick it up a little way in rather than underfoot.")
        lform.addRow("Starting equipment:", self.starting_equipment_cb)

        self.equipment_all_selected_cb = QCheckBox("Place every equipment each player carries, not just the first")
        self.equipment_all_selected_cb.setChecked(bool(CONFIG.get('equipment_all_selected')))
        self.equipment_all_selected_cb.setToolTip(
            "On: every piece of equipment a player has picked up is placed on their spawn. "
            "Off: only their first. Needs 'Starting equipment'.")

        # #5: all-carried is meaningless without starting equipment — gate it.
        def _sync_all_equip(_=False):
            on = self.starting_equipment_cb.isChecked()
            self.equipment_all_selected_cb.setEnabled(on)
            if not on:
                self.equipment_all_selected_cb.setChecked(False)
        self.starting_equipment_cb.toggled.connect(_sync_all_equip)
        _sync_all_equip()
        lform.addRow("    ↳ All carried equipment:", self.equipment_all_selected_cb)
        self._opt_page("Loadout").addWidget(load_g)

        # ---- Boss options (#2): "Add Boss card" is the master; with boss cards off
        # the other two have nothing to shape, so they grey out ----
        boss_g = QGroupBox("Boss options")
        bform = QFormLayout(boss_g)
        bform.setLabelAlignment(Qt.AlignRight)

        # #2: presented as a positive "add the Boss card" switch (on by default),
        # while the stored config stays remove_boss_mods (checked here == NOT removed).
        self.boss_cards_cb = QCheckBox("Add a Boss card on boss levels")
        self.boss_cards_cb.setToolTip("On (default): boss levels draw their guaranteed Boss card. Forced OFF "
                                      "while 'Remove mods that only appear in one game' is set, since bosses "
                                      "are game-specific. While this is off, the two options below do nothing "
                                      "— there are no boss cards to shape.")
        # The forced-off display state must not clobber the user's real preference, so
        # track it separately and restore it when single-game is turned off.
        self._user_boss_cards = not bool(CONFIG.get('remove_boss_mods'))
        bform.addRow("Boss cards:", self.boss_cards_cb)

        self.combine_holo_cb = QCheckBox("Combine Heretic Leader & his Holograms into one mod")
        self.combine_holo_cb.setChecked(bool(CONFIG.get('combine_heretic_hologram')))
        self.combine_holo_cb.setToolTip("On patch: Heretic Leader boss cards target the leader and his decoy "
                                        "holograms together, so one card tunes both.")
        bform.addRow("    ↳ Heretic bosses:", self.combine_holo_cb)

        # Heroes, then the per-hero switches ORDERED BY GAME in release order --
        # Halo 2, Halo 3, ODST, Reach -- the same order halo.json lists its games and
        # its "Hero enemy modifier" entries. An archetype that spans games is filed
        # under the one it first appears in.
        self.heroes_boss_cb = QCheckBox("Heroes are bosses")
        self.heroes_boss_cb.setChecked(bool(CONFIG.get('heroes_are_bosses', True)))
        self.heroes_boss_cb.setToolTip(
            "halo.json keeps two kinds of boss apart, and this switch controls the "
            "second kind.\n"
            "\u2022 Boss enemy modifier \u2014 the named one-off story fights: Prophet "
            "Regret, the Heretic Leader, Tartarus and 343 Guilty Spark. Always "
            "available; this switch does not touch them.\n"
            "\u2022 Hero enemy modifier \u2014 the recurring heavy archetypes that turn "
            "up across whole campaigns: Sentinel Enforcer, Brute Chieftain, Elite "
            "General, Elite Zealot, Grunt Ultra and Jackal Sniper.\n"
            "Turn this off and only the named story fights count as bosses. The "
            "per-hero switches below choose WHICH heroes; this one decides whether "
            "heroes count at all.")
        bform.addRow("    \u21b3 Heroes:", self.heroes_boss_cb)

        self.h2_enforcer_boss_cb = QCheckBox("Sentinel Enforcers count as heroes (Halo 2)")
        self.h2_enforcer_boss_cb.setChecked(
            bool(CONFIG.get('h2_sentinel_enforcer_bosses', True)))
        self.h2_enforcer_boss_cb.setToolTip(
            "Halo 2 only \u2014 Sacred Icon and Quarantine Zone. On by default, because "
            "halo.json used to declare the Enforcer as those missions' boss and this "
            "switch now replaces that.\n"
            "Filed as a hero by intent rather than by the census: the engine does not "
            "class it Hero at all (its character tag populates no metagame bucket and "
            "inherits one), but it is a recurring heavy rather than a named character.")
        bform.addRow("    \u21b3 H2 Enforcers:", self.h2_enforcer_boss_cb)

        self.h2_honor_boss_cb = QCheckBox("Honor Guard Elites count as heroes (Halo 2)")
        self.h2_honor_boss_cb.setChecked(bool(CONFIG.get('h2_honor_guard_bosses')))
        self.h2_honor_boss_cb.setToolTip(
            "Halo 2 only. Hero-class on Sacred Icon, Quarantine Zone, Gravemind and "
            "High Charity.\nNOTE: this variant defines no stats of its own \u2014 "
            "vitality, weapons, grenades and charge are all inherited from the base "
            "Elite \u2014 so there are no Honor-Guard-specific cards yet. The mission "
            "becomes a boss level and draws from the general pool.")
        bform.addRow("    \u21b3 H2 Honor Guards:", self.h2_honor_boss_cb)

        self.chieftain_boss_cb = QCheckBox(
            "Brute Chieftains count as heroes (Halo 3, ODST, Reach)")
        self.chieftain_boss_cb.setChecked(bool(CONFIG.get('brute_chieftain_bosses', True)))
        self.chieftain_boss_cb.setToolTip(
            "Chieftains are Hero-class in Halo 3, ODST and Reach alike \u2014 Halo 2's "
            "chieftain is Tartarus, who is a named boss instead. On by default, "
            "because halo.json used to declare them as mission bosses and this switch "
            "now replaces that.\n"
            "Halo 3: Sierra 117, Crow's Nest, Tsavo Highway, The Storm, The Ark, The "
            "Covenant.\n"
            "ODST: all nine missions \u2014 every one carries a Chieftain in its "
            "character palette, though only seven were ever declared.\n"
            "Reach: Exodus, The Pillar of Autumn, Lone Wolf.")
        bform.addRow("    \u21b3 Brute Chieftains:", self.chieftain_boss_cb)

        self.h3_specops_boss_cb = QCheckBox("Spec-Ops Commander counts as a hero (Halo 3)")
        self.h3_specops_boss_cb.setChecked(bool(CONFIG.get('h3_specops_bosses')))
        self.h3_specops_boss_cb.setToolTip(
            "Halo 3, Floodgate only. Hero-class \u2014 but in Halo 3 this Elite is an "
            "ALLY, so promoting him buffs your own side rather than the enemy.\n"
            "Ignored entirely while 'Elites are allies in Halo 3' is on, so the two "
            "options cannot contradict each other. Turn that off to use this.\n"
            "(Halo 2 has this character too, but classes it Leader, not Hero.)")
        bform.addRow("    \u21b3 H3 Spec-Ops:", self.h3_specops_boss_cb)

        self.odst_specops_boss_cb = QCheckBox("Spec-Ops Commanders count as heroes (ODST)")
        self.odst_specops_boss_cb.setChecked(bool(CONFIG.get('odst_specops_bosses')))
        self.odst_specops_boss_cb.setToolTip(
            "ODST only. Hero-class on eight of the nine missions, and a genuine enemy "
            "here unlike Halo 3's.\nSame caveat as the Halo 2 Honor Guard: it inherits "
            "every stat from elite_specops, so the mission becomes a boss level but "
            "there are no commander-specific cards until its values are inserted.")
        bform.addRow("    \u21b3 ODST Spec-Ops:", self.odst_specops_boss_cb)

        self.reach_elite_boss_cb = QCheckBox("Elite Generals and Zealots count as heroes (Reach)")
        self.reach_elite_boss_cb.setChecked(bool(CONFIG.get('reach_elite_bosses')))
        self.reach_elite_boss_cb.setToolTip(
            "Halo Reach only. Reach has no scripted boss fight, so this promotes its "
            "toughest named Elites.\n"
            "Elite General (90/175 body/shield on Normal, 130/245 on Legendary) on the "
            "eight missions that field one.\n"
            "Elite Zealot on The Pillar of Autumn, the one map whose Zealot "
            "(elite_story_unique) carries its own vitality. The plain story Elites on "
            "Winter Contingency and Tip of the Spear inherit their stats from "
            "elite_ultra, so tuning them would buff every Ultra in the level.")
        bform.addRow("    \u21b3 Reach Elites:", self.reach_elite_boss_cb)

        self.reach_grunt_boss_cb = QCheckBox("Grunt Ultras count as heroes (Reach)")
        self.reach_grunt_boss_cb.setChecked(bool(CONFIG.get('reach_grunt_ultra_bosses')))
        self.reach_grunt_boss_cb.setToolTip(
            "Halo Reach only. The Grunt Ultra is Reach's only shielded Grunt (60/50 "
            "body/shield on Normal, 90/50 on Legendary) and defines its own vitality, "
            "so it can carry hero cards.\n"
            "Three missions: Winter Contingency, Tip of the Spear, Long Night of "
            "Solace. Exodus carries the Ultra in its palette but no squad spawns it.\n"
            "(Halo 2 classes this character Specialist and Halo 3/ODST leave it "
            "inheriting, so it is Hero in Reach only.)")
        bform.addRow("    \u21b3 Reach Grunt Ultras:", self.reach_grunt_boss_cb)

        self.reach_jackal_boss_cb = QCheckBox("Sniper Jackals count as heroes (Reach)")
        self.reach_jackal_boss_cb.setChecked(bool(CONFIG.get('reach_jackal_sniper_bosses')))
        self.reach_jackal_boss_cb.setToolTip(
            "Halo Reach only. The sniper Jackal is Hero-class and, unusually for a "
            "variant, carries its own vitality (60 body on Normal, 90 on Legendary \u2014 "
            "triple a plain Jackal, and it has no shield gauntlet), so its cards "
            "really bite.\nNine missions: everything except Winter Contingency.\n"
            "(Halo 2, Halo 3 and ODST all class this character Specialist, so it is "
            "Hero in Reach only.)")
        bform.addRow("    \u21b3 Reach sniper Jackals:", self.reach_jackal_boss_cb)

        # Boss cards ON is the prerequisite for the other boss options; with them off
        # there is nothing to shape, so grey the children out. single_game forces boss
        # cards off (and locks the switch), which must also disable the children — so
        # children sync from the switch's effective state, done explicitly because the
        # forced change is signal-blocked.
        def _sync_boss_children(_=False):
            on = self.boss_cards_cb.isChecked()
            for cb in (self.combine_holo_cb, self.heroes_boss_cb):
                cb.setEnabled(on)
                if not on:
                    cb.setChecked(False)
            _sync_hero_children()

        # The per-hero switches are children of "Heroes are bosses", not of boss cards
        # directly: with heroes off, picking WHICH heroes is meaningless. Unchecking
        # them on the way down is deliberate, so a hidden switch can't come back on.
        def _sync_hero_children(_=False):
            on = self.boss_cards_cb.isChecked() and self.heroes_boss_cb.isChecked()
            for cb in (self.h2_enforcer_boss_cb, self.h2_honor_boss_cb,
                       self.chieftain_boss_cb, self.h3_specops_boss_cb,
                       self.odst_specops_boss_cb, self.reach_elite_boss_cb,
                       self.reach_grunt_boss_cb, self.reach_jackal_boss_cb):
                cb.setEnabled(on)
                if not on:
                    cb.setChecked(False)
        self.heroes_boss_cb.toggled.connect(_sync_hero_children)
        def _sync_boss_sub():
            forced_off = self.single_game_cb.isChecked()
            self.boss_cards_cb.blockSignals(True)
            self.boss_cards_cb.setChecked(False if forced_off else self._user_boss_cards)
            self.boss_cards_cb.setEnabled(not forced_off)
            self.boss_cards_cb.blockSignals(False)
            _sync_boss_children()
        def _on_boss_toggled(checked):
            if self.boss_cards_cb.isEnabled():   # ignore programmatic (forced) changes
                self._user_boss_cards = checked
            _sync_boss_children()
        self.boss_cards_cb.toggled.connect(_on_boss_toggled)
        self.single_game_cb.toggled.connect(lambda _=False: _sync_boss_sub())
        _sync_boss_sub()
        self._opt_page("Run rules").addWidget(boss_g)

        # ---- Equipment (#3): grenades, then equipment rolls, then denials ----
        equip_g = QGroupBox("Equipment")
        eform = QFormLayout(equip_g)
        eform.setLabelAlignment(Qt.AlignRight)

        self.grenades_cb = QCheckBox("Treat grenades as weapons")
        self.grenades_cb.setChecked(bool(CONFIG.get('include_grenades')))
        self.grenades_cb.setToolTip("Let grenades be offered as weapon picks (and carry weapon effects). "
                                    "They are never used as a starting Primary/Secondary weapon.")
        eform.addRow("Grenades:", self.grenades_cb)

        self.grenades_need_weapon_cb = QCheckBox("…only once the player holds a real weapon")
        self.grenades_need_weapon_cb.setChecked(bool(CONFIG.get('grenades_need_weapon')))
        self.grenades_need_weapon_cb.setToolTip("Keeps a grenade from being the first thing a player "
                                                "picks up, which would leave them with no actual gun. "
                                                "Only available while grenades count as weapons.")

        def _sync_grenade_sub(_=False):
            on = self.grenades_cb.isChecked()
            self.grenades_need_weapon_cb.setEnabled(on)
            if not on:
                self.grenades_need_weapon_cb.setChecked(False)
        self.grenades_cb.toggled.connect(_sync_grenade_sub)
        _sync_grenade_sub()
        eform.addRow("    ↳ Grenades need a gun:", self.grenades_need_weapon_cb)

        self.equipment_rolls_cb = QCheckBox("Equipment can turn up in New Weapon draws (Halo 3, ODST, Reach)")
        self.equipment_rolls_cb.setChecked(bool(CONFIG.get('h3_equipment_in_rolls')))
        self.equipment_rolls_cb.setToolTip("Bubble Shield, Regenerator and the rest of "
                                           "the level's equipment can be drawn by the New Weapon button, "
                                           "same as an actual weapon. In Reach this is the six armour "
                                           "abilities instead, which DO carry mods of their own -- energy "
                                           "drain, recharge, and each ability's own dials.")
        eform.addRow("Equipment in rolls:", self.equipment_rolls_cb)

        self.equipment_need_weapon_cb = QCheckBox("…only once the player holds a real weapon")
        self.equipment_need_weapon_cb.setChecked(bool(CONFIG.get('equipment_need_weapon')))
        self.equipment_need_weapon_cb.setToolTip("Keeps equipment from being the first thing a "
                                                 "player picks up, which would leave them with no "
                                                 "actual gun. Only available while equipment is in "
                                                 "the rolls.")

        def _sync_equip_sub(_=False):
            on = self.equipment_rolls_cb.isChecked()
            self.equipment_need_weapon_cb.setEnabled(on)
            if not on:
                self.equipment_need_weapon_cb.setChecked(False)
        self.equipment_rolls_cb.toggled.connect(_sync_equip_sub)
        _sync_equip_sub()
        eform.addRow("    ↳ Equipment needs a gun:", self.equipment_need_weapon_cb)

        self.no_flare_jammer_cb = QCheckBox("Deny the player Superflare and Jammer")
        self.no_flare_jammer_cb.setChecked(bool(CONFIG.get('remove_superflare_jammer')))
        self.no_flare_jammer_cb.setToolTip("Halo 3: never offer Superflare or Jammer to the "
                                           "player. Brutes still carry and use them.")
        eform.addRow("Deny flare/jammer:", self.no_flare_jammer_cb)

        self.no_invinc_invis_cb = QCheckBox("Deny the player Invincibility and Invisibility")
        self.no_invinc_invis_cb.setChecked(bool(CONFIG.get('remove_invincibility_invisibility')))
        self.no_invinc_invis_cb.setToolTip("Halo 3: never offer Invincibility or Invisibility "
                                           "to the player. Brutes still carry and use them.")
        eform.addRow("Deny invinc/invis:", self.no_invinc_invis_cb)

        self.denied_as_enemy_cb = QCheckBox("…offer the denied ones as enemy modifiers instead")
        self.denied_as_enemy_cb.setChecked(bool(CONFIG.get('denied_equipment_as_enemy_mods')))
        self.denied_as_enemy_cb.setToolTip("Equipment the player is denied becomes an enemy card "
                                           "instead, since Brutes are the only characters that "
                                           "carry equipment. Only on missions where a Brute that "
                                           "actually carries it spawns — Jammer and Invisibility "
                                           "ride on brute_stalker, so they only reach The Ark and "
                                           "The Covenant.")

        def _sync_denied_sub(_=False):
            on = self.no_flare_jammer_cb.isChecked() or self.no_invinc_invis_cb.isChecked()
            self.denied_as_enemy_cb.setEnabled(on)
            if not on:
                self.denied_as_enemy_cb.setChecked(False)
        self.no_flare_jammer_cb.toggled.connect(_sync_denied_sub)
        self.no_invinc_invis_cb.toggled.connect(_sync_denied_sub)
        _sync_denied_sub()
        eform.addRow("    ↳ Denied → enemies:", self.denied_as_enemy_cb)
        self._opt_page("Loadout").addWidget(equip_g)

        # ---- Coop (#6) ----
        # A form row is only obviously inert if its LABEL greys out too — Qt disables the
        # field alone, which leaves the caption at full contrast and the row still looking
        # editable. Use this everywhere a row is conditionally enabled.
        def _row(form, widget, on):
            widget.setEnabled(on)
            lab = form.labelForField(widget)
            if lab is not None:
                lab.setEnabled(on)

        coop_g = QGroupBox("Coop")
        cform = QFormLayout(coop_g)
        cform.setLabelAlignment(Qt.AlignRight)

        self.two_player_cb = QCheckBox("2-player coop: P1 plays Chief, P2 the Dervish (Halo 3)")
        self.two_player_cb.setChecked(bool(CONFIG.get('two_player_coop', True)))
        self.two_player_cb.setToolTip("On by default, and only does anything in Halo 3, which has two "
                                      "playable characters. On: P1's first weapon is given to every "
                                      "Chief profile and P2's to every Dervish profile, and the two "
                                      "options below act on the respawn profiles. Off: both picks "
                                      "go on profile 0 as Primary/Secondary, like Halo 1 and 2.")
        cform.addRow("2-player coop:", self.two_player_cb)

        # Rename per #6: these act on the profiles the player RESPAWNS with in coop.
        # H1/H2: the coop starting-profile (index 1). H3 has many more profiles, so
        # which are start-of-map vs respawn still needs verifying in-game — see the
        # note handed back to the user.
        self.coop_no_start_cb = QCheckBox("Keep coop respawn weapons vanilla")
        self.coop_no_start_cb.setChecked(bool(CONFIG.get('coop_no_starting_weapons')))
        self.coop_no_start_cb.setToolTip("Don't change the weapons you respawn with in coop play — keeps them "
                                         "vanilla. The picked starting weapons still apply to player 1's "
                                         "start-of-map loadout.")
        cform.addRow("Vanilla respawn weapons:", self.coop_no_start_cb)

        self.coop_null_cb = QCheckBox("Empty the coop respawn weapons (null)")
        self.coop_null_cb.setChecked(bool(CONFIG.get('null_coop_starting_equipment')))
        self.coop_null_cb.setToolTip("Clear the coop respawn profile's Primary and Secondary weapons so the "
                                     "coop player respawns empty-handed. Mutually exclusive with keeping them "
                                     "vanilla.")
        cform.addRow("Empty respawn weapons:", self.coop_null_cb)
        # Conflicting intents for the same profile — keep exactly one active.
        self.coop_no_start_cb.toggled.connect(
            lambda on: on and self.coop_null_cb.setChecked(False))
        self.coop_null_cb.toggled.connect(
            lambda on: on and self.coop_no_start_cb.setChecked(False))

        self.h2_respawn_cb = QCheckBox("Add a respawn profile where Halo 2 lacks one")
        self.h2_respawn_cb.setChecked(bool(CONFIG.get('h2_add_respawn_profile', True)))
        self.h2_respawn_cb.setToolTip(
            "Halo 2 gives each level two Player Starting Profiles — one for the initial "
            "spawn, one for respawning — except The Great Journey (08b), which ships only "
            "one, so there is nothing there for the patcher to put your respawn weapons "
            "in. This adds the missing profile as a copy of the first. It restructures "
            "the map (the profile block is relocated), which is why it can be turned "
            "off; levels that already have a respawn profile are left alone.")
        self.swap_players_cb = QCheckBox("Swap player 1 and player 2 loadouts")
        self.swap_players_cb.setChecked(bool(CONFIG.get('swap_player_loadouts')))
        self.swap_players_cb.setToolTip(
            "Write player 1’s weapons, equipment and ability where player 2’s would "
            "go, and vice versa. Affects only what is patched into the map — the run, "
            "the cards and the history still read the way they were drafted. Use it "
            "when the seat and the draft ended up the wrong way round.")
        cform.addRow("Swap players:", self.swap_players_cb)
        cform.addRow("Halo 2 respawn profile:", self.h2_respawn_cb)

        # Tartarus (08b) test knob. Johnson’s Sentinel Beam is REAL damage —
        # Tartarus is unit_impervious 0 once the fight starts and only takes damage
        # from the player’s team, which Johnson is on — and the speedrun tech is to
        # duplicate him so the shield crosses the script’s threshold sooner.
        self.h2_johnson_spin = QSpinBox()
        self.h2_johnson_spin.setRange(0, 8)
        self.h2_johnson_spin.setValue(int(((CONFIG.get('h2_extra_squads') or {})
                                           .get('08b') or {}).get('boss_johnson', 0) or 0))
        self.h2_johnson_spin.setToolTip(
            "Extra Johnsons in the Tartarus fight on The Great Journey (08b). His "
            "Sentinel Beam does real damage to Tartarus, and the boss script opens "
            "the damage window once his shield is chipped past a fixed fraction — so "
            "more Johnsons means the window opens sooner and more often. 0 leaves the "
            "level alone. This restructures the map (the squad’s starting-location "
            "block is grown), and only affects 08b.")
        cform.addRow("Extra Johnsons (08b):", self.h2_johnson_spin)

        # #6: the respawn options only mean anything when starting weapons are being
        # set at all — grey them out otherwise.
        def _sync_coop_respawn(_=False):
            on = self.starting_weapons_cb.isChecked()
            for cb in (self.coop_no_start_cb, self.coop_null_cb):
                _row(cform, cb, on)
                if not on:
                    cb.setChecked(False)
        self.starting_weapons_cb.toggled.connect(_sync_coop_respawn)
        _sync_coop_respawn()
        self._opt_page("Co-op").addWidget(coop_g)

        # ---- Coop session sharing ----
        # One machine drafts and patches; the other needs the same run AND the same
        # magnitudes. Run files now carry their own magnitudes, so pointing both
        # machines at one synced folder turns the handover into a single click.
        share_g = QGroupBox("Coop session sharing")
        shform = QFormLayout(share_g)
        shform.setLabelAlignment(Qt.AlignRight)

        share_row = QWidget()
        share_h = QHBoxLayout(share_row)
        share_h.setContentsMargins(0, 0, 0, 0)
        self.share_dir_edit = QLineEdit(CONFIG.get('shared_session_dir', '') or '')
        self.share_dir_edit.setPlaceholderText("e.g. a Dropbox / OneDrive / Drive folder "
                                               "both players sync")
        share_browse = QPushButton("Browse…")
        share_browse.setMaximumWidth(90)

        def _browse_share():
            start = self.share_dir_edit.text().strip() or str(app_data_dir())
            p = QFileDialog.getExistingDirectory(self, "Select the shared session folder",
                                                 start)
            if p:
                self.share_dir_edit.setText(p)
        share_browse.clicked.connect(_browse_share)
        share_h.addWidget(self.share_dir_edit)
        share_h.addWidget(share_browse)
        share_row.setToolTip("A folder both machines can see. Runs written here carry the "
                             "magnitudes typed for them, so the other machine reproduces "
                             "the same patch — no second file to copy. Leave empty to keep "
                             "sharing files by hand.")
        shform.addRow("Shared folder:", share_row)

        self.share_autosave_cb = QCheckBox("Write the run there after every patch")
        self.share_autosave_cb.setChecked(bool(CONFIG.get('shared_session_autosave', True)))
        self.share_autosave_cb.setToolTip("After a successful patch, drop this run into the "
                                          "shared folder automatically. The other machine "
                                          "picks it up with “Load Latest Shared Session”.")
        shform.addRow("    ↳ Auto-share:", self.share_autosave_cb)

        def _sync_share(_=False):
            on = bool(self.share_dir_edit.text().strip())
            _row(shform, self.share_autosave_cb, on)
        self.share_dir_edit.textChanged.connect(_sync_share)
        _sync_share()
        self._opt_page("Co-op").addWidget(share_g)

        # ---- New Features (Experimental) ----
        # Sprint. Only functions on maps built with the sprint mod (weapon tag +
        # global_scripts sprint.hsc); on a vanilla map these settings no-op. The
        # patcher tunes it live: speed via matg/weapon fields, cooldown/duration via
        # the sprint_ticks/sprint_cooldown script globals, and on/off via the
        # sprint_enabled global. Offered in every game lacking inherent sprint.
        exp_g = QGroupBox("New Features (Experimental)")
        xform = QFormLayout(exp_g)
        xform.setLabelAlignment(Qt.AlignRight)

        self.sprint_cb = QCheckBox("Enable Abilities")
        self.sprint_cb.setChecked(bool(CONFIG.get('sprint_feature')))
        self.sprint_cb.setToolTip("Flashlight-key abilities — Sprint, Overshield, Regeneration and "
                                  "Camo — for games that never shipped with them. Requires maps built "
                                  "with the ability mod; on a plain map these options do nothing.")
        xform.addRow("Abilities:", self.sprint_cb)

        self.sprint_start_cb = QCheckBox("Start with an ability")
        self.sprint_start_cb.setChecked(bool(CONFIG.get('sprint_start_with', True)))
        self.sprint_start_cb.setToolTip("Both players have the chosen ability from the first map. Turn "
                                        "off to draft abilities in the weapon selection instead.")
        xform.addRow("    ↳ From the start:", self.sprint_start_cb)

        self.ability_start_combo = QComboBox()
        for _ab, _label in (('sprint', 'Sprint'), ('overshield', 'Overshield'),
                            ('regeneration', 'Regeneration'), ('camo', 'Camo')):
            self.ability_start_combo.addItem(_label, _ab)
        self.ability_start_combo.setCurrentIndex(
            max(0, self.ability_start_combo.findData(
                CONFIG.get('ability_start_which', 'sprint'))))
        tune_combo(self.ability_start_combo)
        self.ability_start_combo.setToolTip("Which ability both players get when starting with "
                                            "one, instead of drafting it.")
        xform.addRow("        ↳ Which ability:", self.ability_start_combo)

        self.sprint_cards_cb = QCheckBox("Offer abilities in the weapon selection")
        self.sprint_cards_cb.setChecked(bool(CONFIG.get('sprint_as_card')))
        self.sprint_cards_cb.setToolTip("Instead of starting with one, abilities turn up as picks in the "
                                        "weapon selection (initial pick and the New Weapon button), like "
                                        "Halo 3 equipment. A player's ability switches on once they take "
                                        "it, and each player ends up with at most one.")
        xform.addRow("    ↳ As a pick:", self.sprint_cards_cb)

        self.sprint_need_weapon_cb = QCheckBox("…only once the player holds a real weapon")
        self.sprint_need_weapon_cb.setChecked(bool(CONFIG.get('sprint_need_weapon')))
        self.sprint_need_weapon_cb.setToolTip("Keeps Sprint out of the initial pick (when no gun is held "
                                              "yet) — it only appears via the New Weapon button once the "
                                              "player already has a real weapon. Only applies while Sprint "
                                              "is offered as a pick.")
        xform.addRow("        ↳ Needs a gun:", self.sprint_need_weapon_cb)

        def _ability_checkbox_row(selected, tip):
            """A row of one checkbox per ability, returned with its {ability: box} map."""
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            boxes = {}
            for ab, label in (('sprint', 'Sprint'), ('overshield', 'Overshield'),
                              ('regeneration', 'Regeneration'), ('camo', 'Camo')):
                cb = QCheckBox(label)
                cb.setChecked(ab in selected)
                boxes[ab] = cb
                h.addWidget(cb)
            h.addStretch(1)
            row.setToolTip(tip)
            return row, boxes

        offer_row, self.ability_offer_cbs = _ability_checkbox_row(
            set(CONFIG.get('abilities_offered') or ['sprint']),
            "Which abilities can turn up in the weapon selection. Each player ends up with "
            "at most one.")
        xform.addRow("        ↳ Offer:", offer_row)

        cards_row, self.ability_cards_cbs = _ability_checkbox_row(
            set(ability_cards_for()),
            "Draftable player cards that tune an ability for the run — each stacking onto "
            "the base values below. A card is only offered to a player who has that ability.")
        xform.addRow("    ↳ Offer cards for:", cards_row)

        # Per-ability starting values, one subsection each. Disabling a box greys the
        # whole group (title included), so it's obvious which tuning is in play.
        def _ability_box(title):
            box = QGroupBox(title)
            form = QFormLayout(box)
            form.setLabelAlignment(Qt.AlignRight)
            return box, form

        self.sprint_box, sform = _ability_box("Sprint")
        self.sprint_speed = QSpinBox()
        self.sprint_speed.setRange(105, 300)
        self.sprint_speed.setSingleStep(5)
        self.sprint_speed.setSuffix("%")
        self.sprint_speed.setValue(int(CONFIG.get('sprint_speed_pct', 150)))
        self.sprint_speed.setToolTip("Sprint speed as a percentage of normal run speed. 150% matches the "
                                     "reference mod. Normal movement is unaffected — only sprinting scales.")
        sform.addRow("Speed:", self.sprint_speed)

        self.sprint_duration = QDoubleSpinBox()
        self.sprint_duration.setRange(0.5, 30.0)
        self.sprint_duration.setSingleStep(0.5)
        self.sprint_duration.setDecimals(1)
        self.sprint_duration.setSuffix(" s")
        self.sprint_duration.setValue(float(CONFIG.get('sprint_duration_s', 3.0)))
        self.sprint_duration.setToolTip("How long a single sprint lasts before it auto-ends.")
        sform.addRow("Duration:", self.sprint_duration)

        self.sprint_cooldown = QDoubleSpinBox()
        self.sprint_cooldown.setRange(0.0, 30.0)
        self.sprint_cooldown.setSingleStep(0.5)
        self.sprint_cooldown.setDecimals(1)
        self.sprint_cooldown.setSuffix(" s")
        self.sprint_cooldown.setValue(float(CONFIG.get('sprint_cooldown_s', 2.0)))
        self.sprint_cooldown.setToolTip("Delay after a sprint ends before you can sprint again.")
        sform.addRow("Cooldown:", self.sprint_cooldown)
        xform.addRow(self.sprint_box)

        self.overshield_box, oform = _ability_box("Overshield")
        self.overshield_mult = QDoubleSpinBox()
        self.overshield_mult.setRange(1.0, 10.0)
        self.overshield_mult.setSingleStep(0.5)
        self.overshield_mult.setDecimals(2)
        self.overshield_mult.setPrefix("x")
        self.overshield_mult.setValue(float(CONFIG.get('overshield_mult', 3.0)))
        self.overshield_mult.setToolTip("Overshield strength as a multiple of a normal full "
                                        "shield. 3x is the vanilla powerup; it is applied "
                                        "outright, replacing whatever shield you had.")
        oform.addRow("Strength:", self.overshield_mult)
        xform.addRow(self.overshield_box)

        self.regen_box, rform = _ability_box("Regeneration")
        self.regen_percent = QDoubleSpinBox()
        self.regen_percent.setRange(1.0, 400.0)
        self.regen_percent.setSingleStep(10.0)
        self.regen_percent.setDecimals(0)
        self.regen_percent.setSuffix("%")
        self.regen_percent.setValue(float(CONFIG.get('regen_percent', 100.0)))
        self.regen_percent.setToolTip("How much health one use restores, as a percentage of "
                                      "max. Over 100% is allowed and simply heals past what a "
                                      "full bar is worth.")
        rform.addRow("Amount:", self.regen_percent)

        self.regen_duration = QDoubleSpinBox()
        self.regen_duration.setRange(0.1, 30.0)
        self.regen_duration.setSingleStep(0.5)
        self.regen_duration.setDecimals(1)
        self.regen_duration.setSuffix(" s")
        self.regen_duration.setValue(float(CONFIG.get('regen_duration_s', 5.0)))
        self.regen_duration.setToolTip("How long that heal is spread over. Short is a snap heal; "
                                       "long is a slow regeneration that damage can out-pace.")
        rform.addRow("Spread over:", self.regen_duration)

        # Feedback pulse. Halo 2 has no health bar at all, so without this the ability
        # gives the player nothing to go on; H1 has a bar but the pulse still reads
        # better, and in co-op it is the only way to see a partner regenerating. The
        # rate is per game because the effects differ (different tag sets entirely) and
        # so does how dense they look: H1's cyborg shimmer wants ~10 ticks, H2's
        # teleport ~45. The effect ids themselves live in halo_patch.
        self.regen_fx_every = {}
        _fx_cfg = CONFIG.get('regen_fx_every', {})
        if not isinstance(_fx_cfg, dict):
            _fx_cfg = {}
        for _g, _default in (('Halo 1', 10), ('Halo 2', 45)):
            box = QSpinBox()
            box.setRange(1, 120)
            box.setSingleStep(5)
            box.setSuffix(" ticks")
            box.setValue(int(_fx_cfg.get(_g, _default)))
            box.setToolTip("How often the regeneration effect flashes in %s, in ticks "
                           "(30 = once a second). Lower is a denser pulse." % _g)
            self.regen_fx_every[_g] = box
            rform.addRow("Effect every (%s):" % _g, box)
        xform.addRow(self.regen_box)

        self.camo_box, cform2 = _ability_box("Camo")
        self.camo_duration = QDoubleSpinBox()
        self.camo_duration.setRange(0.5, 60.0)
        self.camo_duration.setSingleStep(1.0)
        self.camo_duration.setDecimals(1)
        self.camo_duration.setSuffix(" s")
        self.camo_duration.setValue(float(CONFIG.get('camo_duration_s', 5.0)))
        self.camo_duration.setToolTip("How long invisibility lasts (the camo powerup's own "
                                      "duration; vanilla pickups are 45s). NOTE: this also "
                                      "changes any camo pickups placed in the level.")
        cform2.addRow("Duration:", self.camo_duration)

        self.camo_cooldown = QDoubleSpinBox()
        self.camo_cooldown.setRange(0.0, 120.0)
        self.camo_cooldown.setSingleStep(5.0)
        self.camo_cooldown.setDecimals(1)
        self.camo_cooldown.setSuffix(" s")
        self.camo_cooldown.setValue(float(CONFIG.get('camo_cooldown_s', 30.0)))
        self.camo_cooldown.setToolTip("Delay before camo can be used again. It starts when the "
                                      "camo runs out, so a full cycle is duration + cooldown.")
        cform2.addRow("Cooldown:", self.camo_cooldown)
        xform.addRow(self.camo_box)

        self.sprint_apply_btn = QPushButton("Apply abilities to maps…")
        self.sprint_apply_btn.setToolTip("Write the settings above into every Halo 1 map built with the "
                                         "ability mod, turning the start-with ability on for both players. "
                                         "Maps built without it are skipped. Byte-patched — no rebuild.")
        self.sprint_apply_btn.clicked.connect(self._apply_sprint_to_maps)
        xform.addRow("", self.sprint_apply_btn)


        # Start-with and card are two ways in; starting with sprint makes the card moot.
        self.sprint_start_cb.toggled.connect(
            lambda on: on and self.sprint_cards_cb.setChecked(False))
        self.sprint_cards_cb.toggled.connect(
            lambda on: on and self.sprint_start_cb.setChecked(False))

        def _sync_sprint(_=False):
            on = self.sprint_cb.isChecked()
            card = on and self.sprint_cards_cb.isChecked()
            start = on and self.sprint_start_cb.isChecked()
            _row(xform, self.sprint_start_cb, on)
            _row(xform, self.sprint_cards_cb, on)
            _row(xform, self.sprint_apply_btn, on)
            _row(xform, cards_row, on)
            # "Needs a gun" and the offer list only matter when abilities are drafted;
            # the start-with pick only matters the other way round.
            _row(xform, self.sprint_need_weapon_cb, card)
            if not card:
                self.sprint_need_weapon_cb.setChecked(False)
            _row(xform, offer_row, card)
            _row(xform, self.ability_start_combo, start)
            # Enabling abilities is the gate for their starting values: you set them up
            # before deciding how an ability enters the run, so they stay editable
            # whichever way in is chosen (and even before one is).
            for box in (self.sprint_box, self.overshield_box,
                        self.regen_box, self.camo_box):
                box.setEnabled(on)
        self.sprint_cb.toggled.connect(_sync_sprint)
        self.sprint_cards_cb.toggled.connect(_sync_sprint)
        self.sprint_start_cb.toggled.connect(_sync_sprint)
        self.ability_start_combo.currentIndexChanged.connect(_sync_sprint)
        for _cb in self.ability_offer_cbs.values():
            _cb.toggled.connect(_sync_sprint)
        _sync_sprint()
        self._opt_page("Abilities").addWidget(exp_g)

        # ---- Card rolls ----
        rolls = QGroupBox("Card rolls")
        rform = QFormLayout(rolls)
        rform.setLabelAlignment(Qt.AlignRight)

        # --- The OTHER slot -----------------------------------------------------
        # One card, four kinds. The old per-kind chances are gone: they were rolled
        # independently, so changing one silently changed how often a pair had a third
        # card at all, and a boss level suppressed the slot entirely.
        self.other_chance = QDoubleSpinBox()
        self.other_chance.setRange(0.0, 1.0)
        self.other_chance.setSingleStep(0.05)
        self.other_chance.setDecimals(2)
        self.other_chance.setValue(float(CONFIG.get('other_chance', 0.35)))
        self.other_chance.setToolTip(
            "Per-pair chance of an OTHER card — the fourth slot, alongside Player, "
            "Enemy and Boss. Which of the four kinds it is comes from the weights "
            "below.\n\n0 turns the whole slot off. This is now independent of the Boss "
            "slot: a level with a story boss still rolls Others.")
        rform.addRow("Other-card chance:", self.other_chance)

        # Relative weights, not probabilities: a kind that is off or has nothing left
        # to give drops out and the rest share its share.
        self.other_weight_boxes = {}
        _KINDS = (
            ('hero', 'Hero', "Recurring archetypes — Brute Chieftains, Sentinel "
                             "Enforcers, Elite Zealots. Split off the Boss slot, which "
                             "is now only named story fights."),
            ('exhaust', 'Exhaust', "A one-map negative. Picking one earns a "
                                   "no-negative choice next round."),
            ('skull', 'Skull', "A whole-map rule (Betrayal, Eyepatch) rather than a tag "
                               "tweak. Lasts the REST OF THE RUN once taken, and is "
                               "never offered twice."),
            ('ally', 'Ally', "Friend modifiers and anything flagged as a wildcard. "
                             "Called Wildcard before."),
        )
        # Two columns: four kinds in one vertical list pushed the rest of the page down
        # for no reason. Left column is the first two, right column the last two.
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        for i, (key, label, tip) in enumerate(_KINDS):
            cb = QCheckBox(label)
            cb.setChecked(bool(CONFIG.get('other_%s_enabled' % key, True)))
            cb.setToolTip("Offer %s cards at all." % label)
            sp = QDoubleSpinBox()
            sp.setRange(0.0, 20.0)
            sp.setSingleStep(0.5)
            sp.setDecimals(1)
            sp.setValue(float((CONFIG.get('other_weights') or {}).get(key, 1.0)))
            sp.setToolTip(tip + "\n\nRelative weight against the other kinds, not a "
                                "probability.")
            sp.setMaximumWidth(80)
            cb.toggled.connect(sp.setEnabled)
            sp.setEnabled(cb.isChecked())
            row, col = i % 2, (i // 2) * 2
            grid.addWidget(cb, row, col)
            grid.addWidget(sp, row, col + 1)
            self.other_weight_boxes[key] = (cb, sp)
        grid.setColumnStretch(4, 1)
        _gw = QWidget()
        _gw.setLayout(grid)
        rform.addRow("Kinds & weights:", _gw)

        self.new_weapon_chance = QDoubleSpinBox()
        self.new_weapon_chance.setRange(0.0, 1.0)
        self.new_weapon_chance.setSingleStep(0.05)
        self.new_weapon_chance.setDecimals(2)
        self.new_weapon_chance.setValue(float(CONFIG.get('new_weapon_chance', 0.0)))
        self.new_weapon_chance.setToolTip("Per-pair chance that a card offers a brand-new weapon from the "
                                          "level's pool instead of a modifier. Both players are offered the "
                                          "same number of new-weapon cards. 0 disables.")
        rform.addRow("New-weapon chance:", self.new_weapon_chance)

        # What an automatic new-weapon card may draw beyond the level's plain weapon
        # pool. The New Weapon BUTTON always offers duals and upgrades; without these
        # the automatic rolls silently could not.
        self.auto_nw_abilities_cb = QCheckBox("Abilities")
        self.auto_nw_abilities_cb.setChecked(bool(CONFIG.get('auto_new_weapon_abilities')))
        self.auto_nw_abilities_cb.setToolTip("Let an automatic new-weapon card offer an ability "
                                             "(Sprint / Overshield / Regeneration / Camo), not just "
                                             "the New Weapon button. Halo 1 only, and still subject "
                                             "to the ability options: one per player, and Sprint and "
                                             "Camo only once per run.")
        rform.addRow("    ↳ Rolls may offer:", self.auto_nw_abilities_cb)

        self.auto_nw_duals_cb = QCheckBox("Dual-wield versions of weapons already held")
        self.auto_nw_duals_cb.setChecked(bool(CONFIG.get('auto_new_weapon_duals')))
        self.auto_nw_duals_cb.setToolTip("Halo 2 onward. Same rule the New Weapon button uses: "
                                         "a 'Dual <Weapon>' turns up only once the player holds "
                                         "that one-handed weapon.")
        rform.addRow("", self.auto_nw_duals_cb)

        self.auto_nw_upgrades_cb = QCheckBox("Upgrade weapons whose base is already held")
        self.auto_nw_upgrades_cb.setChecked(bool(CONFIG.get('auto_new_weapon_upgrades')))
        self.auto_nw_upgrades_cb.setToolTip("Halo 2 onward. Same rule the New Weapon button uses: "
                                            "an upgrade weapon is offered only once its base "
                                            "weapon is owned.")
        rform.addRow("", self.auto_nw_upgrades_cb)

        def _sync_auto_nw(_=False):
            on = self.new_weapon_chance.value() > 0
            for cb in (self.auto_nw_abilities_cb, self.auto_nw_duals_cb,
                       self.auto_nw_upgrades_cb):
                cb.setEnabled(on)           # nothing to widen if rolls are disabled
        self.new_weapon_chance.valueChanged.connect(_sync_auto_nw)
        _sync_auto_nw()

        self.special_rate = QDoubleSpinBox()
        self.special_rate.setRange(0.0, 2.0)
        self.special_rate.setSingleStep(0.05)
        self.special_rate.setDecimals(2)
        self.special_rate.setValue(float(CONFIG.get('special_rate_factor', 0.67)))
        self.special_rate.setToolTip("Scales how often special (escalating) effects appear; <1 = rarer.\nThese effects are your prime way to get tankier.")
        rform.addRow("Special-effect rate:", self.special_rate)
        self._opt_page("Run rules").addWidget(rolls)

        # ---- Map patching ----
        # #2: one "Map patching" box had grown to ten rows across three games. Split
        # per game, so a row is found by the game it belongs to. Built as separate
        # group boxes on the same page rather than more nav pages — they are short.
        patchg = QGroupBox("Map patching — Halo 3")
        patch_odst_g = QGroupBox("Map patching — Halo 3: ODST")
        odform = QFormLayout(patch_odst_g)
        odform.setLabelAlignment(Qt.AlignRight)
        form = QFormLayout(patchg)
        form.setLabelAlignment(Qt.AlignRight)

        self.cutscenes_cb = QCheckBox("Remove Cortana / Gravemind cutscenes (Halo 3)")
        self.cutscenes_cb.setChecked(bool(CONFIG.get('remove_h3_cutscenes', True)))
        self.cutscenes_cb.setToolTip("Halo 3 only: on patch, strip the flood Cortana-flicker and Gravemind "
                                     "vision cutscenes from the map. On by default; reversible — turn off "
                                     "and re-patch to restore.")
        form.addRow("Halo 3 cutscenes:", self.cutscenes_cb)

        self.ignore_elite_h3_cb = QCheckBox("Ignore Elite enemy effects in Halo 3 (they're allies)")
        self.red_plasma_cb = QCheckBox("ODST: treat the Red Plasma Rifle as the Brute Plasma Rifle")
        self.red_plasma_cb.setChecked(bool(CONFIG.get('odst_red_plasma_as_brute')))
        self.red_plasma_cb.setToolTip(
            "ODST's obtainable plasma rifle is the RED tag, which Halo 2 shipped as a "
            "separate, stronger Brute Plasma Rifle.\n\nWith this on it is also offered "
            "under that name in ODST, and on patch its base values are retuned to match "
            "Halo 2's: +2 rounds per second at both ends of the range, and 0.5 less "
            "minimum error and error angle on the dual-wield pair.\n\nNormal Plasma "
            "Rifle effects reach the red tag either way — that is in the tag data, not "
            "this option.")
        odform.addRow("Red plasma rifle:", self.red_plasma_cb)

        self.odst_variants_cb = QCheckBox("ODST: Auto Magnum and Silenced SMG ARE the Magnum and SMG")
        self.odst_variants_cb.setChecked(bool(CONFIG.get('odst_variants_as_base', True)))
        self.odst_variants_cb.setToolTip(
            "ODST never places the plain magnum or smg — only the Auto Magnum and "
            "Silenced SMG — so they are the game's sidearm and SMG.\n\nOn: one ordinary "
            "weapon card each; picking it gives the ODST variant, and there are no "
            "upgrade cards.\n\nOff: they become UPGRADES of the Magnum and SMG with "
            "their own cards.")
        odform.addRow("ODST variants:", self.odst_variants_cb)

        self.odst_downgrade_cb = QCheckBox("…and the map only stocks the base until it is drafted")
        self.odst_downgrade_cb.setChecked(bool(CONFIG.get('odst_downgrade_unupgraded')))
        self.odst_downgrade_cb.setToolTip(
            "Only while the variants are treated as upgrades. ODST hands the upgraded "
            "sidearm and SMG out everywhere, which makes an upgrade card for them "
            "meaningless — the map grants it anyway.\n\nWith this on, every Auto Magnum "
            "and Silenced SMG is rewritten to the base weapon until a player actually "
            "drafts that upgrade — on the ground, in the AI's hands, and in the "
            "starting profiles. ODST barely places these at all, so the AI loadouts "
            "are what matters: it is the weapon you pick up off a corpse.\n\nThe red "
            "plasma rifle joins them only while it is being treated as the Brute "
            "Plasma Rifle above; otherwise it simply IS this game's Plasma Rifle and "
            "there would be no card to earn it back with.\n\nNeeds a PREPARED ODST "
            "map — the plain magnum, SMG and plasma rifle are only real, resident "
            "weapons there.")

        def _sync_odst_variants(_=False):
            # only meaningful while they are modelled as upgrades
            on = not self.odst_variants_cb.isChecked()
            self.odst_downgrade_cb.setEnabled(on)
            if not on:
                self.odst_downgrade_cb.setChecked(False)
        self.odst_variants_cb.toggled.connect(_sync_odst_variants)
        _sync_odst_variants()
        odform.addRow("", self.odst_downgrade_cb)

        self.odst_pools_cb = QCheckBox("ODST: offer every weapon the prepared map supports")
        self.odst_pools_cb.setChecked(bool(CONFIG.get('odst_pools_from_map')))
        self.odst_pools_cb.setToolTip(
            "Off: each ODST level offers its own weapon list, close to what that level "
            "actually stocks — so the levels differ from each other and Kikowani stays "
            "a thin level with a short pool.\n\nOn: the pool is rebuilt from what the "
            "map file can really hand a player, which on a PREPARED map is all ~27 "
            "weapons. That is what the map preparation bought, and it also widens the "
            "zoom-donor pool.\n\nRead from the map rather than a fixed list, so a level "
            "that was never prepared offers less instead of offering weapons that would "
            "never appear.")
        odform.addRow("ODST weapon pools:", self.odst_pools_cb)

        self.odst_all_profiles_cb = QCheckBox(
            "ODST: write the starting weapons to EVERY starting profile")
        self.odst_all_profiles_cb.setChecked(
            bool(CONFIG.get('odst_all_starting_profiles')))
        self.odst_all_profiles_cb.setToolTip(
            "ODST picks the player's Starting Profile from the insertion point, and "
            "which one is live can change as a mission progresses — so the run's "
            "weapons can be written to profile 0 and the game can still spawn you on "
            "another profile holding the map's vanilla guns.\n\nWith this on, every "
            "profile in the scenario gets the picked starting weapons, so the loadout "
            "is right wherever the game puts you.\n\nOff by default because ODST also "
            "names NPC profiles (dutch, buck, odst02), so this hands squadmates the "
            "same weapons. That does not affect the run, but you will see it.")
        odform.addRow("ODST profiles:", self.odst_all_profiles_cb)

        self.odst_prof_ins_cb = QCheckBox(
            "ODST: give each player the profile their own insertion point uses")
        self.odst_prof_ins_cb.setChecked(bool(CONFIG.get('odst_profiles_by_insertion')))
        self.odst_prof_ins_cb.setToolTip(
            "The targeted alternative to the two blunt options above: instead of "
            "profile 0 (player 1 only) or every profile (which also arms co-op slots "
            "you are not standing in), each player gets the profile their own "
            "insertion point uses.\n\nODST declares four starting locations per "
            "insertion point — one per co-op player — and its profiles run "
            "in matching groups of four. ONI Alpha Site names them outright: Player / "
            "odst02 / odst03 / odst04 for the first entry, then dutch and the same "
            "three for the second.\n\nNOT YET CONFIRMED IN GAME. The grouping is "
            "inferred from naming and count across all nine maps; it needs one co-op "
            "run entering a mission from two different insertion points to prove. "
            "Overrides the blanket write when both are ticked.")
        odform.addRow("", self.odst_prof_ins_cb)

        self.odst_ai_drops_cb = QCheckBox("ODST: let AI drop equipment again")
        self.odst_ai_drops_cb.setChecked(bool(CONFIG.get('odst_ai_equipment_drops')))
        self.odst_ai_drops_cb.setToolTip(
            "ODST flags every equipment pickup “Never Dropped By AI” — all 11 of them, "
            "where Halo 3 flags none of its 27. That is why Brutes drop equipment in "
            "Halo 3 and never in ODST.\n\nWith this on, the flag is cleared on every "
            "equipment tag in the map, so Brutes drop their gear again — which also "
            "gives the Brute Drop Chance card something to act on, instead of tuning "
            "weights the flag was overriding outright.")
        odform.addRow("ODST AI drops:", self.odst_ai_drops_cb)

        self.odst_escort_cb = QCheckBox(
            "ODST: buff the Engineer and the olifaunt on Data Hive / Coastal Highway")
        self.odst_escort_cb.setChecked(bool(CONFIG.get('odst_escort_buff')))
        self.odst_escort_cb.setToolTip(
            "Both levels fail if the Engineer dies, and Coastal Highway also needs the "
            "olifaunt to survive — but neither scales with the run, so a few enemy "
            "damage cards make them impossible to protect.\n\nWith this on, whatever "
            "operator the run put on Player Health, Player Shield and Player Shield "
            "Recharge is mirrored onto Vergil and (on Coastal Highway) the olifaunt, "
            "so the escorts climb with the player.\n\nVergil is the FREEFORM engineer — "
            "read out of the scenario's own squad list, not guessed — and he ships far "
            "frailer than a normal Engineer: 50 shield against 300, and half the "
            "recharge rate. The enemy-side Engineers that shield Brutes use a different "
            "model and are left alone. Data Hive has no olifaunt tag, and reports that "
            "as a skip.")
        odform.addRow("ODST escorts:", self.odst_escort_cb)

        self.odst_all_ins_cb = QCheckBox(
            "ODST: also drop starting equipment at mid-mission insertion points")
        self.odst_all_ins_cb.setChecked(bool(CONFIG.get('odst_equipment_all_insertions')))
        self.odst_all_ins_cb.setToolTip(
            "Off (default): each player's equipment drops once, at their own start — "
            "insertion point 0, which every ODST level declares with exactly one "
            "location per co-op player.\n\nOn: it also drops at the level's other "
            "insertion points, the places a mission reverts you to as it progresses. "
            "Useful if you keep dying past a checkpoint and want the gear waiting "
            "there too, but it multiplies every pickup: ONI Alpha Site declares three "
            "insertion points, so one Invincibility becomes three.\n\nMombasa Streets' "
            "scripted level-select destinations are handled either way — the hub really "
            "does drop you at them.")
        odform.addRow("ODST equipment:", self.odst_all_ins_cb)

        self.odst_shield_health_cb = QCheckBox("ODST: Starting Shield cards raise Starting Health instead")
        self.odst_shield_health_cb.setChecked(bool(CONFIG.get('odst_shield_into_health', True)))
        self.odst_shield_health_cb.setToolTip(
            "ODST's player has stamina, not a shield. The Starting Shield field still "
            "exists and still accepts a write, it just does nothing useful — a 10x "
            "starting shield drains immediately.\n\nWith this on, a Starting Shield "
            "card spends itself on Starting Health in ODST, so drafting one is not a "
            "wasted pick. Other games are unaffected.")
        odform.addRow("ODST shields:", self.odst_shield_health_cb)

        self.odst_hub_cb = QCheckBox("ODST: patch Mombasa Streets alongside the mission")
        self.odst_hub_cb.setChecked(bool(CONFIG.get('odst_patch_hub', True)))
        self.odst_hub_cb.setToolTip(
            "ODST returns to Mombasa Streets between every story mission, so a run "
            "that only patches the mission leaves the hub — often the level you spend "
            "the most time in — completely vanilla.\n\nWith this on, patching any ODST "
            "mission writes the same plan into Mombasa Streets too. Effects for enemies "
            "the hub does not field are harmless no-ops, and because patching runs from "
            "the .bak baseline the hub always carries the CURRENT run rather than "
            "accumulating older ones.\n\nIMPORTANT: MCC keeps Mombasa Streets RESIDENT "
            "for the whole ODST campaign — it is the level the game returns to "
            "between missions. Once a run is under way the file is held open, so patch "
            "the hub with the game closed. The patcher checks and tells you when it is "
            "locked rather than reporting a failure you cannot act on.")
        odform.addRow("ODST hub:", self.odst_hub_cb)

        self.ignore_elite_h3_cb.setChecked(bool(CONFIG.get('ignore_elite_in_h3', True)))
        self.ignore_elite_h3_cb.setToolTip("On by default. In Halo 3 the Elites fight alongside you, "
                                           "so Elite enemy modifiers would tune your allies — this skips "
                                           "them when patching a Halo 3 map. Turn off to patch them anyway.")
        self.h3_all_chief_cb = QCheckBox("Arm every Chief starting profile, not just the first")
        self.h3_all_chief_cb.setChecked(bool(CONFIG.get('h3_all_chief_profiles', True)))
        self.h3_all_chief_cb.setToolTip(
            "Halo 3 hands the player a starting profile per ENTRY POINT — Crow’s Nest "
            "gives one at each rally point and none at all at level start — so writing "
            "only the first profile can leave you spawning empty-handed. This writes "
            "every Chief-role profile. Profiles a script deliberately leaves weaponless "
            "are still skipped.")
        form.addRow("Halo 3 profiles:", self.h3_all_chief_cb)
        form.addRow("Halo 3 Elites:", self.ignore_elite_h3_cb)

        self._opt_page("Patching").addWidget(patchg, 60)
        self._opt_page("Patching").addWidget(patch_odst_g, 70)

        # ---- Metagame scoring ----
        # Unlike everything else in this dialog, this writes OUTSIDE the map folders,
        # to <mcc_root>\Data\UI\scoredb.xml, and MCC parses that file only at startup.
        # So it is off by default and the restart requirement is stated on the group
        # itself, not buried in a tooltip -- a patch applied to a running game does
        # nothing at all and otherwise just looks broken.
        scoreg = QGroupBox("Metagame score (Data\\UI\\scoredb.xml)")
        sform = QFormLayout(scoreg)
        sform.setLabelAlignment(Qt.AlignRight)

        self.score_scaling_cb = QCheckBox("Enemies made nastier are worth more points")
        self.score_scaling_cb.setChecked(bool(CONFIG.get('score_scaling')))
        self.score_scaling_cb.setToolTip(
            "On patch, scale each enemy's campaign metagame score by the effects the "
            "run has applied to it. An effect's weight comes from its category "
            "(durability and rate of fire count most, senses and aggression least).\n\n"
            "Effects on a shared 'generic' tag only raise the score of the enemies "
            "that actually use it — an enemy that overrides those fields on its own "
            "tag is left out.\n\n"
            "The original file is backed up as scoredb.xml.bak and every patch "
            "re-scales from that baseline, so this never compounds.")
        sform.addRow("Scale scores:", self.score_scaling_cb)

        self.score_step = QDoubleSpinBox()
        self.score_step.setRange(0.0, 1.0)
        self.score_step.setSingleStep(0.01)
        self.score_step.setDecimals(3)
        self.score_step.setValue(float(CONFIG.get('score_step', 0.05)))
        self.score_step.setToolTip("How much one point of effect weight is worth: the "
                                   "multiplier is 1 + step x total weight. At 0.05 a "
                                   "heavily modified enemy lands around 2x.")
        sform.addRow("    ↳ Per weight point:", self.score_step)

        self.score_cap = QDoubleSpinBox()
        self.score_cap.setRange(0.0, 50.0)
        self.score_cap.setSingleStep(0.5)
        self.score_cap.setDecimals(1)
        self.score_cap.setValue(float(CONFIG.get('score_cap_mult', 0.0)))
        self.score_cap.setToolTip("Largest multiplier any enemy may reach. 0 = no cap.")
        sform.addRow("    ↳ Cap multiplier:", self.score_cap)

        self.score_push_cb = QCheckBox("Also push the new scores into a running MCC")
        self.score_push_cb.setChecked(bool(CONFIG.get('score_live_push', True)))
        self.score_push_cb.setToolTip(
            "MCC parses scoredb.xml once at startup, so without this every score change "
            "costs a full restart \u2014 and a Microsoft account login with it.\n\n"
            "With it on, the patcher writes the same numbers straight into the parsed "
            "score records in the running game, matched by enemy bucket, so the change "
            "takes effect immediately. The file is written either way, so a later "
            "restart lands on the same values.\n\n"
            "Harmless when MCC is closed: it simply reports that and the file edit "
            "stands on its own. Turn it off to go back to file-only patching.")
        sform.addRow("Live push:", self.score_push_cb)

        score_note = QLabel("MCC reads this file only at startup. With the live push "
                            "off (or MCC closed at patch time), restart the game for a "
                            "score change to take effect.")
        score_note.setWordWrap(True)
        score_note.setStyleSheet("color:#c8a45a; font-size:11px;")
        sform.addRow("", score_note)

        def _sync_score(_=False):
            on = self.score_scaling_cb.isChecked()
            self.score_step.setEnabled(on)
            self.score_cap.setEnabled(on)
            self.score_push_cb.setEnabled(on)
        self.score_scaling_cb.toggled.connect(_sync_score)
        _sync_score()

        # The death penalty is deliberately NOT under the score-scaling checkbox: that
        # one gates an edit to scoredb.xml, and this is an unrelated live write to the
        # MCC process that works whether or not scores are being rescaled.
        self.death_pen_cb = QCheckBox("Dying costs more the further the run gets")
        self.death_pen_cb.setChecked(bool(CONFIG.get('death_penalty_scaling')))
        self.death_pen_cb.setToolTip(
            "The campaign metagame docks you points for dying. This scales that "
            "penalty with how many rounds the run has taken, so a run that has "
            "collected a lot of buffs pays more for a death.\n\n"
            "penalty = base x (1 + per-round x rounds)\n\n"
            "This is NOT a map patch. Halo 1 and Halo 2 have no campaign metagame in "
            "their own dlls at all — the one scoring engine every game shares is "
            "the MCC wrapper, which holds the penalty as a constant. So it is written "
            "into the running process, which is also why it works in all five games "
            "and why it re-applies with the current round count on every patch.\n\n"
            "Nothing shared is overwritten: the constant has another user elsewhere in "
            "the binary, so the patch gives the death site its own private copy and "
            "leaves the original untouched. Harmless when MCC is closed.")
        sform.addRow("Death penalty:", self.death_pen_cb)

        self.death_pen_base = QDoubleSpinBox()
        self.death_pen_base.setRange(0.0, 10000.0)
        self.death_pen_base.setSingleStep(5.0)
        self.death_pen_base.setDecimals(1)
        self.death_pen_base.setValue(float(CONFIG.get('death_penalty_base', 25.0)))
        self.death_pen_base.setToolTip("Points a death costs at round 0. MCC ships 25.")
        sform.addRow("    ↳ Base penalty:", self.death_pen_base)

        self.death_pen_per = QDoubleSpinBox()
        self.death_pen_per.setRange(0.0, 5.0)
        self.death_pen_per.setSingleStep(0.05)
        self.death_pen_per.setDecimals(2)
        self.death_pen_per.setValue(float(CONFIG.get('death_penalty_per_round', 0.10)))
        self.death_pen_per.setToolTip(
            "Fraction of the base added per round taken. At 0.10 and a base of 25, "
            "round 10 costs 50 and round 20 costs 75.")
        sform.addRow("    ↳ Per round:", self.death_pen_per)

        self.betrayal_score_cb = QCheckBox(
            "Betrayal skull: killing Marines awards points instead of costing them")
        self.betrayal_score_cb.setChecked(bool(CONFIG.get('betrayal_marines_score', True)))
        self.betrayal_score_cb.setToolTip(
            "Under the Betrayal skull every human squad turns on you, so charging you "
            "for killing a Marine is backwards.\n\n"
            "Two things have to change together for that to work, which is why this is "
            "one switch: the ScoreDB Marine rows have to be positive, AND the wrapper's "
            "sign guard has to be opened — it discards any row that is not "
            "negative and charges a flat -50 instead. That guard is why setting the "
            "Marine scores positive by hand never did anything.\n\n"
            "Applied only while the run actually has Betrayal; both halves are put back "
            "otherwise, so a normal run keeps vanilla scoring. Measured in Halo 2 and "
            "Halo 3: Marines then pay out their row value, scaled by difficulty like "
            "any other kill.")
        sform.addRow("Betrayal scoring:", self.betrayal_score_cb)

        def _sync_death(_=False):
            on = self.death_pen_cb.isChecked()
            self.death_pen_base.setEnabled(on)
            self.death_pen_per.setEnabled(on)
        self.death_pen_cb.toggled.connect(_sync_death)
        _sync_death()

        self._opt_page("Patching").addWidget(scoreg, 30)

        # ---- Halo 2 engine patches ----
        # These edit halo2.dll, not a map, so they do NOT ride on the dialog's OK the
        # way every other option does: they take effect outside any run and outlive it.
        # Hence their own Apply button, and a reminder that the dll is mapped at process
        # start -- reloading a level is not enough, MCC has to be restarted.
        h2g = QGroupBox("Map patching — Halo 2 (halo2.dll)")
        h2form = QFormLayout(h2g)
        h2form.setLabelAlignment(Qt.AlignRight)

        self.h2_patch_boxes = {}
        for label, keys, tip in H2_PATCH_SETS:
            cb = QCheckBox(label)
            cb.setToolTip(tip)
            self.h2_patch_boxes[label] = (cb, keys)
            h2form.addRow("", cb)

        self.h2_patch_status = QLabel("")
        self.h2_patch_status.setWordWrap(True)
        self.h2_patch_status.setStyleSheet("color:#9a9a9a; font-size:11px;")
        h2form.addRow("", self.h2_patch_status)

        h2_btn = QPushButton("Apply to halo2.dll")
        h2_btn.setToolTip("Writes the selected patches to halo2.dll and reverts the "
                          "unselected ones. MCC must be CLOSED, and must be restarted "
                          "afterwards for the change to take effect.")
        h2_btn.clicked.connect(self._apply_h2_patches)
        h2form.addRow("", h2_btn)
        self._refresh_h2_patches()
        self._opt_page("Patching").addWidget(h2g, 50)

        # ---- Advanced ----
        adv = QGroupBox("Advanced")
        vform = QFormLayout(adv)
        vform.setLabelAlignment(Qt.AlignRight)

        self.debug_mode_cb = QCheckBox("Debug mode (developer tools)")
        self.debug_mode_cb.setChecked(bool(CONFIG.get('debug_mode')))
        self.debug_mode_cb.setToolTip("Shows the patcher's “＋ field” button and the main-window “ADD MOD” "
                                      "search. Leave off for normal play.")
        vform.addRow("Debug:", self.debug_mode_cb)

        # Debug-only VISIBILITY, but the setting itself keeps applying with debug off —
        # it is a correctness rule, not a developer toy, and hiding it must not quietly
        # turn it back off. _sync_debug_only_options() shows/hides it live.
        self.remove_flood_cb = QCheckBox("Remove Flood cards from ODST onward")
        self.remove_flood_cb.setChecked(bool(CONFIG.get('remove_flood_from_odst', True)))
        self.remove_flood_cb.setToolTip(
            "The Flood stop appearing after Halo 3, but ODST still ships their whole "
            "tag set, so their cards go on being offered and patched onto levels where "
            "nothing they edit can spawn. On by default. Only shown in debug mode — it "
            "stays in force either way.")
        self._debug_only_rows = [self.remove_flood_cb]
        vform.addRow("", self.remove_flood_cb)
        self.debug_mode_cb.toggled.connect(lambda _=None: self._sync_debug_only_options())
        self._sync_debug_only_options()
        self._opt_page("Interface").addWidget(adv)

        # ---- Appearance section ----
        appear = QGroupBox("Appearance")
        aform = QFormLayout(appear)
        aform.setLabelAlignment(Qt.AlignRight)

        auto = QLabel("Card size is worked out from your screen so every card matches "
                      "and stops resizing as you reroll. Tick a box to pin one yourself.")
        auto.setStyleSheet("color: #888; font-size: 11px;")
        auto.setWordWrap(True)
        aform.addRow("", auto)

        wrow = QHBoxLayout()
        self.card_width_override = QCheckBox("Override")
        self.card_width_override.setChecked(bool(CONFIG.get('card_width_override')))
        self.card_width = QSpinBox()
        self.card_width.setRange(240, 1400)
        self.card_width.setSingleStep(10)
        self.card_width.setValue(int(CONFIG.get('card_width', 600)))
        self.card_width.setEnabled(self.card_width_override.isChecked())
        self.card_width_override.toggled.connect(self.card_width.setEnabled)
        wrow.addWidget(self.card_width_override)
        wrow.addWidget(self.card_width, 1)
        tipw = ("Off: the width is (screen width ÷ 3) so three cards fill the row. "
                "On: this value is used instead.")
        self.card_width_override.setToolTip(tipw)
        self.card_width.setToolTip(tipw)
        aform.addRow("Card width (px):", wrow)

        hrow = QHBoxLayout()
        self.card_height_override = QCheckBox("Override")
        self.card_height_override.setChecked(bool(CONFIG.get('card_height_override')))
        self.card_height = QSpinBox()
        self.card_height.setRange(300, 2000)
        self.card_height.setSingleStep(10)
        self.card_height.setValue(int(CONFIG.get('card_height', 800)))
        self.card_height.setEnabled(self.card_height_override.isChecked())
        self.card_height_override.toggled.connect(self.card_height.setEnabled)
        hrow.addWidget(self.card_height_override)
        hrow.addWidget(self.card_height, 1)
        tiph = ("Off: the height is the screen height minus the header and buttons. "
                "On: this value is used instead. The card row scrolls either way.")
        self.card_height_override.setToolTip(tiph)
        self.card_height.setToolTip(tiph)
        aform.addRow("Card height (px):", hrow)

        self.card_spacing = QSpinBox()
        self.card_spacing.setRange(0, 120)
        self.card_spacing.setSingleStep(2)
        self.card_spacing.setValue(int(CONFIG.get('card_spacing', 20)))
        self.card_spacing.setToolTip("Empty space between the three cards. Cards shrink to keep "
                                     "the row fitting, unless the width override is on.")
        aform.addRow("Gap between cards (px):", self.card_spacing)

        self.card_row_margin = QSpinBox()
        self.card_row_margin.setRange(0, 200)
        self.card_row_margin.setSingleStep(5)
        self.card_row_margin.setValue(int(CONFIG.get('card_row_margin', 20)))
        self.card_row_margin.setToolTip("Empty space around the card row (left/right, and half "
                                        "that above/below).")
        aform.addRow("Margin around row (px):", self.card_row_margin)

        self.hide_tags_cb = QCheckBox("Hide the “Tag:” line on cards")
        self.hide_tags_cb.setChecked(bool(CONFIG.get('hide_tags')))
        self.hide_tags_cb.setToolTip("Hide the raw tag path (e.g. “weap …\\assault_rifle”) on cards — "
                                     "cosmetic only, it does not change what gets patched.")
        aform.addRow("Hide tags:", self.hide_tags_cb)

        self.hide_fields_cb = QCheckBox("Hide the “Fields:” line on cards")
        self.hide_fields_cb.setChecked(bool(CONFIG.get('hide_fields')))
        self.hide_fields_cb.setToolTip("Hide the list of tag fields a card edits — cosmetic only.")
        aform.addRow("Hide fields:", self.hide_fields_cb)
        self._opt_page("Interface").addWidget(appear)

        note = QLabel("Saved as global defaults and stored with this run's save.")
        note.setStyleSheet("color: #888; font-size: 11px;")
        note.setWordWrap(True)
        outer.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        # Spin boxes and combos default to WheelFocus, i.e. scrolling over one FOCUSES
        # it — after which the wheel guard rightly lets the wheel through and the value
        # starts changing. Downgrading to StrongFocus means only a click or Tab focuses
        # them, so scrolling the options list can never grab a field.
        for w in (self.findChildren(QAbstractSpinBox) + self.findChildren(QComboBox)):
            w.setFocusPolicy(Qt.StrongFocus)

        # #1: restore the remembered size LAST. Doing it in __init__ before the pages
        # existed was pointless — laying the content out afterwards grew the dialog
        # past whatever was restored, so it reopened at the content's natural size
        # every time. The stack is told it may shrink for the same reason.
        self._opt_stack.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        size = CONFIG.get('options_dialog_size')
        try:
            w0, h0 = int(size[0]), int(size[1])
        except (TypeError, ValueError, IndexError):
            w0, h0 = 620, 720
        self.resize(max(460, w0), max(320, h0))

    def done(self, r):
        # Remember the size on close, including on Cancel — it's a window preference,
        # not one of the options. Reading it here (rather than tracking resizeEvent)
        # keeps it to a single disk write per session.
        CONFIG['options_dialog_size'] = [self.width(), self.height()]
        save_settings()
        super().done(r)

    def _refresh_h2_patches(self):
        """Tick each box from what is actually in the dll right now. This is live state,
        not a saved preference -- the dll may have been patched by the command-line tool
        or restored by a game update since the last run."""
        try:
            hp2 = _h2_dll_patch()
            states = {}
            for label, (cb, keys) in self.h2_patch_boxes.items():
                st = {hp2.state_of(k) for k in keys}
                cb.setEnabled(True)
                cb.setChecked(st == {'APPLIED'})
                states[label] = ('applied' if st == {'APPLIED'} else
                                 'not applied' if st == {'not applied'} else
                                 'PARTIAL/UNRECOGNISED — re-apply to fix')
            self.h2_patch_status.setText(
                '  •  '.join('%s: %s' % (l.split(' (')[0], s) for l, s in states.items())
                + '\nMCC must be closed to apply, and restarted for it to take effect.')
        except Exception as e:
            for cb, _keys in self.h2_patch_boxes.values():
                cb.setEnabled(False)
            self.h2_patch_status.setText('halo2.dll not available: %s' % e)

    def _apply_h2_patches(self):
        try:
            hp2 = _h2_dll_patch()
        except Exception as e:
            QMessageBox.warning(self, "Halo 2 patches", "Could not load the patcher:\n%s" % e)
            return
        done, failed = [], []
        for label, (cb, keys) in self.h2_patch_boxes.items():
            want = cb.isChecked()
            for k in keys:
                try:
                    if (hp2.state_of(k) == 'APPLIED') != want:
                        hp2.apply(k, revert=not want)
                        done.append('%s %s' % ('applied' if want else 'reverted', k))
                except SystemExit as e:          # refused: bytes did not match
                    failed.append('%s: %s' % (k, e))
                except PermissionError:
                    failed.append('%s: halo2.dll is in use — close MCC first' % k)
                except Exception as e:
                    failed.append('%s: %s' % (k, e))
        self._refresh_h2_patches()
        if failed:
            QMessageBox.warning(self, "Halo 2 patches",
                                "Some patches could not be written:\n\n" + '\n'.join(failed))
        else:
            QMessageBox.information(
                self, "Halo 2 patches",
                ('\n'.join(done) if done else 'Nothing to change.')
                + '\n\nRestart MCC for this to take effect.')

    def values(self):
        return {
            'target_difficulty': self.diff_combo.currentData(),   # internal slot name
            'remove_single_game_mods': self.single_game_cb.isChecked(),
            'remove_boss_mods': not self._user_boss_cards,  # inverted UI ("Add Boss card"); boss_mods_removed() ORs in single-game at runtime
            'combine_heretic_hologram': self.combine_holo_cb.isChecked(),
            'remove_h3_cutscenes': self.cutscenes_cb.isChecked(),
            'ignore_elite_in_h3': self.ignore_elite_h3_cb.isChecked(),
            'odst_red_plasma_as_brute': self.red_plasma_cb.isChecked(),
            'odst_variants_as_base': self.odst_variants_cb.isChecked(),
            'odst_downgrade_unupgraded': self.odst_downgrade_cb.isChecked(),
            'odst_shield_into_health': self.odst_shield_health_cb.isChecked(),
            'odst_patch_hub': self.odst_hub_cb.isChecked(),
            'odst_pools_from_map': self.odst_pools_cb.isChecked(),
            'odst_all_starting_profiles': self.odst_all_profiles_cb.isChecked(),
            'odst_ai_equipment_drops': self.odst_ai_drops_cb.isChecked(),
            'odst_escort_buff': self.odst_escort_cb.isChecked(),
            'odst_equipment_all_insertions': self.odst_all_ins_cb.isChecked(),
            'odst_profiles_by_insertion': self.odst_prof_ins_cb.isChecked(),
            'other_chance': round(self.other_chance.value(), 2),
            'other_weights': {k: round(sp.value(), 1)
                              for k, (_cb, sp) in self.other_weight_boxes.items()},
            'other_hero_enabled': self.other_weight_boxes['hero'][0].isChecked(),
            'other_exhaust_enabled': self.other_weight_boxes['exhaust'][0].isChecked(),
            'other_skull_enabled': self.other_weight_boxes['skull'][0].isChecked(),
            'other_ally_enabled': self.other_weight_boxes['ally'][0].isChecked(),
            'new_weapon_chance': round(self.new_weapon_chance.value(), 2),
            'include_grenades': self.grenades_cb.isChecked(),
            'grenades_need_weapon': self.grenades_need_weapon_cb.isChecked(),
            'brute_chieftain_bosses': self.chieftain_boss_cb.isChecked(),
            'reach_elite_bosses': self.reach_elite_boss_cb.isChecked(),
            'reach_grunt_ultra_bosses': self.reach_grunt_boss_cb.isChecked(),
            'reach_jackal_sniper_bosses': self.reach_jackal_boss_cb.isChecked(),
            'h2_honor_guard_bosses': self.h2_honor_boss_cb.isChecked(),
            'odst_specops_bosses': self.odst_specops_boss_cb.isChecked(),
            'h3_specops_bosses': self.h3_specops_boss_cb.isChecked(),
            'heroes_are_bosses': self.heroes_boss_cb.isChecked(),
            'h2_sentinel_enforcer_bosses': self.h2_enforcer_boss_cb.isChecked(),
            'h3_equipment_in_rolls': self.equipment_rolls_cb.isChecked(),
            'score_scaling': self.score_scaling_cb.isChecked(),
            'score_step': round(self.score_step.value(), 3),
            'score_cap_mult': round(self.score_cap.value(), 1),
            'score_live_push': self.score_push_cb.isChecked(),
            'betrayal_marines_score': self.betrayal_score_cb.isChecked(),
            'death_penalty_scaling': self.death_pen_cb.isChecked(),
            'death_penalty_base': self.death_pen_base.value(),
            'death_penalty_per_round': self.death_pen_per.value(),
            'difficulty_baseline': {
                g: {k: round(self.baseline_spins[(g, k)].value(), 3)
                    for k, _t in BASELINE_COLS if self.baseline_spins[(g, k)].value()}
                for g in BASELINE_GAMES
                if any(self.baseline_spins[(g, k)].value() for k, _t in BASELINE_COLS)},
            'auto_new_weapon_abilities': self.auto_nw_abilities_cb.isChecked(),
            'auto_new_weapon_duals': self.auto_nw_duals_cb.isChecked(),
            'auto_new_weapon_upgrades': self.auto_nw_upgrades_cb.isChecked(),
            'equipment_need_weapon': self.equipment_need_weapon_cb.isChecked(),
            'remove_superflare_jammer': self.no_flare_jammer_cb.isChecked(),
            'remove_invincibility_invisibility': self.no_invinc_invis_cb.isChecked(),
            'denied_equipment_as_enemy_mods': self.denied_as_enemy_cb.isChecked(),
            'weapon_swap_cards': self.swap_cards_cb.isChecked(),
            'upgrade_inherits_base': self.upgrade_inherit_cb.isChecked(),
            'weapon_choice_negatives': self.negatives_cb.isChecked(),
            'special_rate_factor': round(self.special_rate.value(), 2),
            'set_starting_weapons': self.starting_weapons_cb.isChecked(),
            'set_starting_equipment': self.starting_equipment_cb.isChecked(),
            'equipment_all_selected': self.equipment_all_selected_cb.isChecked(),
            'two_player_coop': self.two_player_cb.isChecked(),
            'coop_no_starting_weapons': self.coop_no_start_cb.isChecked(),
            'null_coop_starting_equipment': self.coop_null_cb.isChecked(),
            'h2_add_respawn_profile': self.h2_respawn_cb.isChecked(),
            'h3_all_chief_profiles': self.h3_all_chief_cb.isChecked(),
            # Not in OPTION_KEYS: these are machine paths, not run settings, so
            # they must NOT be snapshotted into a saved run and restored onto a
            # co-op partner's machine. values() is also used to write CONFIG, so
            # returning them here is what makes the Options copy take effect.
            'mcc_root': self.mcc_root_edit.text().strip() or None,
            'assembly_plugins_dir': self.plugins_dir_edit.text().strip(),
            'swap_player_loadouts': self.swap_players_cb.isChecked(),
            'remove_superseded_vitality_cards': self.no_vit_cards_cb.isChecked(),
            'h2_extra_squads': {'08b': {'boss_johnson': self.h2_johnson_spin.value()}},
            'zoom_ui_on_scopeless': self.zoom_ui_cb.isChecked(),
            'turrets_are_weapons': self.turret_weapons_cb.isChecked(),
            'debug_mode': self.debug_mode_cb.isChecked(),
            'remove_flood_from_odst': self.remove_flood_cb.isChecked(),
            'card_width': self.card_width.value(),
            'card_height': self.card_height.value(),
            'card_width_override': self.card_width_override.isChecked(),
            'card_height_override': self.card_height_override.isChecked(),
            'card_spacing': self.card_spacing.value(),
            'card_row_margin': self.card_row_margin.value(),
            'hide_tags': self.hide_tags_cb.isChecked(),
            'hide_fields': self.hide_fields_cb.isChecked(),
            'sprint_feature': self.sprint_cb.isChecked(),
            # Legacy mirror of the per-ability card list, so older settings files (and
            # anything still reading the flag) stay consistent with the checkboxes.
            'sprint_mod_cards': self.ability_cards_cbs['sprint'].isChecked(),
            'sprint_start_with': self.sprint_start_cb.isChecked(),
            'sprint_as_card': self.sprint_cards_cb.isChecked(),
            'sprint_need_weapon': self.sprint_need_weapon_cb.isChecked(),
            'sprint_speed_pct': self.sprint_speed.value(),
            'sprint_duration_s': round(self.sprint_duration.value(), 1),
            'sprint_cooldown_s': round(self.sprint_cooldown.value(), 1),
            'shared_session_dir': self.share_dir_edit.text().strip(),
            'shared_session_autosave': self.share_autosave_cb.isChecked(),
            'abilities_offered': [ab for ab, cb in self.ability_offer_cbs.items()
                                  if cb.isChecked()],
            'ability_cards_for': [ab for ab, cb in self.ability_cards_cbs.items()
                                  if cb.isChecked()],
            'ability_start_which': self.ability_start_combo.currentData(),
            'overshield_mult': round(self.overshield_mult.value(), 2),
            'regen_percent': round(self.regen_percent.value(), 1),
            'regen_duration_s': round(self.regen_duration.value(), 1),
            'regen_fx_every': {g: b.value() for g, b in self.regen_fx_every.items()},
            'camo_duration_s': round(self.camo_duration.value(), 1),
            'camo_cooldown_s': round(self.camo_cooldown.value(), 1),
        }

    def _vault_module(self, title):
        """Import the vault tool, reporting rather than raising if it is missing."""
        sys.path.insert(0, str(Path(__file__).resolve().parent / 'sprint_toolkit'))
        try:
            import map_vault
            return map_vault
        except Exception as e:
            QMessageBox.warning(self, title, "Could not load the vault tool:\n%s" % e)
            return None

    def _restore_all_bak(self):
        """Put each map's preserved copy back over the live map, for every game.

        A stopgap, and NOT an undo for patching: the patcher already rebuilds from
        `<map>.bak` on every patch. This is for what the patcher cannot reach -- a map
        replaced wholesale by an Editing Kit build, or hand-copied -- where the only way
        back is the preserved copy.

        Which copy counts as preserved is `map_vault.originals()`'s decision, not a glob
        for `*.bak`: Halo 2 keeps its originals in a parallel `_bak` folder rather than
        beside the map, and `.vanilla.bak` outranks `.bak` where both exist. A glob would
        silently miss all of Halo 2.

        Unlike the archive, a candidate that is itself a rebuild is NOT rejected -- on
        this install several .bak files hold EK rebuilds on purpose, and restoring those
        is a legitimate reason to press this. The confirmation names the source kind
        instead of quietly deciding for you.
        """
        map_vault = self._vault_module("Restore all .bak")
        if map_vault is None:
            return
        jobs, lines = [], []
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            for game in map_vault.MAP_FOLDER:
                got, missing = [], 0
                try:
                    names = map_vault.maps_for(game)
                except Exception as e:
                    lines.append("%s: %s" % (game, e))
                    continue
                for n in names:
                    live = map_vault.resolve(game, n)
                    origs = map_vault.originals(game, live) if live else []
                    if origs:
                        got.append((origs[0][0], live, origs[0][1]))
                    else:
                        missing += 1
                if got:
                    kinds = sorted({k for _s, _d, k in got})
                    lines.append("%s: %d of %d map(s), from %s"
                                 % (game, len(got), len(names), ", ".join(kinds)))
                    jobs += got
                    if missing:
                        lines.append("      %d have no preserved copy \u2014 left alone"
                                     % missing)
                else:
                    lines.append("%s: no preserved copies at all" % game)
        finally:
            QApplication.restoreOverrideCursor()

        if not jobs:
            QMessageBox.information(self, "Restore all .bak",
                                    "Nothing to restore.\n\n" + "\n".join(lines))
            return
        if QMessageBox.question(
                self, "Restore all .bak",
                "Copy the preserved copy back over the live map, for %d map(s)?\n\n%s"
                "\n\nA preserved copy is only as pristine as whatever wrote it last: "
                "after an Editing Kit rebuild it holds THAT build, not the shipped map."
                % (len(jobs), "\n".join(lines)),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return

        done, failed = 0, []
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            for src, dst, _kind in jobs:
                try:
                    shutil.copyfile(src, dst)
                    done += 1
                except Exception as e:
                    failed.append("%s: %s" % (os.path.basename(dst), e))
        finally:
            QApplication.restoreOverrideCursor()
        msg = "Restored %d map(s) from their preserved copies." % done
        if failed:
            msg += "\n\nFailed:\n" + "\n".join(failed[:10])
        QMessageBox.information(self, "Restore all .bak", msg)

    def _restore_from_archive(self):
        """Unpack the per-game archives back over the live maps.

        The mirror image of the archive button: that writes one zip per game, this puts
        them back. Every entry is hashed as it is written and checked against the
        archive's own manifest, so a truncated or corrupted archive fails loudly instead
        of leaving an unbootable map behind -- extraction goes to a temp file beside the
        target and is only moved over the live map once the hash matches.
        """
        map_vault = self._vault_module("Restore from archive")
        if map_vault is None:
            return
        import hashlib
        import json as _json
        import zipfile

        src_dir = QFileDialog.getExistingDirectory(
            self, "Where are the map archives?",
            CONFIG.get('vault_dir') or str(Path.home()))
        if not src_dir:
            return

        plan, lines = [], []
        for game in map_vault.MAP_FOLDER:
            zp = map_vault.archive_path(game, src_dir)
            if not os.path.exists(zp):
                continue
            dest = map_vault.map_dir(game)
            if not os.path.isdir(dest):
                lines.append("%s: archive found, but %s is missing" % (game, dest))
                continue
            try:
                with zipfile.ZipFile(zp) as z:
                    man = _json.loads(z.read(map_vault.MANIFEST))
            except Exception as e:
                lines.append("%s: unreadable \u2014 %s" % (game, e))
                continue
            entries = man.get('entries', {})
            plan.append((game, zp, dest, entries))
            lines.append("%s: %d map(s), archived %s"
                         % (game, len(entries), man.get('created', '?')))
        if not plan:
            QMessageBox.information(
                self, "Restore from archive",
                "No usable archives in:\n%s\n\n%s"
                % (src_dir, "\n".join(lines) or "(none found)"))
            return
        if QMessageBox.question(
                self, "Restore from archive",
                "Unpack these over the live maps?\n\n%s\n\nThis overwrites the current "
                "map files. Anything built and deployed since the archive was made "
                "\u2014 ability plumbing, imported weapons, HUD edits \u2014 goes with them."
                % "\n".join(lines),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return

        CONFIG['vault_dir'] = src_dir
        save_settings()

        done, failed = 0, []
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            for game, zp, dest, entries in plan:
                try:
                    with zipfile.ZipFile(zp) as z:
                        for n, meta in sorted(entries.items()):
                            arc = meta.get('filename', n + '.map')
                            out = os.path.join(dest, os.path.basename(arc))
                            tmp = out + '.restoring'
                            h = hashlib.sha256()
                            with z.open(arc) as fsrc, open(tmp, 'wb') as fdst:
                                for chunk in iter(lambda: fsrc.read(1 << 20), b''):
                                    h.update(chunk)
                                    fdst.write(chunk)
                            want = meta.get('sha256')
                            if want and h.hexdigest() != want:
                                os.remove(tmp)
                                failed.append("%s %s: hash mismatch, left untouched"
                                              % (game, n))
                                continue
                            os.replace(tmp, out)
                            done += 1
                except Exception as e:
                    failed.append("%s: %s" % (game, e))
        finally:
            QApplication.restoreOverrideCursor()
        msg = "Restored %d map(s) from the archive." % done
        if failed:
            msg += "\n\nFailed:\n" + "\n".join(failed[:10])
        msg += ("\n\nThe .bak files beside the maps were NOT touched, so the next patch "
                "still rebuilds from whatever they hold.")
        QMessageBox.information(self, "Restore from archive", msg)

    def _refresh_baseline_vanilla(self):
        """Show what each game ships for the four dials, at the selected difficulty.

        Read from the PATCHER'S baseline -- `<map>.map.bak` where one exists, else the
        live map -- because that is what a patch actually starts from. Reading the live
        map instead would show a previous patch's values back to the user as if they
        were Bungie's.

        Cached per (game, difficulty): each miss opens a campaign map, which is hundreds
        of megabytes, and the difficulty selector would otherwise re-read six of them on
        every change.
        """
        diff = (self.diff_combo.currentData() or self.diff_combo.currentText()
                or 'Normal')
        cache = getattr(self, '_baseline_vanilla_cache', None)
        if cache is None:
            cache = self._baseline_vanilla_cache = {}
        for game in BASELINE_GAMES:
            key = (game, diff)
            if key not in cache:
                cache[key] = self._read_baseline_for(game, diff)
            vals = cache[key]
            for k, _title in BASELINE_COLS:
                lab = self.baseline_vanilla.get((game, k))
                if lab is None:
                    continue
                v = (vals or {}).get(k)
                lab.setText('(%g)' % v if isinstance(v, (int, float))
                            else '(\u2013)')
                lab.setToolTip('' if vals else
                               '%s is not installed, so its shipped values cannot be '
                               'read. The settings are still saved.' % game)

    def _read_baseline_for(self, game, difficulty):
        """{key: shipped value} for one game, or None when it cannot be read.

        The mission list comes from `map_vault.maps_for`, which reads halo.json itself.
        An earlier version used `self.db` — but `db` lives on the MAIN WINDOW, not on
        this dialog, so every call raised AttributeError, the blanket except swallowed
        it, and all six games displayed "(–)" as though nothing were installed. The
        reason is now reported in debug mode rather than vanishing.
        """
        try:
            import halo_patch
            sys.path.insert(0, str(Path(__file__).resolve().parent / 'sprint_toolkit'))
            import map_vault
            if game not in map_vault.MAP_FOLDER:
                return None                      # Reach / Halo 4: no map folder at all
            subdirs = CONFIG.get('plugin_subdirs_by_game', {}).get(game, [])
            registry = halo_patch.PluginRegistry(CONFIG.get('assembly_plugins_dir'),
                                                 subdirs)
            for mid in map_vault.maps_for(game):
                path = map_vault.resolve(game, mid)
                if not path:
                    continue
                src = path + '.bak' if os.path.exists(path + '.bak') else path
                m = halo_patch.open_map(src, game)
                return halo_patch.read_difficulty_baseline(m, registry, difficulty)
        except Exception as e:
            if CONFIG.get('debug_mode'):
                print('baseline read failed for %s @ %s: %s' % (game, difficulty, e))
            return None
        return None

    def _archive_vanilla_maps(self):
        """Archive each game's pristine campaign maps into one zip per game.

        A modded install accumulates copies: the originals sit around as .bak (Halo 1,
        Halo 3, ODST) or in a parallel _bak folder (Halo 2), several GB per game. This
        puts them somewhere chosen, verified, and out of the way.

        The destination is ASKED for rather than assumed — on a play machine this tool
        folder does not exist, and an archive on the same disk as the maps protects
        against nothing.

        Nothing is packed on a guess. A map is archived only from a copy that claims to
        be pristine (.vanilla.bak, then .shipped, then .bak), never from the live file,
        and a candidate that is itself an Editing Kit rebuild is rejected. An archive
        that enshrines a modified map as "the original" is the one mistake here with no
        way back.
        """
        sys.path.insert(0, str(Path(__file__).resolve().parent / 'sprint_toolkit'))
        try:
            import map_vault
        except Exception as e:
            QMessageBox.warning(self, "Archive vanilla maps",
                                "Could not load the vault tool:\n%s" % e)
            return

        dest = QFileDialog.getExistingDirectory(
            self, "Where should the map archives go?",
            CONFIG.get('vault_dir') or str(Path.home()))
        if not dest:
            return

        games = list(map_vault.MAP_FOLDER)
        plans = {}
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            for g in games:
                try:
                    plans[g] = map_vault.plan_pack(g)
                except Exception as e:
                    plans[g] = ([], [("—", str(e))], 0)
        finally:
            QApplication.restoreOverrideCursor()

        lines, ready = [], []
        for g in games:
            picked, skipped, total = plans[g]
            mb = sum(os.path.getsize(p) for _, p, _, _ in picked) / 1048576.0
            lines.append("{}: {} of {} map(s), {:,.0f} MB".format(
                g, len(picked), total, mb))
            for n, why in skipped:
                lines.append("      skipped %s — %s" % (n, why))
            if picked:
                ready.append(g)
        if not ready:
            QMessageBox.information(
                self, "Archive vanilla maps",
                "No pristine originals found for any game.\n\n" + "\n".join(lines))
            return

        warn = ""
        if any(plans[g][1] for g in ready):
            warn = ("\n\nNOTE: some maps have no preserved original and are skipped, "
                    "so those games archive INCOMPLETE.")
        if QMessageBox.question(
                self, "Archive vanilla maps?",
                "Write one archive per game into:\n%s\n\n%s%s"
                % (dest, "\n".join(lines), warn)) != QMessageBox.Yes:
            return

        CONFIG['vault_dir'] = dest          # remembered via SETTINGS_KEYS
        save_settings()

        written, failed = [], []
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            for g in ready:
                try:
                    out = map_vault.pack(g, dest=dest, yes=True, echo=False)
                    ok = map_vault.verify(g, dest=dest)
                    written.append("%s: %s%s" % (g, Path(out).name,
                                                 "" if ok else "   (VERIFY FAILED)"))
                except Exception as e:
                    failed.append("%s: %s" % (g, e))
        finally:
            QApplication.restoreOverrideCursor()

        msg = ("Archived:\n" + "\n".join(written)) if written else "Nothing archived."
        if failed:
            msg += "\n\nFailed:\n" + "\n".join(failed)
        msg += ("\n\nThe originals are still in place — nothing was deleted. "
                "Open the archive and check it before removing anything.")
        QMessageBox.information(self, "Archive vanilla maps", msg)

    def _apply_sprint_to_maps(self):
        """Byte-patch the current sprint settings into every H1 campaign map that
        carries the sprint mod, turning sprint on. Uses the live widget values (not
        yet-saved), reuses halo_patch.apply_run(sprint=cfg) — which skips any map
        without the sprint weapon (checked in _apply_sprint before any write)."""
        import halo_patch
        which = self.ability_start_combo.currentData() or 'sprint'
        cfg = {
            # Applying from here means "turn the start-with ability on for both players".
            'player_abilities': {0: which, 1: which},
            'enabled': True,
            'speed_pct': self.sprint_speed.value(),
            'duration_ticks': max(1, round(self.sprint_duration.value() * 30)),
            'cooldown_ticks': max(0, round(self.sprint_cooldown.value() * 30)),
            'os_mult': self.overshield_mult.value(),
            'medi_percent': self.regen_percent.value(),
            'medi_duration_ticks': max(1, round(self.regen_duration.value() * 30)),
            'regen_fx_every_by_game': {g: b.value()
                                       for g, b in self.regen_fx_every.items()},
            'camo_seconds': self.camo_duration.value(),
            'camo_cooldown_ticks': max(0, round(self.camo_cooldown.value() * 30)),
        }
        root = mcc_root()
        folder = CONFIG.get('map_game_folder', {}).get('Halo 1', 'halo1/maps')
        maps = CONFIG.get('h1_campaign_maps', [])
        paths = [(mid, halo_patch.default_map_path(root, folder, mid)) for mid in maps]
        present = [(mid, p) for mid, p in paths if p and Path(p).is_file()]
        if not present:
            QMessageBox.warning(self, "No maps found",
                                f"No Halo 1 maps under:\n{Path(root) / folder}\n\n"
                                "Point the MCC folder (Options) at your install or the sprint mod.")
            return
        detail = {'sprint': f"{self.sprint_speed.value()}%, "
                            f"{self.sprint_duration.value():g}s / "
                            f"{self.sprint_cooldown.value():g}s cd",
                  'overshield': f"x{self.overshield_mult.value():g}",
                  'regeneration': f"{self.regen_percent.value():g}% over "
                                  f"{self.regen_duration.value():g}s",
                  'camo': f"{self.camo_duration.value():g}s / "
                          f"{self.camo_cooldown.value():g}s cd"}.get(which, '')
        if QMessageBox.question(
                self, "Apply abilities to maps?",
                f"Turn on {which} ({detail}) for both players "
                f"in up to {len(present)} Halo 1 map(s) under:\n{Path(root) / folder}\n\n"
                "Maps not built with the ability mod are skipped. A one-time .bak is made "
                "for each map changed.") != QMessageBox.Yes:
            return

        subdirs = CONFIG.get('plugin_subdirs_by_game', {}).get('Halo 1', ['Halo1MCC', 'Halo1'])
        registry = halo_patch.PluginRegistry(CONFIG.get('assembly_plugins_dir'), subdirs)
        difficulty = CONFIG.get('target_difficulty', 'Normal')
        patched, skipped = [], []
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            for mid, mp in present:
                try:
                    results, _ = halo_patch.apply_run(mp, [], registry, difficulty,
                                                      game='Halo 1', sprint=cfg)
                except Exception as e:
                    skipped.append(f"{mid}: error — {e}")
                    continue
                sres = next((r for r in results if r.get('field') == 'sprint'), None)
                if sres and sres.get('ok') and not sres.get('skip'):
                    patched.append(mid)
                else:
                    skipped.append(f"{mid}: {sres.get('reason', 'skipped') if sres else 'skipped'}")
        finally:
            QApplication.restoreOverrideCursor()

        msg = f"Sprint applied to {len(patched)} map(s): {', '.join(patched) or '—'}"
        if skipped:
            msg += "\n\nSkipped (no sprint mod):\n" + "\n".join(skipped)
        QMessageBox.information(self, "Apply Sprint to maps", msg)



class PatchComparerDialog(QDialog):
    r"""Compare two patch logs — the co-op desync window.

    Two machines in co-op must have byte-identical maps. When they don't, the symptom
    is vague (odd damage numbers, an enemy that behaves differently on one screen,
    a crash on load) and the patch code only confirms that something is off. This
    answers the next question: WHAT is off.

    The heavy lifting is `sprint_toolkit/patch_diff.py`, imported rather than
    reimplemented so the window and the command line can never drift apart.
    """

    HOW_TO = (
        "<b>What this is for</b><br>"
        "In co-op, both machines must be running the <i>same</i> patched map. The "
        "patch code in the status bar tells you whether they match — but not what "
        "differs when they don't. This does."
        "<br><br><b>How to use it</b><br>"
        "1. Patch a map. The Enhancer writes a log of every edit to "
        "<code>patches\\patch_&lt;map&gt;_&lt;date&gt;.json</code>.<br>"
        "2. Have your co-op partner send you theirs for the same map — it is a small "
        "text file, any chat or mail works.<br>"
        "3. Load yours as <b>A</b> and theirs as <b>B</b>, then press Compare.<br>"
        "<i>Use Latest for this map</i> fills in the newest local log, which is also "
        "how you compare two of your <i>own</i> patches — e.g. before and after "
        "changing a magnitude, or to see what a re-patch actually altered."
        "<br><br><b>Reading the result</b> — findings come most-serious first:<br>"
        "&nbsp;• <b>Not comparable</b> — different level, difficulty or tool version. "
        "Fix this first; everything below it is meaningless until you do.<br>"
        "&nbsp;• <b>Planned on one machine only</b> — the runs disagree, not the maps. "
        "Different cards drawn, a card blacklisted on one side, or different options. "
        "Fix it in the run.<br>"
        "&nbsp;• <b>Same edit, different value</b> — if the two <i>original</i> values "
        "differ, that side was patched over an already-patched map instead of from its "
        "<code>.bak</code>, and its multipliers have compounded. Restore and re-patch. "
        "If the originals agree, the magnitude differed.<br>"
        "&nbsp;• <b>Did not land on one machine</b> — usually a tag missing from that "
        "map, so the field is still vanilla there and modified here.<br>"
        "&nbsp;• <b>No differences</b> — then it is not the patch. Check the dll "
        "patches, which .map each machine actually loaded, and whether one side "
        "started the session on an old map."
        "<br><br>Timestamps and file paths are ignored, and order is ignored — a plan "
        "is a set of edits, not a sequence."
    )

    def __init__(self, parent=None, default_mission=''):
        super().__init__(parent)
        self.setWindowTitle("Compare Patches")
        # Deliberately NOT modal: this is a reference window you keep open while you
        # re-patch a map and compare again.
        self.setModal(False)
        self.setMinimumSize(900, 700)
        self.setWindowFlags(self.windowFlags()
                            | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        _sz = CONFIG.get('compare_dialog_size')
        if isinstance(_sz, (list, tuple)) and len(_sz) == 2:
            try:
                self.resize(max(900, int(_sz[0])), max(700, int(_sz[1])))
            except (TypeError, ValueError):
                pass
        self.default_mission = default_mission or ''
        self.setStyleSheet("""
            QLineEdit { background-color: #1a1a1a; color: #e0e0e0;
                        border: 1px solid #3a3a3a; padding: 4px; border-radius: 3px; }
            QLabel { color: #e0e0e0; }
            QGroupBox { color: #e0e0e0; border: 1px solid #3a3a3a;
                        border-radius: 5px; margin-top: 8px; padding-top: 8px; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
            QTextEdit { background-color: #141414; color: #e0e0e0;
                        border: 1px solid #2a2a2a; border-radius: 3px; }
            QScrollBar:vertical { background: #202020; width: 16px; margin: 0; }
            QScrollBar::handle:vertical { background: #6a6a6a; min-height: 40px;
                        border-radius: 5px; border: 1px solid #808080; }
            QScrollBar::handle:vertical:hover { background: #8fb8ff;
                        border-color: #8fb8ff; }
        """)

        root = QVBoxLayout(self)

        help_box = QGroupBox("How to use this")
        hb = QVBoxLayout(help_box)
        help_lbl = QLabel(self.HOW_TO)
        help_lbl.setWordWrap(True)
        help_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        hb.addWidget(help_lbl)
        # The instructions are long on purpose but must not crowd out the result, so
        # they live in a scroll area with a hard ceiling on their height.
        help_scroll = QScrollArea()
        help_scroll.setWidgetResizable(True)
        help_scroll.setWidget(help_box)
        help_scroll.setMaximumHeight(230)
        help_scroll.setFrameShape(QFrame.NoFrame)
        root.addWidget(help_scroll)

        pick = QGridLayout()
        self.edit_a = QLineEdit()
        self.edit_b = QLineEdit()
        for row, (label, edit, who) in enumerate((
                ("A — your patch log", self.edit_a, 'a'),
                ("B — their patch log", self.edit_b, 'b'))):
            lbl = QLabel(label)
            lbl.setMinimumWidth(150)
            pick.addWidget(lbl, row, 0)
            edit.setPlaceholderText("…\\patches\\patch_<map>_<date>.json")
            pick.addWidget(edit, row, 1)
            browse = QPushButton("Browse…")
            browse.setAutoDefault(False)
            browse.setDefault(False)
            browse.clicked.connect(lambda _=False, w=who: self._browse(w))
            pick.addWidget(browse, row, 2)
            latest = QPushButton("Latest for this map")
            latest.setAutoDefault(False)
            latest.setDefault(False)
            latest.setToolTip("Fill in the most recent local patch log for this map. "
                              "Press it on both rows to compare your two newest.")
            latest.clicked.connect(lambda _=False, w=who: self._latest(w))
            pick.addWidget(latest, row, 3)
        pick.setColumnStretch(1, 1)
        root.addLayout(pick)

        bar = QHBoxLayout()
        self.compare_btn = QPushButton("⚖  COMPARE")
        self.compare_btn.setStyleSheet("""
            QPushButton { background-color: #2a4a5a; color: white; font-weight: bold;
                          font-size: 14px; padding: 8px 22px; border-radius: 5px; }
            QPushButton:hover { background-color: #3a6a7a; }
        """)
        self.compare_btn.setDefault(True)
        self.compare_btn.clicked.connect(self.on_compare)
        bar.addWidget(self.compare_btn)

        self.detail_chk = QCheckBox("Also show the full plan and outcome tables")
        self.detail_chk.setStyleSheet("QCheckBox { color: #e0e0e0; }")
        self.detail_chk.setToolTip("Every planned edit and every written row from both "
                                   "sides, not just the differences.")
        bar.addWidget(self.detail_chk)
        bar.addStretch()

        for text, slot, tip in (
                ("Copy result", self.on_copy, "Copy the report to the clipboard"),
                ("Open patches folder", self.on_open_folder,
                 "Where the Enhancer writes patch logs — this is the file to send "
                 "your partner"),
                ("Close", self.close, "")):
            b = QPushButton(text)
            b.setAutoDefault(False)
            b.setDefault(False)
            if tip:
                b.setToolTip(tip)
            b.clicked.connect(slot)
            bar.addWidget(b)
        root.addLayout(bar)

        self.out = QTextEdit()
        self.out.setReadOnly(True)
        self.out.setLineWrapMode(QTextEdit.NoWrap)
        mono = QFont('Consolas')
        mono.setStyleHint(QFont.Monospace)
        mono.setPointSize(9)
        self.out.setFont(mono)
        self.out.setPlaceholderText("Pick two patch logs above and press Compare.")
        root.addWidget(self.out, 1)

    # ---- helpers ---------------------------------------------------------------
    def _patch_dir(self):
        return app_data_dir() / "patches"

    def _browse(self, who):
        start = self._patch_dir()
        path, _ = QFileDialog.getOpenFileName(
            self, "Pick a patch log",
            str(start if start.is_dir() else app_data_dir()),
            "Patch logs (patch_*.json);;JSON files (*.json);;All files (*)")
        if path:
            (self.edit_a if who == 'a' else self.edit_b).setText(path)

    def _latest(self, who):
        """Newest local log for this map. The B row takes the SECOND newest when A is
        already showing the newest, which is what you want when comparing two of your
        own patches — otherwise both rows would name the same file."""
        d = self._patch_dir()
        if not d.is_dir():
            QMessageBox.information(self, "No patch logs yet",
                                    "Nothing has been patched yet — a log is written "
                                    "each time you apply effects to a map.")
            return
        pat = f"patch_{self.default_mission}_*.json" if self.default_mission else "patch_*.json"
        found = sorted(d.glob(pat), key=lambda p: p.stat().st_mtime, reverse=True)
        if not found:
            QMessageBox.information(self, "No patch logs yet",
                                    f"No log matching {pat} in\n{d}")
            return
        target = self.edit_a if who == 'a' else self.edit_b
        other = self.edit_b if who == 'a' else self.edit_a
        pick = str(found[0])
        if pick == other.text().strip() and len(found) > 1:
            pick = str(found[1])
        target.setText(pick)

    def on_open_folder(self):
        d = self._patch_dir()
        d.mkdir(exist_ok=True)
        try:
            if sys.platform == 'win32':
                os.startfile(str(d))                  # noqa: S606 - user-invoked
            else:
                import subprocess
                subprocess.Popen(['xdg-open' if sys.platform.startswith('linux')
                                  else 'open', str(d)])
        except Exception as e:
            QMessageBox.warning(self, "Couldn't open it", f"{d}\n\n{e}")

    def on_copy(self):
        text = self.out.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    def on_compare(self):
        pa, pb = self.edit_a.text().strip(), self.edit_b.text().strip()
        missing = [n for n, p in (('A', pa), ('B', pb)) if not p or not Path(p).is_file()]
        if missing:
            QMessageBox.warning(self, "Pick two patch logs",
                                "Not readable: " + ", ".join(missing))
            return
        try:
            import importlib
            sys.path.insert(0, str(Path(__file__).resolve().parent / 'sprint_toolkit'))
            pd = importlib.import_module('patch_diff')
            importlib.reload(pd)
        except Exception as e:
            QMessageBox.critical(self, "Comparer unavailable",
                                 "sprint_toolkit/patch_diff.py could not be "
                                 f"loaded:\n\n{e}")
            return
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            # 'A'/'B', not the filenames: two logs of the same map on the same day
            # truncate to the same string, which would label both sides identically.
            # The header above the report names the two files in full.
            text, n = pd.compare_files(pa, pb, 'A', 'B',
                                       detail=self.detail_chk.isChecked())
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Comparison failed",
                                 f"{type(e).__name__}: {e}")
            return
        finally:
            QApplication.restoreOverrideCursor()
        header = f"  A = {pa}\n  B = {pb}\n\n"
        self.out.setPlainText(header + text)
        self.setWindowTitle("Compare Patches — %s"
                            % ("no differences" if not n else f"{n} difference(s)"))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        CONFIG['compare_dialog_size'] = [self.width(), self.height()]


class HaloGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        # Let failures propagate so main() can report them and exit cleanly,
        # rather than showing a half-constructed window that crashes later.
        self.db = ModifierDatabase()
        self.run_state = RunState()
        self.loaded_run_path = None   # set when a run is loaded; steers the save default
        self.shared_run_path = None   # this run's file in the shared folder, re-used
        self.enhancer = RunEnhancer(self.db, self.run_state)
        self.pair_cards = []
        self.pending_player2_selection = False
        self._manual_queue = []       # #3: players still owed a New Weapon pick
        self._manual_results = {}     # player -> {weapon, enemy} from the New Weapon draw
        self._p1_start_enemy = None   # P1's tied negative from the start-of-run weapon pick
        self.setup_ui()
        self.show_start_dialog()

    def show_start_dialog(self):
        dialog = StartDialog(self)
        if dialog.exec() == QDialog.Accepted:
            if dialog.choice == 'new':
                self.show_weapon_selection()
            elif dialog.choice == 'load':
                self.load_run_state(dialog.loaded_state, getattr(dialog, 'loaded_path', None))
        else:
            self.close()

    def on_main_menu(self):
        """#4: reopen the start menu mid-session so a different run can be loaded.
        Not show_start_dialog(): there, Cancel means "quit at startup"; here it
        has to mean "never mind, stay in the current run"."""
        if QMessageBox.question(
                self, "Back to main menu",
                "Return to the main menu to start or load a different run?\n\n"
                "Anything you haven't stored with 💾 SAVE SELECTION will be lost.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        dialog = StartDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        if dialog.choice == 'load':
            self.load_run_state(dialog.loaded_state, getattr(dialog, 'loaded_path', None))
        elif dialog.choice == 'new':
            # Fresh run on the level that's currently selected in the dropdowns.
            mid = self.mission_combo.currentData() or self.run_state.mission_id
            self.run_state = RunState()
            # A new run isn't the loaded/shared file any more.
            self.loaded_run_path = None
            self.shared_run_path = None
            self.run_state.mission_id = mid
            info = self.db.mission_enemies.get(mid)
            if info:
                self.run_state.mission_name = info['name']
            self.enhancer = RunEnhancer(self.db, self.run_state)
            self._p1_start_enemy = None
            self._manual_queue = []
            self._manual_results = {}
            self.pending_player2_selection = False
            self.clear_pairs()
            self.update_weapon_display()
            self.update_history()
            self._sync_save_button()
            self.show_weapon_selection()

    # ---- Weapon Selection ----
    def _current_game(self):
        return self.db.get_game_for_mission(self.run_state.mission_id)

    def _enemy_pool(self):
        # Already includes the general negative pool and is blacklist-filtered.
        return self.db.get_enemy_modifiers_filtered(
            self.run_state.mission_id, self.run_state.blacklist, self._current_game())

    def _pick_enemy(self, enemy_mods, used_enemies):
        available = [e for e in enemy_mods if e.get('name', '') not in used_enemies]
        if not available:
            available = enemy_mods
        if not available:
            return None
        enemy = random.choice(available)
        used_enemies.add(enemy.get('name', ''))
        return enemy

    def _drop_taken_one_per_run(self, weapons):
        """Sprint and camo are one-per-run picks: never offer them once either player
        owns them, no matter which pool fed us. A backstop to _ability_offer_pool, not
        a substitute — every card an offer path can PUT ON SCREEN must pass through
        here, which means both the initial build and the rerolls, since rerolls do not
        go through _build_weapon_choices."""
        rs = getattr(self, 'run_state', None)
        if rs is None:
            return weapons
        held = {ability_of_item(w) for w in
                rs.weapons_for('player1') + rs.weapons_for('player2')
                if is_ability_item(w)}
        gone = held & ABILITY_ONE_PER_RUN
        # Weapon uniqueness rides the same backstop: this is the one place every
        # on-screen offer passes through, initial build and rerolls alike.
        weapons = drop_weapons_taken(self.db, weapons, rs)
        if not gone:
            return weapons
        return [w for w in weapons if ability_of_item(w) not in gone]

    def _build_weapon_choices(self, weapons, enemy_mods, count=3, with_enemy=True):
        choices = []
        used_weapons = set()
        used_enemies = set()
        weapons = self._drop_taken_one_per_run(weapons)
        for i in range(count):
            available = [w for w in weapons if w not in used_weapons]
            if not available:
                break
            weapon = random.choice(available)
            used_weapons.add(weapon)
            choices.append({
                'id': i + 1,
                'weapon': weapon,
                'modifiers': self.db.get_offer_modifiers(weapon),
                'enemy_mod': self._pick_enemy(enemy_mods, used_enemies) if with_enemy else None
            })
        return choices

    def _reroll_weapon_choice(self, choice_id, weapon_pool=None, exclude_weapons=(),
                              player_label="", with_enemy=True):
        weapons = weapon_pool if weapon_pool is not None else self.db.get_available_weapons()
        # Same backstop the initial build applies — a reroll is an offer path too.
        weapons = self._drop_taken_one_per_run(weapons)
        exclude_weapons = set(exclude_weapons)
        enemy_mods = self._enemy_pool()
        for card in self.pair_cards:
            if not (hasattr(card, 'pair_data') and card.pair_data['id'] == choice_id):
                continue
            used_weapons = set()
            used_enemies = set()
            for other in self.pair_cards:
                if hasattr(other, 'pair_data') and other.pair_data['id'] != choice_id:
                    used_weapons.add(other.pair_data['weapon'])
                    other_enemy = other.pair_data.get('enemy_mod')
                    if other_enemy:
                        used_enemies.add(other_enemy.get('name', ''))
            avail = [w for w in weapons
                     if w not in exclude_weapons and w not in used_weapons]
            if not avail:
                # Relaxing used_weapons is fine — two cards showing the same weapon is
                # only cosmetic. exclude_weapons is NOT relaxable: it carries the other
                # player's weapon (P2's reroll) and the player's own owned weapons (the
                # manual path), so falling back to the whole pool would offer a weapon
                # the caller specifically said is not offerable. Better to say so below.
                avail = [w for w in weapons if w not in exclude_weapons]
            if not avail:
                # Nothing left to offer — e.g. the last candidate was just blacklisted.
                # Leave the card as it is and say so, rather than raising on an empty
                # random.choice and taking the whole selection down.
                self.update_status("Nothing left to offer%s — un-blacklist a weapon to "
                                   "reroll again." % player_label)
                return
            card.pair_data['weapon'] = random.choice(avail)
            card.pair_data['modifiers'] = self.db.get_offer_modifiers(card.pair_data['weapon'])
            card.pair_data['enemy_mod'] = self._pick_enemy(enemy_mods, used_enemies) if with_enemy else None
            card.setup_ui()
            self.update_status(f"Rerolled choice {choice_id}{player_label}")
            break

    def _blacklisted_weapon(self, weapon):
        return self.db.weapon_label(weapon) in self.run_state.blacklist

    def _game_weapon_pool(self, player=None):
        """Weapons offerable as a fresh pick (initial choice, reroll, manual
        change): the game's weapon pool minus blacklisted weapons AND minus
        upgrade weapons (#3), which must only be reachable via the New Weapon
        button's explicit "base already owned" check in `_weapon_offer_pool`."""
        upgrades = weapon_upgrades()
        pool = [w for w in self.db.get_game_weapons(self._current_game())
                if not self._blacklisted_weapon(w) and w not in upgrades]
        pool = strip_denied_equipment(self.db, pool)
        pool = gate_offer_pool(self.db, pool, self.run_state, player)
        pool = pool + self._ability_offer_pool(player)
        return pool

    def _ability_offer_pool(self, player=None):
        """This window's view of the shared ability rule — see ability_offer_pool."""
        return ability_offer_pool(self.db, self._current_game(), self.run_state, player)

    def _sprint_offer_ok(self, player=None):
        """Back-compat shim: is any ability offerable to this player."""
        return bool(self._ability_offer_pool(player))

    def _weapon_choice_negatives(self):
        return CONFIG.get('weapon_choice_negatives', True)

    def show_weapon_selection(self):
        weapons = self._game_weapon_pool('player1')
        if len(weapons) < 2:
            QMessageBox.warning(self, "Error", "Not enough weapons available!")
            return

        choices = self._build_weapon_choices(weapons, self._enemy_pool(),
                                             with_enemy=self._weapon_choice_negatives())

        self.pending_player2_selection = False
        self.display_weapon_selection(choices, is_player2=False)
        self.run_state.phase = 'weapon_selection'
        self._sync_save_button()      # this phase allows saving; nothing re-synced it
        self.update_status("Select a weapon for Player 1")

    def _clear_pairs_layout(self):
        """Remove and dispose every widget in the pairs layout."""
        for i in reversed(range(self.pairs_layout.count())):
            widget = self.pairs_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        self.pair_cards = []

    def display_weapon_selection(self, choices, is_player2=False, mode='initial'):
        self._last_weapon_display = (choices, is_player2, mode)  # re-render on options change
        self._last_display = None                                 # weapon screen, not pairs
        self.pairs_container.setUpdatesEnabled(False)
        try:
            self._clear_pairs_layout()
            for choice in choices:
                card = WeaponSelectionCard(choice, self, is_player2, mode)
                self.pairs_layout.addWidget(card)
                self.pair_cards.append(card)
        finally:
            self.pairs_container.setUpdatesEnabled(True)

    # Both rerolls ask for their OWN player's pool, like every other offer path: the
    # ability items are per-player, so a player-less pool hides them for both players
    # once either one has an ability.
    def reroll_weapon_choice_p1(self, choice_id):
        self._reroll_weapon_choice(choice_id, weapon_pool=self._game_weapon_pool('player1'),
                                   player_label=" for Player 1",
                                   with_enemy=self._weapon_choice_negatives())

    def reroll_weapon_choice_p2(self, choice_id):
        self._reroll_weapon_choice(choice_id, weapon_pool=self._game_weapon_pool('player2'),
                                   exclude_weapons={self.run_state.player1_weapon},
                                   player_label=" for Player 2",
                                   with_enemy=self._weapon_choice_negatives())

    def blacklist_weapon_choice(self, weapon, choice_id, player):
        """Initial-selection twin of blacklist_manual_weapon: blacklist, then reroll
        the card through that player's own initial-selection reroll, so the pool the
        replacement comes from is the one this screen offers."""
        label = self.db.weapon_label(weapon)
        if label not in self.run_state.blacklist:
            self.run_state.blacklist.add(label)
            self.update_status(f"Blacklisted weapon: {weapon}")
        if player == 'player2':
            self.reroll_weapon_choice_p2(choice_id)
        else:
            self.reroll_weapon_choice_p1(choice_id)

    def on_weapon_selected(self, choice_id):
        selected = None
        for card in self.pair_cards:
            if hasattr(card, 'pair_data') and card.pair_data['id'] == choice_id:
                selected = card.pair_data
                break
        if not selected:
            return
        self.run_state.set_weapon('player1', selected['weapon'])
        self.run_state.enemy_mod = selected['enemy_mod']
        self._p1_start_enemy = selected.get('enemy_mod')  # remember P1's tied negative
        self.run_state.weapon_selection_made = True
        self.update_weapon_display()
        self.update_status(f"Player 1 selected: {selected['weapon']}")
        self.show_player2_weapon_selection()

    def show_player2_weapon_selection(self):
        # Ask for PLAYER 2's pool: ability offers are per-player, so asking without a
        # player would hide every ability the moment player 1 took one.
        available_weapons = [w for w in self._game_weapon_pool('player2')
                             if w != self.run_state.player1_weapon]
        if len(available_weapons) < 1:
            QMessageBox.warning(self, "Error", "No weapons available for Player 2!")
            return

        choices = self._build_weapon_choices(available_weapons, self._enemy_pool(),
                                             with_enemy=self._weapon_choice_negatives())

        self.pending_player2_selection = True
        self.display_weapon_selection(choices, is_player2=True)
        self.update_status("Select a weapon for Player 2")

    def on_weapon_selected_p2(self, choice_id):
        selected = None
        for card in self.pair_cards:
            if hasattr(card, 'pair_data') and card.pair_data['id'] == choice_id:
                selected = card.pair_data
                break
        if not selected:
            return
        self.run_state.set_weapon('player2', selected['weapon'])
        self.update_weapon_display()
        self.update_status(f"Player 2 selected: {selected['weapon']}")
        # Record the starting weapons + their tied negatives so they're saved.
        p1_enemy = getattr(self, '_p1_start_enemy', None)
        p2_enemy = selected.get('enemy_mod')
        if p1_enemy or p2_enemy:
            self.run_state.rounds.append({
                'player1': {'weapon': self.run_state.player1_weapon, 'mod': None,
                            'gained_weapon': None, 'starting': True},
                'player2': {'weapon': self.run_state.player2_weapon, 'mod': None,
                            'gained_weapon': None, 'starting': True},
                'enemy1': p1_enemy, 'enemy2': p2_enemy,
                'wildcard': None, 'boss1': None, 'boss2': None,
            })
        self._p1_start_enemy = None
        self.run_state.phase = 'player1_turn'
        self.run_state.current_turn = 'player1'
        self.pending_player2_selection = False
        self.clear_pairs()
        self.update_history()
        self._sync_save_button()
        self.generate_btn.setEnabled(True)
        # Don't auto-roll the first effects — wait for the user to Generate.
        self.update_status("Weapons set — press 🔄 GENERATE PAIRS when ready")

    # ---- New Weapon button (#3) — both players draw from the game pool ----
    def _game_at_least(self, min_game):
        return game_at_least(self.db, self._current_game(), min_game)

    def _upgrade_allowed_here(self, weapon):
        return upgrade_allowed_here(self._current_game(), weapon)

    def _anything_offer_pool(self, player):
        """EVERYTHING this player could still be handed: weapons, duals, upgrades,
        equipment and abilities.

        The single place the offer RULES live -- blacklist, already owned, taken by the
        other player, denied equipment, one-ability-per-player. The three buttons are
        filters over this, never pools of their own, so a rule fixed here is fixed for
        all of them. Building a second pool is the recurring bug in this codebase."""
        owned = set(self.run_state.weapons_for(player))
        # Pass the player through: ability offers are per-player, so asking without one
        # makes an ability drop out for BOTH players as soon as either takes one.
        pool = [w for w in self._game_weapon_pool(player) if w not in owned]
        # The button always offers both; the automatic rolls gate them behind the
        # auto_new_weapon_* options. Same rule, one definition.
        pool += unlocked_offer_items(self.db, self._current_game(), owned,
                                     self.run_state.blacklist)
        # The NEW WEAPON button draws from here, not from RunEnhancer._new_weapon_pool
        # (which only feeds the automatic per-pair rolls) — equipment has to be added
        # to BOTH or the button never offers any.
        if has_equipment(self._current_game()) and CONFIG.get('h3_equipment_in_rolls'):
            for e in (self.db.mission_equipment.get(self.run_state.mission_id) or []):
                if e not in owned and not self._blacklisted_weapon(e):
                    pool.append(e)
        pool = strip_denied_equipment(self.db, pool)
        pool = drop_weapons_taken(self.db, pool, self.run_state)
        return gate_offer_pool(self.db, pool, self.run_state, player)

    def _weapon_offer_pool(self, player):
        """Guns only. NEW WEAPON used to hand out equipment and abilities too, which
        made it impossible to ask for a gun; NEW ANYTHING is the button that offers
        the lot now."""
        return [w for w in self._anything_offer_pool(player)
                if not self.db.is_equipment(w) and not ability_of_item(w)]

    def _equipment_offer_pool(self, player):
        """The equipment and ability items this player could still be given.

        Deliberately a FILTER over _weapon_offer_pool rather than a second pool built
        from scratch: every gate that decides what may be offered — blacklist, already
        owned, taken by the other player, the denied-equipment options, the
        one-ability-per-player rule — lives there, and a parallel pool would drift out
        of step with it. This is the recurring bug in this codebase, so the offer rules
        stay in one place and this only narrows what comes out.

        Abilities are included where the game has them: an ability IS the equipment
        slot in Halo 1, so a button that refuses to offer one would be empty there."""
        game = self._current_game()
        pool = [w for w in self._anything_offer_pool(player)
                if self.db.is_equipment(w) or ability_of_item(w)]
        # _weapon_offer_pool only adds equipment when h3_equipment_in_rolls is on --
        # that option governs whether equipment turns up in a WEAPON draw, which is a
        # different question from whether this button may hand one out.
        if has_equipment(game) and not CONFIG.get('h3_equipment_in_rolls'):
            owned = set(self.run_state.weapons_for(player))
            extra = [e for e in (self.db.mission_equipment.get(self.run_state.mission_id) or [])
                     if e not in owned and not self._blacklisted_weapon(e)]
            extra = strip_denied_equipment(self.db, extra)
            extra = drop_weapons_taken(self.db, extra, self.run_state)
            for e in gate_offer_pool(self.db, extra, self.run_state, player):
                if e not in pool:
                    pool.append(e)
        return pool

    def on_new_anything_button(self):
        """Same flow, drawing from EVERYTHING — guns, duals, upgrades, equipment,
        abilities. What NEW WEAPON used to do before it was narrowed to guns."""
        if not (self.run_state.player1_weapon and self.run_state.player2_weapon):
            self.update_status("Choose starting weapons for both players first")
            return
        self._manual_mode = 'anything'
        self._manual_queue = ['player1', 'player2']
        self._manual_results = {}
        self._next_manual_weapon()

    def on_new_equipment_button(self):
        """Same flow as NEW WEAPON, drawing only from the equipment/ability pool."""
        if not (self.run_state.player1_weapon and self.run_state.player2_weapon):
            self.update_status("Choose starting weapons for both players first")
            return
        self._manual_mode = 'equipment'
        self._manual_queue = ['player1', 'player2']
        self._manual_results = {}
        self._next_manual_weapon()

    def _grant_weapon(self, player, weapon):
        """Add a weapon; if it's an upgrade and the player dual-wields the base,
        also grant the dual version of the upgrade (#3)."""
        self.run_state.add_weapon(player, weapon)
        base = weapon_upgrades().get(weapon)
        if base and f"Dual {base}" in self.run_state.weapons_for(player):
            self.run_state.add_weapon(player, f"Dual {weapon}")

    def on_new_weapon_button(self):
        if not (self.run_state.player1_weapon and self.run_state.player2_weapon):
            self.update_status("Choose starting weapons for both players first")
            return
        self._manual_mode = 'weapon'
        self._manual_queue = ['player1', 'player2']
        self._manual_results = {}
        self._next_manual_weapon()

    def _next_manual_weapon(self):
        while self._manual_queue:
            player = self._manual_queue.pop(0)
            if self._show_manual_weapon_selection(player):
                return
        self._finish_manual_weapon()

    _MANUAL_POOLS = {'weapon': '_weapon_offer_pool',
                     'equipment': '_equipment_offer_pool',
                     'anything': '_anything_offer_pool'}
    _MANUAL_LABEL = {'weapon': ('🔫 New weapon', 'weapons'),
                     'equipment': ('🎒 New equipment', 'equipment'),
                     'anything': ('🎁 Something new', 'items')}

    def _manual_pool(self, player):
        mode = getattr(self, '_manual_mode', 'weapon')
        return getattr(self, self._MANUAL_POOLS.get(mode, '_weapon_offer_pool'))(player)

    def _show_manual_weapon_selection(self, player):
        mode = getattr(self, '_manual_mode', 'weapon')
        pool = self._manual_pool(player)
        if not pool:
            who = "Player 1" if player == 'player1' else "Player 2"
            self.update_status("No %s left to offer %s on this level"
                               % (self._MANUAL_LABEL[mode][1], who))
            return False
        # New Weapon cards carry a tied negative unless disabled in CONFIG.
        with_enemy = self._weapon_choice_negatives()
        choices = self._build_weapon_choices(pool, self._enemy_pool(),
                                             count=min(3, len(pool)), with_enemy=with_enemy)
        self.display_weapon_selection(choices, is_player2=(player == 'player2'), mode='add')
        who = "Player 1" if player == 'player1' else "Player 2"
        suffix = " (comes with a negative)" if with_enemy else ""
        icon = self._MANUAL_LABEL[mode][0]
        self.update_status(f"{icon} for {who}: pick one{suffix}")
        return True

    def on_manual_weapon_selected(self, player, choice_id):
        selected = next((c.pair_data for c in self.pair_cards
                         if hasattr(c, 'pair_data') and c.pair_data['id'] == choice_id), None)
        if not selected:
            return
        self._grant_weapon(player, selected['weapon'])
        self._manual_results[player] = {'weapon': selected['weapon'],
                                        'enemy': selected.get('enemy_mod')}
        self.update_weapon_display()
        who = "Player 1" if player == 'player1' else "Player 2"
        kind = ("equipment" if self.db.is_equipment(selected['weapon'])
                else ("ability" if ability_of_item(selected['weapon']) else "weapon"))
        self.update_status(f"{who} gained new {kind}: {selected['weapon']}!")
        self._next_manual_weapon()

    def reroll_manual_weapon(self, choice_id, player):
        # A reroll stays in the mode the draw started in.
        pool = self._manual_pool(player)
        self._reroll_weapon_choice(choice_id, weapon_pool=pool,
                                   exclude_weapons=set(self.run_state.weapons_for(player)),
                                   with_enemy=self._weapon_choice_negatives(),
                                   player_label=f" ({player})")

    def blacklist_manual_weapon(self, weapon, choice_id, player):
        label = self.db.weapon_label(weapon)
        if label not in self.run_state.blacklist:
            self.run_state.blacklist.add(label)
            self.update_status(f"Blacklisted weapon: {weapon}")
        self.reroll_manual_weapon(choice_id, player)

    def _finish_manual_weapon(self):
        # Record the weapon draw (with tied negatives) as a round, then allow save.
        res1 = self._manual_results.get('player1')
        res2 = self._manual_results.get('player2')
        if res1 or res2:
            self.run_state.rounds.append({
                'player1': {'weapon': self.run_state.player1_weapon, 'mod': None,
                            'gained_weapon': res1['weapon'] if res1 else None},
                'player2': {'weapon': self.run_state.player2_weapon, 'mod': None,
                            'gained_weapon': res2['weapon'] if res2 else None},
                'enemy1': res1['enemy'] if res1 else None,
                'enemy2': res2['enemy'] if res2 else None,
                'wildcard': None, 'boss1': None, 'boss2': None,
            })
            self.run_state.phase = 'complete'
            self.run_state.current_turn = 'player1'
            self._sync_save_button()
            self.generate_btn.setEnabled(True)
        self.clear_pairs()
        self.update_history()
        self.update_status("New weapons added (with negatives) — save or generate new pairs")

    def add_weapon_to_blacklist(self, weapon, pair_id=None, mod_type=None):
        """Blacklist a weapon offered inside a generated pair (#1), then reroll it."""
        label = self.db.weapon_label(weapon)
        if label not in self.run_state.blacklist:
            self.run_state.blacklist.add(label)
            self.update_status(f"Blacklisted weapon: {weapon}")
        if pair_id is not None and mod_type is not None:
            self.on_reroll_modifier(pair_id, mod_type)

    # ---- Load ----
    def load_run_state(self, state, path=None):
        self.run_state = state
        # Saving defaults back to the file this run came from (see on_save), and if it
        # came from the shared folder, that is also the file this run writes back to.
        self.loaded_run_path = path or None
        self.shared_run_path = None
        folder = (CONFIG.get('shared_session_dir') or '').strip()
        if path and folder:
            try:
                if Path(path).parent.resolve() == Path(folder).resolve():
                    self.shared_run_path = str(path)
            except Exception:
                pass
        self.enhancer = RunEnhancer(self.db, self.run_state)
        self.update_patch_code_display()   # #8: show the loaded run's own code
        # Sync the Game + Level dropdowns to the loaded mission (no signals).
        game = self.db.get_game_for_mission(self.run_state.mission_id)
        if game:
            gi = self.game_combo.findData(game)
            if gi >= 0:
                self.game_combo.blockSignals(True)
                self.game_combo.setCurrentIndex(gi)
                self.game_combo.blockSignals(False)
        self._fill_mission_combo(game, select_mid=self.run_state.mission_id)
        self.update_weapon_display()
        self.update_history()
        if self.run_state.phase in ('player1_turn', 'player2_turn'):
            self.run_state.weapon_selection_made = True
            # A run's pairs are not saved, so a mid-round file has nothing to show and
            # the cards have to be re-rolled. For a LOCAL save that is the convenience
            # it was written to be. For a run picked up out of the SHARED folder it is
            # actively wrong: the draw is random, so rolling on load hands the partner
            # a different set from the one the other machine is looking at, and it does
            # it silently, before anyone can react. Let them press Generate instead.
            if self.shared_run_path:
                self.update_status("Run loaded from the shared folder — press Generate "
                                   "when you're ready to draw this round's cards.")
                self.generate_btn.setEnabled(True)
            else:
                self.on_generate()
        elif self.run_state.phase == 'complete':
            self.run_state.weapon_selection_made = True
            self.update_history()
            self.update_status("Run loaded - Both players have selected!")
            self._sync_save_button()
            self.generate_btn.setEnabled(True)
        elif self.run_state.phase == 'weapon_selection':
            self.show_weapon_selection()

    # ---- UI Setup ----
    def setup_ui(self):
        self.setWindowTitle(f"🎯 Halo Run Enhancer  v{VERSION}")
        self.setMinimumSize(1400, 900)
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(15)

        header_layout = QHBoxLayout()
        header = QLabel("🎯 HALO RUN ENHANCER")
        header.setStyleSheet("font-size: 28px; font-weight: bold; color: #4CAF50; padding: 10px; border-bottom: 2px solid #1a3a1a;")
        header_layout.addWidget(header)
        ver = QLabel(f"v{VERSION}")
        ver.setStyleSheet("font-size: 14px; color: #6a8a6a; padding: 10px 4px;")
        ver.setAlignment(Qt.AlignBottom)
        header_layout.addWidget(ver)
        header_layout.addStretch()

        combo_style = """
            QComboBox {
                color: #4CAF50; font-size: 16px; font-weight: bold;
                padding: 8px 20px; background-color: #0a1a0a;
                border: 2px solid #2a5a2a; border-radius: 8px;
                min-width: %dpx;
            }
            QComboBox::drop-down { border: none; }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #4CAF50;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1a1a; color: #e0e0e0;
                selection-background-color: #2a5a2a;
                border: 1px solid #2a5a2a;
            }
        """

        # Game selector (own dropdown) — filters the Level list below it.
        self.game_combo = QComboBox()
        self.game_combo.setStyleSheet(combo_style % 150)
        games = self.db.get_games() or ["Halo 1"]
        for g in games:
            self.game_combo.addItem(g, g)
        cur_game = self.db.get_game_for_mission(self.run_state.mission_id) or games[0]
        gi = self.game_combo.findData(cur_game)
        if gi >= 0:
            self.game_combo.setCurrentIndex(gi)
        header_layout.addWidget(self.game_combo)

        self.mission_combo = QComboBox()
        self.mission_combo.setStyleSheet(combo_style % 250)
        self._fill_mission_combo(cur_game, select_mid=self.run_state.mission_id)
        sel_mid = self.mission_combo.currentData()
        if sel_mid:
            self.run_state.mission_id = sel_mid
            self.run_state.mission_name = self.db.mission_enemies[sel_mid]['name']
        self.game_combo.currentIndexChanged.connect(self.on_game_changed)
        self.mission_combo.currentIndexChanged.connect(self.on_mission_changed)
        header_layout.addWidget(self.mission_combo)
        main_layout.addLayout(header_layout)

        weapon_layout = QHBoxLayout()
        p1_group = QGroupBox("PLAYER 1")
        p1_layout = QHBoxLayout(p1_group)
        self.p1_weapon_display = QLabel("No weapon selected")
        self.p1_weapon_display.setStyleSheet("color: #4CAF50; font-size: 14px; font-weight: bold; padding: 5px;")
        p1_layout.addWidget(self.p1_weapon_display)
        p1_change_btn = QPushButton("Change")
        p1_change_btn.setMaximumWidth(80)
        p1_change_btn.clicked.connect(lambda: self.change_weapon('player1'))
        p1_layout.addWidget(p1_change_btn)
        weapon_layout.addWidget(p1_group)

        p2_group = QGroupBox("PLAYER 2")
        p2_layout = QHBoxLayout(p2_group)
        self.p2_weapon_display = QLabel("No weapon selected")
        self.p2_weapon_display.setStyleSheet("color: #2196F3; font-size: 14px; font-weight: bold; padding: 5px;")
        p2_layout.addWidget(self.p2_weapon_display)
        p2_change_btn = QPushButton("Change")
        p2_change_btn.setMaximumWidth(80)
        p2_change_btn.clicked.connect(lambda: self.change_weapon('player2'))
        p2_layout.addWidget(p2_change_btn)
        weapon_layout.addWidget(p2_group)
        weapon_layout.addStretch()
        main_layout.addLayout(weapon_layout)

        button_layout = QHBoxLayout()
        self.generate_btn = QPushButton("🔄 GENERATE PAIRS")
        self.generate_btn.setToolTip("Roll this level's cards for the current player. "
                                     "Each card pairs a benefit with a drawback.")
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a5a2a; color: white; font-weight: bold;
                font-size: 14px; padding: 10px 20px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #3a7a3a; }
        """)
        self.generate_btn.clicked.connect(self.on_generate)
        button_layout.addWidget(self.generate_btn)

        self.new_weapon_btn = QPushButton("🔫 NEW WEAPON")
        self.new_weapon_btn.setToolTip(
            "Draw a new WEAPON for both players — guns, duals and upgrades only. "
            "Equipment and abilities have their own button; NEW ANYTHING offers the lot.")
        self.new_weapon_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a4a2a; color: white; font-weight: bold;
                font-size: 14px; padding: 10px 20px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #4a6a3a; }
        """)
        self.new_weapon_btn.clicked.connect(self.on_new_weapon_button)
        # Sibling of NEW WEAPON, same flow, equipment/ability pool only. Coloured with
        # the equipment scheme so the two read as different draws at a glance.
        self.new_equipment_btn = QPushButton("🎒 NEW EQUIPMENT")
        self.new_equipment_btn.setToolTip(
            "Draw a piece of equipment for both players, from what this level actually "
            "stocks. Same rules as NEW WEAPON — blacklist, already owned, taken by the "
            "other player — just narrowed to equipment. In Halo 1 it offers the "
            "flashlight abilities instead, which are that game's equipment slot.")
        self.new_equipment_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a3a5a; color: white; font-weight: bold;
                font-size: 14px; padding: 10px 20px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #3a4f7a; }
        """)
        self.new_equipment_btn.clicked.connect(self.on_new_equipment_button)
        button_layout.addWidget(self.new_weapon_btn)
        button_layout.addWidget(self.new_equipment_btn)

        self.new_anything_btn = QPushButton("🎁 NEW ANYTHING")
        self.new_anything_btn.setToolTip(
            "Draw from EVERYTHING this level can still hand out — guns, duals, "
            "upgrades, equipment and abilities together. This is what NEW WEAPON did "
            "before it was narrowed to guns.")
        self.new_anything_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a2f5a; color: white; font-weight: bold;
                font-size: 14px; padding: 10px 20px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #63407a; }
        """)
        self.new_anything_btn.clicked.connect(self.on_new_anything_button)
        button_layout.addWidget(self.new_anything_btn)

        self.save_btn = QPushButton("💾 SAVE SELECTION")
        self.save_btn.setToolTip("Write this run (picks, weapons, history, options) to a save file "
                                 "so it can be reloaded from the main menu.")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a3a5a; color: white; font-weight: bold;
                font-size: 14px; padding: 10px 20px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #3a5a7a; }
            QPushButton:disabled { background-color: #444; color: #888; }
        """)
        self.save_btn.clicked.connect(self.on_save)
        self._sync_save_button()
        button_layout.addWidget(self.save_btn)

        self.quicksave_btn = QPushButton("⇄ QUICKSAVE (shared)")
        self.quicksave_btn.setToolTip("Write this run straight into the shared session "
                                      "folder, re-using this run's file there so the "
                                      "folder keeps one file per session. Confirms the "
                                      "name first, and can save under a different one.")
        self.quicksave_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a4a3a; color: white; font-weight: bold;
                font-size: 14px; padding: 10px 20px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #3a6a52; }
            QPushButton:disabled { background-color: #444; color: #888; }
        """)
        self.quicksave_btn.clicked.connect(self.quicksave_shared)
        button_layout.addWidget(self.quicksave_btn)

        self.patch_btn = QPushButton("🛠 PATCH MAP")
        self.patch_btn.setToolTip("Set magnitudes for this run's effects and write them into the level's .map")
        self.patch_btn.setStyleSheet("""
            QPushButton {
                background-color: #5a3a2a; color: white; font-weight: bold;
                font-size: 14px; padding: 10px 20px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #7a4a3a; }
        """)
        self.patch_btn.clicked.connect(self.on_patch_map)
        button_layout.addWidget(self.patch_btn)

        self.options_btn = QPushButton("⚙ OPTIONS")
        self.options_btn.setToolTip("Adjust run options (difficulty, mod pools, wildcards…)")
        self.options_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a; color: white; font-weight: bold;
                font-size: 14px; padding: 10px 20px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #4a4a4a; }
        """)
        self.options_btn.clicked.connect(self.on_options)
        button_layout.addWidget(self.options_btn)

        self.compare_btn = QPushButton("⚖ COMPARE")
        self.compare_btn.setToolTip("Compare two patch logs — what actually differs "
                                    "between your patched map and your co-op partner's")
        self.compare_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a; color: white; font-weight: bold;
                font-size: 14px; padding: 10px 20px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #4a4a4a; }
        """)
        self.compare_btn.clicked.connect(self.on_compare_patches)
        button_layout.addWidget(self.compare_btn)

        self.menu_btn = QPushButton("🏠 MAIN MENU")
        self.menu_btn.setToolTip("Back to the start menu to begin a new run or load a saved one. "
                                 "Unsaved progress in this run is lost.")
        self.menu_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a; color: white; font-weight: bold;
                font-size: 14px; padding: 10px 20px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #4a4a4a; }
        """)
        self.menu_btn.clicked.connect(self.on_main_menu)
        button_layout.addWidget(self.menu_btn)
        button_layout.addStretch()

        # Debug: search halo.json's mods and inject one into the run (far right).
        self.add_mod_btn = QPushButton("🔍 ADD MOD")
        self.add_mod_btn.setToolTip("Debug: search all effects in halo.json and add one to this run")
        self.add_mod_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a3a; color: #a0a0d0; font-weight: bold;
                font-size: 14px; padding: 10px 16px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #3a3a5a; }
        """)
        self.add_mod_btn.clicked.connect(self.on_add_mod_debug)
        self.add_mod_btn.setVisible(bool(CONFIG.get('debug_mode')))
        button_layout.addWidget(self.add_mod_btn)
        main_layout.addLayout(button_layout)

        self.pairs_scroll = QScrollArea()
        self.pairs_scroll.setWidgetResizable(True)
        self.pairs_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #2a2a2a; border-radius: 5px;
                background-color: #0a0a0a;
            }
            QScrollArea > QWidget > QWidget { background-color: #0a0a0a; }
        """)
        self.pairs_container = QWidget()
        self.pairs_container.setStyleSheet("background-color: #0a0a0a;")
        self.pairs_layout = QHBoxLayout(self.pairs_container)
        # Gap between cards and around the row — both adjustable in Options, and both
        # fed into card_metrics() so the cards shrink to keep the row fitting.
        self.pairs_layout.setSpacing(int(CONFIG.get('card_spacing', 20)))
        _m = int(CONFIG.get('card_row_margin', 20))
        self.pairs_layout.setContentsMargins(_m, _m // 2, _m, _m // 2)
        # Top-align cards so short cards don't get centered with dead space above
        # them; each card now sizes to its own content (see PairCard).
        self.pairs_layout.setAlignment(Qt.AlignTop)
        self.pairs_scroll.setWidget(self.pairs_container)
        main_layout.addWidget(self.pairs_scroll, 1)

        history_group = QGroupBox("SELECTION HISTORY")
        history_group.setStyleSheet("QGroupBox { border: 1px solid #2a2a2a; border-radius: 5px; padding: 10px; margin-top: 10px; }")
        history_layout = QVBoxLayout(history_group)
        self.history_text = QTextEdit()
        self.history_text.setReadOnly(True)
        self.history_text.setMaximumHeight(150)
        self.history_text.setStyleSheet("background-color: #1a1a1a; color: #e0e0e0; font-size: 12px;")
        history_layout.addWidget(self.history_text)
        main_layout.addWidget(history_group)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)
        # #8: the last patch code, PERMANENTLY on screen until the next patch
        # replaces it. It used to live only in the patcher’s results box, which
        # is gone the moment that dialog closes — so the one number two players
        # are meant to read out to each other was the one you had to re-patch to
        # see. Added as a permanent widget so it sits at the right-hand end and
        # transient update_status() messages never overwrite it.
        self.patch_code_label = QLabel("")
        self.patch_code_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.patch_code_label.setStyleSheet(
            "color: #8fb8ff; font-family: monospace; font-weight: bold; padding-right: 6px;")
        self.status_bar.addPermanentWidget(self.patch_code_label)
        self.update_patch_code_display()

    # ---- Game, Mission and Weapon Changes ----
    def _fill_mission_combo(self, game, select_mid=None):
        """Populate the Level dropdown with a game's missions (no signals fired)."""
        self.mission_combo.blockSignals(True)
        self.mission_combo.clear()
        missions = self.db.get_missions_for_game(game) or self.db.get_mission_list()
        if not missions:
            missions = [("a10", "The Pillar of Autumn")]
        for mid, name in missions:
            self.mission_combo.addItem(name, mid)
        idx = self.mission_combo.findData(select_mid) if select_mid else -1
        self.mission_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.mission_combo.blockSignals(False)

    def on_game_changed(self):
        game = self.game_combo.currentData()
        self._fill_mission_combo(game)
        mid = self.mission_combo.currentData()
        if not mid:
            return
        self.run_state.mission_id = mid
        self.run_state.mission_name = self.db.mission_enemies[mid]['name']
        if self.run_state.phase == 'weapon_selection':
            # Before weapons are locked in: switch to this game's weapon pool
            # and reroll the initial weapon choice from Player 1.
            self.run_state.set_weapon('player1', None)
            self.run_state.set_weapon('player2', None)
            self.update_weapon_display()
            self.show_weapon_selection()
            self.update_status(f"Game: {game} — pick a weapon from its pool")
        else:
            self._reset_for_new_round(f"Game changed to {game}")

    def on_mission_changed(self):
        mission_id = self.mission_combo.currentData()
        if not mission_id or mission_id == self.run_state.mission_id:
            return
        self.run_state.mission_id = mission_id
        self.run_state.mission_name = self.db.mission_enemies[mission_id]['name']
        if self.run_state.phase == 'weapon_selection':
            # Keep the initial weapon choice; only the level context changed.
            self.update_status(f"Level: {self.run_state.mission_name} — weapon choice kept")
        else:
            self._reset_for_new_round(f"Mission changed to {self.run_state.mission_name}")

    def _reset_for_new_round(self, status_prefix):
        self.run_state.selected_pairs = {'player1': None, 'player2': None}
        self.run_state.phase = 'player1_turn'
        self.run_state.current_turn = 'player1'
        self.run_state.pairs = []
        self.run_state.enemy_mod = None
        self.run_state.wildcard_mod = None
        self.clear_pairs()
        self._sync_save_button()
        self.generate_btn.setEnabled(True)
        self.update_status(f"{status_prefix} - Generate pairs manually")

    def _replace_pick(self, player, old_item, new_item):
        """Swap ONE item in a player's arsenal, in place, keeping every other pick.

        Order matters: the first entry is the primary (what the starting-weapon patch
        writes), so replacing in place is what keeps a mid-list change from promoting
        something else to primary. `set_weapon` cannot be used here -- its contract is
        to replace the whole arsenal with one weapon, which is the bug this fixes.
        """
        rs = self.run_state
        lst = rs.weapons_for(player)
        if old_item not in lst:
            return False
        if new_item is None:
            lst.remove(old_item)
        else:
            lst[lst.index(old_item)] = new_item
        primary = lst[0] if lst else None
        if player == 'player1':
            rs.player1_weapon = primary
        else:
            rs.player2_weapon = primary
        return True

    def change_weapon(self, player):
        """Change or remove ONE of a player's picks.

        Previously this offered a single weapon combo and replaced the player's whole
        arsenal with the choice. Now it asks which pick to act on, so a run that has
        accumulated weapons, upgrades, abilities and equipment keeps all of them.
        """
        rs = self.run_state
        current = list(rs.weapons_for(player))
        if not current:
            # Nothing drafted yet: this is the opening pick, where "replace the lot"
            # and "replace the only one" are the same thing.
            return self._change_first_weapon(player)

        other = rs.player2_weapon if player == 'player1' else rs.player1_weapon

        dialog = QDialog(self)
        dialog.setWindowTitle("Change a pick — %s" % player.upper())
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Which pick do you want to change?"))
        which = QComboBox()
        for w in current:
            kind = ("ability" if is_ability_item(w)
                    else "equipment" if self.db.is_equipment(w) else "weapon")
            which.addItem("%s   (%s)" % (w, kind), w)
        layout.addWidget(which)

        layout.addWidget(QLabel("Replace it with:"))
        repl = QComboBox()
        layout.addWidget(repl)
        note = QLabel("")
        note.setStyleSheet("color: #888; font-size: 11px;")
        note.setWordWrap(True)
        layout.addWidget(note)

        def refill():
            """Offer everything this player could be given, minus what they already
            hold — except the pick being changed, which must stay offerable so the
            list is never empty when the arsenal already covers the pool."""
            repl.clear()
            picked = which.currentData()
            pool = [w for w in self._weapon_offer_pool(player)
                    if w != other and w not in current]
            # The blacklist and per-run gating already applied inside the pool call.
            for w in sorted(pool):
                repl.addItem(w)
            if not pool:
                note.setText("Nothing else is available for this player on this level — "
                             "you can still remove the pick.")
            else:
                note.setText("%d option(s). Only this pick changes; the rest of the "
                             "arsenal is kept." % len(pool))
            repl.setEnabled(bool(pool))
        which.currentIndexChanged.connect(lambda _=0: refill())
        refill()

        row = QHBoxLayout()
        ok_btn = QPushButton("Replace")
        rm_btn = QPushButton("Remove pick")
        rm_btn.setStyleSheet("background-color:#3a2222; color:#e0a0a0;")
        cancel_btn = QPushButton("Cancel")
        row.addStretch()
        row.addWidget(ok_btn)
        row.addWidget(rm_btn)
        row.addWidget(cancel_btn)
        layout.addLayout(row)

        outcome = {}
        ok_btn.clicked.connect(lambda: (outcome.update(action='replace'), dialog.accept()))
        rm_btn.clicked.connect(lambda: (outcome.update(action='remove'), dialog.accept()))
        cancel_btn.clicked.connect(dialog.reject)

        if dialog.exec() != QDialog.Accepted or not outcome:
            return
        old_item = which.currentData()
        if outcome['action'] == 'remove':
            if len(current) == 1 and QMessageBox.question(
                    self, "Remove the only pick",
                    "%s is this player's only pick. Remove it and choose again?"
                    % old_item,
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return
            self._replace_pick(player, old_item, None)
            self.update_status("Removed %s from %s" % (old_item, player.upper()))
        else:
            if not repl.isEnabled() or not repl.currentText():
                return
            new_item = repl.currentText()
            self._replace_pick(player, old_item, new_item)
            self.update_status("%s: %s -> %s" % (player.upper(), old_item, new_item))
        self._after_pick_change(player)

    def _change_first_weapon(self, player):
        """The opening pick, where the player holds nothing yet."""
        pool = [w for w in self._game_weapon_pool(player)]
        other = (self.run_state.player2_weapon if player == 'player1'
                 else self.run_state.player1_weapon)
        pool = [w for w in pool if w != other]
        if not pool:
            QMessageBox.warning(self, "Error", "No weapons available!")
            return
        item, ok = QInputDialog.getItem(self, "Select %s weapon" % player.upper(),
                                        "Weapon:", sorted(pool), 0, False)
        if not ok or not item:
            return
        self.run_state.set_weapon(player, item)
        self._after_pick_change(player, deal=True)

    def _after_pick_change(self, player, deal=False):
        """Shared tail after a manual pick change.

        `deal` is False for an edit to an existing arsenal: swapping one weapon should
        not deal a fresh round of cards on the spot -- that reads as the app making a
        decision you did not ask for, and it costs a reroll. The round in progress IS
        cleared (it no longer matches the arsenal) and Generate is enabled, so the next
        round is drawn when YOU ask for it. The opening pick still flows straight on,
        because there the whole point is to get to the first cards."""
        rs = self.run_state
        self.update_weapon_display()
        rs.selected_pairs = {'player1': None, 'player2': None}
        rs.phase = 'player1_turn'
        rs.current_turn = 'player1'
        rs.pairs = []
        self.clear_pairs()
        self.update_history()
        self._sync_save_button()
        self.generate_btn.setEnabled(True)
        if not deal:
            self.update_status(self.status_label.text() + "  —  press Generate when ready")
            return
        if rs.player1_weapon and rs.player2_weapon:
            self.on_generate()
        else:
            self.show_weapon_selection()

    # ---- Pair Generation ----
    def on_generate(self):
        if not self.run_state.player1_weapon or not self.run_state.player2_weapon:
            self.update_status("Please select weapons for both players first")
            return

        if self.run_state.phase == 'player1_turn':
            player = 'player1'
            turn_text = "Player 1"
            show_p1, show_p2 = True, False
        elif self.run_state.phase == 'player2_turn':
            player = 'player2'
            turn_text = "Player 2"
            show_p1, show_p2 = False, True
        else:
            self.run_state.phase = 'player1_turn'
            self.run_state.current_turn = 'player1'
            self.run_state.selected_pairs = {'player1': None, 'player2': None}
            player = 'player1'
            turn_text = "Player 1"
            show_p1, show_p2 = True, False
            self._sync_save_button()
            self.update_status("Regenerating pairs for Player 1")

        pairs = self.enhancer.generate_pairs(for_player=player)
        self.display_pairs(pairs, show_p1, show_p2)
        self.update_status(f"{turn_text}'s turn - Select a pair")
        self.update_history()
        self._sync_save_button()
        self.generate_btn.setEnabled(True)

    def display_pairs(self, pairs, show_player1=True, show_player2=True):
        self._last_display = (pairs, show_player1, show_player2)  # for re-render on options change
        self._last_weapon_display = None                          # pairs screen, not weapon select
        self.pairs_container.setUpdatesEnabled(False)
        try:
            # Re-read the gaps here, not just at construction, so changing them in
            # Options takes effect on the next render instead of needing a restart.
            self.pairs_layout.setSpacing(int(CONFIG.get('card_spacing', 20)))
            _m = int(CONFIG.get('card_row_margin', 20))
            self.pairs_layout.setContentsMargins(_m, _m // 2, _m, _m // 2)
            self._clear_pairs_layout()
            for pair in pairs:
                card = PairCard(pair, self, show_player1, show_player2)
                self.pairs_layout.addWidget(card)
                self.pair_cards.append(card)
        finally:
            self.pairs_container.setUpdatesEnabled(True)

    def clear_pairs(self):
        self.pairs_container.setUpdatesEnabled(False)
        try:
            self._clear_pairs_layout()
        finally:
            self.pairs_container.setUpdatesEnabled(True)

    def _mid_picking_round(self):
        """True while a card-picking round is on screen and not yet concluded.

        The phase alone is not that test: changing a weapon, changing mission and every
        other reset parks the run in 'player1_turn' with NO cards on screen, which read
        as mid-round while nothing was being picked. A round is only really in progress
        once pairs have been generated, so require both.

        Shared by the button's enabled state and on_save's own guard — they used
        different rules, so after the opening weapon selection the button was live but
        saving still refused with "Both players must select before saving!".
        """
        rs = getattr(self, 'run_state', None)
        return (bool(rs) and rs.phase in ('player1_turn', 'player2_turn')
                and bool(getattr(rs, 'pairs', None)))

    def _sync_save_button(self):
        """Save is available at all times EXCEPT while a card-picking round is in
        progress and not yet concluded. Weapon selection and completed rounds allow it."""
        rs = getattr(self, 'run_state', None)
        self.save_btn.setEnabled(not self._mid_picking_round())
        qb = getattr(self, 'quicksave_btn', None)
        if qb is not None:
            # Quicksave writes a completed run for the partner to pick up, so it needs
            # the same completeness the shared export does. It stays CLICKABLE while
            # the round is unfinished, though: a greyed button with no explanation is
            # a mystery to debug mid-session, and quicksave_shared already refuses
            # politely with the reason. What changes is the tooltip, which says why.
            ready = bool(rs) and rs.phase == 'complete'
            qb.setEnabled(bool(rs))
            qb.setToolTip("Write this run straight into the shared session folder."
                          if ready else
                          "Not yet: both players have to finish this round first "
                          "(the run is in the '%s' phase). Quicksave writes a "
                          "completed run for your partner to pick up."
                          % (getattr(rs, 'phase', '?') if rs else '?'))

    def on_pair_selected(self, pair_id):
        player = self.run_state.current_turn
        if not self.enhancer.select_pair(pair_id, player):
            return
        player_name = "Player 1" if player == 'player1' else "Player 2"
        pair = self.run_state.selected_pairs[player]

        # A new-weapon pair grants a weapon instead of a positive modifier.
        if pair.get('new_weapon'):
            self.run_state.add_weapon(player, pair['new_weapon'])
            self.update_weapon_display()
            self.update_status(f"{player_name} gained a new weapon: {pair['new_weapon']}!")
        else:
            mod = pair['player1_mod'] if player == 'player1' else pair['player2_mod']
            self.update_status(f"{player_name} selected: {mod['name'] if mod else '—'}")

        if player == 'player1':
            self.run_state.phase = 'player2_turn'
            self.run_state.current_turn = 'player2'
        else:
            self.run_state.phase = 'complete'

        if self.run_state.phase == 'complete':
            p1_pair = self.run_state.selected_pairs['player1']
            p2_pair = self.run_state.selected_pairs['player2']
            round_data = {
                'player1': {
                    'weapon': self.run_state.player1_weapon,
                    'mod': p1_pair.get('player1_mod'),
                    'gained_weapon': p1_pair.get('new_weapon')
                },
                'player2': {
                    'weapon': self.run_state.player2_weapon,
                    'mod': p2_pair.get('player2_mod'),
                    'gained_weapon': p2_pair.get('new_weapon')
                },
                'enemy1': p1_pair.get('enemy_mod'),
                'enemy2': p2_pair.get('enemy_mod'),
                # wildcards are rolled independently per player (like enemy1/2 and
                # boss1/2), so record BOTH — otherwise a wildcard picked on player 2's
                # side is dropped from the summary and the patch.
                'wildcard': p1_pair.get('wildcard_mod'),
                'wildcard2': p2_pair.get('wildcard_mod'),
                'boss1': p1_pair.get('boss_mod'),
                'boss2': p2_pair.get('boss_mod'),
                # The Other slot's four kinds each get their own key. Heroes and
                # skulls are new; wildcard/exhaust keep theirs so old runs still load.
                'hero1': p1_pair.get('hero_mod'),
                'hero2': p2_pair.get('hero_mod'),
                'skull1': p1_pair.get('skull_mod'),
                'skull2': p2_pair.get('skull_mod')
            }
            # #5: stamp each picked Exhaust with the mission it belongs to (so it
            # only patches that one map), and grant its picker a no-negative
            # choice next round.
            for pk, pr in (('exhaust1', p1_pair), ('exhaust2', p2_pair)):
                ex = pr.get('exhaust_mod')
                if isinstance(ex, dict):
                    ex = {**ex, '_exhaust_mission': self.run_state.mission_id}
                    self.run_state.free_negative_pending[
                        'player1' if pk == 'exhaust1' else 'player2'] = True
                round_data[pk] = ex
            self.run_state.rounds.append(round_data)
            self._update_special_counters(p1_pair.get('player1_mod'), p2_pair.get('player2_mod'))

            self._sync_save_button()
            self.generate_btn.setEnabled(True)
            self.update_status("Both players have selected! Save or generate new pairs.")
            self.clear_pairs()
        else:
            # Player 1 has picked and the phase moved on, so the save buttons' reasons
            # changed too — nothing else re-synced them on this branch.
            self._sync_save_button()
            self.update_status("Player 2's turn...")
            QTimer.singleShot(150, self.on_generate)

        self.update_history()

    def _update_special_counters(self, p1_mod, p2_mod):
        """After a round: a picked special's counter resets to 0, an unpicked
        one increments by 1 (linear odds). Tracked separately per effect (#3)."""
        specials = self.db.special_names()
        if not specials:
            return
        picked = {m['name'] for m in (p1_mod, p2_mod)
                  if isinstance(m, dict) and m.get('name') in specials}
        for name in specials:
            if name in picked:
                self.run_state.special_counters[name] = 0
            else:
                self.run_state.special_counters[name] = \
                    self.run_state.special_counters.get(name, 1) + 1

    def on_reroll_modifier(self, pair_id, mod_type):
        pair = next((p for p in self.run_state.pairs if p['id'] == pair_id), None)
        if not pair:
            return
        game = self._current_game()
        bl = self.run_state.blacklist
        if mod_type in ('player1', 'player2'):
            if pair.get('new_weapon'):
                # Reroll the offered weapon (level pool minus owned, other offers, blacklist).
                level = self.db.get_level_weapons(self.run_state.mission_id)
                owned = set(self.run_state.weapons_for(mod_type))
                used = {p['new_weapon'] for p in self.run_state.pairs
                        if p is not pair and p.get('new_weapon')}
                pool = [w for w in level
                        if w not in owned and w not in used and not self._blacklisted_weapon(w)] \
                    or [w for w in level if w not in owned and not self._blacklisted_weapon(w)]
                if pool:
                    pair['new_weapon'] = random.choice(pool)
            else:
                mods = self.db.get_player_modifiers_filtered(
                    self.run_state.weapons_for(mod_type), bl, game)
                pair[f'{mod_type}_mod'] = random.choice(mods) if mods else None
        elif mod_type == 'enemy':
            mods = self.db.get_enemy_modifiers_filtered(self.run_state.mission_id, bl, game)
            pair['enemy_mod'] = random.choice(mods) if mods else None
        elif mod_type == 'wildcard':
            pair['wildcard_mod'] = self.db.get_wildcard_modifier_filtered(bl, game)
        elif mod_type == 'exhaust':
            active = self.enhancer._active_negative_names()
            pair['exhaust_mod'] = self.db.get_exhaust_modifier_filtered(active, bl, game)
        elif mod_type in ('boss', 'hero'):
            mid = self.run_state.mission_id
            # A boss reroll stays a boss and a hero reroll stays a hero: they are
            # separate slots now and a reroll must not move a card between them.
            names = (self.db.story_bosses_for(mid) if mod_type == 'boss'
                     else self.db.heroes_for(mid))
            name, boss_mods = (None, [])
            if not boss_mods_removed():
                name, boss_mods = self.db.draw_boss(mid, bl, game, names=names)
            if boss_mods:
                pair[f'{mod_type}_mod'] = make_boss_mod(random.choice(boss_mods), name)
        elif mod_type == 'skull':
            active = self.enhancer._active_negative_names()
            pair['skull_mod'] = self.db.get_skull_modifier_filtered(active, bl, game)
        show_p1 = self.run_state.current_turn == 'player1'
        show_p2 = self.run_state.current_turn == 'player2'
        self.display_pairs(self.run_state.pairs, show_p1, show_p2)
        self.update_status(f"Rerolled {mod_type} in Pair {pair_id}")

    # ---- History & Display ----
    @staticmethod
    def _selected_summary(pair, player, primary_weapon):
        if pair.get('new_weapon'):
            return f"🔫 NEW WEAPON: {pair['new_weapon']}"
        mod = pair.get(f'{player}_mod')
        if mod:
            return f"{mod.get('weapon', primary_weapon)} - {mod['name']}"
        return "—"

    # NOT a @staticmethod, unlike its neighbours here: the generic-tag check needs
    # self.db and the current game. It carried the decorator anyway, which made every
    # call bind the mod to `self` and raise as soon as a round history existed.
    def _enemy_effect_label(self, mod):
        """Round-summary label for an enemy modifier: the effect name plus which
        enemy it was picked for — 'Cover Chance (Elite)' for a specific enemy, or
        'Perception (general)' for a general enemy modifier. 'None' if no mod.

        An effect drafted from one enemy but resolving to a tag several enemies share
        (H2's `char ai\\generic`) is reported as generic, because that is what it
        actually edits — naming the enemy there is misleading."""
        if not isinstance(mod, dict):
            return "None"
        who = mod.get('enemy') or "general"
        if mod.get('enemy') and self.db.is_generic_enemy_mod(mod, self._current_game()):
            who = f"generic, from {mod['enemy']}"
        return f"{mod.get('name', '?')} ({who})"

    @staticmethod
    def _round_summary(pdata):
        if pdata.get('starting'):
            return f"{pdata.get('weapon')} (starting weapon)"
        if pdata.get('gained_weapon'):
            return f"{pdata.get('weapon')} (+🔫 {pdata['gained_weapon']})"
        mod = pdata.get('mod')
        if not mod:
            return f"{pdata.get('weapon')}"
        # Name the weapon (or equipment) the effect ACTUALLY belongs to. pdata['weapon']
        # is the player's current weapon, so an effect drafted for their second weapon
        # was being reported against the first one — which made it impossible to tell
        # what had changed.
        owner = mod.get('weapon') or mod.get('equipment') or pdata.get('weapon')
        return f"{owner} - {mod['name']}"

    def update_history(self):
        text = ""
        p1sel = self.run_state.selected_pairs['player1']
        if p1sel:
            text += f"✅ Player 1 selected: {self._selected_summary(p1sel, 'player1', self.run_state.player1_weapon)}\n"
        else:
            text += "⏳ Player 1: Waiting for selection...\n"

        p2sel = self.run_state.selected_pairs['player2']
        if p2sel:
            text += f"✅ Player 2 selected: {self._selected_summary(p2sel, 'player2', self.run_state.player2_weapon)}\n"
        else:
            text += "⏳ Player 2: Waiting for selection...\n"

        if self.run_state.rounds:
            text += "\n--- Previous Rounds ---\n"
            for i, round_data in enumerate(self.run_state.rounds, 1):
                enemy1 = round_data.get('enemy1')
                enemy2 = round_data.get('enemy2')
                # both players' wildcard slots (deduped if the same one)
                wilds = [w for w in (round_data.get('wildcard'), round_data.get('wildcard2')) if w]
                boss1 = round_data.get('boss1')
                boss2 = round_data.get('boss2')
                text += f"Round {i}: P1: {self._round_summary(round_data['player1'])}, "
                text += f"P2: {self._round_summary(round_data['player2'])}, "
                text += f"Enemies: {self._enemy_effect_label(enemy1)}, {self._enemy_effect_label(enemy2)}"
                if wilds:
                    names = list(dict.fromkeys(w['name'] for w in wilds))
                    text += f", Ally: {', '.join(names)}"
                if boss1 or boss2:
                    text += f", Boss: {boss1['name'] if boss1 else 'None'}, {boss2['name'] if boss2 else 'None'}"
                # Exhausts are one-map negatives and were missing from the summary
                # entirely, so a round could show fewer effects than it actually had.
                exhausts = [e for e in (round_data.get('exhaust1'), round_data.get('exhaust2'))
                            if isinstance(e, dict)]
                if exhausts:
                    names = list(dict.fromkeys(e.get('name', '?') for e in exhausts))
                    text += f", Exhaust: {', '.join(names)}"
                text += "\n"

        self.history_text.setText(text)
        self.update_weapon_display()

    def update_weapon_display(self):
        p1 = ", ".join(self.run_state.player1_weapons) or "No weapon selected"
        p2 = ", ".join(self.run_state.player2_weapons) or "No weapon selected"
        self.p1_weapon_display.setText(f"Player 1: {p1}")
        self.p2_weapon_display.setText(f"Player 2: {p2}")

    def update_status(self, msg):
        self.status_label.setText(msg)

    def set_last_patch_code(self, code, map_path=None, difficulty=None):
        """Record the signature of a patch just applied, and show it.

        A patch that wrote nothing produces no code (see patch_signature); that
        must not wipe the last real one, or a failed re-patch would erase the
        code the partner is still comparing against.
        """
        if not code:
            return
        self.run_state.last_patch = {
            'code': code,
            'map': Path(map_path).name if map_path else None,
            'difficulty': difficulty,
            'when': datetime.now().strftime('%Y-%m-%d %H:%M'),
        }
        self.update_patch_code_display()

    def update_patch_code_display(self):
        """Render run_state.last_patch into the status bar (blank if never patched)."""
        lp = getattr(self.run_state, 'last_patch', None) or {}
        code = lp.get('code')
        if not code:
            self.patch_code_label.setText('')
            self.patch_code_label.setToolTip('')
            return
        where = lp.get('map') or '?'
        self.patch_code_label.setText(f"Patch {code}  ·  {where}")
        self.patch_code_label.setToolTip(
            f"Last patch: {code}\n"
            f"Map: {where}\n"
            f"Difficulty: {lp.get('difficulty') or '?'}\n"
            f"Applied: {lp.get('when') or '?'}\n\n"
            'Same code = same patch. Read it out to your co-op partner; codes only '
            'compare between the same tool version. Stays here until the next patch.')

    @staticmethod
    def _debug_mod_round(label, mod):
        """One mod turned into its own single-effect round, categorized the same
        way the real draw would slot it (weapon -> player1, enemy/skull -> enemy1,
        everything else -> wildcard)."""
        mod = copy.deepcopy(mod)
        round_data = {'player1': {'weapon': None, 'mod': None, 'gained_weapon': None},
                      'player2': {'weapon': None, 'mod': None, 'gained_weapon': None},
                      'enemy1': None, 'enemy2': None, 'wildcard': None,
                      'boss1': None, 'boss2': None, 'debug_added': True}
        if mod.get('weapon') or label.startswith('[Player+'):
            round_data['player1'] = {'weapon': mod.get('weapon'), 'mod': mod, 'gained_weapon': None}
        elif mod.get('enemy') or mod.get('skull') or label.startswith(('[Enemy', '[Skull')):
            round_data['enemy1'] = mod
        else:
            round_data['wildcard'] = mod
        return round_data

    # ---- Save ----
    def on_add_mod_debug(self):
        """Debug helper: search every effect in halo.json and inject the picked one
        into the run as its own round, so it shows up in the patcher."""
        entries = []   # (label, mod)
        for weapon, mods in self.db.weapon_mods.items():
            for mod in mods:
                entries.append((f"[Weapon] {weapon}: {mod['name']}", mod))
        for enemy, mods in self.db.enemy_mods.items():
            for mod in mods:
                entries.append((f"[Enemy] {enemy}: {mod['name']}", mod))
        for boss, mods in self.db.boss_mods.items():
            for mod in mods:
                entries.append((f"[Boss] {boss}: {mod['name']}", mod))
        for pool, kind in ((self.db.positive_pool, 'Player+'), (self.db.negative_pool, 'Enemy-'),
                           (self.db.wildcard_pool, 'Wildcard'), (self.db.skull_pool, 'Skull')):
            for mod in pool:
                entries.append((f"[{kind}] {mod['name']}", mod))

        dlg = QDialog(self)
        dlg.setWindowTitle("🔍 Add mod (debug)")
        dlg.setModal(True)
        dlg.setMinimumSize(520, 480)
        dlg.setStyleSheet("QDialog { background-color:#141414; } QLabel { color:#e0e0e0; } "
                          "QLineEdit { background-color:#1a1a1a; color:#e0e0e0; border:1px solid #3a3a3a; "
                          "padding:5px; border-radius:3px; } "
                          "QListWidget { background-color:#1a1a1a; color:#e0e0e0; border:1px solid #3a3a3a; }")
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel("Type to filter; double-click (or OK) to add the effect to this run:"))
        search = QLineEdit()
        search.setPlaceholderText("e.g. jackal special, pistol magazine…")
        lst = QListWidget()
        for label, _ in entries:
            lst.addItem(label)

        def refilter(text):
            words = text.lower().split()
            for i, (label, _) in enumerate(entries):
                lst.item(i).setHidden(bool(words) and not all(w in label.lower() for w in words))
        search.textChanged.connect(refilter)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        # Add every single mod in halo.json to this run at once, each as its own
        # round -- for exercising the patcher/validator against literally everything,
        # not for normal play. A separate result code keeps it distinct from OK/Cancel.
        add_all_btn = QPushButton(f"➕ Add ALL ({len(entries)})")
        add_all_btn.setToolTip("Add every effect currently in halo.json to this run, "
                               "one per round. For testing the patcher, not for play.")
        ADD_ALL = QDialog.Accepted + 1
        add_all_btn.clicked.connect(lambda: dlg.done(ADD_ALL))
        btns.addButton(add_all_btn, QDialogButtonBox.ActionRole)
        lst.itemDoubleClicked.connect(lambda _: dlg.accept())
        v.addWidget(search)
        v.addWidget(lst, 1)
        v.addWidget(btns)
        search.setFocus()
        result = dlg.exec()
        if result == ADD_ALL:
            if QMessageBox.question(
                    self, "Add every mod?",
                    f"Add all {len(entries)} effects to this run, one per round?\n\n"
                    "This is meant for testing the patcher against everything at once, "
                    "not for a normal run.",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return
            for label, mod in entries:
                self.run_state.rounds.append(self._debug_mod_round(label, mod))
            self.update_history()
            self.update_status(f"(debug) Added all {len(entries)} effects to the run.")
            return
        if result != QDialog.Accepted or lst.currentRow() < 0 or lst.currentItem().isHidden():
            return
        label, mod = entries[lst.currentRow()]
        self.run_state.rounds.append(self._debug_mod_round(label, mod))
        self.update_history()
        self.update_status(f"(debug) Added to run: {label}")

    def on_compare_patches(self):
        """Open the patch comparer, seeded with the map this run is on.

        Kept as a single non-modal instance: it is a reference window you leave open
        while you re-patch and compare again, and a second copy would just be two
        stale views of the same folder."""
        # The log filename is keyed on the MAP basename, which is not always the
        # mission id (ODST's are lowercase/uppercase variants of each other), so ask
        # the same resolver the patcher uses and fall back to the raw id.
        mission = ''
        try:
            import halo_patch
            game = self.db.get_game_for_mission(self.run_state.mission_id)
            folder = CONFIG.get('map_game_folder', {}).get(game, '')
            mission = Path(halo_patch.default_map_path(
                mcc_root(), folder, self.run_state.mission_id)).stem
        except Exception:
            mission = str(getattr(getattr(self, 'run_state', None),
                                  'mission_id', '') or '')
        dlg = getattr(self, '_compare_dlg', None)
        if dlg is None:
            dlg = self._compare_dlg = PatchComparerDialog(self, mission)
        else:
            dlg.default_mission = mission
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def on_options(self):
        """Open the Options dialog. On accept, the new values are written to the
        live CONFIG, persisted as global defaults (settings.json), and snapshotted
        onto the current run so they travel with its save."""
        dlg = OptionsDialog(self)
        if dlg.exec() == QDialog.Accepted:
            for k, v in dlg.values().items():
                CONFIG[k] = v
            save_settings()
            self.run_state.options = {k: CONFIG.get(k) for k in OPTION_KEYS}
            if hasattr(self, 'add_mod_btn'):        # debug tools show/hide live
                self.add_mod_btn.setVisible(bool(CONFIG.get('debug_mode')))
            # Re-render the CURRENT screen (weapon selection or pairs) so appearance
            # options (hide tags/fields, card width) apply immediately.
            if getattr(self, '_last_weapon_display', None) and self.pair_cards:
                self.display_weapon_selection(*self._last_weapon_display)
            elif getattr(self, '_last_display', None) and self.pair_cards:
                self.display_pairs(*self._last_display)
            self.update_status("Options updated.")

    def _run_bundle(self):
        """A run file that is SELF-CONTAINED: the draft plus the magnitudes typed for
        it. Sharing one of these is enough for the other machine to patch identically —
        no separate magnitude_presets.json to copy (and clobber)."""
        data = self.run_state.to_dict()
        data['format'] = RUN_FILE_MARKER    # tag it so loading can validate the file
        mags = run_magnitudes(self.run_state.rounds, self.run_state.mission_id)
        if mags:
            data['magnitudes'] = mags
        return data

    def _shared_run_path(self):
        """The file in the shared folder that IS this run, if we know it — either one
        loaded from there or one already written for it. None if the run has no file
        there yet, or the folder isn't configured."""
        folder = (CONFIG.get('shared_session_dir') or '').strip()
        if not folder:
            return None
        known = getattr(self, 'shared_run_path', None) or getattr(self, 'loaded_run_path', None)
        if not known:
            return None
        try:
            p = Path(known)
            # Only counts if it actually lives in the shared folder.
            return p if p.parent.resolve() == Path(folder).resolve() else None
        except Exception:
            return None

    def _default_shared_name(self):
        mission = self.run_state.mission_id or 'run'
        return f"session_{mission}_{datetime.now():%Y-%m-%d_%H-%M-%S}.run"

    def export_shared_session(self, quiet=True):
        """Drop the current run into the shared session folder, if one is configured.
        Called after a patch so the other machine can pick it up with one click —
        point this at a cloud-synced folder and the transfer happens by itself.

        Writes back to the SAME file for the rest of the run: a session handed back and
        forth used to leave one timestamped file per patch, so the folder filled up and
        "the newest one" got harder to trust."""
        folder = (CONFIG.get('shared_session_dir') or '').strip()
        if not folder or self.run_state.phase != 'complete':
            return None
        try:
            d = Path(folder)
            d.mkdir(parents=True, exist_ok=True)
            path = self._shared_run_path() or (d / self._default_shared_name())
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self._run_bundle(), f, indent=2, ensure_ascii=False)
            self.shared_run_path = str(path)
            self.update_status(f"Shared session written: {path.name}")
            return path
        except Exception as e:
            if not quiet:
                QMessageBox.warning(self, "Shared folder",
                                    f"Couldn't write the shared session:\n{e}")
            return None

    def quicksave_shared(self):
        """#9: one-press save into the shared folder, confirming the name first.

        Re-uses this run's file so the folder keeps one file per session, but always
        says which file it is and offers a different name — silently overwriting the
        partner's file would be the worse failure."""
        folder = (CONFIG.get('shared_session_dir') or '').strip()
        if not folder:
            QMessageBox.information(self, "No shared folder",
                                    "Set a shared session folder in Options first "
                                    "(point both machines at the same synced folder).")
            return None
        if self.run_state.phase != 'complete':
            QMessageBox.warning(self, "Not Complete",
                                "Both players must select before saving!")
            return None
        existing = self._shared_run_path()
        name = existing.name if existing else self._default_shared_name()
        box = QMessageBox(self)
        box.setWindowTitle("Quicksave to shared folder")
        box.setText(f"Save to {name}?")
        box.setInformativeText(("This overwrites the run already there."
                                if existing else "This creates a new file.")
                               + f"\n\n{folder}")
        save_b = box.addButton("Save", QMessageBox.AcceptRole)
        rename_b = box.addButton("Save as…", QMessageBox.ActionRole)
        box.addButton("Cancel", QMessageBox.RejectRole)
        box.setDefaultButton(save_b)
        box.exec()
        clicked = box.clickedButton()
        if clicked is rename_b:
            chosen, _ = QFileDialog.getSaveFileName(
                self, "Save run to the shared folder",
                str(Path(folder) / name), "Halo Run (*.run)")
            if not chosen:
                return None
            target = Path(chosen)
        elif clicked is save_b:
            target = existing or (Path(folder) / name)
        else:
            return None
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, 'w', encoding='utf-8') as f:
                json.dump(self._run_bundle(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(self, "Shared folder", f"Couldn't write it:\n{e}")
            return None
        # Later saves (and the post-patch autosave) follow this file.
        self.shared_run_path = str(target)
        self.loaded_run_path = str(target)
        self.update_status(f"✅ Quicksaved to {target.name}")
        return target

    def on_save(self):
        # Same rule the button uses. Demanding 'complete' here refused every save the
        # button offered outside a finished round — including right after the opening
        # weapon selection, which is exactly when a run is worth saving.
        if self._mid_picking_round():
            QMessageBox.warning(self, "Round in progress",
                                "Finish this picking round before saving — both players "
                                "need to choose a card first.")
            return

        selections_dir = app_data_dir() / "selections"
        selections_dir.mkdir(exist_ok=True)

        save_data = self._run_bundle()
        # Default to the file this run was loaded from, so passing a session back and
        # forth keeps ONE file per run instead of a new timestamped one every round.
        # A fresh run still gets a timestamped name.
        prev = getattr(self, 'loaded_run_path', None)
        if prev:
            default_path = prev
        else:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            default_path = str(selections_dir / f"selection_{timestamp}.run")
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Run", default_path, "Halo Run (*.run)"
        )
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            # Subsequent saves follow the file the user actually chose.
            self.loaded_run_path = file_path
            self.update_status(f"✅ Selection saved to {file_path}")
            # Name the magnitude count outright: the run file carrying its own
            # magnitudes is the whole reason a shared save reproduces the same
            # patch, and "did they make it in?" was otherwise unanswerable
            # without opening the JSON.
            n_mag = len(save_data.get("magnitudes") or {})
            mag_line = (f"\n\n{n_mag} magnitude(s) travel with it."
                        if n_mag else
                        "\n\nNo magnitudes are stored for this run\u2019s effects "
                        "yet — open Patch Map and type some, or the other "
                        "machine starts from blank fields.")
            QMessageBox.information(self, "Saved!",
                                    f"Selection saved to:\n{file_path}{mag_line}")

    # ---- Map patching (feature a) ----
    def _refresh_mod_definition(self, mod):
        """A saved/loaded run embeds a full snapshot of each mod's definition
        (tag/field/targets/...) as it was AT ROLL TIME. If halo.json has since
        changed — a tag corrected, converted to a per-game dict, a target
        renamed — that snapshot goes stale: the frozen (often H1-only) tag
        never picks up the fix, and patching an old run against H2 reports
        "not present in this map" for every affected effect, forever. Look
        the mod up again by name in the CURRENT database and overlay its
        patch-relevant fields in place, so patching always uses live data.
        If the effect itself was renamed (see EFFECT_RENAMES), the name-based
        lookup is retried under the new name, and 'name' is updated too.

        The overlaid values are DEEP-COPIED: the caller (on_patch_map) later
        resolves per-game `field`/`block`/`nth` dicts to the active game IN
        PLACE, so handing out references to the shared DB objects would collapse
        their per-game dicts permanently after the first patch — a Halo 1 patch
        would then leave only 'Triggers'/nth 0 behind and a later Halo 2 patch
        of the same effect would fail to find block 'Barrels' ("field?")."""
        def find_by_name(name):
            if mod.get('equipment'):
                key = self.db.resolve_equipment(mod['equipment'])
                return next((m for m in self.db.equipment_mods.get(key, [])
                            if m['name'] == name), None)
            if mod.get('weapon'):
                return next((m for m in self.db.weapon_mods.get(mod['weapon'], [])
                            if m['name'] == name), None)
            if mod.get('enemy'):
                pool = self.db.enemy_mods.get(mod['enemy']) or self.db.boss_mods.get(mod['enemy'], [])
                return next((m for m in pool if m['name'] == name), None)
            # skull_pool included, or a picked skull looks removed-from-halo.json on
            # reload and the patcher warns about a snapshot that's actually current.
            for pool in (self.db.positive_pool, self.db.negative_pool,
                         self.db.wildcard_pool, self.db.skull_pool):
                found = next((m for m in pool if m['name'] == name), None)
                if found:
                    return found
            return None

        name = mod.get('name')
        fresh = find_by_name(name)
        renamed_to = None
        if not fresh:
            renamed_to = EFFECT_RENAMES.get(name)
            if renamed_to:
                fresh = find_by_name(renamed_to)
        if fresh:
            mod.pop('_missing_in_db', None)
            for key in ('name', 'tag', 'field', 'targets', 'special', 'dual_only', 'desc',
                        'desc_overrides', 'debug_desc', 'skull',
                        'harder_when', 'easier_when',
                        'init_defaults', 'games'):
                if key in fresh:
                    mod[key] = copy.deepcopy(fresh[key])
        else:
            # The effect no longer exists in halo.json (removed/renamed away). Keep the
            # frozen snapshot but flag it so the patcher can warn.
            mod['_missing_in_db'] = True

    @staticmethod
    def _combine_heretic_tag(tag):
        """Given a resolved char tag for the Heretic Leader or his hologram, return
        a multi-tag that targets BOTH (dedup class prefix)."""
        cls = tag.split(' ', 1)[0]
        base = "objects\\characters\\heretic\\ai\\"
        return f"{cls} {base}heretic_leader & {base}heretic_leader_hologram"

    def on_patch_map(self):
        try:
            import halo_patch
        except Exception as e:
            QMessageBox.critical(self, "Patching unavailable",
                                 f"Could not load the map-patching modules:\n{e}")
            return
        game = self._current_game()
        games = self.db.get_games()
        # Resolve any per-game dict values to the active game's string so they're
        # hashable/patchable. An effect's `tag`, top-level `field`, and each
        # target's `field`/`block` (and `targets` itself) may carry
        # {"Halo 1": ..., "Halo 2": ...}. Resolve on a deep copy so the live run
        # state's per-game dicts aren't collapsed to one game — that would break
        # re-patching for the other game and corrupt a subsequently saved run.
        rounds = copy.deepcopy(self.run_state.rounds or [])
        for rd in rounds:
            slots = [(rd.get('player1') or {}).get('mod'), (rd.get('player2') or {}).get('mod'),
                     rd.get('enemy1'), rd.get('enemy2'),
                     rd.get('wildcard'), rd.get('wildcard2'),
                     rd.get('boss1'), rd.get('boss2'),
                     rd.get('hero1'), rd.get('hero2'),
                     rd.get('skull1'), rd.get('skull2'),
                     rd.get('exhaust1'), rd.get('exhaust2')]
            for mod in slots:
                if not isinstance(mod, dict):
                    continue
                self._refresh_mod_definition(mod)
                if not self.db._game_ok(mod, game):
                    # A mod-level game filter (e.g. "game": "Halo 1") now excludes the
                    # WHOLE effect from patching the other game, not just its targets.
                    mod['_game_excluded'] = True
                    continue
                if _is_absent_flood_mod(mod, game):
                    # ODST and Reach field no Flood, but ship (ODST) or resolve
                    # (Reach, via the shared cards) enough of their tags that the
                    # cards patch cleanly and do nothing. Debug option, default on.
                    mod['_game_excluded'] = True
                    continue
                if CONFIG.get('ignore_elite_in_h3') and _is_allied_elite_mod(mod, game):
                    # From Halo 3 on the Elites are allies (and ODST fields none at
                    # all) — skip Elite enemy effects there by default (option in the
                    # run settings). ODST inherits Halo 3's cards, so it has to be
                    # covered by the same switch, and a HERO Elite (the spec-ops
                    # commander) is stamped with `boss`, not `enemy`, so matching only
                    # on `enemy` let every Elite hero card straight through.
                    mod['_game_excluded'] = True
                    continue
                # Flagged BEFORE the tag is resolved, since genericness is decided per
                # game from the unresolved per-game tag. collect_effects then files it
                # under the general group instead of the enemy it was drafted from —
                # which is what it actually edits, and stops two such picks from
                # different enemies stacking under whichever came first.
                if self.db.is_generic_enemy_mod(mod, game):
                    mod['_generic_target'] = True
                for c in mod.get('constraints') or []:
                    for key in ('field', 'of', 'block', 'index'):
                        if isinstance(c.get(key), dict):
                            c[key] = resolve_gamed(c[key], game, games)
                for key in ('tag', 'field', 'harder_when', 'easier_when', 'init_defaults'):
                    if isinstance(mod.get(key), dict) and _is_gamed(mod[key], games):
                        mod[key] = resolve_gamed(mod[key], game, games)
                # Boss option: fold the Heretic Leader and his holograms into one
                # target so a single boss card tunes both (fields resolve on
                # whichever tag holds them).
                if (CONFIG.get('combine_heretic_hologram') and mod.get('boss') == 'Heretic Leader'
                        and isinstance(mod.get('tag'), str) and 'heretic_leader' in mod['tag']):
                    mod['tag'] = self._combine_heretic_tag(mod['tag'])
                if isinstance(mod.get('targets'), dict):
                    mod['targets'] = resolve_gamed(mod['targets'], game, games) or []
                # A target must be a dict. halo.json once carried bare strings here (a
                # game name appended to `targets` instead of `game`), and every consumer
                # below calls t.get(), so one typo took the whole patch dialog down with
                # an AttributeError. Drop them rather than trusting the file.
                mod['targets'] = [t for t in (mod.get('targets') or [])
                                  if isinstance(t, dict)]
                for t in mod.get('targets') or []:
                    for key in ('field', 'block', 'negate', 'nth', 'index', 'offset',
                                'zero_is', 'tag'):
                        if isinstance(t.get(key), dict):
                            t[key] = resolve_gamed(t[key], game, games)
                # A target may be limited to specific games (e.g. the derived
                # H2 'Rounds Total Maximum' row has no H1 counterpart), and a
                # per-game field/block that has no entry for this game now
                # resolves to None (see resolve_gamed) — drop such targets too
                # rather than ever calling plugin.find() with a None field.
                mod['targets'] = [t for t in (mod.get('targets') or [])
                                  if target_applies(t, game)
                                  and t.get('field') is not None]
        # Bosses that this mission can't field are dropped: their edits couldn't do
        # anything here, and they made the list harder to read.
        effects = halo_patch.collect_effects(
            rounds, self.run_state.mission_id,
            valid_bosses=set(self.db.bosses_for(self.run_state.mission_id)))
        if not effects:
            QMessageBox.information(self, "No effects yet",
                                    "Select some effects first — there's nothing to patch.")
            return
        subdirs = CONFIG.get('plugin_subdirs_by_game', {}).get(game, [])
        game_folder = CONFIG.get('map_game_folder', {}).get(game, '')
        map_path = halo_patch.default_map_path(mcc_root(), game_folder, self.run_state.mission_id)
        presets_path = str(app_data_dir() / "magnitude_presets.json")
        # Building the dialog reads the (possibly large, ~100 MB) H2 source map,
        # which can take a couple of seconds — show a wait cursor meanwhile.
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            dlg = MagnitudeEditorDialog(self, effects, subdirs, map_path, presets_path,
                                        CONFIG.get('target_difficulty', 'Normal'), game=game,
                                        map_subdir=game_folder, mission_id=self.run_state.mission_id)
        finally:
            QApplication.restoreOverrideCursor()
        dlg.exec()

    def add_to_blacklist(self, mod_data, source, pair_id=None, mod_type=None):
        label = self.db.get_mod_label(mod_data, source)
        if label in self.run_state.blacklist:
            return
        self.run_state.blacklist.add(label)
        self.update_status(f"Blacklisted: {label}")
        
        # Single-reroll behavior: only reroll the specific modifier
        if pair_id is not None and mod_type is not None:
            self.on_reroll_modifier(pair_id, mod_type)
        elif self.run_state.phase == 'weapon_selection':
            # Stay on the CURRENT player's weapon selection — re-showing the P1
            # screen here was resetting Player 2's turn back to Player 1.
            if getattr(self, 'pending_player2_selection', False):
                self.show_player2_weapon_selection()
            else:
                self.show_weapon_selection()
        else:
            self.on_generate()
        
class RunEnhancer:
    def __init__(self, db, run_state):
        self.db = db
        self.run_state = run_state

    def _new_weapon_pool(self, player):
        owned = set(self.run_state.weapons_for(player))
        bl = self.run_state.blacklist
        pool = list(self.db.get_level_weapons(self.run_state.mission_id))
        # New option: H3 equipment can turn up in a New Weapon draw too. Equipment
        # has no weapon mods of its own (get_weapon_modifiers degrades to []), so a
        # picked piece just grants the item, same as a weapon with no mods would.
        game = self.db.get_game_for_mission(self.run_state.mission_id)
        if has_equipment(game) and CONFIG.get('h3_equipment_in_rolls'):
            pool += list(self.db.mission_equipment.get(self.run_state.mission_id) or [])
        # Duals and upgrades: the New Weapon BUTTON has always offered these, the
        # automatic rolls never did. Opt in per kind, so an existing run's rolls keep
        # behaving as before unless the option is turned on.
        pool += unlocked_offer_items(self.db, game, owned, bl,
                                     duals=bool(CONFIG.get('auto_new_weapon_duals')),
                                     upgrades=bool(CONFIG.get('auto_new_weapon_upgrades')))
        pool = [w for w in pool if w not in owned and self.db.weapon_label(w) not in bl]
        pool = strip_denied_equipment(self.db, pool)
        # The automatic rolls do not go through _build_weapon_choices, so they need the
        # uniqueness rule applied here or player 2 keeps drawing player 1's weapons.
        pool = drop_weapons_taken(self.db, pool, self.run_state)
        pool = gate_offer_pool(self.db, pool, self.run_state, player)
        # Abilities last: they are their own gate (ability_offer_pool already checks
        # the sprint feature, per-player ownership and the one-per-run pair), and they
        # must not be filtered by the equipment/grenade gates above.
        if CONFIG.get('auto_new_weapon_abilities'):
            pool += [w for w in ability_offer_pool(self.db, game, self.run_state, player)
                     if w not in owned and self.db.weapon_label(w) not in bl]
        return pool

    def _draw_other(self, mid, game, bl, active_neg):
        """The Other slot: one card from Hero / Exhaust / Skull / Ally, or None.

        Two steps, and the order is the point. First whether this pair gets an Other
        card at all (`other_chance`), then WHICH kind, by relative weight. Rolling the
        kind second means the four compete with each other: raising the Skull weight
        trades skulls against the other three, where the old independent per-kind
        chances traded them against nothing and quietly changed how often a pair had a
        third card at all.

        A kind drops out of the roll when it is switched off OR has nothing to give on
        this level — no hero here, every skull already active, no unused negative left
        for an Exhaust. The remaining weights then share it out, so turning three kinds
        off makes the fourth reliable rather than making the slot mostly empty.

        Returns (kind, mod) or (None, None).
        """
        if random.random() >= (CONFIG.get('other_chance', 0.35) or 0):
            return None, None
        weights = CONFIG.get('other_weights') or {}
        # Each entry: kind -> a zero-arg draw. Called only if the kind wins the roll,
        # so an expensive draw is not paid for on every pair — except where knowing
        # whether it CAN give anything is the availability test itself.
        heroes = self.db.heroes_for(mid) if CONFIG.get('other_hero_enabled', True) else []
        candidates = []
        if heroes and not boss_mods_removed():
            candidates.append(('hero', float(weights.get('hero', 1.0) or 0)))
        if CONFIG.get('other_exhaust_enabled', True):
            candidates.append(('exhaust', float(weights.get('exhaust', 1.0) or 0)))
        if CONFIG.get('other_skull_enabled', True):
            candidates.append(('skull', float(weights.get('skull', 1.0) or 0)))
        if CONFIG.get('other_ally_enabled', True):
            candidates.append(('ally', float(weights.get('ally', 1.0) or 0)))
        candidates = [(k, w) for k, w in candidates if w > 0]
        # Draw, and if the winning kind turns out to have nothing left, drop it and
        # roll again among the rest rather than returning an empty slot.
        while candidates:
            kinds = [k for k, _ in candidates]
            picked = random.choices(kinds, weights=[w for _, w in candidates], k=1)[0]
            mod = None
            if picked == 'hero':
                name, pool = self.db.draw_boss(mid, bl, game, names=heroes)
                if pool:
                    mod = make_boss_mod(random.choice(pool), name)
            elif picked == 'exhaust':
                mod = self.db.get_exhaust_modifier_filtered(active_neg, bl, game)
            elif picked == 'skull':
                mod = self.db.get_skull_modifier_filtered(active_neg, bl, game)
            elif picked == 'ally':
                mod = self.db.get_wildcard_modifier_filtered(bl, game)
            if mod is not None:
                return picked, mod
            candidates = [(k, w) for k, w in candidates if k != picked]
        return None, None

    def _weighted_pick(self, mods):
        """Pick a player mod. A special effect's weight equals its counter =
        rounds since it was last picked (linear; starts at 1, 0 right after a
        pick so it's suppressed for one round). Everything else is weight 1."""
        if not mods:
            return None
        # special_rate_factor (~0.67) trims how often special effects surface —
        # their escalating counter weight is scaled down relative to normal mods.
        sf = CONFIG.get('special_rate_factor', 0.67)
        weights = [self.run_state.special_counters.get(m['name'], 1) * sf if m.get('special') else 1
                   for m in mods]
        if sum(weights) <= 0:                 # degenerate guard
            weights = [1] * len(mods)
        return random.choices(mods, weights=weights, k=1)[0]

    def generate_pairs(self, for_player='player1'):
        mid = self.run_state.mission_id
        game = self.db.get_game_for_mission(mid)
        bl = self.run_state.blacklist
        pmods = self.db.get_player_modifiers_filtered(self.run_state.weapons_for(for_player), bl, game)
        enemy_mods = self.db.get_enemy_modifiers_filtered(mid, bl, game)
        wpool = self._new_weapon_pool(for_player)

        # A level with a named STORY fight gets a guaranteed Boss card on every pair.
        # Heroes no longer count here — they are drawn from the Other slot — so a
        # Chieftain level is a normal level as far as this is concerned.
        has_boss = self.db.mission_has_story_boss(mid) and not boss_mods_removed()
        # Drawn per pair below rather than once for the level: on a map with several
        # heroes each card picks its own, and player 2 is not tied to player 1's.

        # #4: roll each of the 3 pairs independently for "new weapon" status.
        # Player 1 sets the count; Player 2 is guaranteed the SAME count.
        chance = CONFIG.get('new_weapon_chance', 0) or 0
        if for_player == 'player1':
            flags = [bool(wpool) and random.random() < chance for _ in range(3)]
            self.run_state.new_weapon_count = sum(flags)
        else:
            count = min(self.run_state.new_weapon_count, 3) if wpool else 0
            chosen = set(random.sample(range(3), count)) if count else set()
            flags = [i in chosen for i in range(3)]

        # Distinct weapons for the new-weapon pairs where the pool allows.
        n_new = sum(flags)
        if n_new and wpool:
            offered = (random.sample(wpool, n_new) if len(wpool) >= n_new
                       else [random.choice(wpool) for _ in range(n_new)])
        else:
            offered = []

        # #5: exhausts draw from negatives not already active, so there's never
        # an overlap to unwind. Recomputed per generate (active set is stable
        # across this call's three pairs).
        active_neg = self._active_negative_names()

        pairs = []
        wi = 0
        for i in range(3):
            enemy_choice = random.choice(enemy_mods) if enemy_mods else None
            new_weapon = None
            p1_choice = p2_choice = None
            wildcard = exhaust = skull = hero = boss_mod = None
            # The Boss slot is the guaranteed card on a level with a named STORY
            # fight, and nothing else competes for it. Heroes used to sit here and
            # suppressed the third slot entirely on any level that fielded one; they
            # are drawn from the Other slot now, so a Chieftain level still rolls
            # Exhausts, Skulls and Allies.
            if has_boss:
                _bn, _bp = self.db.draw_boss(mid, bl, game,
                                             names=self.db.story_bosses_for(mid))
                if _bp:
                    boss_mod = make_boss_mod(random.choice(_bp), _bn)
            if flags[i] and wi < len(offered):
                new_weapon = offered[wi]
                wi += 1
            else:
                choice = self._weighted_pick(pmods)
                if for_player == 'player1':
                    p1_choice = choice
                else:
                    p2_choice = choice
            # The Other slot is rolled for EVERY pair, including a new-weapon one: it
            # is its own slot now, not the leftover of the player card.
            kind, other = self._draw_other(mid, game, bl, active_neg)
            if kind == 'hero':
                hero = other
            elif kind == 'exhaust':
                exhaust = other
            elif kind == 'skull':
                skull = other
                # A skull is a whole-map rule, so the same one twice does nothing;
                # keep it out of the remaining pairs' draws.
                active_neg = set(active_neg) | {skull.get('name')}
            elif kind == 'ally':
                wildcard = other
            pairs.append({
                'id': i + 1,
                'player1_mod': p1_choice,
                'player2_mod': p2_choice,
                'enemy_mod': enemy_choice,
                # `wildcard_mod` keeps its key: Ally is a RENAME of what the player
                # sees, and changing the stored key would break every saved run.
                'wildcard_mod': wildcard,
                'boss_mod': boss_mod,
                'hero_mod': hero,
                'skull_mod': skull,
                'exhaust_mod': exhaust,
                'new_weapon': new_weapon,
                'no_negative': False,
                'selected_by': None
            })
        # #5: compensation — if this player is owed a no-negative choice (they
        # picked an Exhaust last round), strip the enemy card from one pair.
        if self.run_state.free_negative_pending.get(for_player):
            idx = random.randrange(len(pairs))
            pairs[idx]['enemy_mod'] = None
            pairs[idx]['no_negative'] = True
            self.run_state.free_negative_pending[for_player] = False
        self.run_state.pairs = pairs
        self.run_state.current_turn = for_player
        return pairs

    def _active_negative_names(self):
        """Names of negatives already active this run — every enemy card, every SKULL,
        plus Exhausts still bound to the current mission. Keeps a fresh Exhaust or
        Skull from duplicating something already in force.

        Skulls have to be listed explicitly. They used to ride in the enemy slot, so
        `enemy1/2` caught them for free; moving them to their own slot took them out of
        this set and the same skull could be drafted again and again. A skull is a
        whole-map rule that lasts the REST OF THE RUN — unlike an Exhaust, nothing ever
        expires it — so drawing it twice is pure waste."""
        mid = self.run_state.mission_id
        names = set()
        for rd in self.run_state.rounds:
            for k in ('enemy1', 'enemy2', 'skull1', 'skull2'):
                m = rd.get(k)
                if isinstance(m, dict):
                    names.add(m.get('name'))
            for k in ('exhaust1', 'exhaust2'):
                m = rd.get(k)
                if isinstance(m, dict) and m.get('_exhaust_mission') == mid:
                    names.add(m.get('name'))
        return names

    def select_pair(self, pair_id, player):
        for pair in self.run_state.pairs:
            if pair['id'] == pair_id:
                pair['selected_by'] = player
                self.run_state.selected_pairs[player] = pair
                return True
        return False

def check_dependencies():
    """Return a list of human-readable problems with the runtime environment
    (missing data files / Assembly plugins). Empty list means all good.

    Warn-and-continue: only map PATCHING needs the Assembly plugins (they resolve
    field name -> byte offset); rolling and drafting a run work without them.
    Call after load_settings() so a user-configured assembly_plugins_dir is seen."""
    problems = []
    # 1. halo.json — the modifier database (bundled; a clone always has it).
    hj = Path(resource_path('halo.json'))
    if not hj.is_file():
        problems.append(f"halo.json (the modifier database) was not found at {hj}.")
    # 2. Assembly plugin folder — an EXTERNAL dependency, not bundled. Required to
    #    patch maps; ships with Assembly/HCEEK and is set via assembly_plugins_dir.
    root = CONFIG.get('assembly_plugins_dir')
    subdirs = CONFIG.get('plugin_subdirs_by_game', {})
    expected = sorted({s for subs in subdirs.values() for s in subs})
    if not root or not Path(root).is_dir():
        problems.append(
            f"Assembly plugins folder not found (assembly_plugins_dir = {root!r}).\n"
            "  Map patching needs Assembly's 'Plugins' directory. Install Assembly / "
            "HCEEK and set the folder in Options. Rolling and drafting still work.")
    elif not any((Path(root) / sub).is_dir() and any((Path(root) / sub).glob('*.xml'))
                 for sub in expected):
        problems.append(
            f"Assembly plugins folder {root!r} has none of the expected game "
            f"subfolders ({', '.join(expected)}) with plugin .xml files.\n"
            "  Map patching will not be able to resolve fields.")
    return problems


def main():
    # In a windowed build sys.stdout/err are None; guard the diagnostic prints.
    if sys.stdout is None:
        sys.stdout = _NullWriter()
    if sys.stderr is None:
        sys.stderr = _NullWriter()
    # Diagnostics print check marks and arrows. A real console renders them, but a
    # REDIRECTED stream falls back to the locale encoding (cp1252 here) and raises
    # UnicodeEncodeError mid-print -- which load_data catches as "Error loading
    # data", leaving every pool empty. Never let the log's charset break the app.
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    load_settings()
    app = QApplication(sys.argv)
    # Stop the wheel from changing spin-box values unless the field is focused.
    app._wheel_guard = _WheelGuard()
    app.installEventFilter(app._wheel_guard)
    app.setStyle('Fusion')
    app.setStyleSheet("""
        QMainWindow, QWidget { background-color: #0a0a0a; }
        QLabel { color: #e0e0e0; }
        QPushButton { color: #e0e0e0; }
        QComboBox { background-color: #1a1a1a; color: #e0e0e0; border: 1px solid #3a3a3a; padding: 5px; border-radius: 3px; }
        QComboBox::drop-down { border: none; }
        QComboBox QAbstractItemView { background-color: #1a1a1a; color: #e0e0e0; selection-background-color: #2a5a2a; border: 1px solid #2a5a2a; }
        /* Give dropdown rows real height so a short list isn't squeezed into a
           scrolling sliver — the popup then sizes to fit its options. */
        QComboBox QAbstractItemView::item { min-height: 30px; padding: 3px 6px; }
        /* Spin boxes need a BASE rule, not just a :disabled one: without it Qt paints
           them through the native style and the disabled colour never reaches the text
           (which lives in the spin box's internal line edit). */
        QAbstractSpinBox { background-color: #1a1a1a; color: #e0e0e0;
                           border: 1px solid #3a3a3a; padding: 3px; border-radius: 3px; }
        /* Explicit colours above win over the palette, so a disabled control would
           otherwise look exactly like a live one. Grey the whole row, label included. */
        QLabel:disabled, QCheckBox:disabled, QRadioButton:disabled,
        QGroupBox:disabled, QPushButton:disabled { color: #5c5c5c; }
        QGroupBox::title:disabled { color: #5c5c5c; }
        QAbstractSpinBox:disabled, QComboBox:disabled, QLineEdit:disabled
            { color: #5c5c5c; background-color: #131313; border: 1px solid #262626; }
        QAbstractSpinBox::up-button:disabled, QAbstractSpinBox::down-button:disabled
            { background-color: #131313; }
        QGroupBox { color: #e0e0e0; border: 1px solid #3a3a3a; border-radius: 5px; margin-top: 10px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        QTextEdit { background-color: #1a1a1a; color: #e0e0e0; border: 1px solid #2a2a2a; border-radius: 3px; }
        QScrollBar:vertical { background-color: #1a1a1a; width: 12px; }
        QScrollBar::handle:vertical { background-color: #3a3a3a; border-radius: 6px; min-height: 20px; }
        QScrollBar::handle:vertical:hover { background-color: #4a4a4a; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        QDialog { background-color: #0a0a0a; }
        QScrollArea { background-color: #0a0a0a; }
        QScrollArea > QWidget > QWidget { background-color: #0a0a0a; }
    """)

    # Warn (but continue) if runtime dependencies are missing — rolling/drafting
    # still work; map patching needs the Assembly plugins.
    problems = check_dependencies()
    if problems:
        body = "\n\n".join("• " + p for p in problems)
        print("⚠ Missing dependencies:\n" + body)
        QMessageBox.warning(
            None, "Missing dependencies",
            "Some things needed for full functionality are missing:\n\n" + body
            + "\n\nThe app will still open — affected features (mainly map "
              "patching) won't work until this is resolved. See the README's "
              "Requirements section.")

    try:
        window = HaloGUI()
    except Exception as e:
        import traceback
        traceback.print_exc()
        QMessageBox.critical(None, "Startup Error",
                             f"Failed to start Halo Run Enhancer:\n{e}")
        sys.exit(1)
    window.show()
    window.raise_()
    window.activateWindow()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()