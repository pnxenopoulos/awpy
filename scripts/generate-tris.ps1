param(
    [Parameter(Mandatory=$false)]
    [string]$inputPath = "C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\game\csgo\maps",

    # Final output folder for .tri files; defaults to a folder named "tri" in the current directory.
    [Parameter(Mandatory=$false)]
    [string]$outputDirectory = (Join-Path (Get-Location).Path "tri")
)

$env:PYTHONUTF8 = "1"
# Ensure the output directory exists; create it if it doesn't.
if (-not (Test-Path $outputDirectory)) {
    New-Item -ItemType Directory -Path $outputDirectory | Out-Null
}

# Verify the input path exists.
if (-not (Test-Path $inputPath)) {
    Write-Host "The specified directory does not exist: $inputPath" -ForegroundColor Red
    exit
}

# Get project root and executable path
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = Resolve-Path (Join-Path $scriptRoot "..")
$viewerExe = Join-Path $projectRoot "Source2Viewer-CLI.exe"


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
        $startFound = $false

        $processInfo = New-Object System.Diagnostics.ProcessStartInfo
        $processInfo.FileName = $viewerExe
        $processInfo.Arguments = "-i `"$filePath`" --block `"PHYS`" -f `"maps/$fileNameWithoutExtension/world_physics.vmdl_c`""
        $processInfo.UseShellExecute = $false
        $processInfo.RedirectStandardOutput = $true
        $processInfo.RedirectStandardError = $true
        $processInfo.CreateNoWindow = $true

        $proc = [System.Diagnostics.Process]::Start($processInfo)
        $reader = $proc.StandardOutput
        $writer = New-Object System.IO.StreamWriter($vphysFilePath, $false, [System.Text.Encoding]::UTF8)

        while (($line = $reader.ReadLine()) -ne $null) {
            if (-not $startFound) {
                if ($line -eq '--- Data for block "PHYS" ---') {
                    $startFound = $true
                }
                continue
            }
            $writer.WriteLine($line)
        }

        $writer.Dispose()
        $reader.Dispose()
        $proc.WaitForExit()
        $proc.Dispose()

        if (-not $startFound) {
            throw "PHYS data block not found"
        }
    }
    catch {
        Write-Host "Error processing PHYS data: $_" -ForegroundColor Red
    }
    finally {
        if ($writer) { $writer.Dispose() }
        if ($reader) { $reader.Dispose() }
        if ($proc) { $proc.Dispose() }
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

# Compute and print the hash of the zip archive using SHA256.
$fileHash = Get-FileHash -Path $zipPath -Algorithm SHA256
Write-Host "Zip file hash (SHA256): $($fileHash.Hash)" -ForegroundColor Cyan
