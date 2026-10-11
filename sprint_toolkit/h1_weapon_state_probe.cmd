@echo off
rem Held / dropped weapon live probe (h1_weapon_state_probe.py), read-only. Start it in a Halo 1
rem level while holding the weapon; it logs for 120 s (or until a dropped weapon has been still
rem for 3 s) to out\weapon_state_probe.jsonl:
rem   h1_weapon_state_probe.cmd "note"
rem Run elevated if it says OpenProcess failed. No parenthesised blocks: "(x86)" in the path.
setlocal
python "%~dp0h1_weapon_state_probe.py" --seconds 120 --note "%~1"
pause
