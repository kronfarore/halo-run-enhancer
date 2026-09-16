# -*- coding: utf-8 -*-
r"""behaviour_cards.py -- author the behaviour cards behaviour_census.py measured.

Built from the census JSON, never guessed: a field goes on an enemy's card only for the
games where at least one of that enemy's variants ships a real value (99/999 are the
engine's "disabled" placeholders and do not count).

New cards per enemy:
  * Evasion Properties -- Evasion Chance / Danger Threshold / Delay Timer / Proximity
    Threshold / Dive Retreat Chance. Halo 1 keeps its own actr set (Attacking/Defending
    Evasion Threshold, Evasion Seek-Cover Chance, Evasion Delay Time). Not "Evasion":
    the Watcher already has that card for its Bishop-specific triggers.
  * Search -- Search Time (range), Search Distance (Halo 3 on), Minimum Presearch Time
    (range, Halo 2/3/ODST) and Maximum Presearch Time (range). Halo 1: Target Search Time.
  * Defensive Cover -- Reach / Halo 4: the distances and scary threshold that decide
    when an enemy stops fighting aggressively and goes defensive.
  * Berserk Animation -- Elite (Halo 3, Reach) and Brute (Halo 3, ODST, Reach): the
    third-person `berserk` action's length, through the reload machinery.
  * Knight / Berserk (Halo 4), Brute / Vengeful Berserk (Halo 3, Reach).
Edited cards:
  * Dive From Grenade Chance gains Brace Grenade Chance (Reach / Halo 4) on the enemies
    that ship a Brace value -- grouped, and `inverse`, so raising Dive lowers Brace.
  * Elite Berserk gains Reach and Halo 4 rows (Halo 3's Elite style does not allow the
    shield-down berserk, so its fields there would be inert).

resolve_gamed falls back to the nearest EARLIER game, so every card carries an explicit
`game` list, and `skip_games: ["Halo 3: ODST"]` where ODST would inherit a Halo 3 row it
has no value for.

    python sprint_toolkit/behaviour_cards.py --census CENSUS.json            # report
    python sprint_toolkit/behaviour_cards.py --census CENSUS.json --apply
    python sprint_toolkit/behaviour_cards.py --census CENSUS.json --apply --file X.json
"""
import argparse
import collections
import io
import json
import os
import sys

TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HALO_JSON = os.path.join(TOOL, 'halo.json')
T = '\t'
S = chr(92)
GAMES = ['Halo 1', 'Halo 2', 'Halo 3', 'Halo 3: ODST', 'Halo Reach', 'Halo 4']
DISABLED = 99.0


# ----------------------------------------------------------------------------- census
class Census:
    def __init__(self, path):
        self.r = json.load(io.open(path, encoding='utf-8'))

    def values(self, game, cls, block, field, enemy):
        key = '%s: %s' % (cls, field if not block else block + '/' + field)
        rows = (((self.r.get(game) or {}).get('fields') or {}).get(key) or {}).get(enemy)
        return [v for _t, v in (rows or [])]

    def live(self, game, cls, block, field, enemy):
        """A meaningful value: some variant ships it, and not only as a 99 placeholder."""
        vals = self.values(game, cls, block, field, enemy)
        return bool(vals) and not all(v >= DISABLED for v in vals)


# ----------------------------------------------------------------------------- tags
def enemy_tags(doc):
    """{enemy: {game: most common char/actr tag string}} from the enemy's own cards."""
    se = doc['Enemy modifiers']['Specific Enemy modifier']
    out = {}
    for enemy, cards in se.items():
        per = {g: collections.Counter() for g in GAMES}
        for c in cards.values():
            if not isinstance(c, dict):
                continue
            tag, gl = c.get('tag'), c.get('game')
            gl = [gl] if isinstance(gl, str) else gl
            for g in GAMES:
                if gl and g not in gl:
                    continue
                v = tag.get(g, tag.get('default')) if isinstance(tag, dict) else tag
                if (isinstance(v, str) and v.split(' ', 1)[0] in ('char', 'actr')
                        and ('ai' + S + 'generic') not in v):
                    per[g][v] += 1
        out[enemy] = {g: c.most_common(1)[0][0] for g, c in per.items() if c}
    return out


