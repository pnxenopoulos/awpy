param(
    [Parameter(Mandatory=$false)]
    [string]$inputPath = "C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\game\csgo\maps",

    # The output directory where the final .json files will be placed. Defaults to a folder named "nav".
    [Parameter(Mandatory=$false)]
    [string]$outputDirectory = (Join-Path (Get-Location).Path "nav")
)

# Ensure the output directory ("nav") exists; create it if it doesn't.
if (-not (Test-Path $outputDirectory)) {
    New-Item -ItemType Directory -Path $outputDirectory | Out-Null
}

# Verify the input path exists.
if (-not (Test-Path $inputPath)) {
    Write-Host "The specified directory does not exist: $inputPath" -ForegroundColor Red
    exit
}

# Process each .vpk file, excluding files with unwanted substrings.
Get-ChildItem -Path $inputPath -Filter "*.vpk" | Where-Object {
    $_.Name -notlike "*_preview*" -and $_.Name -notlike "*_vanity*" -and $_.Name -notlike "*lobby_*"
} | ForEach-Object {
    $filePath = $_.FullName
    $fileNameWithoutExtension = $_.BaseName

    Write-Host "Processing file: $filePath" -ForegroundColor Green

    # Create a temporary output directory in the system temp folder.
    $tempOutputDir = Join-Path ([System.IO.Path]::GetTempPath()) ([System.Guid]::NewGuid().ToString())
    New-Item -ItemType Directory -Path $tempOutputDir | Out-Null

    # Run Source2Viewer-CLI to generate the .nav file into the temporary folder.
    .\Source2Viewer-CLI.exe -i $filePath -e "nav" -o $tempOutputDir -d

    # Construct the expected path for the generated .nav file.
    $navFilePath = Join-Path -Path $tempOutputDir -ChildPath "maps\$fileNameWithoutExtension.nav"
    if (-not (Test-Path $navFilePath)) {
        Write-Host "Error: Expected nav file not found for $fileNameWithoutExtension" -ForegroundColor Red
        Remove-Item -Path $tempOutputDir -Recurse -Force
        return
    }

    # Run the awpy nav command to create a .json file.
    $jsonTempPath = Join-Path -Path $tempOutputDir -ChildPath "$fileNameWithoutExtension.json"
    Write-Host "Running awpy nav on: $navFilePath" -ForegroundColor Yellow
    uv run awpy nav $navFilePath --outpath $jsonTempPath

    if (Test-Path $jsonTempPath) {
        $finalJsonPath = Join-Path -Path $outputDirectory -ChildPath "$fileNameWithoutExtension.json"
        Move-Item -Path $jsonTempPath -Destination $finalJsonPath -Force
        Write-Host "Output saved as: $finalJsonPath" -ForegroundColor Cyan
    } else {
        Write-Host "Error: .json output not created for $fileNameWithoutExtension" -ForegroundColor Red
    }

    # Clean up the temporary directory.
    Remove-Item -Path $tempOutputDir -Recurse -Force
}

# Create a zip archive of the output JSON files.
$zipPath = Join-Path (Split-Path $outputDirectory) "navs.zip"
Compress-Archive -Path (Join-Path $outputDirectory "*") -DestinationPath $zipPath -Force

if (Test-Path $zipPath) {
    Write-Host "Zip file created at: $zipPath" -ForegroundColor Green
} else {
    Write-Host "Error: Zip file was not created." -ForegroundColor Red
}

# Function to compute a hash based on the contents of all files in a directory.
function Get-DirectoryContentHash {
    param(
        [Parameter(Mandatory=$true)]
        [string]$DirectoryPath,
        [string]$Algorithm = "SHA256"
    )
    # Get all files recursively and sort them by their full path for consistency.
    $files = Get-ChildItem -Path $DirectoryPath -File -Recurse | Sort-Object FullName

    # Initialize the hasher.
    $hasher = [System.Security.Cryptography.HashAlgorithm]::Create($Algorithm)
    
    # Create a memory stream to accumulate the data.
    $ms = New-Object System.IO.MemoryStream

    foreach ($file in $files) {
        # Write the file's relative path (as bytes) to ensure files with identical contents but different names produce different results.
        $relativePath = $file.FullName.Substring($DirectoryPath.Length).TrimStart('\')
        $pathBytes = [System.Text.Encoding]::UTF8.GetBytes($relativePath)
        $ms.Write($pathBytes, 0, $pathBytes.Length)

        # Write the file's contents.
        $fileBytes = [System.IO.File]::ReadAllBytes($file.FullName)
        $ms.Write($fileBytes, 0, $fileBytes.Length)
    }

    # Compute the hash of the combined stream.
    $ms.Position = 0
    $hashBytes = $hasher.ComputeHash($ms)
    $hashHex = [BitConverter]::ToString($hashBytes) -replace '-', ''
    return $hashHex
}

# Compute and print the hash of the zip archive using SHA256.
$fileHash = Get-FileHash -Path $zipPath -Algorithm SHA256
Write-Host "Zip file hash (SHA256): $($fileHash.Hash)" -ForegroundColor Cyan

# Compute and print the hash of the contents of the output directory (ignoring zip metadata).
$contentHash = Get-DirectoryContentHash -DirectoryPath $outputDirectory
Write-Host "Combined content hash of output files: $contentHash" -ForegroundColor Cyan
