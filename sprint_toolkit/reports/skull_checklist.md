# Skull checks (2026-10-05)

Test **one skull at a time** where possible: Thunderstorm left enemies unarmed, which hid
Famine in ODST last time. "Any map" means the result does not depend on the level.

## 0. The crash
- [ ] Patch Map with a per-enemy skull drawn (Assassins / Thunderstorm / Downpour): no TypeError.

## 1. Tilt (any map, every game)
New rule: weaknesses x2, **everything else halved** (a neutral 1.0 becomes 0.5), immunities stay.
- [ ] H1: plasma strips Elite shields in about half the shots; the AR is weaker against Elite shields.
- [ ] H2 / H3 / Reach / H4: plasma strips shields much faster; the AR / BR now do **half** against Elite and Brute shields.
- [ ] You: enemy plasma strips your shield faster; enemy bullets do half.
- Details per game: sprint_toolkit/reports/tilt_explained.md (written before the 1.0 -> 0.5 rule).

## 2. Fog
- [ ] H3 (050 Flood Voi is good, lots of Infection Forms): no blips at all, no dial.
- [ ] H4 (any map): the dial is still drawn but shows no blips.
- [ ] ODST: Fog is never offered.
- H1 / H2 / Reach already confirmed.

## 3. Famine (any map with weapons lying around)
- [ ] Weapons placed in the level have half their magazine and reserve.
- [ ] Your marker-spawned starting weapons are full.
- [ ] Enemy drops are halved (H1/H2/H3/Reach/H4 confirmed; check ODST without Thunderstorm).

## 4. Assassins (now a skull, one per enemy type)
- [ ] It is offered only on levels where that enemy fights.
- [ ] Reach (m10 Grunt or Elite): that enemy is cloaked. The other games are already confirmed.

## 5. Thunderstorm (now one per enemy type)
- [ ] H2 03a, Thunderstorm: Grunt -> Jackals with weapons and normal AI; Thunderstorm: Jackal -> armed Elites.
- [ ] H3 020 / 040: Grunts -> armed Jackals; Grunts that ride Phantoms stay Grunts and still unload; Jackal -> armed Brutes; Brute -> Hunter on 040 (010 has no Hunters).
- [ ] ODST sc130 / sc150: Grunt -> Jackal, Jackal -> armed Brute; Phantoms still unload.
- [ ] Reach m10 / m30: promoted enemies spawn at all.
- [ ] H4 m10: Grunts become Jackals, never Elites; no Crawler / Watcher / Knight card exists.
- [ ] No double move: Thunderstorm Grunt + Thunderstorm Jackal together -> Grunts become Jackals and only the ORIGINAL Jackals become Elites.

## 6. Downpour (new, one per enemy type)
- [ ] e.g. H2 Downpour: Elite -> Elites become Jackals; the patcher shows x1.5 rows for Jackal shield / vitality / fire rate and they are editable.
- [ ] Downpour: Hunter -> Hunters become Elites (Brutes in H3 / ODST).

## 7. Pool rules
- [ ] After Thunderstorm: Grunt, no Grunt card is offered any more (enemy cards and Assassins: Grunt).
- [ ] Thunderstorm X and Downpour X are never both drawn for the same enemy.
- [ ] Thunderstorm: Jackal alone -> Jackal cards leave the pool; with Thunderstorm: Grunt too they stay.

## 8. Betrayal / Schism
- [ ] Betrayal + Friend Movement Speed / Friend Active Camo: the patch results show them as skipped ("Betrayal: the allies this card acts on fight you now").
- [ ] Betrayal + Friend Spawn Count: no extra hostile Marines from it.
- [ ] After Betrayal, Human cards appear in the Enemy slot (e.g. Human Body Vitality works); Human Spawn Count adds more hostile Marines.
- [ ] H3 010: the opening Johnson squad stays friendly (by design).
- Schism in ODST: nothing to test (no non-human allies).

## 9. Iron
- [ ] Co-op, both machines patched with MCC running: one player dies -> both go back to the checkpoint. Solo is already confirmed in all six games.

## 10. Options -> Skulls (new page)
- [ ] "A skull lasts one map only": draw a skull on map A; patching map B no longer applies it, and it can be drawn again. Iron is switched off by the map-B patch.
- [ ] Untick a category: it is never offered. A co-op partner who loads the run has the same boxes.

## 11. Halo 1 grenades
- [ ] Options: "Place drafted grenades at the starting-weapon marker" ON (it is off by default, in every game). Draft a grenade on an H1 level: it lies at your marker.

## 12. Friend Active Camo (ally card)
- [ ] Any game: allied Marines are cloaked.