def tag_for(tags, enemy, game):
    """The enemy's tag for this game, or the nearest earlier game's (same rule the
    enhancer resolves by)."""
    t = tags.get(enemy) or {}
    for g in reversed(GAMES[:GAMES.index(game) + 1]):
        if g in t:
            return t[g]
    return None


# ----------------------------------------------------------------------------- targets
def tgt(field, block=None, **kw):
    d = {'field': field}
    if block:
        d['block'] = block
    d.update(kw)
    return d


def build_evasion(cen, enemy):
    per = {}
    for g in GAMES:
        rows = []
        if g == 'Halo 1':
            for f, kw in (('Attacking Evasion Threshold', dict(harder_when='decreased', min=0)),
                          ('Defending Evasion Threshold', dict(harder_when='decreased', min=0)),
                          ('Evasion Seek-Cover Chance', dict(harder_when='increased', min=0, max=1)),
                          ('Evasion Delay Time', dict(harder_when='decreased', min=0))):
                if cen.live(g, 'actr', None, f, enemy):
                    rows.append(tgt(f, **kw))
        else:
            B = 'Evasion Properties'
            for f, kw in (('Evasion Chance', dict(harder_when='increased', min=0, max=1)),
                          ('Evasion Danger Threshold', dict(harder_when='decreased', min=0)),
                          ('Evasion Delay Timer', dict(harder_when='decreased', min=0)),
                          ('Evasion Proximity Threshold', dict(harder_when='increased', min=0)),
                          ('Dive Retreat Chance', dict(harder_when='increased', min=0, max=1))):
                if cen.live(g, 'char', B, f, enemy):
                    rows.append(tgt(f, B, **kw))
        if rows:
            per[g] = rows
    return per


def _range(cen, g, cls, block, name, enemy, group, **kw):
    """Both ends of a range when the low end is live (they are one setting)."""
    if not cen.live(g, cls, block, name, enemy):
        return []
    return [tgt(name, block, group=group, **kw), tgt(name + ' Max', block, group=group, **kw)]


def build_search(cen, enemy):
    per = {}
    for g in GAMES:
        rows = []
        if g == 'Halo 1':
            rows += _range(cen, g, 'actr', None, 'Target Search Time', enemy, 'Search Time',
                           harder_when='increased', min=0)
        else:
            SP, PP = 'Search Properties', 'Pre-Search Properties'
            rows += _range(cen, g, 'char', SP, 'Search Time', enemy, 'Search Time',
                           harder_when='increased', min=0)
            if cen.live(g, 'char', SP, 'Search Distance', enemy):
                rows.append(tgt('Search Distance', SP, harder_when='increased', min=0))
            rows += _range(cen, g, 'char', PP, 'Minimum Presearch Time', enemy,
                           'Minimum Presearch Time', min=0)
            rows += _range(cen, g, 'char', PP, 'Maximum Presearch Time', enemy,
                           'Maximum Presearch Time', min=0)
        if rows:
            per[g] = rows
    return per


def build_defensive(cen, enemy):
    per = {}
    B = 'Cover Properties'
    for g in ('Halo Reach', 'Halo 4'):
        rows = [tgt(f, B, min=0) for f in ('Minimum Defensive Distance From Target',
                                           'Minimum Defensive Distance From Cover',
                                           'Always Defensive Scary Threshold')
                if cen.live(g, 'char', B, f, enemy)]
        if rows:
            per[g] = rows
    return per


