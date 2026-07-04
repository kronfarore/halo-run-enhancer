# halo_enhancer.py - Final version

import json
import random
import sys
from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *


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


class _NullWriter:
    """Stand-in for sys.stdout/err in a windowed (--noconsole) build where they
    are None, so diagnostic print() calls never raise."""
    def write(self, *args):
        pass

    def flush(self):
        pass


# Settings that persist across runs (editable in-app), stored next to saves.
SETTINGS_FILE = 'settings.json'
SETTINGS_KEYS = ('assembly_plugins_dir', 'target_difficulty')


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
    "include_wildcards": True,
    "font_size_title": 20,
    "font_size_subtitle": 18,
    "font_size_name": 16,
    "font_size_desc": 14,
    "font_size_small": 12,
    "font_size_button": 17,
    "font_size_weapon": 18,
    
    "weapon_card_height": 500,
    "card_height_no_wildcard": 500,
    "card_height_wildcard": 700,

    "wildcard_chance": 0.1,
    "new_weapon_chance": 0.0,
    # Whether deliberate weapon choices (start-of-run picks and the New Weapon
    # button) carry a tied negative. Random new-weapon pairs from
    # new_weapon_chance are unaffected (their pair always has an enemy). False
    # strips negatives from those deliberate weapon choices.
    "weapon_choice_negatives": True,

    "include_grenades": True,          # #2: treat grenades as weapons; False hides them
    # #7: one-handed weapons that can be offered as "Dual <Weapon>" in the
    # New Weapon card (only once the player already owns the base weapon).
    "one_handed_weapons": ["Pistol", "Plasma Pistol", "Plasma Rifle", "Needler", "SMG"],
    # Dual wield and weapon upgrades only unlock from these games onward
    # (matched against game order in the JSON). Set to the first game to allow everywhere.
    "dual_wield_from_game": "Halo 2",
    "upgrades_from_game": "Halo 2",

    # --- Map patching (Halo 1 for now) ---
    "target_difficulty": "Impossible",   # which difficulty slot difficulty-effects write to
    "assembly_plugins_dir": r"C:\Program Files (x86)\Steam\steamapps\common\HCEEK\Assembly-1-2023-11-29-1702446457\Plugins",
    "plugin_subdirs_by_game": {"Halo 1": ["Halo1MCC", "Halo1"], "Halo 2": ["Halo2MCC", "Halo2"]},
    "map_game_folder": {"Halo 1": "halo1", "Halo 2": "halo2"},
    # #6: alternate internal names mapped to a canonical weapon. The alias
    # shares the canonical weapon's modifiers and is not treated as new.
    # e.g. {"Magnum": "Pistol"}
    "weapon_aliases": {"Magnum": "Pistol"},
    # #3: upgrade weapons offered in the New Weapon card only once the player
    # owns the required base weapon. Value = base weapon (also the mod source
    # unless the upgrade has its own entry in the JSON). Picking an upgrade while
    # dual-wielding the base also grants "Dual <upgrade>".
    "weapon_upgrades": {"Brute Plasma Rifle": "Plasma Rifle"},

    "blacklist_label_separator": ": ",
}

# border / background hex for mod widgets, keyed by logical color name
MOD_COLORS = {
    'green': {'border': '4CAF50', 'bg': '0a1a0a'},
    'red':   {'border': 'f44336', 'bg': '1a0a0a'},
    'gold':  {'border': 'FFD700', 'bg': '1a1a0a'},
    'boss':  {'border': 'AA00FF', 'bg': '160016'},  # #4: menacing purple
    'special': {'border': '00E5FF', 'bg': '06201f'},  # #3: standout cyan
}


def resolve_gamed(value, game, games=None):
    """A `tag`/`field` value may be a plain string (applies to all games) or a
    dict keyed by game name. Resolution for the active game:
      1. exact game match wins;
      2. else an explicit 'default' key, if present;
      3. else the nearest EARLIER game that has an entry (e.g. a missing Halo 3
         falls back to Halo 2), using `games` as the ordering;
      4. else the nearest later game, then any entry; '' if the dict is empty.
    `games` is the ordered list of game names (from the DB)."""
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
        for g in games[idx + 1:]:            # then nearest later game
            if g in value:
                return value[g]
    return next(iter(value.values()), '')

