r"""Stage the Stable Grenades in-game test: one level per game, built from the E: baseline.

    python sprint_toolkit\stable_grenades_stage.py            # build both sets
    python sprint_toolkit\stable_grenades_stage.py --check    # only re-read the staged maps
    python sprint_toolkit\stable_grenades_stage.py "Halo 1"   # only the named game(s)
    ... --stable-only                                        # rebuild only the stable set
Two sets under E:\HaloBackups\stable_grenades_test\, each laid out like the MCC folder:
  vanilla\  the baseline through halo_patch.apply_run with an EMPTY plan
  stable\   the same, plus the Stable Grenades card of every grenade of that game
  itemonly\ Halo 2 only: the card's item-flag write alone (no hlmt write). Tells whether
            the eqip flag by itself stops a pickup chaining -- the H2 plasma pickup shares
            its hlmt TAG with the thrown plasma grenade, so the hlmt write reaches both.
  accel\    Halo 1 / 2 / 3: vanilla + "does accelerate" on every placed grenade (the gate?)
Halo 2 and Halo 3 copies carry test buffs (god shield, run x2, a player-only x1000 weapon).
All go through the same apply_run with the same options, so the ONLY difference between
the two is this card. stable_grenades_test.cmd swaps them into the game (and back).

Halo 1 SWAP (both sets, 2026-11-06): the vanilla a30 test showed placed frag pickups do
not chain while dropped plasma pickups do. To tell "placed vs dropped" apart from "frag vs
plasma", every Halo 1 copy is staged with the grenade kinds swapped:
  placed  -> plasma: scnr equipment palette entries naming the frag eqip name the plasma one
  dropped -> frag:   matg Grenades[*].equipment (what a dying unit drops) = the frag eqip
Thrown grenades, carried counts and the pickups' own grenade type are untouched.

Levels (placed grenade pickups, scnr Equipment block, 2026-11-05):
  Halo 1  a30 Halo                  17 frag (plasma only from Covenant drops)
  Halo 2  01b Cairo Station         13 frag, 26 plasma
  Halo 3  100 The Covenant          18 frag, 22 plasma, 26 spike, 1 firebomb
  ODST    h100 Mombasa Streets      28 frag, 13 plasma, 7 spike, 17 firebomb
  Reach   m60 The Package           18 frag, 12 plasma
  Halo 4  m40_invasion Infinity     8 frag, 61 plasma, 4 pulse
"""
import json
import os
import shutil
import struct
import sys

TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL)
sys.path.insert(0, os.path.join(TOOL, "sprint_toolkit"))
os.chdir(TOOL)
import halo_enhancer as he    # noqa: E402
import halo_patch as hp       # noqa: E402

C = dict(he.CONFIG)
C.update(json.load(open(os.path.join(TOOL, 'settings.json'), encoding='utf-8')))
OUT = r'E:\HaloBackups\stable_grenades_test'
LEVELS = {'Halo 1': 'a30', 'Halo 2': '01b', 'Halo 3': '100', 'Halo 3: ODST': 'h100',
          'Halo Reach': 'm60', 'Halo 4': 'm40_invasion'}
GRENADES = ('Frag Grenade', 'Plasma Grenade', 'Claymore Grenade', 'Firebomb Grenade',
            'Pulse Grenade')
DB = json.load(open(os.path.join(TOOL, 'halo.json'), encoding='utf-8'))
GAMES = list(DB['Missions'])
SW = DB['Player Modifiers']['Specific Weapon Modifier']


