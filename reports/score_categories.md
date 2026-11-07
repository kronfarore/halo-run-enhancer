# Metagame score categories

Generated 2026-11-07 by the U4 B8 fix (scratchpad gen_score_report.py) from `halo.json` and `scoredb_patch.CATEGORIES`: every offered enemy-effect name of the four enemy groups (General, Specific Enemy, Boss, Hero; `ignore`d cards left out) and the score category it falls in. The WEIGHTS are the ones set on 2026-08-10 and were not changed; the review (U4 B8, 2026-11-07) found 252 of these names scoring zero and placed them with the keyword rules of the fix plan. `General <x>` scores as `<x>`; `Armed: <weapon>` as equipment; `Hardened: ...` as durability. A card offered to several enemies is listed once.

| category | weight | names |
|---|---|---|
| durability | 5 | 59 |
| rate_of_fire | 5 | 31 |
| damage | 4 | 22 |
| ranks | 4 | 21 |
| accuracy | 3 | 20 |
| flood_forms | 3 | 8 |
| grenades | 3 | 21 |
| range | 3 | 28 |
| positioning | 2 | 50 |
| aggression | 1 | 42 |
| equipment | 1 | 7 |
| senses | 1 | 10 |

## durability (weight 5)

| name | offered to | new |
|---|---|---|
| Armor Lock Chance | Specific (Brute, Elite, Human) | yes |
| Armor Lock Duration | Specific (Brute, Elite, Human) | yes |
| Body Recharge | Hero (Jackal Ranger, Jackal Sniper) |  |
| Body Recharge Amount | Specific (Brute, Flood Pure Form, Human, Jackal, Skirmisher) | yes |
| Body Recharge Delay | Specific (Brute, Flood Pure Form, Human, Jackal, Skirmisher) | yes |
| Body Recharge Time | Specific (Brute, Flood Pure Form, Human, Jackal, Skirmisher) | yes |
| Body Vitality | Specific (Brute, Bugger, Crawler, Elite, Flood Carrier Form, Flood Combat Form, Flood Infection Form, Flood Pure Form, Grunt, Human, Hunter, Jackal, Knight, Sentinel, Skirmisher, Watcher); Boss (343 Guilty Spark, Heretic Leader, Mule, Prophet Regret, Tartarus); Hero (Brute Chieftain, Elite General, Elite Honor Guard, Elite Specops Commander, Elite Zealot, Grunt Ultra, Jackal Ranger, Jackal Sniper, Knight Commander, Sentinel Enforcer) |  |
| Detonation Body Vitality | Specific (Engineer) | yes |
| General Enemy Recharge | General |  |
| General Enemy Shield | General |  |
| General Enemy Vitality | General |  |
| Hardened: Armour vs Bullets | General | yes |
| Hardened: Armour vs Mounted guns | General | yes |
| Hardened: Armour vs Needles | General | yes |
| Hardened: Armour vs Plasma | General | yes |
| Hardened: Armour vs Precision rounds | General | yes |
| Hardened: Brute hide vs Bullets | General | yes |
| Hardened: Brute hide vs Plasma | General | yes |
| Hardened: Flesh vs Blades and melee | General | yes |
| Hardened: Flesh vs Bullets | General | yes |
| Hardened: Flesh vs Explosives | General | yes |
| Hardened: Flesh vs Fire | General | yes |
| Hardened: Flesh vs Mounted guns | General | yes |
| Hardened: Flesh vs Plasma | General | yes |
| Hardened: Flesh vs Precision rounds | General | yes |
| Hardened: Flood vs Anything | General | yes |
| Hardened: Flood vs Blades and melee | General | yes |
| Hardened: Flood vs Bullets | General | yes |
| Hardened: Flood vs Explosives | General | yes |
| Hardened: Flood vs Fire | General | yes |
| Hardened: Hunters vs Precision rounds | General | yes |
| Hardened: Shields vs Blades and melee | General | yes |
| Hardened: Shields vs Bullets | General | yes |
| Hardened: Shields vs Explosives | General | yes |
| Hardened: Shields vs Lasers | General | yes |
| Hardened: Shields vs Mounted guns | General | yes |
| Hardened: Shields vs Needles | General | yes |
| Hardened: Shields vs Plasma | General | yes |
| Hardened: Shields vs Precision rounds | General | yes |
| Hardened: Vehicles and Hunter plates vs Explosives | General | yes |
| Hardened: Vehicles and Hunter plates vs Lasers | General | yes |
| Hardened: Vehicles and Hunter plates vs Mounted guns | General | yes |
| Hardened: Vehicles and Hunter plates vs Plasma | General | yes |
| Hologram Body Vitality | Boss (Heretic Leader) |  |
| Hologram Shield Vitality | Boss (Heretic Leader) |  |
| Protect Damage Amount | Specific (Flood Pure Form) | yes |
| Protect Time | Specific (Flood Pure Form) | yes |
| Recharge Delay | Specific (Elite, Jackal) | yes |
| Resurrection | Specific (Watcher) | yes |
| Shield Boost Period | Specific (Engineer) | yes |
| Shield Boost Radius | Specific (Engineer) | yes |
| Shield Boost Strength | Specific (Engineer) | yes |
| Shield Recharge Delay | Specific (Elite, Human, Jackal, Knight); Boss (Heretic Leader); Hero (Elite General, Knight Commander) | yes |
| Shield Recharge Time | Specific (Elite, Human, Jackal, Knight); Boss (Heretic Leader); Hero (Elite General, Knight Commander) | yes |
| Shield Vitality | Specific (Elite, Flood Combat Form, Human, Jackal, Knight, Sentinel, Skirmisher, Watcher); Boss (Heretic Leader, Prophet Regret, Tartarus); Hero (Brute Chieftain, Elite General, Elite Honor Guard, Elite Specops Commander, Elite Zealot, Grunt Ultra, Jackal Ranger, Jackal Sniper, Knight Commander, Sentinel Enforcer) |  |
| Turret Vitality | Specific (Watcher) | yes |
| Turtle Distance | Specific (Flood Pure Form) | yes |
| Turtle Threshold | Specific (Flood Pure Form) | yes |
| Turtle Time | Specific (Flood Pure Form) | yes |