class ModifierDatabase:
    """Load and manage all modifiers from halo.json"""
    
    def __init__(self, json_path=None):
        # Resolve relative to this script (or the bundled data dir when frozen).
        self.json_path = json_path or resource_path('halo.json')
        self.data = None
        self.positive_pool = []
        self.negative_pool = []
        self.wildcard_pool = []
        self.weapon_mods = {}
        self.enemy_mods = {}
        self.mission_enemies = {}
        self.mission_list = []
        self.games = []             # game names in JSON order
        self.mission_games = {}     # mission_id -> game name
        self.mission_weapons = {}   # mission_id -> level weapon pool
        self.mission_grenades = {}  # mission_id -> grenade pool (#2)
        self.mission_boss = {}      # mission_id -> list of boss names (#4)
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

    def _build_mod(self, mod_name, mod_data, extra=None):
        mod = {
            'name': mod_name,
            'desc': mod_data.get('desc', ''),
            'tag': mod_data.get('tag', ''),
            'field': mod_data.get('field', ''),
            'impact': mod_data.get('impact', 'p'),
            'games': self._parse_games(mod_data.get('game')),
            'wildcard': bool(mod_data.get('wildcard', False)),
            'special': bool(mod_data.get('special', False)),  # escalating-odds effect
            'targets': list(mod_data.get('targets', []) or []),  # map-patch targets
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
                    mod = self._build_mod(mod_name, mod_data)
                    mod['impact'] = mod_data.get('impact', 'n')
                    self.negative_pool.append(mod)
            if 'Specific Enemy modifier' in self.data['Enemy modifiers']:
                for enemy, mods in self.data['Enemy modifiers']['Specific Enemy modifier'].items():
                    self.enemy_mods[enemy] = []
                    for mod_name, mod_data in mods.items():
                        mod = self._build_mod(mod_name, mod_data, {'enemy': enemy})
                        mod['impact'] = mod_data.get('impact', 'n')
                        self.enemy_mods[enemy].append(mod)
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
                        'enemies': mission_data.get('enemies', [])
                    }
                    self.mission_games[mission_id] = game
                    self.mission_weapons[mission_id] = mission_data.get('weapons', [])
                    self.mission_grenades[mission_id] = mission_data.get('grenades', [])
                    boss = mission_data.get('boss')
                    self.mission_boss[mission_id] = ([boss] if isinstance(boss, str)
                                                     else list(boss) if boss else [])
                    self.mission_list.append((mission_id, mission_data.get('name', mission_id)))
        self.mission_list.sort(key=lambda x: x[0])
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
            name = CONFIG.get('weapon_upgrades', {}).get(name, name)
        return name

    def weapon_label(self, weapon):
        """Blacklist label for a weapon (distinct from modifier labels)."""
        return f"Weapon{CONFIG['blacklist_label_separator']}{weapon}"

    def get_weapon_modifiers(self, weapon_name):
        return self.weapon_mods.get(self.resolve_weapon(weapon_name), [])

    def get_enemy_modifiers(self, mission_id):
        if mission_id not in self.mission_enemies:
            return list(self.negative_pool)
        enemy_names = self.mission_enemies[mission_id]['enemies']
        specific_mods = []
        for enemy in enemy_names:
            if enemy in self.enemy_mods:
                specific_mods.extend(self.enemy_mods[enemy])
        return specific_mods + self.negative_pool

    def get_available_weapons(self):
        return list(self.weapon_mods.keys())

    def get_level_weapons(self, mission_id):
        """Weapon pool for a level: its `weapons` list (plus grenades unless
        disabled in CONFIG), restricted to entries that resolve to real mods.
        Aliases collapse to their canonical weapon. Falls back to all weapons."""
        wl = list(self.mission_weapons.get(mission_id) or [])
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
    def mission_has_boss(self, mission_id):
        return bool(self.mission_boss.get(mission_id))

    def get_boss_name(self, mission_id):
        names = self.mission_boss.get(mission_id) or []
        return ", ".join(names) if names else None

    def get_boss_modifiers_filtered(self, mission_id, blacklist, game=None):
        """Boss pool: any boss enemy's specific mods (if defined) plus the
        general negative pool, so bosses can always draw a challenge effect."""
        mods = []
        for boss in self.mission_boss.get(mission_id) or []:
            mods.extend(self.enemy_mods.get(boss, []))
        mods = mods + self.negative_pool
        return self.filter_blacklisted(mods, blacklist, game)

    def get_games(self):
        return list(self.games)

    def get_game_for_mission(self, mission_id):
        return self.mission_games.get(mission_id)

    def get_missions_for_game(self, game):
        result = [(mid, self.mission_enemies[mid]['name'])
                  for mid, g in self.mission_games.items() if g == game]
        result.sort(key=lambda x: x[0])
        return result

    def get_mission_list(self):
        return self.mission_list

    @staticmethod
    def _game_ok(mod, game):
        games = mod.get('games')
        return (not games) or (game is None) or (game in games)

    def get_mod_label(self, mod, source=None):
        if source:
            return f"{source}{CONFIG['blacklist_label_separator']}{mod['name']}"
        elif mod.get('weapon'):
            return f"{mod['weapon']}{CONFIG['blacklist_label_separator']}{mod['name']}"
        elif mod.get('enemy'):
            return f"{mod['enemy']}{CONFIG['blacklist_label_separator']}{mod['name']}"
        else:
            return f"General{CONFIG['blacklist_label_separator']}{mod['name']}"

    def filter_blacklisted(self, mods, blacklist, game=None):
        return [m for m in mods
                if self.get_mod_label(m) not in blacklist and self._game_ok(m, game)]

    def get_weapon_modifiers_filtered(self, weapon_name, blacklist, game=None):
        mods = self.get_weapon_modifiers(weapon_name)
        return self.filter_blacklisted(mods, blacklist, game)

    def get_player_modifiers_filtered(self, weapons, blacklist, game=None):
        """Player pool = the union of each owned weapon's mods (a player may own
        several) plus the general positive pool. `weapons` may be a str or list."""
        if isinstance(weapons, str):
            weapons = [weapons]
        weapon_mods = []
        for w in weapons or []:
            if w:
                weapon_mods.extend(self.get_weapon_modifiers_filtered(w, blacklist, game))
        # Copy each general mod before tagging it so we never mutate the
        # shared pool entries that random.choice hands back elsewhere.
        general_mods = [{**m, 'source': 'General'}
                        for m in self.filter_blacklisted(self.positive_pool, blacklist, game)]
        return weapon_mods + general_mods

    def get_enemy_modifiers_filtered(self, mission_id, blacklist, game=None):
        mods = self.get_enemy_modifiers(mission_id)
        return self.filter_blacklisted(mods, blacklist, game)

    def get_wildcard_modifier_filtered(self, blacklist, game=None):
        if not (self.wildcard_pool and CONFIG['include_wildcards']):
            return None
        # Filter first, then pick, so a blacklisted roll doesn't suppress
        # the wildcard entirely when other choices remain.
        available = [m for m in self.wildcard_pool
                     if self.get_mod_label(m) not in blacklist and self._game_ok(m, game)]
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
            "rounds": self.rounds
        }

    @classmethod
    def from_dict(cls, data):
        state = cls()
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
        player_text = "PLAYER 2" if self.is_player2 else "PLAYER 1"
        heading = "🔫 NEW WEAPON" if self.mode == 'add' else "CHOICE"
        title = QLabel(f"{player_text} - {heading} {self.pair_data['id']}")
        title.setStyleSheet(f"font-weight: bold; font-size: {CONFIG['font_size_title']}px; color: #e0e0e0;")
        layout.addWidget(title)

        weapon_group = QGroupBox("WEAPON")
        weapon_group.setStyleSheet("border: 2px solid #4CAF50; border-radius: 4px; padding: 10px; margin-top: 5px; background-color: #0a1a0a;")
        weapon_layout = QVBoxLayout(weapon_group)
        weapon_label = QLabel(f"Weapon: {self.pair_data['weapon']}")
        weapon_label.setStyleSheet(f"font-weight: bold; font-size: {CONFIG['font_size_weapon']}px; color: #4CAF50;")
        weapon_layout.addWidget(weapon_label)
        mod_count = len(self.pair_data.get('modifiers', []))
        mod_label = QLabel(f"Available modifiers: {mod_count}")
        mod_label.setStyleSheet(f"color: #aaa; font-size: {CONFIG['font_size_desc']}px;")
        weapon_layout.addWidget(mod_label)
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

        if self.mode == 'add':
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
        elif weapon in CONFIG.get('weapon_upgrades', {}):
            self.setStyleSheet("QGroupBox { border: 3px double #FF8C00; border-radius: 8px; "
                               "padding: 15px; background-color: #120c08; }")
        else:
            self.setStyleSheet("QGroupBox { border: 1px solid #444; border-radius: 8px; "
                               "padding: 15px; background-color: #0d0d0d; }")
        # 'add' cards carry a tied negative + an extra button, so they need more
        # room than the start-of-run weapon picks or they get squished.
        self.setFixedHeight(CONFIG['card_height_wildcard'] if self.mode == 'add'
                            else CONFIG['weapon_card_height'])

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
        desc = QLabel(mod_data.get('desc', ''))
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: #aaa; font-size: {CONFIG['font_size_desc']}px;")
        layout.addWidget(desc)
        game = self.parent_widget._current_game() if self.parent_widget else None
        games = self.parent_widget.db.get_games() if self.parent_widget else None
        tag = resolve_gamed(mod_data.get('tag', 'N/A'), game, games) or 'N/A'
        field = resolve_gamed(mod_data.get('field', 'N/A'), game, games) or 'N/A'
        tag_field = QLabel(f"Tag: {tag[:60]}{'...' if len(tag) > 60 else ''}\nField: {field}")
        tag_field.setStyleSheet(f"color: #666; font-size: {CONFIG['font_size_small']}px; font-family: monospace;")
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
        if self.parent_widget:
            player = 'player2' if self.is_player2 else 'player1'
            self.parent_widget.blacklist_manual_weapon(self.pair_data['weapon'], self.pair_data['id'], player)

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

        layout.setSpacing(10)
        player_text = ""
        if self.show_player1 and not self.show_player2:
            player_text = "PLAYER 1 - "
        elif self.show_player2 and not self.show_player1:
            player_text = "PLAYER 2 - "
        title = QLabel(f"{player_text}PAIR {self.pair['id']}")
        title.setStyleSheet(f"font-weight: bold; font-size: {CONFIG['font_size_title']}px; color: #e0e0e0;")
        layout.addWidget(title)

        # The positive (player) card is replaced by a new-weapon offer when the
        # pair rolled one (#4); the enemy/negative card below still shows.
        if self.show_player1:
            if self.pair.get('new_weapon'):
                layout.addWidget(self.create_weapon_widget(
                    self.pair['new_weapon'], "PLAYER 1 - 🔫 NEW WEAPON", 'player1'))
            elif self.pair['player1_mod']:
                layout.addWidget(self.create_mod_widget(
                    self.pair['player1_mod'],
                    f"PLAYER 1 ({self.pair['player1_mod'].get('weapon', 'Unknown Weapon')})",
                    "green", 'player1'))

        if self.show_player2:
            if self.pair.get('new_weapon'):
                layout.addWidget(self.create_weapon_widget(
                    self.pair['new_weapon'], "PLAYER 2 - 🔫 NEW WEAPON", 'player2'))
            elif self.pair['player2_mod']:
                layout.addWidget(self.create_mod_widget(
                    self.pair['player2_mod'],
                    f"PLAYER 2 ({self.pair['player2_mod'].get('weapon', 'Unknown Weapon')})",
                    "green", 'player2'))

        if self.pair['enemy_mod']:
            enemy_widget = self.create_mod_widget(self.pair['enemy_mod'], "ENEMY", "red", 'enemy')
            layout.addWidget(enemy_widget)

        if self.pair['wildcard_mod']:
            wildcard_widget = self.create_mod_widget(self.pair['wildcard_mod'], "🎲 WILDCARD", "gold", 'wildcard')
            layout.addWidget(wildcard_widget)

        # #4: guaranteed boss card on boss levels (replaces the wildcard roll).
        if self.pair.get('boss_mod'):
            boss_name = self.pair['boss_mod'].get('boss', 'Boss')
            boss_widget = self.create_mod_widget(self.pair['boss_mod'], f"☠ BOSS: {boss_name}", "boss", 'boss')
            layout.addWidget(boss_widget)

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

        self.setStyleSheet("QGroupBox { border: 1px solid #444; border-radius: 8px; padding: 15px; background-color: #0d0d0d; }")
        if self.pair.get('wildcard_mod') is not None or self.pair.get('boss_mod') is not None:
            self.setFixedHeight(CONFIG['card_height_wildcard'])
        else:
            self.setFixedHeight(CONFIG['card_height_no_wildcard'])

    def on_blacklist_weapon(self, weapon, mod_type):
        if self.parent_widget:
            self.parent_widget.add_weapon_to_blacklist(weapon, self.pair['id'], mod_type)

    def create_weapon_widget(self, weapon, label, mod_type):
        """Offer to add a weapon to the arsenal (replaces the positive card)."""
        scheme = MOD_COLORS['green']
        widget = QGroupBox(label)
        widget.setStyleSheet(f"""
            QGroupBox {{
                border: 2px solid #{scheme['border']};
                border-radius: 4px; padding: 10px; margin-top: 5px;
                background-color: #{scheme['bg']};
            }}
        """)
        layout = QVBoxLayout(widget)
        name = QLabel(f"➕ Add weapon: {weapon}")
        name.setStyleSheet(f"font-weight: bold; font-size: {CONFIG['font_size_name']}px; color: #4CAF50;")
        layout.addWidget(name)
        info = QLabel("Selecting this pair adds the weapon to your arsenal instead of a "
                      "positive effect. The enemy effect below still applies.")
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
                source = mod_data.get('weapon', 'Unknown Weapon')
        elif mod_type == 'enemy':
            source = mod_data.get('enemy', 'General')
        elif mod_type == 'boss':
            source = mod_data.get('boss', 'Boss')
        else:
            source = 'Wildcard'

        scheme = MOD_COLORS.get(color, MOD_COLORS['green'])
        border_width = 2 if color in ('gold', 'boss') else 1  # emphasize wildcard/boss
        special = bool(mod_data.get('special'))  # #3: escalating-odds effect
        if special:
            scheme = MOD_COLORS['special']
            border_width = 3
        widget = QGroupBox(label)
        widget.setStyleSheet(f"""
            QGroupBox {{
                border: {border_width}px {'double' if special else 'solid'} #{scheme['border']};
                border-radius: 4px;
                padding: 10px;
                margin-top: 5px;
                background-color: #{scheme['bg']};
            }}
        """)
        layout = QVBoxLayout(widget)
        name = QLabel(f"{'★ ' if special else ''}{source}: {mod_data.get('name', 'Unknown')}")
        name.setStyleSheet("font-weight: bold; font-size: %dpx; color: %s;"
                           % (CONFIG['font_size_name'], '#00E5FF' if special else '#e0e0e0'))
        layout.addWidget(name)
        desc = QLabel(mod_data.get('desc', ''))
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: #aaa; font-size: {CONFIG['font_size_desc']}px;")
        layout.addWidget(desc)
        game = self.parent_widget._current_game() if self.parent_widget else None
        games = self.parent_widget.db.get_games() if self.parent_widget else None
        tag = resolve_gamed(mod_data.get('tag', 'N/A'), game, games) or 'N/A'
        field = resolve_gamed(mod_data.get('field', 'N/A'), game, games) or 'N/A'
        tag_field = QLabel(f"Tag: {tag[:60]}{'...' if len(tag) > 60 else ''}\nField: {field}")
        tag_field.setStyleSheet(f"color: #666; font-size: {CONFIG['font_size_small']}px; font-family: monospace;")
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
        else:
            bl_source = 'Wildcard'
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
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Saved Run",
            "selections/",
            "JSON Files (*.json)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.loaded_state = RunState.from_dict(data)
                self.choice = 'load'
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file:\n{str(e)}")


