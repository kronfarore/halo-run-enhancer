r"""Write a PORTED weapon's cards into halo.json, one game per port, from its donor.

A port lands in a game where halo.json has no cards for it (the SAW's are Halo 4's).
Its donor weapon in that game (weapon_ports_catalog.json: the SAW's is the Assault
Rifle everywhere but Halo 2, where it is the SMG) already has the right cards, so each
donor card valid in that game is MERGED into the port's own entry (user, 2026-10-03:
in halo.json, not rebuilt at every load, so the cards can be tuned like any other):

  * a card the port already has: the game joins its 'game' list, its 'tag' becomes a
    per-game dict, its existing targets are pinned to their old games ('games' is
    matched LITERALLY on targets) and the donor's targets for the new game are
    appended with "games": [game] (+ ODST alongside Halo 3, which inherits its cards);
  * a card only the donor has: added to the port with the same shape.

Donor-specific tags are pointed at the port's own (ModifierDatabase._port_tag: weapon,
first-person animations, HUD, bullet / projectile / damage effect by name); shared
tags (globals melee) stay. Every resulting tag is CHECKED before writing -- Halo 1 in
the editing kit's tag files (its maps may predate the port's own bullet), the other
games in a deployed map that carries the port -- and a card with a tag that does not
exist is skipped and reported, never guessed. A game a card already covers is never
overwritten, so running it twice changes nothing.

    python port_cards.py --weapon SAW            (dry run: prints the plan)
    python port_cards.py --weapon SAW --write    (rewrites the weapon's halo.json block)
"""
import argparse
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

HALO_JSON = os.path.join(ROOT, 'halo.json')
SECTION = ('Player Modifiers', 'Specific Weapon Modifier')
KIT_TAGS = {'Halo 1': r'F:\SteamLibrary\steamapps\common\HCEEK\tags'}
KIT_EXT = {'weap': 'weapon', 'proj': 'projectile', 'jpt!': 'damage_effect',
           'antr': 'model_animations', 'wphi': 'weapon_hud_interface'}
INHERITS = {'Halo 3': ['Halo 3: ODST']}       # targets name these too ('games' is literal)


def _games(card):
    """A card's `game` as a list (a single game may be a plain string)."""
    g = card.get('game') or []
    return [g] if isinstance(g, str) else list(g)


def _resolve(v, game, games):
    import halo_enhancer as he
    return he.resolve_gamed(v, game, games)


def _tag_parts(tag):
    """'jpt! a & b' -> [('jpt!', 'a'), ('jpt!', 'b')] (later parts inherit the class)."""
    out, cls = [], None
    for part in tag.split(' & '):
        c, _s, p = part.strip().partition(' ')
        if chr(92) in c or not p:                      # no class of its own
            out.append((cls, part.strip()))
        else:
            cls = c
            out.append((c, p))
    return out