## rate_of_fire (weight 5)

| name | offered to | new |
|---|---|---|
| Beam Projectiles Per Shot | Hero (Sentinel Enforcer) | yes |
| Beam Rate of Fire | Boss (343 Guilty Spark) |  |
| Beam Salvo | Hero (Sentinel Enforcer) | yes |
| Distance Damage Time | Specific (Flood Pure Form) | yes |
| Fight Circle Firing Time | Specific (Crawler) | yes |
| General Burst Seperation | General |  |
| General Bursting | General | yes |
| General Firing Patterns | General |  |
| General New Target Delay | General |  |
| General Overcharge Chance | General |  |
| General Rate of Fire | General |  |
| General Special Fire Delay | General |  |
| Gravity Cannon Projectiles Per Shot | Boss (Prophet Regret) | yes |
| Gravity Cannon Salvo | Boss (Prophet Regret) | yes |
| Head Gun Rate of Fire | Specific (Crawler) | yes |
| Hologram Rate of Fire | Boss (Heretic Leader) |  |
| Hunter Fuel Rod Charging Time | Specific (Hunter) |  |
| Hunter Fuel Rod Projectiles Per Shot | Specific (Hunter) |  |
| Hunter Fuel Rod Rounds per Second | Specific (Hunter) |  |
| Needler Projectiles Per Shot | Hero (Sentinel Enforcer) | yes |
| Needler Salvo | Hero (Sentinel Enforcer) | yes |
| Projectiles Per Shot | Specific (Sentinel) | yes |
| Rate of Fire | Specific (Brute, Elite, Flood Combat Form, Flood Pure Form, Grunt, Human, Hunter, Jackal, Sentinel, Watcher) |  |
| Rocket Projectiles Per Shot | Hero (Sentinel Enforcer) | yes |
| Rocket Salvo | Hero (Sentinel Enforcer) | yes |
| Run Time | Specific (Flood Combat Form) | yes |
| Special-Fire Chance | Specific (Grunt, Jackal) | yes |
| Special-Fire Delay | Specific (Grunt, Jackal) | yes |
| Spew Chance | Specific (Flood Pure Form) | yes |
| Spew Frequency | Specific (Flood Pure Form) | yes |
| Turret Rate of Fire | Specific (Watcher) | yes |