def plan_for(game, item_only=False):
    """The plan PatchDialog builds for one positive pick of each grenade's card
    (item_only: keep only the eqip item-flag ops)."""
    plan = []
    for w in GRENADES:
        eff = SW[w].get('Stable Grenades')
        if not eff or game not in eff['game']:
            continue
        ops = [{'field': t['field'], 'block': t.get('block'), 'index': 0,
                'nth': t.get('nth', 0) or 0, 'tag': t.get('tag'),
                'unshare': bool(t.get('unshare')),
                **({'set': t['set']} if t.get('set') is not None else
                   {('set_bit' if t.get('flag_on') else 'clear_bit'): t['flag']})}
               for t in he.resolve_gamed(eff['targets'], game, GAMES)
               if not item_only or (t.get('tag') or '').startswith('eqip ')]
        plan.append({'tag': he.resolve_gamed(eff['tag'], game, GAMES),
                     'name': 'Stable Grenades', 'ops': ops, 'weapon': w})
    return plan


def _h1_eqip_ref(m, path):
    """(name pointer, tag id) of a Halo 1 eqip tag, read from the tag index."""
    for row in range(m.tag_count):
        b = m.tag_array_off + row * 32
        if m.data[b:b + 4] == b'piqe' and hp._tag_name_by_id(m, m.u32(b + 0xC)) == path:
            return m.u32(b + 0x10), m.u32(b + 0xC)
    raise KeyError(path)


def h1_swap_grenades(path):
    """Placed grenade pickups -> plasma, dropped grenades -> frag (see the header)."""
    m = hp.open_map(path, 'Halo 1')
    frag, plasma = 'weapons\\frag grenade\\frag grenade', 'weapons\\plasma grenade\\plasma grenade'
    fr, pr = _h1_eqip_ref(m, frag), _h1_eqip_ref(m, plasma)
    out = []
    sb = hp._scnr_base(m)
    po, pe = hp._MAP_EQUIPMENT['Halo 1']['palette']
    pb = hp._block_base(m, sb + po)
    for i in range(m.i32(sb + po)):
        e = pb + i * pe
        if hp._tag_name_by_id(m, m.u32(e + 0xC)) == frag:
            struct.pack_into('<II', m.data, e + 4, pr[0], 0)
            struct.pack_into('<I', m.data, e + 0xC, pr[1])
            out.append('placed palette %d: frag -> plasma' % i)
    gb = m.find_tags('matg', 'globals' + chr(92) + 'globals')[0][1]
    base = hp._block_base(m, gb + 296)                # Grenades, 68-byte entries
    for i in range(m.i32(gb + 296)):
        e = base + i * 68 + 36                        # equipment tag reference
        was = hp._tag_name_by_id(m, m.u32(e + 0xC))
        if was != frag:
            struct.pack_into('<II', m.data, e + 4, fr[0], 0)
            struct.pack_into('<I', m.data, e + 0xC, fr[1])
            out.append('dropped type %d: %s -> frag' % (i, was.split(chr(92))[-1]))
    m.save(path)
    return out


# scnr Equipment placement: offset of the Equipment (H1: Misc) Flags inside one entry;
# bit 2 = "does accelerate (moves due to explosions)". OFF on every placed grenade of
# every campaign map in all six games (survey 2026-11-06).
EQUIP_FLAGS_AT = {'Halo 1': 34, 'Halo 2': 52, 'Halo 3': 84, 'Halo 3: ODST': 84,
                  'Halo Reach': 88, 'Halo 4': 156}


def accelerate_placed(path, game):
    """`accel` set: turn ON "does accelerate (moves due to explosions)" on every placed
    grenade pickup. CONFIRMED the gate in Halo 1 (a30, 2026-11-06): off, placed grenades
    don't chain while dropped ones (no placement) do; on, placed ones chain too. Halo 2
    CONFIRMED too (01b, 2026-11-08). Halo 3: same flag at +84, unproven -- its set tests it."""
    m = hp.open_map(path, game)
    E = hp._MAP_EQUIPMENT[game]
    at = EQUIP_FLAGS_AT[game]
    fmt = '<H' if game == 'Halo 1' else '<I'
    sb = hp._scnr_base(m)
    po, pe = E['palette']
    pb = hp._block_base(m, sb + po)
    gren = {i for i in range(m.i32(sb + po))
            if 'grenade' in (hp._tag_name_by_id(m, m.u32(pb + i * pe + E['pal_id_at'])) or '')}
    io, ie = E['items']
    ib = hp._block_base(m, sb + io)
    n = 0
    for i in range(m.i32(sb + io)):
        e = ib + i * ie
        if struct.unpack_from('<h', m.data, e)[0] in gren:
            f = struct.unpack_from(fmt, m.data, e + at)[0]
            struct.pack_into(fmt, m.data, e + at, f | 4)
            n += 1
    m.save(path)
    return '%d placed grenades: does accelerate on' % n


