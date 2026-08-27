"""Reload-speed patching via first-person animation graphs (jmad), for the weapons
whose reload has no tag-side timer — the reload duration is the length of the
first-person reload ANIMATION. This module scales those animations in place. Supports
Halo 3 and Halo 2 (the two share the jmad approach but differ in block offsets).

Identification is robust, not frame-count guesswork: every fp graph's `Modes` tree
maps action Labels (stringIDs like `reload_empty`, `reload_full`, and the shotgun's
`reload_enter`/`reload_continue_*`/`reload_exit`) to an Animation Index. We resolve
each Action label to its name and take every animation targeted by a `reload*`
action, then scale that animation's Frame Count and every keyed event frame by the
multiplier, so the mag-refill keyframe and sounds stay in sync.

Two dedup traps handled: several actions point at the same animation index, and
several animations share one physical event block — each animation and each event
element is scaled exactly once.

Layouts (see Assembly Halo3/Halo2/ODST jmad.xml):
  Halo 3: Animations @0x50 el0x88 (Frame Count i16@0x10); event blocks 0x2C/0x38/0x44/0x50
          (frame i16@+0x2); Modes @0x5C el0x28 -> WClass @0x4 el0x1C -> WType @0x4 el0x34
          -> Actions @0x4 el0x08 (Label sid@0, Anim Index i16@6).
  ODST:   Halo 3's, except Effect Events is el0xC (not 0x8) -- the ONLY divergence.
  Halo 2: Animations @0x2C el0x60 (Frame Count i16@0x14); event blocks 0x40/0x48/0x50
          (frame i16@+0x2); Modes @0x34 el0x14 -> WClass @0x4 el0x14 -> WType @0x4 el0x34
          -> Actions @0x4 el0x08 (Label sid@0, Anim Index i16@6).
"""
import struct

# (anim_blk, anim_el, frame_count_off, event_blocks[(blk,el)], frame_off_in_event,
#  modes_blk, modes_el, wclass_blk, wclass_el, wtype_blk, wtype_el, actions_blk,
#  actions_el, action_anim_idx_off)
LAYOUTS = {
    'Halo 3': dict(anim_blk=0x50, anim_el=0x88, fc_off=0x10,
                   events=((0x2C, 0x04), (0x38, 0x08), (0x44, 0x08), (0x50, 0x04)),
                   frame_off=0x2, modes_blk=0x5C, modes_el=0x28,
                   wclass_blk=0x04, wclass_el=0x1C, wtype_blk=0x04, wtype_el=0x34,
                   actions_blk=0x04, actions_el=0x08, act_anim_off=0x6),
    'Halo 2': dict(anim_blk=0x2C, anim_el=0x60, fc_off=0x14,
                   events=((0x40, 0x04), (0x48, 0x08), (0x50, 0x04)),
                   frame_off=0x2, modes_blk=0x34, modes_el=0x14,
                   wclass_blk=0x04, wclass_el=0x14, wtype_blk=0x04, wtype_el=0x34,
                   actions_blk=0x04, actions_el=0x08, act_anim_off=0x6),
    # ODST was missing entirely, so `scale_reload` bailed with "no reload layout for
    # Halo 3: ODST" on every ODST map and the reload cards -- inherited from Halo 3 like
    # the rest -- never did anything. Its jmad is Halo 3's with ONE difference: Effect
    # Events is 0xC per element, not 0x8. Striding it at 8 would walk the wrong frame
    # fields and corrupt the sound/effect timing of every reload it touched, so the
    # layout is copied out rather than aliased to Halo 3's.
    'Halo 3: ODST': dict(anim_blk=0x50, anim_el=0x88, fc_off=0x10,
                         events=((0x2C, 0x04), (0x38, 0x08), (0x44, 0x0C), (0x50, 0x04)),
                         frame_off=0x2, modes_blk=0x5C, modes_el=0x28,
                         wclass_blk=0x04, wclass_el=0x1C, wtype_blk=0x04, wtype_el=0x34,
                         actions_blk=0x04, actions_el=0x08, act_anim_off=0x6),
}


