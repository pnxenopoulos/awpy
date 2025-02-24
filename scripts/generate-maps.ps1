# Note: On Windows you must keep the .dll from the .zip in the same directory as the .exe
param(
    [Parameter(Mandatory=$false)]
    [string]$inputPath = "C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\game\csgo\pak01_dir.vpk",

    [Parameter(Mandatory=$false)]
    [string]$outputPath = "."
)

# Define the fixed command and filters
$exePath = ".\Source2Viewer-CLI.exe"
$folderFilter = "panorama/images/overheadmaps/"
$extensionFilter = "vtex_c"

# Run the command to extract the files
& $exePath -i $inputPath -f $folderFilter -e $extensionFilter -o $outputPath -d

# Define the source directory (where the extracted files are)
$sourceDir = Join-Path $outputPath $folderFilter

# Define the target directory for the renamed files ("maps")
$targetDir = Join-Path $outputPath "maps"

# If the target directory doesn't exist, create it.
if (-not (Test-Path $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir | Out-Null
}

# Check if the source directory exists before processing.
if (Test-Path $sourceDir) {
    # Process each file ending with "_radar_psd.png"
    Get-ChildItem -Path $sourceDir -Filter "*_radar_psd.png" | ForEach-Object {
        # Skip files with undesired substrings.
        if ($_.Name -like "*_preview*" -or $_.Name -like "*_vanity*") {
            return
        }

        # Define the new file name by replacing "_radar_psd.png" with ".png"
        $newFileName = $_.Name -replace "_radar_psd\.png$", ".png"
        
        # Rename the file within the source directory.
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

# Generate map data
$resourceFolder = "resource/overviews/"
& $exePath -i $inputPath -f $resourceFolder -e "txt" -o $outputPath -d
$tempOutputDir = Join-Path -Path $outputPath -ChildPath $resourceFolder
uv run awpy mapdata $tempOutputDir
Move-Item -Path "map-data.json" -Destination $targetDir -Force

# Create a zip archive of the final files in the target directory.
$zipPath = Join-Path $outputPath "maps.zip"
Compress-Archive -Path (Join-Path $targetDir "*") -DestinationPath $zipPath -Force
Write-Host "Zip archive created at: $zipPath" -ForegroundColor Cyan

# Function to compute a hash based on the actual contents of all files in a directory.
function Get-DirectoryContentHash {
    param(
        [Parameter(Mandatory=$true)]
        [string]$DirectoryPath,
        [string]$Algorithm = "SHA256"
    )
    # Retrieve all files recursively and sort them by full path for consistency.
    $files = Get-ChildItem -Path $DirectoryPath -File -Recurse | Sort-Object FullName

    $hasher = [System.Security.Cryptography.HashAlgorithm]::Create($Algorithm)
    $ms = New-Object System.IO.MemoryStream

    foreach ($file in $files) {
        # Include the file's relative path (as bytes) so that names affect the hash.
        $relativePath = $file.FullName.Substring($DirectoryPath.Length).TrimStart('\')
        $pathBytes = [System.Text.Encoding]::UTF8.GetBytes($relativePath)
        $ms.Write($pathBytes, 0, $pathBytes.Length)

        # Include the file's content.
        $fileBytes = [System.IO.File]::ReadAllBytes($file.FullName)
        $ms.Write($fileBytes, 0, $fileBytes.Length)
    }

    $ms.Position = 0
    $hashBytes = $hasher.ComputeHash($ms)
    $hashHex = [BitConverter]::ToString($hashBytes) -replace '-', ''
    return $hashHex
}

# Compute and print the hash of the zip archive using SHA256.
$fileHash = Get-FileHash -Path $zipPath -Algorithm SHA256
Write-Host "Zip file hash (SHA256): $($fileHash.Hash)" -ForegroundColor Cyan

# Compute and print the hash of the contents of the output directory (the .tri files).
$contentHash = Get-DirectoryContentHash -DirectoryPath $targetDir
Write-Host "Combined content hash of output files: $contentHash" -ForegroundColor Cyan
