# Path to the file you want to update
$initFile = "awpy\data\__init__.py"

# 1. Update the CURRENT_BUILD_ID line.
(Get-Content $initFile) -replace 'CURRENT_BUILD_ID\s*=\s*\d+', "CURRENT_BUILD_ID = $env:latestPatchId" | Set-Content $initFile

# 2. Define the new patch entry as a multiline string.
$newPatch = @"
    $env:latestPatchId: {
        "url": "https://steamdb.info/patchnotes/$env:latestPatchId/",
        "datetime": datetime.datetime.fromtimestamp($env:latestPatchTimestamp, datetime.UTC),
        "available": POSSIBLE_ARTIFACTS,
    },
"@.Trim()

# 3. Insert the new patch entry into the AVAILABLE_PATCHES dictionary.
#    This regex finds the block starting with AVAILABLE_PATCHES = { and ending with the matching closing brace.
$contents = Get-Content $initFile -Raw
$pattern = '(?s)(AVAILABLE_PATCHES\s*=\s*\{)(.*?)(\n\})'

# Initialize a flag to track if an update was made.
$patchUpdated = $false

$contentsUpdated = [regex]::Replace($contents, $pattern, {
    param($match)
    # If the patch key already exists, don't add it again.
    if ($match.Groups[2].Value -match $env:latestPatchId) {
        return $match.Value
    } else {
        $patchUpdated = $true
        # Insert the new patch entry before the closing brace.
        return $match.Groups[1].Value + $match.Groups[2].Value + "`n$newPatch" + $match.Groups[3].Value
    }
})
Set-Content $initFile -Value $contentsUpdated

# Return true if patch was updated, false otherwise.
if ($patchUpdated) {
    Write-Output $true
} else {
    Write-Output $false
}