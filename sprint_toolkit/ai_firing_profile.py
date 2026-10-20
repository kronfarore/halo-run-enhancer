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

PARALLEL SESSIONS (2026-10-13): a write reads the file under the kit lock and changes ONLY
its own weapon's profile; every other profile that differs from HEAD (the other session's
uncommitted one) is printed FOREIGN and kept as read. `--commit MSG` (repeatable: one
paragraph each) commits just this profile inside the same lock hold (kit_commit.commit_json).
"""
import argparse
import json
import math
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
    return save(to_game, to_weapon, prof, commit=write if isinstance(write, list) else None)


def save(game, weapon, prof, commit=None):
    """Write ONE profile into the file as read now (under the kit lock: every caller runs in
    kit_lock.script) and print the FOREIGN profiles that differ from HEAD, kept as read.
    `commit`: message paragraphs -> commit this profile only (kit_commit.commit_json)."""
    sys.path.insert(0, HERE)
    import kit_commit
    try:
        with open(PROFILE_FILE, encoding='utf-8') as fh:
            data = json.load(fh)
    except FileNotFoundError:                    # never {} for an unreadable file: that rewrote all
        data = {}
    kit_commit.report_foreign('firing profile', kit_commit.head_json(PROFILE_FILE), data,
                              {(game, weapon): None})

    def apply(d):
        d.setdefault(game, {})[weapon] = prof
    apply(data)
    with open(PROFILE_FILE, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1)
    if commit:
        kit_commit.commit_json(PROFILE_FILE, apply, commit)
    return data[game][weapon]


def parse_sets(sets):
    """['0x1D8=0.7:Drop Weapon Loaded', ...] -> {offset: ['<f', value, name]} (floats); a
    value `h<int>` is a SHORT (an enum16: the Spartan Laser's 'Special-Fire Mode' 0x154 =
    h1, overcharge -- its AI held no charge without it, firing only the tap's tracer); `I<int>`
    a LONG (flags)."""
    out = {}
    for s in sets or ():
        off, rest = s.split('=', 1)
        val, name = (rest.split(':', 1) + [''])[:2]
        # `I<int>` is a LONG (the Gravity Hammer: actv flags 0x0 -- its sword-commander donor's
        # 'cannot use ranged weapons' rode along in the cloned block and kept the trigger unused)
        out['0x%X' % int(off, 16)] = (['<h', int(val[1:]), name] if val.startswith('h')
                                      else ['<I', int(val[1:], 0), name] if val.startswith('I')
                                      else ['<f', float(val), name])
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
    return save(to_game, to_weapon, prof, commit=write if isinstance(write, list) else None)


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
    Any mode may add 'balanced_set': ['0xOFF=V:NAME'] -- fields for the BALANCED box only.
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
    if fp.get('species_skill'):
        # THE SPECIES SKILL RULE (user, 2026-10-14; h1_enemy_weapons.species_skill_rule): the
        # skill fields scaled per slot by the slot's own stock variant over the donor
        prof['species_skill'] = True
    wdm_rule(prof, fp.get('wdm_rule'))
    if fp.get('balanced_set'):
        # explicit BALANCED fields (the Plasma Repeater, 2026-10-12: the drop battery by the
        # ratio rule; the default keeps the source's own), over the WDM rule's
        prof.setdefault('balanced_fields', {}).update(parse_sets(fp['balanced_set']))
    if write:
        save('Halo 1', weapon, prof, commit=write if isinstance(write, list) else None)
    print(prof['source'], '->', weapon)
    for off, (fmt, v, name) in sorted(prof['fields'].items(), key=lambda kv: int(kv[0], 16)):
        print('  %-6s %-32s %s' % (off, name, round(v, 4) if isinstance(v, float) else v))
    for off, (fmt, v, name) in sorted((prof.get('balanced_fields') or {}).items()):
        print('  %-6s %-32s %s  (BALANCED)' % (off, name, round(v, 4)))
    print('written' if write else '(dry: not written)', PROFILE_FILE)
    return prof


# --- HALO 2 DESTINATION (2026-10-20, H2_PORT_PLAN.md 0.5b) -------------------------------
# Halo 2 has a shared ai\generic like the sources, with the same field names and TWO patterns
# per weapon, so nothing is averaged or renamed: the source entry is copied name-for-name over a
# same-game donor's entry and WRITTEN INTO THE KIT TAG (h2_ai_firing.py) -- not a patch-time
# profile like Halo 1's actv slots. ai_firing_profiles.json['Halo 2'] keeps a record of the values
# (for the enhancer's Balanced switching), written under the Halo 1 lock like every record.

FMT_H2 = dict(FMT, flags32='<I', int32='<i')
SAME_ENUMS = ('Halo 3', 'Halo 3: ODST')     # enum tables = Halo 2's (Reach / Halo 4 grew them)


def source_entry(from_map, from_game, from_weapon, char='ai\\generic'):
    """The source's entry PER PATTERN: ({field: (type, value)}, [{field: (type, value)}, ...],
    where). Patterns from Firing Pattern Properties, else Halo 3's inner block."""
    reg = _plugins()
    pl = reg(from_game).get('char')
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

    def inner(e, ioff, iesz):
        n = m.i32(e + ioff)
        ib = hp._block_base(m, e + ioff) if n > 0 else None
        return [ib + k * iesz for k in range(max(0, n))]

    pe, pi = elem(*lay['props'])
    fe, fi = elem(*lay['pattern'][:3])
    if pe is None and fe is None:
        raise SystemExit('%s has no entry for %s' % (char, from_weapon))
    pats = (inner(fe, *lay['pattern'][3:]) if fe is not None
            else inner(pe, *lay['inner']) if (pe is not None and 'inner' in lay) else [])
    props, patterns = {}, [{} for _ in pats]
    for f in pl.fields:
        fmt = FMT_H2.get(f['type'])
        if not fmt:
            continue
        chain = f['block_chain']
        if chain == ['Weapons Properties'] and pe is not None:
            props[f['name']] = (f['type'], struct.unpack_from(fmt, m.data, pe + f['offset'])[0])
        elif chain and chain[-1] == 'Firing Patterns' and (
                (chain[0] == 'Firing Pattern Properties' and fe is not None) or
                (chain[0] == 'Weapons Properties' and fe is None)):
            for k, a in enumerate(pats):
                patterns[k][f['name']] = (f['type'], struct.unpack_from(fmt, m.data, a + f['offset'])[0])
    return props, patterns, '%s %s %s (weapons properties #%s, firing pattern #%s, %d patterns)' % (
        from_game, char, from_weapon, pi, fi, len(pats))