def berserk_rows(cen, g, enemy, harder_more):
    """The shield-down berserk set. `harder_more`: does MORE berserking make the enemy
    harder (a charging Knight) or easier (an Elite that roars in place)?"""
    more = 'increased' if harder_more else 'decreased'
    less = 'decreased' if harder_more else 'increased'
    CP = 'Charge Properties'
    rows = []
    if cen.live(g, 'char', CP, 'Beserk Cooldown', enemy):
        rows.append(tgt('Beserk Cooldown', CP, harder_when=less, min=0))
    rows += _range(cen, g, 'char', CP, 'Shield-Down Berserk Chance', enemy,
                   'Shield-Down Berserk Chance', harder_when=more, min=0, max=1)
    if not any(r['field'].startswith('Shield-Down Berserk Chance') for r in rows) and \
            cen.live(g, 'char', CP, 'Shield-Down Berserk Chance Max', enemy):
        rows += [tgt('Shield-Down Berserk Chance', CP, group='Shield-Down Berserk Chance',
                     harder_when=more, min=0, max=1),
                 tgt('Shield-Down Berserk Chance Max', CP, group='Shield-Down Berserk Chance',
                     harder_when=more, min=0, max=1)]
    rows += _range(cen, g, 'char', CP, 'Shield-Down Berserk Ranges', enemy,
                   'Shield-Down Berserk Range', harder_when=more, min=0)
    if cen.live(g, 'char', CP + '/Difficulty Limits', 'Maximum Berserk Count', enemy):
        rows.append(tgt('Maximum Berserk Count', CP + '/Difficulty Limits', index='all',
                        harder_when=more, min=0))
    return rows


# ----------------------------------------------------------------------------- emit
def jv(v):
    return json.dumps(v, ensure_ascii=False)


def emit_target(t):
    return '{ ' + ', '.join('%s: %s' % (jv(k), jv(v)) for k, v in t.items()) + ' }'


def emit_card(name, card, depth=4):
    """One card as halo.json-style text lines (tabs, one target per line)."""
    d = T * depth
    out = [d + '%s: {' % jv(name)]
    body = []
    for k in ('desc', 'debug_desc', 'harder_when', 'game', 'skip_games'):
        if card.get(k) is not None:
            body.append([d + T + '%s: %s' % (jv(k), jv(card[k]))])
    tag = card['tag']
    if isinstance(tag, dict):
        inner = [d + T * 2 + '%s: %s' % (jv(g), jv(v)) for g, v in tag.items()]
        body.append([d + T + '"tag": {'] + [l + ',' for l in inner[:-1]] + [inner[-1],
                                                                            d + T + '}'])
    else:
        body.append([d + T + '"tag": %s' % jv(tag)])
    targets = card['targets']
    if isinstance(targets, dict):
        blk = [d + T + '"targets": {']
        items = list(targets.items())
        for i, (g, rows) in enumerate(items):
            blk.append(d + T * 2 + '%s: [' % jv(g))
            blk += [d + T * 3 + emit_target(r) + (',' if j < len(rows) - 1 else '')
                    for j, r in enumerate(rows)]
            blk.append(d + T * 2 + ']' + (',' if i < len(items) - 1 else ''))
        blk.append(d + T + '}')
    else:
        blk = [d + T + '"targets": [']
        blk += [d + T * 2 + emit_target(r) + (',' if j < len(targets) - 1 else '')
                for j, r in enumerate(targets)]
        blk.append(d + T + ']')
    body.append(blk)
    for i, lines in enumerate(body):
        if i < len(body) - 1:
            lines[-1] += ','
        out += lines
    out.append(d + '}')
    return out


def gamed_card(name, per, tags, enemy, desc, debug_desc, extra_tag=None):
    games = [g for g in GAMES if g in per]
    tag = {}
    for g in games:
        t = (extra_tag or {}).get(g) or tag_for(tags, enemy, g)
        if t:
            tag[g] = t
    card = {'desc': desc, 'debug_desc': debug_desc, 'game': games, 'tag': tag,
            'targets': {g: per[g] for g in games}}
    # ODST inherits Halo 3's row; refuse it where ODST ships nothing for this enemy.
    if 'Halo 3' in per and 'Halo 3: ODST' not in per and 'Halo 3: ODST' not in games:
        card['skip_games_odst_check'] = True
    return card


