r"""Write the ported SAW's own (Halo 4) numbers into its Halo 1 tags -- step 4.

A port carries its SOURCE game's numbers in its tags, and the suggested balance goes on
top at patch time. So the built map ships the Halo 4 SAW: magazine 72, velocity 300,
7.5 damage. Turning the balance option on is what produces 135 / 64.8 / 10.

Both halves come out of one file, `balance_SAW_Halo4_to_Halo1.json`: this writes each
row's `original`, and `make_port_catalog.py` publishes the same row's `balanced` for the
patcher. They cannot drift, because neither one holds a number of its own.

RECONSTRUCTED 2026-09-29. The Halo 1 tools were rescued out of a session scratchpad in
df48675; 21 were promoted and this one was called by saw_build.py and missed, so the
build died on a script that had never been in the repo. Nothing about it was recoverable
except what it had to do, which is why it verifies itself rather than trusting a table
of paths typed from memory.

THE TWO UNIT CONVERSIONS, both measured rather than assumed

Assembly's plugins and Reclaimer's definitions do not agree on units, and the balance
table is in Assembly's -- because the patcher writes through those plugins. Two kinds of
field differ, and getting either wrong ships a weapon that is quietly broken rather than
one that fails:

  * ANGLES are DEGREES in the table and RADIANS in the tag. The Assault Rifle's
    Magnetism Angle reads 12 in the table and 0.20944 in the tag; 12 written raw is
    687 degrees of aim assist.
  * VELOCITIES are units per TICK in the table and units per SECOND in the tag, a factor
    of 30. The Assault Rifle reads 10.8 against 324. The Halo 4 SAW's 10 is 300 in the
    tag -- which is the number the Halo 3 port independently anchors on, and is the check
    that this factor is right.

Ranges differ in SHAPE too: Assembly splits one range into `X` and `X Max`, Reclaimer
keeps a single field with `from` and `to`.

THE SELF-CHECK, which is the point

Every row names the DONOR's field as well as the port's, and carries the donor's own
value as `donor_dst`. So before writing anything this reads the Assault Rifle's tags and
asserts that each path, with its factor applied, reproduces `donor_dst`. A path typed
wrong, a factor missed, a Reclaimer definition that moves a field, or a regenerated table
all fail here rather than in game. Nothing is written unless all of them pass.

    python saw_port_values.py            # verify and report, touching nothing
    python saw_port_values.py --write
"""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'pylibs'))
sys.path.insert(0, HERE)
import env  # noqa: E402,F401
from reclaimer.hek.defs.weap import weap_def                    # noqa: E402
from reclaimer.hek.defs.proj import proj_def                    # noqa: E402
from reclaimer.hek.defs.jpt_ import jpt__def                    # noqa: E402

B = os.sep
HCEEK = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'HCEEK')
TAGS = os.path.join(HCEEK, 'tags')
TABLE = os.path.join(HERE, 'balance_SAW_Halo4_to_Halo1.json')

#: Both are the factor that takes a TAG value to a TABLE value, so the table's units are
#: always `tag * factor` and the tag's are always `table / factor`. They pull in opposite
#: directions, which is why they are written this way round rather than as two multipliers
#: -- and the donor check caught exactly that mistake when TICK was first written as 30.
DEG = 180.0 / math.pi          # tag radians * DEG  = table degrees
TICK = 1.0 / 30.0              # tag units/second * TICK = table units/tick

_AR = 'weapons' + B + 'assault rifle' + B
_SAW = 'weapons' + B + 'saw' + B

#: (donor class, donor tag) -> (port tag, extension, Reclaimer definition).
#: The same mapping make_port_catalog.py uses for the balanced half, kept beside it on
#: purpose: a row the catalog publishes and this does not write would be a port whose
#: patched value has no unpatched counterpart.
PAIRS = {
    ('weap', _AR + 'assault rifle'): (_SAW + 'saw', '.weapon', weap_def),
    ('proj', _AR + 'bullet'): (_SAW + 'bullet', '.projectile', proj_def),
    ('jpt!', _AR + 'bullet'): (_SAW + 'bullet', '.damage_effect', jpt__def),
    ('jpt!', _AR + 'melee'): (_SAW + 'melee', '.damage_effect', jpt__def),
}