def _xml_key(name):
    """Assembly plugin field name -> (the name tool's XML export prints, component index)."""
    n, idx = name, 0
    if n.endswith(' Max'):
        n, idx = n[:-4], 1
    elif n[-2:] in (' i', ' j', ' k'):
        n, idx = n[:-2], ' i j k'.split(' ').index(n[-1:]) - 1
    n = n.lower().replace('maximum special target distance', 'max special target distance')
    return n, idx


def _parse_set(s):
    """'<plugin field name>[#pattern]=value' -> (name, pattern or None, value)."""
    k, v = s.rsplit('=', 1)
    pat = None
    if '#' in k:
        k, p = k.rsplit('#', 1)
        pat = int(p)
    return k.strip(), pat, float(v)


def h2_profile(key, write=True):
    """Halo 2 step 11 from ports_h2/<key>.py 'firing_profile':
      {'from_game', 'from_map', 'from_weapon'[, 'char'],   the source entry (copied by name)
       'donor_weapon': <stock Halo 2 weapon tag>,           the base (fields the source lacks)
       'set': ['<field>[#pattern]=value', ...]}             explicit values on top
    A same-game port (no source entry: the Sticky Detonator) gives only donor_weapon + set.
    Writes the entries into H2EK ai\\generic.character (H2 kit lock, export-checked) and the
    record ai_firing_profiles.json['Halo 2'][weapon]."""
    sys.path.insert(0, HERE)
    import h2_ai_firing as H
    import h2_port_residency as R
    import kit_lock
    import ports_h2
    p = ports_h2.load(key)
    fp = p.get('firing_profile') or {}
    weapon = R.weapon_path(p)
    donor = fp.get('donor_weapon')
    if not donor:
        raise SystemExit('%s: firing_profile has no donor_weapon (a stock Halo 2 weapon whose '
                         'ai\\generic entry is the base)' % key)
    tag = bytearray(open(H.GENERIC, 'rb').read())
    dpe, dfe, dpats = H.find(tag, donor)
    if dpe is None or dfe is None or len(dpats) != 2:
        raise SystemExit('donor %s: no complete entry in ai\\generic (props %s, patterns %d)'
                         % (donor, dpe is not None, len(dpats)))
    props_elem = bytearray(tag[dpe:dpe + H.PROPS_ES])
    pats = [bytearray(tag[a:a + H.PAT_ES]) for a in dpats]
    b = H.blocks(tag)
    melee = next(pth[1] for e, pth, _s, _t in b['props'][1] if e == dpe)
    if fp.get('from_map'):
        src = fp['from_map']
        sprops, spats, where = source_entry(src if os.path.isabs(src) else os.path.join(MCC, src),
                                            fp['from_game'], fp['from_weapon'],
                                            fp.get('char', 'ai\\generic'))
        source = '%s over Halo 2 %s' % (where, donor)
    else:
        sprops, spats, source = {}, [], 'Halo 2 %s (same game: no source entry%s)' % (
            donor, ', ' + fp['why'] if fp.get('why') else '')
    if len(spats) == 1:
        spats = spats * 2                         # one source pattern: both ends of the blend
    dst = _plugins()('Halo 2').get('char')
    written = {'props': {}, 'patterns': [{}, {}]}
    expect = {}
    skipped = []

    def put(buf, off, ftype, v, block, name, pat=None):
        fmt = FMT_H2[ftype]
        if fmt in ('<h', '<H', '<i', '<I'):
            v = int(round(v))
        struct.pack_into(fmt, buf, off, v)
        v = struct.unpack_from(fmt, buf, off)[0]
        (written['props'] if pat is None else written['patterns'][pat])[name] = v
        xn, idx = _xml_key(name)
        shown = math.degrees(v) if ftype == 'degree' else v
        expect.setdefault((block, xn + ('' if pat is None else '#%d' % pat)), {})[idx] = shown

    sets = [_parse_set(s) for s in fp.get('set') or ()]
    for f in dst.fields:
        ftype, name, chain = f['type'], f['name'], f['block_chain']
        if ftype not in FMT_H2:
            continue
        if chain == ['Weapons Properties']:
            src = sprops.get(name)
            if src and (ftype.startswith('flags') or ftype.startswith('enum')) \
                    and fp.get('from_game') not in SAME_ENUMS:
                skipped.append(name)
                src = None
            v = next((v for n, pt, v in sets if n == name and pt is None), None)
            if v is None and src is not None:
                v = src[1]
            if v is not None:
                put(props_elem, H.props_loose(f['offset']), ftype, v, 'weapons properties', name)
        elif chain == ['Firing Pattern Properties', 'Firing Patterns']:
            for k in range(2):
                src = spats[k].get(name) if spats else None
                v = next((v for n, pt, v in sets if n == name and pt in (None, k)), None)
                if v is None and src is not None:
                    v = src[1]
                if v is not None:
                    put(pats[k], f['offset'], ftype, v, 'firing pattern properties', name, k)
    # Halo 2-only ranges a Reach / Halo 4 source lacks (timid / aggressive combat range):
    # APPROXIMATED, not left at the donor's -- the donor's bounds scaled per end by how the
    # normal combat range moved (the SAW: SMG 3-7 -> storm_lmg 5-15)
    nf = {f['name']: f for f in dst.fields if f['block_chain'] == ['Weapons Properties']}
    donor_elem = tag[dpe:dpe + H.PROPS_ES]
    scaled = []
    for rng in ('Timid Combat Range', 'Aggressive Combat Range'):
        for end in ('', ' Max'):
            name, ref = rng + end, 'Normal Combat Range' + end
            if name in sprops or ref not in written['props'] or any(n == name for n, _p, _v in sets):
                continue
            old_ref = struct.unpack_from('<f', donor_elem, H.props_loose(nf[ref]['offset']))[0]
            old = struct.unpack_from('<f', donor_elem, H.props_loose(nf[name]['offset']))[0]
            if old_ref > 0:
                put(props_elem, H.props_loose(nf[name]['offset']), 'float32',
                    old * written['props'][ref] / old_ref, 'weapons properties', name)
                scaled.append(name)
    missing = sorted(n for n, pt, v in sets if not any(
        f['name'] == n for f in dst.fields if f['block_chain'] in
        (['Weapons Properties'], ['Firing Pattern Properties', 'Firing Patterns'])))
    if missing:
        raise SystemExit('%s: set rows name no Halo 2 field: %s' % (key, missing))
    only_donor = sorted(f['name'] for f in dst.fields if f['block_chain'] == ['Weapons Properties']
                        and f['type'] in FMT_H2 and f['name'] not in written['props']
                        and f['name'] not in skipped)

    def pred(want):
        def ok(text):
            first = text.splitlines()[0] if text else ''
            import re
            nums = [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?(?:e-?\d+)?', first)]
            return all(i < len(nums) and abs(nums[i] - w) <= max(1e-4, abs(w) * 1e-4)
                       for i, w in want.items())
        return ok
    checks = {k: pred(w) for k, w in expect.items()}
    prof = {'source': source, 'donor_weapon': donor, 'weapon': weapon,
            'props': written['props'], 'patterns': written['patterns'],
            'set': list(fp.get('set') or ()), 'donor_only': only_donor,
            'not_copied': skipped, 'scaled_by_normal_range': scaled}
    # THE HALO 2 ARMED WDM RULE (user, 2026-10-20): the default keeps the source game's own
    # Weapon Damage Modifier; BALANCED = that WDM x Halo 2's damage number of the balanced
    # difficulty baseline (halo_enhancer.BALANCED_BASELINE, the cross-game TTK calibration).
    # A source WDM of 0 ('unmodified') counts as 1.0. h2_enemy_weapons.balance writes the rows
    # into the map for a port whose Balanced box is on.
    import halo_enhancer as he
    dmg = he.BALANCED_BASELINE['Halo 2']['damage']
    prof['balanced_patterns'] = [
        {'Weapon Damage Modifier': (pt.get('Weapon Damage Modifier') or 1.0) * dmg}
        for pt in written['patterns']]
    prof['balanced_rule'] = 'WDM x %g (BALANCED_BASELINE Halo 2 damage)' % dmg
    for s in fp.get('balanced_set') or ():          # explicit BALANCED rows on top
        name, pat, v = _parse_set(s)
        for k in ((pat,) if pat is not None else range(len(prof['balanced_patterns']))):
            if any(f['name'] == name and f['block_chain'] == ['Weapons Properties'] for f in dst.fields):
                prof.setdefault('balanced_props', {})[name] = v
            else:
                prof['balanced_patterns'][k][name] = v
    print(source, '->', weapon)
    for n, v in written['props'].items():
        print('  %-36s %s' % (n, round(v, 4) if isinstance(v, float) else v))
    for n in written['patterns'][0]:
        a, c = written['patterns'][0][n], written['patterns'][1][n]
        print('  pattern %-28s %-10s %s' % (n, round(a, 4), round(c, 4)))
    print('  kept the donor\'s: %s' % (', '.join(only_donor + skipped) or 'nothing'))
    print('  BALANCED (%s): %s%s' % (prof['balanced_rule'], ' / '.join(
        ', '.join('%s %.4g' % kv for kv in row.items()) for row in prof['balanced_patterns']),
        ''.join('; %s %.4g' % kv for kv in (prof.get('balanced_props') or {}).items())))
    if scaled:
        print('  scaled by the normal combat range: %s' % ', '.join(scaled))
    if not write:
        print('(dry: nothing written)')
        return prof
    with kit_lock.held('ai_firing_profile --h2-port %s' % key, owner=key, kit='h2'):
        res = H.write_checked(weapon, bytes(props_elem), melee, [bytes(x) for x in pats],
                              {(blk, n): ok for (blk, n), ok in checks.items()})
    print('ai\\generic: %s; export-checked (%d rows of the port, %d other rows unchanged)'
          % ('entry replaced' if res['replaced'] else 'entry appended', res['rows'], res['others']))
    save('Halo 2', weapon, prof, commit=write if isinstance(write, list) else None)
    print('recorded', PROFILE_FILE, "['Halo 2']")
    return prof


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', help='a Halo 1 port config key (ports_h1/<key>.py): run its '
                                   'firing_profile section')
    ap.add_argument('--h2-port', help='a Halo 2 port config key (ports_h2/<key>.py): write its '
                                      'ai\\generic entries into H2EK (h2_ai_firing)')
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
    ap.add_argument('--commit', action='append', metavar='MSG',
                    help='commit this profile only, under the same lock hold (repeatable)')
    a = ap.parse_args()
    if a.commit and a.dry:
        ap.error('--commit with --dry')
    write = a.commit or True                     # a list = write + commit (save)
    if a.h2_port:
        h2_profile(a.h2_port, write=False if a.dry else write)
        return
    if a.port:
        from_config(a.port, write=False if a.dry else write)
        return
    if not a.to_weapon:
        ap.error('--to-weapon (or --port)')
    if a.donor_weapon:
        prof = same_game(a.donor_weapon, a.to_weapon, a.to_game, a.why, parse_sets(a.set),
                         write=write)
        for off, (fmt, v, name) in sorted(prof['fields'].items()):
            print('  %-6s %-24s %s' % (off, name, v))
        print(prof['source'], '->', a.to_weapon)
        print('written', PROFILE_FILE)
        return
    if not (a.from_map and a.from_weapon):
        ap.error('--from-map and --from-weapon (or --donor-weapon)')
    prof = build(a.from_map, a.from_game, a.from_weapon, a.to_weapon, a.to_game, a.char,
                 write=write)
    print(prof['source'])
    for off, (fmt, v, name) in sorted(prof['fields'].items(), key=lambda kv: int(kv[0], 16)):
        print('  %-6s %-32s %s' % (off, name, round(v, 4) if isinstance(v, float) else v))
    print('written', PROFILE_FILE)


if __name__ == '__main__':
    import kit_lock   # the shared-kit lock: two port sessions in parallel (H1_PORT_PLAN.md)
    with kit_lock.script('ai_firing_profile'):
        main()
