# This script generates .tri files containing CS2 .vphys_c triangle information.

# Define the directory containing .vpk files
$sourcePath = "C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\game\csgo\maps"

# Get the current directory where the script is run
$outputDirectory = (Get-Location).Path

# Ensure the path exists
if (Test-Path $sourcePath) {
    # Get all .vpk files in the directory
    Get-ChildItem -Path $sourcePath -Filter "*.vpk" | ForEach-Object {
        # Get full path and base name of the file
        $filePath = $_.FullName
        $fileNameWithoutExtension = $_.BaseName

        # Temporary output directory for the tool
        $tempOutputDir = Join-Path -Path $outputDirectory -ChildPath $fileNameWithoutExtension

        # Create a temporary directory for the output
        if (-Not (Test-Path $tempOutputDir)) {
            New-Item -ItemType Directory -Path $tempOutputDir | Out-Null
        }

        # Construct and run the Source2Viewer-CLI command
        Write-Host "Processing file: $filePath" -ForegroundColor Green
        .\Source2Viewer-CLI.exe -i $filePath -e "vphys_c" -o $tempOutputDir -d

        # Move the output file to the current directory and rename it
        $generatedFile = Join-Path -Path $tempOutputDir -ChildPath "maps\$fileNameWithoutExtension\world_physics.vphys"
        $newFileName = Join-Path -Path $outputDirectory -ChildPath "$fileNameWithoutExtension.vphys"

        if (Test-Path $generatedFile) {
            Move-Item -Path $generatedFile -Destination $newFileName -Force
            Write-Host "Output saved as: $newFileName" -ForegroundColor Cyan

            # Run the awpy generate-tri command
            Write-Host "Running awpy generate-tri on: $newFileName" -ForegroundColor Yellow
            uv run awpy generate-tri $newFileName
        } else {
            Write-Host "Error: Expected output file not found for $fileNameWithoutExtension" -ForegroundColor Red
        }

        # Clean up the temporary directory
        Remove-Item -Path $tempOutputDir -Recurse -Force
    }
} else {
    Write-Host "The specified directory does not exist: $sourcePath" -ForegroundColor Red
}
