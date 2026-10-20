r"""Options -> Weapon: 'Hunters drop a Fuel Rod' (opt-in, user 2026-10-19), every game but
Halo 2 (that one needs an H2EK rebuild with a new effect; parked by the user).

No game's Hunter can drop its own gun: in every game it is a modelless arm weapon with no
magazine (measured on the E: baselines, 2026-10-19). Per game:

  Halo 1      the rebuilt maps carry a death effect with a weapon part on the Hunter coll's
              body DEPLETED slot (ports_h1/fuel_rod.py); off blanks it -- CONFIRMED (b30)
  Halo 3 /    DEBRIS: the Hunter's armour-break effect already spawns debris objects (Halo
  ODST /      3 / ODST `trans_torso_destroyed`: back shield + two spikes, on the body's 50%
  Reach       response; Reach `back_destroyed`: back shield + spike, on the back-shield
              section). One spike becomes the game's fuel rod, and the effect moves to the
              Hunter's DEATH, so the rod and the debris fall when it dies (user: on death).
              Reach: onto the body's death response (threshold 0.0) -- CONFIRMED m70_bonus.
              Halo 3 / ODST have NO body response that fires on the killing blow (sc100,
              2026-10-19: a grown response at 0 / 0.001 and the burn response edited in
              place to 0.001 never fired; the rod at the 50% break did): the effect goes on
              the death ANIMATIONS instead -- one Effect Reference on the Hunter jmad and a
              frame-0 Effect Event on every kill animation (stock precedent: Brute / Elite /
              Flood morphs, the Engineer's chest bomb). Reach also makes the rod's closure
              resident wherever the Hunter is (m30 holds it in no Hunter set;
              reach_pools.apply_fix). Reach's gun 'Tossed Weapon' (+0x43C) dropped NOTHING.
  Halo 4      the Hunter gun's 'Tossed Override' (weap +0x290) -> storm_fuel_rod_cannon --
              stock precedent: the Crawler's modelless head weapons toss a real sniper
              rifle through it (m70)

The cache-map routes start from the baseline every patch, so off writes nothing.
"""
import os
import struct
import sys

BS = chr(92)


def _p(*parts):
    return BS.join(parts)


HUNTER = _p('objects', 'characters', 'hunter', 'hunter')          # hlmt + bipd, H3 to Reach
ROD = _p('objects', 'weapons', 'support_high', 'flak_cannon', 'flak_cannon')
_FX = _p('objects', 'characters', 'hunter', 'fx', 'destruction', '')

# The debris route, per game (plugins: Halo3MCC / ODSTMCC / ReachMCC hlmt + effe).
# ndi: the New Damage Info block holding the sections (None: they sit in the hlmt); sections
# and responses (offset, element); the response's threshold, Specific Transition Effect and
# its marker; effect events / parts (offset, element) and the part's Type; part = the one
# that becomes the rod (Halo 3 / ODST: the second spike; Reach: its only spike).
#
# death_anims (Halo 3 / ODST): the jmad Effect References (offset, element) and Animations
# (offset, element) with each animation's Effect Events (offset, element); `kills` picks the
# death animations by name (h_kill / s_kill, and landing_dead after an airborne death).
_H3 = {'ndi': None, 'sections': (0x68, 0x2C), 'responses': (0xC, 0x88), 'threshold': 0xC,
       'specific': 0x20, 'marker': 0x58, 'events': (0x2C, 0x44), 'parts': (0x20, 0x60),
       'type': 0x10, 'effect': _FX + 'trans_torso_destroyed', 'part': 2,
       'death_anims': {'refs': (0x2C, 0x14), 'anims': (0x50, 0x88), 'events': (0x44, 0xC),
                       'kills': ('h_kill:', 's_kill:', 'landing_dead')}}
DEBRIS = {
    'Halo 3': dict(_H3, ndi=0x88),
    'Halo 3: ODST': dict(_H3, ndi=0x94),
    'Halo Reach': {'ndi': None, 'sections': (0xE0, 0xC0), 'responses': (0x84, 0xB0),
                   'threshold': 0x8, 'specific': 0x20, 'marker': 0x30,
                   'events': (0x2C, 0x40), 'parts': (0x1C, 0x64), 'type': 0x14,
                   'effect': _FX + 'back_destroyed', 'part': 1},
}

TOSS = {
    'Halo 4': (_p('objects', 'characters', 'storm_hunter', 'hunter_fuel_rod',
                  'storm_storm_hunter_fuel_rod'), 0x290,
               _p('objects', 'weapons', 'support_high', 'storm_fuel_rod_cannon',
                  'storm_fuel_rod_cannon')),
}

