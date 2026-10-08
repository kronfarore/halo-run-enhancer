r"""AI firing profiles for PORTED weapons (2026-10-02).

A Halo 1 actor variant's firing behaviour (actv 0x74-0x15F, 0x1D8-0x1E3) is copied
from the most similar character that already carries the weapon (h1_enemy_weapons).
A PORTED weapon has no such character in Halo 1, so its values come from the game it
was ported FROM: there the shared AI base ai\generic usually lists every weapon's
firing data (Halo 4: Weapons Properties +0x204/0xCC, Weapon ref +0x4; Firing Pattern
Properties +0x210/0x1C, Weapon ref +0x0, Firing Patterns +0x10/0x40 -- two patterns,
the start and the end of a burst series, AVERAGED here because Halo 1 has one).

Fields are matched by NAME between the source char plugin and the Halo 1 actv plugin
(23 of them line up), plus two renames (Maximum Firing Range -> Maximum Firing
Distance, Normal Combat Range -> Desired Combat Range). Raw values are copied: both
engines store floats and radians alike. Halo 1-only fields (new-target / moving /
berserk modifiers, damage per second) and every field the source leaves at 0 are left to
the base donor h1_enemy_weapons picks by animation label.

Output: ai_firing_profiles.json (tool dir): {game: {weapon path: {'source': ...,
'fields': {hex offset: [struct fmt, value]}}}}.

    python ai_firing_profile.py --from-map ..\..\halo4\maps\m020.map --from-game "Halo 4" ^
        --from-weapon "objects\weapons\rifle\storm_lmg\storm_lmg" --to-weapon "weapons\saw\saw"

SAME-GAME mode (no source map): fire like the characters carrying another weapon, with
optional explicit fields over the donor -- Halo 1's Sentinel Beam:

    python ai_firing_profile.py --to-weapon "weapons\sentinel beam\sentinel beam" ^
        --donor-weapon "characters\sentinel\sentinel" ^
        --set "0x1D8=0.7:Drop Weapon Loaded" --set "0x1DC=0.9:Drop Weapon Loaded Max"

FROM A PORT'S CONFIG (H1_PORT_PLAN.md phase 0): the step-11 command lives in the weapon's
ports_h1/<key>.py 'firing_profile' section, and this runs it. Source layouts known: Halo 4,
Halo 3 (+ ODST), Halo Reach.

    python ai_firing_profile.py --port sentinel_beam [--dry]
    python ai_firing_profile.py --port smg --dry
"""
import argparse
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import halo_patch as hp  # noqa: E402

PROFILE_FILE = os.path.join(ROOT, 'ai_firing_profiles.json')
FMT = {'float32': '<f', 'degree': '<f', 'int16': '<h', 'enum16': '<H'}
RENAMES = {'Maximum Firing Range': 'Maximum Firing Distance',
           'Normal Combat Range': 'Desired Combat Range',
           'Normal Combat Range Max': 'Desired Combat Range Max'}
# source layouts: (props block, elem, weapon ref) and (patterns block, elem, weapon ref,
# inner Firing Patterns block, elem)
# Halo 3 / Reach read off the Assembly plugins (Halo3MCC / Reach char.xml, 2026-10-07):
# Halo 3's Weapons Properties ALSO carry their own Firing Patterns (+0xC4, 0x40) -- read when
# the Firing Pattern Properties block has no entry for the weapon ('inner').
SOURCES = {'Halo 4': {'props': (0x204, 0xCC, 0x4), 'pattern': (0x210, 0x1C, 0x0, 0x10, 0x40)},
           'Halo 3': {'props': (0x174, 0xE0, 0x4), 'pattern': (0x180, 0x1C, 0x0, 0x10, 0x40),
                      'inner': (0xC4, 0x40)},
           'Halo Reach': {'props': (0x1EC, 0xC4, 0x4), 'pattern': (0x1F8, 0x1C, 0x0, 0x10, 0x40)}}
SOURCES['Halo 3: ODST'] = SOURCES['Halo 3']
MCC = os.path.dirname(ROOT)


def _plugins():
    import halo_enhancer as he
    c = he.CONFIG
    reg = lambda g: hp.PluginRegistry(c.get('assembly_plugins_dir'), c.get('plugin_subdirs_by_game', {}).get(g))
    return reg


