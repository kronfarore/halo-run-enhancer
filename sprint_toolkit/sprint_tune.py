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

# Vanilla stock values, so --mult is always applied to a known baseline rather
# than to whatever a previous run left behind.
STOCK_RUN_FORWARD = 2.25
STOCK_SNEAK_FORWARD = 0.9

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
                    help="set sprint_enabled true (simulates Start with Sprint)")
    ap.add_argument('--disable', dest='enable', action='store_false',
                    help="set sprint_enabled false (map behaves vanilla)")
    ap.add_argument('--sprint-weap', default=SPRINT_WEAP,
                    help="sprint weapon tag path; override to inspect another "
                         "build, e.g. Sprint Evolved's altis\\weapons\\sprint\\sprint")
    a = ap.parse_args()
    SPRINT_WEAP = a.sprint_weap

    path = Path(a.map_path)
    if not path.is_file():
        sys.exit(f"no such map: {path}")
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
        if loose:
            print('    !! %d player weapon(s) at zero penalty = permanent sprint'
                  % len(loose))
        has_sprint = bool(m.find_tags('weap', SPRINT_WEAP))
        print('    sprint weapon tag present: %s' % ('YES' if has_sprint else 'NO'))

    if a.show:
        report(hp.open_map(str(path), 'Halo 1'), f"{path.name} (live):")
        return

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
    if a.enable is not None:
        res = set_global(m, 'sprint_enabled', a.enable)
        if res:
            print('  sprint_enabled -> %s' % ('true' if a.enable else 'false'))
            ok += 1
        else:
            print('  !! sprint_enabled not found (map lacks the sprint script)')

    if not ok:
        sys.exit("nothing resolved -- refusing to save")
    m.save(str(path))
    report(hp.open_map(str(path), 'Halo 1'), "after:")
    print(f"\nwrote {ok} field(s)%s to {path.name}"
          % (f", {fail} failed" if fail else ""))
    print(f"Undo:  python sprint_tune.py {path.name} --restore")


if __name__ == '__main__':
    main()