EFFECT = 'Hunters drop a Fuel Rod'


def _row(field, ok=True, skip=False, tag='', old=None, new=None, reason=None):
    r = {'effect': EFFECT, 'field': field, 'ok': ok, 'tag': tag}
    for k, v in (('skip', skip or None), ('old', old), ('new', new), ('reason', reason)):
        if v is not None:
            r[k] = v
    return r


def _tag(m, cls, name):
    for t in m.tags:
        if isinstance(t, dict) and t.get('class') == cls and t.get('name') == name \
                and t.get('base') is not None:
            return t
    return None


def _weapon_ref(m, game, ident):
    """The 16 bytes of a tagRef to `ident`, copied from the scenario's weapon palette (the
    map's own encoding of group + ident), or None when the palette does not carry it."""
    import halo_patch as HP
    lay = HP._MAP_WEAPONS[game]
    off, es = lay['palette']
    scnr = HP._scnr_base(m)
    b, n = HP._block_base(m, scnr + off), max(0, m.i32(scnr + off))
    for i in range(n) if b else []:
        e = b + i * es + lay['pal_id_at'] - 0xC
        if m.u32(e + 0xC) == ident:
            return bytes(m.data[e:e + 16])
    return None


def _elems(m, at, esz):
    import halo_patch as HP
    n, b = m.i32(at), HP._block_base(m, at)
    return [b + i * esz for i in range(n)] if (b and n > 0) else []


def _name_of(m, ident):
    import halo_patch as HP
    return HP._tag_name_by_id(m, ident) if ident not in (0, 0xFFFFFFFF) else None


def _debris(m, game):
    L = DEBRIS[game]
    hlmt, effe, rod = _tag(m, 'hlmt', HUNTER), _tag(m, 'effe', L['effect']), _tag(m, 'weap', ROD)
    if hlmt is None:
        return [_row('Hunter model', skip=True, reason='no Hunter on this level')]
    if effe is None or rod is None:
        return [_row('Hunter model', ok=False, tag='hlmt',
                     reason='no %s in this map' % ('Hunter debris effect' if effe is None
                                                   else 'fuel rod'))]
    ref = _weapon_ref(m, game, rod['ident'])
    if ref is None:
        return [_row('Hunter model', ok=False, tag='weap',
                     reason='the fuel rod is not in the weapon palette')]
    root = hlmt['base']
    if L['ndi'] is not None:
        ndi = _elems(m, root + L['ndi'], 1)
        root = ndi[0] if ndi else None
    secs = _elems(m, root + L['sections'][0], L['sections'][1]) if root else []
    resp = [_elems(m, sc + L['responses'][0], L['responses'][1]) for sc in secs]
    spec = L['specific']
    src = [q for rs in resp for q in rs if m.u32(q + spec + 0xC) == effe['ident']]
    # the death response: the body's (section 0) lowest threshold
    body = sorted(resp[0] if resp else [],
                  key=lambda q: struct.unpack_from('<f', m.data, q + L['threshold'])[0])
    if not src or not body:
        return [_row('body responses', ok=False, tag='hlmt',
                     reason='no debris / death response on the Hunter')]
    events = _elems(m, effe['base'] + L['events'][0], L['events'][1])
    parts = _elems(m, events[0] + L['parts'][0], L['parts'][1]) if events else []
    if len(parts) <= L['part']:
        return [_row('debris effect', ok=False, tag='effe',
                     reason='%d parts, the spike part is missing' % len(parts))]
    pe = parts[L['part']] + L['type']
    old = _name_of(m, m.u32(pe + 0xC))
    m.data[pe:pe + 16] = ref
    s, d = src[0], body[0]
    if L.get('death_anims'):
        n = _death_anim_events(m, L, bytes(m.data[s + spec:s + spec + 16]),
                               m.u32(s + L['marker']))
        if not n:
            return [_row('death animations', ok=False, tag='jmad',
                         reason='no Hunter death animation / no slack to add the event')]
        d = None
    if d is not None and s != d:
        for off, k in ((spec, 16), (L['marker'], 4)):
            m.data[d + off:d + off + k] = m.data[s + off:s + off + k]
    # the old response keeps its generic effect (sparks), not the debris: once is enough
    struct.pack_into('<I', m.data, s + spec + 0xC, 0xFFFFFFFF)
    fx = L['effect'].split(BS)[-1]
    return [_row('%s part %d' % (fx, L['part']), tag='effe',
                 old=(old or '').split(BS)[-1], new=ROD.split(BS)[-1]),
            _row('death animations' if L.get('death_anims') else 'body death response effect',
                 tag='jmad' if L.get('death_anims') else 'hlmt', old='-',
                 new='%s (moved from the armour-break response)' % fx)]