def build(from_map, from_game, from_weapon, to_weapon, to_game='Halo 1', char='ai\\generic',
          write=True):
    reg = _plugins()
    src_pl, dst_pl = reg(from_game).get('char'), reg(to_game).get('actv')
    lay = SOURCES[from_game]
    m = hp.open_map(from_map, from_game)
    base = dict(m.find_tags('char', char)).get(char)
    if base is None:
        raise SystemExit('no %s in %s' % (char, from_map))

    def elem(off, esz, ref):
        n = m.i32(base + off)
        b = hp._block_base(m, base + off) if n > 0 else None
        for i in range(max(0, n)):
            if hp._tag_name_by_id(m, m.u32(b + i * esz + ref + 0xC)) == from_weapon:
                return b + i * esz, i
        return None, None

    pe, pi = elem(*lay['props'])
    fe, fi = elem(*lay['pattern'][:3])
    if pe is None and fe is None:
        raise SystemExit('%s has no entry for %s' % (char, from_weapon))
    values = {}                                      # source field name -> value
    for f in src_pl.fields:
        fmt = FMT.get(f['type'])
        if not fmt:
            continue
        chain = f['block_chain']
        if chain == ['Weapons Properties'] and pe is not None:
            values[f['name']] = struct.unpack_from(fmt, m.data, pe + f['offset'])[0]
        elif chain == ['Firing Pattern Properties', 'Firing Patterns'] and fe is not None:
            ioff, iesz = lay['pattern'][3:]
            n = m.i32(fe + ioff)
            ib = hp._block_base(m, fe + ioff) if n > 0 else None
            vals = [struct.unpack_from(fmt, m.data, ib + k * iesz + f['offset'])[0] for k in range(max(0, n))]
            if vals:
                values[f['name']] = sum(vals) / len(vals)
        elif (chain == ['Weapons Properties', 'Firing Patterns'] and fe is None
              and pe is not None and 'inner' in lay):
            ioff, iesz = lay['inner']
            n = m.i32(pe + ioff)
            ib = hp._block_base(m, pe + ioff) if n > 0 else None
            vals = [struct.unpack_from(fmt, m.data, ib + k * iesz + f['offset'])[0] for k in range(max(0, n))]
            if vals:
                values[f['name']] = sum(vals) / len(vals)
    fields = {}
    for f in dst_pl.fields:
        if f['block_chain'] or not (0x74 <= f['offset'] < 0x160 or 0x1D8 <= f['offset'] < 0x1E4):
            continue
        src = next((s for s, d in RENAMES.items() if d == f['name']), f['name'])
        if src in values and f['type'] in FMT:
            v = values[src]
            # Halo 4 writes 0 for 'not set -- use the weapon's own value' (its SAW's Rate
            # Of Fire is 0); in Halo 1 a 0 rate never fires. The base donor keeps those.
            if not v:
                continue
            if FMT[f['type']] in ('<h', '<H'):
                v = int(round(v))
            fields['0x%X' % f['offset']] = [FMT[f['type']], v, f['name']]
    prof = {'source': '%s %s %s (weapon properties #%s, firing pattern #%s)' % (
                from_game, char, from_weapon, pi, fi),
            'fields': fields}
    if not write:
        return prof
    try:
        with open(PROFILE_FILE, encoding='utf-8') as fh:
            data = json.load(fh)
    except Exception:
        data = {}
    data.setdefault(to_game, {})[to_weapon] = prof
    with open(PROFILE_FILE, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1)
    return data[to_game][to_weapon]


def parse_sets(sets):
    """['0x1D8=0.7:Drop Weapon Loaded', ...] -> {offset: ['<f', value, name]} (floats)."""
    out = {}
    for s in sets or ():
        off, rest = s.split('=', 1)
        val, name = (rest.split(':', 1) + [''])[:2]
        out['0x%X' % int(off, 16)] = ['<f', float(val), name]
    return out


