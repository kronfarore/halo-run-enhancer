import re, sys, os
K = r'F:\SteamLibrary\steamapps\common'
PATS = [rb'weapon propert', rb'firing pattern', rb'weapons? block', rb'no firing', rb'firing propert',
        rb'weapon.{0,30}(animation|graph)', rb'(animation|graph).{0,30}weapon', rb'weapon class',
        rb'cannot (use|carry|fire|hold).{0,20}weapon', rb'initial.{0,12}weapon', rb'character.{0,40}weapon',
        rb'actor.{0,40}weapon', rb'squad.{0,40}weapon', rb'weapon.{0,40}(actor|character|squad)',
        rb'resident', rb'object_new', rb'not (loaded|resident)', rb'unit_add_weapon', rb'unit_can',
        rb'drop.{0,12}weapon', rb'no.{0,12}weapon']
seen = {}
for kit, exe in (('H3EK', 'sapien.exe'), ('H3EK', 'tool.exe'), ('H3EK', 'guerilla.exe'), ('H3ODSTEK', 'sapien.exe')):
    p = os.path.join(K, kit, exe)
    if not os.path.exists(p):
        print('missing', p); continue
    d = open(p, 'rb').read()
    strs = re.findall(rb'[\x20-\x7e]{6,}', d)
    u = re.findall(rb'(?:[\x20-\x7e]\x00){6,}', d)
    strs += [s.replace(b'\x00', b'') for s in u]
    print('==', kit, exe, len(d), len(strs))
    for s in strs:
        ls = s.lower()
        if len(s) > 400:
            continue
        if any(re.search(x, ls) for x in PATS):
            if s not in seen:
                seen[s] = 1
                print(s.decode('latin-1'))