def _reload_anim_indices(m, base, L, match=('reload',)):
    """Animation indices driven by any action whose resolved label contains one of
    `match`. Deduped, order-preserving.

    `match` is a parameter because the swap is the same problem as the reload: weapon
    SWAP speed is the `ready` and `put_away` animations in this very graph, and no
    weap field drives it (Ready Time is non-zero on three weapons, ODST's Weapon Ready
    1st Person Animation Playback Scale on none at all).
    """
    out, seen = [], set()
    for mo in m.follow_all(base, [L['modes_blk']], [L['modes_el']], 'all'):
        for wc in m.follow_all(mo, [L['wclass_blk']], [L['wclass_el']], 'all'):
            for wt in m.follow_all(wc, [L['wtype_blk']], [L['wtype_el']], 'all'):
                for a in m.follow_all(wt, [L['actions_blk']], [L['actions_el']], 'all'):
                    label = struct.unpack_from('<I', m.data, a)[0]
                    name = m.resolve_stringid(label)
                    if not name or not any(k in name for k in match):
                        continue
                    ai = struct.unpack_from('<h', m.data, a + L['act_anim_off'])[0]
                    if ai >= 0 and ai not in seen:
                        seen.add(ai)
                        out.append(ai)
    return out


FPS = 30.0     # jmad/antr animations play at 30 fps (NTSC); reload seconds = frames / FPS


def reload_frames(m, tag_pattern, game='Halo 3'):
    """Reference read for the patcher: reload-animation frame counts per graph, as
    [(who, [frames...]), ...]. Abstracts the H1 antr vs H2/H3 jmad layouts. `who` is a
    friendly label (Master Chief / Arbiter / tag basename). Returns [] if none found."""
    g = str(game).strip()

    def who_of(name):
        if 'dervish' in name:
            return 'Arbiter'
        if 'masterchief' in name:
            return 'Master Chief'
        base = name.rsplit(chr(92), 1)[-1]
        return 'first-person' if base == 'fp' else base

    out = []
    if g == 'Halo 1':
        for name, base in m.find_tags('antr', tag_pattern):
            fcs = []
            for el in m.follow_all(base, [H1_ANIM_BLK], [H1_ANIM_EL], 'all'):
                nm = m.data[el:m.data.index(b'\x00', el)].decode('latin1', 'replace')
                if 'reload' in nm.lower():
                    fcs.append(struct.unpack_from('<h', m.data, el + H1_FC)[0])
            if fcs:
                out.append((who_of(name), sorted(set(fcs))))
        return out
    L = LAYOUTS.get(g)
    if L is None or not hasattr(m, 'resolve_stringid'):
        return out
    for name, base in m.find_tags('jmad', tag_pattern):
        anims = m.follow_all(base, [L['anim_blk']], [L['anim_el']], 'all')
        fcs = sorted({struct.unpack_from('<h', m.data, anims[i] + L['fc_off'])[0]
                      for i in _reload_anim_indices(m, base, L)})
        if fcs:
            out.append((who_of(name), fcs))
    return out


def _scale_frame(m, off, mult, cap):
    v = struct.unpack_from('<h', m.data, off)[0]
    nv = max(0, min(cap, int(round(v * mult))))
    struct.pack_into('<h', m.data, off, nv)
    return v, nv


# --- Halo 1: model_animations (antr) master Animations block ---
# elem 0xB4: Name ascii@0x0 (0x20), Frame Count i16@0x22, Loop Frame @0x2E,
# Key Frame @0x34, Second Key Frame @0x36, Sound Frame @0x3E, foot i8 @0x40/0x41.
H1_ANIM_BLK, H1_ANIM_EL, H1_FC = 0x74, 0xB4, 0x22
H1_I16_FRAMES = (0x2E, 0x34, 0x36, 0x3E)
H1_I8_FRAMES = (0x40, 0x41)