class Checker:
    """Does a tag exist where the port lives in `game`?"""

    def __init__(self, db, game, weapon, wpath=None):
        self.game, self.map = game, None
        # Halo 1: the kit can hold port tags nothing USES -- weapons\saw\melee exists,
        # but the SAW keeps the Assault Rifle's melee (user's call). A bullet / damage
        # tag counts only if the port's weapon or one of its projectiles names it.
        self.refs = b''
        if game in KIT_TAGS and wpath:
            root = KIT_TAGS[game]
            wfile = os.path.join(root, wpath + '.weapon')
            if os.path.exists(wfile):
                self.refs = open(wfile, 'rb').read()
                folder = os.path.dirname(wfile)
                for f in os.listdir(folder):
                    if f.endswith('.projectile'):
                        self.refs += open(os.path.join(folder, f), 'rb').read()
        if game not in KIT_TAGS:
            for mid, g in db.mission_games.items():
                if g == game and weapon in db.ports_on_level(mid, scan=True):
                    import halo_patch
                    self.map = halo_patch.open_map(db._port_level_map(mid), game)
                    self.where = mid
                    break

    def ok(self, cls, path, exists_only=False):
        if self.game in KIT_TAGS:
            if '*' in path:
                return True                       # a pattern: resolved at patch time
            ext = KIT_EXT.get(cls)
            if not ext or not os.path.exists(os.path.join(KIT_TAGS[self.game], path + '.' + ext)):
                return False
            if cls in ('proj', 'jpt!') and self.refs and not exists_only:
                return path.encode('latin-1') in self.refs
            return True
        return self.map is not None and bool(self.map.find_tags(cls, path))

    def zoom(self, wpath):
        """(Magnification Levels, Magnification Range from) of the PORT's own weapon, or
        None when it cannot be read. Halo 1: the kit tag; later games: the built map."""
        if not wpath:
            return None
        if self.game in KIT_TAGS:
            f = os.path.join(KIT_TAGS[self.game], wpath + '.weapon')
            if not os.path.exists(f):
                return None
            import port_env  # noqa: F401  (reclaimer on the path)
            from reclaimer.hek.defs.weap import weap_def
            w = weap_def.build(filepath=f).data.tagdata.weap_attrs.aiming
            return int(w.zoom_levels), float(w.zoom_ranges[0])
        if self.map is None:
            return None
        import halo_enhancer as he
        import halo_patch
        found = self.map.find_tags('weap', wpath)
        plugin = halo_patch.PluginRegistry(
            he.CONFIG.get('assembly_plugins_dir'),
            (he.CONFIG.get('plugin_subdirs_by_game') or {}).get(self.game)).get('weap')
        if not found or plugin is None:
            return None
        levels = self.map.read_tag_field(found[0][1], 'Magnification Levels', plugin)
        rng = self.map.read_tag_field(found[0][1], 'Magnification Range', plugin)
        if levels is None or rng is None:
            return None
        return int(levels), float(rng[0] if isinstance(rng, (tuple, list)) else rng)


def zoom_ladders(levels, frm):
    """The Zoom card's inverse ladder per field for a weapon zooming `levels` stages
    from `frm` -- the shape every stock weapon's ladder has (Halo 1 Sniper, 2 stages
    from 2: levels =1,=0 / range *1,=0 / range max =2,=0). None = no innate zoom: the
    card GIVES a zoom (from_zero) and Zoom Time waits for a Zoom pick (requires_zoom)."""
    if levels <= 0:
        return None
    return {'Magnification Levels': ['=%d' % (levels - i) for i in range(1, levels + 1)],
            'Magnification Range': ['*1'] * (levels - 1) + ['=0'],
            'Magnification Range Max': ['=%g' % frm] * (levels - 1) + ['=0']}


