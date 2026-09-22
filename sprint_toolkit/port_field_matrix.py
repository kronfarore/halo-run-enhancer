r"""Which of the ported weapon's fields reach each target game, and why the rest do not.

Every game spells its weapons differently, so a field that carries into Halo 1 may have
no counterpart in Halo 3 and vice versa. This lines the balance tables up side by side:
for each field of the SOURCE weapon, whether the target game got a row, and if not, the
reason the balance tool recorded -- so a gap is a decision rather than an oversight.

    python port_field_matrix.py [table.json ...]
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT = ['balance_SAW_Halo4_to_Halo1.json', 'balance_SAW_Halo4_to_Halo3_mgvel.json',
           'balance_SAW_Halo4_to_Halo2.json']


def load(path):
    d = json.load(open(os.path.join(HERE, path), encoding='utf-8'))
    got = {}
    for r in d['rows']:
        key = (r.get('card'), r.get('field'))
        if r.get('dst_field') and r.get('balanced') is not None:
            got[key] = ('ok', r['dst_field'])
        elif r.get('dst_field'):
            got[key] = ('no value', r.get('note') or '')
        else:
            got[key] = ('gap', (r.get('note') or '')[:44])
    return d['target'], got


def main():
    tables = sys.argv[1:] or DEFAULT
    loaded = []
    for t in tables:
        if os.path.exists(os.path.join(HERE, t)):
            loaded.append(load(t))
    if not loaded:
        raise SystemExit('no balance tables found')
    games = [g for g, _ in loaded]
    keys = sorted({k for _g, got in loaded for k in got})
    print('%-20s %-26s %s' % ('card', 'source field', '  '.join('%-14s' % g for g in games)))
    counts = {g: [0, 0] for g in games}
    for card, field in keys:
        cells = []
        for game, got in loaded:
            state = got.get((card, field))
            if state is None:
                cells.append('%-14s' % '-')
                continue
            kind, detail = state
            counts[game][0 if kind == 'ok' else 1] += 1
            cells.append('%-14s' % (detail[:14] if kind == 'ok' else kind.upper()))
        print('%-20s %-26s %s' % ((card or '')[:20], (field or '')[:26], '  '.join(cells)))
    print()
    for g in games:
        ok, gap = counts[g]
        print('%-14s %d field(s) carried, %d not' % (g, ok, gap))
    print('\nreasons for the gaps:')
    for game, got in loaded:
        why = {}
        for (card, field), (kind, detail) in got.items():
            if kind != 'ok':
                why.setdefault(detail or kind, []).append(field)
        print('   %s' % game)
        for reason, fields in sorted(why.items(), key=lambda kv: -len(kv[1])):
            print('      %-46s %s' % (reason[:46], ', '.join(sorted(set(fields)))[:60]))


if __name__ == '__main__':
    main()