class MagnitudeEditorDialog(QDialog):
    """Per-run editor: lists the selected effects grouped by tag, shows each
    field's vanilla value, takes a typed operator (-x/+x/*x/=x) per target
    (pre-filled from the presets library), then backs up and patches the .map."""

    _CUSTOM = '__custom__'

    def __init__(self, parent, effects, subdirs, map_path, presets_path, target_difficulty):
        super().__init__(parent)
        import halo_patch
        self._hp = halo_patch
        self.subdirs = subdirs
        self.presets_path = presets_path
        self.presets = halo_patch.load_presets(presets_path)
        self.target_difficulty = target_difficulty
        self.effects = effects
        self.rows = []          # (effect, target, QLineEdit)
        self._srcmap = None     # cached read-source map for vanilla values
        self.setWindowTitle("Apply Effects to Map")
        self.setModal(True)
        self.setMinimumSize(940, 760)
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
            self._srcmap = self._hp.hm.HaloMap(src)
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
        field = target['field']
        if target.get('difficulty'):
            field = f"{self.target_difficulty} {field}"
        v = m.read_first(cls, path, field, plugin, target.get('block'), target.get('index', 0) or 0)
        if v is None:
            return "field?"
        return f"{round(v, 4)}" if isinstance(v, float) else str(v)

    def _variant_values_str(self, tag, target):
        """List every matching variant's vanilla value as 'variant=value'
        (or a single value / status if there's just one / none)."""
        m = self._read_source()
        if not m:
            return "?"
        cls, path = self._hp.hm.split_tag(tag)
        plugin = self.registry.get(cls)
        if plugin is None:
            return "no plugin"
        field = target['field']
        if target.get('difficulty'):
            field = f"{self.target_difficulty} {field}"
        vals = m.read_all(cls, path, field, plugin, target.get('block'), target.get('index', 0) or 0)
        if not vals:
            return "— not in map" if not m.find_tags(cls, path) else "field?"
        fmt = lambda x: round(x, 4) if isinstance(x, float) else x
        # #1: collapse variants that share a value onto one line.
        by_value = {}
        for p, vv in vals:
            by_value.setdefault(fmt(vv), []).append(p.rsplit(chr(92), 1)[-1])
        if len(by_value) == 1:
            return str(next(iter(by_value)))
        return "\n".join(f"{val}   ({', '.join(names)})" for val, names in by_value.items())

    # ---- targets (halo.json + preset fallbacks, #7) ----
    def _effect_targets(self, eff):
        base = list(eff.get('targets') or [])
        custom = list(self.presets.get(self._hp.preset_key(eff['tag'], eff['name'], self._CUSTOM)) or [])
        for c in custom:
            c['custom'] = True
        return base + custom, (not base and bool(custom))

    # ---- build ----
    @staticmethod
    def _wrap(layout):
        w = QWidget()
        w.setLayout(layout)
        return w

    def _build(self, map_path):
        layout = QVBoxLayout(self)

        prow = QHBoxLayout()
        prow.addWidget(QLabel("Assembly plugins folder:"))
        self.plugins_edit = QLineEdit(CONFIG.get('assembly_plugins_dir', ''))
        prow.addWidget(self.plugins_edit, 1)
        pbrowse = QPushButton("Browse…")
        pbrowse.clicked.connect(self._browse_plugins)
        prow.addWidget(pbrowse)
        layout.addLayout(prow)

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
        layout.addLayout(maprow)

        drow = QHBoxLayout()
        drow.addWidget(QLabel("Difficulty:"))
        self.diff_combo = QComboBox()
        self.diff_combo.addItems(["Easy", "Normal", "Hard", "Impossible"])
        di = self.diff_combo.findText(self.target_difficulty)
        if di >= 0:
            self.diff_combo.setCurrentIndex(di)
        self.diff_combo.currentTextChanged.connect(self._on_difficulty_changed)
        drow.addWidget(self.diff_combo)
        help_lbl = QLabel("operators:  =x set   +x add   -x subtract   *x multiply   (blank = skip)")
        help_lbl.setStyleSheet("color: #aaa; font-size: 12px;")
        drow.addSpacing(16)
        drow.addWidget(help_lbl)
        drow.addStretch()
        layout.addLayout(drow)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._cont = QWidget()
        self.form = QVBoxLayout(self._cont)
        scroll.setWidget(self._cont)
        layout.addWidget(scroll, 1)
        self._populate()

        self.results = QTextEdit()
        self.results.setReadOnly(True)
        self.results.setMaximumHeight(170)
        self.results.setStyleSheet("background-color: #1a1a1a; color: #e0e0e0; font-family: monospace; font-size: 12px;")
        layout.addWidget(self.results)

        btns = QHBoxLayout()
        apply_btn = QPushButton("💾 Backup && Apply to Map")
        apply_btn.setStyleSheet("background-color: #5a3a2a; color: white; font-weight: bold; padding: 8px 16px; border-radius: 5px;")
        apply_btn.clicked.connect(self._apply)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        btns.addWidget(apply_btn)
        btns.addStretch()
        btns.addWidget(close_btn)
        layout.addLayout(btns)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _populate(self):
        self._clear_layout(self.form)
        self.rows = []
        for grp, effs in self._hp.group_effects(self.effects):
            hdr = QLabel(grp)
            hdr.setStyleSheet("font-weight: bold; font-size: 15px; color: #4CAF50; margin-top: 8px;")
            self.form.addWidget(hdr)
            for eff in effs:
                self.form.addWidget(self._effect_box(eff))
        self.form.addStretch()

    def _effect_box(self, eff):
        box = QGroupBox(f"{eff['name']}   ×{eff['count']}")
        v = QVBoxLayout(box)
        if eff.get('desc'):
            d = QLabel(eff['desc'])
            d.setWordWrap(True)
            d.setStyleSheet("color: #aaa; font-size: 12px;")
            v.addWidget(d)
        tagl = QLabel(eff['tag'])
        tagl.setStyleSheet("color: #666; font-size: 11px; font-family: monospace;")
        v.addWidget(tagl)

        targets, fallback = self._effect_targets(eff)
        if fallback:
            flag = QLabel("Not defined in halo.json — using fallback field(s) from magnitude_presets.")
            flag.setStyleSheet("color: #e0b83a; font-size: 12px;")
            flag.setWordWrap(True)
            v.addWidget(flag)
        elif not targets:
            note = QLabel("⚠ No target defined in halo.json — add one with ‘＋ field’ below.")
            note.setStyleSheet("color: #e08a3a; font-size: 12px;")
            note.setWordWrap(True)
            v.addWidget(note)

        for t in targets:
            row = QHBoxLayout()
            fname = t['field'] + (f"  [{self.target_difficulty}]" if t.get('difficulty') else "")
            if t.get('custom'):
                fname += "  (preset)"
            # #1: field name on top, operator input directly below it.
            left = QVBoxLayout()
            left.setSpacing(2)
            lbl = QLabel(fname)
            left.addWidget(lbl)
            inrow = QHBoxLayout()
            le = QLineEdit()
            le.setPlaceholderText("-x / +x / *x / =x")
            le.setMaximumWidth(120)
            key = self._hp.preset_key(eff['tag'], eff['name'], t['field'])
            if key in self.presets and not isinstance(self.presets[key], list):
                le.setText(str(self.presets[key]))
            inrow.addWidget(le)
            if t.get('custom'):
                rm = QPushButton("✕")
                rm.setMaximumWidth(28)
                rm.setToolTip("Remove this fallback field")
                rm.clicked.connect(lambda _=False, e=eff, tt=t: self._remove_custom(e, tt))
                inrow.addWidget(rm)
            inrow.addStretch()
            left.addLayout(inrow)
            leftw = self._wrap(left)
            leftw.setMinimumWidth(240)
            row.addWidget(leftw)
            # #1/#2: variant values on the right, one line per distinct value.
            variants = QLabel(self._variant_values_str(eff['tag'], t))
            variants.setStyleSheet("color: #7aa0c0; font-size: 12px; font-family: monospace;")
            variants.setWordWrap(True)
            variants.setAlignment(Qt.AlignTop)
            row.addWidget(variants, 1)
            v.addWidget(self._wrap(row))
            self.rows.append((eff, t, le))

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
        key = self._hp.preset_key(eff['tag'], eff['name'], self._CUSTOM)
        lst = self.presets.get(key) or []
        lst.append({'field': field, 'block': block})
        self.presets[key] = lst
        self._hp.save_presets(self.presets_path, self.presets)
        self._populate()

    def _remove_custom(self, eff, target):
        key = self._hp.preset_key(eff['tag'], eff['name'], self._CUSTOM)
        lst = [c for c in (self.presets.get(key) or [])
               if not (c.get('field') == target['field'] and c.get('block') == target.get('block'))]
        if lst:
            self.presets[key] = lst
        else:
            self.presets.pop(key, None)
        self._hp.save_presets(self.presets_path, self.presets)
        self._populate()

    def _on_difficulty_changed(self, text):
        # #2: switch the difficulty slot; vanilla values re-read from the same map.
        self.target_difficulty = text
        CONFIG['target_difficulty'] = text
        save_settings()
        self._populate()

    # ---- path handling ----
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

    def _apply(self):
        map_path = self.map_edit.text().strip()
        if not Path(map_path).is_file():
            QMessageBox.warning(self, "Map not found", f"Not a file:\n{map_path}")
            return

        plan_map = {}
        for eff, t, le in self.rows:
            txt = le.text().strip()
            if not txt:
                continue
            key = (eff['tag'], eff['name'])
            plan_map.setdefault(key, {'tag': eff['tag'], 'name': eff['name'], 'ops': []})
            plan_map[key]['ops'].append({'field': t['field'], 'block': t.get('block'),
                                         'difficulty': t.get('difficulty'),
                                         'index': t.get('index', 0), 'op_str': txt})
            self.presets[self._hp.preset_key(eff['tag'], eff['name'], t['field'])] = txt
        plan = list(plan_map.values())
        if not plan:
            QMessageBox.information(self, "Nothing to apply", "Enter at least one operator first.")
            return

        confirm = QMessageBox.question(
            self, "Apply to map?",
            f"Write {sum(len(i['ops']) for i in plan)} edit(s) into:\n{map_path}\n\n"
            f"A one-time backup (.bak) of the original will be made first.")
        if confirm != QMessageBox.Yes:
            return

        try:
            results, backup = self._hp.apply_run(map_path, plan, self.registry, self.target_difficulty)
        except Exception as e:
            QMessageBox.critical(self, "Patch failed", str(e))
            return

        self._hp.save_presets(self.presets_path, self.presets)
        self._write_patch_file(map_path, plan, results, backup)
        self._srcmap = None  # map changed on disk; re-read vanilla next time

        ok = [r for r in results if r.get('ok')]
        bad = [r for r in results if not r.get('ok')]
        lines = [f"Applied {len(ok)} edit(s); {len(bad)} skipped/failed."]
        if backup:
            lines.append(f"Backup: {backup}")
        lines.append("")
        for r in ok:
            lines.append(f"  OK  {r['effect']}: {r['field']}  {round(r['old'], 4)} -> {round(r['new'], 4)}")
        for r in bad:
            lines.append(f"  --  {r['effect']}: {r.get('field')}  ({r['reason']})")
        self.results.setPlainText("\n".join(lines))

    def _write_patch_file(self, map_path, plan, results, backup):
        try:
            patch_dir = app_data_dir() / "patches"
            patch_dir.mkdir(exist_ok=True)
            mission = Path(map_path).stem
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            grouped = {}
            for item in plan:
                grouped.setdefault(self._hp.hm.split_tag(item['tag'])[0], []).append(item)
            data = {"map": map_path, "backup": backup,
                    "target_difficulty": self.target_difficulty,
                    "timestamp": ts, "groups": grouped, "results": results}
            with open(patch_dir / f"patch_{mission}_{ts}.json", 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass  # patch-log failure shouldn't block the actual patch


class HaloGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        # Let failures propagate so main() can report them and exit cleanly,
        # rather than showing a half-constructed window that crashes later.
        self.db = ModifierDatabase()
        self.run_state = RunState()
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
                self.load_run_state(dialog.loaded_state)
        else:
            self.close()

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

    def _build_weapon_choices(self, weapons, enemy_mods, count=3, with_enemy=True):
        choices = []
        used_weapons = set()
        used_enemies = set()
        for i in range(count):
            available = [w for w in weapons if w not in used_weapons]
            if not available:
                break
            weapon = random.choice(available)
            used_weapons.add(weapon)
            choices.append({
                'id': i + 1,
                'weapon': weapon,
                'modifiers': self.db.get_weapon_modifiers(weapon),
                'enemy_mod': self._pick_enemy(enemy_mods, used_enemies) if with_enemy else None
            })
        return choices

    def _reroll_weapon_choice(self, choice_id, weapon_pool=None, exclude_weapons=(),
                              player_label="", with_enemy=True):
        weapons = weapon_pool if weapon_pool is not None else self.db.get_available_weapons()
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
                avail = [w for w in weapons if w not in exclude_weapons] or weapons
            card.pair_data['weapon'] = random.choice(avail)
            card.pair_data['modifiers'] = self.db.get_weapon_modifiers(card.pair_data['weapon'])
            card.pair_data['enemy_mod'] = self._pick_enemy(enemy_mods, used_enemies) if with_enemy else None
            card.setup_ui()
            self.update_status(f"Rerolled choice {choice_id}{player_label}")
            break

    def _blacklisted_weapon(self, weapon):
        return self.db.weapon_label(weapon) in self.run_state.blacklist

    def _game_weapon_pool(self):
        return [w for w in self.db.get_game_weapons(self._current_game())
                if not self._blacklisted_weapon(w)]

    def _weapon_choice_negatives(self):
        return CONFIG.get('weapon_choice_negatives', True)

    def show_weapon_selection(self):
        weapons = self._game_weapon_pool()
        if len(weapons) < 2:
            QMessageBox.warning(self, "Error", "Not enough weapons available!")
            return

        choices = self._build_weapon_choices(weapons, self._enemy_pool(),
                                             with_enemy=self._weapon_choice_negatives())

        self.pending_player2_selection = False
        self.display_weapon_selection(choices, is_player2=False)
        self.run_state.phase = 'weapon_selection'
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
        self.pairs_container.setUpdatesEnabled(False)
        try:
            self._clear_pairs_layout()
            for choice in choices:
                card = WeaponSelectionCard(choice, self, is_player2, mode)
                self.pairs_layout.addWidget(card)
                self.pair_cards.append(card)
        finally:
            self.pairs_container.setUpdatesEnabled(True)

    def reroll_weapon_choice_p1(self, choice_id):
        self._reroll_weapon_choice(choice_id, weapon_pool=self._game_weapon_pool(),
                                   player_label=" for Player 1",
                                   with_enemy=self._weapon_choice_negatives())

    def reroll_weapon_choice_p2(self, choice_id):
        self._reroll_weapon_choice(choice_id, weapon_pool=self._game_weapon_pool(),
                                   exclude_weapons={self.run_state.player1_weapon},
                                   player_label=" for Player 2",
                                   with_enemy=self._weapon_choice_negatives())

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
        available_weapons = [w for w in self._game_weapon_pool()
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
        self.save_btn.setEnabled(False)
        self.generate_btn.setEnabled(True)
        # Don't auto-roll the first effects — wait for the user to Generate.
        self.update_status("Weapons set — press 🔄 GENERATE PAIRS when ready")

    # ---- New Weapon button (#3) — both players draw from the game pool ----
    def _game_at_least(self, min_game):
        """True if the current game is `min_game` or later in JSON game order."""
        games = self.db.get_games()
        cur = self._current_game()
        if cur in games and min_game in games:
            return games.index(cur) >= games.index(min_game)
        return True  # unknown ordering -> don't restrict

    def _weapon_offer_pool(self, player):
        """Game weapon pool minus owned, plus 'Dual <Weapon>' options for owned
        one-handed weapons (#7) and upgrade weapons whose base is owned (#3).
        Dual wield and upgrades only unlock from their configured game onward.
        Blacklisted weapons are excluded (#1)."""
        owned = set(self.run_state.weapons_for(player))
        pool = [w for w in self._game_weapon_pool() if w not in owned]
        if self._game_at_least(CONFIG.get('dual_wield_from_game', 'Halo 2')):
            one_handed = CONFIG.get('one_handed_weapons', [])
            for w in self.run_state.weapons_for(player):
                if w in one_handed and not w.startswith('Dual '):
                    dual = f"Dual {w}"
                    if dual not in owned and not self._blacklisted_weapon(dual):
                        pool.append(dual)
        if self._game_at_least(CONFIG.get('upgrades_from_game', 'Halo 2')):
            for upgrade, base in CONFIG.get('weapon_upgrades', {}).items():
                if base in owned and upgrade not in owned and not self._blacklisted_weapon(upgrade):
                    pool.append(upgrade)
        return pool

    def _grant_weapon(self, player, weapon):
        """Add a weapon; if it's an upgrade and the player dual-wields the base,
        also grant the dual version of the upgrade (#3)."""
        self.run_state.add_weapon(player, weapon)
        base = CONFIG.get('weapon_upgrades', {}).get(weapon)
        if base and f"Dual {base}" in self.run_state.weapons_for(player):
            self.run_state.add_weapon(player, f"Dual {weapon}")

    def on_new_weapon_button(self):
        if not (self.run_state.player1_weapon and self.run_state.player2_weapon):
            self.update_status("Choose starting weapons for both players first")
            return
        self._manual_queue = ['player1', 'player2']
        self._manual_results = {}
        self._next_manual_weapon()

    def _next_manual_weapon(self):
        while self._manual_queue:
            player = self._manual_queue.pop(0)
            if self._show_manual_weapon_selection(player):
                return
        self._finish_manual_weapon()

    def _show_manual_weapon_selection(self, player):
        pool = self._weapon_offer_pool(player)
        if not pool:
            return False
        # New Weapon cards carry a tied negative unless disabled in CONFIG.
        with_enemy = self._weapon_choice_negatives()
        choices = self._build_weapon_choices(pool, self._enemy_pool(),
                                             count=min(3, len(pool)), with_enemy=with_enemy)
        self.display_weapon_selection(choices, is_player2=(player == 'player2'), mode='add')
        who = "Player 1" if player == 'player1' else "Player 2"
        suffix = " (comes with a negative)" if with_enemy else ""
        self.update_status(f"🔫 New weapon for {who}: pick one{suffix}")
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
        self.update_status(f"{who} gained a new weapon: {selected['weapon']}!")
        self._next_manual_weapon()

    def reroll_manual_weapon(self, choice_id, player):
        pool = self._weapon_offer_pool(player)
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
            self.save_btn.setEnabled(True)
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
    def load_run_state(self, state):
        self.run_state = state
        self.enhancer = RunEnhancer(self.db, self.run_state)
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
        if self.run_state.phase == 'player1_turn':
            self.run_state.weapon_selection_made = True
            self.on_generate()
        elif self.run_state.phase == 'player2_turn':
            self.run_state.weapon_selection_made = True
            self.on_generate()
        elif self.run_state.phase == 'complete':
            self.run_state.weapon_selection_made = True
            self.update_history()
            self.update_status("Run loaded - Both players have selected!")
            self.save_btn.setEnabled(True)
            self.generate_btn.setEnabled(True)
        elif self.run_state.phase == 'weapon_selection':
            self.show_weapon_selection()

    # ---- UI Setup ----
    def setup_ui(self):
        self.setWindowTitle("🎯 Halo Run Enhancer")
        self.setMinimumSize(1400, 900)
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(15)

        header_layout = QHBoxLayout()
        header = QLabel("🎯 HALO RUN ENHANCER")
        header.setStyleSheet("font-size: 28px; font-weight: bold; color: #4CAF50; padding: 10px; border-bottom: 2px solid #1a3a1a;")
        header_layout.addWidget(header)
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
        self.new_weapon_btn.setToolTip("Draw a new weapon from the current game's pool for both players")
        self.new_weapon_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a4a2a; color: white; font-weight: bold;
                font-size: 14px; padding: 10px 20px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #4a6a3a; }
        """)
        self.new_weapon_btn.clicked.connect(self.on_new_weapon_button)
        button_layout.addWidget(self.new_weapon_btn)

        self.save_btn = QPushButton("💾 SAVE SELECTION")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a3a5a; color: white; font-weight: bold;
                font-size: 14px; padding: 10px 20px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #3a5a7a; }
            QPushButton:disabled { background-color: #444; color: #888; }
        """)
        self.save_btn.clicked.connect(self.on_save)
        self.save_btn.setEnabled(False)
        button_layout.addWidget(self.save_btn)

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
        button_layout.addStretch()
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
        self.pairs_layout.setSpacing(20)
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
        self.save_btn.setEnabled(False)
        self.generate_btn.setEnabled(True)
        self.update_status(f"{status_prefix} - Generate pairs manually")

    def change_weapon(self, player):
        weapons = self._game_weapon_pool()
        if player == 'player1' and self.run_state.player2_weapon:
            available = [w for w in weapons if w != self.run_state.player2_weapon]
        elif player == 'player2' and self.run_state.player1_weapon:
            available = [w for w in weapons if w != self.run_state.player1_weapon]
        else:
            available = weapons
        if not available:
            QMessageBox.warning(self, "Error", "No weapons available!")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Select {player.upper()} Weapon")
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(f"Select weapon for {player.upper()}:"))
        combo = QComboBox()
        for w in available:
            combo.addItem(w)
        current = self.run_state.player1_weapon if player == 'player1' else self.run_state.player2_weapon
        if current in available:
            combo.setCurrentIndex(available.index(current))
        layout.addWidget(combo)
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Select")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        if dialog.exec() == QDialog.Accepted:
            new_weapon = combo.currentText()
            if player == 'player1':
                self.run_state.set_weapon('player1', new_weapon)
                if self.run_state.player2_weapon == new_weapon:
                    self.run_state.set_weapon('player2', None)
            else:
                self.run_state.set_weapon('player2', new_weapon)
                if self.run_state.player1_weapon == new_weapon:
                    self.run_state.set_weapon('player1', None)
            self.update_weapon_display()
            self.run_state.selected_pairs = {'player1': None, 'player2': None}
            self.run_state.phase = 'player1_turn'
            self.run_state.current_turn = 'player1'
            self.run_state.pairs = []
            self.clear_pairs()
            self.update_history()
            self.save_btn.setEnabled(False)
            self.generate_btn.setEnabled(True)
            self.update_status(f"Weapon changed for {player.upper()} - Generate new pairs")
            if self.run_state.player1_weapon and self.run_state.player2_weapon:
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
            self.save_btn.setEnabled(False)
            self.update_status("Regenerating pairs for Player 1")

        pairs = self.enhancer.generate_pairs(for_player=player)
        self.display_pairs(pairs, show_p1, show_p2)
        self.update_status(f"{turn_text}'s turn - Select a pair")
        self.update_history()
        self.save_btn.setEnabled(False)
        self.generate_btn.setEnabled(True)

    def display_pairs(self, pairs, show_player1=True, show_player2=True):
        self.pairs_container.setUpdatesEnabled(False)
        try:
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
                'wildcard': p1_pair.get('wildcard_mod'),
                'boss1': p1_pair.get('boss_mod'),
                'boss2': p2_pair.get('boss_mod')
            }
            self.run_state.rounds.append(round_data)
            self._update_special_counters(p1_pair.get('player1_mod'), p2_pair.get('player2_mod'))

            self.save_btn.setEnabled(True)
            self.generate_btn.setEnabled(True)
            self.update_status("Both players have selected! Save or generate new pairs.")
            self.clear_pairs()
        else:
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
        elif mod_type == 'boss':
            boss_mods = self.db.get_boss_modifiers_filtered(self.run_state.mission_id, bl, game)
            if boss_mods:
                name = self.db.get_boss_name(self.run_state.mission_id)
                pair['boss_mod'] = {**random.choice(boss_mods), 'boss': name}
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

    @staticmethod
    def _round_summary(pdata):
        if pdata.get('starting'):
            return f"{pdata.get('weapon')} (starting weapon)"
        if pdata.get('gained_weapon'):
            return f"{pdata.get('weapon')} (+🔫 {pdata['gained_weapon']})"
        mod = pdata.get('mod')
        return f"{pdata.get('weapon')} - {mod['name']}" if mod else f"{pdata.get('weapon')}"

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
                wildcard = round_data.get('wildcard')
                boss1 = round_data.get('boss1')
                boss2 = round_data.get('boss2')
                text += f"Round {i}: P1: {self._round_summary(round_data['player1'])}, "
                text += f"P2: {self._round_summary(round_data['player2'])}, "
                text += f"Enemies: {enemy1['name'] if enemy1 else 'None'}, {enemy2['name'] if enemy2 else 'None'}"
                if wildcard:
                    text += f", Wildcard: {wildcard['name']}"
                if boss1 or boss2:
                    text += f", Boss: {boss1['name'] if boss1 else 'None'}, {boss2['name'] if boss2 else 'None'}"
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

    # ---- Save ----
    def on_save(self):
        if self.run_state.phase != 'complete':
            QMessageBox.warning(self, "Not Complete", "Both players must select before saving!")
            return

        selections_dir = app_data_dir() / "selections"
        selections_dir.mkdir(exist_ok=True)

        save_data = self.run_state.to_dict()
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_name = f"selection_{timestamp}.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Selection",
            str(selections_dir / default_name),
            "JSON Files (*.json)"
        )
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            self.update_status(f"✅ Selection saved to {file_path}")
            QMessageBox.information(self, "Saved!", f"Selection saved to:\n{file_path}")
            
    # ---- Map patching (feature a) ----
    def on_patch_map(self):
        try:
            import halo_patch
        except Exception as e:
            QMessageBox.critical(self, "Patching unavailable",
                                 f"Could not load the map-patching modules:\n{e}")
            return
        game = self._current_game()
        games = self.db.get_games()
        # Resolve any per-game dict tags to the active game's string so they're
        # hashable/patchable (some effects carry {"Halo 1": ..., "Halo 2": ...}).
        for rd in self.run_state.rounds or []:
            slots = [(rd.get('player1') or {}).get('mod'), (rd.get('player2') or {}).get('mod'),
                     rd.get('enemy1'), rd.get('enemy2'), rd.get('wildcard'),
                     rd.get('boss1'), rd.get('boss2')]
            for mod in slots:
                if isinstance(mod, dict) and isinstance(mod.get('tag'), dict):
                    mod['tag'] = resolve_gamed(mod['tag'], game, games)
        effects = halo_patch.collect_effects(self.run_state.rounds)
        if not effects:
            QMessageBox.information(self, "No effects yet",
                                    "Select some effects first — there's nothing to patch.")
            return
        subdirs = CONFIG.get('plugin_subdirs_by_game', {}).get(game, [])
        game_folder = CONFIG.get('map_game_folder', {}).get(game, '')
        map_path = halo_patch.default_map_path(
            Path(__file__).resolve().parent, game_folder, self.run_state.mission_id)
        presets_path = str(app_data_dir() / "magnitude_presets.json")
        dlg = MagnitudeEditorDialog(self, effects, subdirs, map_path, presets_path,
                                    CONFIG.get('target_difficulty', 'Normal'))
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
        return [w for w in self.db.get_level_weapons(self.run_state.mission_id)
                if w not in owned and self.db.weapon_label(w) not in bl]

    def _weighted_pick(self, mods):
        """Pick a player mod. A special effect's weight equals its counter =
        rounds since it was last picked (linear; starts at 1, 0 right after a
        pick so it's suppressed for one round). Everything else is weight 1."""
        if not mods:
            return None
        weights = [self.run_state.special_counters.get(m['name'], 1) if m.get('special') else 1
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

        # #4: boss levels get a guaranteed Boss card on every pair, and wildcards
        # are disabled for the level.
        has_boss = self.db.mission_has_boss(mid)
        boss_pool = self.db.get_boss_modifiers_filtered(mid, bl, game) if has_boss else []
        boss_name = self.db.get_boss_name(mid)

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

        pairs = []
        wi = 0
        for i in range(3):
            enemy_choice = random.choice(enemy_mods) if enemy_mods else None
            new_weapon = None
            p1_choice = p2_choice = None
            wildcard = None
            boss_mod = {**random.choice(boss_pool), 'boss': boss_name} if boss_pool else None
            if flags[i] and wi < len(offered):
                new_weapon = offered[wi]
                wi += 1
            else:
                choice = self._weighted_pick(pmods)
                if for_player == 'player1':
                    p1_choice = choice
                else:
                    p2_choice = choice
                if (not has_boss and CONFIG['include_wildcards']
                        and random.random() < CONFIG['wildcard_chance']):
                    wildcard = self.db.get_wildcard_modifier_filtered(bl, game)
            pairs.append({
                'id': i + 1,
                'player1_mod': p1_choice,
                'player2_mod': p2_choice,
                'enemy_mod': enemy_choice,
                'wildcard_mod': wildcard,
                'boss_mod': boss_mod,
                'new_weapon': new_weapon,
                'selected_by': None
            })
        self.run_state.pairs = pairs
        self.run_state.current_turn = for_player
        return pairs

    def select_pair(self, pair_id, player):
        for pair in self.run_state.pairs:
            if pair['id'] == pair_id:
                pair['selected_by'] = player
                self.run_state.selected_pairs[player] = pair
                return True
        return False

def main():
    # In a windowed build sys.stdout/err are None; guard the diagnostic prints.
    if sys.stdout is None:
        sys.stdout = _NullWriter()
    if sys.stderr is None:
        sys.stderr = _NullWriter()
    load_settings()
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet("""
        QMainWindow, QWidget { background-color: #0a0a0a; }
        QLabel { color: #e0e0e0; }
        QPushButton { color: #e0e0e0; }
        QComboBox { background-color: #1a1a1a; color: #e0e0e0; border: 1px solid #3a3a3a; padding: 5px; border-radius: 3px; }
        QComboBox::drop-down { border: none; }
        QComboBox QAbstractItemView { background-color: #1a1a1a; color: #e0e0e0; selection-background-color: #2a5a2a; border: 1px solid #2a5a2a; }
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