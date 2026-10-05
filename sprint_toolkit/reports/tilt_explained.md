# What the Enhancer's "Tilt" skull does, per game

> **Rule change 2026-10-05 (user):** a neutral **1.0 is now halved to 0.5** as well. Every "1 -> 1 (no change)" row below now reads 1 -> 0.5 -- e.g. bullets against Elite and player shields from Halo 3 on do half. A matchup with NO row in the Halo 2+ table stays 1 (the engine's default), and only element [0] of the H3+ table is written.

**The rule** (`_apply_tilt`, halo_patch.py): every damage multiplier moves further away from 1.
A value above 1 doubles, a value between 0 and 1 halves, and 0 and 1 stay as they are.
So a weakness gets twice as strong, a resistance gets twice as strong, an immunity stays an immunity,
and a neutral matchup stays neutral.

**What most players won't expect:** a matchup sitting at exactly **1.0** does not change. In Halo 3, ODST, Reach
and Halo 4 that covers most "bread and butter" hits: bullets against an Elite's or the player's shield,
the sniper against flesh, and most weapons against Grunt and Jackal flesh. In those games Tilt mostly
affects plasma against shields, explosives, armour, vehicles, Flood and Hunters. Halo 1 sets these numbers
weapon by weapon, so far more of them are not 1 there.

All values below were read from the baseline maps (E:\HaloBaselines). The names for Halo 3 and later come from
the map's own string table (see "Method" at the end). "→" means vanilla → with Tilt.

---

## How the engine uses the numbers

**Halo 1.** Each damage effect (`jpt!`) holds its own list of 33 multipliers, one per material
(jpt! 0x200-0x280, from Dirt to Hunter Shield). When a hit lands, the engine looks up the material of the
part that was hit. Bodies use the collision model's material. Shields use the `coll` "Shield Material Type", which is one of the
"... Energy Shield" entries: Elite Energy Shield, Cyborg Energy Shield, Jackal Energy Shield and so on. The hit's damage is multiplied by the
damage effect's value for that material. The player is **Cyborg** (body) and **Cyborg Energy Shield**
(shield). Tilt edits every jpt! in the map, which includes AI weapons and ported weapons.

**Halo 2 and later.** There is one global table: matg → Damage Table → Damage Groups → Armor Modifiers → Damage
Multiplier.
- A damage effect names a **damage group** through its *General Damage* string id, plus an optional
  *Specific Damage* id. Examples: `bullet_slow`, `plasma_slow`, `explosion_small`; a sniper hit is `bullet_fast` + `sniper`.
- The thing that was hit gives an **armour** name. Its model material (body, or the shield's global material) names a
  global material in matg → Materials. That material carries a *General Armor* and an optional *Specific Armor*,
  both inherited up its parent chain. For example, `energy_shield_thin_cov_elite` has general armour
  `energy_shield_thin`, and in H3/ODST also the specific armour `energy_shield_thin_player`.
- multiplier = Damage Groups[group].Armor Modifiers[armour]. If no row exists, the multiplier is 1.
- In Halo 3 and later, **the player and the Elites use the same armour rows**. Shields are `energy_shield_thin`
  (masterchief / spartan / elite shield materials). Bodies are `hard_metal_thin` (masterchief / spartan
  armour, Elite armour, and Elite flesh). Halo 2 is the same: Chief and Elite shields → `energy_shield_thin`,
  Chief armour and Elite flesh → `hard_metal_thin`. **Any change Tilt makes to Elites, it also makes to the player.**
- Open question: how general and specific rows combine. `port_ttk.py` takes the most specific row that exists
  and stops there. The native Tilt tables in Halo 3 suggest the engine **multiplies** them instead. There,
  `plasma_slow × hard_metal_thin = 0.11667` and `× hard_metal_thin_player = 3`, and 0.11667 × 3 = 0.35, which
  is exactly the normal value. `bullet_slow × energy_shield_thin = 0.25` and `× energy_shield_thin_player = 4`
  give 0.25 × 4 = 1, also the normal value. This only matters for the `_player`, `sniper`, `anti_flood`, `hunter`
  and `scarab` specific rows. Under either reading, Tilt keeps a <1 / >1 pair at the same product.

## Which table is campaign (H3, ODST, Reach, H4): answered offline

Both elements apply in every game mode. **Element [0] is the normal table, and element [1] is the game's own native
Tilt skull table**, which the engine uses only while MCC's Tilt skull is on. The evidence:
- The H4EK export names the elements: `[0] "default"` and `[1] "tilt skull active"`. Halo 4's tool.exe holds the same strings.
- In every kit (H3EK, H3ODSTEK, HREK, H4EK), tool.exe's `import_damage_table.cpp` imports
  `data\globals\armor_vs_damage.csv` and `data\globals\armor_vs_damage_tilted.csv`. Both CSVs ship in
  each kit's `data\globals`.

So campaign without the native skull uses **[0]**. The Enhancer writes both elements. Turning on MCC's own
Tilt skull as well stacks the two: you get the native tilted table, tilted again by the Enhancer.
The native Tilt is **not** "everything ×2". In Reach and H4 it *lowers* plasma against shields (1.6 → 1.25) and
needles against shields (2 → 1), and it makes bullets weaker against shields (1 → 0.25). Halo 2 has a single
table. Halo 1's native MCC Tilt is code-side and does not touch these tags.

---

## Halo 1 (values per damage effect; c10/b30/d20)

| Weapon (jpt!) | Target material | Vanilla → Tilt |
|---|---|---|
| Plasma rifle bolt | Elite Energy Shield | 2 → **4** |
| Plasma rifle / Ghost / Banshee bolt | **player shield** (Cyborg Energy Shield) | 2 → **4** |
| Plasma rifle / Ghost / Banshee bolt | **player body** (Cyborg) | 0.5 → 0.25 |
| Plasma pistol bolt | Elite Energy Shield | 2 → 4 |
| Plasma pistol bolt | player shield / body | 0.6 → 0.3 |
| Plasma bolts (all) | Sentinel | 2 → 4 |
| Plasma bolts (all) | Hunter armour / skin | 0.5 → 0.25 |
| Assault rifle bullet | Elite Energy Shield | 0.7 → **0.35** |
| Assault rifle bullet | Flood combat / carrier | 0.65 → 0.325 |
| Assault rifle bullet | Engineer | 0.6 → 0.3 |
| Pistol bullet | Elite Energy Shield | 0.8 → 0.4 |
| Pistol bullet | Flood combat / carrier | 1.5 → 3 |
| Pistol bullet | Engineer | 2 → 4 |
| Pistol bullet | Hunter armour, Sentinel | 0.2 → 0.1 |
| Shotgun pellet | Flood combat / carrier | 1.5 / 1.75 → **3 / 3.5** |
| Shotgun pellet | Hunter armour | 0.2 → 0.1 |
| Sniper bullet | Elite Energy Shield | 2 → **4** |
| Sniper bullet | Flood | 0.05 → 0.025 |
| Sniper bullet | Hunter armour / skin | 0.5 → 0.25 |
| Needler supercombine explosion | Elite Energy Shield, Sentinel | 4 → **8** |
| Needle (impact) | Flood | 1.2 → 2.4 |
| Plasma grenade explosion | Elite Energy Shield, Sentinel | 4 → **8** |
| Plasma grenade explosion | Jackal Energy Shield | 1.5 → 3 |
| Frag / plasma grenade, rocket, fuel rod | Flood combat / carrier | 2 / 4 → **4 / 8** |
| Frag / plasma grenade | Hunter armour | 0.25 → 0.125 |
| Flamethrower burn | Elite / Jackal Energy Shield | 0.2 / 0.1 → 0.1 / 0.05 |
| Flamethrower burn | Hunter armour, Sentinel | 0.5 → 0.25 |
| Shade turret bolt ("c gun turret") | **player shield and body** | 1.5 → **3** |
| Shade turret bolt | Elite Energy Shield | 3 → 6 |
| Shade turret bolt | Grunt / Elite / Jackal flesh | 0.7 → 0.35 |
| Player melee (every weapon) | Flood / Sentinel | 0.2 → 0.1 |
| Player melee (every weapon) | Cyborg (co-op partner) | 1.4 → 2.8 |
| Energy sword melee | Sentinel | 2 → 4 |
| Bullets (AR, warthog), plasma bolts | vehicles (Metal hollow/thin/thick) | 0.25 → 0.125 |
| Most weapons | Jackal shield (bullets), Hunter Shield, Monitor, Engineer force field | 0 → 0 (still immune) |

**What the player notices in Halo 1:** plasma becomes the Elite killer, needing half the bolts to strip a shield.
The AR is now poor against Elite shields and the Flood. The shotgun and pistol shred the Flood, and every
explosive deletes Flood carriers. Hunters and vehicles are twice as tough against guns.
**Damage to you:** enemy plasma rifles, Ghosts and Banshees strip your shield twice as fast but hurt your
health half as much. Elite plasma pistols do half damage. Shade turrets do double damage to both.

---

## Halo 2 (one table; 03a/05b)

| Damage group (weapons) | Armour (who) | Vanilla → Tilt |
|---|---|---|
| plasma_slow (plasma rifle, plasma pistol, needler) | energy_shield_thin (**Elite + player shields**) | 1.5 → **3** |
| plasma_slow | hard_metal_thin (**Elite + player bodies**) | 0.35 → 0.175 |
| plasma_slow | tough_organic (Brutes) | 0.5 → 0.25 |
| plasma_slow | sentinel / sentinel_enforcer | 4 / 2 → 8 / 4 |
| plasma_slow | soft_organic_flesh_hunter (Hunter flesh) | 2 → 4 |
| plasma_slow | hard_metal_thick (Hunter armour, Ghost, Wraith hull) | 0.1 → 0.05 |
| bullet_slow (SMG, magnum, shotgun) | energy_shield_thin | 1 → 1 (no change) |
| bullet_slow | tough_organic (Brutes) | 0.5 → 0.25 |
| bullet_slow | tough_floodflesh (combat forms) | 1.25 → 2.5 |
| bullet_slow / bullet_fast | Hunter flesh | 2 → 4 |
| bullet_slow | brittle_mech (engines) | 1.5 → 3 |
| bullet_fast (BR, sniper, Brute Shot impact) | tough_floodflesh | 0.5 → 0.25 |
| bullet_fast | hard_metal_thick | 0.5 → 0.25 |
| sniper (sniper + beam rifle, specific) | energy_shield_thin | 2 → **4** |
| sniper | Hunter flesh | 4 → 8 |
| plasma_fast (carbine, beam rifle) | energy_shield_thick (Jackal shield) | 0.5 → 0.25 |
| plasma_fast | tough_floodflesh | 0.5 → 0.25 |
| cutting (energy sword) | tough_floodflesh | 4 → **8** |
| cutting | soft / tough flesh (Grunts, Jackals, Brutes) | 2 → 4 |
| kill_flood (shotgun, specific) | tough_floodflesh | 2 → 4 |
| melee | brittle (glass, electronics) | 2 → 4 |
| melee | tough_organic_flesh_brute_tartarus | 0.5 → 0.25 |
| explosion_small / large / attached (grenades, rockets, plasma stick) | energy_shield_thin / thick | 0.5 → **0.25** |
| explosion_small / large | brittle | 2 → 4 |
| explosion_attached | Tartarus | 0.25 → 0.125 |
| bullet_vehicle / plasma_vehicle (turrets, Ghost, Banshee, Wraith bolts) | hard_metal_solid | 0.5 → 0.25 |
| plasma_vehicle | sentinel | 2 → 4 |
| emp (plasma pistol overcharge) | energy shields / sentinel | 500 → 1000 (it already popped them instantly) |
| emp | sentinel_enforcer | 50 → 100 |
| many groups | liquid, energy_shield_invincible, hard_metal_solid, Jackal shield vs bullets | 0 → 0 |

**What the player notices in Halo 2:** the plasma-then-headshot combo is much stronger, since plasma takes
shields at ×3. Plasma does very little to bodies and Brutes. The sniper strips Elite shields at ×4,
and the sword is lethal to the Flood. Grenades and rockets barely touch shields. Hunters' flesh and Sentinels
are much weaker, while Hunter armour and vehicle hulls are much tougher.
**Damage to you:** Elite plasma strips your shield twice as fast. Enemy grenades, rockets and Brute Shot blasts
do half to your shield. Brute plasma rifles hurt your body less.

---

## Halo 3: table [0] (010_jungle; [1] = native Tilt, also edited)

| Damage group (weapons) | Armour (who) | Vanilla → Tilt |
|---|---|---|
| plasma_slow (plasma rifle, plasma pistol, needler impact) | energy_shield_thin (**Elite and Chief shields**) | 1.5 → **3** |
| plasma_slow | hard_metal_thin (**Elite + Chief bodies**) | 0.35 → 0.175 |
| plasma_slow / bullet_slow | tough_organic (Brute flesh **and** Brute armour) | 0.5 → 0.25 |
| plasma_slow | sentinel | 4 → 8 |
| plasma_slow / bullet_slow / bullet_fast / plasma_fast | Hunter flesh | 2 → 4 |
| plasma_slow | hard_metal_thick (Hunter plates, Ghost/Banshee/Chopper) | 0.1 → 0.05 |
| bullet_slow (AR, SMG, magnum, shotgun, spiker) | energy_shield_thin | 1 → 1 (no change) |
| bullet_slow | energy_shield_thick (Jackal shield) | 0 → 0 (still immune) |
| bullet_slow | brittle_flood / brittle_mech | 1.5 → 3 |
| bullet_fast (BR, sniper, MG turret) | tough_floodflesh (combat / carrier forms) | 0.25 → **0.125** |
| bullet_fast / plasma_fast | soft_floodflesh (pure forms, infection) | 2 → 4 |
| bullet_fast | hard_metal_thick | 0.5 → 0.25 |
| plasma_fast (carbine, beam rifle, sentinel beam) | tough_floodflesh | 0.25 → 0.125 |
| plasma_fast | energy_shield_thick (Jackal shield) | 0.5 → 0.25 |
| plasma_fast | sentinel | 2 → 4 |
| sniper (sniper + beam rifle, specific) | hard_metal_thick / soft_floodflesh | 0.5 → 0.25 |
| anti_flood (all melee, flamethrower, firebomb, sentinel beam, specific) | every flood flesh | 2 → **4** |
| burning (flamethrower, firebomb) | Grunt / Brute flesh, flood | 2 → 4 |
| burning | energy_shield_thin | 2 → 4 |
| cutting (sword, dash melee) | flood, soft / tough flesh | 2 → 4 |
| melee | brittle, flood | 2 → 4 |
| melee | hard_metal_thick / hard_terrain | 0.25 → 0.125 |
| explosion_small (frag / plasma grenades, Brute Shot, gravity hammer) | energy_shield_thin / thick | 0.5 → **0.25** |
| explosion_small | hard_metal_thin (Elite + Chief bodies) | 0.5 → 0.25 |
| explosion_small | hard_metal_solid (Wraith, Scarab, Pelican) | 0.25 → 0.125 |
| explosion_large (rockets, missile pod, fuel rod) | energy shields | 0.5 → 0.25 |
| explosion_* | brittle (glass, electronics, explosives) | 2 → 4 |
| laser (Spartan laser) | energy shields, hard_metal_thin / solid | 0.5 → 0.25 |
| laser | brittle, soft_floodflesh | 2 → 4 |
| bullet_vehicle / plasma_vehicle (Warthog, Hornet, Ghost, Banshee, Wraith, Shade guns) | hard_metal_solid / thick, tough_floodflesh | 0.5 → 0.25 |
| emp (plasma pistol overcharge, power drainer) | vehicles 0.001; every other row 0 or 1 | effectively unchanged |
| infection (infection-form attack) | soft flesh (Marines, Grunts) | 2 → 4 |
| infection | hard_metal_thin (Chief, Elites) | 0.25 → 0.125 |

**What the player notices in Halo 3:** your AR, BR and SMG against Elite and Brute *shields* stay the same. Plasma pops
shields twice as fast but barely hurts bodies afterwards. Brutes (flesh and armour) take half from bullets and plasma. Combat forms
shrug off the BR, sniper and carbine (×0.125), while melee, the sword, the flamethrower and the shotgun shred them. Hunters
die fast to almost anything that reaches the flesh. Vehicles take half from vehicle guns and grenades.
**Damage to you:** enemy plasma and needler impacts strip your shield twice as fast but chip your body at half rate.
Enemy grenades, Brute Shots and fuel rods do half to your shield and to your armour. Infection forms do half.

## Halo 3: ODST: table [0] (sc110)
Same groups and armours as Halo 3, with these differences in the vanilla values:

| Damage group | Armour | Vanilla → Tilt |
|---|---|---|
| bullet_slow (SMG, Automag, AR, shotgun, spiker) | energy_shield_thin (Elite / Brute shields) | 0.5 → **0.25** |
| bullet_fast (sniper, MG turret) | energy_shield_thin | 0.5 → 0.25 |
| bullet_fast_h3 (Battle Rifle, ODST-only group) | energy_shield_thin | 1 → 1 |
| plasma_vehicle | energy_shield_thin | 0.75 → 0.375 |
| plasma_vehicle | `hunter` (Hunter plates, specific) | 0.1 → 0.05 |

**What the player notices in ODST:** this is the harshest version. The silenced SMG and Automag already do half against shields, and Tilt
cuts that to a quarter. Plasma (×3) or explosives become close to mandatory against Brute shields.

---

## Halo Reach and Halo 4: table [0] (m10 / m10_crash; the two are nearly identical)

| Damage group (weapons) | Armour (who) | Vanilla → Tilt |
|---|---|---|
| plasma_slow (plasma pistol, plasma rifle; H4 storm rifle) | energy_shield_thin (**Elite, Knight and player shields**) | 1.6 → **3.2** |
| plasma_slow | hard_metal_thin (**Elite, Knight and Spartan bodies**) | 0.4 → 0.2 |
| plasma_slow / needle | tough_organic (Brutes), "hard" | 0.5 → 0.25 |
| needle (needler, needle rifle; H4 railgun impact) | energy_shield_thin | 2 → **4** |
| needle | hard_metal_thin | 0.25 → 0.125 |
| needle / plasma_slow | brittle_elec | 1.5 → 3 |
| bullet_slow (AR, magnum, shotgun; H4 scattershot, boltshot) | energy_shield_thin / hard_metal_thin | 1 → 1 (no change) |
| bullet_slow | tough_organic (Brutes) | 0.5 → 0.25 |
| bullet_slow | energy_shield_thick (Jackal shield) | 0.125 → 0.0625 |
| bullet_slow | hard_metal_thick (Hunter plates, Ghost, Banshee, Wraith) | 0.25 → 0.125 |
| bullet_fast (DMR; H4 BR, LMG) | energy_shield_thick / hard_metal_thick | 0.25 / 0.5 → 0.125 / 0.25 |
| bullet_turret (MG turret, Warthog / Falcon guns) | hard_metal_thick | 0.75 → 0.375 |
| sniper (sniper rifle; H4 beam rifle, binary rifle) | energy_shield_thick / hard_metal_solid | 0.75 → 0.375 |
| plasma_fast (focus rifle, plasma repeater, concussion rifle; H4 carbine, lightrifle, suppressor) | energy_shield_thick | 0.5 → 0.25 |
| plasma_fast | hard_metal_thick | 0.25 → 0.125 |
| laser (Spartan laser; H4 enemy Sentinel Beam) | energy shields | 0.25 → **0.125** |
| laser | brittle | 2 → 4 |
| explosion_small (frag / plasma grenades, grenade launcher, needler supercombine, gauss) | energy_shield_thin | 0.5 → **0.25** |
| explosion_small | hard_metal_thin (Elite / Spartan bodies) | Reach 0.75 → 0.375; H4 0.5 → 0.25 |
| explosion_small | brittle | 2 → 4 |
| explosion_large (rockets, fuel rod / flak, Banshee bomb) | brittle | 3 → **6** |
| explosion_large | energy_shield_thin / hard_metal_thick | 0.75 → 0.375 |
| cutting (energy sword) | soft / tough flesh (Grunts, Jackals, Brutes) | 2 → 4 |
| cutting / melee | hard, hard_metal_thick | 0.5 / 0.25 → 0.25 / 0.125 |
| burning | energy_shield_thin, Grunt / Brute flesh | 2 → 4 |
| emp (plasma pistol charged bolt) | energy_shield_solid 0.5 → 0.25; vehicles 0.001 | shields and flesh unchanged |
| H4 bullet_turret_mech (Mantis gun) | soft flesh | 2 → 4 |

Reach and H4 have no Hunter-flesh, `_player`, Flood or Sentinel rows. Hunters use plain armour/flesh rows.

**What the player notices in Reach and H4:** the noob combo becomes brutal. Plasma takes Elite and Knight shields at ×3.2 and needles at ×4,
then the bodies resist plasma (×0.2). Bullets are unchanged against shields. Brutes take half from everything except
the sword and fire. Every grenade does a quarter to shields. Hunter plates and vehicles take half from small arms.
**Damage to you:** you share the Elites' rows, so enemy plasma pistols and rifles strip your shield 2× faster
(1.6 → 3.2), and enemy needlers, needle rifles and H4 railguns do so too (2 → 4). Enemy grenades do half to your shield
(0.5 → 0.25) and your armour, the Sentinel Beam does half to your shield, and enemy bullets are unchanged.

---

## Method (for checking)
- Values: baseline maps opened with `halo_patch.open_map`. matg Damage Table / Materials offsets came from the
  `*MCC` plugins: H2 0xD0/0x150, H3 0x3EC/0x464, ODST 0x3FC/0x480, Reach 0x3F0/0x48C, H4 0x580/0x610.
  jpt! General/Specific Damage: H2/H3/ODST 0x50/0x54, Reach 0x70/0x74, H4 0x94/0x98.
- Names: Halo 2 resolves directly. For H3, ODST, Reach and H4, `resolve_stringid` **misnames these ids**: they are
  *dynamic* strings with indices below 0x800, at 0x499-0x4D0 in H3, so they take the straight lookup and come back
  as e.g. "colors" or "ring_of_light" in Reach. They were resolved through the dynamic offset instead
  (index + 1490 on H3 010, + 1857 on ODST sc110, + 4747 Reach, + 6841 H4, which are the existing per-game constants).
  The offset that matched the most names (56/60, 58/62, 37/42, 40/45) was taken against the kits' damage-group and armour
  names. The remaining few were static strings: melee, all, sniper, infection, energy, plasma_turret.
- Native-Tilt identification: the H4EK `export-tag-to-xml` element labels and the kits' tool.exe strings, as described above.
- Unverified: whether general and specific rows multiply or the specific one wins, and which materials the ODST
  Rookie (no shield) and the H4 Prometheans other than Knights, Crawlers and Watchers actually use.
