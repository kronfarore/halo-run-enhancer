# Halo 2 phase 0: yardstick candidates, stock weapons, donors (PROPOSALS, 2026-10-20)

Read-only research. Nothing in the kits, the repo or MCC was written. Every number below was
read by `tool export-tag-to-xml` from H2EK / H3EK / HREK / H4EK (scratch exports under this
session's scratchpad: `h2x\`, `sx\`, `h2_weapons.json`). The user picks each weapon's
yardstick at its step 4a; these are proposals only.

## The rule, and what changes for Halo 2

target value = H2 yardstick x source port / source yardstick. A yardstick has to exist in
the SOURCE kit AND in Halo 2, share the port's role and damage type, and (for
`balance_compare` / `balance_port`) have a halo.json card in BOTH games -- the card list is
the practical gate. Card coverage (halo.json "Specific Weapon Modifier", checked):

| card | H2 | H3 | Reach | H4 |
|---|---|---|---|---|
| Pistol, Plasma Pistol, Needler, Sniper Rifle, Rocket Launcher, Shotgun, Flak Cannon (fuel rod), Energy Blade, Frag / Plasma Grenade, Gravity Hammer | yes | yes | yes | yes |
| Plasma Rifle | yes | yes | yes | (card only; H4EK has NO plasma_rifle .weapon) |
| SMG | yes | yes | no | no |
| Battle Rifle, Covenant Carbine, Beam Rifle | yes | yes | no | **yes** (storm_br, storm_covenant_carbine, storm_beam_rifle) |
| Sentinel Beam | yes (pickable) | yes | no | yes (storm_sentinel_beam, AI-only) |
| Brute Shot | yes | yes | no | no |
| Brute Plasma Rifle | yes | **no card** (H3EK has plasma_rifle_red.weapon, uncarded) | no | no |
| Assault Rifle, DMR, Machine Gun, Spartan Laser, Concussion Rifle, Focus Rifle ... | no | - | - | - |