H2_CHEAT_ROUNDS = (36, 360)


def h2_test_buffs(path):
    """Test aids on every Halo 2 copy (user 2026-11-07: faster run, more shield and
    vitality, a stronger player-only weapon) -- the Halo 2 Armed-test helpers:
    h2_armed_test.god_shield (player body + shield 1e6, no stun) and cheat_map (Covenant
    Carbine slug damage x1000, matg run / sneak x2), plus the Carbine as the SECONDARY of
    the two player starting profiles. No 01b squad carries the Carbine, so only the player
    holds the x1000 slug. The grenade data the test is about is not touched."""
    import h2_armed_test as T
    m = hp.open_map(path, 'Halo 2')
    out = ['god shield: ' + (', '.join(T.god_shield(m)) or 'NO player model')]
    out += T.cheat_map(m)
    sb = hp._scnr_base(m)
    pb = hp._block_base(m, sb + 0x98)               # weapon palette, 0x28 entries
    ids = {hp._tag_name_by_id(m, m.u32(pb + i * 0x28 + 4)): m.u32(pb + i * 0x28 + 4)
           for i in range(m.i32(sb + 0x98))}
    cid = ids.get('objects\\weapons\\rifle\\covenant_carbine\\covenant_carbine')
    if cid is None:
        out.append('Carbine NOT in the weapon palette -- no cheat weapon')
    else:
        reg = hp.PluginRegistry(C['assembly_plugins_dir'], C['plugin_subdirs_by_game']['Halo 2'])
        bf = reg.get('scnr').find('Starting Health Damage', 'Player Starting Profile') or \
            reg.get('scnr').find('Starting Health Modifier', 'Player Starting Profile')
        boff, es = bf['block_offsets'][-1], bf['block_sizes'][-1]
        for i in range(min(2, m.i32(sb + boff))):     # 0 spawn, 1 respawn
            poff = m.follow(sb, [boff], [es], i)
            hp._write_starting_weapon(m, poff, 'secondary', cid, *H2_CHEAT_ROUNDS, 'Halo 2')
            out.append('profile %d secondary = Carbine %d/%d' % ((i,) + H2_CHEAT_ROUNDS))
    m.save(path)
    return out


#: Halo 3 cheat weapon: NOT the Carbine -- on 100 eleven squad entries hand it to Brutes and
#: Jackals. The SMG is in 100's palette (the rebuild's dz_enhancer) but no squad carries it;
#: its damage effect is shared only with the Silenced SMG, which no squad carries either.
H3_CHEAT = ('objects\\weapons\\rifle\\smg\\smg',
            'objects\\weapons\\rifle\\smg\\damage_effects\\smg_bullet')


def h3_test_buffs(path):
    """Test aids on every Halo 3 copy (the user's 2026-11-07 rule for these tests) -- the
    Halo 3 Armed-test helper h3_armed_test.god_and_cheat with the SMG as the cheat weapon:
    masterchief body + shield 1e6 (no stun, 0.1 s recharge), smg_bullet damage x1000, the
    SMG as every chief profile's secondary, matg run / sneak x2."""
    import contextlib
    import io
    import h3_armed_test as T
    T.CHEAT_WEAPON, T.CHEAT_DAMAGE = H3_CHEAT
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(path, 'Halo 3')
    out = []
    T.god_and_cheat(m, out)
    m.save(path)
    # god_and_cheat's report text names the Carbine whatever CHEAT_* hold
    return [s.replace('carbine_slug', 'smg_bullet').replace('covenant_carbine', 'smg')
            for s in out]


