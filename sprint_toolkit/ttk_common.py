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
import os
import re
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
