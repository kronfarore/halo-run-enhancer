r"""Time-to-kill on LEGENDARY, every game (user, 2026-10-13): shared core.

One method for all six games; each game has its own collector (ttk_<game>.py) that reads
the numbers out of the game's data and calls the functions here. Output: one JSON per game
in sprint_toolkit/reports/ttk/ and the combined report reports/ttk_legendary.md (ttk_report.py).

READ-ONLY, and safe beside other sessions (user: "make sure nobody else is using the tool"):
  * Halo 1 is read from the E: BASELINE MAPS, never the HCEEK kit (port sessions hold its
    kit lock and edit its tags);
  * H2EK / H3EK / H3ODSTEK / HREK / H4EK tags are read with `tool export-tag-to-xml` into a
    PRIVATE temp file (unique name, deleted after) -- port_field_audit.flatten_xml writes
    one fixed '_field_audit.xml' per kit, which two sessions would overwrite for each other.
    The parser is port_field_audit's, unchanged.

THE METHOD (signed off by the user 2026-10-13):
  * LEGENDARY only. Every shot hits, BODY shots only (no headshots), the target starts with
    full shield and body, nothing recharges during the fight (a fight longer than the
    target's shield recharge delay is FLAGGED, not modelled).
  * damage of one hit = the damage effect's UPPER bound (the mean of its min/max pair where
    the game has a pair) x every damage multiplier that applies:
      - H2+: the globals damage table -- damage group x armour; ALL rows found multiply
        (jpt general and specific x material general and specific; a missing row = 1).
        Verified in game for Halo 3 (the engine binary-searches and multiplies every row).
      - H1: the damage effect's own per-material modifier for the target's shield material
        and body material.
      - the difficulty dials (matg Difficulty, Legendary): enemy vitality / shield on the
        enemy's pool, enemy damage on what the AI deals to the player.
  * shield first; the shot that breaks the shield carries its EXCESS into the body at the
    body multiplier (excess x body_hit / shield_hit).
  * player -> enemy: the trigger is held at the weapon's own rate (rounds per second, or
    the fire recovery time if longer), with magazine RELOADS and OVERHEAT pauses in
    between. time = moment of the killing shot, first shot at t = 0.
  * enemy -> player: two times. 'held' = the AI firing continuously at its weapon rate x
    the character's / difficulty rate-of-fire factors; 'paced' = the same in the AI's own
    bursts (burst duration) with its burst separation between them. Paced is what the
    player feels; misses are not counted in either.
"""
import json
import math
import os
import re
import struct
import subprocess
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
STEAM = r'F:\SteamLibrary\steamapps\common'
OUT_DIR = os.path.join(HERE, 'reports', 'ttk')

_CACHE = {}


# ----------------------------------------------------------------------------- reading
def flatten(kit, tag):
    """{path: (type, value)} of a kit tag (H2EK / H3EK / H3ODSTEK / HREK / H4EK), read
    with a PRIVATE export file. Same keys as port_field_audit.flatten (its parsers, copied
    so the export path is ours)."""
    key = (kit, tag)
    if key in _CACHE:
        return _CACHE[key]
    ek = os.path.join(STEAM, kit)
    tmp = os.path.join(os.environ.get('TEMP') or ek,
                       'ttk_%s_%s.xml' % (os.getpid(), uuid.uuid4().hex[:8]))
    try:
        subprocess.run([os.path.join(ek, 'tool.exe'), 'export-tag-to-xml',
                        os.path.join(ek, 'tags', tag), tmp], cwd=ek, capture_output=True)
        if not os.path.exists(tmp) or not os.path.getsize(tmp):
            raise SystemExit('could not export %s from %s' % (tag, kit))
        vals = _parse_h2(tmp) if kit == 'H2EK' else _parse_xml(tmp)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    _CACHE[key] = vals
    return vals


SKIP_TYPES = ('pad', 'skip', 'explanation', 'struct', 'unknown', 'data')