## damage (weight 4)

| name | offered to | new |
|---|---|---|
| Beam Damage | Specific (Sentinel); Boss (343 Guilty Spark); Hero (Sentinel Enforcer) |  |
| Berserk Damage | Specific (Flood Combat Form, Hunter) | yes |
| Chieftain Hammer Damage | Hero (Brute Chieftain) |  |
| Death Detonation Time | Specific (Engineer) | yes |
| Death Height | Specific (Engineer) | yes |
| Explosion Damage | Specific (Sentinel) |  |
| General Enemy damage | General |  |
| General Weapon Damage Modifier | General |  |
| Gravity Hammer Damage | Boss (Tartarus) |  |
| Ground Smash Damage | Boss (Mule) | yes |
| Grunt Damage | Specific (Grunt) | yes |
| Head Gun Damage | Specific (Crawler) | yes |
| Hunter Fuel Rod Damage | Specific (Hunter) |  |
| Melee Damage | Specific (Brute, Bugger, Crawler, Elite, Flood Combat Form, Flood Infection Form, Human, Hunter, Knight); Boss (Mule) |  |
| Morph Damage | Specific (Flood Pure Form) | yes |
| Needler Damage | Hero (Sentinel Enforcer) |  |
| Pop Damage | Specific (Flood Carrier Form, Flood Infection Form) |  |
| Roar Damage | Boss (Mule) | yes |
| Rocket Damage | Hero (Sentinel Enforcer) |  |
| Special Damage | Specific (Grunt, Jackal) | yes |
| Turret Damage | Specific (Watcher) | yes |
| Weapon Damage Modifier | Specific (Elite, Flood Combat Form, Grunt, Human, Hunter, Jackal, Sentinel) |  |

## ranks (weight 4)

| name | offered to | new |
|---|---|---|
| Elite Incursion | General | yes |
| Few Upgrade Chance | Specific (Elite, Grunt) | yes |
| Flood Combat Incursion | General | yes |
| Flood Infection Incursion | General | yes |
| General Few Upgrade Chance | General | yes |
| General Major Upgrades (Few) | General |  |
| General Major Upgrades (Many) | General |  |
| General Major Upgrades (Normal) | General |  |
| General Many Upgrade Chance | General | yes |
| General Normal Upgrade Chance | General | yes |
| General Spawn Count | General | yes |
| Grunt Incursion | General | yes |
| Hunter Incursion | General | yes |
| Infection Conversion | Specific (Flood Combat Form) | yes |
| Jackal Incursion | General | yes |
| Many Upgrade Chance | Specific (Elite, Grunt) | yes |
| Normal Upgrade Chance | Specific (Elite, Grunt) | yes |
| Sentinel Incursion | General | yes |
| Shard Spawning | Specific (Watcher) | yes |
| Spawn Count | Specific (Brute, Bugger, Crawler, Elite, Engineer, Flood Carrier Form, Flood Combat Form, Flood Infection Form, Flood Pure Form, Grunt, Human, Hunter, Jackal, Knight, Sentinel, Watcher); Boss (Mule); Hero (Sentinel Enforcer) | yes |
| Transformation Time | Specific (Flood Pure Form) | yes |

## accuracy (weight 3)