NEW vs Halo 1: **Halo 4 has a Battle Rifle, a Covenant Carbine and a Beam Rifle** (the
brief's "H4 has no Brute weapons" holds; its BR / Carbine / Beam Rifle exist and are carded),
so the LightRifle gets a single-hop BR yardstick and H4 ports in general have more anchors
into Halo 2 than they had into Halo 1. Multi-hop chains (`balance_port.py --hop`, the SAW's
`Assault Rifle:Halo 4>Halo 3` + `SMG:Halo 3>Halo 2`) let a port reach a Halo 2 weapon its
source game lacks; each hop is the same weapon in two games, so a chain = "the bridge game's
yardstick". `port_families.json` already maps the automatic-rifle role to the **SMG** in
Halo 2.

## 0.4 Yardstick candidates (PROPOSALS -- the user picks at step 4a)

Source tags = the ports_h1 configs' (kit-relative). "H1 pick" = what the user chose for the
Halo 1 port (a precedent, not a rule). Every source-side yardstick listed was checked to
exist in the source kit by listing (`H3EK/HREK objects\weapons\...`, H4EK `storm_*`).

| # | weapon | source tag (kit-relative) | provisional | alternatives | direct | step-5b peers (H2) | why |
|---|---|---|---|---|---|---|---|
| H1 | Assault Rifle | H3 rifle\assault_rifle\assault_rifle | SMG | Battle Rifle; Plasma Rifle | none (no AR in H2; the SMG is the family table's H2 automatic rifle) | SMG, Battle Rifle, Plasma Rifle, Brute Plasma Rifle, SAW (port) | magazine 32 full-auto bullet projectile (10/s) = the SMG's role; SMG exists in H3 and H2 so it is ONE hop (balance_SMG_Halo3_to_Halo2.json exists). AR not dual-wieldable: carry rule x1.5 does NOT apply the other way -- watch carry (H2 SMG 240 vs H3 AR 384) |
| H2 | Spartan Laser | H3 support_high\spartan_laser\spartan_laser | Rocket Launcher (H1 pick: laser damage = explosion_large) | Beam Rifle (instant beam + battery + heat in both games); Sniper Rifle; Sentinel Beam | none | Rocket Launcher, Beam Rifle, Sniper, Flak Cannon | spew-charge 2.5 s, battery (age), heat 1.0/shot, 2.5x zoom, instant beam. H2 has no spew-charge: the 'Charge' behaviour (scarab main gun's: 2.8 s, overcharged discharge) is the closest -- UNTESTED on a player weapon |
| H3 | Spike Rifle | H3 rifle\spike_rifle\spike_rifle | SMG | Needler; Plasma Rifle | none (Brutes exist in both, but H2 Brutes never carry a spiker) | SMG, Needler, Brute Plasma Rifle, Plasma Rifle | magazine 40 auto 8/s, slow arcing projectile, dual-wieldable like the SMG (H1 pick AR is not in H2; the SMG is the same bullet magazine automatic, BOTH dual-wield -> no x1.5 carry fudge). Brute Plasma Rifle would be the Brute twin but has NO H3 card |
| H4 | Mauler | H3 pistol\excavator\excavator | Shotgun (H1 pick) | Pistol | none | Shotgun, Energy Blade, Magnum | magazine 5 latch, pellets, dual-wieldable one-hand shotgun |
| H5 | Gravity Hammer | H3 melee\gravity_hammer\gravity_hammer | Energy Blade (H1 pick) | H2's own Gravity Hammer (Tartarus); Rocket / Fuel Rod melee | **H2 gravity_hammer (Tartarus) = the same weapon, card in both** -- but its numbers are a boss's (see below) | Energy Blade, Shotgun | melee-only, ages per swing; the sword is H2's only player melee weapon with Bungie's own player numbers. A ratio on Tartarus's hammer would scale player damage off an AI boss's jpt (tartarus_hammer_melee / _explosion) -- show it, do not default to it |
| R1 | DMR | Reach rifle\dmr\dmr | Sniper Rifle (H1 pick) | **Battle Rifle via Halo 4** (`--hop "DMR:Halo Reach>Halo 4" --hop "Battle Rifle:Halo 4>Halo 2"` = H4's DMR:BR relation onto H2's BR); Pistol | none | Battle Rifle, Magnum, Sniper, Carbine | semi-auto 15, 3x zoom, near-instant. The BR is H2's mid-range precision rifle (closer role than the sniper) but Reach has no BR -- the bridge stacks Halo 4's own scale. FLAG: needs the user's call |
| R2 | Grenade Launcher | Reach rifle\grenade_launcher\grenade_launcher | Frag Grenade + RL for the holes (H1 pick) | Rocket Launcher; Flak Cannon | none | Brute Shot, Rocket Launcher, Flak Cannon | 1-round latch-tether, bouncing grenade. H2 has no tether trigger (approximate as in H1). The Brute Shot is H2's own grenade launcher -- a peer only (no Reach Brute Shot) |
| R3 | Needle Rifle | Reach rifle\needle_rifle\needle_rifle | Needler (H1 pick: needle damage + supercombine) | Pistol; Sniper Rifle | none | Covenant Carbine, Needler, Battle Rifle | 21-round semi-auto 4/s, 2x zoom, supercombining needle. The Carbine is its exact role twin in H2 (18 rounds, 2x) but Reach has no Carbine and there is no bridge (H4 has a Carbine, no Needle Rifle) |
| R4 | Focus Rifle | Reach rifle\focus_rifle\focus_rifle | Plasma Rifle (H1 pick) | Sentinel Beam via Halo 4 (`Focus Rifle:Halo Reach>Halo 4`, `Sentinel Beam:Halo 4>Halo 2`; H4's beam is AI-only); Sniper; Plasma Pistol | none | Sentinel Beam, Beam Rifle, Sniper | continuous instant beam 30/s, heat 0.025/round + battery, 2 zooms 3.5-9.5 (= H2 Beam Rifle's exact zoom range). H2's pickable Sentinel Beam is the same mechanism (30/s, instant, heat + battery) but Reach has none |
| R5 | Plasma Launcher | Reach support_high\plasma_launcher\plasma_launcher | Plasma Grenade + RL holes (H1 pick) | Flak Cannon; Rocket Launcher | none | Rocket Launcher, Flak Cannon, Brute Shot | charge 3 s (charged 2 s, discharge), heat 0.4/round + battery, 3x zoom, sticky explosive bolts; H2 has 'Charge' / 'Latch-Autofire' (charge), no lock-on |
| R6 | Plasma Repeater | Reach rifle\plasma_repeater\plasma_repeater | Plasma Rifle (H1 pick) | Plasma Pistol; Brute Plasma Rifle (no Reach card -- not usable) | Elite: carries the Plasma Rifle in both (= provisional) | Plasma Rifle, Brute Plasma Rifle, SMG, Needler | heat automatic plasma, battery, rate 15 -> 3 with heat. H2's trigger RAMPS over held time (6 -> 9) like Halo 1: approximation B carries over |
| R7 | Concussion Rifle | Reach rifle\concussion_rifle\concussion_rifle | Flak Cannon (fuel rod; H1 pick) | Rocket Launcher; Plasma Grenade | none | Flak Cannon, Rocket Launcher, Brute Shot | magazine 6 latch explosive plasma; Reach's AND H2's fuel rods are both 5-round magazines (cleaner than H1's charge fuel rod) |
| C1 | Storm Rifle | H4 rifle\storm_assault_carbine\storm_assault_carbine | Plasma Pistol (H1 pick) | Needler; Covenant Carbine (H4 storm_covenant_carbine); Sentinel Beam | none (role = H2 Plasma Rifle, but H4 has none: the family table's plasma-rifle row maps Storm Rifle -> Plasma Rifle 1:1, i.e. the port would simply take H2 Plasma Rifle numbers -- degenerate) | Plasma Rifle, Brute Plasma Rifle, SMG, Needler | heat automatic plasma 10/s, heat 0.09/round, battery |
| C2 | Suppressor | H4 rifle\storm_forerunner_smg\storm_forerunner_smg | SMG via the SAW's chain (`Assault Rifle:Halo 4>Halo 3`, `SMG:Halo 3>Halo 2`) | Needler; Sentinel Beam | none (H4 has no SMG) | SMG, Plasma Rifle, Needler, SAW (port) | magazine 48 auto 15/s, decelerating hardlight projectile -- literally the Forerunner SMG; H1 pick AR has no H2 counterpart, the SAW's two-hop is the precedent |
| C3 | Boltshot | H4 pistol\storm_stasis_pistol\storm_stasis_pistol | Pistol (bolt) + Shotgun (blast) (H1 pick) | Plasma Pistol | none | Magnum, Plasma Pistol, Shotgun, Mauler (port) | magazine 10, latch-autofire 0.6 s charge -> 5-round blast: EXACTLY H2's plasma pistol trigger (latch-autofire, 0.6 s, two barrels) |
| C4 | LightRifle | H4 rifle\storm_forerunner_rifle\storm_forerunner_rifle | **Battle Rifle** (single hop, H4 storm_br <-> H2 battle_rifle) | Pistol (H1 pick); Covenant Carbine; Sniper | none | Battle Rifle, Carbine, Magnum, Sniper, DMR (port) | magazine 36, 3x zoom, 3-round burst unscoped / one 3-round shot scoped: the BR's role, and the BR exists in both games. H2's trigger is the same 'latch-zoom' with primary + secondary barrel indices as H4's -- the scoped mode H1 could not do LOOKS native here (UNVERIFIED in game) |
| C5 | Scattershot | H4 rifle\storm_spread_gun\storm_spread_gun | Shotgun (H1 pick) | Energy Blade | none | Shotgun, Energy Blade, Mauler (port) | magazine 5 latch, 6 shards, close range, ricochet |
| C6 | Binary Rifle | H4 rifle\storm_forerunner_sniper_rifle\storm_forerunner_sniper_rifle | Sniper Rifle (H1 pick) | Beam Rifle (H4 storm_beam_rifle; heat weapon -- mag ratios degenerate); Rocket Launcher | none | Sniper, Beam Rifle, Spartan Laser (port) | magazine 2, two zooms 4-10, one-hit kill |
| C7 | Railgun | H4 rifle\storm_rail_gun\storm_rail_gun_pve | Rocket Launcher (H1 pick) | Flak Cannon; Sniper; Beam Rifle | none | Rocket Launcher, Sniper, Flak Cannon, Spartan Laser (port) | 1-round magazine, charge-with-magazine 0.75 s (charged 1.5 s, discharge), slug + blast. H2 has NO charge-with-magazine: 'Latch-Autofire' / 'Charge' on a magazine weapon is UNTESTED |
| C8 | Sticky Detonator | H4 pistol\storm_sticky_detonator\storm_sticky_detonator_pve | Plasma Grenade + RL holes (H1 pick) | Rocket Launcher; Flak Cannon | none | Brute Shot, Rocket Launcher, Flak Cannon | 1-round double-latch-tether, arcing sticky explosive; no tether in H2 (stick + fuse, as H1) |
| C9 | Incineration Cannon | H4 support_high\storm_forerunner_incineration_launcher\storm_forerunner_incineration_launcher | Rocket Launcher (H1 pick) | Flak Cannon | none | Rocket Launcher, Flak Cannon | rocket-launcher type, 1 round, latch, 1.8x zoom (= H2 RL's 1.8x exactly); cluster approximated |

Source-kit yardstick paths: H3EK / HREK `objects\weapons\pistol\magnum\magnum`, `pistol\needler`,
`pistol\plasma_pistol`, `rifle\shotgun`, `rifle\sniper_rifle`, `rifle\plasma_rifle`,
`support_high\rocket_launcher`, `support_high\flak_cannon`, H3 `rifle\smg\smg`,
`rifle\battle_rifle`, `rifle\covenant_carbine`, `rifle\beam_rifle`, `support_low\brute_shot`,
`support_low\sentinel_gun`, `melee\energy_blade` (Reach `melee\energy_sword`),
`melee\gravity_hammer` (H3 + Reach); H4EK `pistol\storm_magnum`, `storm_needler`,
`storm_plasma_pistol`, `rifle\storm_assault_rifle`, `storm_br`, `storm_covenant_carbine`,
`storm_beam_rifle`, `storm_dmr`, `storm_shotgun`, `storm_sniper_rifle`,
`support_high\storm_rocket_launcher`, `storm_fuel_rod_cannon`, `pistol\storm_sentinel_beam`,
`melee\storm_energy_sword`, `storm_gravity_hammer`. Grenades: `objects\weapons\grenade\
(storm_)frag_grenade` / `(storm_)plasma_grenade` in all four kits (H2EK has both).

## Halo 2 stock weapons (H2EK, exported)

Trigger behaviours Halo 2 knows (Assembly Halo2MCC weap plugin): Spew, Latch, Latch-Autofire,
Charge, Latch-Zoom, Latch-Rocketlauncher. NOT present: spew-charge (Spartan Laser),
latch-tether (GL), double-latch-tether (Sticky Det), charge-with-magazine (Railgun).
"battery" = no rounds, `cannot fire at maximum age`. Velocities are the projectile's
initial -> final (wu/s); "instant" = projectile flag `travels instantaneously`.

| tag (objects\weapons\...) | card | msg prefix | class | delivery | ammo | trigger | zoom | dual | blocks mag/trig/barrel | HUD |
|---|---|---|---|---|---|---|---|---|---|---|
| pistol\magnum\magnum | Pistol | mp | bullet | instant (400) | magazine 12 / 60 | latch, recovery 0.1 | none | yes | 1/1/1 | ui\hud\magnum |
| pistol\needler\needler | Needler | nd | needle (supercombine) | projectile 6 homing | magazine 30 / 120 | spew 8/s | none | yes | 1/1/1 | needler |
| pistol\plasma_pistol\plasma_pistol | Plasma Pistol | pp | plasma | projectile 11 (charged 5), faster when player-owned | heat 0.16 + battery | latch-autofire, charge 0.6 s | none | yes | 0/1/2 | pp_test |
| rifle\smg\smg | SMG | smg | bullet | projectile 400 | magazine 60 / 240 | spew 15/s | none | yes | 1/1/1 | smg |
| rifle\smg_silenced\smg_silenced | (SMG) | ssmg | bullet | projectile 400 | magazine 60 / 240 | spew 15/s | none | yes | 1/1/1 | silenced_smg |
| rifle\battle_rifle\battle_rifle | Battle Rifle | br | bullet | instant (400) | magazine 36 / 144 | latch-zoom, 3-burst 15/s, recovery 0.26 | 1 (2x) | no | 1/1/1 | battle_rifle |
| rifle\covenant_carbine\covenant_carbine | Covenant Carbine | cc | carbine slug | instant (400) | magazine 18 / 90 | latch-zoom (both barrel indices -> barrel 1, recovery 0.14) | 1 (2x) | no | 1/1/2 | carbine |
| rifle\sniper_rifle\sniper_rifle | Sniper Rifle | sn | bullet | instant (1200) | magazine 4 / 24 | latch, recovery 0.5 | 2 (3.5-9.5) | no | 1/1/1 | sniper_rifle |
| rifle\beam_rifle\beam_rifle | Beam Rifle | be | plasma beam | instant (1200) | heat 0.65 + battery | latch, recovery 0.25 | 2 (3.5-9.5) | no | 0/1/1 | beam_rifle |
| rifle\shotgun\shotgun | Shotgun | sg | bullet pellets x10 | projectile 120, distance falloff | magazine 12 / 48, shell reload | latch, recovery 1.0 | none | no | 1/1/1 | shotgun |
| rifle\plasma_rifle\plasma_rifle | Plasma Rifle | pr | plasma | projectile 14, faster when player-owned | heat 0.15 + battery (dummy 0-round magazine) | spew 6 -> 9/s | none | yes | 1/1/1 | pr_hud |
| rifle\brute_plasma_rifle\brute_plasma_rifle | Brute Plasma Rifle | bpr | plasma | projectile 14 | heat 0.15 + battery | spew 8 -> 11/s | none | yes | 1/1/1 | pr_hud |
| support_high\rocket_launcher\rocket_launcher | Rocket Launcher | rl | explosive | projectile 8 -> 20, steering | magazine 2 / 8 | latch-rocketlauncher, recovery 0.8 | 1 (1.8x) | no | 1/1/2 | rocket_launcher |
| support_high\flak_cannon\flak_cannon (fuel rod) | Flak Cannon | fc | explosive plasma | projectile 15 -> 6.5 | magazine 5 / 30 | latch, recovery 0.4 | 1 (2x) | no | 1/1/2 | flak_cannon |
| support_low\brute_shot\brute_shot | Brute Shot | bs | explosive grenade | projectile 20 -> 10, ballistic | magazine 4 / 16 | latch, recovery 0.3 | none | no | 1/1/1 | brute_shot |
| melee\energy_blade\energy_blade | Energy Blade | ps | melee | - | ages per kill (battery) | melee only | none | no | 0/0/0 | plasma_sword |
| melee\gravity_hammer\gravity_hammer | Gravity Hammer (Tartarus) | (none) | melee | - | - | melee only | none | no | 0/0/0 | (none) |
| rifle\gpmg\gpmg (CUT, in no scenario) | - | gpmg | bullet | projectile 800 | magazine 40 / 260 | spew 10 -> 13/s | none | no | 1/1/1 | gpmg |
| rifle\saw\saw (OUR PORT) | SAW | saw2 | bullet | projectile 800 | magazine 72 / 288 | spew 20/s | none | no | 1/1/1 | saw |
| characters\sentinel_aggressor\weapons\beam\sentinel_aggressor_beam | Sentinel Beam | sen_b | beam | instant (1200) 30/s | heat 0.04 + battery | spew | none | no | 0/1/1 | sentinel_beam |
| characters\sentinel_aggressor\weapons\beam_elim\sent_agg_beam_elim | Sentinel Eliminator Beam | sen_b | beam | instant 30/s | heat 0.045 + battery | spew | none | no | 0/1/1 | sentinel_beam |
| rifle\beam_rifle\beam_rifle_noplayer | - | be | (AI copy: `cannot be used by player`) | | | | | | | |
| melee\energy_blade\energy_blade_useless | - | ps | (cinematic/AI sword, primary trigger melee) | | | | | | | |
| fixed\plasma_cannon\plasma_cannon, vehicles\...\*_handheld, scarab_main_gun_handheld | (turrets) | pr / none | plasma | | heat / none | spew; the scarab main gun is the only `Charge` trigger (2.8 s) | | | | |

AI-only character weapons (no player HUD / fp anims): hunter_particle_cannon, prophet
gravity_cannon, sentinel_enforcer beam / needler / rocket, sentinel_aggressor_welder.
Ignore `objects\weapons\sz_01..sz_21\saw` (21 SAW copies + `ui\hud\s01..s21`, created
2026-10-20 16:21 by `h2_size_test_map.py`, a parallel capacity test) and `digsite\...`
(Bungie's combo test copies).

UNUSED message families in `data\ui\hud\hud_messages.txt` (no weapon tag points at them):
`di_` (Disintegrator), `sen_g_` (Sentinel Grenade Launcher), `sen_n_` (Sentinel Needler).
They are spare slots like `gpmg_` was. `gpmg_*` stays with the cut GPMG (the SAW moved to
`saw2_*`).

## The Gravity Hammer in Halo 2 (what the "fix" is)

- **Carrier**: Tartarus only. `objects\characters\brute\ai\brute_tartarus.character`
  `weapons properties` / `firing pattern properties` name it (max firing range 3 wu).
  Gameplay placement: the `08b_deltacontrol` boss (weapons resource + master ai resource).
  Elsewhere it is a cinematic prop: `gravity_hammer.scenery` in the 04a, 04b, 06b, 07a, 08b
  scenery resources, and cinematic scripts in 00a / 01b / 04a / 04b / 06b / 07a (01b's
  weapons resource also lists it -- cinematic, or a leftover of an earlier test on 01b:
  UNCERTAIN). The user keeps a shortcut `objects\weapons\1enemy_only\gravity_hammer.weapon`.
- **Its damage is not in the weapon**: Tartarus hits with
  `objects\characters\brute\damage_effects\tartarus_hammer_melee`, `tartarus_hammer_explosion`,
  `tartarus_obstacle_smash` (the enhancer's H2 Gravity Hammer Damage / Radius cards target
  exactly these), driven by the Brute's melee.
- **The weapon tag is a stub**: flags `melee only`; weapon class `melee`, name `gh`; NO
  magazines, triggers or barrels; NO first-person animations (the `first person` block's
  masterchief entry points its fp model at the 3P render model, no jmad, no dervish entry);
  NO HUD; ALL message string ids empty (and no `gh_*` family exists in hud_messages);
  NO player melee damage / response, no 1st/2nd/3rd-hit or lunge damage, magnetism 0;
  no `weapon ages`/`cannot fire at maximum age` (no energy). A player who picked it up
  (it never drops in normal play) would hold an unanimated, silent, damage-less object.
- **H3's by contrast**: melee only + `cannot fire at maximum age` (energy per swing), its own
  fp_gravity_hammer graph, HUD, messages and gravity_hammer_explosion / smash damage.
- **The fix, proposed**: treat it as a full PORT, not a flag flip. Build a NEW player tag
  (e.g. cloned from `energy_blade`: melee-only, aging, plasma_sword HUD, `ps` 2-char prefix ->
  a new 2-char `gh` family, the weapon name it already uses) and leave Tartarus's tag alone
  (PORTING step 3: a tag shared with a live weapon changes it when tuned -- here, the 08b
  boss). Reusable from H2 itself: Bungie's hammer render / collision / physics model (3P art
  exists, so geometry is mostly done). Needed from H3: FP animations (none exist in H2:
  `masterchief\fp\weapons\melee` holds only fp_energy_blade) retimed via the H2 anim codec,
  player melee damage + the area blast (H3's hammer jpts, ratio'd), energy per swing, HUD,
  messages. 3P: masterchief / dervish graphs show `sword` classes but no confirmed `melee`
  (hammer) class -- the brute graph has it -- so 3P hammer animations for the player are
  probably missing too (UNVERIFIED).

## Donors: which Halo 2 tag each port's weapon tag is cloned from

What actually constrains a Halo 2 donor: H2 tags are byte-edited (no XML import), so the
BLOCK SHAPE should match -- magazines (0/1), barrels (1/2) -- because inserting a block
element is the expensive edit, while trigger behaviour, charge times, heat values, zoom and
flags are plain fields present on every tag (h2_tagfield). Then the HUD KIND (ammo counter
vs heat/battery meter) and the handedness. Animations, projectile, effects and messages are
the port's own anyway (steps 3, 8, 9). MESSAGE PREFIX: `h2_port_messages.py` repoints a tag
in place, so the port's new prefix must be EXACTLY as long as the donor's (`gpmg` -> `saw2`).

| # | port | donor tag (objects\weapons\...) | donor prefix (port prefix length) | why / edits |
|---|---|---|---|---|
| H1 | Assault Rifle | rifle\smg\smg | smg (3) | spew magazine bullet 1/1/1, ammo HUD; clear `can be dual wielded`. Alt: battle_rifle (br) for a two-handed non-dual base |
| H2 | Spartan Laser | rifle\beam_rifle\beam_rifle | be (2) | battery + heat, instant beam, two-handed, heat/battery HUD, 0 mags; trigger latch -> Charge (2.5 s), zoom levels 2 -> 1. Alt: plasma_pistol (pp) has the 2 barrels + charge but is a one-hand pistol |
| H3 | Spike Rifle | rifle\smg\smg | smg (3) | spew magazine 1/1/1 AND dual-wieldable -- keep the flag |
| H4 | Mauler | rifle\shotgun\shotgun | sg (2) | latch magazine pellets 1/1/1; set `can be dual wielded`. Alt: magnum (mp) for one-hand + dual (pellet count is a barrel field either way) |
| H5 | Gravity Hammer | melee\energy_blade\energy_blade | ps (2) -> new `gh` | melee-only, ages, 0/0/0, sword HUD; plus H2's own gravity_hammer model (see above) |
| R1 | DMR | rifle\battle_rifle\battle_rifle | br (2) | latch-zoom magazine instant bullet, zoom 1 level; burst -> single (rounds per second / recovery fields). Alt: sniper_rifle (sn) |
| R2 | Grenade Launcher | support_low\brute_shot\brute_shot | bs (2) | latch magazine arcing explosive grenade, ballistic AI aim; magazine 4 -> 1 |
| R3 | Needle Rifle | rifle\covenant_carbine\covenant_carbine | cc (2) | Covenant semi-auto magazine, latch-zoom, 2x zoom, 1/1/2 (barrel 1 used); projectile from the needler (supercombine) |
| R4 | Focus Rifle | characters\sentinel_aggressor\weapons\beam\sentinel_aggressor_beam | sen_b (5) | spew 30/s instant beam, heat + battery, 0 mags, beam HUD -- the same mechanism; add the beam rifle's 2 zoom levels (fields). Alt: beam_rifle (be) |
| R5 | Plasma Launcher | pistol\plasma_pistol\plasma_pistol | pp (2) | charge trigger + 2 barrels (tap / charged volley) + heat/battery HUD, 0 mags; clear dual wield, charge 0.6 -> 3.0. One-hand pistol base: handedness comes from the port's own graphs. Alt: flak_cannon (fc) if a magazine HUD is acceptable |
| R6 | Plasma Repeater | rifle\plasma_rifle\plasma_rifle | pr (2) | spew heat automatic + battery + rate ramp; clear dual wield. Alt: brute_plasma_rifle (bpr, 3) |
| R7 | Concussion Rifle | support_high\flak_cannon\flak_cannon | fc (2) | latch magazine (5 -> 6) explosive plasma bolt, two-handed Covenant HUD; zoom 1 -> 0 |
| C1 | Storm Rifle | rifle\plasma_rifle\plasma_rifle | pr (2) | heat automatic plasma + battery; clear dual wield |
| C2 | Suppressor | rifle\smg\smg | smg (3) | spew magazine 1/1/1 (48-round); clear dual wield. (`ssmg` (4) is the other SMG-shaped prefix) |
| C3 | Boltshot | pistol\plasma_pistol\plasma_pistol | pp (2) | latch-autofire 0.6 s + 2 barrels = the Boltshot's exact trigger; ADD a magazine element (10 / 40) -- the one block insert; clear dual wield. Alt: magnum (mp) + a second barrel (heavier insert) |
| C4 | LightRifle | rifle\battle_rifle\battle_rifle | br (2) | latch-zoom 3-burst magazine 36 -- the same burst; for the scoped mode add a 2nd barrel (or start from covenant_carbine, cc, which already has 2 barrels under latch-zoom) |
| C5 | Scattershot | rifle\shotgun\shotgun | sg (2) | latch magazine pellets; 10 -> 6 projectiles, 12 -> 5 rounds |
| C6 | Binary Rifle | rifle\sniper_rifle\sniper_rifle | sn (2) | latch magazine instant, 2 zooms (3.5-9.5 vs 4-10); magazine 4 -> 2 |
| C7 | Railgun | support_high\rocket_launcher\rocket_launcher | rl (2) | 1-2 round magazine power weapon, 2 barrels, two-handed; trigger -> latch-autofire / Charge with 0.75 s (UNTESTED on a magazine weapon) |
| C8 | Sticky Detonator | support_low\brute_shot\brute_shot | bs (2) | latch magazine arcing grenade; magazine -> 1. (One-handed in H4: the port's own graphs) |
| C9 | Incineration Cannon | support_high\rocket_launcher\rocket_launcher | rl (2) | rocket-launcher type, 1.8x zoom already, latch-rocketlauncher -> latch, magazine 2 -> 1 |

Donor reuse: smg x3, plasma_pistol x2, plasma_rifle x2, battle_rifle x2, brute_shot x2,
rocket_launcher x2, shotgun x2, one each of beam_rifle, energy_blade, covenant_carbine,
sentinel beam, flak_cannon, sniper_rifle. A clone is a new tag, so sharing a donor is fine;
the 2-char prefix space is ample, the 3-char `smg` donors need three distinct 3-char port
prefixes.

## Uncertain / to check at each weapon's step

1. H2 `Charge` / `Latch-Autofire` charge on a weapon WITH a magazine (Railgun) or as the
   Spartan Laser's hold-to-fire -- no stock player weapon does it.
2. H2 latch-zoom firing the SECONDARY barrel when zoomed (LightRifle scoped mode): inferred
   from the carbine's barrel indices and H4 using the same enum; not tested.
3. DMR / Focus Rifle bridges through Halo 4 chain H4's own scale -- shown as alternatives only.
4. Brute Plasma Rifle has no H3 / Reach card, so it cannot be a yardstick for the Spiker or
   the Repeater without a card being added.
5. The hammer's 01b weapons-resource entry (cinematic vs a test leftover) and the player
   3P hammer animation class.
6. Velocities of H2 plasma bolts (11-14) read low against later games; they carry `faster
   when owned by player` -- measure before ratioing speed.
