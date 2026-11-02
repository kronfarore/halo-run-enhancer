import re, os, sys
K = r'F:\SteamLibrary\steamapps\common'
seen = set()
rx = re.compile(rb'[\x20-\x7e]{8,300}')
rxu = re.compile(rb'(?:[\x20-\x7e]\x00){8,300}')
KW = (b'weapon', b'firing', b'not resident', b'resident', b'animation graph')
for kit, exe in (('H3EK', 'sapien.exe'), ('H3EK', 'guerilla.exe')):
    d = open(os.path.join(K, kit, exe), 'rb').read()
    print('==', kit, exe, len(d), flush=True)
    for r_, conv in ((rx, lambda s: s), (rxu, lambda s: s.replace(b'\x00', b''))):
        for mo in r_.finditer(d):
            s = conv(mo.group())
            l = s.lower()
            if any(k in l for k in KW) and s not in seen:
                seen.add(s)
                print(s.decode('latin-1'), flush=True)