def plan(weapon, only_cards=None, only_game=None):
    import halo_enhancer as he
    import weapon_ports
    db = he.ModifierDatabase(HALO_JSON)
    raw = json.load(open(HALO_JSON, encoding='utf-8'))
    weapons = raw[SECTION[0]][SECTION[1]]
    port_cards = copy.deepcopy(weapons.get(weapon) or {})
    report = []
    for game, ports in sorted(weapon_ports.load_catalog().items()):
        port = next((p for p in ports or () if p.get('weapon') == weapon), None)
        if not port or game in sum(INHERITS.values(), []) or (only_game and game != only_game):
            continue
        # a second donor may supply named cards (catalog 'card_donors': the Halo 1 Beam
        # Rifle aims and hits like the Sniper Rifle but heats and drains like the Plasma
        # Pistol it was built on); the main donor then skips those names
        extra = port.get('card_donors') or {}
        claimed = {n for names in extra.values() for n in names}
        for donor, only in [(port['donor'], None)] + [(d, set(n)) for d, n in extra.items()]:
            wpath = weapon_ports.weap_path(port)
            dtag = db.weap_tag_for(donor, game)
            dpath = dtag.split(' & ')[0][5:]
            dfolder = dpath.rsplit(chr(92), 1)[0]
            dbase = dpath.rsplit(chr(92), 1)[-1].replace(' ', '_')
            ptags = [r.get('tag') for r in port.get('balance') or () if r.get('tag')]
            check = Checker(db, game, weapon, wpath)
            targets_games = [game] + INHERITS.get(game, [])
            for name, dcard in (weapons.get(db.resolve_weapon(donor) or donor) or {}).items():
                if not isinstance(dcard, dict):
                    continue
                if (name not in only) if only is not None else (name in claimed):
                    continue
                mod = next((m for m in db.weapon_mods.get(db.resolve_weapon(donor) or donor, [])
                            if m['name'] == name), None)
                if mod is None or not db._game_ok(mod, game) or mod.get('ignore'):
                    continue
                # dual-wield cards only for a port that can be dual wielded (catalog
                # 'dual_wield': true) -- the SAW cannot (user, 2026-10-03)
                if name.startswith('Dual ') and not port.get('dual_wield'):
                    continue
                # donor cards the port has no use for (catalog 'skip_cards': the Halo 1 fuel
                # rod has no zoom, the Rocket Launcher does)
                if name in (port.get('skip_cards') or ()):
                    continue
                # --only: just these cards this run (a partial pass; the rest stays for later)
                if only_cards and name not in only_cards:
                    continue
                # the port may file a donor card under its own name (catalog 'card_map': the
                # Halo 1 Sentinel Beam's damage is 'Beam Damage' like its other games, where
                # the Plasma Rifle says 'Bullet Damage')
                name = (port.get('card_map') or {}).get(name, name)
                card = port_cards.get(name)
                if card is not None and game in _games(card):
                    continue                                     # already covered: never overwrite
                tag = _resolve(dcard.get('tag'), game, db.games)
                if not isinstance(tag, str) or not tag:
                    continue
                mapped, bad = [], None
                tag_map = port.get('tag_map') or {}
                for cls, path in _tag_parts(tag):
                    # the catalog's explicit donor -> port tag map wins (names that share no
                    # word: Halo 1's rocket -> the fuel rod's 'grunt fuel rod'); it only has
                    # to EXIST -- a damage effect reached through an effect tag is not named
                    # by the weapon or its projectile, so the reference check would refuse it
                    explicit = tag_map.get('%s %s' % (cls, path))
                    m = explicit or he.ModifierDatabase._port_tag(
                        '%s %s' % (cls, path), dpath, dfolder, dbase, wpath, ptags,
                        port.get('fp_animations'))
                    if m is None:
                        bad = 'no %s counterpart for %s' % (weapon, path)
                        break
                    mc, _s, mp = m.partition(' ')
                    if not check.ok(mc, mp, exists_only=bool(explicit)):
                        bad = '%s %s does not exist in %s' % (mc, mp, game)
                        break
                    mapped.append(m)
                if bad:
                    report.append((game, name, 'SKIPPED', bad))
                    continue
                # halo.json's form: the class once, on the first part
                tag = ' & '.join([mapped[0]] + [x.partition(' ')[2] for x in mapped[1:]])
                dtargets = _resolve(dcard.get('targets'), game, db.games) or []
                new_targets = []
                for t in dtargets:
                    if not isinstance(t, dict) or not he.target_applies(t, game):
                        continue
                    t = {k: (_resolve(v, game, db.games) if isinstance(v, dict) and k != 'set' else v)
                         for k, v in t.items() if k not in ('games', 'skip_games')}
                    t['games'] = list(targets_games)
                    new_targets.append(t)
                if not new_targets:
                    continue
                if name == 'Zoom':
                    # the inverse ladder says whether the weapon zooms innately
                    # (weapon_has_zoom, which gates Zoom Time): the PORT's zoom, never the
                    # donor's (the Halo 1 Brute Shot has none, its Rocket Launcher does)
                    z = check.zoom(wpath)
                    if z is None:
                        report.append((game, name, 'WARN', 'port zoom unreadable: donor ladder kept'))
                    else:
                        lad = zoom_ladders(*z)
                        for t in new_targets:
                            if t.get('field') in ('Magnification Levels', 'Magnification Range',
                                                  'Magnification Range Max'):
                                t.pop('inverse_steps', None)
                                if lad:
                                    t['inverse_steps'] = lad[t['field']]
                        report.append((game, name, 'ZOOM', '%d stage(s) from %g' % z))
                if card is None:                                  # donor-only card
                    card = {k: copy.deepcopy(v) for k, v in dcard.items()
                            if k not in ('game', 'tag', 'targets', 'skip_games')}
                    card['game'] = [game]
                    card['tag'] = {game: tag}
                    card['targets'] = new_targets
                    port_cards[name] = card
                    report.append((game, name, 'NEW', tag))
                else:                                             # extend the port's card
                    old_games = card.get('game') or []
                    # a single game may be written as a plain string ("Halo 3"): list()
                    # would split it into letters (Spike Rifle, 2026-10-08)
                    old_games = [old_games] if isinstance(old_games, str) else list(old_games)
                    if isinstance(card.get('tag'), str):
                        card['tag'] = {g: card['tag'] for g in old_games} or {'default': card['tag']}
                    card['tag'][game] = tag
                    if isinstance(card.get('targets'), list):
                        for t in card['targets']:
                            if isinstance(t, dict) and 'games' not in t:
                                # keep them where they were -- and target 'games' are matched
                                # LITERALLY, so a game that INHERITS (ODST from Halo 3) has to
                                # be named or it silently loses the target
                                pinned = list(old_games)
                                for base, kids in INHERITS.items():
                                    if base in pinned:
                                        pinned += [k for k in kids if k not in pinned]
                                t['games'] = pinned
                        card['targets'] += new_targets
                    else:
                        card.setdefault('targets', {})[game] = new_targets
                    card['game'] = old_games + [game]
                    report.append((game, name, 'EXTENDED', tag))
    return port_cards, report