def _scale_reload_h1(m, tag_pattern, mult, match=('reload',)):
    tags = m.find_tags('antr', tag_pattern)
    if not tags:
        return {'ok': False, 'reason': f'no antr tags match {tag_pattern!r}'}
    graphs = anims_scaled = edits = 0
    for _, base in tags:
        anims = m.follow_all(base, [H1_ANIM_BLK], [H1_ANIM_EL], 'all')
        hit = False
        for el in anims:
            nm = m.data[el:m.data.index(b'\x00', el)].decode('latin1', 'replace')
            if not any(k in nm.lower() for k in match):
                continue
            hit = True
            _, new_fc = _scale_frame(m, el + H1_FC, mult, 0x7FFF)
            if new_fc < 1:
                new_fc = 1
                struct.pack_into('<h', m.data, el + H1_FC, 1)
            anims_scaled += 1
            edits += 1
            cap = new_fc - 1
            for off in H1_I16_FRAMES:
                _scale_frame(m, el + off, mult, cap)          # 0 stays 0
                edits += 1
            for off in H1_I8_FRAMES:
                v = m.data[el + off]
                if v not in (0, 0xFF):                        # 0xFF = unset
                    m.data[el + off] = max(0, min(cap, int(round(v * mult))))
        if hit:
            graphs += 1
    if anims_scaled == 0:
        return {'ok': True, 'skip': True, 'reason': 'no reload animations found',
                'graphs': graphs, 'animations': 0, 'edits': 0}
    return {'ok': True, 'graphs': graphs, 'animations': anims_scaled, 'edits': edits}


def scale_reload(m, tag_pattern, mult, game='Halo 3', match=('reload',)):
    """Scale animation length by `mult` (0.5 = half duration = faster) on every jmad
    tag matching `tag_pattern`. `match` picks WHICH actions: ('reload',) for reload
    speed, ('ready', 'put_away') for weapon swap speed.

    Scale reload animation length by `mult` on every jmad tag matching `tag_pattern`. Idempotency is the caller's job: like every op it
    runs from the pristine .bak baseline, so re-patching re-scales the original frame
    counts rather than compounding. Returns a report dict."""
    if mult is None or mult <= 0:
        return {'ok': False, 'reason': 'invalid reload multiplier'}
    if str(game).strip() == 'Halo 1':
        return _scale_reload_h1(m, tag_pattern, mult, match)  # antr, ascii-named, no stringID
    L = LAYOUTS.get(str(game).strip())
    if L is None:
        return {'ok': False, 'reason': f'no reload layout for {game}'}
    if not hasattr(m, 'resolve_stringid'):
        return {'ok': False, 'reason': f'{game} map has no stringID resolver'}
    tags = m.find_tags('jmad', tag_pattern)
    if not tags:
        return {'ok': False, 'reason': f'no jmad tags match {tag_pattern!r}'}
    graphs = anims_scaled = edits = 0
    seen_events = set()          # (frame_field_addr) — event blocks are shared between anims
    fo = L['frame_off']
    for _, base in tags:
        idxs = _reload_anim_indices(m, base, L, match)
        if not idxs:
            continue
        anims = m.follow_all(base, [L['anim_blk']], [L['anim_el']], 'all')
        graphs += 1
        for ai in idxs:
            if not (0 <= ai < len(anims)):
                continue
            el = anims[ai]
            _, new_fc = _scale_frame(m, el + L['fc_off'], mult, 0x7FFF)
            if new_fc < 1:
                new_fc = 1
                struct.pack_into('<h', m.data, el + L['fc_off'], 1)
            anims_scaled += 1
            edits += 1
            cap = new_fc - 1
            for blk_off, elem_sz in L['events']:
                for e in m.follow_all(el, [blk_off], [elem_sz], 'all'):
                    key = e + fo
                    if key in seen_events:
                        continue
                    seen_events.add(key)
                    _scale_frame(m, e + fo, mult, cap)
                    edits += 1
    if anims_scaled == 0:
        return {'ok': True, 'skip': True, 'reason': 'no reload animations found',
                'graphs': graphs, 'animations': 0, 'edits': 0}
    return {'ok': True, 'graphs': graphs, 'animations': anims_scaled, 'edits': edits}
