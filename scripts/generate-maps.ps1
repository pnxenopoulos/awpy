# Note: On Windows you must keep the .dll from the .zip in the same directory as the .exe
param(
    [Parameter(Mandatory=$false)]
    [string]$inputPath = "C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\game\csgo",

    [Parameter(Mandatory=$false)]
    [string]$outputPath = "."
)

$env:PYTHONUTF8 = "1"
$generalInputPath = Join-Path $inputPath "pak01_dir.vpk"
$mapsInputPath = Join-Path $inputPath "maps"
$inputPathWithoutCsgo = Split-Path $inputPath -Parent
$communityAddonsPath = Join-Path $inputPathWithoutCsgo "csgo_community_addons"

# Define the fixed command and filters
$exePath = ".\Source2Viewer-CLI.exe"
$folderFilter = "panorama/images/overheadmaps/"
$resourceFolder = "resource/overviews/"
$extensionFilter = "vtex_c"

# Generate map data
Write-Host "Generating general map data"  -ForegroundColor Green
Write-Host "& `"$exePath`" -i `"$generalInputPath`" -f `"$resourceFolder`" -e `"txt`" -o `"$outputPath`" -d" -ForegroundColor Cyan
& $exePath -i $generalInputPath -f $resourceFolder -e "txt" -o $outputPath -d


# Run the command to extract the radar files
Write-Host "Extracting general radar files"  -ForegroundColor Green
Write-Host "& `"$exePath`" -i `"$generalInputPath`" -f `"$folderFilter`" -e `"$extensionFilter`" -o `"$outputPath`" -d" -ForegroundColor Cyan
& $exePath -i $generalInputPath -f $folderFilter -e $extensionFilter -o $outputPath -d

# Generate image and overview for all extra maps
Get-ChildItem -Path $mapsInputPath -Filter "*.vpk" | Where-Object {
    $_.Name -notlike "*_preview*" -and $_.Name -notlike "*_vanity*" -and $_.Name -notlike "*lobby_*"  -and $_.Name -notlike "*graphics_*"
} | ForEach-Object {
    $filePath = $_.FullName
    $fileNameWithoutExtension = $_.BaseName

    Write-Host "Processing file: $filePath" -ForegroundColor Green

    Write-Host "& `"$exePath`" -i `"$filePath`" -f `"$folderFilter`" -e `"$extensionFilter`" -o `"$outputPath`" -d" -ForegroundColor Cyan
    & $exePath -i $filePath -f $folderFilter -e $extensionFilter -o $outputPath -d
    # Extract the map data
    Write-Host "& `"$exePath`" -i `"$filePath`" -f `"$resourceFolder`" -e `"txt`" -o `"$outputPath`" -d" -ForegroundColor Cyan
    & $exePath -i $filePath -f $resourceFolder -e "txt" -o $outputPath -d
}

# Generate image and overview for all extra maps in csgo_community_addons
Get-ChildItem -Path $communityAddonsPath -Directory | ForEach-Object {
    $subdir = $_.FullName
    Get-ChildItem -Path $subdir -Filter "*_dir.vpk" | Where-Object {
        $_.Name -notlike "*_preview*" -and $_.Name -notlike "*_vanity*" -and $_.Name -notlike "*lobby_*" -and $_.Name -notlike "*graphics_*"
    } | ForEach-Object {
        $filePath = $_.FullName
        $fileNameWithoutExtension = $_.BaseName

        Write-Host "Processing file: $filePath" -ForegroundColor Green

        # Generate the overview image
        Write-Host "& `"$exePath`" -i `"$filePath`" -f `"$folderFilter`" -e `"$extensionFilter`" -o `"$outputPath`" -d" -ForegroundColor Cyan
        & $exePath -i $filePath -f $folderFilter -e $extensionFilter -o $outputPath -d
        # Extract the map data
        Write-Host "& `"$exePath`" -i `"$filePath`" -f `"$resourceFolder`" -e `"txt`" -o `"$outputPath`" -d" -ForegroundColor Cyan
        & $exePath -i $filePath -f $resourceFolder -e "txt" -o $outputPath -d
    }
}



# Define the source directory (where the extracted files are)
$sourceDir = Join-Path $outputPath $folderFilter

# Define the target directory for the renamed files ("maps")
$targetDir = Join-Path $outputPath "maps"

# If the target directory doesn't exist, create it.
if (-not (Test-Path $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir | Out-Null
}

$seenNames = @{}
# Check if the source directory exists before processing.
if (Test-Path $sourceDir) {
    # Process each file ending with "_radar_psd.png"
    Get-ChildItem -Path $sourceDir -Filter "*.png" | Where-Object {
        $_.Name -match "_radar_psd\.png$|_radar_tga\.png$"
    } | ForEach-Object {
        # Skip files with undesired substrings.
        if ($_.Name -like "*_preview*" -or $_.Name -like "*_vanity*") {
            return
        }
        # Define the new file name by replacing "_radar_psd.png" with ".png"
        $newFileName = $_.Name -replace "_radar_psd\.png$|_radar_tga\.png$", ".png"

        # Skip if already processed in this run
        if ($seenNames.ContainsKey($newFileName)) {
            Write-Host "Skipping rename: $newFileName already processed in this run" -ForegroundColor DarkYellow
            return
        }

        $seenNames[$newFileName] = $true

        Write-Host "Renaming file: $($_.Name) to $newFileName" -ForegroundColor Yellow
        Rename-Item -Path $_.FullName -NewName $newFileName

        # Define full paths for the renamed file and its destination.
        $currentPath = Join-Path $sourceDir $newFileName
        $destinationPath = Join-Path $targetDir $newFileName

        Write-Host "Moving file: $currentPath" -ForegroundColor Green
        Write-Host "To: $destinationPath" -ForegroundColor Green

        # Move the file to the target directory.
        Move-Item -Path $currentPath -Destination $destinationPath -Force
    }

    # Optionally, remove the 'panorama' folder if it's no longer needed.
    $panoramaPath = Join-Path $outputPath "panorama"
    if (Test-Path $panoramaPath) {
        Remove-Item -Path $panoramaPath -Recurse -Force
    }
} else {
    Write-Host "Source directory '$sourceDir' does not exist." -ForegroundColor Red
    exit
}

# Combine map data into a single JSON file.
$tempOutputDir = Join-Path -Path $outputPath -ChildPath $resourceFolder
uv run awpy mapdata $tempOutputDir
Move-Item -Path "map-data.json" -Destination $targetDir -Force


# Create a zip archive of the final files in the target directory.
$zipPath = Join-Path $outputPath "maps.zip"
Compress-Archive -Path (Join-Path $targetDir "*") -DestinationPath $zipPath -Force
Write-Host "Zip archive created at: $zipPath" -ForegroundColor Cyan

# Compute and print the hash of the zip archive using SHA256.
$fileHash = Get-FileHash -Path $zipPath -Algorithm SHA256
Write-Host "Zip file hash (SHA256): $($fileHash.Hash)" -ForegroundColor Cyan