#: (class, Assembly field name) -> (where, dotted path, range member, factor)
#:
#: `where` picks the struct the path starts at: the tag itself, or one element of the
#: Triggers or Magazines block. `factor` converts TABLE units to TAG units by division,
#: so 1.0 means the two agree.
FIELDS = {
    # --- weapon, on the tag -------------------------------------------------------
    ('weap', 'Magnetism Angle'): ('tag', 'weap_attrs.aiming.magnetism_angle', None, DEG),
    ('weap', 'Magnetism Range'): ('tag', 'weap_attrs.aiming.magnetism_range', None, 1.0),
    ('weap', 'Autoaim Angle'): ('tag', 'weap_attrs.aiming.autoaim_angle', None, DEG),
    ('weap', 'Autoaim Range'): ('tag', 'weap_attrs.aiming.autoaim_range', None, 1.0),
    ('weap', 'Magnification Levels'): ('tag', 'weap_attrs.aiming.zoom_levels', None, 1.0),
    ('weap', 'Magnification Range'): ('tag', 'weap_attrs.aiming.zoom_ranges', 'from', 1.0),
    ('weap', 'Magnification Range Max'): ('tag', 'weap_attrs.aiming.zoom_ranges', 'to', 1.0),
    # --- weapon, Triggers ---------------------------------------------------------
    ('weap', 'Distribution Function'): ('trigger', 'projectile.distribution_function', None, 1.0),
    ('weap', 'Distribution Angle'): ('trigger', 'projectile.distribution_angle', None, DEG),
    ('weap', 'Firing Noise'): ('trigger', 'firing.firing_noise', None, 1.0),
    ('weap', 'Rounds Per Second'): ('trigger', 'firing.rounds_per_second', 'from', 1.0),
    ('weap', 'Rounds Per Second Max'): ('trigger', 'firing.rounds_per_second', 'to', 1.0),
    ('weap', 'Projectiles Per Shot'): ('trigger', 'projectile.projectiles_per_shot', None, 1.0),
    ('weap', 'Rounds Per Shot'): ('trigger', 'firing.rounds_per_shot', None, 1.0),
    ('weap', 'Minimum Error'): ('trigger', 'projectile.minimum_error', None, DEG),
    ('weap', 'Error Angle'): ('trigger', 'projectile.error_angle', 'from', DEG),
    ('weap', 'Error Angle Max'): ('trigger', 'projectile.error_angle', 'to', DEG),
    # --- weapon, Magazines --------------------------------------------------------
    ('weap', 'Rounds Total Initial'): ('magazine', 'rounds_total_initial', None, 1.0),
    ('weap', 'Rounds Total Maximum'): ('magazine', 'rounds_total_maximum', None, 1.0),
    ('weap', 'Rounds Loaded Maximum'): ('magazine', 'rounds_loaded_maximum', None, 1.0),
    ('weap', 'Rounds Reloaded'): ('magazine', 'rounds_reloaded', None, 1.0),
    # --- projectile ---------------------------------------------------------------
    ('proj', 'Maximum Range'): ('tag', 'proj_attrs.detonation.maximum_range', None, 1.0),
    ('proj', 'Minimum Velocity'): ('tag', 'proj_attrs.detonation.minimum_velocity', None, TICK),
    ('proj', 'Air Damage Range'): ('tag', 'proj_attrs.physics.air_damage_range', 'from', 1.0),
    ('proj', 'Air Damage Range Max'): ('tag', 'proj_attrs.physics.air_damage_range', 'to', 1.0),
    ('proj', 'Water Damage Range'): ('tag', 'proj_attrs.physics.water_damage_range', 'from', 1.0),
    ('proj', 'Water Damage Range Max'): ('tag', 'proj_attrs.physics.water_damage_range', 'to', 1.0),
    ('proj', 'Initial Velocity'): ('tag', 'proj_attrs.physics.initial_velocity', None, TICK),
    ('proj', 'Final Velocity'): ('tag', 'proj_attrs.physics.final_velocity', None, TICK),
    ('proj', 'Air Gravity Scale'): ('tag', 'proj_attrs.physics.air_gravity_scale', None, 1.0),
    ('proj', 'Water Gravity Scale'): ('tag', 'proj_attrs.physics.water_gravity_scale', None, 1.0),
    # --- damage effect, both the bullet's and the melee's --------------------------
    ('jpt!', 'Damage Lower Bound'): ('tag', 'damage.damage_lower_bound', None, 1.0),
    ('jpt!', 'Damage Upper Bound'): ('tag', 'damage.damage_upper_bound', 'from', 1.0),
    ('jpt!', 'Damage Upper Bound Max'): ('tag', 'damage.damage_upper_bound', 'to', 1.0),
}

