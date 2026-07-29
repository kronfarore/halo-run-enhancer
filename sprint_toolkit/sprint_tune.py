"""Apply (or undo) the sprint SPEED half on a built Halo 1 map.

Split of responsibilities:
  * The editing kit adds the structure once -- the sprint weapon tag and the
    compiled script. That needs a rebuild.
  * This script sets the numbers, as plain field edits on the built .map, so
    sprint speed is tunable in seconds without ever rebuilding. This is the
    part the Enhancer can eventually own as a modifier card.

The trick, from decoding Sprint Evolved: raise the GLOBAL run speed to the
sprint speed, then give every real weapon a Forward Movement Penalty that
scales the player back down to normal. Normal = Run x (1 - penalty), so:

    penalty = 1 - (1 / multiplier)      e.g. 1.5x -> 0.3333

Holding a weapon with no penalty (ours) = sprinting.

Usage:
    python sprint_tune.py <map.map> --mult 1.5
    python sprint_tune.py <map.map> --show
    python sprint_tune.py <map.map> --restore

A .bak of the pristine map is made once and every patch rebuilds from it, so
repeats never compound -- the same discipline halo_patch.apply_run uses.
"""
import argparse
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402  (install paths — edit paths.py)

sys.path.insert(0, paths.TOOL)
import halo_patch as hp  # noqa: E402

PLUGINS = paths.PLUGINS

GLOBALS = 'globals\\globals'
MOVE = 'Player Information'
SPRINT_WEAP = 'weapons\\sprint\\sprint'

# Flashlight-key ability selector (matches sprint.hsc ability0/ability1).
ABILITIES = {'none': 0, 'sprint': 1, 'overshield': 2, 'camo': 3, 'medikit': 4}

# Vanilla stock values, so --mult is always applied to a known baseline rather
# than to whatever a previous run left behind.
STOCK_RUN_FORWARD = 2.25
STOCK_SNEAK_FORWARD = 0.9

# Overshield: object_set_shield's raw value is awkward (a tiny number already
# overshields). Calibrated in-game 2026-07-28: the raw value is LINEAR in the
# overshield multiplier, v = mult * OS_SHIELD_BASE, so x2=0.0267, x3=0.04005,
# x4=0.0534. Users pass a clean multiplier (--os-mult 2); we store the raw value.
OS_SHIELD_BASE = 0.01335   # raw object_set_shield value for x1 (normal full shield)

# Only PLAYER-HELD weapons get the penalty. Anything left at zero is a
# permanent-sprint weapon, so the exclusions matter:
#   vehicles\...   turret/vehicle guns, never carried on foot
#   AI-only        weapons no H1 player can hold (the sword is Elite-only here)
# Sprint Evolved draws exactly these lines, and being wrong the other way is the
# dangerous direction: a missed player weapon = sprint that never turns off.
AI_ONLY = (
    'weapons\\energy sword\\energy sword',
    'weapons\\fuel rod gun\\hunter fuel rod',
)


def resolve_map(arg):
    """Find the map the user meant. Accepts a full path (with or without .map) or a
    bare id like 'a10', which resolves to the DEPLOYED game map under
    <MCC>\\halo1\\maps — the copy the game actually loads, which is what you tune."""
    p = Path(arg)
    cands = [p, Path(str(p) + '.map')]
    if os.sep not in arg and '/' not in arg:      # bare id -> deployed game map
        base = Path(paths.MCC) / 'halo1' / 'maps'
        cands += [base / arg, base / (arg + '.map')]
    for c in cands:
        if c.is_file():
            return c
    return p


def player_held(name):
    return not name.startswith('vehicles\\') and name not in AI_ONLY