| name | offered to | new |
|---|---|---|
| Accuracy | Specific (Flood Combat Form) |  |
| Accuracy Bounds | Specific (Brute, Bugger, Elite, Flood Carrier Form, Flood Infection Form, Flood Pure Form, Grunt, Human, Hunter, Jackal) | yes |
| Accuracy Time | Specific (Brute, Bugger, Elite, Flood Carrier Form, Flood Infection Form, Flood Pure Form, Grunt, Human, Hunter, Jackal) | yes |
| Distribution Function | Specific (Hunter, Sentinel) | yes |
| General AI Projectile Speed | General |  |
| General Accuracy Bounds | General | yes |
| General Accuracy Time | General | yes |
| General Burst Error | General |  |
| General Guidance Vs Player | General |  |
| General Projectile Error | General |  |
| General Target Leading | General | yes |
| General Target Tracking | General | yes |
| General Tracking & Leading | General | yes |
| Head Gun Accuracy | Specific (Crawler) | yes |
| Hologram Accuracy | Boss (Heretic Leader) |  |
| Hologram Target Leading | Boss (Heretic Leader) | yes |
| Hologram Target Tracking | Boss (Heretic Leader) | yes |
| Projectile Error | Specific (Brute, Bugger, Elite, Flood Carrier Form, Flood Infection Form, Grunt, Human, Hunter, Jackal) |  |
| Target Leading | Specific (Elite, Flood Combat Form, Human, Hunter, Jackal, Sentinel, Watcher); Boss (Prophet Regret) | yes |
| Target Tracking | Specific (Elite, Flood Combat Form, Human, Hunter, Jackal, Sentinel, Watcher); Boss (Prophet Regret) | yes |

## flood_forms (weight 3)

| name | offered to | new |
|---|---|---|
| General Infection Forms | General |  |
| Group Morph | Specific (Flood Pure Form) |  |
| Infestation Speed | Specific (Flood Infection Form) |  |
| Morph Distance | Specific (Flood Pure Form) | yes |
| Ranged Distance | Specific (Flood Pure Form) | yes |
| Stalk Charge | Specific (Flood Pure Form) | yes |
| Stalk Range | Specific (Flood Pure Form) | yes |
| Throttle Distance | Specific (Flood Pure Form) | yes |

## grenades (weight 3)

| name | offered to | new |
|---|---|---|
| Anti-Vehicle Grenade Chance | Specific (Brute, Grunt, Human) | yes |
| Encounter Grenade Timeout | Specific (Elite) | yes |
| General Grenade Chance | General | yes |
| General Grenade Chance Scale | General | yes |
| General Grenade Collateral | General | yes |
| General Grenade Range | General | yes |
| General Grenade Timer Scale | General | yes |
| General Grenade Velocity | General | yes |
| Grenade Catch Attack Speed | Specific (Watcher) | yes |
| Grenade Catch Chance | Specific (Watcher) | yes |
| Grenade Catch Cooldown | Specific (Watcher) | yes |
| Grenade Catch Range | Specific (Watcher) | yes |
| Grenade Catch Strength | Specific (Watcher) | yes |
| Grenade Chance | Specific (Brute, Elite, Grunt, Human); Hero (Brute Chieftain, Elite General, Elite Honor Guard, Elite Specops Commander, Elite Zealot, Grunt Ultra, Knight Commander) | yes |
| Grenade Check Time | Specific (Elite, Grunt, Human) | yes |
| Grenade Collateral | Specific (Brute, Bugger, Elite, Flood Combat Form, Flood Pure Form, Grunt, Human, Knight) | yes |
| Grenade Range | Specific (Brute, Bugger, Elite, Flood Combat Form, Flood Pure Form, Grunt, Human, Knight) | yes |
| Grenade Throw Delay | Specific (Grunt, Human) | yes |
| Grenade Velocity | Specific (Brute, Bugger, Elite, Flood Combat Form, Flood Pure Form, Grunt, Human, Knight) | yes |
| Kamikaze Chance | Specific (Grunt) | yes |
| Kamikaze Count | Specific (Grunt) | yes |

## range (weight 3)

