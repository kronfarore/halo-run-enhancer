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
import struct
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402  (install paths — edit paths.py)

sys.path.insert(0, paths.TOOL)
import halo_patch as hp  # noqa: E402
import map_vault as V  # noqa: E402

PLUGINS = paths.PLUGINS

GLOBALS = 'globals\\globals'
MOVE = 'Player Information'
SPRINT_WEAP = 'weapons\\sprint\\sprint'

# Camo's real duration is the equipment tag's Powerup Time (eqip @0x30C, stock 45s).
CAMO_TAG = 'powerups\\active camouflage'
EQIP_POWERUP_TIME = 0x30C

# Flashlight-key ability selector (matches sprint.hsc ability0/ability1). Ability 4 is
# "Regeneration" to the user; `medikit` stays as an internal alias (globals are medi_*).
# Order matters: the first name for a value is the one we display.
ABILITIES = {'none': 0, 'sprint': 1, 'overshield': 2, 'camo': 3,
             'regeneration': 4, 'medikit': 4}

# Vanilla stock values, so --mult is always applied to a known baseline rather
# than to whatever a previous run left behind.
STOCK_RUN_FORWARD = 2.25
STOCK_SNEAK_FORWARD = 0.9

# The engine's absolute vitality scale, measured in-game: a full body/shield is 75
# units, and the unit_get_health/_shield getters return a [0,1] fraction OF THAT.
# It has to be exact -- the regeneration write-back rewrites body/shield as
# fraction*VIT_MAX every tick, so 76 ratchets both to full and 74 drains them.
VIT_MAX = 75.0

# Overshield: object_set_shield's raw value is awkward (a tiny number already
# overshields) because it too is in 1/VIT_MAX units -- one normal full shield is
# 1/75. So the same constant drives both abilities; the in-game calibration
# (x2=0.0267, x3=0.04005, x4=0.0534) is 2/75, 3/75, 4/75 to measurement error.
# Users pass a clean multiplier (--os-mult 2); we store the raw value.
OS_SHIELD_BASE = 1.0 / VIT_MAX   # raw object_set_shield value for x1 (normal full shield)

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


# scnr Player Starting Profile block @0x348, element 0x68:
#   Starting Health Modifier @0x20, Starting Shield Modifier @0x24.
PROFILE_BLOCK = 0x348
PROFILE_ELEM = 0x68
PROFILE_FIELDS = {'health': 0x20, 'shield': 0x24}


def set_profile_vitality(m, which, value, skip_substr='sprint'):
    """Set a spawn modifier ('health' or 'shield') on every Player Starting Profile whose
    name doesn't contain skip_substr. Setting shield also lifts a 0 health modifier to 1.0
    so a profile reset can't spawn the player dead. Returns [(name, old)] for what was set."""
    import struct
    off = PROFILE_FIELDS[which]
    scnr = [k for k in m.tags if k[0] == 'scnr'][0]
    meta = m.tags[scnr]
    cnt = m.i32(meta + PROFILE_BLOCK)
    ptr = (m.u32(meta + PROFILE_BLOCK + 4) - m.magic) & 0xFFFFFFFF
    done = []
    for i in range(cnt):
        b = ptr + i * PROFILE_ELEM
        name = m._cstr(b)
        if skip_substr and skip_substr in name:
            continue
        old = struct.unpack_from('<f', m.data, b + off)[0]
        struct.pack_into('<f', m.data, b + off, float(value))
        if which == 'shield' and struct.unpack_from('<f', m.data, b + 0x20)[0] <= 0.0:
            struct.pack_into('<f', m.data, b + 0x20, 1.0)
        done.append((name, old))
    return done


