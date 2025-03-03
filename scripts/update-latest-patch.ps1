# Path to the file you want to update
$initFile = "awpy\data\__init__.py"

# Read the file contents once.
$contents = Get-Content $initFile -Raw

# Extract the current build id using a regex.
$currentBuildIdMatch = [regex]::Match($contents, 'CURRENT_BUILD_ID\s*=\s*(\d+)')
if ($currentBuildIdMatch.Success -and $currentBuildIdMatch.Groups[1].Value -eq $env:LATEST_PATCH_ID) {
    # If the build ids are the same, no update is needed.
    Write-Output $false
    exit
}

# Update the CURRENT_BUILD_ID line.
$contents = $contents -replace 'CURRENT_BUILD_ID\s*=\s*\d+', "CURRENT_BUILD_ID = $env:LATEST_PATCH_ID"

# Define the new patch entry as a multiline string.
$newPatch = @"
    ${env:LATEST_PATCH_ID}: {
        "url": "https://steamdb.info/patchnotes/${env:LATEST_PATCH_ID}/",
        "datetime": datetime.datetime.fromtimestamp(${env:LATEST_PATCH_TIMESTAMP}, datetime.UTC),
        "available": POSSIBLE_ARTIFACTS
    }
"@.Trim()

# Insert the new patch entry into the AVAILABLE_PATCHES dictionary.
$pattern = '(?s)(AVAILABLE_PATCHES\s*=\s*\{)(.*?)(\})'
$contents = [regex]::Replace($contents, $pattern, {
    param($match)
    # If the patch key already exists, return the original match.
    if ($match.Groups[2].Value -match ${env:LATEST_PATCH_ID}) {
        return $match.Value
    } else {
        # Always add the new patch first, followed by existing content (if any)
        $existingContent = $match.Groups[2].Value.Trim()
        if ($existingContent -eq "") {
            $insert = "`n$newPatch`n"
        } else {
            $insert = "`n$newPatch,`n$existingContent"
        }
        return $match.Groups[1].Value + $insert + $match.Groups[3].Value
    }
})

# Write the updated content back to the file.
Set-Content $initFile -Value $contents

# Return true to indicate a change was made.
Write-Output $true