def _grow(m, blk, esz, extra):
    """Append `extra` (bytes, whole elements) to the block at `blk` (count, pointer),
    relocated into partition slack as halo_patch grows H3 palettes. Returns the new
    elements' offset, or None."""
    import halo_patch as HP
    n = max(0, m.i32(blk))
    old = HP._block_base(m, blk) if n else None
    got = HP._h3_reserve(m, [n * esz + len(extra)])
    if not got:
        return None
    dst = got[0]
    if n:
        m.data[dst:dst + n * esz] = m.data[old:old + n * esz]
    e = dst + n * esz
    m.data[e:e + len(extra)] = extra
    struct.pack_into('<i', m.data, blk, n + len(extra) // esz)
    struct.pack_into('<I', m.data, blk + 4, m.off2data(dst))
    return e


def _death_anim_events(m, L, effect_ref, marker):
    """The debris effect on the Hunter's death animations: an Effect Reference on its jmad
    (`effect_ref`: the 16 tagRef bytes, copied from the torso response that held it), a
    frame-0 Effect Event at `marker` on every kill animation. Returns the events added."""
    A = L['death_anims']
    jmad = _tag(m, 'jmad', HUNTER)
    if jmad is None:
        return 0
    b = jmad['base']
    roff, res = A['refs']
    ref = bytearray(res)
    ref[0:16] = effect_ref
    idx = max(0, m.i32(b + roff))
    if _grow(m, b + roff, res, bytes(ref)) is None:
        return 0
    ev = bytearray(A['events'][1])
    struct.pack_into('<hhI', ev, 0, idx, 0, marker)
    n = 0
    for a in _elems(m, b + A['anims'][0], A['anims'][1]):
        name = str(m.resolve_stringid(m.u32(a)) or '')
        if any(k in name for k in A['kills']):
            if _grow(m, a + A['events'][0], A['events'][1], bytes(ev)) is not None:
                n += 1
    return n


def _reach_residency(m):
    """The rod's closure resident wherever the Hunter is (m30 holds it in no Hunter set)."""
    tk = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sprint_toolkit')
    if tk not in sys.path:
        sys.path.insert(0, tk)
    import reach_pools as rp
    rp.bind(m, 'Halo Reach')
    zb = rp.zone_base(m)
    sets, res = rp.zone_sets(m, zb), rp.tag_resources(m, zb)
    hunter, rod = _tag(m, 'bipd', HUNTER), _tag(m, 'weap', ROD)
    donor = rp.chain_of(m, zb, hunter['ident'], res) if hunter else None
    if not donor or rod is None:
        return 0
    return rp.apply_fix(m, zb, sets, res, rod['ident'], donor[0], donor[1])


def _toss(m, game):
    gun_name, off, rod_name = TOSS[game]
    gun, rod = _tag(m, 'weap', gun_name), _tag(m, 'weap', rod_name)
    if gun is None:
        return [_row('Hunter weapon', skip=True, reason='no Hunter on this level')]
    if rod is None:
        return [_row('Hunter weapon', ok=False, tag='weap', reason='no fuel rod in this map')]
    ref = _weapon_ref(m, game, rod['ident'])
    if ref is None:
        return [_row('Hunter weapon', ok=False, tag='weap',
                     reason='the fuel rod is not in the weapon palette')]
    at = gun['base'] + off
    old = _name_of(m, m.u32(at + 0xC))
    m.data[at:at + 16] = ref
    return [_row('Tossed Override', tag='weap',
                 old=(old or '-').split(BS)[-1], new=rod_name.split(BS)[-1])]


def apply(m, game, on):
    game = str(game).strip()
    if game == 'Halo 1':
        import h1_enemy_weapons as ew
        return ew.hunter_fuel_rod_drop(m, bool(on))
    if not on:
        return []
    if game in DEBRIS:
        out = _debris(m, game)
        if game == 'Halo Reach' and all(r.get('ok') and not r.get('skip') for r in out):
            n = _reach_residency(m)
            if n:
                out.append(_row('fuel rod residency', tag='zone',
                                new='%d pool bit(s) where the Hunter is' % n))
        return out
    if game in TOSS:
        return _toss(m, game)
    return []