def set_global(m, name, val):
    """Patch a Halo 1 script-global's initialization value in a built map, by name,
    WITHOUT a rebuild. The scnr Globals block (0x4A8, elem 0x5C) gives each global's
    Init Expression Index (@0x28); that indexes the Script Syntax Data blob (dataref
    @0x474), whose 56-byte header precedes 20-byte nodes. The node's VALUE TYPE is an
    int16 at node+0x04 (5=boolean, 6=real, 7=short, 8=long -- the global-type enum),
    and the constant sits at node+0x10: 1 byte for a boolean, int16 for a short,
    float32 for a real, int32 for a long. Returns (old, new) or None if absent.
    This is how sprint duration/cooldown/enable are tuned live."""
    import struct
    scnr = [k for k in m.tags if k[0] == 'scnr'][0]
    meta = m.tags[scnr]
    syn = (m.u32(meta + 0x474 + 12) - m.magic) & 0xFFFFFFFF
    cnt = m.i32(meta + 0x4A8)
    ptr = (m.u32(meta + 0x4A8 + 4) - m.magic) & 0xFFFFFFFF
    for i in range(cnt):
        b = ptr + i * 0x5C
        if m._cstr(b) != name:
            continue
        node = m.u32(b + 0x28) & 0xFFFF
        nb = syn + 56 + node * 20
        vtype = struct.unpack_from('<h', m.data, nb + 0x04)[0]
        off = nb + 0x10
        if vtype == 5:      # boolean -- single byte, leave the 0xFFFFFF terminator
            old = m.data[off]
            m.data[off] = 1 if val else 0
            return old, m.data[off]
        if vtype == 6:      # real
            old = struct.unpack_from('<f', m.data, off)[0]
            struct.pack_into('<f', m.data, off, float(val)); return old, float(val)
        if vtype == 8:      # long
            old = struct.unpack_from('<i', m.data, off)[0]
            struct.pack_into('<i', m.data, off, int(val)); return old, int(val)
        old = struct.unpack_from('<h', m.data, off)[0]   # short (default)
        struct.pack_into('<h', m.data, off, int(val)); return old, int(val)
    return None


def set_profile_shield(m, value, skip_substr='sprint'):
    """Set Starting Shield Modifier (spawn overshield multiplier) on every Player
    Starting Profile whose name doesn't contain skip_substr. Also lifts a 0 health
    modifier to 1.0 so a profile reset can't spawn the player dead. scnr Player Starting
    Profile block @0x348, elem 0x68: Starting Health Modifier @0x20, Shield @0x24.
    Returns [(name, old_shield)] for what was set."""
    import struct
    scnr = [k for k in m.tags if k[0] == 'scnr'][0]
    meta = m.tags[scnr]
    cnt = m.i32(meta + 0x348)
    ptr = (m.u32(meta + 0x348 + 4) - m.magic) & 0xFFFFFFFF
    done = []
    for i in range(cnt):
        b = ptr + i * 0x68
        name = m._cstr(b)
        if skip_substr and skip_substr in name:
            continue
        old = struct.unpack_from('<f', m.data, b + 0x24)[0]
        struct.pack_into('<f', m.data, b + 0x24, float(value))
        if struct.unpack_from('<f', m.data, b + 0x20)[0] <= 0.0:
            struct.pack_into('<f', m.data, b + 0x20, 1.0)
        done.append((name, old))
    return done


def read_global(m, name):
    """Read a script-global's current value without writing. Same layout as
    set_global. Returns the value, or None if the global isn't in this map."""
    import struct
    scnr = [k for k in m.tags if k[0] == 'scnr'][0]
    meta = m.tags[scnr]
    syn = (m.u32(meta + 0x474 + 12) - m.magic) & 0xFFFFFFFF
    cnt = m.i32(meta + 0x4A8)
    ptr = (m.u32(meta + 0x4A8 + 4) - m.magic) & 0xFFFFFFFF
    for i in range(cnt):
        b = ptr + i * 0x5C
        if m._cstr(b) != name:
            continue
        node = m.u32(b + 0x28) & 0xFFFF
        nb = syn + 56 + node * 20
        vtype = struct.unpack_from('<h', m.data, nb + 0x04)[0]
        off = nb + 0x10
        if vtype == 5:
            return m.data[off]
        if vtype == 6:
            return struct.unpack_from('<f', m.data, off)[0]
        if vtype == 8:
            return struct.unpack_from('<i', m.data, off)[0]
        return struct.unpack_from('<h', m.data, off)[0]
    return None