def same_game(donor_weapon, to_weapon, to_game='Halo 1', why='', fields=None, write=True):
    """A profile with NO foreign fields: the clone takes its whole firing block from the
    best character in the target game carrying `donor_weapon` (h1_enemy_weapons.donor_for
    reads 'donor_weapon'). For a weapon whose animation label nobody else uses, so the
    label search finds no base: Halo 1's Sentinel Beam ('sb') fires like Halo 1's own
    Sentinel, whose beam (characters\\sentinel\\sentinel) it replaces."""
    prof = {'source': '%s %s (own carriers%s)' % (to_game, donor_weapon, ', ' + why if why else ''),
            'donor_weapon': donor_weapon, 'fields': dict(fields or {})}
    if not write:
        return prof
    try:
        with open(PROFILE_FILE, encoding='utf-8') as fh:
            data = json.load(fh)
    except Exception:
        data = {}
    data.setdefault(to_game, {})[to_weapon] = prof
    with open(PROFILE_FILE, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1)
    return data[to_game][to_weapon]


WDM = '0xC4'                     # Halo 1 actor_variant Weapon Damage Modifier


def wdm_rule(prof, rule):
    """THE ARMED WEAPON DAMAGE MODIFIER RULE (user, 2026-10-08, the Covenant Carbine):
    WDM = base x (yardstick player dps / port player dps), once for the DEFAULT numbers
    (`fields`) and once for the BALANCED rows (`balanced_fields`; h1_enemy_weapons uses
    them for a port listed in its spec's 'balanced'). base = the Weapon Damage Modifier of
    the carriers the port fires from (the AR donors: 0.4); the dps values are
    h1_role_compare's (step 5b on the built port). A stronger port gets a gentler AI.
    Checked in game on the Carbine (a30, all Elite minors, stopwatch time to die x5):
    stock plasma rifle 3.61 s, Armed carbine (balanced, WDM 0.40) 2.04 s -> measured
    0.40 x 2.04/3.61 = 0.23 against the rule's 0.26. Source profiles carry no WDM of their
    own from Halo 3 (Halo 4 does: the SAW's 0.75) -- a rule value replaces it."""
    if not rule:
        return
    base, yard = rule['base'], rule['yardstick_dps']
    prof['fields'][WDM] = ['<f', base * yard / rule['port_dps'], 'Weapon Damage Modifier']
    if rule.get('balanced_port_dps'):
        prof['balanced_fields'] = {WDM: ['<f', base * yard / rule['balanced_port_dps'],
                                         'Weapon Damage Modifier']}
    prof['wdm_rule'] = dict(rule)