#: (pair key, where, dotted path, member, TAG value, index, label) -- fields no card
#: targets, so no balance row carries them (port_field_audit.py). Error deceleration
#: time: H4 SAW 0.49 / H4 AR 0.5 x H1 AR 1.0 = 0.98.
EXTRA = [
    (('weap', _AR + 'assault rifle'), 'trigger', 'firing.error_deceleration_time', None,
     0.98, 0, 'Error Deceleration Time'),
]

#: Factors that could not be PROVEN from the donor because the donor's value is zero,
#: and zero survives any factor. They are assigned by kind -- an angle is an angle, a
#: velocity is a velocity -- and listed here so the claim is visible rather than implied.
#: The Halo 4 SAW happens to be zero for all of them too, so today nothing turns on it.
UNPROVEN = {('weap', 'Distribution Angle'), ('weap', 'Minimum Error'),
            ('proj', 'Minimum Velocity'), ('weap', 'Magnification Levels'),
            ('weap', 'Magnification Range'), ('weap', 'Magnification Range Max'),
            ('proj', 'Water Damage Range')}


def _struct(root, where, index):
    """The struct a field's path starts at: the tag, or one block element."""
    if where == 'tag':
        return root
    block = root.weap_attrs.triggers if where == 'trigger' else root.weap_attrs.magazines
    return block.STEPTREE[index]


def _walk(node, dotted):
    for part in dotted.split('.'):
        node = getattr(node, part)
    return node


def _read(root, where, dotted, member, index=0):
    node = _walk(_struct(root, where, index), dotted)
    if member:
        node = getattr(node, member)
    try:
        return float(node)
    except TypeError:
        return float(node.data)                 # an EnumBlock reads as its index


def _write(root, where, dotted, member, value, index=0):
    parent = _walk(_struct(root, where, index), dotted)
    if member:
        cur = getattr(parent, member)
        setattr(parent, member, int(round(value)) if isinstance(cur, int) else value)
        return
    if hasattr(parent, 'data') and not hasattr(parent, 'NAME_MAP'):
        parent.data = int(round(value))         # EnumBlock
        return
    owner = _struct(root, where, index)
    parts = dotted.split('.')
    for p in parts[:-1]:
        owner = getattr(owner, p)
    cur = getattr(owner, parts[-1])
    try:
        cur_is_int = isinstance(cur, int) and not isinstance(cur, bool)
    except TypeError:
        cur_is_int = False
    if hasattr(cur, 'data'):
        cur.data = int(round(value))
    else:
        setattr(owner, parts[-1], int(round(value)) if cur_is_int else value)


def rows():
    """The table rows that name a port tag, a field this knows, and a Halo 4 value."""
    table = json.load(open(TABLE, encoding='utf-8'))
    out = []
    for r in table['rows']:
        key = (r.get('dst_class'), r.get('dst_tag'))
        if key not in PAIRS or not r.get('dst_field') or r.get('original') is None:
            continue
        spec = FIELDS.get((key[0], r['dst_field']))
        if spec is None:
            raise SystemExit(
                'the balance table names a field this does not know how to write:\n'
                '    %s  %s\nAdd it to FIELDS with its Reclaimer path and its unit '
                'factor, and let the donor check prove the factor.' % key + r['dst_field'])
        out.append((key, spec, r))
    return out


def load(path, definition):
    return definition.build(filepath=os.path.join(TAGS, path))


