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
# STATUS: DOES NOT WORK against the H3ODSTEK build. Both Start() overloads throw
# NotImplementedException, and while InitializeProject(TagsOnly, root) returns fine,
# the next TagFile.Load kills the process natively -- no .NET exception, the script
# just stops. Interactively it shows "Assert hit ... result < 1ull << 32".
# Untried lead: ManagedBlamSystem.kVirtualToPhysicalBaseOffset, since the assert is
# about a value not fitting in 32 bits. Until that is cracked, edit the scenario in
# Guerilla instead; the rebuild half of the pipeline works fine.
#
# Two sub-problems ARE solved here and are worth keeping: the crash callback has to be
# a real delegate (Windows PowerShell 5.1 cannot make one from a scriptblock, hence the
# C# via Add-Type), and managedblam must be bound with an AssemblyResolve handler
# because .NET resolves it against the host's directory, not the kit's.
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
    [string]$Filter = '',
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

    // This build does not implement every entry point: the three-argument Start throws
    // NotImplementedException, and InitializeProject on its own asserts
    // "result < 1ull << 32". So try them in order and report which one takes, rather
    // than assuming.
    public static string Start(string projectRoot)
    {
        if (started) return "already started";
        var log = new StringBuilder();
        var cb = new ManagedBlamCrashCallback(OnCrash);

        try
        {
            var p = new ManagedBlamStartupParameters();
            p.InitializationLevel = InitializationType.TagsOnly;
            ManagedBlamSystem.Start(projectRoot, cb, p);
            started = true;
            return "started via Start(root, callback, parameters)";
        }
        catch (Exception e) { log.AppendLine("   Start(root,cb,params): " + e.GetType().Name); }

        try
        {
            ManagedBlamSystem.Start(projectRoot, cb);
            started = true;
            return log + "started via Start(root, callback)";
        }
        catch (Exception e) { log.AppendLine("   Start(root,cb): " + e.GetType().Name); }

        // Both Start overloads are NotImplemented in the H3ODSTEK build, so
        // InitializeProject is the real entry point -- and it pops a modal
        // "Assert hit ... result < 1ull << 32" dialog. Click OK, then decline the
        // debugger, and it carries on. Nothing is written by a read action.
        ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly, projectRoot);
        started = true;
        return log + "started via InitializeProject(TagsOnly, root)";
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
        var tp = TagPath.FromPathAndType(scenario, "scnr*");
        sb.AppendLine("   tagpath   : " + tp.RelativePathWithExtension);
        sb.AppendLine("   accessible: " + tp.IsTagFileAccessible());
        var f = Open(scenario);
        try
        {
            sb.AppendLine("   file.Fields: " + (f.Fields == null ? "null" : f.Fields.Length.ToString()));
            sb.AppendLine("   root       : " + (f.Root == null ? "null" : "ok"));
            if (f.Root != null)
                sb.AppendLine("   root.Fields: " + (f.Root.Fields == null ? "null" : f.Root.Fields.Length.ToString()));
            foreach (var fld in (f.Root != null ? f.Root.Fields : f.Fields))
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

# The C# compiled below references managedblam by display name, and .NET resolves that
# against the host's directory -- PowerShell's -- not the kit's. PATH does not affect
# assembly resolution, so bind it explicitly or Start() fails with
# "Could not load file or assembly 'managedblam'".
[Reflection.Assembly]::LoadFrom($dll) | Out-Null
$resolver = [System.ResolveEventHandler] {
    param($sender, $e)
    if ($e.Name -like 'managedblam*') { return [Reflection.Assembly]::LoadFrom($script:dll) }
    return $null
}
[AppDomain]::CurrentDomain.add_AssemblyResolve($resolver)

Add-Type -TypeDefinition $source -ReferencedAssemblies $dll -Language CSharp | Out-Null
Write-Output ([MBScenario]::Start($EK))

Write-Output "-- running action '$Action' on '$Scenario' --"
try {
switch ($Action) {
    'fields' { Write-Output ([MBScenario]::Fields($Scenario, $Filter)) }
    'list'   { Write-Output ([MBScenario]::List($Scenario, $Block)) }
    'add'    { Write-Output ([MBScenario]::Add($Scenario, $Block, $Entries, $Type)) }
}
} catch { Write-Output ('ACTION FAILED: ' + $_.Exception.GetType().Name + ': ' + $_.Exception.Message) }