def main():
    global SPRINT_WEAP
    ap = argparse.ArgumentParser()
    ap.add_argument('map_path')
    ap.add_argument('--mult', type=float, default=1.5,
                    help="sprint speed as a multiple of vanilla run (default 1.5)")
    ap.add_argument('--show', action='store_true')
    ap.add_argument('--restore', action='store_true')
    ap.add_argument('--fp-none', action='store_true',
                    help="empty first person (no hands) instead of the cyborg "
                         "hands model")
    ap.add_argument('--duration', type=int, default=None,
                    help="sprint duration in TICKS (30/sec); patches sprint_ticks")
    ap.add_argument('--cooldown', type=int, default=None,
                    help="sprint cooldown in TICKS (30/sec); patches sprint_cooldown")
    ap.add_argument('--enable', dest='enable', action='store_true', default=None,
                    help="give BOTH players the sprint ability (same as --ability sprint)")
    ap.add_argument('--disable', dest='enable', action='store_false',
                    help="clear both players' ability (map behaves vanilla)")
    ap.add_argument('--ability', choices=list(ABILITIES), default=None,
                    help="set BOTH players' flashlight-key ability: "
                         "none/sprint/overshield/camo/medikit")
    # Powerup tuning (durations/cooldowns in TICKS, 30/sec; magnitudes in engine units).
    ap.add_argument('--os-mult', type=float, help="overshield strength as a clean MULTIPLIER "
                    "(x2, x3, ...); converted to the raw object_set_shield value internally "
                    "(v = mult * %g). Prefer this over --os-shield." % OS_SHIELD_BASE)
    ap.add_argument('--os-shield', type=float, help="RAW object_set_shield value (advanced; "
                    "use --os-mult instead). ~0.0267 = x2, 0.0534 = x4.")
    ap.add_argument('--os-body', type=float, help="UNUSED (retired unit_set_maximum_vitality "
                    "body arg; overshield uses object_set_shield now)")
    ap.add_argument('--os-duration', type=int, help="overshield window, ticks")
    ap.add_argument('--os-cooldown', type=int, help="overshield cooldown, ticks")
    ap.add_argument('--camo-duration', type=int, help="camo window, ticks")
    ap.add_argument('--camo-cooldown', type=int, help="camo cooldown, ticks")
    ap.add_argument('--medi-heal', type=float, help="medikit health while active (1.0 = full)")
    ap.add_argument('--medi-duration', type=int, help="medikit window, ticks")
    ap.add_argument('--medi-cooldown', type=int, help="medikit cooldown, ticks")
    ap.add_argument('--spawn-shield', type=float, default=None,
                    help="spawn OVERSHIELD: set Starting Shield Modifier on the player/coop "
                         "profiles (1=normal, 2=red 2x, 3=vanilla 3x). Real, gradually-"
                         "charging overshield applied on every spawn.")
    ap.add_argument('--sprint-weap', default=SPRINT_WEAP,
                    help="sprint weapon tag path; override to inspect another "
                         "build, e.g. Sprint Evolved's altis\\weapons\\sprint\\sprint")
    a = ap.parse_args()
    SPRINT_WEAP = a.sprint_weap

    path = resolve_map(a.map_path)
    if not path.is_file():
        base = os.path.join(paths.MCC, 'halo1', 'maps')
        sys.exit("no such map: %s\n"
                 "   Pass the DEPLOYED game map (this is what you play in-game), e.g.\n"
                 "   a bare id resolves automatically:  python sprint_tune.py a10 ...\n"
                 "   or the full path:  \"%s\\a10.map\"" % (a.map_path, base))
    bak = Path(str(path) + '.bak')

    reg = hp.PluginRegistry(PLUGINS, ['Halo1MCC', 'Halo1'])
    mg, wp = reg.get('matg'), reg.get('weap')
    if mg is None or wp is None:
        sys.exit("missing matg/weap plugin -- check the Assembly Plugins path")

    if a.restore:
        if not bak.is_file():
            sys.exit(f"no backup to restore: {bak}")
        shutil.copy2(bak, path)
        print(f"restored {path.name}")
        return

    def report(m, label):
        print(f"  {label}")
        for f in ('Run Forward', 'Sneak Forward'):
            print('    %-24s %s' % (f, m.read_first('matg', GLOBALS, f, mg,
                                                    block=MOVE)))
        pens = m.read_all('weap', '*', 'Forward Movement Penalty', wp)
        held = [p for p in pens if player_held(p[0])]
        loose = [p for p in held if abs(p[1]) < 1e-6 and p[0] != SPRINT_WEAP]
        print('    weapons: %d total, %d player-held' % (len(pens), len(held)))
        for name, v in sorted(held):
            print('      %-45s %.4f' % (name, v))
        # Zero penalty only means "permanent sprint" when run speed is actually raised
        # above vanilla. At --mult 1.0 (e.g. a powerup test) it's just normal movement.
        if loose and a.mult > 1.0:
            print('    !! %d player weapon(s) at zero penalty = permanent sprint'
                  % len(loose))
        has_sprint = bool(m.find_tags('weap', SPRINT_WEAP))
        print('    sprint weapon tag present: %s' % ('YES' if has_sprint else 'NO'))

    if a.show:
        report(hp.open_map(str(path), 'Halo 1'), f"{path.name} (live):")
        return

    # If no ability was specified, preserve whatever the LIVE (deployed) map already
    # has, so re-tuning just a value (e.g. --os-shield) doesn't silently turn the
    # ability off by rebuilding from the pristine .bak baseline. Read before patching.
    preserved_ability = None
    if a.ability is None and a.enable is None:
        live = hp.open_map(str(path), 'Halo 1')
        preserved_ability = read_global(live, 'ability0')
        if preserved_ability is None:
            preserved_ability = 1 if read_global(live, 'sprint_enabled0') else 0
        del live

    if not bak.is_file():
        shutil.copy2(path, bak)
        print(f"made baseline backup: {bak.name}")
    m = hp.open_map(str(bak), 'Halo 1')
    report(m, "before:")

    if not m.find_tags('weap', SPRINT_WEAP):
        print(f"\n!! '{SPRINT_WEAP}' is not in this map.\n"
              "   The speed edits alone would just make every weapon feel normal\n"
              "   with no way to sprint. Build the map with the sprint weapon and\n"
              "   the script first. Refusing to patch.")
        sys.exit(2)

    penalty = 1.0 - (1.0 / a.mult)
    print('\n  multiplier %.3fx -> run %.3f, weapon penalty %.4f'
          % (a.mult, STOCK_RUN_FORWARD * a.mult, penalty))

    ok = fail = 0
    for field, val in (('Run Forward', STOCK_RUN_FORWARD * a.mult),
                       ('Sneak Forward', STOCK_SNEAK_FORWARD * a.mult)):
        rows = m.apply_field('matg', GLOBALS, field, 'set', val, mg, block=MOVE)
        ok += sum(1 for r in rows if r.get('ok'))

    # Every player-held weapon gets the penalty; ours alone stays at zero.
    for name, _ in m.read_all('weap', '*', 'Forward Movement Penalty', wp):
        if not player_held(name):
            continue
        target = 0.0 if name == SPRINT_WEAP else penalty
        rows = m.apply_field('weap', name, 'Forward Movement Penalty', 'set',
                             target, wp)
        if any(r.get('ok') for r in rows):
            ok += 1
        else:
            fail += 1
    # No fast strafing while sprinting.
    m.apply_field('weap', SPRINT_WEAP, 'Sideways Movement Penalty', 'set', 0.5, wp)

    # First-person view of the sprint weapon. It is flag-derived and still points
    # First Person Model + First Person Animations at weapons\flag\fp\fp (the flag
    # arms). Two looks, both vanilla:
    #   default   point FP Model at the cyborg hands model, FP Anim null -> bare
    #             hands (static, since there is no bare-hands animation graph).
    #   --fp-none null both -> empty view, no hands at all.
    # tagRef is 16 bytes: class fourcc @+0, datum id @+0xC. A null ref is both
    # 0xFFFFFFFF. Offsets from Halo1\weap.xml: FP Model 0x45C, FP Anim 0x46C.
    # Plain map edit -- reversible via --restore, no rebuild.
    sp = m.find_tags('weap', SPRINT_WEAP)
    if sp:
        wbase = sp[0][1]
        import struct

        def null_ref(roff):
            struct.pack_into('<I', m.data, wbase + roff + 0, 0xFFFFFFFF)
            struct.pack_into('<I', m.data, wbase + roff + 12, 0xFFFFFFFF)

        def point_ref(roff, cls, name):
            """Write class fourcc + datum id of (cls, name) into the ref, reading
            the datum from the tag index so it survives rebuilds."""
            for i in range(m.tag_count):
                b = m.tag_array_off + i * 32
                c = bytes(m.data[b:b + 4][::-1]).decode('latin1')
                try:
                    nm = m._cstr((m.u32(b + 0x10) - m.magic) & 0xFFFFFFFF)
                except Exception:
                    continue
                if c == cls and nm == name:
                    m.data[wbase + roff:wbase + roff + 4] = m.data[b:b + 4]  # class
                    struct.pack_into('<I', m.data, wbase + roff + 12,
                                     m.u32(b + 0x0C))                        # datum
                    return True
            return False

        # First Person Animations: no bare-hands graph exists, so always null it.
        null_ref(0x46C)
        if a.fp_none:
            null_ref(0x45C)
            print('  first person: empty (no hands)')
        elif point_ref(0x45C, 'mod2', 'characters\\cyborg\\fp\\fp'):
            print('  first person: cyborg hands model (static)')
        else:
            null_ref(0x45C)
            print('  first person: hands model not in map, fell back to empty')

    # Script-global tuning (duration / cooldown / enable) -- byte edits, no rebuild.
    for gname, gval in (('sprint_ticks', a.duration), ('sprint_cooldown', a.cooldown)):
        if gval is None:
            continue
        res = set_global(m, gname, gval)
        if res:
            print('  %s %d -> %d ticks (%.2fs)' % (gname, res[0], res[1], res[1] / 30.0))
            ok += 1
        else:
            print('  !! global %s not found (map lacks the sprint script)' % gname)
    # Overshield strength: a clean multiplier (--os-mult) converts to the raw
    # object_set_shield value; --os-shield stays as a raw override. --os-mult wins.
    os_shield_raw = a.os_shield
    if a.os_mult is not None:
        os_shield_raw = a.os_mult * OS_SHIELD_BASE
        print('  overshield x%g -> object_set_shield %.5f' % (a.os_mult, os_shield_raw))

    # Powerup tuning globals (only those given). Real for magnitudes, short for ticks.
    for gname, gval in (('os_shield', os_shield_raw), ('os_body', a.os_body),
                        ('os_ticks', a.os_duration),
                        ('os_cooldown', a.os_cooldown), ('camo_ticks', a.camo_duration),
                        ('camo_cooldown', a.camo_cooldown), ('medi_heal', a.medi_heal),
                        ('medi_ticks', a.medi_duration), ('medi_cooldown', a.medi_cooldown)):
        if gval is None:
            continue
        res = set_global(m, gname, gval)
        if res:
            print('  %s %s -> %s' % (gname, res[0], res[1]))
            ok += 1
        else:
            print('  !! global %s not found (map lacks the ability script)' % gname)

    # Spawn overshield: the vanilla mechanism -- Starting Shield Modifier on the player
    # profiles. Not a script global; a scnr edit, so it works on any map with profiles.
    if a.spawn_shield is not None:
        done = set_profile_shield(m, a.spawn_shield)
        for name, old in done:
            print('  spawn shield [%s] %.2f -> %.2f' % (name, old, a.spawn_shield))
        ok += len(done)
        if not done:
            print('  !! no player profiles found to set spawn shield on')

    # Ability selection. --ability wins; --enable/--disable map to sprint/none; with
    # none of those, preserve whatever the live map already had (so a value-only tune
    # doesn't disable the ability).
    ability = ABILITIES[a.ability] if a.ability is not None else (
        1 if a.enable is True else (0 if a.enable is False else preserved_ability))
    if ability is not None:
        name = next((k for k, v in ABILITIES.items() if v == ability), 'ability %d' % ability)
        # Both players (this CLI is the whole-map toggle). Newer maps have ability0/1;
        # a pre-rebuild map only has the old sprint_enabled(0/1) booleans.
        r0 = set_global(m, 'ability0', ability)
        r1 = set_global(m, 'ability1', ability)
        if r0 is not None or r1 is not None:
            print('  ability0/1 -> %s (%d)' % (name, ability))
            ok += 1
        else:
            on = ability == 1
            r0 = set_global(m, 'sprint_enabled0', on)
            r1 = set_global(m, 'sprint_enabled1', on)
            if r0 is not None or r1 is not None:
                print('  sprint_enabled0/1 -> %s (old map: sprint only)' % ('true' if on else 'false'))
                ok += 1
            elif set_global(m, 'sprint_enabled', on) is not None:
                print('  sprint_enabled -> %s (old map: sprint only)' % ('true' if on else 'false'))
                ok += 1
            else:
                print('  !! ability global not found (map lacks the ability script)')

    if not ok:
        sys.exit("nothing resolved -- refusing to save")
    m.save(str(path))
    report(hp.open_map(str(path), 'Halo 1'), "after:")
    print(f"\nwrote {ok} field(s)%s to {path.name}"
          % (f", {fail} failed" if fail else ""))
    print(f"Undo:  python sprint_tune.py {path.name} --restore")


if __name__ == '__main__':
    main()
