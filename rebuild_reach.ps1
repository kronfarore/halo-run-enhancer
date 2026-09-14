# rebuild_reach.ps1 -- rebuild every Reach campaign map with the HREK and finish the
# recipe: build, install, residency fix, pool-cache warm, publish the baseline.
# Roughly an hour; builds have long silent stretches and look hung when they are not.
#
# Run from anywhere:
#     powershell -ExecutionPolicy Bypass -File rebuild_reach.ps1
#     powershell -ExecutionPolicy Bypass -File rebuild_reach.ps1 m20,m45   # just these
#
# Close MCC first (or at least stay out of Reach): a map the game has loaded cannot
# be replaced. Everything is logged to rebuild_reach.log next to this script.

param([string]$Maps = '')

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\python.exe'
$log = Join-Path $here 'rebuild_reach.log'
$env:PYTHONUNBUFFERED = '1'
$env:QT_QPA_PLATFORM = 'offscreen'

$toolArgs = @((Join-Path $here 'sprint_toolkit\reach_ek_build.py'), '--all')
if ($Maps) { $toolArgs += @('--maps', $Maps) }

"==== rebuild_reach started $(Get-Date -Format s) ($(if ($Maps) { $Maps } else { 'all maps' }))" |
    Tee-Object -FilePath $log
& $py @toolArgs 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
$code = $LASTEXITCODE
"==== finished $(Get-Date -Format s), exit code $code" | Tee-Object -FilePath $log -Append

# The standing residency check, so a rebuild that left anything half-loaded says so.
& $py (Join-Path $here 'sprint_toolkit\reach_pools.py') --audit 2>&1 |
    ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
exit $code
