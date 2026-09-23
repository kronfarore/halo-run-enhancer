"""Suggested balance for a ported weapon, precomputed.

For every card target of the PORTED weapon (its own cards, source game), a DONOR weapon
that exists in two games gives two readings of the same halo.json target -- and the ratio
between them is a pure GAME-scale conversion, because it is the same weapon on either
side. balanced = ported_source * that ratio. Ratios cancel units, so the result lands in
the target game's own stored units. `original` is the ported value converted only where
the units differ (see unit_factor).

CHAINS. The donor has to exist in BOTH games of a hop, and often none does: Halo 2 has no
Assault Rifle, Halo 4 has no SMG. So the conversion walks through a bridge game that
shares a weapon with each side --

    Halo 4 --[Assault Rifle]--> Halo 3 --[SMG]--> Halo 2

-- and the ratios multiply. Every hop is the SAME weapon in two games, so none of the
weapons' own differences leak in; only the games' scales do.

    python balance_port.py SAW "Assault Rifle" "Halo 4" "Halo 1"     # one hop (legacy)
    python balance_port.py SAW "Halo 4" "Halo 2" --hop "Assault Rifle:Halo 4>Halo 3" --hop "SMG:Halo 3>Halo 2"
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import balance_compare as bc      # the map + plugin readers (sets up the tool paths)
import contextlib, io
import halo_enhancer as he
import halo_patch as hp

# (source game, target game, field) -> factor applied to ORIGINAL values. Halo 1 stores
# projectile velocity per tick (AR bullet 10.8 = 324 wu/s; every later game per second).
PER_TICK = ('Initial Velocity', 'Final Velocity', 'Minimum Velocity')

ZERO_AS_ONE = False        # set by --zero-as-one


def unit_factor(src, dst, field):
    if field in PER_TICK:
        if dst == 'Halo 1' and src != 'Halo 1':
            return 1 / 30.0
        if src == 'Halo 1' and dst != 'Halo 1':
            return 30.0
    return 1.0


def read_targets(weapon, game, db):
    """{card: [(target index, field, block, value), ...]} for one weapon in one game."""
    folder, mission = bc.MAPS[game]
    sub = he.CONFIG.get('map_game_folder', {}).get(game, folder)
    src = he.baseline_source(hp.default_map_path(he.mcc_root(), sub, mission), game)
    with contextlib.redirect_stdout(io.StringIO()):
        m = hp.open_map(src, game)
    reg = hp.PluginRegistry(he.CONFIG.get('assembly_plugins_dir'),
                            he.CONFIG.get('plugin_subdirs_by_game', {}).get(game, []))
    out = {}
    for name, c in db.data['Player Modifiers']['Specific Weapon Modifier'][weapon].items():
        if not isinstance(c, dict) or str(c.get('ignore', '')).lower() in ('yes', 'true'):
            continue
        games = c.get('game')
        if games and game not in (games if isinstance(games, list) else [games]):
            continue
        if game in (c.get('skip_games') or []):
            continue
        tag = bc.resolve(c.get('tag'), game)
        if not isinstance(tag, str) or ' ' not in tag:
            continue
        cls, path_ = hp.hm.split_tag(tag.split(' & ')[0])
        plugin = reg.get(cls)
        if plugin is None:
            continue
        for i, t in enumerate(bc.resolve(c.get('targets'), game) or []):
            if not isinstance(t, dict) or not he.target_applies(t, game):
                continue
            field, block = bc.resolve(t.get('field'), game), bc.resolve(t.get('block'), game)
            if not field:
                continue
            nth = bc.resolve(t.get('nth', 0), game) or 0
            try:
                v = m.read_first(cls, path_, field, plugin, block, t.get('index', 0) or 0,
                                 nth=nth)
            except Exception:
                v = None
            out.setdefault(name, []).append((i, field, block, v, cls, path_, nth,
                                             t.get('index', 0) or 0))
    return out


def _find(targets, field, index, shared):
    """The donor card entry matching a target: by FIELD NAME first, because a card may
    keep separate target lists per game, where list positions mean nothing; by position
    only when the card has one shared list, where the same entry simply resolves to a
    different name in each game."""
    for row in targets:
        if row[1] == field:
            return row
    if shared:
        for row in targets:
            if row[0] == index:
                return row
    return None


def parse_hop(text):
    """'SMG:Halo 3>Halo 2' -> ('SMG', 'SMG', 'Halo 3', 'Halo 2')"""
    weapon, _, games = text.partition(':')
    a, _, b = games.partition('>')
    if not weapon.strip() or not a.strip() or not b.strip():
        raise SystemExit('bad --hop %r, want "Weapon:Game A>Game B"' % text)
    return weapon.strip(), weapon.strip(), a.strip(), b.strip()


FAMILIES = os.path.join(HERE, 'port_families.json')


def family_hop(ported, src, dst, family=None, use_overrides=True):
    """(hops, per-field hops) between the weapons that play the same ROLE in each game.

    A port keeps its RATIO to its game's related weapon, so the SAW at 2.25x the Halo 4
    Assault Rifle's magazine becomes 2.25x whatever the target game's automatic rifle
    holds. That is the whole conversion, not a leg of one -- see the module docstring for
    why bridging through a third game is only safe with the same weapon on both sides.

    `field_overrides` names a different yardstick for particular fields, because a
    related weapon only transfers a number honestly while it holds the same POSITION in
    both games. The Assault Rifle does not for bullet speed: 1500 in Halo 4, the fastest
    automatic weapon there, against 80 in Halo 3, one of the slowest. The Machine Gun
    sits beside the SAW in both, so velocity is measured against that instead. A game
    with no weapon in the override family falls back to the base one.
    """
    cfg = json.load(open(FAMILIES, encoding='utf-8'))
    fam = family or (cfg.get('ports') or {}).get(ported)
    if not fam:
        raise SystemExit('no family for %r; name one with --family' % ported)
    table = (cfg.get('families') or {}).get(fam)
    if not table:
        raise SystemExit('unknown family %r' % fam)
    for g in (src, dst):
        if g not in table:
            raise SystemExit('family %r does not name a weapon for %s' % (fam, g))
    print('related weapons (%s): %s in %s -> %s in %s'
          % (fam, table[src], src, table[dst], dst))
    hops = [(table[src], table[dst], src, dst)]
    overrides = {}
    for field, other in ((cfg.get('field_overrides') or {}).get(fam) or {}).items():
        if not use_overrides:
            continue
        alt = (cfg.get('families') or {}).get(other) or {}
        # BOTH sides or neither: falling back on one side only would compare two
        # different weapons across the hop, which is the whole thing an override is
        # meant to avoid (Halo 1 has no Machine Gun, so it keeps the Assault Rifle).
        if src not in alt or dst not in alt:
            continue
        wa, wb = alt[src], alt[dst]
        if (wa, wb) == (table[src], table[dst]):
            continue
        overrides[field] = [(wa, wb, src, dst)]
        print('   %-18s measured against %s -> %s (%s)' % (field, wa, wb, other))
    print()
    return hops, overrides


def main(ported, src, dst, hops, overrides=None):
    he.load_settings()
    with contextlib.redirect_stdout(io.StringIO()):
        db = he.ModifierDatabase()
    sw = db.data['Player Modifiers']['Specific Weapon Modifier']
    cache = {}

    def targets_of(weapon, game):
        if (weapon, game) not in cache:
            cache[(weapon, game)] = read_targets(weapon, game, db)
        return cache[(weapon, game)]

    def is_shared(weapon, card):
        return not isinstance(sw.get(weapon, {}).get(card, {}).get('targets'), dict)

    for wa, wb, a, b in hops:
        for w in (wa, wb):
            if w not in sw:
                raise SystemExit('no cards for related weapon %r' % w)
    if hops[0][2] != src or hops[-1][3] != dst:
        raise SystemExit('the hops must run from %s to %s' % (src, dst))

    p_src = targets_of(ported, src)
    rows = []
    for card, targets in p_src.items():
        seen_dst = set()
        for entry in targets:
            i, field, block, pv = entry[0], entry[1], entry[2], entry[3]
            cur_i, cur_field, ratio = i, field, 1.0
            note, legs, hit = None, [], None
            # A field with its own yardstick is converted against that instead.
            for wa, wb, ga, gb in (overrides or {}).get(field, hops):
                A = targets_of(wa, ga).get(card) or []
                B = targets_of(wb, gb).get(card) or []
                ha = _find(A, cur_field, cur_i, is_shared(wa, card))
                if ha is None:
                    note = '%s has no %s target in %s' % (wa, cur_field, ga)
                    break
                ia, fa, _ba, va = ha[0], ha[1], ha[2], ha[3]
                hb = _find(B, fa, ia, is_shared(wb, card))
                if hb is None:
                    note = '%s card has no target in %s' % (wb, gb)
                    break
                ib, fb, vb = hb[0], hb[1], hb[3]
                legs.append(('%s>%s' % (wa, wb) if wa != wb else wa, ga, gb, fa, va, fb, vb))
                numeric = all(isinstance(x, (int, float)) and not isinstance(x, bool)
                              for x in (va, vb))
                # A donor reading 0 leaves no ratio. With --zero-as-one both sides are
                # nudged to 1 so the chain still produces a number -- which is only
                # meaningful where 0 is a PLACEHOLDER (halo.json's zero_is), not where
                # the weapon genuinely has none of that thing.
                if numeric and ZERO_AS_ONE:
                    va, vb = (va or 1), (vb or 1)
                if not numeric:
                    ratio = None
                elif not va:
                    ratio, note = None, '%s reads 0 in %s, nothing to scale from' % (wa, ga)
                elif ratio is not None:
                    ratio *= vb / float(va)
                cur_i, cur_field, hit = ib, fb, hb
            if hit is None:
                rows.append(dict(card=card, field=field, note=note or 'no donor target'))
                continue
            f_dst, b_dst, ddv, cls, path_ = hit[1], hit[2], hit[3], hit[4], hit[5]
            nth_dst, idx_dst = (hit[6] if len(hit) > 6 else 0), (hit[7] if len(hit) > 7 else 0)
            if (f_dst, b_dst) in seen_dst:
                continue        # several source targets, one field in the target game
            seen_dst.add((f_dst, b_dst))
            row = dict(card=card, field=field, dst_field=f_dst, dst_block=b_dst,
                       dst_class=cls, dst_tag=path_, dst_nth=nth_dst, dst_index=idx_dst,
                       ported_src=pv, donor_dst=ddv,
                       legs=[dict(donor=w, frm=g1, to=g2, field_from=f1, value_from=v1,
                                  field_to=f2, value_to=v2)
                             for w, g1, g2, f1, v1, f2, v2 in legs])
            if legs:
                row['donor_src'] = legs[0][4]
            if isinstance(pv, (int, float)) and not isinstance(pv, bool):
                row['original'] = pv * unit_factor(src, dst, field)
                row['ratio'] = ratio
                if ratio is not None:
                    row['balanced'] = pv * ratio
                elif isinstance(ddv, (int, float)) and not isinstance(ddv, bool) \
                        and not ddv:
                    # The TARGET's related weapon reads 0: that game does not use this
                    # field, so neither does the port. A weapon with no zoom lends no
                    # zoom; a game that leaves Fire Recovery at 0 gets 0, not the 1 a
                    # zero-as-one substitution would invent.
                    row['balanced'] = 0
                elif isinstance(ddv, (int, float)) and not isinstance(ddv, bool) \
                        and not row.get('donor_src'):
                    # A donor reading 0 in the source game gives no ratio, but it is not
                    # nothing: a field the source game leaves at 0 and the target game
                    # uses (Halo 1's Air Damage Range) is a CONVENTION, so the port
                    # adopts the target's value -- as long as the port sits at the same
                    # 0 the donor does. Otherwise the port keeps its own number.
                    row['balanced'] = ddv if pv == row.get('donor_src') else row['original']
                elif note:
                    row['note'] = note
            rows.append(row)
    fmt = lambda x: '-' if x is None else ('%.4g' % x if isinstance(x, float) else str(x))
    for r in rows:
        if 'dst_field' not in r:
            print('%-20s %-30s -- %s' % (r['card'][:20], r['field'][:30], r['note']))
            continue
        chain = '  '.join('%s %s>%s %s/%s' % (l['donor'].split()[0], l['frm'][-1], l['to'][-1],
                                              fmt(l['value_from']), fmt(l['value_to']))
                          for l in r.get('legs') or [])
        print('%-18s %-26s port %-7s | %-40s | orig %-7s bal %-7s %s' % (
            r['card'][:18], r['field'][:26], fmt(r['ported_src']), chain[:40],
            fmt(r.get('original')), fmt(r.get('balanced')),
            '' if r.get('ratio') is None else 'x%.4f' % r['ratio']))
    tag = '' if not any((overrides or {}).values()) else '_mgvel'
    out = os.path.join(HERE, 'balance_%s_%s_to_%s%s.json' % (
        ported.replace(' ', '_'), src.replace(' ', '').replace(':', ''),
        dst.replace(' ', '').replace(':', ''), tag))
    json.dump(dict(ported=ported, source=src, target=dst, donor=hops[-1][1],
                   hops=[list(h) for h in hops], rows=rows),
              open(out, 'w'), indent=1, default=str)
    print('wrote', out)


if __name__ == '__main__':
    globals()["ZERO_AS_ONE"] = "--zero-as-one" in sys.argv
    if "--zero-as-one" in sys.argv:
        ZERO_AS_ONE = True
        sys.argv.remove('--zero-as-one')
    hop_specs = [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == '--hop']
    args = []
    skip = False
    for a in sys.argv[1:]:
        if skip:
            skip = False
        elif a == '--hop':
            skip = True
        else:
            args.append(a)
    fam = None
    if '--family' in sys.argv:
        fam = sys.argv[sys.argv.index('--family') + 1]
        args = [a for a in args if a != fam]
    use_over = '--no-overrides' not in sys.argv
    args = [a for a in args if a != '--no-overrides']
    if hop_specs:                                   # ported, source, target + the hops
        main(args[0], args[1], args[2], [parse_hop(h) for h in hop_specs])
    elif fam or len(args) == 3:                     # ported, source, target + families
        hops, over = family_hop(args[0], args[1], args[2], fam, use_over)
        main(args[0], args[1], args[2], hops, over)
    else:                                           # legacy: ported, donor, source, target
        main(args[0], args[2], args[3], [(args[1], args[1], args[2], args[3])])
