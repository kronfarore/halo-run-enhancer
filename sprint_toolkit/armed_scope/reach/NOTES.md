# Reach Armed scoping: full notes (read-only, 2026-11-02)
Source: E:\HaloBaselines\haloreach\maps (10 missions, rebuilt caches; m10/m20 sizes = live map stamps), HREK ai\generic via ttk_common.flatten.
Scripts: rc_census.py (per map -> rc_<map>.json), rc_analyze.py -> rc_an.txt (units, residency, firing, graphs), rc_matrix.py -> rc_mx.txt
(species x weapon matrix: T own type, a class+any, x class without type/any, - no class but mode has class 'any', . nothing),
rc2.py -> rc2_m52.txt (variants, cell/spawn weapons), rc3.py -> rc3_m52.txt (bipd default weapons, Disallowed Trading, sort order, class block sizes),
rc4.py -> rc4_m10.txt, rc4_m50.txt (residency bits a fix needs, counted only; hlmt shield children).
Layouts found: weap class/name +0x3AC/+0x3B0 (ReachMCC; the Reach plugin's 0x3E0 is wrong); jmad Modes 0x104/0x30 > class 0xC/0x38 > type 0x8/0x14 > sets 0x8/0x48;
Parent graph +0 (none on any armable graph); Weapon List 0x140/8 (only elite_ai: pr>pistol, spr>pistol); Variants 0x3C/0x14 aliases +8.
Scenario: spawn weapon +0x34/+0x36, cell index +0x10, Actor Variant +0x44; cell weapon array 0x20/0x10 (index +0xC, Chance +0xE), secondary 0x2C (empty everywhere measured).
char Weapons Properties 0x1EC/0xC4, Firing Pattern 0x1F8/0x1C; Retreat Backup Weapon only grunt_ultra. bipd default: grunt/jackal/bugger plasma_pistol, elite_ai energy_sword, marine AR, brute none listed.
Shield: hlmt jackal Variants/Objects child weapons jackal_shield (minor), jackal_shield_major, skirmisher_bracers (2 variants). Graph aliases jackal_minor/major combat>shield, crouch>shield_crouch; murmillo combat>murm: all pistol-only.
Stock: char jackal only plasma_pistol/needler (m10, m50, m52); rifles only on skirmisher / jackal_sniper.
Sort: Modes, classes, types ascending by raw string id (checked on grunt, m52).
Slack: >=4 KB zero runs: 5-9 per map, largest 28-65 KB. _h3_reserve has the >=4 KB rule only for Halo 4; Reach takes any run.
Residency bits are NOT written anywhere; rc4 counts include every zone-set kind where the biped is resident.
Bogus: `timeout` with the WindowsApps python exits silently; a sibling session shares ..\ (hence this subfolder).