def _parse_xml(path):
    """port_field_audit.flatten_xml's parser (H3 / ODST / Reach / H4 dialects)."""
    stack, vals = [], {}
    reach_block = {}
    for line in open(path, encoding='utf-8', errors='replace'):
        s = line.lstrip(' ')
        ind = len(line) - len(s)
        if s.startswith('</'):
            continue
        while stack and stack[-1][0] >= ind:
            stack.pop()
        here = '/'.join(n for _i, n in stack)
        m = re.match(r'<block name="([^"]*)" (?:value="[^"]*,|count=")(\d+)"', s)
        if m:
            vals[(here + '/' if here else '') + m.group(1).lower() + '/#count'] = ('count', m.group(2))
            stack.append((ind, m.group(1).lower()))
            continue
        m = re.match(r'<element index="(\d+)"', s)
        if m:
            owner = reach_block.get(ind)
            stack.append((ind, '%s/[%s]' % (owner, m.group(1)) if owner else '[%s]' % m.group(1)))
            continue
        m = re.match(r'<field name="([^"]*)" value="([^"]*)" type="([^"]*)"', s)
        if not m:
            continue
        name, val, typ = m.group(1).lower(), m.group(2), m.group(3)
        if typ == 'struct':
            stack.append((ind, name))
            continue
        if typ == 'block':
            vals[(here + '/' if here else '') + name + '/#count'] = ('count', val)
            reach_block[ind] = name
            continue
        if typ in SKIP_TYPES or not name or name.startswith('runtime'):
            continue
        key = (here + '/' if here else '') + name
        while key in vals:
            key += "'"
        vals[key] = (typ, val)
    return vals


def _parse_h2(path):
    """port_field_audit.flatten_h2's parser (Halo 2's real XML)."""
    import xml.etree.ElementTree as ET
    vals = {}

    def walk(node, p0):
        for c in node:
            name = (c.get('name') or '').lower()
            p = (p0 + '/' if p0 else '') + name
            if c.tag == 'block':
                vals[p + '/#count'] = ('count', str(len([e for e in c if e.tag == 'element'])))
                for e in c:
                    if e.tag == 'element':
                        walk(e, '%s/[%s]' % (p, e.get('index')))
            elif c.tag == 'tag_reference':
                vals[p] = ('tag reference', (c.text or '').strip())
            elif c.tag == 'block_index' and c.get('type'):
                # named by its TYPE ('location'): the name attribute is only 'long block index'
                q = (p0 + '/' if p0 else '') + c.get('type').lower()
                while q in vals:
                    q += "'"
                vals[q] = ('block index', c.get('index') or '')
            elif c.tag == 'field':
                typ = c.get('type') or ''
                if typ in SKIP_TYPES or not name or name.startswith('runtime'):
                    continue
                v = ' '.join((c.text or '').split())
                if 'enum' in typ:
                    v = re.sub(r'^-?\d+,', '', v)
                while p in vals:
                    p += "'"
                vals[p] = (typ, v.replace(', ', ','))
            elif len(c):
                walk(c, p)
    walk(ET.parse(path).getroot(), '')
    return vals


def num(v, default=0.0):
    try:
        return float(str(v[1] if isinstance(v, tuple) else v).split(',')[0])
    except (TypeError, ValueError, IndexError):
        return default


# ----------------------------------------------------------------------------- simulation
def shots_to_kill(shield, body, hit_shield, hit_body):
    """Number of hits to kill, and (shield hits, body hits). Overflow of the breaking shot
    carries into the body at the body multiplier."""
    if hit_body <= 0 and (shield <= 0 or hit_shield <= 0):
        return None, (0, 0)
    n, s, b = 0, float(shield), float(body)
    while b > 1e-9:
        n += 1
        if s > 1e-9:
            if hit_shield <= 0:
                return None, (n, 0)
            if hit_shield >= s:
                excess = hit_shield - s
                s = 0.0
                b -= excess * (hit_body / hit_shield) if hit_shield else 0
            else:
                s -= hit_shield
        else:
            if hit_body <= 0:
                return None, (n, 0)
            b -= hit_body
        if n > 100000:
            return None, (n, 0)
    return n, (n, 0)


def player_time(n, interval, mag=0, reload=0.0, heat_per_shot=0.0, overheat_at=1.0,
                overheat_pause=0.0):
    """Seconds until the n-th shot leaves (first shot at 0): n-1 intervals, a reload each
    time the magazine runs dry, an overheat pause each time the heat reaches the limit."""
    if n is None:
        return None
    t, heat, inmag = 0.0, 0.0, mag
    for i in range(1, n):
        dt = interval
        if mag:
            inmag -= 1
            if inmag <= 0:
                dt = max(dt, reload)
                inmag = mag
        if heat_per_shot:
            heat += heat_per_shot
            if heat >= overheat_at - 1e-9:
                dt = max(dt, overheat_pause)
                heat = 0.0
        t += dt
    return t