ZOOM_FIELDS = ('Magnification Levels', 'Magnification Range', 'Magnification Range Max')


def refresh_zoom(weapon):
    """Re-set the inverse ladders on the port's EXISTING Zoom card, per game, from the
    port's own zoom (plan() never overwrites a card; this is the one rewrite it allows).
    Only targets pinned to that game ('games') are touched."""
    import halo_enhancer as he
    import weapon_ports
    db = he.ModifierDatabase(HALO_JSON)
    raw = json.load(open(HALO_JSON, encoding='utf-8'))
    cards = copy.deepcopy(raw[SECTION[0]][SECTION[1]].get(weapon) or {})
    zoom, report = cards.get('Zoom'), []
    if not isinstance(zoom, dict) or not isinstance(zoom.get('targets'), list):
        return cards, [('-', 'Zoom', 'SKIPPED', 'no Zoom card with a target list')]
    for game, ports in sorted(weapon_ports.load_catalog().items()):
        port = next((p for p in ports or () if p.get('weapon') == weapon), None)
        if not port or game in sum(INHERITS.values(), []) or game not in _games(zoom):
            continue
        wpath = weapon_ports.weap_path(port)
        z = Checker(db, game, weapon, wpath).zoom(wpath)
        if z is None:
            report.append((game, 'Zoom', 'WARN', 'port zoom unreadable: left as it is'))
            continue
        lad = zoom_ladders(*z)
        for t in zoom['targets']:
            if t.get('field') in ZOOM_FIELDS and game in (t.get('games') or ()):
                old = t.pop('inverse_steps', None)
                if lad:
                    t['inverse_steps'] = lad[t['field']]
                if old != t.get('inverse_steps'):
                    report.append((game, 'Zoom', 'LADDER', '%s %s -> %s' % (
                        t['field'], json.dumps(old), json.dumps(t.get('inverse_steps')))))
        report.append((game, 'Zoom', 'ZOOM', '%d stage(s) from %g' % z))
    return cards, report