def verify(found):
    """Prove every path and factor against the DONOR before touching the port."""
    cache, bad, checked = {}, [], 0
    for key, spec, r in found:
        if r.get('donor_dst') is None:
            continue
        where, dotted, member, factor = spec
        _port, ext, definition = PAIRS[key]
        if key not in cache:
            cache[key] = load(key[1] + ext, definition).data.tagdata
        got = _read(cache[key], where, dotted, member) * factor
        want = float(r['donor_dst'])
        checked += 1
        if abs(got - want) > max(1e-3, abs(want) * 1e-4):
            bad.append((key[0], r['dst_field'], want, got))
    for cls, field, want, got in bad:
        print('   MISMATCH %-5s %-24s donor says %-12.6g path gives %-12.6g'
              % (cls, field, want, got))
    unproven = sum(1 for key, _s, r in found if (key[0], r['dst_field']) in UNPROVEN)
    print('donor check: %d of %d fields reproduce the donor exactly, %d unprovable '
          '(the donor is zero), %d WRONG' % (checked - len(bad), checked, unproven,
                                             len(bad)))
    return not bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()

    found = rows()
    print('%d fields, from %s' % (len(found), os.path.basename(TABLE)))
    if not verify(found):
        raise SystemExit(
            'REFUSING TO WRITE. A path or a unit factor no longer reproduces the '
            'Assault Rifle,\nso the numbers this would put in the port are not the ones '
            'it means to.')

    tags, changes = {}, []
    for key, spec, r in found:
        port, ext, definition = PAIRS[key]
        if port + ext not in tags:
            tags[port + ext] = load(port + ext, definition)
        root = tags[port + ext].data.tagdata
        where, dotted, member, factor = spec
        want = float(r['original']) / factor
        index = r.get('dst_index')
        indices = [0]
        if where in ('trigger', 'magazine') and index == 'all':
            block = (root.weap_attrs.triggers if where == 'trigger'
                     else root.weap_attrs.magazines)
            indices = list(range(len(block.STEPTREE)))
        elif isinstance(index, int):
            indices = [index]
        for i in indices:
            was = _read(root, where, dotted, member, i)
            if abs(was - want) > 1e-9:
                changes.append((port, r['dst_field'], i, was, want))
            if a.write:
                _write(root, where, dotted, member, want, i)

    # FIELDS NO CARD COVERS (port_field_audit.py --game h1, 2026-10-05): the Halo 4 SAW
    # differs from the Halo 4 AR there, and the clone still carried the AR's value. In
    # TAG units: the ratio rule ported_src * donor_dst / donor_src, read on the tags.
    for key, where, dotted, member, want, i, label in EXTRA:
        port, ext, definition = PAIRS[key]
        if port + ext not in tags:
            tags[port + ext] = load(port + ext, definition)
        root = tags[port + ext].data.tagdata
        was = _read(root, where, dotted, member, i)
        if abs(was - want) > 1e-6:
            changes.append((port, label, i, was, want))
        if a.write:
            _write(root, where, dotted, member, want, i)

    for port, field, i, was, want in changes:
        print('   %-18s %-24s [%d]  %-12.6g -> %.6g'
              % (os.path.basename(port), field, i, was, want))
    # Against what the PORT currently holds, not the donor. A field the port already
    # carries is silent, which is what makes a second run report nothing -- and what
    # makes the surviving projectile and damage tags from an earlier build read as
    # already correct rather than as skipped.
    print('%d of %d fields differ from what the port holds and would change'
          % (len(changes), len(found)))

    # THE HIT-EFFECT RULE (user, 2026-10-08): the shield-hit effect on the player, an own copy
    # sized by the rule (ports_h1/saw.py `impact_thin`; h1_hit_effect_load.thin_effect)
    import h1_hit_effect_load as HL
    from ports_h1 import saw as saw_port
    I = saw_port.PORT['impact_thin']
    key = ('proj', _AR + 'bullet')
    port, ext, definition = PAIRS[key]
    if port + ext not in tags:
        tags[port + ext] = load(port + ext, definition)
    effects = []
    for i in I['materials']:
        x = tags[port + ext].data.tagdata.proj_attrs.material_responses.STEPTREE[i]
        et, own, kept, total = HL.thin_effect(I, x.effect.filepath)
        print('   impact on material %d: %s -> %s' % (i, x.effect.filepath, own))
        if a.write:
            x.effect.filepath = own
        effects.append((et, own))

    if not a.write:
        print('(dry run -- pass --write)')
        return
    for et, own in effects:
        p = os.path.join(TAGS, own + '.effect')
        os.makedirs(os.path.dirname(p), exist_ok=True)
        et.serialize(filepath=p, temp=False, backup=False)
        print('wrote %s' % own)
    for name, t in sorted(tags.items()):
        t.serialize(temp=False, backup=False)
        print('wrote %s' % name)


if __name__ == '__main__':
    main()