def player_time_drain(n, interval, heat_per_shot, loss_per_sec, overheat_at=1.0,
                      recovery_at=0.0, overheated_loss_per_sec=0.0, mag=0, reload=0.0):
    """player_time with heat that DRAINS WHILE FIRING (user, 2026-10-13: H3 and H4 both
    drain while the trigger is held; the earlier Focus Rifle reading was wrong). Each
    shot adds heat_per_shot; between shots heat falls by loss_per_sec x interval. At the
    threshold the gun locks until heat falls to recovery_at at the overheated loss rate.
    Returns (seconds, overheats)."""
    if n is None:
        return None, 0
    t, heat, inmag, over = 0.0, 0.0, mag, 0
    for i in range(1, n):
        heat += heat_per_shot
        dt = interval
        if mag:
            inmag -= 1
            if inmag <= 0:
                dt = max(dt, reload)
                inmag = mag
        if heat_per_shot and heat >= overheat_at - 1e-9:
            over += 1
            lock = (heat - recovery_at) / (overheated_loss_per_sec or loss_per_sec or 1.0)
            dt = max(dt, lock)
            heat = recovery_at
        else:
            heat = max(0.0, heat - loss_per_sec * dt)
        t += dt
    return t, over


# ----------------------------------------------------------------------------- the 30 Hz trigger
#: MEASURED in all six games (Halo 2: the Plasma Repeater port 2026-11-22, reports/h2_fire_rule.jsonl;
#: Halo 3 / ODST / Reach / Halo 4 / Halo 2 at 30/s: rof_test_stage.py 2026-11-23, reports/rof_test.jsonl;
#: Halo 1: h1_weapon_state_probe, ttk_halo1.player_ticks): every tick rate / 30 is added in float32,
#: a shot leaves when the sum reaches 1 and the sum RESETS -- a shot every ceil(30 / rate) ticks.
#: No game caps at 15/s: a 30 tag fires every tick (Halo 2 measured 2026-11-23; Halo 1 by the
#: Focus Rifle probe -- its Sentinel Beam's 15/s is most likely the age rate-of-fire penalty).
TICK_HZ = 30.0


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def tick_rate(rate, min_ticks=1):
    """Rounds a second the reset rule fires for a CONSTANT rate (min_ticks 2 = Halo 1's cap)."""
    if rate <= 0:
        return 0.0
    step, s, n = f32(rate / TICK_HZ), 0.0, 0
    while s < 1.0:
        s = f32(s + step)
        n += 1
    return TICK_HZ / max(n, min_ticks)


