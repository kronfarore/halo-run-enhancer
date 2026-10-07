r"""Per-weapon configs of the Halo 1 weapon ports (H1_PORT_PLAN.md, phase 0).

One file per weapon (`ports_h1/<key>.py`, a dict `PORT`), so a port session edits its own
file and never the shared scripts. The scripts load their part of every config:

    section        read by
    -------------  ----------------------------------------------------------------------
    model          h1_h3_weapon_model.py      Halo 3 geometry + bitmaps + shaders
    retarget       h1_fp_retarget.py          Halo 3 FP animations onto Halo 1's arms
    pickable       h1_pickable_weapons.py     the weapon tag and everything it edits
    sounds         h1_port_sounds.py          Halo 3 audio -> tags + FMOD bank manifest
    catalog        make_port_catalog_h1_ports.py   weapon_ports_catalog.json entry
    firing_profile ai_firing_profile.py --port <key>   step 11 (Armed cards)
    test           h1_port_test_map.py        the dry test map
    backup         port_backup.py --game h1   extra folders/tags (most are derived)

Top-level keys every config has:
    order          int: the order the scripts process ports in (iteration order of the old
                   WEAPONS dicts; it decides e.g. which label a shared tag gets first)
    name           the catalog / halo.json weapon name (exactly halo.json's)
    source         'Halo 1' (restored), 'Halo 3', 'Halo Reach', 'Halo 4'
    status         'done' | 'reserved' (a stub: reservations + yardstick candidates only)
    reservations   indices and names no other port may take (see RESERVED_KEYS)
    yardstick      {'pick', 'reason', 'candidates': {...}} -- the pick is made WITH the
                   user at step 4a and recorded here; phase 0 only lists candidates

    import ports_h1
    ports_h1.section('pickable')   # {key: PORT['pickable']} in `order`
    ports_h1.load('smg')           # one config
"""
import importlib
import os
import pkgutil

HERE = os.path.dirname(os.path.abspath(__file__))
SECTIONS = ('model', 'retarget', 'pickable', 'sounds', 'catalog', 'firing_profile', 'test', 'field_audit',
            'backup')
RESERVED_KEYS = ('messages', 'icon', 'reticle', 'label', 'teach_from', 'sound_dir',
                 'weapon_dir')


def keys():
    """Every config's key (file name), in `order`."""
    found = [m.name for m in pkgutil.iter_modules([HERE]) if not m.name.startswith('_')]
    return sorted(found, key=lambda k: (load(k)['order'], k))


def load(key):
    return importlib.import_module('ports_h1.' + key).PORT


def all_ports():
    return [(k, load(k)) for k in keys()]


def section(name):
    """{key: PORT[name]} for every config that has the section, in `order`."""
    if name not in SECTIONS:
        raise KeyError(name)
    return {k: p[name] for k, p in all_ports() if p.get(name) is not None}


def by_name(name):
    """The config whose catalog name is `name` (halo.json's weapon name)."""
    for k, p in all_ports():
        if p['name'] == name:
            return k, p
    raise KeyError(name)


def check_reservations():
    """Every reserved value is unique across the configs. Returns a list of clashes."""
    seen, clashes = {}, []
    for k, p in all_ports():
        r = p.get('reservations', {})
        for field in RESERVED_KEYS:
            if field == 'teach_from' or r.get(field) is None:
                continue
            vals = r[field] if field == 'messages' else (r[field],)
            for v in vals:
                v = v.lower() if isinstance(v, str) else v
                if (field, v) in seen:
                    clashes.append('%s %r: %s and %s' % (field, v, seen[(field, v)], k))
                seen[(field, v)] = k
    return clashes
