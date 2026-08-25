r"""Does this level actually FIELD the boss halo.json claims for it?

halo.json gives every mission a `boss`, and the patcher offers that boss's cards on
that mission. But a boss card only does anything if the level really spawns the
character -- and "the tag is in the map" is not that: a standalone Editing Kit build
pulls in tags that no squad ever uses, and a shipped map can carry a character purely
for a cinematic.

So this walks the evidence in order, and reports the WEAKEST link:

  1. is the `char` tag in the map's tag index at all?
  2. is it in the scenario's **Character Palette**? (a palette slot is what a squad
     indexes; a char outside the palette cannot be spawned by AI placement)
  3. does any **Squad** actually reference that palette slot? Squads reach characters
     through several nested blocks (the squad's own cells, and the designer/template
     rows), so every `Character Type Index` under `Squads` is collected, not just one.

Only 3 means the boss really turns up. 1 or 2 alone means the cards patch a character
the level never spawns -- they succeed at patch time and change nothing in play, which
is the failure mode that looks like a bug in the effect.

    python boss_census.py                       # every game, every mission
    python boss_census.py --game "Halo 3: ODST"
    python boss_census.py --boss "Brute Chieftain"
    python boss_census.py -v                    # name the squads that field it

Reads only. MCC may be running.
"""
import argparse
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import assembly_plugins
import halo_patch as HP                                          # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import map_vault as V                                            # noqa: E402

# Resolved rather than hardcoded: Assembly moved off the Steam drive and every
# CLI tool that had the old path baked in stopped finding it.
PLUGINS = assembly_plugins.plugins_dir()
SUBDIRS = {'Halo 1': ['Halo1MCC', 'Halo1'], 'Halo 2': ['Halo2MCC', 'Halo2'],
           'Halo 3': ['Halo3MCC', 'Halo3'], 'Halo 3: ODST': ['ODSTMCC', 'ODST']}
HALO_JSON = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'halo.json')


def _boss_tag(data, boss, game):
    """The `char` tag a boss's cards aim at, for this game. Cards may name several
    tags; the char one is what decides whether the character spawns."""
    group = data['Enemy modifiers']['Boss enemy modifier'].get(boss) or {}
    for eff in group.values():
        tag = eff.get('tag')
        if isinstance(tag, dict):
            tag = tag.get(game)
        if isinstance(tag, str) and tag.startswith('char '):
            return tag[5:]
    return None


_XML_BLOCKS = {}


def _block(plugin_path, name):
    """(offset, elementSize) of a top-level scnr tagblock, read from the plugin XML.

    NOT via `Plugin.find`: that only records fields whose type is in `TYPE_FMT`, and
    `tagRef` and `ascii` are not among them -- so the Character Palette (one tagRef)
    and the name columns of Squad Groups / Editor Folders are invisible to the normal
    lookup and `find` returns None. Asking the XML directly keeps the per-game offsets
    out of this file (Character Palette is 0x3A8 in Halo 3, 0x3E8 in ODST) without
    inventing field types the rest of the toolkit does not have.
    """
    import xml.etree.ElementTree as ET
    key = (plugin_path, name.lower())
    if key not in _XML_BLOCKS:
        found = None
        for node in ET.parse(plugin_path).getroot().iter():
            if (node.tag.lower() == 'tagblock'
                    and (node.get('name') or '').lower() == name.lower()):
                found = (int(node.get('offset'), 16), int(node.get('elementSize'), 16))
                break
        _XML_BLOCKS[key] = found
    return _XML_BLOCKS[key]


def _names(m, plug, scnr, block, name_off):
    """The Name column of a flat top-level block, as a list indexed by element."""
    blk = _block(plug.path, block)
    if not blk:
        return []
    off, es = blk
    n = max(0, m.i32(scnr + off))
    base = HP._block_base(m, scnr + off)
    return [m._cstr(base + i * es + name_off) or '' for i in range(n)] if base else []


def _palette(m, plug, scnr):
    """[(slot, tag name)] from the scenario's Character Palette."""
    blk = _block(plug.path, 'Character Palette')
    if not blk:
        return None
    off, es = blk
    fld = {'offset': 0}
    n = max(0, m.i32(scnr + off))
    base = HP._block_base(m, scnr + off)
    if not base:
        return []
    out = []
    for i in range(n):
        # tagRef datum index sits at +0xC of the ref; the ref is at the field offset
        rid = m.u32(base + i * es + fld['offset'] + 0xC)
        out.append((i, HP._tag_name_by_id(m, rid)))
    return out


