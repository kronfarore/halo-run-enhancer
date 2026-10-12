@echo off
rem Projectile live probe (h1_projectile_probe.py), read-only. Start it in a Halo 1 level, then
rem fire: every projectile is logged from creation to detonation for 120 s to
rem out\projectile_probe.jsonl:
rem   h1_projectile_probe.cmd "note"
rem Run elevated if it says OpenProcess failed. No parenthesised blocks: "(x86)" in the path.
setlocal
python "%~dp0h1_projectile_probe.py" --seconds 120 --note "%~1"
pause