# ---------------------------------------------------------------- house-style writer
def _inline(v):
    if isinstance(v, dict):
        return '{ ' + ', '.join('%s: %s' % (json.dumps(k), _inline(x)) for k, x in v.items()) + ' }'
    if isinstance(v, list):
        return '[' + ', '.join(_inline(x) for x in v) + ']'
    return json.dumps(v, ensure_ascii=False)


def _card_text(name, card, ind):
    t = '\t' * ind
    lines = ['%s%s: {' % (t, json.dumps(name, ensure_ascii=False))]
    keys = list(card)
    for i, k in enumerate(keys):
        v = card[k]
        end = ',' if i < len(keys) - 1 else ''
        if k == 'targets' and isinstance(v, list):
            lines.append('%s\t"targets": [' % t)
            for j, x in enumerate(v):
                lines.append('%s\t\t%s%s' % (t, _inline(x), ',' if j < len(v) - 1 else ''))
            lines.append('%s\t]%s' % (t, end))
        elif k == 'targets' and isinstance(v, dict):
            lines.append('%s\t"targets": {' % t)
            gk = list(v)
            for j, g in enumerate(gk):
                lines.append('%s\t\t%s: [' % (t, json.dumps(g)))
                for jj, x in enumerate(v[g]):
                    lines.append('%s\t\t\t%s%s' % (t, _inline(x), ',' if jj < len(v[g]) - 1 else ''))
                lines.append('%s\t\t]%s' % (t, ',' if j < len(gk) - 1 else ''))
            lines.append('%s\t}%s' % (t, end))
        else:
            lines.append('%s\t%s: %s%s' % (t, json.dumps(k), _inline(v), end))
    lines.append('%s}' % t)
    return lines


def write_block(text, weapon, cards):
    """Replace the weapon's block inside the Specific Weapon Modifier section."""
    nl = '\r\n' if '\r\n' in text else '\n'
    head = '\t\t\t%s: {' % json.dumps(weapon)
    sec = text.index('"%s"' % SECTION[1])
    a = text.index(head, sec)
    depth, i = 0, a + len(head) - 1
    while True:
        c = text[i]
        if c == '"':
            i += 1
            while text[i] != '"':
                i += 2 if text[i] == '\\' else 1
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                break
        i += 1
    body = [head]
    names = list(cards)
    for k, n in enumerate(names):
        lines = _card_text(n, cards[n], 4)
        if k < len(names) - 1:
            lines[-1] += ','
        body += lines
    body.append('\t\t\t}')
    return text[:a] + nl.join(body) + text[i + 1:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--weapon', required=True)
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--only', help='comma-separated card names: derive just these')
    ap.add_argument('--game', help='derive for this game only')
    ap.add_argument('--refresh-zoom', action='store_true',
                    help="re-set the existing Zoom card's ladders from the port's own zoom")
    ap.add_argument('--file', default=HALO_JSON, help='halo.json to rewrite (default: the live one)')
    a = ap.parse_args()
    if a.refresh_zoom:
        cards, report = refresh_zoom(a.weapon)
    else:
        cards, report = plan(a.weapon, [c.strip() for c in a.only.split(',')] if a.only else None, a.game)
    for game, name, what, info in report:
        print('%-12s %-26s %-8s %s' % (game, name, what, info))
    if a.write:
        text = open(a.file, encoding='utf-8', newline='').read()
        new = write_block(text, a.weapon, cards)
        json.loads(new)                                   # still valid JSON
        open(a.file, 'w', encoding='utf-8', newline='').write(new)
        print('written', a.file)


if __name__ == '__main__':
    main()