def _squad_uses(m, plug, scnr, slots):
    """Squad names that reference any palette slot in `slots`.

    A squad reaches its character through more than one nested block -- its own cells
    carry `Character Type Index`, and so do the designer/template rows -- and which one
    a level uses varies. Every distinct block path under `Squads` that defines that
    field is walked, so a level is never reported empty because it happens to use the
    other one.
    """
    paths, seen = [], set()
    for f in plug.fields:
        if f['name'].lower() != 'character type index':
            continue
        chain = [b.lower() for b in f['block_chain']]
        if not chain or chain[0] != 'squads':
            continue
        key = tuple(f['block_offsets']) + (f['offset'],)
        if key not in seen:
            seen.add(key)
            paths.append(f)
    if not paths:
        return None

    sq = paths[0]['block_offsets'][0], paths[0]['block_sizes'][0]
    n = max(0, m.i32(scnr + sq[0]))
    base = HP._block_base(m, scnr + sq[0])
    if not base:
        return []
    gi = plug.find('Parent Squad Group Index', 'Squads')
    fi = plug.find('Editor Folder Index', 'Squads')
    hits = []
    for i in range(n):
        e = base + i * sq[1]
        name = m._cstr(e) or ('squad %d' % i)
        g = struct.unpack_from('<h', m.data, e + gi['offset'])[0] if gi else -1
        d = struct.unpack_from('<h', m.data, e + fi['offset'])[0] if fi else -1
        for f in paths:
            # Walk this field's block chain below the squad element.
            cur = [e]
            for depth in range(1, len(f['block_offsets'])):
                nxt = []
                for c in cur:
                    o = c + f['block_offsets'][depth]
                    cnt = max(0, m.i32(o))
                    b = HP._block_base(m, o)
                    if b:
                        nxt += [b + k * f['block_sizes'][depth] for k in range(cnt)]
                cur = nxt
                if not cur:
                    break
            for c in cur:
                idx = struct.unpack_from('<h', m.data, c + f['offset'])[0]
                if idx in slots:
                    hits.append((name, g, d))
                    break
            else:
                continue
            break
    return sorted(set(hits))


# A campaign scenario also carries its FIREFIGHT population, and in ODST that is most
# of it: Tayari Plaza's only Chieftain squads are `sq_sur_final_*`, which exist purely
# for Firefight waves and never spawn in the campaign. Counting those as "the level
# fields a Chieftain" is how a boss ends up offered on a mission where the player can
# never meet one. Classified by the squad's own SQUAD GROUP / EDITOR FOLDER first --
# the scenario's own filing -- and only by name prefix when the level files nothing.
SURVIVAL_WORDS = ('survival', 'firefight')
SURVIVAL_PREFIXES = ('sq_sur', 'sur_')


def _is_survival(name, group, folder):
    for label in (group, folder):
        if label and any(w in label.lower() for w in SURVIVAL_WORDS):
            return True
    return str(name).lower().startswith(SURVIVAL_PREFIXES)


def census(game, data, boss_filter=None, verbose=False):
    reg = HP.PluginRegistry(PLUGINS, SUBDIRS[game])
    plug = reg.get('scnr')
    if plug is None:
        print("  no scnr plugin for %s" % game)
        return
    for mid, mission in data['Missions'][game].items():
        boss = mission.get('boss')
        if not boss or str(boss).lower() == 'none':
            continue
        if boss_filter and boss != boss_filter:
            continue
        path = V.resolve(game, mid)
        if not path:
            print("  %-6s %-24s %-18s map not found" % (mid, mission.get('name'), boss))
            continue
        tag = _boss_tag(data, boss, game)
        if not tag:
            print("  %-6s %-24s %-18s no char tag in the boss's cards"
                  % (mid, mission.get('name'), boss))
            continue
        try:
            m = HP.open_map(path, game)
            scnr = HP._scnr_base(m)
            tags = m.find_tags('char', tag)
            pal = _palette(m, plug, scnr)
            slots = {i for i, nm in (pal or []) if nm and _matches(nm, tag)}
            squads = _squad_uses(m, plug, scnr, slots) if slots else []
            groups = _names(m, plug, scnr, 'Squad Groups', 0)
            folders = _names(m, plug, scnr, 'Editor Folders', 4)

            def _label(lst, idx):
                return lst[idx] if 0 <= idx < len(lst) else None
            camp = [s_ for s_ in squads
                    if not _is_survival(s_[0], _label(groups, s_[1]),
                                        _label(folders, s_[2]))]
            fire = [s_ for s_ in squads if s_ not in camp]
        except Exception as e:
            print("  %-6s %-24s %-18s ERROR %s" % (mid, mission.get('name'), boss, e))
            continue

        if camp:
            verdict = "SPAWNS \u2014 %d campaign squad(s)" % len(camp)
            if fire:
                verdict += " (+%d Firefight)" % len(fire)
        elif fire:
            verdict = ("FIREFIGHT ONLY \u2014 %d squad(s), none in the campaign"
                       % len(fire))
        elif slots:
            verdict = "in the palette but NO SQUAD uses it"
        elif tags:
            verdict = "tag present but NOT in the character palette"
        else:
            verdict = "NOT IN THE MAP AT ALL"
        print("  %-6s %-24s %-18s %s" % (mid, mission.get('name'), boss, verdict))
        if verbose and squads:
            for tag_, lst in (('campaign', camp), ('firefight', fire)):
                if lst:
                    print("           %-9s %s%s"
                          % (tag_, ", ".join(x[0] for x in lst[:10]),
                             " \u2026" if len(lst) > 10 else ""))


def _matches(name, pattern):
    """halo.json tag patterns may end in '*' (brute_chieftain* covers the hammer and
    armoured variants), so match that the same way the patcher does."""
    n, p = str(name).lower(), str(pattern).lower()
    return n.startswith(p[:-1]) if p.endswith('*') else n == p


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game', action='append', choices=sorted(SUBDIRS))
    ap.add_argument('--boss')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args(argv)
    with open(HALO_JSON, encoding='utf-8') as f:
        data = json.load(f)
    for game in (a.game or list(data['Missions'])):
        print("== %s" % game)
        census(game, data, a.boss, a.verbose)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
