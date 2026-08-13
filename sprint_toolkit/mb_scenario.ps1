# ManagedBlam driver for editing ODST scenario tags headlessly.
#
# Adding a weapon ODST cut -- battle_rifle, plasma_rifle, energy_blade -- cannot be
# done by patching a built map: those tags are absent from the map's tag set entirely,
# so no residency bit and no segment import reaches them. They DO exist in the Editing
# Kit's tag source, so the route is to add them to the scenario's weapon palette and
# rebuild, which makes tool.exe pull in the tags AND their resources.
#
# Guerilla is a GUI, so this drives Bungie's own ManagedBlam API instead.
#
# INITIALISATION MATTERS. Calling ManagedBlamSystem.InitializeProject() on its own
# crashes with "Assert hit ... result < 1ull << 32" -- its memory system is never
# configured. The working sequence is Start(projectRoot, crashCallback, parameters)
# with InitializationLevel = TagsOnly. The callback is a real delegate, which Windows
# PowerShell 5.1 cannot build from a scriptblock, so the work is done in C# compiled
# by Add-Type and this file is only a thin wrapper.
#
#   powershell -File mb_scenario.ps1 -Action fields -Scenario levels\atlas\sc150\sc150
#   powershell -File mb_scenario.ps1 -Action list   -Scenario ... -Block "weapon palette"
#   powershell -File mb_scenario.ps1 -Action add    -Scenario ... -Block "weapon palette" `
#              -Entries "objects\weapons\rifle\battle_rifle\battle_rifle"
param(
    [Parameter(Mandatory=$true)][ValidateSet('fields','list','add')][string]$Action,
    [Parameter(Mandatory=$true)][string]$Scenario,
    [string]$Block = 'weapon palette',
    [string[]]$Entries = @(),
    [string]$Type = 'weap',
    [string]$EK = 'C:\Program Files (x86)\Steam\steamapps\common\H3ODSTEK'
)

$ErrorActionPreference = 'Stop'
$dll = Join-Path $EK 'bin\ManagedBlam.dll'
if (-not (Test-Path $dll)) { throw "ManagedBlam not found at $dll" }

# Native dependencies sit next to the dll, so run from the kit's own directory.
Set-Location $EK
$env:PATH = (Join-Path $EK 'bin') + ';' + $env:PATH

$source = @'
using System;
using System.Collections.Generic;
using System.Text;
using Bungie;
using Bungie.Tags;

public static class MBScenario
{
    static bool started;

    static void OnCrash(ManagedBlamCrashInfo info)
    {
        Console.WriteLine("   ManagedBlam crash callback: " + info);
    }

    public static void Start(string projectRoot)
    {
        if (started) return;
        var p = new ManagedBlamStartupParameters();
        p.InitializationLevel = InitializationType.TagsOnly;
        ManagedBlamSystem.Start(projectRoot, new ManagedBlamCrashCallback(OnCrash), p);
        started = true;
    }

    static TagFile Open(string scenario)
    {
        var path = TagPath.FromPathAndType(scenario, "scnr*");
        var f = new TagFile();
        f.Load(path);
        return f;
    }

    public static string Fields(string scenario, string filter)
    {
        var sb = new StringBuilder();
        var f = Open(scenario);
        try
        {
            foreach (var fld in f.Root.Fields)
            {
                var n = fld.FieldName ?? "";
                if (filter.Length == 0 || n.ToLower().Contains(filter.ToLower()))
                    sb.AppendLine("   " + n + "   <" + fld.GetType().Name + ">");
            }
        }
        finally { f.Dispose(); }
        return sb.ToString();
    }

    public static string List(string scenario, string block)
    {
        var sb = new StringBuilder();
        var f = Open(scenario);
        try
        {
            var blk = (TagFieldBlock)f.SelectField("Block:" + block);
            sb.AppendLine("   " + block + ": " + blk.Elements.Count + " element(s)");
            foreach (var el in blk.Elements)
            {
                var r = el.SelectField("Reference:name") as TagFieldReference;
                sb.AppendLine("   [" + el.ElementIndex + "] " +
                    (r != null && r.Path != null ? r.Path.RelativePath : "(none)"));
            }
        }
        finally { f.Dispose(); }
        return sb.ToString();
    }

    public static string Add(string scenario, string block, string[] entries, string type)
    {
        var sb = new StringBuilder();
        var f = Open(scenario);
        try
        {
            var blk = (TagFieldBlock)f.SelectField("Block:" + block);
            var have = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var el in blk.Elements)
            {
                var r = el.SelectField("Reference:name") as TagFieldReference;
                if (r != null && r.Path != null) have.Add(r.Path.RelativePath);
            }
            int added = 0;
            foreach (var e in entries)
            {
                if (have.Contains(e)) { sb.AppendLine("   already present: " + e); continue; }
                var el = blk.AddElement();
                var r = (TagFieldReference)el.SelectField("Reference:name");
                r.Path = TagPath.FromPathAndType(e, type + "*");
                sb.AppendLine("   added [" + el.ElementIndex + "] " + e);
                added++;
            }
            if (added > 0) { f.Save(); sb.AppendLine("   SAVED " + scenario + " (" + added + " added)"); }
            else sb.AppendLine("   nothing to do");
        }
        finally { f.Dispose(); }
        return sb.ToString();
    }
}
'@

Add-Type -TypeDefinition $source -ReferencedAssemblies $dll -Language CSharp | Out-Null
[MBScenario]::Start($EK)

switch ($Action) {
    'fields' { Write-Output ([MBScenario]::Fields($Scenario, 'palette')) }
    'list'   { Write-Output ([MBScenario]::List($Scenario, $Block)) }
    'add'    { Write-Output ([MBScenario]::Add($Scenario, $Block, $Entries, $Type)) }
}