def flag_rows(path, game, reg):
    """(tag, flags) of the grenade pickups' item flags and models' damage flags."""
    m = hp.open_map(path, game)
    out = []
    eq = reg.get('eqip')
    allf = [f for f in eq.fields if f['name'].lower() == 'flags']
    item = [i for i, f in enumerate(allf) if 'always maintains z up' in (f.get('bits') or {})]
    for tp, tb in m.find_tags('eqip', '*grenade*'):
        out.append(('eqip ' + tp, m.read_tag_field(tb, 'Flags', eq, None, 0, item[0])))
    if game != 'Halo 1':
        pl = reg.get('hlmt')
        blk = 'Old Damage Info' if game in ('Halo Reach', 'Halo 4') else 'New Damage Info'
        for tp, tb in m.find_tags('hlmt', '*grenade*'):
            v = m.read_tag_field(tb, 'Flags', pl, blk)
            if v is not None:
                out.append(('hlmt ' + tp, v))
    return out


def main(check_only=False, only=()):
    for g, mid in LEVELS.items():
        if only and g not in only:
            continue
        reg = hp.PluginRegistry(C['assembly_plugins_dir'], C['plugin_subdirs_by_game'][g])
        sub = C['map_game_folder'][g]
        live = hp.default_map_path(C['mcc_root'], sub, mid)
        src = hp.existing_baseline(live, C.get('baseline_root'), sub)
        name = os.path.basename(live)
        print('##', g, name, '<-', src, flush=True)
        staged = {}
        extra = {'Halo 1': ('accel',), 'Halo 2': ('itemonly', 'accel'),
                 'Halo 3': ('accel',)}.get(g, ())
        for kind in ('vanilla', 'stable') + extra:
            dst = os.path.join(OUT, kind, sub.replace('/', os.sep), name)
            staged[kind] = dst
            if check_only or ('--stable-only' in sys.argv and kind != 'stable'):
                continue          # re-read only
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
            plan = plan_for(g, kind == 'itemonly') if kind in ('stable', 'itemonly') else []
            res, _ = hp.apply_run(dst, plan, reg, 'Normal', backup=False, game=g,
                                  from_baseline=False)
            mine = [r for r in res if r.get('effect') == 'Stable Grenades']
            print('  %-8s %d rows (%d card: %d applied, %d skipped, %d failed)  sig %s' % (
                kind, len(res), len(mine),
                sum(1 for r in mine if r.get('ok') and not r.get('skip')),
                sum(1 for r in mine if r.get('skip')),
                sum(1 for r in mine if not r.get('ok') and not r.get('skip')),
                hp.patch_signature(res)), flush=True)
            for r in res:
                if not r.get('ok') and not r.get('skip'):
                    print('     FAIL', r.get('effect'), r.get('tag'), r.get('reason'))
            if g == 'Halo 1':
                print('     swap:', '; '.join(h1_swap_grenades(dst)), flush=True)
            if kind == 'accel':
                print('     accel:', accelerate_placed(dst, g), flush=True)
            if g == 'Halo 2':
                print('     buffs:', '; '.join(h2_test_buffs(dst)), flush=True)
            if g == 'Halo 3':
                print('     buffs:', '; '.join(h3_test_buffs(dst)), flush=True)
        rows = {k: dict(flag_rows(v, g, reg)) for k, v in staged.items()}
        a = rows['vanilla']
        for k in sorted(set().union(*rows.values())):
            print('     %-80s %s%s' % (k, '  '.join('%s %-5s' % (kind, r.get(k))
                                                for kind, r in rows.items()),
                  '   <- card' if any(r.get(k) != a.get(k) for r in rows.values()) else ''))


if __name__ == '__main__':
    main('--check' in sys.argv, [a for a in sys.argv[1:] if not a.startswith('--')])