# ----------------------------------------------------------------------------- text ops
class Doc:
    def __init__(self, path):
        self.path = path
        self.lines = io.open(path, encoding='utf-8').read().split('\n')
        self.se = next(i for i, l in enumerate(self.lines)
                       if l == T * 2 + '"Specific Enemy modifier": {')

    def enemy_range(self, enemy):
        s = next(i for i in range(self.se, len(self.lines))
                 if self.lines[i] == T * 3 + '"%s": {' % enemy)
        e = next(i for i in range(s + 1, len(self.lines))
                 if self.lines[i] in (T * 3 + '},', T * 3 + '}'))
        return s, e

    def card_range(self, enemy, name):
        s, e = self.enemy_range(enemy)
        c = next((i for i in range(s, e) if self.lines[i] == T * 4 + '%s: {' % jv(name)), None)
        if c is None:
            return None
        ce = next(i for i in range(c + 1, e + 1) if self.lines[i] in (T * 4 + '},', T * 4 + '}'))
        return c, ce

    def add_card(self, enemy, name, card):
        if self.card_range(enemy, name):
            raise SystemExit('%s / %s already exists' % (enemy, name))
        s, e = self.enemy_range(enemy)
        last = e - 1
        if not self.lines[last].endswith(','):
            self.lines[last] += ','
        self.lines[e:e] = emit_card(name, card)

    def replace_card(self, enemy, name, card):
        c, ce = self.card_range(enemy, name)
        trail = ',' if self.lines[ce].endswith(',') else ''
        new = emit_card(name, card)
        new[-1] += trail
        self.lines[c:ce + 1] = new

    def text(self):
        return '\n'.join(self.lines)


# ----------------------------------------------------------------------------- plan
EVASION_DESC = "How readily they dodge -- chance, how much danger sets it off, and how soon they try again."
EVASION_DEBUG = ("Evasion Properties, only the fields this enemy really ships per game "
                 "(measured on every map by sprint_toolkit/behaviour_census.py; 99/999 "
                 "are disabled placeholders and were left out). Halo 1 keeps its own actr "
                 "set: attacking/defending evasion thresholds, the chance to seek cover "
                 "when evading, and the delay between evasions. No card drove any of "
                 "this before -- the coverage audit only reports fields some other game "
                 "already cards, and none did.")
SEARCH_DESC = "How long and how far they hunt for you once they lose track of you."
SEARCH_DEBUG = ("Search Properties (Search Time range; Search Distance from Halo 3 on) and "
                "Pre-Search Properties (the suppress/uncover phase before the hunt: "
                "Minimum Presearch Time in Halo 2/3/ODST, Maximum Presearch Time in every "
                "game from Halo 2). Halo 1's equivalent is the actr Target Search Time. "
                "Only fields this enemy really ships are offered, per game.")
DEFENSIVE_DESC = "When they stop pressing you and play it safe."
DEFENSIVE_DEBUG = ("Reach and Halo 4 Cover Properties: an enemy turns defensive when its "
                   "target is closer than Minimum Defensive Distance From Target, when "
                   "cover is further than Minimum Defensive Distance From Cover allows, "
                   "or always once the target's scariness passes Always Defensive Scary "
                   "Threshold. Raising the distances makes them go defensive more often.")