| name | offered to | new |
|---|---|---|
| Advance Range | Specific (Knight) | yes |
| Beam Projectile Range | Hero (Sentinel Enforcer) | yes |
| Beam Projectile Velocity | Hero (Sentinel Enforcer) | yes |
| Beam Range | Boss (343 Guilty Spark) |  |
| Beam Velocity | Boss (343 Guilty Spark) | yes |
| Chieftain Hammer Radius | Hero (Brute Chieftain) |  |
| Distance Damage Radius | Specific (Flood Pure Form) | yes |
| Explosion Radius | Specific (Sentinel) |  |
| Fuel Rod Gravity | Specific (Hunter) | yes |
| Fuel Rod Range | Specific (Hunter) | yes |
| Fuel Rod Velocity | Specific (Hunter) | yes |
| General Firing Range | General | yes |
| General Maximum Firing Distance | General |  |
| Gravity Cannon Projectile Range | Boss (Prophet Regret) | yes |
| Gravity Cannon Projectile Velocity | Boss (Prophet Regret) | yes |
| Gravity Hammer Radius | Boss (Tartarus) |  |
| Grunt Radius | Specific (Grunt) | yes |
| Hunter Radius | Specific (Hunter) | yes |
| Maximum Firing Distance | Specific (Brute, Elite, Flood Combat Form, Flood Pure Form, Grunt, Human, Jackal, Sentinel, Watcher); Boss (Prophet Regret, Tartarus) |  |
| Maximum Firing Distance Hunter Fuel Rod | Specific (Hunter) |  |
| Needler Projectile Range | Hero (Sentinel Enforcer) | yes |
| Needler Projectile Velocity | Hero (Sentinel Enforcer) | yes |
| Pop Radius | Specific (Flood Carrier Form, Flood Infection Form) |  |
| Rocket Projectile Range | Hero (Sentinel Enforcer) | yes |
| Rocket Projectile Velocity | Hero (Sentinel Enforcer) | yes |
| Rocket Radius | Hero (Sentinel Enforcer) | yes |
| Sentinel Beam Gravity | Specific (Sentinel) | yes |
| Sentinel Beam Range | Specific (Sentinel) | yes |

## positioning (weight 2)

| name | offered to | new |
|---|---|---|
| Advance | Specific (Knight) | yes |
| Boarding | Specific (Brute, Bugger, Elite, Flood Combat Form) | yes |
| Combat Position Time | Specific (Elite, Grunt, Human, Hunter, Jackal, Sentinel) | yes |
| Cover Chance | Specific (Brute, Bugger, Elite, Engineer, Flood Pure Form, Grunt, Human, Jackal); Boss (Tartarus) |  |
| Cover Threshold | Specific (Brute, Bugger, Crawler, Elite, Engineer, Flood Pure Form, Grunt, Human, Jackal, Knight, Sentinel, Skirmisher); Boss (Tartarus) | yes |
| Crouch Chance | Specific (Flood Combat Form) | yes |
| Defensive Cover | Specific (Brute, Bugger, Crawler, Elite, Engineer, Grunt, Human, Hunter, Jackal, Knight, Skirmisher) | yes |
| Dive From Grenade Chance | Specific (Brute, Bugger, Crawler, Elite, Grunt, Human, Jackal, Knight, Skirmisher); Boss (Heretic Leader) |  |
| Enforcer Chassis Acceleration | Hero (Sentinel Enforcer) | yes |
| Enforcer Chassis Speed | Hero (Sentinel Enforcer) | yes |
| Enforcer Chassis Turn | Hero (Sentinel Enforcer) | yes |
| Evasion | Specific (Watcher) | yes |
| Evasion Properties | Specific (Brute, Bugger, Crawler, Elite, Engineer, Flood Combat Form, Flood Pure Form, Grunt, Human, Hunter, Jackal, Knight, Sentinel, Skirmisher, Watcher) | yes |
| Fight Circle Angles | Specific (Crawler) | yes |
| Fight Circle Strafe Time | Specific (Crawler) | yes |
| Flanking | Specific (Brute, Bugger, Crawler, Elite, Engineer, Grunt, Human, Hunter, Jackal, Knight, Skirmisher) | yes |
| Flight Acceleration | Specific (Bugger, Engineer, Sentinel, Watcher) | yes |
| Flight Speed | Specific (Bugger, Engineer, Sentinel, Watcher) | yes |
| General Cover Threshold | General | yes |
| General Fight Flank Chance | General | yes |
| General Hide Behind Cover | General | yes |
| General Movement Speed | General | yes |
| General Player Vehicle Ram Chance | General |  |
| Gravity Jump Cooldown | Hero (Knight Commander) | yes |
| Gravity Jump Descend Gravity | Hero (Knight Commander) | yes |
| Gravity Jump Float Time | Hero (Knight Commander) | yes |
| Gravity Jump Height | Hero (Knight Commander) | yes |
| Gravity Jump Retreat Radius | Hero (Knight Commander) | yes |
| Gravity Jump Target Attractor | Hero (Knight Commander) | yes |
| Gravity Jump Trigger Distance | Hero (Knight Commander) | yes |
| Gravity Throne Acceleration | Boss (Prophet Regret) | yes |
| Gravity Throne Speed | Boss (Prophet Regret) | yes |
| Gravity Throne Turn | Boss (Prophet Regret) | yes |
| Guard Position Time | Specific (Elite, Grunt, Human, Hunter, Jackal, Sentinel) | yes |
| Hide Behind Cover | Specific (Brute, Bugger, Crawler, Elite, Engineer, Flood Pure Form, Grunt, Human, Jackal, Knight, Sentinel, Skirmisher); Boss (Tartarus) | yes |
| Hologram Cooldown | Specific (Skirmisher) | yes |
| Hologram Wait Time | Specific (Skirmisher) | yes |
| Hopping | Specific (Elite, Grunt, Jackal) | yes |
| Leader Leash | Specific (Brute, Crawler, Engineer, Grunt, Human, Jackal, Sentinel, Skirmisher) |  |
| Leap | Specific (Elite, Human, Jackal, Knight, Skirmisher) | yes |
| Movement Speed | Specific (Brute, Crawler, Elite, Flood Carrier Form, Flood Combat Form, Flood Infection Form, Flood Pure Form, Grunt, Human, Hunter, Jackal, Knight); Boss (Mule) | yes |
| Position Avoid Distance | Specific (Elite, Grunt, Hunter, Jackal, Sentinel) | yes |
| Search: Destroy Cover | Specific (Brute, Bugger, Crawler, Elite, Grunt, Human, Hunter, Jackal, Knight, Sentinel, Skirmisher) | yes |
| Search: Guard | Specific (Brute, Bugger, Crawler, Elite, Grunt, Human, Hunter, Jackal, Knight, Sentinel, Skirmisher, Watcher) | yes |
| Search: Investigate | Specific (Brute, Bugger, Crawler, Elite, Grunt, Human, Hunter, Jackal, Knight, Sentinel, Skirmisher, Watcher) | yes |
| Search: Leap On Cover | Specific (Brute, Bugger, Crawler, Elite, Grunt, Human, Hunter, Jackal, Knight, Skirmisher) | yes |
| Search: Suppressing Fire | Specific (Brute, Bugger, Crawler, Elite, Grunt, Human, Hunter, Jackal, Knight, Sentinel, Skirmisher, Watcher) | yes |
| Search: Uncover | Specific (Brute, Bugger, Crawler, Elite, Grunt, Human, Hunter, Jackal, Knight, Sentinel, Skirmisher, Watcher) | yes |
| Teleport | Specific (Knight) | yes |
| Thrust | Specific (Grunt) | yes |

