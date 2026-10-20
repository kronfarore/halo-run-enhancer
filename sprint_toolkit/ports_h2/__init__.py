r"""Per-weapon configs of the Halo 2 weapon ports (H2_PORT_PLAN.md, phase 0, 2026-10-20).

One file per weapon (`ports_h2/<key>.py`, a dict `PORT`), so a port session edits its own
file and never the shared scripts -- Halo 1's ports_h1 shape. The Halo 2 pipeline is the
SAW's (PORTING.md "## Halo 2"), its h2_saw_*.py steps generalized into h2_port_*.py tools
that read their SECTION of a config (`python h2_port_<step>.py <key> ...`); the old
h2_saw_*.py names stay as thin wrappers that run the same tool for key 'saw'.

    section        step  read by
    -------------  ----  -------------------------------------------------------------------
    geometry        1    h2_port_geometry.py       source mesh -> H2 JMS on the donor skeleton
    textures        2    h2_port_textures.py       source maps -> H2 bitmaps (height bump), shaders
    weapon          3    h2_port_weapon.py         own weapon / projectile / effects (clone+wire)
    numbers         4    h2_port_numbers.py        the source weapon's own values
    yardstick_fields 4b  h2_port_yardstick.py      fields no card covers -> the yardstick donor's
    collision       5    h2_port_collision.py      the donor's authored hull, scaled per axis
    meter           7    h2_port_meter.py          ammo tick art + the HUD clone + backpack icon
    hud_plate       7    h2_port_hud_plate.py      the weapon symbol painted into its plate
    reticle         7    h2_port_reticle.py        the source game's crosshair, own bitmap
    scope           7    h2_port_scope.py          blank scope widgets (non-zooming port)
    glyph           8    h2_port_glyph.py          pickup icon at the reserved codepoint, 8 fonts
    messages        8    h2_port_messages.py       own pickup lines + repoint (any prefix length)
    animations      9    h2_port_animations.py     own FP graphs per species + their sounds
    retime          9    h2_anim_retime.py         (already generic: the invocations are recorded)
    sounds         10    h2_port_sounds.py         own sounds (classic, Opus) + repoint
    residency       -    h2_port_residency.py      palette entry in every level's weapons resource
    test            -    h2_port_test_map.py       the dry test map (--level/--stage/--restore)
    catalog         -    make_port_catalog_h2.py   weapon_ports_catalog.json 'Halo 2' entry
    firing_profile 11    (Armed: see H2_PORT_PLAN 0.5 -- the enhancer session's side)
    backup          -    port_backup.py --game h2  extra folders/tags (most are derived)

Top-level keys every config has:
    order          int, processing order
    name           the catalog / halo.json weapon name
    source         'Halo 3' | 'Halo Reach' | 'Halo 4'
    status         'done' | 'reserved' (a stub) | 'in progress' | 'rework' -- proofs and
                   shipping builds treat every status but 'done' as in progress
    reservations   names no other port may take (RESERVED_KEYS); see check_reservations()
    yardstick      {'pick', 'reason', 'candidates'}: the pick is made WITH the user at step 4a
    donor          {'weapon': the Halo 2 weapon tag the port's weapon is cloned from, why}

    import ports_h2
    ports_h2.load('saw'); ports_h2.section('geometry'); ports_h2.check_reservations()
"""
import importlib
import os
import pkgutil

HERE = os.path.dirname(os.path.abspath(__file__))
SECTIONS = ('geometry', 'textures', 'weapon', 'numbers', 'yardstick_fields', 'collision', 'meter',
            'hud_plate', 'reticle', 'scope', 'glyph', 'messages', 'animations', 'retime', 'sounds',
            'residency', 'test', 'catalog', 'firing_profile', 'backup')
#: every value here must be unique across the configs (case-insensitive)
RESERVED_KEYS = ('message_prefix', 'glyph', 'weapon_dir', 'effects_dir', 'fp_graph', 'hud',
                 'hud_bitmap_prefix', 'sound_dir', 'test_level')
#: test levels may be shared over time, not at once -- only checked among ports in progress
SHARED_OVER_TIME = ('test_level',)

#: Halo 2's 13 campaign levels (h2_batch.LEVELS order); residency covers ALL of them, 01b
#: included (user, 2026-10-20)
LEVELS = ('01b_spacestation', '03a_oldmombasa', '03b_newmombasa', '04a_gasgiant', '04b_floodlab',
          '05a_deltaapproach', '05b_deltatowers', '06a_sentinelwalls', '06b_floodzone',
          '07a_highcharity', '08a_deltacliffs', '07b_forerunnership', '08b_deltacontrol')
SPECIES = ('masterchief', 'dervish')


def keys():
    found = [m.name for m in pkgutil.iter_modules([HERE]) if not m.name.startswith('_')]
    return sorted(found, key=lambda k: (load(k)['order'], k))


def load(key):
    return importlib.import_module('ports_h2.' + key).PORT


def all_ports():
    return [(k, load(k)) for k in keys()]


def section(name):
    if name not in SECTIONS:
        raise KeyError(name)
    return {k: p[name] for k, p in all_ports() if p.get(name) is not None}


def get(key, name):
    """One config's section, or SystemExit naming what is missing."""
    p = load(key)
    if p.get(name) is None:
        raise SystemExit('ports_h2/%s.py has no %r section yet' % (key, name))
    return p[name]


def by_name(name):
    for k, p in all_ports():
        if p['name'] == name:
            return k, p
    raise KeyError(name)


def done_keys():
    return [k for k, p in all_ports() if p.get('status') == 'done']


def busy_keys():
    return [k for k, p in all_ports() if p.get('status') != 'done']


def owned_dirs(p):
    """Kit-relative folders a port OWNS outright (tags and data), from its reservations."""
    r = p.get('reservations') or {}
    out = [r.get('weapon_dir'), r.get('effects_dir'), r.get('sound_dir')]
    if r.get('fp_graph'):
        out += [r'objects\characters\%s\fp\%s' % (sp, os.path.dirname(r['fp_graph']))
                for sp in SPECIES]
    return [d for d in out if d]


def owned_files(p):
    """Kit-relative tag files a port owns inside SHARED folders (HUD + its bitmaps)."""
    r = p.get('reservations') or {}
    out = []
    if r.get('hud'):
        out.append(r['hud'] + '.new_hud_definition')
    pre = r.get('hud_bitmap_prefix')
    if pre:
        nh = r'ui\hud\bitmaps\new_hud'
        out += [nh + r'\meters\%smeter.bitmap' % pre, nh + r'\backgrounds\%sbkd.bitmap' % pre,
                nh + r'\crosshairs\%sreticle.bitmap' % pre, nh + r'\%sbackpack.bitmap' % pre,
                nh + r'\scope_masks\%sblank.bitmap' % pre]
    return out


def check_reservations():
    """Every reserved value is unique across the configs. Returns a list of clashes."""
    seen, clashes = {}, []
    for k, p in all_ports():
        r = p.get('reservations', {})
        for field in RESERVED_KEYS:
            v = r.get(field)
            if v is None:
                continue
            if field in SHARED_OVER_TIME and p.get('status') in ('done', 'reserved'):
                continue
            v = v.lower() if isinstance(v, str) else v
            if (field, v) in seen:
                clashes.append('%s %r: %s and %s' % (field, v, seen[(field, v)], k))
            seen[(field, v)] = k
    return clashes
