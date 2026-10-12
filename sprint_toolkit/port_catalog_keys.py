r"""Set the enhancer's own keys on a weapon_ports_catalog.json entry, under the shared kit lock.

The catalog is also rewritten by the port sessions (make_port_catalog_h1_ports takes the lock
too), so the enhancer's keys -- hands, tag_map, card_map, skip_cards, card_donors,
trigger_index, actor_flags -- go in through here rather than a hand edit that could race a
regeneration. The file is written exactly as make_port_catalog writes it (json.dump, indent 1).

    python port_catalog_keys.py --game "Halo 1" --weapon "Plasma Repeater" ^
        --set hands=\"two\" --set skip_cards=[\"Reload Time\"]
    python port_catalog_keys.py --game "Halo 1" --weapon DMR --show

Each --set is KEY=JSON; --unset KEY removes one.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
CATALOG = os.path.join(os.path.dirname(HERE), 'weapon_ports_catalog.json')
OWNED = ('hands', 'tag_map', 'card_map', 'skip_cards', 'card_donors', 'trigger_index',
         'actor_flags')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', required=True)
    ap.add_argument('--weapon', required=True)
    ap.add_argument('--set', action='append', default=[], metavar='KEY=JSON')
    ap.add_argument('--unset', action='append', default=[], metavar='KEY')
    ap.add_argument('--show', action='store_true')
    a = ap.parse_args()
    changes = []
    for s in a.set:
        k, _eq, v = s.partition('=')
        changes.append((k.strip(), json.loads(v)))
    for k, _v in changes:
        if k not in OWNED:
            raise SystemExit('%s is not an enhancer key (%s)' % (k, ', '.join(OWNED)))
    import kit_lock
    with kit_lock.held('port_catalog_keys %s / %s' % (a.game, a.weapon), owner='enhancer'):
        with open(CATALOG, encoding='utf-8') as f:
            cat = json.load(f)
        port = next((p for p in cat.get(a.game) or () if p.get('weapon') == a.weapon), None)
        if port is None:
            raise SystemExit('no %s entry for %s' % (a.game, a.weapon))
        if a.show:
            print(json.dumps({k: port[k] for k in OWNED if k in port}, indent=1))
        if not changes and not a.unset:
            return
        for k, v in changes:
            port[k] = v
        for k in a.unset:
            port.pop(k, None)
        with open(CATALOG, 'w', encoding='utf-8') as f:     # text mode: CRLF, as the generator
            json.dump(cat, f, indent=1)
        print('%s / %s: %s' % (a.game, a.weapon, ', '.join(
            ['%s set' % k for k, _v in changes] + ['%s removed' % k for k in a.unset])))


if __name__ == '__main__':
    main()