## aggression (weight 1)

| name | offered to | new |
|---|---|---|
| Berserk Animation | Specific (Brute, Elite) | yes |
| Berserk Chance | Specific (Flood Combat Form) | yes |
| Berserk Cooldown | Specific (Brute, Hunter, Knight) | yes |
| Berserk Count | Specific (Brute, Flood Combat Form, Hunter, Knight) | yes |
| Berserk Distance | Specific (Flood Combat Form) | yes |
| Berserk Grenade | Specific (Flood Combat Form, Hunter) | yes |
| Berserk Perimeter Range | Specific (Hunter) | yes |
| Berserk Special Chances | Specific (Knight) | yes |
| Cower Time | Specific (Crawler, Engineer, Grunt, Human, Jackal, Skirmisher, Watcher) | yes |
| Elite Berserk | Specific (Elite) |  |
| Flee Time | Specific (Jackal) | yes |
| Flee Timeout | Specific (Crawler, Engineer, Grunt, Human, Jackal, Skirmisher, Watcher) | yes |
| General Cower Time | General | yes |
| General I am not scared | General | yes |
| General Melee Chance | General | yes |
| General Melee Delay | General | yes |
| General Melee Reach | General | yes |
| General Melee Timing | General | yes |
| General Player Preference | General | yes |
| General Retreat Chance | General | yes |
| General Surprise Behavior | General | yes |
| General Wildfire | General | yes |
| Grapple Melee | Hero (Sentinel Enforcer) |  |
| Hamstring | Specific (Crawler) | yes |
| Hamstring Angle | Specific (Crawler) | yes |
| Hamstring Distance | Specific (Crawler) | yes |
| Hamstring Time | Specific (Crawler) | yes |
| I am not scared | Specific (Brute, Bugger, Crawler, Elite, Engineer, Grunt, Human, Hunter, Jackal, Knight, Sentinel, Skirmisher) | yes |
| Leader Charge Chance | Specific (Brute) | yes |
| Leader Charge Range | Specific (Brute) | yes |
| Melee Chance | Specific (Brute, Bugger, Elite, Flood Carrier Form, Flood Combat Form, Flood Infection Form, Flood Pure Form, Human, Hunter, Knight); Boss (Tartarus); Hero (Brute Chieftain, Elite General, Elite Honor Guard, Elite Specops Commander, Elite Zealot, Knight Commander) | yes |
| Melee Leap Chance | Specific (Brute, Bugger, Flood Carrier Form, Flood Combat Form, Flood Infection Form, Knight); Boss (Tartarus) | yes |
| Melee Leap Range | Specific (Brute, Bugger, Flood Carrier Form, Flood Combat Form, Flood Infection Form, Knight); Boss (Tartarus); Hero (Brute Chieftain, Elite General, Elite Honor Guard, Elite Specops Commander, Elite Zealot, Knight Commander) | yes |
| Melee Leap Velocity | Specific (Brute, Bugger, Flood Carrier Form, Flood Combat Form, Flood Infection Form, Knight); Boss (Tartarus) | yes |
| Melee Radius | Specific (Brute, Bugger, Crawler, Elite, Flood Combat Form, Flood Infection Form, Human, Knight) | yes |
| Melee Timing | Specific (Brute, Bugger, Elite, Flood Carrier Form, Flood Combat Form, Flood Infection Form, Flood Pure Form, Human, Hunter, Knight); Boss (Tartarus); Hero (Brute Chieftain, Elite General, Elite Honor Guard, Elite Specops Commander, Elite Zealot, Knight Commander) | yes |
| Panic Chance | Specific (Jackal) | yes |
| Retreat Chance | Specific (Crawler, Engineer, Grunt, Human, Jackal, Skirmisher) | yes |
| Shield-Down Berserk Chance | Specific (Brute) | yes |
| Shield-Down Berserk Range | Specific (Brute) | yes |
| Suppress | Specific (Brute, Bugger, Elite, Engineer, Flood Pure Form, Grunt, Human, Hunter, Jackal, Knight, Sentinel) | yes |
| Vengeful Berserk | Specific (Brute) | yes |

