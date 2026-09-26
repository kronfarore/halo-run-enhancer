"""card-stacking: split every weapon's Zoom card and give it the zoom ladder.

Zoom used to carry Weapon Zoom Time too, which the user does not want tuned together
with the magnification (2026-09-27). Weapon Zoom Time moves to its own "Zoom Time" card
(same tag and games), and the Zoom card's magnification rows get:
  Magnification Levels     step +1 (max 2);  from zero: =1, =2
  Magnification Range      no step;          from zero: =2, =2
  Magnification Range Max  step *1.2;        from zero: =2, =4
`from_zero` is the per-pick ladder used when the weapon ships WITHOUT a zoom (vanilla
Magnification Levels 0 -- `zero_field` points Range and Max at that field, since they
ship at 1 on a zoomless gun): the first pick gives it 1 level at 2x, the second 2 levels up
to 4x. Past the end of the ladder the last entry holds, which is what saturates it.
Idempotent: a Zoom card with no Weapon Zoom Time row is left alone.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import json_spans

HALO_JSON = os.path.join(os.path.dirname(HERE), 'halo.json')
LADDER = {
    'Magnification Levels': {'step': '+1', 'max': 2, 'from_zero': ['=1', '=2']},
    'Magnification Range': {'step': None, 'from_zero': ['=2', '=2'],
                            'zero_field': 'Magnification Levels'},
    'Magnification Range Max': {'step': '*1.2', 'from_zero': ['=2', '=4'],
                                'zero_field': 'Magnification Levels'},
}


def dump_card(card, ind):
    """A card in halo.json's hand style: one key per line, one target per line."""
    lines = ['{']
    keys = list(card)
    for i, k in enumerate(keys):
        comma = ',' if i < len(keys) - 1 else ''
        if k == 'targets':
            lines.append('%s\t"targets": [' % ind)
            for j, t in enumerate(card[k]):
                tc = ',' if j < len(card[k]) - 1 else ''
                lines.append('%s\t\t%s%s' % (ind, json.dumps(t, ensure_ascii=False)
                                             .replace('{"', '{ "').replace('}', ' }'), tc))
            lines.append('%s\t]%s' % (ind, comma))
        else:
            lines.append('%s\t%s: %s%s' % (ind, json.dumps(k), json.dumps(card[k], ensure_ascii=False), comma))
    lines.append(ind + '}')
    return '\n'.join(lines)


def main():
    text = io.open(HALO_JSON, encoding='utf-8').read()
    zooms = [c for c in json_spans.card_spans(text)
             if len(c[0]) == 4 and c[0][:2] == ('Player Modifiers', 'Specific Weapon Modifier')
             and c[0][-1] == 'Zoom']
    done = 0
    for path, s, e in sorted(zooms, key=lambda c: -c[1]):
        card = json.loads(text[s:e])
        wzt = [t for t in card['targets'] if t.get('field') == 'Weapon Zoom Time']
        if not wzt:
            continue
        line_start = text.rfind('\n', 0, s) + 1
        ind = text[line_start:s].split('"')[0]           # the card key's indentation
        zoom = dict(card)
        zoom['desc'] = 'Magnification Levels, Magnification Range'
        new_t = []
        for t in card['targets']:
            if t.get('field') == 'Weapon Zoom Time':
                continue
            rule = LADDER.get(t.get('field'))
            if rule:
                t = {k: v for k, v in t.items() if k != 'step'}
                if rule['step']:
                    t = dict({'step': rule['step']}, **t)
                if rule.get('max') is not None:
                    t['max'] = rule['max']
                t['from_zero'] = rule['from_zero']
                if rule.get('zero_field'):
                    t['zero_field'] = rule['zero_field']
            new_t.append(t)
        zoom['targets'] = new_t
        zt = {k: v for k, v in card.items() if k not in ('targets', 'desc')}
        zt = dict({'desc': 'Weapon Zoom Time: how long zooming in and out takes'}, **zt)
        games = wzt[0].get('games')
        if games:
            zt['game'] = games
        zt['targets'] = [{k: v for k, v in wzt[0].items() if k != 'games'}]
        repl = dump_card(zoom, ind) + ',\n' + ind + '"Zoom Time": ' + dump_card(zt, ind)
        text = text[:s] + repl + text[e:]
        done += 1
    json.loads(text)
    io.open(HALO_JSON, 'w', encoding='utf-8', newline='').write(text)
    print('split %d Zoom cards' % done)


if __name__ == '__main__':
    main()