def set_profile_shield(m, value, skip_substr='sprint'):
    """Back-compat wrapper: Starting Shield Modifier (spawn overshield multiplier)."""
    return set_profile_vitality(m, 'shield', value, skip_substr)


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
    ap.add_argument('--fx-ready', type=int,
                    help="effect id flashed once when a cooldown expires; 0 = off")
    ap.add_argument('--fx-ready-n', type=int,
                    help='how many flashes the ready cue fires (default 3)')
    ap.add_argument('--fx-ready-gap', type=int,
                    help='ticks between those flashes (default 5)')
    ap.add_argument('--fx-ladder', type=int,
                    help="1 = advance fx_kind on every activation, so one build "
                         "can be walked through the whole candidate list in game")
    ap.add_argument('--fx-min', type=int, help='ladder lower bound')
    ap.add_argument('--fx-max', type=int, help='ladder upper bound')
    ap.add_argument('--fx-kind', type=int,
                    help="regeneration pulse effect: 0 off, 1 co-op teleport, "
                         "2 teleportation, 3 teleportation short, 4 teleport light, "
                         "5 cyborg shield, 6 monitor glow rings")
    ap.add_argument('--fx-every', type=int,
                    help="ticks between regeneration pulses (30/sec)")
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
    ap.add_argument('--camo-duration', type=int, help="camo window, ticks. Keep it >= the "
                    "camo tag's Powerup Time (--camo-seconds), or re-triggering mid-camo "
                    "drops a pickup that can't be collected.")
    ap.add_argument('--camo-seconds', type=float, help="REAL camo duration: the eqip "
                    "Powerup Time on powerups\\active camouflage (stock 45). Also sets the "
                    "ability window to match.")
    ap.add_argument('--camo-cooldown', type=int, help="camo cooldown, ticks")
    ap.add_argument('--medi-percent', type=float, help="Regeneration total heal as a PERCENT of "
                    "max health (100 = a full heal), spread over --medi-duration. Preferred "
                    "over --medi-heal.")
    ap.add_argument('--medi-heal', type=float, help="Regeneration TOTAL heal in raw vitality "
                    "units (%g = full health), spread evenly over --medi-duration" % VIT_MAX)
    ap.add_argument('--medi-duration', type=int, help="Regeneration window, ticks "
                    "(1 = instant; 90 = healed over 3s)")
    ap.add_argument('--medi-rate', type=float, help="Regeneration PER-TICK heal, set outright "
                    "(overrides --medi-heal/--medi-duration). 0 = no heal, for calibrating "
                    "--vit-max.")
    ap.add_argument('--vit-max', type=float, help="absolute vitality scale (default 100): what "
                    "the [0,1] health/shield getters are multiplied by. MUST match the unit's "
                    "true max -- too high and each tick rewrites health higher than it was, "
                    "ratcheting to full regardless of the heal rate.")
    ap.add_argument('--medi-cooldown', type=int, help="medikit cooldown, ticks")
    ap.add_argument('--spawn-shield', type=float, default=None,
                    help="spawn OVERSHIELD: set Starting Shield Modifier on the player/coop "
                         "profiles (1=normal, 2=red 2x, 3=vanilla 3x). Real, gradually-"
                         "charging overshield applied on every spawn.")
    ap.add_argument('--spawn-health', type=float, default=None,
                    help="set Starting Health Modifier on the player/coop profiles "
                         "(1 = normal). Spawn-time health multiplier.")
    ap.add_argument('--start-weapon', default=None,
                    help="give the player a starting weapon, e.g. 'assault rifle' or a full "
                         "tag path. Handy on levels that start you unarmed (a10).")
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
    bak = Path(V.baseline_for('Halo 1', path))

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

    # Regeneration: the script adds a PER-TICK amount (medi_rate) rather than dividing in
    # HSC. --medi-rate sets it outright; otherwise heal/duration derive it, falling back to
    # whatever the map already carries for the half that wasn't passed.
    # Camo's REAL duration lives on the equipment tag (Powerup Time), not in a global.
    # The script's window only gates re-triggering, so it has to cover that duration.
    camo_ticks = a.camo_duration
    if a.camo_seconds is not None:
        for _p, base in m.find_tags('eqip', CAMO_TAG):
            old = struct.unpack_from('<f', m.data, base + EQIP_POWERUP_TIME)[0]
            struct.pack_into('<f', m.data, base + EQIP_POWERUP_TIME, float(a.camo_seconds))
            print('  camo Powerup Time %.1fs -> %.1fs' % (old, a.camo_seconds))
            ok += 1
        if camo_ticks is None:
            camo_ticks = int(round(a.camo_seconds * 30))

    medi_rate = a.medi_rate
    medi_heal = a.medi_heal
    if a.medi_percent is not None:      # percent of max wins over raw units
        medi_heal = a.medi_percent / 100.0 * VIT_MAX
        print('  regeneration %g%% of max -> %g vitality units' % (a.medi_percent, medi_heal))
    if medi_rate is None and (medi_heal is not None or a.medi_duration is not None):
        heal = medi_heal if medi_heal is not None else read_global(m, 'medi_heal')
        ticks = a.medi_duration if a.medi_duration is not None else read_global(m, 'medi_ticks')
        if heal is not None and ticks:
            medi_rate = float(heal) / float(ticks)
            print('  regeneration %g over %d ticks -> %.5f per tick'
                  % (heal, int(ticks), medi_rate))

    # Powerup tuning globals (only those given). Real for magnitudes, short for ticks.
    for gname, gval in (('medi_rate', medi_rate),
                        ('os_shield', os_shield_raw), ('os_body', a.os_body),
                        ('os_ticks', a.os_duration),
                        ('os_cooldown', a.os_cooldown),
                        ('camo_ticks', camo_ticks),
                        ('camo_cooldown', a.camo_cooldown), ('medi_heal', medi_heal),
                        ('medi_ticks', a.medi_duration), ('medi_cooldown', a.medi_cooldown),
                        ('vit_max', a.vit_max),
                        ('fx_kind', a.fx_kind), ('fx_every', a.fx_every),
                        ('fx_ready', a.fx_ready), ('fx_ready_n', a.fx_ready_n),
                        ('fx_ready_gap', a.fx_ready_gap),
                        ('fx_ladder', a.fx_ladder), ('fx_min', a.fx_min),
                        ('fx_max', a.fx_max)):
        if gval is None:
            continue
        res = set_global(m, gname, gval)
        if res:
            print('  %s %s -> %s' % (gname, res[0], res[1]))
            ok += 1
        else:
            print('  !! global %s not found (map lacks the ability script)' % gname)

    # Starting weapon, via the patcher's own Starting Profile writer. A bare name like
    # "assault rifle" expands to the usual weapons\<n>\<n> tag path.
    if a.start_weapon:
        w = a.start_weapon
        if '\\' not in w:
            w = 'weapons\\%s\\%s' % (w, w)
        if not m.find_tags('weap', w):
            print('  !! no such weapon tag on this map: %s' % w)
        else:
            # _apply_starting_equipment takes halo.json-style "<class> <path>" tags.
            res = hp._apply_starting_equipment(m, 'Halo 1', reg,
                                               {'primary': 'weap ' + w, 'secondary': None})
            for r in res:
                print('  start weapon: %s %s' % (r.get('field', ''),
                                                 r.get('new') or r.get('reason', '')))
                ok += 1 if r.get('ok') else 0

    # Spawn modifiers: the vanilla mechanism -- Starting Shield/Health Modifier on the
    # player profiles. Not script globals; a scnr edit, so they work on any map with
    # profiles (and stack with the flashlight abilities rather than replacing them).
    for which, val in (('shield', a.spawn_shield), ('health', a.spawn_health)):
        if val is None:
            continue
        done = set_profile_vitality(m, which, val)
        for name, old in done:
            print('  spawn %s [%s] %.2f -> %.2f' % (which, name, old, val))
        ok += len(done)
        if not done:
            print('  !! no player profiles found to set spawn %s on' % which)

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