## equipment (weight 1)

| name | offered to | new |
|---|---|---|
| Arm Shield | Specific (Jackal, Skirmisher) | yes |
| Equipment Use Chance | Specific (Brute) |  |
| Shield Projection | Specific (Watcher) | yes |
| Shield Projector Duration | Specific (Watcher) | yes |
| Shield Projector Recharge | Specific (Watcher) | yes |
| Shield Use Recent Damage | Specific (Brute) | yes |
| Shield Use Vitality | Specific (Brute) | yes |

## senses (weight 1)

| name | offered to | new |
|---|---|---|
| General Hearing Distance | General |  |
| General Perception | General |  |
| General Peripheral Vision | General | yes |
| General Vision | General |  |
| Hearing Distance | Specific (Elite, Flood Carrier Form, Flood Combat Form, Flood Infection Form, Flood Pure Form, Grunt, Human, Hunter, Jackal, Sentinel) |  |
| Perception | Specific (Elite, Flood Carrier Form, Flood Combat Form, Flood Infection Form, Flood Pure Form, Grunt, Human, Hunter, Jackal, Sentinel) |  |
| Peripheral Vision | Specific (Elite, Flood Carrier Form, Flood Combat Form, Flood Infection Form, Flood Pure Form, Grunt, Human, Hunter, Jackal, Sentinel) | yes |
| Search | Specific (Brute, Bugger, Crawler, Elite, Engineer, Flood Carrier Form, Flood Combat Form, Flood Pure Form, Grunt, Human, Hunter, Jackal, Knight, Sentinel, Skirmisher, Watcher) | yes |
| Suicide Sensing Distance | Specific (Flood Carrier Form) |  |
| Vision | Specific (Elite, Flood Carrier Form, Flood Combat Form, Flood Infection Form, Flood Pure Form, Grunt, Human, Hunter, Jackal, Sentinel) |  |

