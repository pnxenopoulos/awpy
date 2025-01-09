# This script processes and decompiles .vtex_c files to images.

# Define the source directory containing the .vtex_c files
$sourcePath = "C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\game\csgo\panorama\images\overheadmaps"

# Get the current directory where the script is run
$outputDirectory = (Get-Location).Path

# Ensure the path exists
if (Test-Path $sourcePath) {
    # Get all .vtex_c files in the directory
    Get-ChildItem -Path $sourcePath -Filter "*_radar_psd.vtex_c" | ForEach-Object {
        # Get full path and base name of the file
        $filePath = $_.FullName
        $fileNameWithoutExtension = $_.BaseName

        # Construct and run the Source2Viewer-CLI command
        Write-Host "Processing file: $filePath" -ForegroundColor Green
        $outputFileName = "$fileNameWithoutExtension.png"
        $outputFilePath = Join-Path -Path $outputDirectory -ChildPath $outputFileName

        .\Source2Viewer-CLI.exe -i $filePath -o $outputFilePath

        # Check if the image was successfully created
        if (Test-Path $outputFilePath) {
            Write-Host "Output saved as: $outputFilePath" -ForegroundColor Cyan
        } else {
            Write-Host "Error: Failed to process $fileNameWithoutExtension" -ForegroundColor Red
        }
    }
} else {
    Write-Host "The specified directory does not exist: $sourcePath" -ForegroundColor Red
}
