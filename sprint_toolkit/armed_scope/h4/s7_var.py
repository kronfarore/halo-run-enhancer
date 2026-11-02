import sys
sys.path.insert(0, '..')
from lib import *
P = "F:/SteamLibrary/steamapps/common/HCEEK/Assembly-1-2023-11-29-1702446457/Plugins/Halo4MCC/hlmt.xml"
import re
x = open(P, encoding='utf8', errors='replace').read()
i = x.find('name="Variants"')
print(x[i - 20:i + 120])
print(re.findall(r'<tagblock name="Objects"[^>]*>', x), re.findall(r'<tagRef name="Child Object"[^>]*>', x, re.I), )
m = op('m10_crash')
hb = dict(m.find_tags('hlmt', '*storm_jackal'))
for n, b in hb.items():
    print(n)
    off = int(re.search(r'name="Variants" offset="(0x[0-9A-F]+)".*?elementSize="(0x[0-9A-F]+)"', x).group(1), 16)
    es = int(re.search(r'name="Variants" offset="(0x[0-9A-F]+)".*?elementSize="(0x[0-9A-F]+)"', x).group(2), 16)
    so = re.search(r'name="Objects" offset="(0x[0-9A-F]+)".*?elementSize="(0x[0-9A-F]+)"', x)
    oo, oe = int(so.group(1), 16), int(so.group(2), 16)
    co = int(re.search(r'name="Child Object" offset="(0x[0-9A-F]+)"', x, re.I).group(1), 16)
    for v in block(m, b + off, es):
        nm = m.resolve_stringid(m.u32(v)) if m.u32(v) else ''
        kids = [leaf(ref(m, e + co)) for e in block(m, v + oo, oe)]
        print('  ', nm, kids)
# carbine/rifle jackals shipped: designer cells and spawn points only
for mid in ('m10_crash', 'm80_delta', 'm40_invasion'):
    m = op(mid)
    scnr = hp._scnr_base(m)
    chars = palette(m, scnr, 0x444, 0x10, 0xC)
    weaps = palette(m, scnr, 0x1BC, 0x10, 0xC)
    c = collections.Counter()
    for sq in block(m, scnr + 0x3F0, 0x6C):
        for s_ in block(m, sq + 0x3C, 0x7C):
            ci, w = i16(m, s_ + 0x2E), i16(m, s_ + 0x30)
            cn = leaf(chars[ci]) if 0 <= ci < len(chars) else None
            if cn and ('jackal' in cn or 'grunt' in cn or 'elite' in cn) and w >= 0:
                c[(cn, leaf(weaps[w]))] += 1
        for cell in block(m, sq + 0x54, 0x64):
            cc = [leaf(chars[i16(m, q + 4)]) for q in block(m, cell + 0xC, 8) if 0 <= i16(m, q + 4) < len(chars)]
            for e in block(m, cell + 0x18, 8):
                wi = i16(m, e + 4)
                if cc and 0 <= wi < len(weaps):
                    c[('D:' + cc[0], leaf(weaps[wi]), hex(m.u32(e) & 0xFFFF), i16(m, e + 6))] += 1
    print(mid, sorted(c.items(), key=lambda kv: str(kv[0]))[:70])