## Choices made where the plan rules overlapped

| names | category | why |
|---|---|---|
| Melee Leap Range / Velocity, Melee Radius, Melee Reach, Berserk Distance / Perimeter Range, Leader Charge Range, Hamstring Distance | aggression | the Melee* / Berserk* / Charge* rule before the *Range / *Distance rule: how far they come at you is still aggression |
| Grenade Range / Velocity / Collateral, Grenade Catch Range | grenades | Grenade* before *Range / *Velocity |
| Shield Boost Period / Radius / Strength (Engineer) | durability | the plan proposed equipment; the existing bare "Shield Boost" card is durability (2026-08-10), so the three knobs follow it -- a choice to review |
| Shield Use Recent Damage / Vitality (Brute) | equipment | when a Brute deploys its shield equipment, not a shield of its own |
| Shield-Down Berserk Chance / Range | aggression | Berserk* before Shield*: berserking when the shield drops |
| Spew Chance / Frequency, Run Time (Flood) | rate_of_fire | the Spew* / Run Time rule, not the Flood-forms rule |
| Stalk Charge / Range, Morph Distance, Ranged Distance, Throttle Distance (Pure Form) | flood_forms | the form knobs; Morph Damage and Distance Damage Radius / Time go with damage / range / rate of fire by their words |
| Death Height, Death Detonation Time (Engineer) | damage | the existing "Death" card (its corpse detonates) is damage |
| Gravity Jump * (Knight Commander), Gravity Throne Acceleration / Speed / Turn, Enforcer Chassis Acceleration / Speed / Turn | positioning | movement knobs, like Hopping / Thrust / Flight*; the bare "Gravity Throne" and "Enforcer Chassis" cards keep their 2026-08-10 categories |
| Position Avoid Distance, Combat / Guard Position Time | positioning | Position* before *Distance |
| Crouch Chance | positioning | not in the plan rules; a stance, not an attack |
| Resurrection, Turret Vitality (Watcher) | durability | enemies staying alive |
| Shard Spawning (Watcher) | ranks | more enemies, like Spawn Count |
| Hamstring, Hamstring Angle / Time (Crawler) | aggression | an attack behaviour |
| Head Gun Accuracy / Damage / Rate of Fire, Turret Damage / Rate of Fire | accuracy / damage / rate_of_fire | by their last words |
| Fight Circle Angles / Strafe Time | positioning | Fight Circle Firing Time is rate of fire |

## Boss and hero buckets (scoredb.xml rows)

| card group | scoredb (class, type) | stock rows |
|---|---|---|
| 343 Guilty Spark | none (not a scored kill) |  |
| Brute Chieftain | ('hero', 'brute') | Brute Chieftan 150 |
| Elite General | ('leader', 'elite') | Elite Zealot 75, Prophet 150 |
| Elite Honor Guard | ('hero', 'elite') | Elite Honor Guard 150 |
| Elite Specops Commander | ('leader', 'elite') | Elite Zealot 75, Prophet 150 |
| Elite Zealot | ('leader', 'elite') | Elite Zealot 75, Prophet 150 |
| Grunt Ultra | ('specialist', 'grunt') | Grunt Ranger 15 |
| Heretic Leader | ('leader', 'elite') | Elite Zealot 75, Prophet 150 |
| Jackal Ranger | ('specialist', 'jackel') | Jackal Sniper 20 |
| Jackal Sniper | ('specialist', 'jackel') | Jackal Sniper 20 |
| Knight Commander | ('leader', 'knight') | Knight Commander 150 |
| Mule | ('infantry', 'mule') | Mule 200 |
| Prophet Regret | ('leader', 'elite') | Elite Zealot 75, Prophet 150 |
| Sentinel Enforcer | ('*', 'sentinel') |  |
| Tartarus | ('hero', 'brute') | Brute Chieftan 150 |

