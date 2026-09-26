"""Write a per-pick default `"step"` into every halo.json card target (card-stacking).

A card's magnitude used to be typed by hand and raised by hand each time the card was
drawn again. From card-stacking on, a target carries the op ONE pick applies ("*1.2",
"+1") and the patcher applies it once per pick, LINEARLY: *1.2 picked 3 times is
*1.6, +1 picked 3 times is +3.

Rules (user, 2026-09-27), in priority order:
  size       general cards 10% per pick (General Modifiers, cards on ai\\generic,
             Friend cards), specific cards 20%.
  direction  player-side cards step towards EASIER, enemy-side towards HARDER, read
             from harder_when / easier_when (target, then card). Without either, the
             direction the finished run's preset moved the field; failing that a
             guess (increase), reported.
  form       multiplicative where the rule applies. Where the preset ADDED, SUBTRACTED
             or SET the field, the rule cannot apply: the step is the preset value
             divided by the number of times the card was picked in the run.
  skipped    choice / set / derived / swap / sprint / follows_choice rows, and targets
             that are per-game variant dicts.

usage: card_steps.py [--write] [--presets F:\\magnitude_presets.json] [--run F:\\Run1.run]
Existing "step" keys are never overwritten (they are the user's overrides).
"""
import collections
import io
import json
import os
import sys

TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [TOOL, os.path.dirname(os.path.abspath(__file__))]
import json_spans
import halo_map as hm
import halo_patch as hp

HALO_JSON = os.path.join(TOOL, 'halo.json')
GAMES = ['Halo 1', 'Halo 2', 'Halo 3', 'Halo 3: ODST', 'Halo Reach', 'Halo 4']
SKIP_KEYS = ('choice', 'set', 'derived', 'map_swap', 'map_equip', 'sprint',
             'follows_choice', 'equip_drop', 'ignore')
PLAYER_SIDE = ('Player Modifiers', 'Equipment', 'Friend modifiers')
GENERAL_SECTIONS = ('General Modifiers', 'General modifiers')
LOWER_IS_BETTER = ('time', 'delay', 'error', 'penalty', 'cooldown', 'spread', 'noise',
                   'timeout', 'heat', 'recovery', 'deviation', 'wind', 'drain')


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def resolve(v, game):
    if not isinstance(v, dict):
        return v
    if game in v:
        return v[game]
    if 'default' in v:
        return v['default']
    for g in reversed(GAMES[:GAMES.index(game)]):
        if g in v:
            return v[g]
    return None


def card_games(card):
    g = card.get('game') or card.get('games')
    if isinstance(g, str):
        return [g]
    return list(g) if g else list(GAMES)


def fmt(x):
    return ('%.4f' % x).rstrip('0').rstrip('.')


def main():
    text = io.open(HALO_JSON, encoding='utf-8').read()
    doc = json.loads(text)
    presets = json.load(io.open(arg('--presets', r'F:\magnitude_presets.json'), encoding='utf-8'))
    run = json.load(io.open(arg('--run', r'F:\Run1.run'), encoding='utf-8'))
    counts = {}
    for e in hp.collect_effects(run['rounds']):
        tags = e['tag'] if isinstance(e['tag'], dict) else {'*': e['tag']}
        for v in tags.values():
            counts[(v, e['name'])] = e['count']

    def card_at(path):
        n = doc
        for k in path:
            n = n[k]
        return n

    edits, report = [], collections.Counter()
    lines = []
    for path, s, e in json_spans.target_spans(text):
        t = json.loads(text[s:e])
        card = card_at(path)
        label = ' / '.join(str(p) for p in path[1:])
        if 'field' not in t or any(t.get(k) not in (None, False) for k in SKIP_KEYS):
            report['skipped'] += 1
            continue
        side_player = path[0] in PLAYER_SIDE
        general = (path[1] in GENERAL_SECTIONS or path[0] == 'Friend modifiers'
                   or 'ai\\generic' in json.dumps(card.get('tag')))
        pct = 0.10 if general else 0.20
        # the finished run's preset for this card+field, any game, newest first
        pre, cnt = None, 1
        for g in reversed(card_games(card)):
            tag = resolve(t.get('tag') or card.get('tag'), g)
            fld = resolve(t['field'], g)
            if not isinstance(tag, str) or not isinstance(fld, str):
                continue
            v = presets.get('%s||%s||%s||%s' % (tag, path[-1], fld, g))
            po = hm.parse_operator(v) if isinstance(v, str) and v.strip() else None
            if po and not (po[0] == 'mul' and po[1] == 1.0) and not (
                    po[0] in ('add', 'sub') and po[1] == 0):
                pre = po
                cnt = counts.get((tag, path[-1]), 1) or 1
                break
        hw = t.get('harder_when') or card.get('harder_when')
        ew = t.get('easier_when') or card.get('easier_when')
        hw = resolve(hw, 'Halo 4') if isinstance(hw, dict) else hw
        ew = resolve(ew, 'Halo 4') if isinstance(ew, dict) else ew
        how = 'direction'
        if hw in ('increased', 'decreased') or ew in ('increased', 'decreased'):
            harder_up = (hw == 'increased') if hw else (ew == 'decreased')
            up = (not harder_up) if side_player else harder_up
        elif pre:
            op, val = pre
            up = (op == 'add' and val > 0) or (op == 'sub' and val < 0) or \
                 (op == 'mul' and val > 1) or op == 'set'
            how = 'preset'
        else:
            # Lower is better for whoever holds the card on times, delays, errors,
            # penalties, cooldowns, spread and noise; higher on everything else. The
            # holder is the player on player-side cards and the enemy on enemy cards,
            # and both want the field to move the way that helps THEM.
            f = json.dumps(t['field']).lower()
            lower_better = any(w in f for w in LOWER_IS_BETTER)
            up, how = (not lower_better), 'GUESS'
        if pre and pre[0] in ('add', 'sub'):
            per = abs(pre[1]) / cnt
            step = ('+' if up else '-') + fmt(per)
            form = 'preset/%d' % cnt
        elif pre and pre[0] == 'set':
            step = '=' + fmt(pre[1])
            form = 'preset set'
        else:
            step = '*' + fmt(1 + pct if up else 1 - pct)
            form = 'rule %d%%' % round(pct * 100)
        have = t.get('step')
        if have is None:
            edits.append((s, step))
        elif have != step:
            form += ' (kept %s)' % have
        report[how] += 1
        lines.append('%-6s %-9s %-11s %-62s %-40s %s' % (
            how, step, form, label[:62], str(t['field'])[:40],
            ('preset ' + ('%s %s' % pre if pre else '')) if pre else ''))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'card_steps_report.txt')
    io.open(out, 'w', encoding='utf-8').write(
        'counts: %s\n\n' % dict(report) + '\n'.join(sorted(lines)) + '\n')
    print(dict(report), '->', out)
    if '--write' in sys.argv:
        for s, step in sorted(edits, reverse=True):
            text = text[:s + 1] + ' "step": "%s",' % step + text[s + 1:]
        json.loads(text)                   # still valid JSON
        io.open(HALO_JSON, 'w', encoding='utf-8', newline='').write(text)
        print('wrote %d steps into halo.json' % len(edits))


if __name__ == '__main__':
    main()
