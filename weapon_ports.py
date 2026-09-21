r"""weapon_ports.py -- weapons carried from one game into another (EXPERIMENTAL).

A port is built into the target game's tags with its SOURCE game's numbers, so it plays
like the weapon it came from. `weapon_ports_catalog.json` lists what exists and carries
the precomputed SUGGESTED BALANCE for each one:

    {game: [{weapon, source, desc, tags: {...}, balance: [{tag, class, field, block,
             value}, ...], anims: {reload: mult, swap: mult}}]}

`balance` is applied by the patcher BEFORE any card op (like the difficulty baseline), so
the balanced numbers become the vanilla a run's cards scale from. `anims` scales the
port's first-person animations by the same yardstick -- halo3_reload resamples them in the
map, so they can grow as well as shrink.

How the numbers are derived (sprint_toolkit/weapon_port_balance.py): a donor weapon that
exists in BOTH games (the SAW's donor is the Assault Rifle) is read field by field in each,
and every card field of the port moves by donor_target / donor_source. Ratios cancel the
engines' unit differences, so the result is already in the target game's stored units.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG_PATH = os.path.join(HERE, 'weapon_ports_catalog.json')


def load_catalog(path=CATALOG_PATH):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def ports_for(game, catalog=None):
    cat = catalog if catalog is not None else load_catalog()
    return list((cat or {}).get(str(game).strip()) or [])


def enabled_ports(game, config_ports, catalog=None):
    """The ports the run has switched on for this game, as catalog entries."""
    chosen = ((config_ports or {}).get(str(game).strip()) or {})
    return [p for p in ports_for(game, catalog)
            if (chosen.get(p.get('weapon')) or {}).get('enabled', p.get('default_on', False))]