def tick_shots(n, w, limit_s=600.0, cool_while_firing=True, rate_fn=None):
    """Ticks (30 Hz, from the trigger pull at tick 0) of the first n shots, trigger held, by the
    measured reset rule. `w` (the collectors' weapon dict): 'rps' [lo, hi] (a rate of 0 reads as
    30, every tick: the RECOVERY weapons' placeholder), 'accel', 'shots per fire' [lo, hi],
    'fire recovery', 'heat per round', 'overheated threshold', 'heat recovery threshold',
    'heat loss', 'overheated heat loss', 'mag', 'reload'; optional 'heat per tick' (heat while
    the trigger is held: Reach's per-tick heat function) and 'never overheats'.
      * every tick the rate (ramped lo -> hi over 'acceleration time' of HELD time, or
        rate_fn(heat) for a heat-driven rate) / 30 is added in float32 to a sum that starts at 0
        on the pull; a shot leaves on the tick the sum reaches 1 and the sum resets to 0;
      * heat + per round on a shot, - 'heat loss per second' / 30 every tick (while firing too,
        unless cool_while_firing is False); at the overheated threshold the gun stops, cools at
        'overheated heat loss per second' / 30 a tick to the recovery threshold, then the
        trigger starts over (sum 0, ramp from lo) -- ASSUMED as the cold start;
      * 'shots per fire' > 1 = a burst at the barrel rate, then 'fire recovery time' (rounded UP
        to whole ticks) from the burst's last shot before the next may leave (the sum keeps
        running); without bursts the recovery gates every shot the same way -- ASSUMED;
      * an empty magazine: the next shot leaves when the reload time (rounded up to ticks) has
        passed after the last round, and the ramp restarts.
    Returns (ticks list, events)."""
    lo, hi = [r if r > 0 else TICK_HZ for r in w['rps']]
    spf = w.get('shots per fire') or [1.0, 1.0]
    burst = int(spf[1]) if spf[1] > 1 else 1
    rec_ticks = int(math.ceil(w['fire recovery'] * TICK_HZ - 1e-6)) if w.get('fire recovery') else 0
    # the recovery is the cooldown between FIRES: it paces a one-shot-a-pull weapon (shots per
    # fire 1, or a rate of 0) but not a held automatic (shots per fire 0 = fire while held) --
    # Reach's Needler (12/s, recovery 0.2) would otherwise fire 5/s. INFERRED, not measured
    gate_each = burst == 1 and (spf[1] >= 1 or all(r <= 0 for r in w['rps']))
    hpr, oh = w.get('heat per round') or 0.0, w.get('overheated threshold') or 1.0
    hpt = w.get('heat per tick') or 0.0
    can_overheat = bool(hpr or hpt) and not w.get('never overheats')
    loss = (w.get('heat loss') or 0.0) / TICK_HZ
    loss_oh = (w.get('overheated heat loss') or w.get('heat loss') or 1.0) / TICK_HZ
    rec_at = w.get('heat recovery threshold') or 0.0
    mag, reload_ticks = w.get('mag') or 0, int(math.ceil((w.get('reload') or 0.0) * TICK_HZ - 1e-6))
    s, heat, held, inmag, in_burst = 0.0, 0.0, 0, mag, 0
    tick, busy_until, reloading, overheated, oh_tick = 0, 0, False, False, 0
    shots = []
    ev = {'overheats': 0, 'reloads': 0, 'bursts': 0, 'first overheat at shot': None}
    while len(shots) < n and tick < limit_s * TICK_HZ:
        if overheated:
            heat -= loss_oh
            if heat <= rec_at + 1e-9:
                overheated, s, held = False, 0.0, 0
                heat = max(heat, 0.0)
                ev['overheat pause s'] = round((tick + 1 - oh_tick) / TICK_HZ, 3)
            tick += 1
            continue
        if reloading:
            if tick >= busy_until:
                reloading, s, held = False, 1.0, 0   # ready: leaves on this tick
        else:
            if rate_fn is not None:
                rate = rate_fn(heat)
            else:
                rate = hi if not w.get('accel') else lo + (hi - lo) * min(1.0, held / TICK_HZ / w['accel'])
            s = f32(s + f32(rate / TICK_HZ))
            heat = min(1.0, heat + hpt) if hpt else heat
        if s >= 1.0 and tick >= busy_until:
            if shots:
                ev['longest gap s'] = round(max(ev.get('longest gap s') or 0.0,
                                                (tick - shots[-1]) / TICK_HZ), 3)
            shots.append(tick)
            s = 0.0
            heat += hpr
            in_burst += 1
            if burst > 1:
                if in_burst >= burst:
                    busy_until = tick + rec_ticks
                    in_burst = 0
                    ev['bursts'] += 1
            elif rec_ticks and gate_each:
                busy_until = tick + rec_ticks
            if mag:
                inmag -= 1
                if inmag <= 0:
                    busy_until = tick + reload_ticks
                    reloading, inmag, in_burst = True, mag, 0
                    ev['reloads'] += 1
            if can_overheat and heat >= oh - 1e-9 and len(shots) < n:
                overheated, oh_tick = True, tick
                ev['overheats'] += 1
                if ev['first overheat at shot'] is None:
                    ev['first overheat at shot'] = len(shots)
                tick += 1
                continue
        if cool_while_firing:
            heat = max(0.0, heat - loss)
        if not reloading:
            held += 1
        tick += 1
    return shots, ev


def tick_seconds(n, w, **kw):
    """(seconds from the FIRST shot to the n-th, events) by tick_shots; (None, events) when the
    gun never gets there. The pull-to-first-shot ticks are not counted (TTK's first shot at 0)."""
    if n is None:
        return None, {}
    shots, ev = tick_shots(n, w, **kw)
    if len(shots) < n:
        return None, ev
    return (shots[-1] - shots[0]) / TICK_HZ, ev



def ai_times(n, shots_per_sec, burst_duration=0.0, burst_separation=0.0):
    """(held, paced) seconds until the AI's n-th hit. Paced: bursts of `burst_duration`
    seconds at the same rate, `burst_separation` seconds between them."""
    if n is None or shots_per_sec <= 0:
        return None, None
    held = (n - 1) / shots_per_sec
    if burst_duration <= 0 or burst_separation <= 0:
        return held, held
    per_burst = max(1, int(burst_duration * shots_per_sec + 1e-9) + 1)
    bursts_before = (n - 1) // per_burst
    in_last = (n - 1) % per_burst
    paced = bursts_before * ((per_burst - 1) / shots_per_sec + burst_separation) + \
        in_last / shots_per_sec
    return held, paced


# ----------------------------------------------------------------------------- output
def write(game, rows, notes=()):
    """rows: dicts with keys
      direction  'player->enemy' | 'enemy->player'
      attacker, target, weapon     labels
      shots, seconds               (enemy->player: seconds = held)
      seconds_paced                enemy->player only
      inputs                       every number used, with where it came from
      flags                        list of strings ('fight outlasts shield recharge delay', ...)"""
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, 'ttk_%s.json' % game.lower().replace(' ', '_').replace(':', ''))
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'game': game, 'difficulty': 'Legendary', 'rows': rows, 'notes': list(notes)},
                  f, indent=1)
    return path
