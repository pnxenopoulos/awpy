param(
    [Parameter(Mandatory=$false)]
    [string]$inputPath = "C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\game\csgo\maps",

    # Final output folder for .tri files; defaults to a folder named "tri" in the current directory.
    [Parameter(Mandatory=$false)]
    [string]$outputDirectory = (Join-Path (Get-Location).Path "tri")
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

# Process each .vpk file, excluding files with unwanted substrings.
Get-ChildItem -Path $inputPath -Filter "*.vpk" | Where-Object {
    $_.Name -notlike "*_preview*" -and $_.Name -notlike "*_vanity*" -and $_.Name -notlike "*lobby_*" -and $_.Name -notlike "*graphics_*"
} | ForEach-Object {
    $filePath = $_.FullName
    $fileNameWithoutExtension = $_.BaseName

    Write-Host "Processing file: $filePath" -ForegroundColor Green

    # Create a temporary output directory in the system temp folder.
    $tempOutputDir = Join-Path ([System.IO.Path]::GetTempPath()) ([System.Guid]::NewGuid().ToString())
    New-Item -ItemType Directory -Path $tempOutputDir | Out-Null

    $vphysFilePath = Join-Path $tempOutputDir "maps\$fileNameWithoutExtension\world_physics.vphys"
    $parentDir = Split-Path $vphysFilePath -Parent
    if (!(Test-Path $parentDir)) {
        New-Item -ItemType Directory -Path $parentDir -Force | Out-Null
    }

    try {
        # Try fast in-memory method first
        $output = .\Source2Viewer-CLI.exe -i $filePath --block "PHYS" -f "maps/$fileNameWithoutExtension/world_physics.vmdl_c" 2>&1
        $outputLines = $output -split "`r?`n"

        $startIndex = $outputLines.IndexOf('--- Data for block "PHYS" ---') + 1
        if ($startIndex -le 0 -or $startIndex -ge $outputLines.Count) {
            throw "PHYS data block not found"
        }

        $physData = $outputLines[$startIndex..($outputLines.Count - 1)] -join "`n"
        $physData | Out-File -FilePath $vphysFilePath -Encoding utf8
    }
    catch [System.OutOfMemoryException] {
        # Fall back to stream processing if OOM occurs
        Write-Warning "Falling back to streaming method due to memory constraints"

        $tempFile = [System.IO.Path]::GetTempFileName()
        try {
            $process = Start-Process -FilePath ".\Source2Viewer-CLI.exe" -ArgumentList @(
                "-i", "`"$filePath`"",
                "--block `"PHYS`"",
                "-f `"maps/$fileNameWithoutExtension/world_physics.vmdl_c`""
            ) -NoNewWindow -RedirectStandardOutput $tempFile -PassThru -Wait

            $foundMarker = $false
            $stream = [System.IO.File]::OpenRead($tempFile)
            $reader = New-Object System.IO.StreamReader($stream)
            $fileStream = [System.IO.File]::Create($vphysFilePath)
            $writer = New-Object System.IO.StreamWriter($fileStream, [System.Text.Encoding]::UTF8)

            while ($null -ne ($line = $reader.ReadLine())) {
                if (-not $foundMarker) {
                    if ($line -eq '--- Data for block "PHYS" ---') {
                        $foundMarker = $true
                    }
                    continue
                }
                $writer.WriteLine($line)
            }

            if (-not $foundMarker) {
                Write-Host "Error: PHYS data block not found (streaming method)" -ForegroundColor Red
            }
        }
        finally {
            if ($writer) { $writer.Dispose() }
            if ($fileStream) { $fileStream.Dispose() }
            if ($reader) { $reader.Dispose() }
            if ($stream) { $stream.Dispose() }
            if (Test-Path $tempFile) { Remove-Item $tempFile -ErrorAction SilentlyContinue }
        }
    }
    catch {
        Write-Host "Error processing PHYS data: $_" -ForegroundColor Red
    }


    if (-not (Test-Path $vphysFilePath)) {
        Write-Host "Error: Expected vphys file not found for $fileNameWithoutExtension" -ForegroundColor Red
        Remove-Item -Path $tempOutputDir -Recurse -Force
        return
    }

    # Run the awpy tri command to generate a .tri file, outputting to a temporary file.
    $triTempPath = Join-Path -Path $tempOutputDir -ChildPath "$fileNameWithoutExtension.tri"
    Write-Host "Running awpy generate-tri on: $vphysFilePath" -ForegroundColor Yellow
    uv run awpy tri $vphysFilePath --outpath $triTempPath

    if (Test-Path $triTempPath) {
        $finalTriPath = Join-Path -Path $outputDirectory -ChildPath "$fileNameWithoutExtension.tri"
        Move-Item -Path $triTempPath -Destination $finalTriPath -Force
        Write-Host "Output saved as: $finalTriPath" -ForegroundColor Cyan
    } else {
        Write-Host "Error: .tri output not created for $fileNameWithoutExtension" -ForegroundColor Red
    }

    # Run the awpy tri command to generate a .tri file, outputting to a temporary file.
    $triTempPath = Join-Path -Path $tempOutputDir -ChildPath "$fileNameWithoutExtension-clippings.tri"
    Write-Host "Running awpy generate-tri on: $vphysFilePath" -ForegroundColor Yellow
    uv run awpy tri $vphysFilePath --outpath $triTempPath --include_player_clippings

    if (Test-Path $triTempPath) {
        $finalTriPath = Join-Path -Path $outputDirectory -ChildPath "$fileNameWithoutExtension-clippings.tri"
        Move-Item -Path $triTempPath -Destination $finalTriPath -Force
        Write-Host "Output saved as: $finalTriPath" -ForegroundColor Cyan
    } else {
        Write-Host "Error: .tri output not created for $fileNameWithoutExtension" -ForegroundColor Red
    }

    # Clean up the temporary directory.
    Remove-Item -Path $tempOutputDir -Recurse -Force
}

# Create a zip archive of the output .tri files.
$zipPath = Join-Path (Split-Path $outputDirectory) "tris.zip"
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
$contentHash = Get-DirectoryContentHash -DirectoryPath $outputDirectory
Write-Host "Combined content hash of output files: $contentHash" -ForegroundColor Cyan