def from_config(key, write=True):
    """Step 11 from a Halo 1 port's config (ports_h1/<key>.py, section 'firing_profile'):
      {'mode': 'carried'}                      a character spawns with it: nothing to write
      {'mode': 'same_game', 'donor_weapon': <H1 weapon>, 'why': .., 'set': ['0xOFF=V:NAME']}
      {'mode': 'source', 'from_game': 'Halo 3', 'from_map': <path under the MCC folder>,
       'from_weapon': <source weapon tag>[, 'char': 'ai\\generic']}
    The port's weapon tag comes from its 'pickable' section (else reservations weapon_dir)."""
    sys.path.insert(0, HERE)
    import ports_h1
    p = ports_h1.load(key)
    fp = p.get('firing_profile') or {}
    weapon = (p.get('pickable') or {}).get('weapon')
    if not weapon:
        d = p['reservations']['weapon_dir']
        weapon = d + '\\' + d.rsplit('\\', 1)[-1]
    mode = fp.get('mode')
    if mode == 'carried' or not mode:
        print('%s: %s -- nothing to write (carried in game: best_donor finds the carriers)'
              % (key, mode or 'no firing_profile'))
        return None
    if mode == 'same_game':
        if not fp.get('donor_weapon'):
            raise SystemExit('%s: same_game profile without a donor_weapon -- %s'
                             % (key, fp.get('why', 'choose the Halo 1 weapon it fires like')))
        prof = same_game(fp['donor_weapon'], weapon, why=fp.get('why', ''),
                         fields=parse_sets(fp.get('set')), write=False)   # written below
    elif mode == 'source':
        src = fp['from_map']
        prof = build(src if os.path.isabs(src) else os.path.join(MCC, src), fp['from_game'],
                     fp['from_weapon'], weapon, char=fp.get('char', 'ai\\generic'), write=False)
        prof['fields'].update(parse_sets(fp.get('set')))      # explicit fields over the source
        if fp.get('donor_weapon'):
            # the BASE the source fields are laid over. Without it donor_for looks for a
            # carrier of the port's own animation LABEL -- the SAW is 'ar', but a port with
            # a label of its own (the SMG's 'sm') finds none and gets no Armed card. With
            # it donor_for takes the best carrier of donor_weapon (its same-game branch)
            prof['donor_weapon'] = fp['donor_weapon']
            prof['source'] += ' over %s carriers' % fp['donor_weapon']
    else:
        raise SystemExit('%s: unknown firing_profile mode %r' % (key, mode))
    if fp.get('donor_variant'):
        # ONE carrier for every slot (the Beam Rifle, user 2026-10-08: the Flood combat Elite
        # sniper for Grunts and Jackals too -- best_donor's similarity ranking gave them the
        # armoured Marine). h1_enemy_weapons.donor_for reads it before any saved choice
        prof['donor_variant'] = fp['donor_variant']
        prof['source'] += ' (always %s)' % fp['donor_variant']
    wdm_rule(prof, fp.get('wdm_rule'))
    if write:
        try:
            with open(PROFILE_FILE, encoding='utf-8') as fh:
                data = json.load(fh)
        except Exception:
            data = {}
        data.setdefault('Halo 1', {})[weapon] = prof
        with open(PROFILE_FILE, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, indent=1)
    print(prof['source'], '->', weapon)
    for off, (fmt, v, name) in sorted(prof['fields'].items(), key=lambda kv: int(kv[0], 16)):
        print('  %-6s %-32s %s' % (off, name, round(v, 4) if isinstance(v, float) else v))
    for off, (fmt, v, name) in sorted((prof.get('balanced_fields') or {}).items()):
        print('  %-6s %-32s %s  (BALANCED)' % (off, name, round(v, 4)))
    print('written' if write else '(dry: not written)', PROFILE_FILE)
    return prof


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', help='a Halo 1 port config key (ports_h1/<key>.py): run its '
                                   'firing_profile section')
    ap.add_argument('--dry', action='store_true', help='with --port: print, write nothing')
    ap.add_argument('--from-map')
    ap.add_argument('--from-game', default='Halo 4')
    ap.add_argument('--from-weapon')
    ap.add_argument('--to-weapon')
    ap.add_argument('--to-game', default='Halo 1')
    ap.add_argument('--char', default='ai\\generic')
    ap.add_argument('--donor-weapon', help='same-game mode: fire like the characters '
                                           'carrying this weapon (no foreign fields)')
    ap.add_argument('--why', default='')
    # explicit float fields written over the donor's bytes. The Sentinel Beam: its donor
    # (the Sentinel) never drops a weapon (Drop Weapon Loaded 0 / 0), so a Grunt or Elite
    # armed with it might drop an empty battery -- the plasma-rifle Elite's 0.7 / 0.9
    # (actv +0x1D8 / +0x1DC, read off the tag) make it drop charged, whatever 0 means
    ap.add_argument('--set', action='append', metavar='0xOFF=VALUE:NAME')
    a = ap.parse_args()
    if a.port:
        from_config(a.port, write=not a.dry)
        return
    if not a.to_weapon:
        ap.error('--to-weapon (or --port)')
    if a.donor_weapon:
        prof = same_game(a.donor_weapon, a.to_weapon, a.to_game, a.why, parse_sets(a.set))
        for off, (fmt, v, name) in sorted(prof['fields'].items()):
            print('  %-6s %-24s %s' % (off, name, v))
        print(prof['source'], '->', a.to_weapon)
        print('written', PROFILE_FILE)
        return
    if not (a.from_map and a.from_weapon):
        ap.error('--from-map and --from-weapon (or --donor-weapon)')
    prof = build(a.from_map, a.from_game, a.from_weapon, a.to_weapon, a.to_game, a.char)
    print(prof['source'])
    for off, (fmt, v, name) in sorted(prof['fields'].items(), key=lambda kv: int(kv[0], 16)):
        print('  %-6s %-32s %s' % (off, name, round(v, 4) if isinstance(v, float) else v))
    print('written', PROFILE_FILE)


if __name__ == '__main__':
    main()