BERSERK_ANIM_DESC = "How long their berserk roar takes. *0.5 is twice as fast."
BERSERK_ANIM_DEBUG = ("Scales the third-person `berserk` ANIMATIONS in the enemy's graph -- "
                      "the same machinery as Reload Time and Weapon Swap Speed, matching the "
                      "`berserk` action instead. Measured at 30fps: Halo 3 Elite 45 frames "
                      "(1.5s, five weapon classes), Reach Elite 47-48, ODST Brute 43-46. "
                      "For an Elite the roar is pure downtime, so a SHORTER roar is harder. "
                      "Halo 4 has no animation-graph layout in the machinery yet.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--census', required=True)
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--file', default=HALO_JSON)
    a = ap.parse_args()
    cen = Census(a.census)
    doc_json = json.load(io.open(a.file, encoding='utf-8'))
    tags = enemy_tags(doc_json)
    se = doc_json['Enemy modifiers']['Specific Enemy modifier']
    doc = Doc(a.file)
    report = []

    def finish(card, per):
        if card.pop('skip_games_odst_check', False):
            card['skip_games'] = ['Halo 3: ODST']
        return card

    # --- new per-enemy behaviour cards
    for enemy in se:
        for name, builder, desc, dbg in (
                ('Evasion Properties', build_evasion, EVASION_DESC, EVASION_DEBUG),
                ('Search', build_search, SEARCH_DESC, SEARCH_DEBUG),
                ('Defensive Cover', build_defensive, DEFENSIVE_DESC, DEFENSIVE_DEBUG)):
            per = builder(cen, enemy)
            per = {g: rows for g, rows in per.items() if tag_for(tags, enemy, g)}
            if not per:
                continue
            # ODST inherits Halo 3: drop an ODST row identical in shape to Halo 3's
            if 'Halo 3' in per and 'Halo 3: ODST' in per and \
                    [r['field'] for r in per['Halo 3']] == [r['field'] for r in per['Halo 3: ODST']]:
                del per['Halo 3: ODST']
                odst_has = True
            else:
                odst_has = 'Halo 3: ODST' in per
            card = gamed_card(name, per, tags, enemy, desc, dbg)
            if 'Halo 3' in per and not odst_has:
                card['skip_games_odst_check'] = True
            else:
                card.pop('skip_games_odst_check', None)
            finish(card, per)
            report.append((enemy, name, card['game'],
                           sum(len(r) for r in card['targets'].values())))
            if a.apply:
                doc.add_card(enemy, name, card)

    # --- Brace Grenade Chance on the Dive cards (inverse, grouped)
    brace = []
    for enemy in se:
        games = [g for g in ('Halo Reach', 'Halo 4')
                 if cen.live(g, 'char', 'Movement Properties', 'Brace Grenade Chance', enemy)]
        rng = doc.card_range(enemy, 'Dive From Grenade Chance')
        if not games or not rng:
            continue
        brace.append((enemy, games))
        if not a.apply:
            continue
        c, ce = rng
        body = doc.lines[c:ce + 1]
        ti = next(i for i, l in enumerate(body) if l.strip().startswith('"targets": ['))
        te = next(i for i in range(ti + 1, len(body)) if body[i].strip() == ']')
        dive_line = body[te - 1]
        dive = json.loads(dive_line.strip().rstrip(','))
        dive['group'] = 'Grenade Reaction'
        ind = dive_line[:len(dive_line) - len(dive_line.lstrip())]
        brace_t = tgt('Brace Grenade Chance', 'Movement Properties', games=games,
                      inverse=True, group='Grenade Reaction', min=0, max=1)
        body[te - 1:te] = [ind + emit_target(dive) + ',', ind + emit_target(brace_t)]
        for i, l in enumerate(body):
            if l.strip().startswith('"desc":'):
                body[i] = (l[:len(l) - len(l.lstrip())] + '"desc": "Chance of diving away '
                           'from a grenade. Where the enemy can also brace (Reach, Halo 4), '
                           'raising the dive chance lowers the brace chance.",')
                break
        doc.lines[c:ce + 1] = body

    # --- Elite Berserk: add Reach and Halo 4
    elite_per = {g: berserk_rows(cen, g, 'Elite', harder_more=False)
                 for g in ('Halo Reach', 'Halo 4')}
    elite_per = {g: r for g, r in elite_per.items() if r}
    if a.apply and elite_per:
        old = se['Elite']['Elite Berserk']
        h1 = [{k: v for k, v in t.items() if k != 'games'} for t in old['targets']]
        card = {'desc': old['desc'],
                'debug_desc': (old.get('debug_desc', '') + " Reach and Halo 4 bring the "
                               "berserk back as the shield-down berserk the Elite's style "
                               "allows (with stuck-with-grenade and surprise berserks, which "
                               "have no numbers): the chance and range once shields drop, "
                               "the cooldown between berserks and the per-difficulty maximum "
                               "count. Halo 3 ships those fields on the Elite too, but its "
                               "style does not allow the shield-down berserk, so they are "
                               "inert there and left out."),
                'game': ['Halo 1'] + list(elite_per),
                'tag': {'Halo 1': old['tag']['Halo 1'],
                        **{g: tag_for(tags, 'Elite', g) for g in elite_per}},
                'targets': {'Halo 1': h1, **elite_per}}
        doc.replace_card('Elite', 'Elite Berserk', card)

    # --- Knight / Berserk (Halo 4)
    knight = berserk_rows(cen, 'Halo 4', 'Knight', harder_more=True)
    if cen.live('Halo 4', 'char', 'Charge Properties', 'Play Berserk Animation Chance When Stuck',
                'Knight'):
        knight.append(tgt('Play Berserk Animation Chance When Stuck', 'Charge Properties',
                          harder_when='increased', min=0, max=1))
    if knight and a.apply:
        doc.add_card('Knight', 'Berserk', {
            'desc': 'How readily Knights berserk and rush you.',
            'debug_desc': ("Halo 4 Charge Properties the Knight really ships: the "
                           "shield-down berserk (chance and range once its shield drops), "
                           "the cooldown between berserks, the per-difficulty maximum "
                           "count, and the chance to play the berserk animation when it is "
                           "stuck. Its style allows the shield-down and stuck-with-grenade "
                           "berserks. For a Knight berserking is a charge at you, so more "
                           "of it is harder."),
            'game': ['Halo 4'], 'tag': tag_for(tags, 'Knight', 'Halo 4'), 'targets': knight})

    # --- Brute / Vengeful Berserk (Halo 3 leader abandoned, Reach friendly/peer/leader killed)
    CP = 'Charge Properties'
    vb = {}
    if cen.live('Halo 3', 'char', CP, 'Leader Abandoned Berserk Chance', 'Brute'):
        vb['Halo 3'] = [tgt('Leader Abandoned Berserk Chance', CP, harder_when='increased',
                            min=0, max=1)]
    reach = [tgt(f, CP, harder_when='increased', min=0, **({'max': 1} if 'Chance' in f else {}))
             for f in ('Leader Killed Berserk Chance', 'Peer Killed Berserk Chance',
                       'Friendly Killed Maximum Berserk Distance')
             if cen.live('Halo Reach', 'char', CP, f, 'Brute')]
    if reach:
        vb['Halo Reach'] = reach
    if vb and a.apply:
        card = gamed_card('Vengeful Berserk', vb, tags, 'Brute',
                          'How readily Brutes berserk when their leader or pack falls.',
                          "Halo 3: the chance a Brute berserks when its leader abandons it. "
                          "Reach replaced that with killed-ally triggers: the chance when its "
                          "leader or a peer dies, and how close the death must be. ODST "
                          "ships none of it on the Brute, so ODST is skipped.")
        card.pop('skip_games_odst_check', None)
        card['skip_games'] = ['Halo 3: ODST']
        doc.add_card('Brute', 'Vengeful Berserk', card)

    # --- Berserk Animation (Elite H3/Reach, Brute H3/ODST/Reach)
    anim = [('Elite', {'Halo 3': 'jmad objects' + S + 'characters' + S + 'elite' + S + 'elite',
                       'Halo Reach': 'jmad objects' + S + 'characters' + S + 'elite_ai' + S + 'elite_ai'},
             'decreased'),
            ('Brute', {'Halo 3': 'jmad objects' + S + 'characters' + S + 'brute' + S + 'brute',
                       'Halo 3: ODST': 'jmad objects' + S + 'characters' + S + 'brute' + S + 'brute',
                       'Halo Reach': 'jmad objects' + S + 'characters' + S + 'brute' + S + 'brute'},
             'decreased')]
    for enemy, jt, hw in anim:
        if a.apply:
            doc.add_card(enemy, 'Berserk Animation', {
                'desc': BERSERK_ANIM_DESC, 'debug_desc': BERSERK_ANIM_DEBUG,
                'harder_when': hw, 'game': list(jt), 'tag': jt,
                'targets': [tgt('Berserk Animation', berserk_anim=True)]})

    for enemy, name, games, n in report:
        print('  %-20s %-20s %2d rows  %s' % (enemy, name, n, games))
    print('  brace added to Dive cards: %s' % brace)
    print('  Elite Berserk rows: %s' % {g: len(r) for g, r in elite_per.items()})
    print('  Knight Berserk rows: %d ; Brute Vengeful Berserk: %s'
          % (len(knight), {g: len(r) for g, r in vb.items()}))
    if a.apply:
        out = doc.text()
        json.loads(out)
        io.open(a.file, 'w', encoding='utf-8', newline='').write(out)
        print('written: %s' % a.file)
    else:
        print('(report only -- pass --apply)')


if __name__ == '__main__':
    main()
