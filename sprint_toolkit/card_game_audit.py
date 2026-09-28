"""Which cards are OFFERED in a game where they can do nothing? (card-stacking audit)

A card is offered in every game its `game` list names (none = every game; ODST also
through Halo 3, see game_inherits), minus `skip_games`. It can only do something there
if its tag resolves for that game AND at least one of its rows applies and names a
field. The splits copied their family's `game` list onto every new card, so a card whose
rows exist only from Halo 2 on was still offered in Halo 1 -- the user's suspicion.

Reports per card: offered games where it is INERT, and why (no tag / no rows). With
--write, sets each flagged card's `game` to the games where it works (textual edit,
halo.json formatting kept); a card that works nowhere is reported, not touched.

usage: card_game_audit.py [--write]
"""
import collections
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
sys.path[:0] = [TOOL, HERE]
import json_spans
import halo_enhancer as he

HALO_JSON = os.path.join(TOOL, 'halo.json')
GAMES = ['Halo 1', 'Halo 2', 'Halo 3', 'Halo 3: ODST', 'Halo Reach', 'Halo 4']


def offered_in(card):
    g = card.get('game') or card.get('games')
    games = [g] if isinstance(g, str) else list(g or [])
    if not games:
        out = list(GAMES)
    else:
        out = [x for x in GAMES if x in games or (x == 'Halo 3: ODST' and 'Halo 3' in games)]
    skip = card.get('skip_games') or []
    skip = [skip] if isinstance(skip, str) else skip
    return [x for x in out if x not in skip]


def works_in(card, game):
    tag = he.resolve_gamed(card.get('tag'), game, GAMES)
    if not isinstance(tag, str) or not tag.strip():
        return 'no tag'
    tg = card.get('targets')
    rows = he.resolve_gamed(tg, game, GAMES) if isinstance(tg, dict) else tg
    live = []
    for t in rows or []:
        if not isinstance(t, dict) or not he.target_applies(t, game):
            continue
        f = he.resolve_gamed(t.get('field'), game, GAMES)
        if f is None:
            continue
        live.append(t)
    return None if live else 'no rows'


def main():
    text = io.open(HALO_JSON, encoding='utf-8').read()
    doc = json.loads(text)
    flagged, dead = [], []
    for path, s, e in json_spans.card_spans(text):
        if not path or path[0] == 'Missions':
            continue
        card = json.loads(text[s:e])
        if 'tag' not in card or 'targets' not in card or card.get('ignore') or card.get('skull'):
            continue
        off = offered_in(card)
        why = {g: works_in(card, g) for g in off}
        bad = {g: r for g, r in why.items() if r}
        if not bad:
            continue
        good = [g for g in off if not why[g]]
        (flagged if good else dead).append((path, s, e, card, good, bad))
    lines = ['Cards offered in games where they do nothing.', '']
    lines.append('== works nowhere it is offered (%d) -- not changed' % len(dead))
    for path, s, e, card, good, bad in dead:
        lines.append('  %-70s %s' % (' / '.join(map(str, path[1:])), bad))
    lines.append('')
    lines.append('== inert in some offered games (%d) -- game list narrowed with --write' % len(flagged))
    by = collections.Counter()
    for path, s, e, card, good, bad in flagged:
        lines.append('  %-70s inert: %-40s -> game %s' % (
            ' / '.join(map(str, path[1:])), ', '.join('%s (%s)' % kv for kv in bad.items()), good))
        for g in bad:
            by[g] += 1
    lines.insert(1, 'inert card-games per game: %s' % dict(by))
    out = os.path.join(HERE, 'card_game_audit.txt')
    io.open(out, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('%d cards narrowable, %d dead; per game %s -> %s' % (len(flagged), len(dead), dict(by), out))
    if '--write' not in sys.argv:
        return
    for path, s, e, card, good, bad in sorted(flagged, key=lambda x: -x[1]):
        body = text[s:e]
        c = json.loads(body)
        # ODST comes along with Halo 3 unless it is itself inert
        keep = [g for g in good if not (g == 'Halo 3: ODST' and 'Halo 3' in good)]
        new_games = json.dumps(keep, ensure_ascii=False)
        skip = []
        if 'Halo 3' in good and 'Halo 3: ODST' in bad:
            skip = ['Halo 3: ODST']
        # replace or insert "game" right after the opening brace's first line
        k = '"game"' if '"game"' in body.split('"targets"')[0] else None
        if k:
            # the existing value: a string or a one-line list
            i = body.index('"game"')
            j = body.index(':', i) + 1
            dec = json.JSONDecoder()
            ws = len(body[j:]) - len(body[j:].lstrip())
            _v, end = dec.raw_decode(body, j + ws)
            body = body[:j] + ' ' + new_games + body[end:]
        else:
            nl = body.index('\n') if '\n' in body else None
            ind = body[nl + 1:].split('"')[0] if nl is not None else ' '
            body = body[:nl + 1] + ind + '"game": ' + new_games + ',\n' + body[nl + 1:] \
                if nl is not None else '{ "game": ' + new_games + ', ' + body[1:]
        if skip:
            nl = body.index('\n')
            ind = body[nl + 1:].split('"')[0]
            if '"skip_games"' not in body.split('"targets"')[0]:
                body = body[:nl + 1] + ind + '"skip_games": ' + json.dumps(skip) + ',\n' + body[nl + 1:]
        assert json.loads(body)
        text = text[:s] + body + text[e:]
    json.loads(text)
    io.open(HALO_JSON, 'w', encoding='utf-8', newline='').write(text)
    print('written')


if __name__ == '__main__':
    main()
