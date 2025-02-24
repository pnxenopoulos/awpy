param(
    [Parameter(Mandatory=$false)]
    [string]$inputPath = "C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\game\csgo\maps",

    # Final output folder for spawn JSONs; defaults to a folder named "spawns" in the current directory.
    [Parameter(Mandatory=$false)]
    [string]$outputDirectory = (Join-Path (Get-Location).Path "spawns")
)

# Ensure the output directory exists; create it if it doesn't.
if (-not (Test-Path $outputDirectory)) {
    New-Item -ItemType Directory -Path $outputDirectory | Out-Null
}

# Verify the input path exists.
if (-not (Test-Path $inputPath)) {
    Write-Host "The specified directory does not exist: $inputPath" -ForegroundColor Red
    exit
}

# Process each .vpk file found in the input directory, skipping those with unwanted substrings.
Get-ChildItem -Path $inputPath -Filter "*.vpk" | Where-Object {
    $_.Name -notlike "*_preview*" -and $_.Name -notlike "*_vanity*" -and $_.Name -notlike "*lobby_*"  -and $_.Name -notlike "*graphics_*"
} | ForEach-Object {
    $filePath = $_.FullName
    $fileNameWithoutExtension = $_.BaseName

    Write-Host "Processing file: $filePath" -ForegroundColor Green

    # Create a temporary output directory in the system's temp folder.
    $tempOutputDir = Join-Path ([System.IO.Path]::GetTempPath()) ([System.Guid]::NewGuid().ToString())
    New-Item -ItemType Directory -Path $tempOutputDir | Out-Null

    # Run Source2Viewer-CLI to generate the vents file into the temporary folder.
    .\Source2Viewer-CLI.exe -i $filePath -e "vents_c" -o $tempOutputDir -d

    # Construct the expected path for the generated vents file.
    $ventsFilePath = Join-Path -Path $tempOutputDir -ChildPath "maps\$fileNameWithoutExtension\entities\default_ents.vents"
    if (-not (Test-Path $ventsFilePath)) {
        Write-Host "Error: Expected vents file not found for $fileNameWithoutExtension" -ForegroundColor Red
        Remove-Item -Path $tempOutputDir -Recurse -Force
        return
    }

    # Run the awpy spawn command to create a .json file, outputting to a temporary file.
    $spawnJsonTempPath = Join-Path -Path $tempOutputDir -ChildPath "$fileNameWithoutExtension.json"
    Write-Host "Running awpy spawns on: $ventsFilePath" -ForegroundColor Yellow
    uv run awpy spawn $ventsFilePath --outpath $spawnJsonTempPath

    if (Test-Path $spawnJsonTempPath) {
        $finalJsonPath = Join-Path -Path $outputDirectory -ChildPath "$fileNameWithoutExtension.json"
        Move-Item -Path $spawnJsonTempPath -Destination $finalJsonPath -Force
        Write-Host "Output saved as: $finalJsonPath" -ForegroundColor Cyan
    } else {
        Write-Host "Error: .json output not created for $fileNameWithoutExtension" -ForegroundColor Red
    }

    # Clean up the temporary directory.
    Remove-Item -Path $tempOutputDir -Recurse -Force
}

# Create a zip archive of the output spawn JSON files.
$zipPath = Join-Path (Split-Path $outputDirectory) "spawns.zip"
Compress-Archive -Path (Join-Path $outputDirectory "*") -DestinationPath $zipPath -Force

if (Test-Path $zipPath) {
    Write-Host "Zip file created at: $zipPath" -ForegroundColor Green
} else {
    Write-Host "Error: Zip file was not created." -ForegroundColor Red
}

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
        # Include the file's relative path (as bytes) so that file names affect the hash.
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

# Compute and print the hash of the contents of the output directory (the spawn JSON files).
$contentHash = Get-DirectoryContentHash -DirectoryPath $outputDirectory
Write-Host "Combined content hash of output files: $contentHash" -ForegroundColor Cyan
