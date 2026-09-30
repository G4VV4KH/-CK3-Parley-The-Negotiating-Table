# Shared, read-only MCA 3.1 check of the CK3 1.20 frozen GUI contract.
# Historical 2.2 and 2.3 artifacts are retained.
# The adjacent reviewed manifest pins BOTH vanilla and the functional patch.
# Updating MCA alone cannot bless itself: upstream, patch, and rebuilt result
# must all match the reviewed contract. No fuzzy patching or token stripping.
$script:McaFrozenContractDirectory = $PSScriptRoot

function Get-McaFrozenTextHash([string[]]$Lines) {
    $bytes = [System.Text.Encoding]::UTF8.GetBytes(($Lines -join "`n"))
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try { return ([System.BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '') }
    finally { $sha.Dispose() }
}

function Restore-McaFrozenPatch([string[]]$Baseline, [string[]]$Patch) {
    $result = New-Object System.Collections.Generic.List[string]
    $cursor = 0
    $hunks = 0
    $fileHeaders = @($Patch | Where-Object { $_ -match '^--- ' }).Count
    if ($fileHeaders -ne 1) { throw "Reviewed patch must contain exactly one file; found $fileHeaders." }
    for ($i = 0; $i -lt $Patch.Count; $i++) {
        if ($Patch[$i] -notmatch '^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@') { continue }
        $oldStart = [int]$Matches[1]
        $oldCount = 1
        if ($Matches.ContainsKey(2) -and $Matches[2] -ne '') { $oldCount = [int]$Matches[2] }
        $newStart = [int]$Matches[3]
        $newCount = 1
        if ($Matches.ContainsKey(4) -and $Matches[4] -ne '') { $newCount = [int]$Matches[4] }
        $start = [Math]::Max(0, $oldStart - 1)
        if ($oldCount -eq 0) { $start = $oldStart }
        if ($start -lt $cursor -or $start -gt $Baseline.Count) { throw "Patch hunk $($hunks + 1) has invalid or overlapping baseline offset $oldStart." }
        while ($cursor -lt $start) { $result.Add($Baseline[$cursor]); $cursor++ }
        $expectedNewStart = [Math]::Max(0, $newStart - 1)
        if ($newCount -eq 0) { $expectedNewStart = $newStart }
        if ($result.Count -ne $expectedNewStart) { throw "Patch hunk $($hunks + 1) output offset does not match its header." }
        $oldSeen = 0
        $newSeen = 0
        $i++
        while ($i -lt $Patch.Count -and $Patch[$i] -notmatch '^@@ ') {
            $line = $Patch[$i]
            if ($line -eq '\ No newline at end of file') { $i++; continue }
            if ($line.Length -eq 0) { throw "Unprefixed empty line in patch at $($i + 1)." }
            $kind = $line.Substring(0, 1)
            $payload = $line.Substring(1)
            if ($kind -eq ' ' -or $kind -eq '-') {
                if ($cursor -ge $Baseline.Count -or $Baseline[$cursor] -cne $payload) {
                    throw "Reviewed patch context/deletion mismatch at vanilla line $($cursor + 1). Rebase and review upstream drift."
                }
                $cursor++
                $oldSeen++
            }
            if ($kind -eq ' ' -or $kind -eq '+') { $result.Add($payload); $newSeen++ }
            if ($kind -notin @(' ', '-', '+')) { throw "Unsupported patch row at $($i + 1)." }
            $i++
        }
        $i--
        if ($oldSeen -ne $oldCount -or $newSeen -ne $newCount) { throw "Patch hunk count mismatch: old $oldSeen/$oldCount; new $newSeen/$newCount." }
        $hunks++
    }
    if ($hunks -eq 0) { throw 'Reviewed patch has no hunks.' }
    while ($cursor -lt $Baseline.Count) { $result.Add($Baseline[$cursor]); $cursor++ }
    return ,$result.ToArray()
}

function Measure-McaMarriageCopy([string]$copyPath, [string]$upPath) {
    $errors = New-Object System.Collections.Generic.List[string]
    $sites = New-Object System.Collections.Generic.List[int]
    $tokens = 0
    $firstDiff = 0
    $copyLines = @()
    $upLines = @()
    $upHash = ''
    $copyHash = ''
    $patchHash = ''
    $expectedLines = @()
    try {
        $manifestPath = Join-Path $script:McaFrozenContractDirectory 'tnt_mca_31_marriage_contract.json'
        $manifest = [System.IO.File]::ReadAllText($manifestPath) | ConvertFrom-Json
        if ($manifest.format -cne 'mca-frozen-patch-v1' -or $manifest.normalization -cne 'ReadAllLines joined with LF, no final LF') {
            throw 'Unsupported frozen manifest format/normalization.'
        }
        if ([System.IO.Path]::GetFileName([string]$manifest.patch_file) -cne [string]$manifest.patch_file) { throw 'Patch manifest must name a sibling artifact, not an external path.' }
        $descriptorPath = Join-Path (Split-Path (Split-Path $copyPath -Parent) -Parent) 'descriptor.mod'
        $descriptorText = [System.IO.File]::ReadAllText($descriptorPath)
        $requiredSupported = [regex]::Escape([string]$manifest.required_supported_version)
        if ($descriptorText -notmatch ('(?m)^supported_version\s*=\s*"' + $requiredSupported + '"\s*$')) {
            throw 'MCA 3.1 frozen GUI requires the reviewed CK3 1.20.* descriptor; a current GUI hash cannot bless older metadata.'
        }
        $patchPath = Join-Path $script:McaFrozenContractDirectory $manifest.patch_file
        $copyLines = [System.IO.File]::ReadAllLines($copyPath)
        $upLines = [System.IO.File]::ReadAllLines($upPath)
        $patchLines = [System.IO.File]::ReadAllLines($patchPath)
        $upHash = Get-McaFrozenTextHash $upLines
        $copyHash = Get-McaFrozenTextHash $copyLines
        $patchHash = Get-McaFrozenTextHash $patchLines
        if ($upHash -cne $manifest.vanilla_sha256) { $errors.Add("Vanilla baseline drift: actual $upHash; reviewed $($manifest.vanilla_sha256). Review upstream and regenerate the functional patch explicitly.") }
        if ($patchHash -cne $manifest.patch_sha256) { $errors.Add("Approved patch artifact drift: actual $patchHash; reviewed $($manifest.patch_sha256). Do not auto-bless the current MCA file.") }
        if ($errors.Count -eq 0) {
            $expectedLines = Restore-McaFrozenPatch $upLines $patchLines
            $rebuiltHash = Get-McaFrozenTextHash $expectedLines
            if ($rebuiltHash -cne $manifest.mca_sha256) { $errors.Add("Reviewed patch rebuild hash $rebuiltHash differs from manifest $($manifest.mca_sha256). Contract artifacts are inconsistent.") }
            $length = [Math]::Min($expectedLines.Count, $copyLines.Count)
            for ($i = 0; $i -lt $length; $i++) {
                if ($expectedLines[$i] -cne $copyLines[$i]) { $firstDiff = $i + 1; break }
            }
            if ($firstDiff -eq 0 -and $expectedLines.Count -ne $copyLines.Count) { $firstDiff = $length + 1 }
            if ($firstDiff -ne 0 -or $copyHash -cne $manifest.mca_sha256) {
                $errors.Add("MCA functional patch drift at line $firstDiff; expected/current lines $($expectedLines.Count)/$($copyLines.Count). Review the change against the approved patch.")
            }
        }
        for ($i = 0; $i -lt $copyLines.Count; $i++) {
            $line = $copyLines[$i]
            # Derived identifiers occur outside strings. Remove strings before comments.
            $active = [regex]::Replace($line, '"[^"]*"', '""')
            $comment = $active.IndexOf('#')
            if ($comment -ge 0) { $active = $active.Substring(0, $comment) }
            $tokens += [regex]::Matches($active, '\btnt_ma_widget_character_list_item\b').Count
            if ($active -match '^\s*tnt_ma_widget_character_list_item\s*=\s*\{\s*$') { $sites.Add($i + 1) }
        }
        if ($sites.Count -ne 3 -or $tokens -ne 3) { $errors.Add("Derived row sites/tokens $($sites.Count)/$tokens; expected exactly 3/3.") }
    }
    catch { $errors.Add($_.Exception.Message) }
    return [pscustomobject]@{
        Passed = ($errors.Count -eq 0)
        Errors = $errors.ToArray()
        Sites = $sites.ToArray()
        Tokens = $tokens
        FirstDiff = $firstDiff
        CopyCount = $copyLines.Count
        UpCount = $upLines.Count
        ExpectedCount = $expectedLines.Count
        UpstreamHash = $upHash
        CopyHash = $copyHash
        PatchHash = $patchHash
    }
}
